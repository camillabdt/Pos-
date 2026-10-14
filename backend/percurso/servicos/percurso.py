"""Operações sobre o percurso do discente (entrada, meio, fim)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from percurso.dominio import situacao as regras
from percurso.dominio.modelos import (
    Avaliacao,
    Desligamento,
    Discente,
    DiscenteAtualizar,
    DiscenteCriar,
    DisciplinaCursada,
    PlanoTrabalho,
    Prorrogacao,
)
from percurso.servicos.repo import RegraViolada, Repo


class DiscenteResumo(BaseModel):
    id: str
    nome: str
    matricula: str
    nivel: str
    data_ingresso: date
    orientador_id: str
    orientador_nome: str | None
    tema: str | None
    situacao: regras.Situacao


class DiscenteDetalhe(Discente):
    orientador_nome: str | None = None
    coorientadores_nomes: list[str] = []
    situacao: regras.Situacao


class PercursoServico:
    def __init__(self, repo: Repo, hoje: date | None = None) -> None:
        self.repo = repo
        self._hoje = hoje

    @property
    def hoje(self) -> date:
        return self._hoje or date.today()

    # ---------------------------------------------------------------- leitura

    def situacao(self, d: Discente, catalogo=None) -> regras.Situacao:
        catalogo = catalogo if catalogo is not None else self.repo.disciplinas.por_id()
        return regras.calcular(d, self.repo.programa(), catalogo, self.hoje)

    def listar(self, filtro: str | None = None, orientador_id: str | None = None,
               busca: str | None = None) -> list[DiscenteResumo]:
        if filtro and filtro not in regras.FILTROS:
            raise RegraViolada(f"Filtro desconhecido: {filtro}. Use um de: {', '.join(regras.FILTROS)}.")
        programa = self.repo.programa()
        catalogo = self.repo.disciplinas.por_id()
        docentes = self.repo.docentes.por_id()
        termo = (busca or "").strip().lower()
        saida = []
        for d in self.repo.discentes.listar():
            if orientador_id and d.orientador_id != orientador_id and orientador_id not in d.coorientador_ids:
                continue
            if termo and termo not in d.nome.lower() and termo not in d.matricula.lower():
                continue
            s = regras.calcular(d, programa, catalogo, self.hoje)
            if filtro and not regras.FILTROS[filtro](s):
                continue
            orient = docentes.get(d.orientador_id)
            saida.append(DiscenteResumo(
                id=d.id, nome=d.nome, matricula=d.matricula, nivel=d.nivel,
                data_ingresso=d.data_ingresso, orientador_id=d.orientador_id,
                orientador_nome=orient.nome if orient else None, tema=d.tema, situacao=s,
            ))
        # Mais urgentes primeiro: atrasados, depois menor folga de prazo.
        saida.sort(key=lambda r: (
            not r.situacao.atrasado,
            r.situacao.dias_para_prazo if r.situacao.dias_para_prazo is not None else 10**6,
            r.nome.lower(),
        ))
        return saida

    def detalhe(self, d: Discente) -> DiscenteDetalhe:
        docentes = self.repo.docentes.por_id()
        orient = docentes.get(d.orientador_id)
        return DiscenteDetalhe(
            **d.model_dump(),
            orientador_nome=orient.nome if orient else None,
            coorientadores_nomes=[docentes[i].nome for i in d.coorientador_ids if i in docentes],
            situacao=self.situacao(d),
        )

    # ---------------------------------------------------------------- entrada

    def _valida_orientacao(self, orientador_id: str | None, coorientadores: list[str] | None) -> None:
        if orientador_id is not None and not self.repo.docentes.existe(orientador_id):
            raise RegraViolada("Orientador(a) não cadastrado(a) como docente.")
        for c in coorientadores or []:
            if not self.repo.docentes.existe(c):
                raise RegraViolada(f"Coorientador(a) '{c}' não cadastrado(a) como docente.")
        if orientador_id and coorientadores and orientador_id in coorientadores:
            raise RegraViolada("O(a) orientador(a) não pode ser também coorientador(a).")

    def _valida_disciplinas(self, ids: list[str]) -> None:
        faltando = [i for i in ids if not self.repo.disciplinas.existe(i)]
        if faltando:
            raise RegraViolada(f"Disciplina(s) não cadastrada(s): {', '.join(faltando)}.")

    def criar(self, dados: DiscenteCriar) -> Discente:
        self._valida_orientacao(dados.orientador_id, dados.coorientador_ids)
        if dados.plano:
            self._valida_disciplinas(dados.plano.disciplinas_planejadas)
        if any(d.matricula == dados.matricula for d in self.repo.discentes.listar()):
            raise RegraViolada(f"Já existe discente com a matrícula {dados.matricula}.")
        return self.repo.discentes.criar(dados)

    def atualizar(self, id: str, dados: DiscenteAtualizar) -> Discente:
        atual = self.repo.discentes.obter(id)
        self._valida_orientacao(
            dados.orientador_id if dados.orientador_id is not None else atual.orientador_id,
            dados.coorientador_ids if dados.coorientador_ids is not None else atual.coorientador_ids,
        )
        return self.repo.discentes.atualizar(id, dados)

    def definir_plano(self, d: Discente, plano: PlanoTrabalho) -> Discente:
        self._valida_disciplinas(plano.disciplinas_planejadas)
        d.plano = plano
        return self.repo.discentes.salvar(d)

    # ---------------------------------------------------------------- meio

    def registrar_disciplina(self, d: Discente, item: DisciplinaCursada) -> Discente:
        self._valida_disciplinas([item.disciplina_id])
        # Mesma disciplina no mesmo semestre = atualização (ex.: cursando -> aprovado).
        d.disciplinas = [
            c for c in d.disciplinas
            if not (c.disciplina_id == item.disciplina_id and c.semestre == item.semestre)
        ] + [item]
        d.disciplinas.sort(key=lambda c: c.semestre)
        return self.repo.discentes.salvar(d)

    def remover_disciplina(self, d: Discente, disciplina_id: str, semestre: str) -> Discente:
        antes = len(d.disciplinas)
        d.disciplinas = [c for c in d.disciplinas
                         if not (c.disciplina_id == disciplina_id and c.semestre == semestre)]
        if len(d.disciplinas) == antes:
            raise RegraViolada("Essa disciplina não está registrada nesse semestre.")
        return self.repo.discentes.salvar(d)

    def _valida_avaliacao(self, d: Discente, a: Avaliacao) -> None:
        if a.data < d.data_ingresso:
            raise RegraViolada("A data não pode ser anterior ao ingresso.")
        for m in a.banca:
            if m.docente_id and not self.repo.docentes.existe(m.docente_id):
                raise RegraViolada(f"Membro da banca '{m.nome}' aponta para docente inexistente.")

    def registrar_qualificacao(self, d: Discente, q: Avaliacao) -> Discente:
        self._valida_avaliacao(d, q)
        if d.defesa and d.defesa.aprovada and not q.aprovada:
            raise RegraViolada("Discente já titulado(a): a qualificação precisa constar como aprovada.")
        d.qualificacao = q
        return self.repo.discentes.salvar(d)

    def conceder_prorrogacao(self, d: Discente, p: Prorrogacao) -> Discente:
        d.prorrogacoes.append(p)
        return self.repo.discentes.salvar(d)

    def remover_prorrogacao(self, d: Discente, indice: int) -> Discente:
        if not 0 <= indice < len(d.prorrogacoes):
            raise RegraViolada("Prorrogação não encontrada.")
        d.prorrogacoes.pop(indice)
        return self.repo.discentes.salvar(d)

    # ---------------------------------------------------------------- fim

    def registrar_defesa(self, d: Discente, defesa: Avaliacao) -> Discente:
        self._valida_avaliacao(d, defesa)
        if defesa.aprovada and not (d.qualificacao and d.qualificacao.aprovada):
            raise RegraViolada("Registre a qualificação aprovada antes de uma defesa aprovada.")
        if d.qualificacao and defesa.data < d.qualificacao.data:
            raise RegraViolada("A defesa não pode ser anterior à qualificação.")
        if d.desligamento:
            raise RegraViolada("Discente desligado(a). Remova o desligamento antes de registrar a defesa.")
        d.defesa = defesa
        if not d.tema:
            d.tema = defesa.titulo
        return self.repo.discentes.salvar(d)

    def desligar(self, d: Discente, des: Desligamento | None) -> Discente:
        if des and d.defesa and d.defesa.aprovada:
            raise RegraViolada("Discente já titulado(a) não pode ser desligado(a).")
        if des and des.data < d.data_ingresso:
            raise RegraViolada("A data não pode ser anterior ao ingresso.")
        d.desligamento = des
        return self.repo.discentes.salvar(d)
