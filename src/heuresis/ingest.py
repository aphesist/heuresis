"""Read a path with a domain plug-in and load it into a store."""
from __future__ import annotations

from typing import Any

from .domains import get_domain


def ingest(store: Any, path: str, domain: Any = "text") -> dict[str, int]:
    """Load ``path`` into ``store`` through ``domain`` (a plug-in or its name).

    Calls ``store.add`` then ``store.rebuild``; embeds nothing. Ids are
    deterministic and ``store.add`` is idempotent, so ingesting twice is a no-op.
    """
    if isinstance(domain, str):
        domain = get_domain(domain)
    sources, units, events, edges = domain.read(str(path))
    store.add(sources=sources, units=units, events=events, edges=edges)
    store.rebuild()
    return {
        "sources": len(sources),
        "units": len(units),
        "events": len(events),
        "edges": len(edges),
    }
