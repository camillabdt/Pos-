"""Coleta da produção docente no OpenAlex (portado e simplificado do Poshboard).

Diferenças em relação ao Poshboard:
- grava direto como `Producao` (sem camada "raw" separada), deduplicando por
  id do OpenAlex e por DOI — produções já cadastradas à mão só ganham o vínculo;
- usa `primary_location.source` (o `host_venue` foi descontinuado pelo OpenAlex);
- reconhece coautores que são docentes ou discentes do programa
  (por ORCID / id OpenAlex, ou pelo nome normalizado);
- herda o Qualis do cadastro de veículos pelo ISSN.
"""

from __future__ import annotations

import time
from datetime import date

import httpx
from pydantic import BaseModel

from percurso.dominio.modelos import (
    Autor,
    Docente,
    Metricas,
    Producao,
    TipoProducao,
    VeiculoRef,
    cauda_id,
    normaliza_doi,
)
from percurso.servicos.producoes import ProducoesServico, normaliza_nome
from percurso.servicos.repo import RegraViolada, Repo

BASE = "https://api.openalex.org"
TIPOS_IGNORADOS = {"dissertation", "paratext", "erratum", "retraction", "peer-review", "editorial", "letter"}


class ResultadoColeta(BaseModel):
    docente_id: str
    autor_openalex: str
    nome_openalex: str | None
    obras_lidas: int
    novas: int
    atualizadas: int
    ignoradas: int
    metricas: Metricas


class OpenAlexCliente:
    def __init__(self, mailto: str | None = None, http: httpx.Client | None = None,
                 pausa_s: float = 0.15) -> None:
        self.mailto = mailto
        self.http = http or httpx.Client(timeout=30, headers={
            "User-Agent": f"percurso/1.0 (mailto:{mailto})" if mailto else "percurso/1.0",
            "Accept": "application/json",
        })
        self.pausa_s = pausa_s

    def _get(self, caminho: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        if self.mailto:
            params.setdefault("mailto", self.mailto)
        r = self.http.get(f"{BASE}{caminho}", params=params)
        if r.status_code == 404:
            return {}
        if r.status_code >= 400:
            raise RegraViolada(f"OpenAlex respondeu {r.status_code}. Tente de novo em alguns minutos.")
        return r.json()

    def autor(self, docente: Docente) -> dict | None:
        if docente.openalex_id:
            return self._get(f"/authors/{docente.openalex_id}") or None
        if docente.orcid:
            res = self._get("/authors", {"filter": f"orcid:{docente.orcid}"}).get("results", [])
            if res:
                return res[0]
        res = self._get("/authors", {"search": docente.nome, "per_page": 10}).get("results", [])
        if not res:
            return None
        # Mesma heurística do Poshboard: o candidato mais citado / com mais obras.
        return max(res, key=lambda a: (a.get("cited_by_count") or 0, a.get("works_count") or 0))

    def obras(self, autor_id: str, max_paginas: int = 5) -> list[dict]:
        obras, cursor, paginas = [], "*", 0
        while cursor and paginas < max_paginas:
            pagina = self._get("/works", {
                "filter": f"author.id:{autor_id}", "per_page": 200, "cursor": cursor,
            })
            obras.extend(pagina.get("results", []))
            cursor = (pagina.get("meta") or {}).get("next_cursor")
            paginas += 1
            if cursor and self.pausa_s:
                time.sleep(self.pausa_s)
        return obras


def tipo_da_obra(w: dict) -> TipoProducao | None:
    t = (w.get("type") or "").lower()
    if t in TIPOS_IGNORADOS:
        return None
    if t == "book":
        return TipoProducao.LIVRO
    if t == "book-chapter":
        return TipoProducao.CAPITULO
    fonte = ((w.get("primary_location") or {}).get("source") or {})
    tipo_fonte = (fonte.get("type") or "").lower()
    if t in ("article", "review", "proceedings-article"):
        if tipo_fonte == "conference" or t == "proceedings-article":
            return TipoProducao.ARTIGO_EVENTO
        if tipo_fonte == "journal":
            return TipoProducao.ARTIGO_PERIODICO
    return TipoProducao.OUTRO


class ColetaServico:
    def __init__(self, repo: Repo, cliente: OpenAlexCliente, hoje: date | None = None) -> None:
        self.repo = repo
        self.cliente = cliente
        self.producoes = ProducoesServico(repo)
        self.hoje = hoje or date.today()

    def _indices_pessoas(self):
        docentes = self.repo.docentes.listar()
        discentes = self.repo.discentes.listar()
        por_oa = {d.openalex_id: d.id for d in docentes if d.openalex_id}
        por_orcid = {d.orcid: d.id for d in docentes if d.orcid}
        doc_nome = {normaliza_nome(d.nome): d.id for d in docentes}
        dis_nome = {normaliza_nome(d.nome): d.id for d in discentes}
        return por_oa, por_orcid, doc_nome, dis_nome

    def _autores(self, w: dict, indices) -> list[Autor]:
        por_oa, por_orcid, doc_nome, dis_nome = indices
        autores = []
        for a in w.get("authorships") or []:
            info = a.get("author") or {}
            nome = info.get("display_name") or a.get("raw_author_name") or "?"
            oa, orcid, chave = cauda_id(info.get("id")), cauda_id(info.get("orcid")), normaliza_nome(nome)
            docente_id = por_oa.get(oa) or por_orcid.get(orcid) or doc_nome.get(chave)
            discente_id = None if docente_id else dis_nome.get(chave)
            autores.append(Autor(nome=nome, docente_id=docente_id, discente_id=discente_id))
        return autores

    def coletar(self, docente_id: str, max_paginas: int = 5) -> ResultadoColeta:
        docente = self.repo.docentes.obter(docente_id)
        autor = self.cliente.autor(docente)
        if not autor:
            raise RegraViolada(
                "Não encontrei esse(a) docente no OpenAlex. Informe o ORCID ou o id OpenAlex no cadastro."
            )
        autor_id = cauda_id(autor.get("id")) or ""
        if not docente.openalex_id:
            # Fixa o autor encontrado para as próximas coletas não dependerem do nome.
            docente.openalex_id = autor_id
            docente.orcid = docente.orcid or cauda_id(autor.get("orcid"))

        indices = self._indices_pessoas()
        indices[0].setdefault(autor_id, docente.id)
        existentes = self.repo.producoes.listar()
        por_oa = {p.openalex_id: p for p in existentes if p.openalex_id}
        por_doi = {p.doi: p for p in existentes if p.doi}

        obras = self.cliente.obras(autor_id, max_paginas)
        novas = atualizadas = ignoradas = 0
        for w in obras:
            tipo = tipo_da_obra(w)
            titulo = w.get("display_name") or w.get("title")
            ano = w.get("publication_year")
            if not tipo or not titulo or not ano:
                ignoradas += 1
                continue
            oa_id = cauda_id(w.get("id"))
            doi = normaliza_doi(w.get("doi"))
            autores = self._autores(w, indices)
            if not any(a.docente_id == docente.id for a in autores):
                autores.append(Autor(nome=docente.nome, docente_id=docente.id))

            atual = por_oa.get(oa_id) or (por_doi.get(doi) if doi else None)
            if atual:
                atual.openalex_id = atual.openalex_id or oa_id
                atual.citacoes = w.get("cited_by_count")
                ja = {(a.docente_id, a.discente_id) for a in atual.autores}
                # Mantém os autores cadastrados à mão; só acrescenta vínculos novos.
                for a in autores:
                    if (a.docente_id or a.discente_id) and (a.docente_id, a.discente_id) not in ja:
                        atual.autores.append(a)
                self.repo.producoes.salvar(atual)
                atualizadas += 1
                continue

            fonte = (w.get("primary_location") or {}).get("source") or {}
            veiculo = self.producoes.completar_qualis(VeiculoRef(
                nome=fonte.get("display_name"), issn=fonte.get("issn") or [],
            )) if fonte else None
            data_pub = w.get("publication_date")
            nova = Producao(
                id=self.repo.store.novo_id("producoes"),
                tipo=tipo, titulo=titulo, ano=ano,
                data=date.fromisoformat(data_pub) if data_pub else None,
                autores=autores, doi=doi, veiculo=veiculo,
                origem="openalex", openalex_id=oa_id, citacoes=w.get("cited_by_count"),
            )
            self.repo.producoes.salvar(nova)
            por_oa[oa_id] = nova
            if doi:
                por_doi[doi] = nova
            novas += 1

        m = self.producoes.metricas_docente(docente.id, self.hoje.year)
        docente.metricas = Metricas(
            **m, total_obras=autor.get("works_count") or len(obras), coletado_em=self.hoje,
        )
        self.repo.docentes.salvar(docente)
        return ResultadoColeta(
            docente_id=docente.id, autor_openalex=autor_id, nome_openalex=autor.get("display_name"),
            obras_lidas=len(obras), novas=novas, atualizadas=atualizadas, ignoradas=ignoradas,
            metricas=docente.metricas,
        )
