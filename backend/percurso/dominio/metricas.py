"""Métricas bibliométricas calculadas localmente (portado do Poshboard)."""

from __future__ import annotations

from collections.abc import Iterable


def h_index(citacoes: Iterable[int | None]) -> int:
    ordenadas = sorted((c or 0 for c in citacoes), reverse=True)
    h = 0
    for i, c in enumerate(ordenadas, start=1):
        if c >= i:
            h = i
        else:
            break
    return h


def i10_index(citacoes: Iterable[int | None]) -> int:
    return sum(1 for c in citacoes if (c or 0) >= 10)


def h5_index(obras: Iterable[tuple[int | None, int | None]], ano_atual: int) -> int:
    """h-index restrito às obras dos últimos 5 anos. `obras` = (ano, citações)."""
    return h_index(c for ano, c in obras if ano is not None and ano >= ano_atual - 4)
