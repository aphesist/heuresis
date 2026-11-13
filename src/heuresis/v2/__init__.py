"""Version 2 of the engine. Import-light: ``EngineV2`` is loaded on first use."""
from __future__ import annotations

from .locked.schema import load_surface

__all__ = ["EngineV2", "load_surface"]


def __getattr__(name: str):
    if name == "EngineV2":
        from .engine import EngineV2

        return EngineV2
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
