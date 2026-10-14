from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from percurso.config import Config
from percurso.exemplo import carregar
from percurso.main import criar_app
from percurso.servicos.repo import Repo
from percurso.store.memoria import MemoriaStore

HOJE = date(2026, 10, 13)


@pytest.fixture
def store():
    return MemoriaStore()


@pytest.fixture
def app(store):
    app = criar_app(Config(armazenamento="memoria", auth="dev"), store=store)
    app.state.hoje = HOJE
    carregar(Repo(store), hoje=HOJE)
    return app


@pytest.fixture
def cliente(app):
    return TestClient(app)


def como(cliente: TestClient, papel: str, id: str | None = None) -> TestClient:
    cliente.headers.update({"X-Dev-Papel": papel, **({"X-Dev-Id": id} if id else {})})
    return cliente
