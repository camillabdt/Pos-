"""Acesso tipado às coleções. Converte entre modelos Pydantic e documentos."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from percurso.dominio.modelos import (
    Discente,
    Disciplina,
    Docente,
    Linha,
    Producao,
    Programa,
    Veiculo,
)
from percurso.store.base import Store

T = TypeVar("T", bound=BaseModel)


class NaoEncontrado(Exception):
    def __init__(self, oque: str, id: str) -> None:
        super().__init__(f"{oque} '{id}' não encontrado(a).")


class RegraViolada(Exception):
    """Operação válida no formato mas que fere uma regra do programa (HTTP 422)."""


class Colecao(Generic[T]):
    def __init__(self, store: Store, nome: str, modelo: type[T], rotulo: str) -> None:
        self._store, self.nome, self._modelo, self._rotulo = store, nome, modelo, rotulo

    def get(self, id: str | None) -> T | None:
        if not id:
            return None
        doc = self._store.get(self.nome, id)
        return self._modelo.model_validate(doc) if doc else None

    def obter(self, id: str) -> T:
        obj = self.get(id)
        if obj is None:
            raise NaoEncontrado(self._rotulo, id)
        return obj

    def existe(self, id: str | None) -> bool:
        return bool(id) and self._store.get(self.nome, id) is not None

    def listar(self) -> list[T]:
        return [self._modelo.model_validate(d) for d in self._store.listar(self.nome)]

    def por_id(self) -> dict[str, T]:
        return {o.id: o for o in self.listar()}  # type: ignore[attr-defined]

    def criar(self, dados: BaseModel, id: str | None = None, **extra) -> T:
        id = id or self._store.novo_id(self.nome)
        obj = self._modelo.model_validate({**dados.model_dump(), **extra, "id": id})
        self.salvar(obj)
        return obj

    def salvar(self, obj: T) -> T:
        self._store.salvar(self.nome, obj.id, obj.model_dump(mode="json"))  # type: ignore[attr-defined]
        return obj

    def atualizar(self, id: str, mudancas: BaseModel) -> T:
        atual = self.obter(id)
        novos = mudancas.model_dump(exclude_unset=True)
        obj = self._modelo.model_validate({**atual.model_dump(), **novos})
        return self.salvar(obj)

    def apagar(self, id: str) -> None:
        if not self._store.apagar(self.nome, id):
            raise NaoEncontrado(self._rotulo, id)


class Repo:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.discentes = Colecao(store, "discentes", Discente, "Discente")
        self.docentes = Colecao(store, "docentes", Docente, "Docente")
        self.disciplinas = Colecao(store, "disciplinas", Disciplina, "Disciplina")
        self.linhas = Colecao(store, "linhas", Linha, "Linha de pesquisa")
        self.veiculos = Colecao(store, "veiculos", Veiculo, "Veículo")
        self.producoes = Colecao(store, "producoes", Producao, "Produção")

    def programa(self) -> Programa:
        doc = self.store.get("config", "programa")
        return Programa.model_validate({k: v for k, v in doc.items() if k != "id"}) if doc else Programa()

    def salvar_programa(self, p: Programa) -> Programa:
        self.store.salvar("config", "programa", p.model_dump(mode="json"))
        return p
