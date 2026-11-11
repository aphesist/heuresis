"""Content hash of the locked folder and the surface-only diff check."""
from __future__ import annotations

import hashlib
from pathlib import Path

SURFACE_PREFIX = ("src", "heuresis", "surface")


def locked_hash(directory: str | Path | None = None) -> str:
    """sha256 over the sorted file names and bytes of ``locked/*.py``."""
    d = Path(directory) if directory is not None else Path(__file__).resolve().parent
    h = hashlib.sha256()
    for f in sorted(d.glob("*.py"), key=lambda p: p.name):
        h.update(f.name.encode("utf-8") + b"\0")
        h.update(f.read_bytes() + b"\0")
    return h.hexdigest()


def _inside_surface(path: str) -> bool:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    parts = p.split("/")
    if ".." in parts or "" in parts or "." in parts:
        return False
    return len(parts) > len(SURFACE_PREFIX) and tuple(parts[: len(SURFACE_PREFIX)]) == SURFACE_PREFIX


def check_diff(changed_paths: list[str]) -> list[str]:
    """Return the paths that are not inside ``src/heuresis/surface/``."""
    return [p for p in changed_paths if not _inside_surface(p)]
