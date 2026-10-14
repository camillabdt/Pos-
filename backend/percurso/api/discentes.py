"""Discentes e o percurso: entrada, meio e fim."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from percurso.api import deps
from percurso.auth import Usuario, equipe, so_coordenacao, usuario_atual
from percurso.dominio.modelos import (
    Avaliacao,
    Desligamento,
    Discente,
    DiscenteAtualizar,
    DiscenteCriar,
    DisciplinaCursada,
    PlanoTrabalho,
    Prorrogacao,
)
from percurso.dominio.situacao import FILTROS
from percurso.servicos.percurso import DiscenteDetalhe, DiscenteResumo, PercursoServico

router = APIRouter(prefix="/discentes", tags=["Discentes"])

FiltroQuery = Query(default=None, description=f"Um de: {', '.join(FILTROS)}")


def _carrega(id: str, u: Usuario, s: PercursoServico) -> Discente:
    d = s.repo.discentes.obter(id)
    if not u.pode_ver_discente(d):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você só pode ver o seu próprio percurso.")
    return d


def _editavel(id: str, u: Usuario, s: PercursoServico) -> Discente:
    d = _carrega(id, u, s)
    if not u.pode_editar_percurso(d):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só a coordenação ou a orientação podem alterar este percurso.")
    return d


@router.get("", response_model=list[DiscenteResumo])
def listar(
    filtro: str | None = FiltroQuery,
    orientador_id: str | None = None,
    busca: str | None = None,
    u: Usuario = Depends(equipe),
    s: PercursoServico = Depends(deps.percurso),
):
    return s.listar(filtro=filtro, orientador_id=orientador_id, busca=busca)


@router.post("", response_model=DiscenteDetalhe, status_code=201)
def criar(dados: DiscenteCriar, u: Usuario = Depends(so_coordenacao),
          s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.criar(dados))


@router.get("/{id}", response_model=DiscenteDetalhe)
def obter(id: str, u: Usuario = Depends(usuario_atual), s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(_carrega(id, u, s))


@router.patch("/{id}", response_model=DiscenteDetalhe)
def atualizar(id: str, dados: DiscenteAtualizar, u: Usuario = Depends(usuario_atual),
              s: PercursoServico = Depends(deps.percurso)):
    d = _editavel(id, u, s)
    mexe_em_vinculo = dados.model_dump(exclude_unset=True).keys() - {"tema"}
    if mexe_em_vinculo and not u.coordenacao:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A orientação só pode alterar o tema; o restante é com a coordenação.")
    return s.detalhe(s.atualizar(d.id, dados))


@router.delete("/{id}", status_code=204)
def apagar(id: str, u: Usuario = Depends(so_coordenacao), s: PercursoServico = Depends(deps.percurso)):
    s.repo.discentes.apagar(id)


# --- Entrada ---------------------------------------------------------------

@router.put("/{id}/plano", response_model=DiscenteDetalhe)
def definir_plano(id: str, plano: PlanoTrabalho, u: Usuario = Depends(usuario_atual),
                  s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.definir_plano(_editavel(id, u, s), plano))


# --- Meio ------------------------------------------------------------------

@router.put("/{id}/disciplinas", response_model=DiscenteDetalhe)
def registrar_disciplina(id: str, item: DisciplinaCursada, u: Usuario = Depends(usuario_atual),
                         s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.registrar_disciplina(_editavel(id, u, s), item))


@router.delete("/{id}/disciplinas/{disciplina_id}", response_model=DiscenteDetalhe)
def remover_disciplina(id: str, disciplina_id: str, semestre: str, u: Usuario = Depends(usuario_atual),
                       s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.remover_disciplina(_editavel(id, u, s), disciplina_id, semestre))


@router.put("/{id}/qualificacao", response_model=DiscenteDetalhe)
def registrar_qualificacao(id: str, q: Avaliacao, u: Usuario = Depends(usuario_atual),
                           s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.registrar_qualificacao(_editavel(id, u, s), q))


@router.post("/{id}/prorrogacoes", response_model=DiscenteDetalhe)
def conceder_prorrogacao(id: str, p: Prorrogacao, u: Usuario = Depends(so_coordenacao),
                         s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.conceder_prorrogacao(s.repo.discentes.obter(id), p))


@router.delete("/{id}/prorrogacoes/{indice}", response_model=DiscenteDetalhe)
def remover_prorrogacao(id: str, indice: int, u: Usuario = Depends(so_coordenacao),
                        s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.remover_prorrogacao(s.repo.discentes.obter(id), indice))


# --- Fim -------------------------------------------------------------------

@router.put("/{id}/defesa", response_model=DiscenteDetalhe)
def registrar_defesa(id: str, defesa: Avaliacao, u: Usuario = Depends(usuario_atual),
                     s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.registrar_defesa(_editavel(id, u, s), defesa))


@router.put("/{id}/desligamento", response_model=DiscenteDetalhe)
def desligar(id: str, des: Desligamento, u: Usuario = Depends(so_coordenacao),
             s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.desligar(s.repo.discentes.obter(id), des))


@router.delete("/{id}/desligamento", response_model=DiscenteDetalhe)
def desfazer_desligamento(id: str, u: Usuario = Depends(so_coordenacao),
                          s: PercursoServico = Depends(deps.percurso)):
    return s.detalhe(s.desligar(s.repo.discentes.obter(id), None))
