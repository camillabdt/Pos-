"""Visão geral do programa: quantos em dia, atrasados, sem qualificar etc."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import mean, median

from pydantic import BaseModel

from percurso.dominio import situacao as regras
from percurso.dominio.modelos import Nivel
from percurso.servicos.percurso import PercursoServico


class Totais(BaseModel):
    ativos: int = 0
    em_dia: int = 0
    atrasados: int = 0
    nao_qualificados: int = 0
    qualificacao_atrasada: int = 0
    prazo_proximo: int = 0
    titulados: int = 0
    desligados: int = 0


class Titulacao(BaseModel):
    nivel: str
    titulados: int
    media_meses: float | None
    mediana_meses: float | None
    no_prazo: int


class LinhaOrientador(BaseModel):
    docente_id: str
    nome: str
    ativos: int = 0
    em_dia: int = 0
    atrasados: int = 0
    nao_qualificados: int = 0
    titulados: int = 0


class AnoContagem(BaseModel):
    ano: int
    ingressos: int = 0
    titulacoes: int = 0
    desligamentos: int = 0


class Painel(BaseModel):
    hoje: date
    programa: str
    totais: Totais
    por_nivel: dict[str, Totais]
    titulacao: list[Titulacao]
    por_orientador: list[LinhaOrientador]
    por_ano: list[AnoContagem]
    producao_por_tipo: dict[str, int]
    producao_discente_ultimos_5_anos: int


def _acumula(t: Totais, s: regras.Situacao) -> None:
    for nome, pred in regras.FILTROS.items():
        if pred(s):
            setattr(t, nome, getattr(t, nome) + 1)


def montar_painel(servico: PercursoServico) -> Painel:
    repo = servico.repo
    programa = repo.programa()
    catalogo = repo.disciplinas.por_id()
    docentes = repo.docentes.por_id()
    hoje = servico.hoje

    totais = Totais()
    por_nivel = {n.value: Totais() for n in Nivel}
    tempos: dict[str, list[tuple[float, bool]]] = defaultdict(list)
    orient: dict[str, LinhaOrientador] = {}
    anos: dict[int, AnoContagem] = {}

    def ano(a: int) -> AnoContagem:
        return anos.setdefault(a, AnoContagem(ano=a))

    for d in repo.discentes.listar():
        s = regras.calcular(d, programa, catalogo, hoje)
        _acumula(totais, s)
        _acumula(por_nivel[d.nivel], s)

        ano(d.data_ingresso.year).ingressos += 1
        if s.vinculo == regras.Vinculo.TITULADO and d.defesa:
            ano(d.defesa.data.year).titulacoes += 1
            tempos[d.nivel].append((s.tempo_titulacao_meses or 0.0, bool(s.titulou_no_prazo)))
        elif s.vinculo == regras.Vinculo.DESLIGADO and d.desligamento:
            ano(d.desligamento.data.year).desligamentos += 1

        doc = docentes.get(d.orientador_id)
        linha = orient.setdefault(
            d.orientador_id,
            LinhaOrientador(docente_id=d.orientador_id, nome=doc.nome if doc else "(docente removido)"),
        )
        linha.ativos += s.vinculo == regras.Vinculo.ATIVO
        linha.em_dia += s.em_dia
        linha.atrasados += s.atrasado
        linha.nao_qualificados += regras.FILTROS["nao_qualificados"](s)
        linha.titulados += s.vinculo == regras.Vinculo.TITULADO

    titulacao = []
    for n in Nivel:
        lista = tempos.get(n.value, [])
        meses = [m for m, _ in lista]
        titulacao.append(Titulacao(
            nivel=n.value,
            titulados=len(lista),
            media_meses=round(mean(meses), 1) if meses else None,
            mediana_meses=round(median(meses), 1) if meses else None,
            no_prazo=sum(1 for _, ok in lista if ok),
        ))

    producoes = repo.producoes.listar()
    corte = hoje.year - 4
    return Painel(
        hoje=hoje,
        programa=programa.sigla,
        totais=totais,
        por_nivel=por_nivel,
        titulacao=titulacao,
        por_orientador=sorted(orient.values(), key=lambda x: (-x.atrasados, -x.ativos, x.nome)),
        por_ano=sorted(anos.values(), key=lambda a: a.ano),
        producao_por_tipo=dict(Counter(p.tipo.value for p in producoes if p.ano >= corte).most_common()),
        producao_discente_ultimos_5_anos=sum(
            1 for p in producoes if p.ano >= corte and any(a.discente_id for a in p.autores)
        ),
    )
