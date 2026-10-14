from __future__ import annotations

from datetime import date

from percurso.dominio.modelos import (
    Avaliacao,
    Desligamento,
    Discente,
    Disciplina,
    DisciplinaCursada,
    PlanoTrabalho,
    Programa,
    Prorrogacao,
)
from percurso.dominio.situacao import Fase, Vinculo, calcular, soma_meses

HOJE = date(2026, 10, 13)
PROG = Programa()
CAT = {
    "a": Disciplina(id="a", codigo="A", nome="A", creditos=4),
    "b": Disciplina(id="b", codigo="B", nome="B", creditos=4),
    "c": Disciplina(id="c", codigo="C", nome="C", creditos=2),
}


def aluno(meses_atras: int, **kw) -> Discente:
    base = dict(id="x", nome="X", matricula="1", data_ingresso=soma_meses(HOJE, -meses_atras), orientador_id="o")
    return Discente(**{**base, **kw})


def aprovada(data: date) -> Avaliacao:
    return Avaliacao(data=data, titulo="T", resultado="aprovado")


def test_soma_meses_ajusta_fim_de_mes():
    assert soma_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert soma_meses(date(2026, 3, 15), -3) == date(2025, 12, 15)
    assert soma_meses(date(2024, 8, 1), 24) == date(2026, 8, 1)


def test_recem_chegado_esta_em_dia_na_fase_de_entrada():
    s = calcular(aluno(2), PROG, CAT, HOJE)
    assert s.em_dia and not s.atrasado and s.fase == Fase.ENTRADA
    assert "Sem plano de trabalho" in s.pendencias


def test_atrasado_quando_passa_do_prazo():
    s = calcular(aluno(25, qualificacao=aprovada(date(2025, 6, 1))), PROG, CAT, HOJE)
    assert s.atrasado and not s.em_dia and s.dias_para_prazo < 0


def test_prorrogacao_estende_o_prazo():
    d = aluno(25, qualificacao=aprovada(date(2025, 6, 1)),
              prorrogacoes=[Prorrogacao(meses=6, motivo="m", concedida_em=HOJE)])
    s = calcular(d, PROG, CAT, HOJE)
    assert not s.atrasado and s.em_dia and s.meses_prorrogados == 6


def test_qualificacao_atrasada_depois_do_prazo_de_qualificar():
    s = calcular(aluno(13), PROG, CAT, HOJE)
    assert s.qualificacao_atrasada and not s.em_dia and not s.atrasado


def test_qualificacao_agendada_nao_conta_como_qualificado():
    d = aluno(13, qualificacao=Avaliacao(data=HOJE, titulo="T", resultado="agendada"))
    assert not calcular(d, PROG, CAT, HOJE).qualificado


def test_prazo_proximo():
    s = calcular(aluno(22, qualificacao=aprovada(date(2025, 12, 1))), PROG, CAT, HOJE)
    assert s.prazo_proximo and s.em_dia


def test_titulado_tempo_e_no_prazo():
    ing = soma_meses(HOJE, -30)
    d = aluno(30, qualificacao=aprovada(soma_meses(ing, 12)), defesa=aprovada(soma_meses(ing, 23)))
    s = calcular(d, PROG, CAT, HOJE)
    assert s.vinculo == Vinculo.TITULADO and s.fase == Fase.TITULADO
    assert 22.5 < s.tempo_titulacao_meses < 23.5 and s.titulou_no_prazo
    assert not s.atrasado and not s.em_dia and s.pendencias == []


def test_titulado_fora_do_prazo():
    ing = soma_meses(HOJE, -40)
    d = aluno(40, qualificacao=aprovada(soma_meses(ing, 12)), defesa=aprovada(soma_meses(ing, 27)))
    assert calcular(d, PROG, CAT, HOJE).titulou_no_prazo is False


def test_desligado_sai_dos_contadores_de_atraso():
    d = aluno(40, desligamento=Desligamento(data=soma_meses(HOJE, -20), motivo="m"))
    s = calcular(d, PROG, CAT, HOJE)
    assert s.vinculo == Vinculo.DESLIGADO and not s.atrasado and not s.qualificacao_atrasada


def test_doutorado_usa_prazos_proprios():
    s = calcular(aluno(30, nivel="doutorado"), PROG, CAT, HOJE)
    assert not s.atrasado and not s.qualificacao_atrasada  # qualifica até 30 meses
    s = calcular(aluno(31, nivel="doutorado"), PROG, CAT, HOJE)
    assert s.qualificacao_atrasada


def test_disciplinas_planejadas_vs_cursadas():
    d = aluno(10, plano=PlanoTrabalho(titulo_projeto="P", disciplinas_planejadas=["a", "b"]),
              disciplinas=[
                  DisciplinaCursada(disciplina_id="a", semestre="2026/1", situacao="aprovado"),
                  DisciplinaCursada(disciplina_id="c", semestre="2026/1", situacao="aproveitada"),
                  DisciplinaCursada(disciplina_id="b", semestre="2026/2", situacao="cursando"),
              ])
    r = calcular(d, PROG, CAT, HOJE).disciplinas
    assert r.planejadas == 2 and r.cumpridas_do_plano == 1
    assert r.pendentes_do_plano == ["b"] and r.fora_do_plano == ["c"]
    assert r.creditos_concluidos == 6 and r.cursando == 1
