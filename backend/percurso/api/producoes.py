"""Produções de discentes e docentes (artigos, software, registros, eventos, startups...)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from percurso.api import deps
from percurso.auth import Usuario, usuario_atual
from percurso.dominio.modelos import Papel, Producao, ProducaoCriar
from percurso.servicos.producoes import ProducoesServico, ResumoProducao, ids_autores

router = APIRouter(prefix="/producoes", tags=["Produções"])


@router.get("", response_model=list[Producao])
def listar(
    discente_id: str | None = None,
    docente_id: str | None = None,
    tipo: str | None = None,
    ano_de: int | None = None,
    ano_ate: int | None = None,
    so_com_discentes: bool = False,
    busca: str | None = None,
    u: Usuario = Depends(usuario_atual),
    s: ProducoesServico = Depends(deps.producoes),
):
    if u.papel == Papel.DISCENTE:
        discente_id = u.discente_id  # discente vê só as próprias
    return s.listar(discente_id, docente_id, tipo, ano_de, ano_ate, so_com_discentes, busca)


@router.get("/resumo", response_model=ResumoProducao)
def resumo(
    discente_id: str | None = None,
    docente_id: str | None = None,
    ano_de: int | None = None,
    ano_ate: int | None = None,
    u: Usuario = Depends(usuario_atual),
    s: ProducoesServico = Depends(deps.producoes),
):
    if u.papel == Papel.DISCENTE:
        discente_id = u.discente_id
    return s.resumir(s.listar(discente_id, docente_id, None, ano_de, ano_ate))


@router.post("", response_model=Producao, status_code=201)
def criar(dados: ProducaoCriar, u: Usuario = Depends(usuario_atual),
          s: ProducoesServico = Depends(deps.producoes)):
    if not u.pode_editar_producao(None, ids_autores(dados)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inclua você mesmo(a) entre os autores para registrar a produção.")
    return s.criar(dados)


def _editavel(id: str, u: Usuario, s: ProducoesServico) -> Producao:
    p = s.repo.producoes.obter(id)
    if not u.pode_editar_producao(p, ids_autores(p)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só autores do programa ou a coordenação podem alterar esta produção.")
    return p


@router.put("/{id}", response_model=Producao)
def atualizar(id: str, dados: ProducaoCriar, u: Usuario = Depends(usuario_atual),
              s: ProducoesServico = Depends(deps.producoes)):
    _editavel(id, u, s)
    return s.atualizar(id, dados)


@router.delete("/{id}", status_code=204)
def apagar(id: str, u: Usuario = Depends(usuario_atual), s: ProducoesServico = Depends(deps.producoes)):
    _editavel(id, u, s)
    s.repo.producoes.apagar(id)
