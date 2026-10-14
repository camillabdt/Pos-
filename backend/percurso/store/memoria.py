from __future__ import annotations

import copy
import uuid

from percurso.store.base import Doc


class MemoriaStore:
    """Armazenamento em memória. Os dados somem ao reiniciar o servidor."""

    def __init__(self) -> None:
        self._dados: dict[str, dict[str, Doc]] = {}

    def get(self, colecao: str, id: str) -> Doc | None:
        doc = self._dados.get(colecao, {}).get(id)
        return copy.deepcopy(doc) if doc is not None else None

    def listar(self, colecao: str) -> list[Doc]:
        return [copy.deepcopy(d) for d in self._dados.get(colecao, {}).values()]

    def salvar(self, colecao: str, id: str, dados: Doc) -> None:
        self._dados.setdefault(colecao, {})[id] = copy.deepcopy({**dados, "id": id})

    def apagar(self, colecao: str, id: str) -> bool:
        return self._dados.get(colecao, {}).pop(id, None) is not None

    def novo_id(self, colecao: str) -> str:
        return uuid.uuid4().hex[:12]
