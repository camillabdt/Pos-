from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    # "memoria" (dev, dados de exemplo) ou "firestore"
    armazenamento: str = field(default_factory=lambda: os.getenv("PERCURSO_ARMAZENAMENTO", "memoria"))
    # "dev" (papel escolhido por cabeçalho, SÓ para desenvolvimento) ou "firebase"
    auth: str = field(default_factory=lambda: os.getenv("PERCURSO_AUTH", "dev"))
    firebase_project_id: str | None = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_ID"))
    openalex_mailto: str | None = field(default_factory=lambda: os.getenv("OPENALEX_MAILTO"))
    cors_origens: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip() for o in os.getenv("CORS_ORIGENS", "http://localhost:5173").split(",") if o.strip()
        )
    )
    carregar_exemplo: bool = field(
        default_factory=lambda: os.getenv("PERCURSO_EXEMPLO", "1") == "1"
    )
