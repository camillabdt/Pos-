from datetime import date

from percurso.importacao import de_poshboard, de_saga


def test_saga_converte_percurso_e_avisa_lacunas():
    lote = de_saga(
        advisors={"adv1": {"nome": "Ana"}},
        students={
            "s1": {"uid": "u1", "nome": "Rafa", "matricula": "1", "orientador_id": "adv1", "nivel": "mestrado",
                   "data_ingresso": "2024-03-01", "prazo_final": "2026-09-01",
                   "qualificacao_aprovada": True, "qualificacao_data": "2025-03-10",
                   "situacao_registrada": "concluido", "data_conclusao": "2026-08-20"},
            "s2": {"nome": "Sem orientador", "data_ingresso": "2024-03-01", "orientador_id": "x"},
        },
        work_plans={"s1": {"titulo": "Plano do Rafa"}},
        activities={"s1": [{"tipo_nome": "Disciplina Cursada", "status": "aprovado", "descricao": "Metodologia",
                            "creditos_concedidos": 4, "data_realizacao": "2024-05-01"}]},
        productions={"p1": {"titulo": "Artigo", "tipo_producao": "artigo", "autores": ["u1", "Externo"],
                            "data_realizacao": "2025-06-01", "veiculo_id": "v1", "doi": "https://doi.org/10.1/X"}},
        vehicles={"v1": {"nome": "Revista", "nivel": "A2"}},
    )
    assert len(lote.discentes) == 1 and any("Sem orientador" in a for a in lote.avisos)
    d = lote.discentes[0]
    assert d.plano.titulo_projeto == "Plano do Rafa"
    assert d.prorrogacoes and d.prorrogacoes[0].meses == 6
    assert d.qualificacao.data == date(2025, 3, 10) and d.defesa.data == date(2026, 8, 20)
    assert d.disciplinas[0].semestre == "2024/1" and lote.disciplinas[0].creditos == 4
    p = lote.producoes[0]
    assert p.autores[0].discente_id == "s1" and p.veiculo.qualis == "A2" and p.doi == "10.1/x"


def test_poshboard_usa_pesquisa_como_fonte_de_orientacao():
    lote = de_poshboard({
        "linhas": {"l1": {"nome": "IA"}},
        "docentes": {"d1": {"nome": "Bruno", "tipo": "COLABORADOR", "orcid": "https://orcid.org/0000-0002"}},
        "discentes": {"x1": {"nome": "Maria"}, "x2": {"nome": "Sem pesquisa"}},
        "pesquisas": {"p": {"discente_id": "x1", "orientador_id": "d1", "titulo": "Tema", "status": "DEFENDIDA",
                            "data_inicio": "2023-03-01", "data_fim": "2025-02-20", "linha_id": "l1"}},
        "produtos": {"a": {"titulo": "algo"}},
    })
    assert lote.docentes[0].tipo == "colaborador" and lote.docentes[0].orcid == "0000-0002"
    assert len(lote.discentes) == 1
    m = lote.discentes[0]
    assert m.tema == "Tema" and m.defesa.data == date(2025, 2, 20) and m.linha_id == "l1"
    assert any("OpenAlex" in a for a in lote.avisos)
