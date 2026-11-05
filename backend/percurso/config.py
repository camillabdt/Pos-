from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def carregar_env(caminho: Path = Path(__file__).resolve().parents[1] / ".env") -> None:
    """Lê backend/.env (CHAVE=valor por linha) sem sobrescrever variáveis já definidas."""
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        if valor.strip():
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env()


@dataclass(frozen=True)
class Config:
    # "memoria" (dev, dados de exemplo) ou "firestore"
    armazenamento: str = field(default_factory=lambda: os.getenv("PERCURSO_ARMAZENAMENTO", "memoria"))
    # "dev" (papel escolhido por cabeçalho, SÓ para desenvolvimento) ou "firebase"
    auth: str = field(default_factory=lambda: os.getenv("PERCURSO_AUTH", "dev"))
    firebase_project_id: str | None = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_ID"))
    openalex_mailto: str | None = field(default_factory=lambda: os.getenv("OPENALEX_MAILTO"))
    openalex_api_key: str | None = field(default_factory=lambda: os.getenv("OPENALEX_API_KEY"))
    cors_origens: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip() for o in os.getenv("CORS_ORIGENS", "http://localhost:5173").split(",") if o.strip()
        )
    )
    carregar_exemplo: bool = field(
        default_factory=lambda: os.getenv("PERCURSO_EXEMPLO", "1") == "1"
    )
