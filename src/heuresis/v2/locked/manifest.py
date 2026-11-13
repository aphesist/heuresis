"""Hashes of every protected file, and the path guard for improvement-loop candidates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Iterable

_BENCH = ("stats", "datasets", "brlaw", "brlaw_versioned", "citations", "judge", "ledger",
          "splits", "run", "report", "types", "calibrate2", "systems", "systems_v2")

#: Glob patterns relative to the repository root; ``dir/**`` means every file below ``dir``.
PROTECTED: tuple[str, ...] = (
    "src/heuresis/locked/**",
    "src/heuresis/v2/locked/**",
    "src/heuresis/store.py",
    "src/heuresis/model.py",
    "src/heuresis/interfaces.py",
    "src/heuresis/tools/**",
    "src/heuresis/references.py",
    "src/heuresis/v2/bind.py",
    *(f"src/heuresis/bench/{n}.py" for n in _BENCH),
    "src/heuresis/evolve/**",
)

SURFACE_DIR = "src/heuresis/v2/surface"
MANIFEST_PATH = "src/heuresis/v2/locked/PROTECTED.json"


def default_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _root(root) -> Path:
    return Path(root) if root is not None else default_root()


def _expand(root: Path, pattern: str) -> list[Path]:
    if pattern.endswith("/**"):
        base = root / pattern[:-3]
        return [p for p in base.rglob("*") if p.is_file()] if base.is_dir() else []
    return [p for p in root.glob(pattern) if p.is_file()]


def protected_files(root=None) -> dict[str, str]:
    """Path (relative, posix) -> sha256 of every protected file that exists."""
    r = _root(root)
    out: dict[str, str] = {}
    for pat in PROTECTED:
        for p in _expand(r, pat):
            rel = p.relative_to(r).as_posix()
            if rel == MANIFEST_PATH or "__pycache__" in p.parts or p.suffix == ".pyc":
                continue
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(sorted(out.items()))


def _hash_of(files: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()


def protected_hash(root=None) -> str:
    return _hash_of(protected_files(root))


def write_manifest(root=None) -> Path:
    r = _root(root)
    files = protected_files(r)
    path = r / MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"files": files, "hash": _hash_of(files)}, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_manifest(root=None) -> list[str]:
    """Changed, missing or new protected paths relative to ``PROTECTED.json``."""
    r = _root(root)
    path = r / MANIFEST_PATH
    try:
        recorded = json.loads(path.read_text(encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return [f"missing or unreadable: {MANIFEST_PATH}"]
    now = protected_files(r)
    out = [f"changed: {p}" for p in sorted(now) if p in recorded and now[p] != recorded[p]]
    out += [f"missing: {p}" for p in sorted(recorded) if p not in now]
    out += [f"new: {p}" for p in sorted(now) if p not in recorded]
    return out


def check_candidate_paths(paths: Iterable[str]) -> list[str]:
    """Violations: a path outside ``SURFACE_DIR``, not ``.json``/``.txt``, with ``..``, or absolute."""
    out: list[str] = []
    for raw in paths:
        s = str(raw)
        norm = s.replace("\\", "/")
        parts = PurePosixPath(norm).parts
        if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":") or norm.startswith("~"):
            out.append(f"{s}: absolute path")
            continue
        if ".." in parts:
            out.append(f"{s}: contains '..'")
            continue
        clean = PurePosixPath(*[x for x in parts if x != "."]) if parts else PurePosixPath("")
        base = PurePosixPath(SURFACE_DIR)
        if clean == base or base not in (clean, *clean.parents):
            out.append(f"{s}: outside {SURFACE_DIR}")
        elif clean.suffix not in (".json", ".txt"):
            out.append(f"{s}: only .json and .txt files may change")
    return out
