from __future__ import annotations

from fastapi import Request

from percurso.servicos.percurso import PercursoServico
from percurso.servicos.producoes import ProducoesServico
from percurso.servicos.repo import Repo


def repo(request: Request) -> Repo:
    return request.app.state.repo


def percurso(request: Request) -> PercursoServico:
    return PercursoServico(request.app.state.repo, hoje=getattr(request.app.state, "hoje", None))


def producoes(request: Request) -> ProducoesServico:
    return ProducoesServico(request.app.state.repo)
