"""Conversão dos dados do SAGA (Firestore) e do Poshboard (Realtime Database).

As funções `de_saga` e `de_poshboard` recebem os dados brutos já lidos
(dicts) e devolvem objetos do Percurso + uma lista de avisos para revisão
manual. A leitura das fontes fica em `scripts/importar.py`.

O que NÃO é importado de propósito:
- Produções docentes do Poshboard: rode a coleta do OpenAlex no Percurso,
  que já deduplica por DOI e vincula coautores discentes.
- Pontuação Qualis/RL05, créditos por grupo e checklist do SAGA: o Percurso
  calcula a situação a partir dos fatos, não guarda situação.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from percurso.dominio.modelos import (
    Autor,
    Avaliacao,
    Desligamento,
    Discente,
    Disciplina,
    DisciplinaCursada,
    Docente,
    Linha,
    PlanoTrabalho,
    Producao,
    Programa,
    Prorrogacao,
    Resultado,
    TipoDocente,
    TipoProducao,
    Veiculo,
    VeiculoRef,
    normaliza_doi,
)
from percurso.dominio.situacao import meses_entre, soma_meses
from percurso.servicos.producoes import normaliza_nome

SEM_TITULO = "(título não registrado na origem — completar)"


@dataclass
class Lote:
    docentes: list[Docente] = field(default_factory=list)
    discentes: list[Discente] = field(default_factory=list)
    disciplinas: list[Disciplina] = field(default_factory=list)
    linhas: list[Linha] = field(default_factory=list)
    veiculos: list[Veiculo] = field(default_factory=list)
    producoes: list[Producao] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def resumo(self) -> str:
        return (f"{len(self.docentes)} docentes, {len(self.discentes)} discentes, "
                f"{len(self.disciplinas)} disciplinas, {len(self.linhas)} linhas, "
                f"{len(self.veiculos)} veículos, {len(self.producoes)} produções, "
                f"{len(self.avisos)} avisos")


def _data(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if hasattr(v, "isoformat"):  # Timestamp do Firestore
        return date.fromisoformat(v.isoformat()[:10])
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normaliza_nome(texto)).strip("-")[:40] or "item"


# --------------------------------------------------------------------------- SAGA

TIPO_SAGA = {"artigo": TipoProducao.ARTIGO_PERIODICO, "livro": TipoProducao.LIVRO,
             "capitulo": TipoProducao.CAPITULO}


def de_saga(
    advisors: dict[str, dict],
    students: dict[str, dict],
    work_plans: dict[str, dict] | None = None,       # student_id -> doc do plano
    activities: dict[str, list[dict]] | None = None,  # student_id -> atividades
    productions: dict[str, dict] | None = None,
    vehicles: dict[str, dict] | None = None,
    programa: Programa | None = None,
) -> Lote:
    lote = Lote()
    programa = programa or Programa()
    work_plans, activities = work_plans or {}, activities or {}
    productions, vehicles = productions or {}, vehicles or {}

    for id, a in advisors.items():
        lote.docentes.append(Docente(id=id, nome=a.get("nome") or "?", email=a.get("email"),
                                     lattes=a.get("lattes"), tipo=TipoDocente.PERMANENTE))
    docentes_ids = {d.id for d in lote.docentes}

    catalogo: dict[str, Disciplina] = {}
    uid_para_id: dict[str, str] = {}
    for id, s in students.items():
        nome = s.get("nome") or "?"
        ingresso = _data(s.get("data_ingresso"))
        if not ingresso or s.get("orientador_id") not in docentes_ids:
            lote.avisos.append(
                f"Discente '{nome}' ({id}) sem data de ingresso ou orientador válido — não importado."
            )
            continue
        uid_para_id[s.get("uid") or id] = id
        nivel = s.get("nivel") or "mestrado"
        d = Discente(
            id=id, nome=nome, email=s.get("email"), matricula=s.get("matricula") or id, nivel=nivel,
            data_ingresso=ingresso, orientador_id=s["orientador_id"],
            coorientador_ids=[c for c in [s.get("coorientador_id")] if c in docentes_ids],
        )

        plano = work_plans.get(id)
        if plano and plano.get("titulo"):
            d.plano = PlanoTrabalho(titulo_projeto=plano["titulo"], resumo=plano.get("descricao"))

        # Prorrogações: diferença entre o prazo final do SAGA e o prazo regular.
        prazo_saga = _data(s.get("prazo_final"))
        regular = soma_meses(ingresso, programa.prazos(d.nivel).conclusao_meses)
        if prazo_saga and prazo_saga > regular:
            meses = max(1, round(meses_entre(regular, prazo_saga)))
            d.prorrogacoes.append(Prorrogacao(meses=min(meses, 24), motivo="Importada do SAGA", concedida_em=regular))

        data_q = _data(s.get("qualificacao_data"))
        if s.get("qualificacao_aprovada"):
            if data_q:
                d.qualificacao = Avaliacao(data=data_q, titulo=SEM_TITULO, resultado=Resultado.APROVADO)
            else:
                lote.avisos.append(f"{nome}: qualificação aprovada no SAGA sem data — registrar manualmente.")

        situacao = s.get("situacao_registrada")
        if situacao == "concluido":
            fim = _data(s.get("data_conclusao")) or _data(s.get("atualizado_em"))
            if fim:
                d.defesa = Avaliacao(data=fim, titulo=SEM_TITULO, resultado=Resultado.APROVADO)
            lote.avisos.append(f"{nome}: concluído no SAGA — completar título e banca da defesa.")
        elif situacao == "desligado":
            d.desligamento = Desligamento(data=_data(s.get("atualizado_em")) or date.today(), motivo="Importado do SAGA")

        # Disciplinas cursadas viram itens do catálogo (o SAGA guardava em texto livre).
        for atv in activities.get(id, []):
            nome_tipo = (atv.get("tipo_nome") or atv.get("tipo_id") or "").lower()
            if "disciplina" not in nome_tipo or atv.get("status") != "aprovado":
                continue
            descricao = (atv.get("descricao") or "Disciplina").strip()
            chave = _slug(descricao)
            if chave not in catalogo:
                catalogo[chave] = Disciplina(id=chave, codigo=f"SAGA-{len(catalogo) + 1:03d}", nome=descricao,
                                             creditos=int(atv.get("creditos_concedidos") or atv.get("creditos_gerados") or 0))
            quando = _data(atv.get("data_realizacao")) or ingresso
            d.disciplinas.append(DisciplinaCursada(
                disciplina_id=chave, semestre=f"{quando.year}/{1 if quando.month <= 6 else 2}", situacao="aprovado"))
        lote.discentes.append(d)

    if catalogo:
        lote.disciplinas = list(catalogo.values())
        lote.avisos.append(
            f"{len(catalogo)} disciplinas criadas a partir de texto livre do SAGA — revise nomes, códigos e créditos."
        )

    for id, v in vehicles.items():
        lote.veiculos.append(Veiculo(id=id, nome=v.get("nome") or "?", issn=[v["issn"]] if v.get("issn") else [],
                                     qualis=v.get("nivel") or v.get("qualis")))
    veic = {v.id: v for v in lote.veiculos}
    nomes = {d.id: d.nome for d in lote.discentes}

    for id, p in productions.items():
        autores: list[Autor] = []
        for a in p.get("autores") or []:
            sid = uid_para_id.get(a) or (a if a in nomes else None)
            autores.append(Autor(nome=nomes[sid], discente_id=sid) if sid else Autor(nome=str(a)))
        if not any(a.discente_id for a in autores):
            sid = uid_para_id.get(p.get("aluno_id")) or p.get("aluno_id")
            if sid in nomes:
                autores.insert(0, Autor(nome=nomes[sid], discente_id=sid))
        quando = _data(p.get("data_realizacao"))
        if not autores or not quando or not p.get("titulo"):
            lote.avisos.append(f"Produção '{p.get('titulo', id)}' sem autores, data ou título — não importada.")
            continue
        v = veic.get(p.get("veiculo_id"))
        lote.producoes.append(Producao(
            id=id, tipo=TIPO_SAGA.get(p.get("tipo_producao"), TipoProducao.OUTRO), titulo=p["titulo"],
            ano=quando.year, data=quando, autores=autores, doi=normaliza_doi(p.get("doi")),
            veiculo=VeiculoRef(nome=v.nome, issn=v.issn, qualis=v.qualis) if v else None,
            detalhes={"situacao_publicacao": p["status_publicacao"]} if p.get("status_publicacao") else {},
        ))
    return lote


# --------------------------------------------------------------------- Poshboard

def de_poshboard(rtdb: dict[str, Any]) -> Lote:
    """`rtdb` = o JSON exportado do Realtime Database (nós linhas, docentes, discentes, pesquisas, veiculos)."""
    lote = Lote()
    no = lambda nome: {k: v for k, v in (rtdb.get(nome) or {}).items() if isinstance(v, dict)}  # noqa: E731

    for id, ln in no("linhas").items():
        lote.linhas.append(Linha(id=id, nome=ln.get("nome") or id, descricao=ln.get("descricao")))
    linhas = {x.id for x in lote.linhas}

    for id, d in no("docentes").items():
        tipo = (d.get("tipo") or "PERMANENTE").lower()
        lote.docentes.append(Docente(
            id=id, nome=d.get("nome") or d.get("name") or "?", email=d.get("email"),
            tipo=tipo if tipo in TipoDocente.__members__.values() else TipoDocente.PERMANENTE,
            linha_id=d.get("linha_id") if d.get("linha_id") in linhas else None,
            lattes=d.get("lattes"), orcid=d.get("orcid"), openalex_id=d.get("openalex_id"),
        ))
    docentes = {x.id for x in lote.docentes}

    pesquisas_por_discente: dict[str, dict] = {}
    for p in no("pesquisas").values():
        if p.get("discente_id"):
            pesquisas_por_discente[p["discente_id"]] = p

    for id, d in no("discentes").items():
        nome = d.get("nome") or "?"
        pq = pesquisas_por_discente.get(id, {})
        orientador = pq.get("orientador_id") or d.get("orientador_id")
        ingresso = _data(d.get("data_ingresso")) or _data(pq.get("data_inicio"))
        if orientador not in docentes or not ingresso:
            lote.avisos.append(f"Discente '{nome}' ({id}) sem orientador ou data de ingresso — não importado.")
            continue
        disc = Discente(
            id=id, nome=nome, email=d.get("email"), matricula=d.get("matricula") or id,
            nivel="doutorado" if (d.get("nivel") or "").lower().startswith("dout") else "mestrado",
            data_ingresso=ingresso, orientador_id=orientador,
            coorientador_ids=[c for c in (pq.get("coorientadores") or {}) if c in docentes],
            linha_id=pq.get("linha_id") if pq.get("linha_id") in linhas else None,
            tema=pq.get("titulo"),
        )
        if pq.get("titulo"):
            disc.plano = PlanoTrabalho(titulo_projeto=pq["titulo"])
        status = pq.get("status")
        if status in ("QUALIFICADA", "DEFENDIDA"):
            lote.avisos.append(f"{nome}: qualificou no Poshboard, mas sem data — registrar a qualificação.")
        if status == "DEFENDIDA":
            fim = _data(pq.get("data_fim"))
            if fim:
                disc.defesa = Avaliacao(data=fim, titulo=pq.get("titulo") or SEM_TITULO, resultado=Resultado.APROVADO)
            else:
                lote.avisos.append(f"{nome}: defendeu no Poshboard, mas sem data — registrar a defesa.")
        elif status == "ARQUIVADA":
            disc.desligamento = Desligamento(
                data=_data(pq.get("data_fim")) or date.today(), motivo="Pesquisa arquivada (Poshboard)"
            )
        lote.discentes.append(disc)

    for id, v in no("veiculos").items():
        lote.veiculos.append(Veiculo(id=id, nome=v.get("nome") or v.get("titulo") or "?",
                                     issn=[v["issn"]] if v.get("issn") else [], qualis=v.get("qualis") or v.get("estrato")))
    if no("produtos"):
        lote.avisos.append("Produtos do Poshboard não foram copiados: rode 'Coletar do OpenAlex' para os docentes.")
    return lote


def gravar(lote: Lote, repo) -> None:
    for nome in ("linhas", "docentes", "disciplinas", "veiculos", "discentes", "producoes"):
        col = getattr(repo, nome)
        for obj in getattr(lote, nome):
            col.salvar(obj)
