"""Interface mínima de armazenamento de documentos.

Duas implementações: `MemoriaStore` (desenvolvimento e testes, sem credenciais)
e `FirestoreStore` (produção). Os serviços só conhecem esta interface.
Documentos são dicts JSON-serializáveis (datas como 'AAAA-MM-DD').
"""

from __future__ import annotations

from typing import Any, Protocol

Doc = dict[str, Any]


class Store(Protocol):
    def get(self, colecao: str, id: str) -> Doc | None: ...
    def listar(self, colecao: str) -> list[Doc]: ...
    def salvar(self, colecao: str, id: str, dados: Doc) -> None: ...
    def apagar(self, colecao: str, id: str) -> bool: ...
    def novo_id(self, colecao: str) -> str: ...
