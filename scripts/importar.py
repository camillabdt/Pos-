#!/usr/bin/env python3
"""Importa dados do SAGA (Firestore) ou do Poshboard (RTDB) para o Percurso.

Sempre rode primeiro com --simular: mostra o que seria importado e os avisos,
sem gravar nada.

  # SAGA: lê o Firestore do projeto do SAGA
  GOOGLE_APPLICATION_CREDENTIALS=~/chaves/saga.json \
    python scripts/importar.py saga --projeto-origem saga-xyz --simular

  # Poshboard: use o JSON exportado do RTDB (Console > Realtime Database > Exportar JSON)
  python scripts/importar.py poshboard --arquivo poshbard-export.json --simular

  # Gravação de verdade no Firestore do Percurso
  FIREBASE_PROJECT_ID=percurso-ppg python scripts/importar.py poshboard --arquivo export.json

As chaves ficam FORA do repositório.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from percurso.importacao import de_poshboard, de_saga, gravar  # noqa: E402


def ler_saga(projeto: str):
    import firebase_admin
    from firebase_admin import credentials, firestore

    app = firebase_admin.initialize_app(credentials.ApplicationDefault(), {"projectId": projeto}, name="saga")
    db = firestore.client(app)

    def col(nome):
        return {s.id: s.to_dict() for s in db.collection(nome).stream()}

    students = col("students")
    planos, atividades = {}, {}
    for sid in students:
        ref = db.collection("students").document(sid)
        planos_docs = list(ref.collection("work_plan").limit(1).stream())
        if planos_docs:
            planos[sid] = planos_docs[0].to_dict()
        atividades[sid] = [a.to_dict() for a in ref.collection("activities").stream()]
    return de_saga(col("advisors"), students, planos, atividades, col("productions"), col("vehicles"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origem", choices=["saga", "poshboard"])
    ap.add_argument("--projeto-origem", help="project id do Firebase do SAGA")
    ap.add_argument("--arquivo", help="JSON exportado do RTDB do Poshboard")
    ap.add_argument("--simular", action="store_true", help="não grava, só mostra o resultado")
    args = ap.parse_args()

    if args.origem == "saga":
        if not args.projeto_origem:
            ap.error("informe --projeto-origem")
        lote = ler_saga(args.projeto_origem)
    else:
        if not args.arquivo:
            ap.error("informe --arquivo")
        lote = de_poshboard(json.loads(Path(args.arquivo).read_text(encoding="utf-8")))

    print("Encontrado:", lote.resumo())
    for a in lote.avisos:
        print("  aviso:", a)
    if args.simular:
        print("\nSimulação: nada foi gravado.")
        return

    from percurso.servicos.repo import Repo
    from percurso.store.firestore import FirestoreStore

    gravar(lote, Repo(FirestoreStore(os.getenv("FIREBASE_PROJECT_ID"))))
    print("\nGravado no Firestore do Percurso.")


if __name__ == "__main__":
    main()
