"""Regras que derivam a situação do discente a partir do percurso registrado.

Tudo aqui é função pura: recebe os fatos (discente, programa, disciplinas,
data de hoje) e devolve a situação. Nada é persistido — mudar uma regra
muda imediatamente o painel, sem migração de dados.

Regras (para um discente com vínculo ativo):

- prazo de conclusão = ingresso + prazo do nível + soma das prorrogações
- prazo de qualificação = ingresso + meses até qualificar do nível
- ATRASADO            = hoje > prazo de conclusão
- QUALIFICAÇÃO ATRASADA = não qualificou e hoje > prazo de qualificação
- PRAZO PRÓXIMO       = não atrasado e faltam <= alerta_dias para o prazo
- EM DIA              = nem atrasado nem com qualificação atrasada
- TITULADO            = defesa com resultado aprovado (com ou sem ressalvas)
- DESLIGADO           = desligamento registrado
"""

from __future__ import annotations

import calendar
from datetime import date
from enum import StrEnum

from pydantic import BaseModel

from percurso.dominio.modelos import (
    DISCIPLINA_CONCLUIDA,
    Discente,
    Disciplina,
    Programa,
)

DIAS_POR_MES = 30.4375


class Vinculo(StrEnum):
    ATIVO = "ativo"
    TITULADO = "titulado"
    DESLIGADO = "desligado"


class Fase(StrEnum):
    """Em que ponto do percurso o discente está — para a linha do tempo."""

    ENTRADA = "entrada"          # ainda sem plano de trabalho
    CURSANDO = "cursando"        # com plano, ainda não qualificou
    QUALIFICADO = "qualificado"  # qualificou, ainda não defendeu
    DEFESA_AGENDADA = "defesa_agendada"
    TITULADO = "titulado"
    DESLIGADO = "desligado"


class ResumoDisciplinas(BaseModel):
    planejadas: int = 0
    cumpridas_do_plano: int = 0
    pendentes_do_plano: list[str] = []   # ids de disciplinas planejadas ainda não concluídas
    fora_do_plano: list[str] = []        # ids concluídos que não estavam no plano
    cursando: int = 0
    creditos_concluidos: int = 0
    creditos_minimos: int = 0


class Situacao(BaseModel):
    vinculo: Vinculo
    fase: Fase
    prazo_qualificacao: date
    prazo_conclusao: date
    meses_prorrogados: int
    qualificado: bool
    atrasado: bool
    qualificacao_atrasada: bool
    prazo_proximo: bool
    em_dia: bool
    dias_para_prazo: int | None      # negativo = dias de atraso; None se não ativo
    meses_no_programa: float
    tempo_titulacao_meses: float | None
    titulou_no_prazo: bool | None
    disciplinas: ResumoDisciplinas
    pendencias: list[str]            # frases curtas para exibir ("Não qualificou", ...)


def soma_meses(d: date, meses: int) -> date:
    """Soma meses a uma data, ajustando para o último dia quando o mês é mais curto."""
    total = d.month - 1 + meses
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def meses_entre(inicio: date, fim: date) -> float:
    return round((fim - inicio).days / DIAS_POR_MES, 1)


def resumir_disciplinas(
    discente: Discente,
    catalogo: dict[str, Disciplina],
    creditos_minimos: int,
) -> ResumoDisciplinas:
    planejadas = list(dict.fromkeys(discente.plano.disciplinas_planejadas)) if discente.plano else []
    concluidas = {c.disciplina_id for c in discente.disciplinas if c.situacao in DISCIPLINA_CONCLUIDA}
    cursando = {c.disciplina_id for c in discente.disciplinas if c.situacao == "cursando"}
    creditos = sum(catalogo[i].creditos for i in concluidas if i in catalogo)
    return ResumoDisciplinas(
        planejadas=len(planejadas),
        cumpridas_do_plano=sum(1 for i in planejadas if i in concluidas),
        pendentes_do_plano=[i for i in planejadas if i not in concluidas],
        fora_do_plano=sorted(i for i in concluidas if i not in planejadas),
        cursando=len(cursando),
        creditos_concluidos=creditos,
        creditos_minimos=creditos_minimos,
    )


def calcular(
    discente: Discente,
    programa: Programa,
    catalogo: dict[str, Disciplina],
    hoje: date,
) -> Situacao:
    prazos = programa.prazos(discente.nivel)
    meses_prorrogados = sum(p.meses for p in discente.prorrogacoes)
    prazo_conclusao = soma_meses(discente.data_ingresso, prazos.conclusao_meses + meses_prorrogados)
    prazo_qualificacao = soma_meses(discente.data_ingresso, prazos.qualificacao_meses)

    qualificado = bool(discente.qualificacao and discente.qualificacao.aprovada)
    titulado = bool(discente.defesa and discente.defesa.aprovada)
    disciplinas = resumir_disciplinas(discente, catalogo, prazos.creditos_minimos)

    if titulado:
        vinculo = Vinculo.TITULADO
    elif discente.desligamento:
        vinculo = Vinculo.DESLIGADO
    else:
        vinculo = Vinculo.ATIVO
    ativo = vinculo == Vinculo.ATIVO

    atrasado = ativo and hoje > prazo_conclusao
    qualificacao_atrasada = ativo and not qualificado and hoje > prazo_qualificacao
    dias_para_prazo = (prazo_conclusao - hoje).days if ativo else None
    prazo_proximo = (
        ativo and not atrasado and dias_para_prazo is not None and dias_para_prazo <= programa.alerta_dias
    )
    em_dia = ativo and not atrasado and not qualificacao_atrasada

    fim = (
        discente.defesa.data if titulado and discente.defesa
        else discente.desligamento.data if discente.desligamento
        else hoje
    )
    tempo_titulacao = meses_entre(discente.data_ingresso, discente.defesa.data) if titulado and discente.defesa else None
    no_prazo = (discente.defesa.data <= prazo_conclusao) if titulado and discente.defesa else None

    if vinculo == Vinculo.TITULADO:
        fase = Fase.TITULADO
    elif vinculo == Vinculo.DESLIGADO:
        fase = Fase.DESLIGADO
    elif discente.defesa and discente.defesa.resultado == "agendada":
        fase = Fase.DEFESA_AGENDADA
    elif qualificado:
        fase = Fase.QUALIFICADO
    elif discente.plano:
        fase = Fase.CURSANDO
    else:
        fase = Fase.ENTRADA

    pendencias: list[str] = []
    if ativo:
        if atrasado:
            pendencias.append(f"Prazo de conclusão vencido há {-dias_para_prazo} dias")
        elif prazo_proximo:
            pendencias.append(f"Prazo de conclusão em {dias_para_prazo} dias")
        if qualificacao_atrasada:
            pendencias.append(f"Qualificação atrasada desde {prazo_qualificacao.strftime('%d/%m/%Y')}")
        if not discente.plano:
            pendencias.append("Sem plano de trabalho")
        if disciplinas.pendentes_do_plano:
            n = len(disciplinas.pendentes_do_plano)
            pendencias.append(f"{n} disciplina{'s' if n > 1 else ''} do plano por cursar")
        if qualificado and not discente.tema:
            pendencias.append("Tema da dissertação não registrado" if discente.nivel == "mestrado"
                              else "Tema da tese não registrado")

    return Situacao(
        vinculo=vinculo,
        fase=fase,
        prazo_qualificacao=prazo_qualificacao,
        prazo_conclusao=prazo_conclusao,
        meses_prorrogados=meses_prorrogados,
        qualificado=qualificado,
        atrasado=atrasado,
        qualificacao_atrasada=qualificacao_atrasada,
        prazo_proximo=prazo_proximo,
        em_dia=em_dia,
        dias_para_prazo=dias_para_prazo,
        meses_no_programa=meses_entre(discente.data_ingresso, fim),
        tempo_titulacao_meses=tempo_titulacao,
        titulou_no_prazo=no_prazo,
        disciplinas=disciplinas,
        pendencias=pendencias,
    )


# Filtros do painel: nome -> predicado sobre a situação.
FILTROS = {
    "ativos": lambda s: s.vinculo == Vinculo.ATIVO,
    "em_dia": lambda s: s.em_dia,
    "atrasados": lambda s: s.atrasado,
    "nao_qualificados": lambda s: s.vinculo == Vinculo.ATIVO and not s.qualificado,
    "qualificacao_atrasada": lambda s: s.qualificacao_atrasada,
    "prazo_proximo": lambda s: s.prazo_proximo,
    "titulados": lambda s: s.vinculo == Vinculo.TITULADO,
    "desligados": lambda s: s.vinculo == Vinculo.DESLIGADO,
}
