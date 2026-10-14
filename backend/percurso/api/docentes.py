"""Docentes e produção docente (coleta OpenAlex herdada do Poshboard)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from percurso.api import deps
from percurso.auth import Usuario, equipe, so_coordenacao
from percurso.dominio.modelos import Docente, DocenteAtualizar, DocenteCriar
from percurso.servicos.openalex import ColetaServico, OpenAlexCliente, ResultadoColeta
from percurso.servicos.percurso import DiscenteResumo, PercursoServico
from percurso.servicos.producoes import ProducoesServico, ResumoProducao
from percurso.servicos.repo import Repo

router = APIRouter(prefix="/docentes", tags=["Docentes"])


class DocenteDetalhe(Docente):
    orientandos: list[DiscenteResumo]
    producao: ResumoProducao


def _pode_editar(u: Usuario, id: str) -> None:
    if not (u.coordenacao or u.docente_id == id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você só pode alterar o seu próprio cadastro.")


@router.get("", response_model=list[Docente])
def listar(u: Usuario = Depends(equipe), r: Repo = Depends(deps.repo)):
    return sorted(r.docentes.listar(), key=lambda d: d.nome.lower())


@router.post("", response_model=Docente, status_code=201)
def criar(dados: DocenteCriar, u: Usuario = Depends(so_coordenacao), r: Repo = Depends(deps.repo)):
    return r.docentes.criar(dados)


@router.get("/{id}", response_model=DocenteDetalhe)
def obter(id: str, u: Usuario = Depends(equipe), s: PercursoServico = Depends(deps.percurso),
          p: ProducoesServico = Depends(deps.producoes)):
    d = s.repo.docentes.obter(id)
    return DocenteDetalhe(
        **d.model_dump(),
        orientandos=s.listar(orientador_id=id),
        producao=p.resumir(p.listar(docente_id=id)),
    )


@router.patch("/{id}", response_model=Docente)
def atualizar(id: str, dados: DocenteAtualizar, u: Usuario = Depends(equipe), r: Repo = Depends(deps.repo)):
    _pode_editar(u, id)
    if not u.coordenacao and dados.model_dump(exclude_unset=True).keys() & {"tipo", "ativo"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tipo de vínculo e situação são definidos pela coordenação.")
    return r.docentes.atualizar(id, dados)


@router.delete("/{id}", status_code=204)
def apagar(id: str, u: Usuario = Depends(so_coordenacao), r: Repo = Depends(deps.repo)):
    if any(d.orientador_id == id or id in d.coorientador_ids for d in r.discentes.listar()):
        raise HTTPException(422, "Docente com orientandos não pode ser removido(a). Marque como inativo(a).")
    r.docentes.apagar(id)


@router.post("/{id}/coletar", response_model=ResultadoColeta)
def coletar(id: str, request: Request, u: Usuario = Depends(equipe), r: Repo = Depends(deps.repo)):
    _pode_editar(u, id)
    cliente = getattr(request.app.state, "openalex", None) or OpenAlexCliente(request.app.state.config.openalex_mailto)
    return ColetaServico(r, cliente, hoje=getattr(request.app.state, "hoje", None)).coletar(id)


class ColetaGeral(BaseModel):
    resultados: list[ResultadoColeta]
    erros: dict[str, str]


@router.post("/coletar-todos", response_model=ColetaGeral)
def coletar_todos(request: Request, u: Usuario = Depends(so_coordenacao), r: Repo = Depends(deps.repo)):
    cliente = getattr(request.app.state, "openalex", None) or OpenAlexCliente(request.app.state.config.openalex_mailto)
    servico = ColetaServico(r, cliente, hoje=getattr(request.app.state, "hoje", None))
    resultados, erros = [], {}
    for d in r.docentes.listar():
        if not d.ativo:
            continue
        try:
            resultados.append(servico.coletar(d.id))
        except Exception as exc:  # um docente com problema não para a coleta dos outros
            erros[d.nome] = str(exc)
    return ColetaGeral(resultados=resultados, erros=erros)
