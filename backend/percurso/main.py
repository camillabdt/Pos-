"""Percurso — acompanhamento do percurso discente e da produção do PPG."""

from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from percurso.api import cadastros, discentes, docentes, painel, producoes
from percurso.auth import Usuario, usuario_atual
from percurso.config import Config
from percurso.servicos.repo import NaoEncontrado, RegraViolada, Repo
from percurso.store.base import Store


def _store(config: Config) -> Store:
    if config.armazenamento == "firestore":
        from percurso.store.firestore import FirestoreStore

        return FirestoreStore(config.firebase_project_id)
    from percurso.store.memoria import MemoriaStore

    return MemoriaStore()


def criar_app(config: Config | None = None, store: Store | None = None) -> FastAPI:
    config = config or Config()
    app = FastAPI(title="Percurso", version="1.0.0",
                  description="Percurso discente (entrada, meio, fim) e produção do programa.")
    app.state.config = config
    app.state.repo = Repo(store or _store(config))

    if store is None and config.armazenamento == "memoria" and config.carregar_exemplo:
        from percurso.exemplo import carregar

        carregar(app.state.repo)

    app.add_middleware(CORSMiddleware, allow_origins=list(config.cors_origens),
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(NaoEncontrado)
    async def _404(_: Request, exc: NaoEncontrado):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(RegraViolada)
    async def _422(_: Request, exc: RegraViolada):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/saude", tags=["Sistema"])
    def saude():
        return {"ok": True, "armazenamento": config.armazenamento, "auth": config.auth,
                "openalex_chave": bool(config.openalex_api_key)}

    @app.get("/eu", response_model=Usuario, tags=["Sistema"])
    def eu(u: Usuario = Depends(usuario_atual)):
        return u

    for r in (painel.router, discentes.router, docentes.router, producoes.router, cadastros.router):
        app.include_router(r)
    return app


app = criar_app()
