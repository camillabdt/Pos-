"""Produções de discentes e docentes, numa coleção só (coautoria natural)."""

from __future__ import annotations

import unicodedata
from collections import Counter

from pydantic import BaseModel

from percurso.dominio import metricas
from percurso.dominio.modelos import (
    TIPOS_BIBLIOGRAFICOS,
    Autor,
    Producao,
    ProducaoCriar,
    Veiculo,
    VeiculoRef,
    normaliza_issn,
)
from percurso.servicos.repo import RegraViolada, Repo


def normaliza_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().replace(".", " ").split())


def ids_autores(p: ProducaoCriar) -> set[str]:
    return {i for a in p.autores for i in (a.discente_id, a.docente_id) if i}


class ResumoProducao(BaseModel):
    total: int
    por_tipo: dict[str, int]
    por_ano: dict[int, int]
    por_qualis: dict[str, int]
    com_discentes: int


class ProducoesServico:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    def _valida_autores(self, autores: list[Autor]) -> None:
        """Confere os vínculos e preenche o nome de quem é do programa."""
        for a in autores:
            pessoa = None
            if a.discente_id:
                pessoa = self.repo.discentes.get(a.discente_id)
                if not pessoa:
                    raise RegraViolada(f"Autor(a) '{a.nome}' aponta para discente inexistente.")
            elif a.docente_id:
                pessoa = self.repo.docentes.get(a.docente_id)
                if not pessoa:
                    raise RegraViolada(f"Autor(a) '{a.nome}' aponta para docente inexistente.")
            if pessoa and not a.nome.strip():
                a.nome = pessoa.nome
            if not a.nome.strip():
                raise RegraViolada("Informe o nome de cada autor(a) externo(a).")

    def completar_qualis(self, veiculo: VeiculoRef | None) -> VeiculoRef | None:
        """Se o veículo tem ISSN cadastrado, herda o estrato Qualis do cadastro."""
        if not veiculo or veiculo.qualis or not veiculo.issn:
            return veiculo
        cadastro = self.veiculo_por_issn(veiculo.issn)
        if cadastro:
            veiculo.qualis = cadastro.qualis
            veiculo.nome = veiculo.nome or cadastro.nome
        return veiculo

    def veiculo_por_issn(self, issns: list[str]) -> Veiculo | None:
        alvo = {normaliza_issn(i) for i in issns}
        for v in self.repo.veiculos.listar():
            if alvo & set(v.issn):
                return v
        return None

    def criar(self, dados: ProducaoCriar) -> Producao:
        self._valida_autores(dados.autores)
        dados.veiculo = self.completar_qualis(dados.veiculo)
        if dados.doi and self.por_doi(dados.doi):
            raise RegraViolada(f"Já existe produção com o DOI {dados.doi}. Edite a existente e inclua o(a) autor(a).")
        return self.repo.producoes.criar(dados)

    def atualizar(self, id: str, dados: ProducaoCriar) -> Producao:
        atual = self.repo.producoes.obter(id)
        self._valida_autores(dados.autores)
        dados.veiculo = self.completar_qualis(dados.veiculo)
        outra = self.por_doi(dados.doi) if dados.doi else None
        if outra and outra.id != id:
            raise RegraViolada(f"Outra produção já usa o DOI {dados.doi}.")
        return self.repo.producoes.salvar(Producao(
            **dados.model_dump(), id=id, origem=atual.origem,
            openalex_id=atual.openalex_id, citacoes=atual.citacoes,
        ))

    def por_doi(self, doi: str | None) -> Producao | None:
        if not doi:
            return None
        return next((p for p in self.repo.producoes.listar() if p.doi == doi), None)

    def listar(
        self,
        discente_id: str | None = None,
        docente_id: str | None = None,
        tipo: str | None = None,
        ano_de: int | None = None,
        ano_ate: int | None = None,
        so_com_discentes: bool = False,
        busca: str | None = None,
    ) -> list[Producao]:
        termo = (busca or "").strip().lower()
        saida = []
        for p in self.repo.producoes.listar():
            if discente_id and not any(a.discente_id == discente_id for a in p.autores):
                continue
            if docente_id and not any(a.docente_id == docente_id for a in p.autores):
                continue
            if tipo and p.tipo != tipo:
                continue
            if ano_de and p.ano < ano_de:
                continue
            if ano_ate and p.ano > ano_ate:
                continue
            if so_com_discentes and not any(a.discente_id for a in p.autores):
                continue
            if termo and termo not in p.titulo.lower():
                continue
            saida.append(p)
        saida.sort(key=lambda p: (-p.ano, p.titulo.lower()))
        return saida

    @staticmethod
    def resumir(producoes: list[Producao]) -> ResumoProducao:
        return ResumoProducao(
            total=len(producoes),
            por_tipo=dict(Counter(p.tipo.value for p in producoes).most_common()),
            por_ano=dict(sorted(Counter(p.ano for p in producoes).items())),
            por_qualis=dict(sorted(Counter(
                (p.veiculo.qualis if p.veiculo and p.veiculo.qualis else "sem estrato")
                for p in producoes if p.tipo in TIPOS_BIBLIOGRAFICOS
            ).items())),
            com_discentes=sum(1 for p in producoes if any(a.discente_id for a in p.autores)),
        )

    def metricas_docente(self, docente_id: str, ano_atual: int):
        prods = [p for p in self.listar(docente_id=docente_id) if p.citacoes is not None]
        cits = [p.citacoes for p in prods]
        return {
            "h_index": metricas.h_index(cits),
            "h5_index": metricas.h5_index(((p.ano, p.citacoes) for p in prods), ano_atual),
            "i10_index": metricas.i10_index(cits),
            "citacoes": sum(c or 0 for c in cits),
        }
