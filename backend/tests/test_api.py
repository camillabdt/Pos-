from __future__ import annotations

from tests.conftest import como


def nomes(resp):
    return {x["nome"] for x in resp.json()}


def test_painel_responde_as_perguntas_da_coordenacao(cliente):
    p = cliente.get("/painel").json()
    t = p["totais"]
    assert t["ativos"] == t["em_dia"] + len({
        x["id"] for f in ("atrasados", "qualificacao_atrasada")
        for x in cliente.get("/discentes", params={"filtro": f}).json()
    })
    assert t["atrasados"] == 2 and t["titulados"] == 3 and t["desligados"] == 1
    assert {"Larissa Nunes", "Júlia Fernandes", "Henrique Castro"} == nomes(
        cliente.get("/discentes", params={"filtro": "qualificacao_atrasada"}))


def test_filtro_invalido_explica_opcoes(cliente):
    r = cliente.get("/discentes", params={"filtro": "xyz"})
    assert r.status_code == 422 and "atrasados" in r.json()["detail"]


def test_percurso_completo_entrada_meio_fim(cliente):
    novo = cliente.post("/discentes", json={
        "nome": "Nova Pessoa", "matricula": "2025X1", "data_ingresso": "2024-08-01",
        "orientador_id": "ana", "nivel": "mestrado",
    })
    assert novo.status_code == 201, novo.text
    id = novo.json()["id"]
    assert novo.json()["situacao"]["fase"] == "entrada"

    r = cliente.put(f"/discentes/{id}/plano", json={"titulo_projeto": "Projeto", "disciplinas_planejadas": ["metod", "eswe"]})
    assert r.json()["situacao"]["fase"] == "cursando"
    assert r.json()["situacao"]["disciplinas"]["pendentes_do_plano"] == ["metod", "eswe"]

    for disc in ("metod", "eswe"):
        r = cliente.put(f"/discentes/{id}/disciplinas", json={"disciplina_id": disc, "semestre": "2024/2", "situacao": "aprovado"})
    assert r.json()["situacao"]["disciplinas"]["pendentes_do_plano"] == []

    r = cliente.put(f"/discentes/{id}/qualificacao", json={
        "data": "2025-07-10", "titulo": "Título da qualificação", "resultado": "aprovado",
        "banca": [{"nome": "Ana Ribeiro", "papel": "presidente", "docente_id": "ana"},
                  {"nome": "Externa", "instituicao": "UFSM", "papel": "externo"}],
    })
    assert r.json()["situacao"]["qualificado"] is True

    r = cliente.put(f"/discentes/{id}/defesa", json={
        "data": "2026-07-20", "titulo": "Título final", "resultado": "aprovado",
        "banca": [{"nome": "Ana Ribeiro", "papel": "presidente", "docente_id": "ana"}],
    })
    corpo = r.json()
    assert corpo["situacao"]["vinculo"] == "titulado"
    assert corpo["tema"] == "Título final"
    assert 23 < corpo["situacao"]["tempo_titulacao_meses"] < 24
    assert corpo["situacao"]["titulou_no_prazo"] is True


def test_defesa_aprovada_exige_qualificacao(cliente):
    r = cliente.put("/discentes/julia/defesa", json={"data": "2026-10-01", "titulo": "T", "resultado": "aprovado"})
    assert r.status_code == 422 and "qualificação" in r.json()["detail"]


def test_defesa_pode_ser_agendada_antes(cliente):
    r = cliente.put("/discentes/camila/defesa", json={"data": "2026-11-20", "titulo": "T", "resultado": "agendada"})
    assert r.status_code == 200 and r.json()["situacao"]["fase"] == "defesa_agendada"
    assert r.json()["situacao"]["atrasado"] is True  # agendar não tira do atraso


def test_validacoes_de_entrada(cliente):
    base = {"nome": "X", "matricula": "M1", "data_ingresso": "2026-03-01"}
    assert cliente.post("/discentes", json={**base, "orientador_id": "ninguem"}).status_code == 422
    r = cliente.post("/discentes", json={**base, "orientador_id": "ana", "plano": {"titulo_projeto": "P", "disciplinas_planejadas": ["nao-existe"]}})
    assert r.status_code == 422
    cliente.post("/discentes", json={**base, "orientador_id": "ana"})
    assert cliente.post("/discentes", json={**base, "orientador_id": "ana"}).status_code == 422  # matrícula repetida
    r = cliente.put("/discentes/lucas/disciplinas", json={"disciplina_id": "metod", "semestre": "2026-1"})
    assert r.status_code == 422


def test_prorrogacao_tira_do_atraso(cliente):
    assert cliente.get("/discentes/camila").json()["situacao"]["atrasado"] is True
    r = cliente.post("/discentes/camila/prorrogacoes", json={"meses": 6, "motivo": "Coleta de dados", "concedida_em": "2026-10-01"})
    assert r.json()["situacao"]["atrasado"] is False


def test_permissoes(cliente):
    como(cliente, "discente", "rafael")
    assert cliente.get("/discentes/rafael").status_code == 200
    assert cliente.get("/discentes/julia").status_code == 403
    assert cliente.get("/painel").status_code == 403
    assert cliente.get("/discentes").status_code == 403
    assert all(any(a.get("discente_id") == "rafael" for a in p["autores"]) for p in cliente.get("/producoes").json())
    assert cliente.put("/discentes/rafael/defesa", json={"data": "2026-11-01", "titulo": "T"}).status_code == 403

    como(cliente, "docente", "ana")
    assert cliente.get("/painel").status_code == 200
    assert cliente.put("/discentes/rafael/defesa", json={"data": "2026-11-01", "titulo": "T"}).status_code == 200
    assert cliente.put("/discentes/pedro/defesa", json={"data": "2026-11-01", "titulo": "T"}).status_code == 403
    assert cliente.patch("/discentes/rafael", json={"tema": "Novo tema"}).status_code == 200
    assert cliente.patch("/discentes/rafael", json={"orientador_id": "bruno"}).status_code == 403
    assert cliente.post("/discentes/rafael/prorrogacoes", json={"meses": 3, "motivo": "m", "concedida_em": "2026-10-01"}).status_code == 403
    assert cliente.patch("/docentes/bruno", json={"lattes": "x"}).status_code == 403
    assert cliente.patch("/docentes/ana", json={"lattes": "http://lattes.cnpq.br/1"}).status_code == 200


def test_producoes_tecnicas_e_coautoria(cliente):
    r = cliente.post("/producoes", json={
        "tipo": "startup", "titulo": "Minha Startup", "ano": 2026,
        "autores": [{"nome": "Pedro Henrique Silva", "discente_id": "pedro"}, {"nome": "Carla Menezes", "docente_id": "carla"}],
        "detalhes": {"cnpj": "11.111.111/0001-11"},
    })
    assert r.status_code == 201
    assert any(p["titulo"] == "Minha Startup" for p in cliente.get("/producoes", params={"discente_id": "pedro"}).json())
    assert any(p["titulo"] == "Minha Startup" for p in cliente.get("/producoes", params={"docente_id": "carla"}).json())


def test_qualis_herdado_pelo_issn_e_doi_unico(cliente):
    r = cliente.post("/producoes", json={
        "tipo": "artigo_periodico", "titulo": "Artigo", "ano": 2026, "doi": "https://doi.org/10.1/ABC",
        "autores": [{"nome": "Ana Ribeiro", "docente_id": "ana"}],
        "veiculo": {"issn": ["01641212"]},
    })
    assert r.status_code == 201
    assert r.json()["veiculo"]["qualis"] == "A1" and r.json()["doi"] == "10.1/abc"
    r = cliente.post("/producoes", json={
        "tipo": "artigo_periodico", "titulo": "Duplicado", "ano": 2026, "doi": "10.1/abc",
        "autores": [{"nome": "Ana Ribeiro", "docente_id": "ana"}],
    })
    assert r.status_code == 422


def test_discente_so_registra_producao_propria(cliente):
    como(cliente, "discente", "marina")
    corpo = {"tipo": "participacao_evento", "titulo": "Evento", "ano": 2026}
    assert cliente.post("/producoes", json={**corpo, "autores": [{"nome": "Outra", "discente_id": "julia"}]}).status_code == 403
    assert cliente.post("/producoes", json={**corpo, "autores": [{"nome": "Marina Costa", "discente_id": "marina"}]}).status_code == 201


def test_disciplina_em_uso_nao_pode_ser_apagada(cliente):
    assert cliente.delete("/disciplinas/metod").status_code == 422
    nova = cliente.post("/disciplinas", json={"codigo": "X1", "nome": "Nova", "creditos": 2}).json()
    assert cliente.delete(f"/disciplinas/{nova['id']}").status_code == 204


def test_prazos_configuraveis(cliente):
    prog = cliente.get("/programa").json()
    prog["mestrado"]["conclusao_meses"] = 30
    assert cliente.put("/programa", json=prog).status_code == 200
    assert cliente.get("/painel").json()["totais"]["atrasados"] == 0


def test_nome_do_autor_do_programa_e_preenchido(cliente):
    como(cliente, "discente", "marina")
    r = cliente.post("/producoes", json={"tipo": "software", "titulo": "App", "ano": 2026, "autores": [{"discente_id": "marina"}]})
    assert r.status_code == 201 and r.json()["autores"][0]["nome"] == "Marina Costa"
    r = cliente.post("/producoes", json={"tipo": "software", "titulo": "App", "ano": 2026,
                                         "autores": [{"discente_id": "marina"}, {"nome": " "}]})
    assert r.status_code == 422
