#!/usr/bin/env python3
"""Dá um papel a uma conta do Firebase Auth (custom claims).

  python scripts/definir_papel.py silvio@unipampa.edu.br coordenacao --docente-id silvio
  python scripts/definir_papel.py ana@unipampa.edu.br docente --docente-id ana
  python scripts/definir_papel.py aluno@unipampa.edu.br discente --discente-id lucas

A pessoa precisa sair e entrar de novo para o papel valer.
"""

from __future__ import annotations

import argparse

import firebase_admin
from firebase_admin import auth


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("email")
    ap.add_argument("papel", choices=["coordenacao", "docente", "discente"])
    ap.add_argument("--docente-id", help="id do cadastro de docente (coordenação que orienta também usa)")
    ap.add_argument("--discente-id", help="id do cadastro de discente")
    a = ap.parse_args()
    if a.papel == "docente" and not a.docente_id:
        ap.error("docente precisa de --docente-id")
    if a.papel == "discente" and not a.discente_id:
        ap.error("discente precisa de --discente-id")

    firebase_admin.initialize_app()
    try:
        u = auth.get_user_by_email(a.email)
    except auth.UserNotFoundError:
        u = auth.create_user(email=a.email)
        print(f"Conta criada para {a.email}. Envie um link de redefinição de senha pelo console do Firebase.")
    claims = {"papel": a.papel}
    if a.docente_id:
        claims["docente_id"] = a.docente_id
    if a.discente_id:
        claims["discente_id"] = a.discente_id
    auth.set_custom_user_claims(u.uid, claims)
    print(f"{a.email}: {claims}")


if __name__ == "__main__":
    main()
