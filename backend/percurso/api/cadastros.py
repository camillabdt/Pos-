"""Cadastros de apoio: programa (prazos), disciplinas, linhas de pesquisa e veículos."""


from fastapi import APIRouter, Depends, HTTPException

from percurso.api import deps
from percurso.auth import Usuario, so_coordenacao, usuario_atual
from percurso.dominio.modelos import (
    Disciplina,
    DisciplinaCriar,
    Linha,
    LinhaCriar,
    Programa,
    Veiculo,
    VeiculoCriar,
)
from percurso.servicos.repo import Repo

router = APIRouter(tags=["Cadastros"])


@router.get("/programa", response_model=Programa)
def programa(u: Usuario = Depends(usuario_atual), r: Repo = Depends(deps.repo)):
    return r.programa()


@router.put("/programa", response_model=Programa)
def salvar_programa(p: Programa, u: Usuario = Depends(so_coordenacao), r: Repo = Depends(deps.repo)):
    return r.salvar_programa(p)


def _crud(prefixo: str, colecao: str, Criar, Modelo, ordem, em_uso):
    @router.get(f"/{prefixo}", response_model=list[Modelo], name=f"listar_{prefixo}")
    def listar(u: Usuario = Depends(usuario_atual), r: Repo = Depends(deps.repo)):
        return sorted(getattr(r, colecao).listar(), key=ordem)

    @router.post(f"/{prefixo}", response_model=Modelo, status_code=201, name=f"criar_{prefixo}")
    def criar(dados: Criar, u: Usuario = Depends(so_coordenacao), r: Repo = Depends(deps.repo)):
        return getattr(r, colecao).criar(dados)

    @router.put(f"/{prefixo}/{{id}}", response_model=Modelo, name=f"atualizar_{prefixo}")
    def atualizar(id: str, dados: Criar, u: Usuario = Depends(so_coordenacao), r: Repo = Depends(deps.repo)):
        getattr(r, colecao).obter(id)
        return getattr(r, colecao).salvar(Modelo(**dados.model_dump(), id=id))

    @router.delete(f"/{prefixo}/{{id}}", status_code=204, name=f"apagar_{prefixo}")
    def apagar(id: str, u: Usuario = Depends(so_coordenacao), r: Repo = Depends(deps.repo)):
        if em_uso(r, id):
            raise HTTPException(422, "Este item está em uso e não pode ser removido.")
        getattr(r, colecao).apagar(id)


def _disciplina_em_uso(r: Repo, id: str) -> bool:
    return any(
        id in (d.plano.disciplinas_planejadas if d.plano else []) or any(c.disciplina_id == id for c in d.disciplinas)
        for d in r.discentes.listar()
    )


def _linha_em_uso(r: Repo, id: str) -> bool:
    return any(x.linha_id == id for x in [*r.discentes.listar(), *r.docentes.listar()])


_crud("disciplinas", "disciplinas", DisciplinaCriar, Disciplina, lambda d: d.codigo, _disciplina_em_uso)
_crud("linhas", "linhas", LinhaCriar, Linha, lambda x: x.nome.lower(), _linha_em_uso)
_crud("veiculos", "veiculos", VeiculoCriar, Veiculo, lambda v: v.nome.lower(), lambda r, id: False)
