from __future__ import annotations

from datetime import date

import httpx

from percurso.exemplo import carregar
from percurso.servicos.openalex import ColetaServico, OpenAlexCliente
from percurso.servicos.repo import Repo
from percurso.store.memoria import MemoriaStore

AUTOR = {"id": "https://openalex.org/A999", "display_name": "Ana Ribeiro",
         "orcid": "https://orcid.org/0000-0001-2345-6789", "works_count": 3, "cited_by_count": 50}


def obra(n, tipo="article", fonte="journal", doi=None, cit=10, ano=2025, coautores=()):
    return {
        "id": f"https://openalex.org/W{n}", "display_name": f"Obra {n}", "type": tipo,
        "publication_year": ano, "publication_date": f"{ano}-05-01", "doi": doi, "cited_by_count": cit,
        "primary_location": {"source": {"display_name": "Journal of Systems and Software", "type": fonte, "issn": ["0164-1212"]}},
        "authorships": [{"author": {"id": "https://openalex.org/A999", "display_name": "Ana Ribeiro"}}]
                       + [{"author": {"display_name": c}} for c in coautores],
    }


def transporte(obras):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/authors" or req.url.path.startswith("/authors/"):
            if req.url.path.startswith("/authors/"):
                return httpx.Response(200, json=AUTOR)
            return httpx.Response(200, json={"results": [AUTOR]})
        if req.url.path == "/works":
            return httpx.Response(200, json={"results": obras, "meta": {"next_cursor": None}})
        return httpx.Response(404, json={})
    return httpx.MockTransport(handler)


def test_coleta_cria_deduplica_e_vincula_coautores():
    repo = Repo(MemoriaStore())
    carregar(repo, hoje=date(2026, 10, 13))
    antes = len(repo.producoes.listar())
    obras = [
        obra(1, coautores=["Rafael Moura"]),                       # discente do programa
        obra(2, tipo="article", fonte="conference", cit=3),
        obra(3, doi="https://doi.org/10.1016/j.jss.2026.000001", cit=7),  # já existe (p1, manual)
        obra(4, tipo="dissertation"),                              # ignorada
    ]
    cliente = OpenAlexCliente(http=httpx.Client(transport=transporte(obras)), pausa_s=0)
    r = ColetaServico(repo, cliente, hoje=date(2026, 10, 13)).coletar("ana")

    assert (r.novas, r.atualizadas, r.ignoradas) == (2, 1, 1)
    assert len(repo.producoes.listar()) == antes + 2
    docente = repo.docentes.obter("ana")
    assert docente.openalex_id == "A999" and docente.orcid == "0000-0001-2345-6789"
    assert docente.metricas.coletado_em == date(2026, 10, 13)

    p1 = repo.producoes.obter("p1")
    assert p1.openalex_id == "W3" and p1.citacoes == 7 and p1.origem == "manual"

    nova = next(p for p in repo.producoes.listar() if p.openalex_id == "W1")
    assert nova.veiculo.qualis == "A1"  # herdado do cadastro pelo ISSN
    assert any(a.discente_id == "rafael" for a in nova.autores)
    assert next(p for p in repo.producoes.listar() if p.openalex_id == "W2").tipo == "artigo_evento"

    # Segunda coleta não duplica nada.
    r2 = ColetaServico(repo, cliente, hoje=date(2026, 10, 13)).coletar("ana")
    assert r2.novas == 0 and len(repo.producoes.listar()) == antes + 2


def test_coleta_via_api(cliente, app):
    app.state.openalex = OpenAlexCliente(http=httpx.Client(transport=transporte([obra(9)])), pausa_s=0)
    r = cliente.post("/docentes/bruno/coletar")
    assert r.status_code == 200 and r.json()["novas"] == 1


def test_orcid_usa_consulta_direta_e_envia_chave():
    vistos = []

    def handler(req: httpx.Request) -> httpx.Response:
        vistos.append(req.url)
        if req.url.path == "/authors/orcid:0000-0001-2345-6789":
            return httpx.Response(200, json=AUTOR)
        return httpx.Response(404, json={})

    cli = OpenAlexCliente(http=httpx.Client(transport=httpx.MockTransport(handler)), pausa_s=0, api_key="k123")
    from percurso.dominio.modelos import Docente
    a = cli.autor(Docente(id="x", nome="Qualquer", orcid="https://orcid.org/0000-0001-2345-6789"))
    assert a["display_name"] == "Ana Ribeiro"
    assert vistos[0].params["api_key"] == "k123" and len(vistos) == 1  # não caiu na busca por nome


def test_sem_chave_explica_o_que_fazer():
    import pytest

    from percurso.servicos.repo import RegraViolada

    cli = OpenAlexCliente(http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(409, json={}))), pausa_s=0)
    with pytest.raises(RegraViolada, match="OPENALEX_API_KEY"):
        cli.candidatos("Fulano")


def test_candidatos_via_api_nao_grava_e_marca_orcid(cliente, app):
    outro = {**AUTOR, "id": "https://openalex.org/A111", "display_name": "Ana Ribeiro", "orcid": None, "cited_by_count": 3}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/authors/orcid:0000-0001-2345-6789":
            return httpx.Response(200, json=AUTOR)
        if req.url.path == "/authors":
            return httpx.Response(200, json={"results": [outro, AUTOR]})
        return httpx.Response(404, json={})

    app.state.openalex = OpenAlexCliente(http=httpx.Client(transport=httpx.MockTransport(handler)), pausa_s=0)
    antes = len(cliente.get("/producoes").json())
    r = cliente.get("/docentes/openalex/candidatos", params={"nome": "Ana Ribeiro", "orcid": "0000-0001-2345-6789"})
    assert r.status_code == 200, r.text
    c = r.json()
    assert [x["openalex_id"] for x in c] == ["A999", "A111"]  # o do ORCID primeiro, sem repetir
    assert c[0]["achado_por_orcid"] and c[1]["nome_identico"]
    assert len(cliente.get("/producoes").json()) == antes
    assert cliente.get("/docentes/openalex/candidatos").status_code == 422
