#!/usr/bin/env python3
"""Coleta a produção de todos os docentes ativos no OpenAlex.

Pensado para rodar agendado (Cloud Scheduler -> Cloud Run Job, ou cron),
como o job de harvest do Poshboard. Usa o Firestore do Percurso.

  FIREBASE_PROJECT_ID=percurso-ppg OPENALEX_MAILTO=voce@unipampa.edu.br \
    python scripts/coletar_docentes.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from percurso.servicos.openalex import ColetaServico, OpenAlexCliente  # noqa: E402
from percurso.servicos.repo import Repo  # noqa: E402
from percurso.store.firestore import FirestoreStore  # noqa: E402


def main() -> int:
    repo = Repo(FirestoreStore(os.getenv("FIREBASE_PROJECT_ID")))
    servico = ColetaServico(repo, OpenAlexCliente(os.getenv("OPENALEX_MAILTO")))
    falhas = 0
    for d in repo.docentes.listar():
        if not d.ativo:
            continue
        try:
            r = servico.coletar(d.id)
            print(f"{d.nome}: {r.novas} novas, {r.atualizadas} atualizadas, h={r.metricas.h_index}")
        except Exception as exc:
            falhas += 1
            print(f"{d.nome}: FALHOU — {exc}", file=sys.stderr)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
