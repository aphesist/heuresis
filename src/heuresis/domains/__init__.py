"""Domain plug-ins: everything specific to one kind of corpus."""
from __future__ import annotations

import importlib

from ..interfaces import Domain

#: name -> (module, class)
_REGISTRY: dict[str, tuple[str, str]] = {
    "text": ("text", "TextDomain"),
    "git": ("git", "GitDomain"),
    "tables": ("tables", "TablesDomain"),
    "jsonl": ("jsonl", "JsonlDomain"),
    "legal_br": ("legal_br", "LegalBRDomain"),
}


def available() -> list[str]:
    return sorted(_REGISTRY)


def get_domain(name: str, **options) -> Domain:
    """Return a fresh plug-in instance by name. Options go to its constructor."""
    try:
        module, cls = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown domain {name!r}; available: {', '.join(available())}"
        ) from None
    mod = importlib.import_module(f"{__name__}.{module}")
    return getattr(mod, cls)(**options)


def utc_date(timestamp: float) -> str:
    import datetime as _dt

    return _dt.datetime.fromtimestamp(timestamp, _dt.timezone.utc).strftime("%Y-%m-%d")


__all__ = ["get_domain", "available", "utc_date"]
