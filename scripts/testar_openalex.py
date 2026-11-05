#!/usr/bin/env python3
"""Testa se o Percurso encontra um(a) professor(a) no OpenAlex. Não grava nada.

  python scripts/testar_openalex.py "Silvio Ereno Quincozes"
  python scripts/testar_openalex.py "Silvio Ereno Quincozes" --orcid 0000-0001-6793-4033

Mostra os candidatos com nome parecido, qual deles a coleta escolheria,
e um resumo da produção (obras, tipos, h-index) como o Percurso calcularia.
Use OPENALEX_API_KEY (gratuita em openalex.org/settings/api); sem ela há só
uma pequena cota diária de demonstração.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from percurso.dominio.metricas import h5_index, h_index, i10_index  # noqa: E402
from percurso.dominio.modelos import Docente, cauda_id  # noqa: E402
from percurso.servicos.openalex import OpenAlexCliente, tipo_da_obra  # noqa: E402
from percurso.servicos.producoes import normaliza_nome  # noqa: E402
from percurso.servicos.repo import RegraViolada  # noqa: E402


def inst(a: dict) -> str:
    ult = a.get("last_known_institutions") or []
    if ult:
        return ult[0].get("display_name") or "—"
    afs = a.get("affiliations") or []
    return (afs[0].get("institution") or {}).get("display_name", "—") if afs else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("nome")
    ap.add_argument("--orcid")
    ap.add_argument("--paginas", type=int, default=2, help="páginas de 200 obras (cada uma gasta 1 crédito)")
    a = ap.parse_args()

    key = os.getenv("OPENALEX_API_KEY")
    if not key:
        print("Aviso: sem OPENALEX_API_KEY — usando a cota de demonstração do OpenAlex.\n")
    cli = OpenAlexCliente(os.getenv("OPENALEX_MAILTO"), api_key=key)

    try:
        print(f"Candidatos para \"{a.nome}\":")
        cands = cli.candidatos(a.nome)
        if not cands:
            print("  nenhum. Tente o nome como aparece nos artigos (ex.: com sobrenome do meio).")
        alvo = normaliza_nome(a.nome)
        for i, c in enumerate(cands[:8], 1):
            igual = "  ← nome idêntico" if normaliza_nome(c.get("display_name") or "") == alvo else ""
            print(f"  {i}. {c.get('display_name')} ({cauda_id(c.get('id'))}) · {c.get('works_count')} obras · "
                  f"{c.get('cited_by_count')} citações · ORCID {cauda_id(c.get('orcid')) or '—'} · {inst(c)}{igual}")
        if len(cands) > 1 and not a.orcid:
            print("  Atenção: há mais de um candidato. Sem ORCID, a coleta escolhe o mais citado (o nº 1).")

        autor = cli.autor(Docente(id="teste", nome=a.nome, orcid=a.orcid))
        if not autor:
            print("\nNão encontrado.")
            return 1
        via = "ORCID" if a.orcid and cauda_id(autor.get("orcid")) == cauda_id(a.orcid) else "nome (mais citado)"
        print(f"\nEscolhido (por {via}): {autor.get('display_name')} — {autor.get('id')}")
        print(f"  ORCID no OpenAlex: {cauda_id(autor.get('orcid')) or 'não vinculado'} · instituição: {inst(autor)}")
        if a.orcid and cauda_id(autor.get("orcid")) != cauda_id(a.orcid):
            print("  ⚠ O ORCID informado não está vinculado a nenhum perfil; caiu na busca por nome.")

        obras = cli.obras(cauda_id(autor.get("id")) or "", max_paginas=a.paginas)
        tipos = Counter((t.value if (t := tipo_da_obra(w)) else "ignorada") for w in obras)
        # Mesmas obras que a coleta guardaria (teses, erratas etc. ficam de fora das métricas).
        uteis = [w for w in obras if tipo_da_obra(w)]
        cits = [w.get("cited_by_count") or 0 for w in uteis]
        ano = date.today().year
        print(f"\nObras lidas: {len(obras)} (o perfil informa {autor.get('works_count')})")
        print("  Tipos no Percurso: " + ", ".join(f"{k}: {v}" for k, v in tipos.most_common()))
        h5 = h5_index(((w.get("publication_year"), w.get("cited_by_count")) for w in uteis), ano)
        print(f"  h-index {h_index(cits)} · h5 {h5} · i10 {i10_index(cits)} · {sum(cits)} citações")
        print("\nMais recentes:")
        for w in sorted(obras, key=lambda w: w.get("publication_date") or "", reverse=True)[:8]:
            print(f"  {w.get('publication_year')} · {w.get('display_name')}")
    except RegraViolada as e:
        print(f"\nErro: {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
