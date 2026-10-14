"""Autenticação e regras de permissão.

Papéis (custom claims do Firebase Auth):
  { "papel": "coordenacao" | "docente" | "discente",
    "docente_id": "...",   # para docentes (e coordenação que orienta)
    "discente_id": "..." } # para discentes

Em PERCURSO_AUTH=dev, o papel vem dos cabeçalhos X-Dev-Papel / X-Dev-Id.
NUNCA use o modo dev em produção.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from percurso.dominio.modelos import Discente, Papel, Producao


class Usuario(BaseModel):
    uid: str
    papel: Papel
    docente_id: str | None = None
    discente_id: str | None = None

    @property
    def coordenacao(self) -> bool:
        return self.papel == Papel.COORDENACAO

    def orienta(self, d: Discente) -> bool:
        return bool(self.docente_id) and (
            d.orientador_id == self.docente_id or self.docente_id in d.coorientador_ids
        )

    def pode_ver_discente(self, d: Discente) -> bool:
        if self.papel == Papel.DISCENTE:
            return d.id == self.discente_id
        return True

    def pode_editar_percurso(self, d: Discente) -> bool:
        """Plano, disciplinas, qualificação, tema, defesa: coordenação ou orientação."""
        return self.coordenacao or self.orienta(d)

    def pode_editar_producao(self, p: Producao | None, autores_ids: set[str]) -> bool:
        if self.coordenacao:
            return True
        meus = {self.docente_id, self.discente_id} - {None}
        return bool(meus & autores_ids)


def _erro(codigo: int, msg: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=msg)


async def usuario_atual(
    request: Request,
    authorization: str | None = Header(default=None),
    x_dev_papel: str | None = Header(default=None),
    x_dev_id: str | None = Header(default=None),
) -> Usuario:
    modo = request.app.state.config.auth
    if modo == "dev":
        papel = Papel(x_dev_papel or "coordenacao")
        return Usuario(
            uid=f"dev-{papel}",
            papel=papel,
            docente_id=x_dev_id if papel in (Papel.DOCENTE, Papel.COORDENACAO) else None,
            discente_id=x_dev_id if papel == Papel.DISCENTE else None,
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise _erro(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        from firebase_admin import auth as fb_auth

        dados = fb_auth.verify_id_token(token)
    except Exception as exc:  # token inválido, expirado, etc.
        raise _erro(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada. Entre novamente.") from exc
    try:
        papel = Papel(dados.get("papel"))
    except ValueError as exc:
        raise _erro(status.HTTP_403_FORBIDDEN, "Conta sem papel definido. Peça acesso à coordenação.") from exc
    return Usuario(
        uid=dados["uid"],
        papel=papel,
        docente_id=dados.get("docente_id"),
        discente_id=dados.get("discente_id"),
    )


def exige(*papeis: Papel):
    async def _dep(u: Usuario = Depends(usuario_atual)) -> Usuario:
        if u.papel not in papeis:
            raise _erro(status.HTTP_403_FORBIDDEN, "Seu papel não tem acesso a esta área.")
        return u

    return _dep


so_coordenacao = exige(Papel.COORDENACAO)
equipe = exige(Papel.COORDENACAO, Papel.DOCENTE)
