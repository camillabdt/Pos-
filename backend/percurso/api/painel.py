from __future__ import annotations

from fastapi import APIRouter, Depends

from percurso.api import deps
from percurso.auth import Usuario, equipe
from percurso.servicos.painel import Painel, montar_painel
from percurso.servicos.percurso import PercursoServico

router = APIRouter(tags=["Painel"])


@router.get("/painel", response_model=Painel)
def painel(u: Usuario = Depends(equipe), s: PercursoServico = Depends(deps.percurso)):
    return montar_painel(s)
