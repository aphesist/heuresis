"""Candidates of the improvement loop: a JSON document of overrides of the packaged surface.

``{"config": {"<section>.<key>": value, ...}, "prompts": {"<name>": "<text>", ...}}``, always
relative to the packaged default surface (``v2/surface/``), so a candidate directory that mirrors
the champion's surface gives the champion's overrides and the same id. The id is the sha256 of the
canonical JSON of the normalised document (values equal to the default are dropped, keys sorted).

A candidate can come from a dict, a JSON file or a directory that mirrors ``v2/surface/``
(``default.json`` and ``prompts/<name>.txt``). Loading never raises on a bad candidate: it returns
the problems (path guard, unreadable file, unexpected file) so that the static stage can record
them; schema violations are found by ``surface_of`` (``apply_overrides``).
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..v2.locked import manifest
from ..v2.locked import schema as schema_mod
from ..v2.locked.schema import Surface

MAX_FILE_BYTES = 200_000


def canonical_json(doc: Any) -> str:
    return json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _same(a: Any, b: Any) -> bool:
    return type(a) is type(b) and a == b or (
        isinstance(a, (int, float)) and isinstance(b, (int, float))
        and not isinstance(a, bool) and not isinstance(b, bool) and a == b)


def normalise(doc: Any, base: Surface | None = None) -> dict:
    """The document with empty sections dropped and, given ``base``, every value equal to the base
    surface's dropped. A document that is not an object is returned as ``{}``."""
    if not isinstance(doc, dict):
        return {}
    out: dict[str, Any] = {}
    for part in ("config", "prompts"):
        sec = doc.get(part)
        if isinstance(sec, dict) and sec:
            kept = {}
            for k, v in sec.items():
                if base is not None:
                    try:
                        if part == "config":
                            s, _, key = str(k).partition(".")
                            cur = base.config[s][key]
                        else:
                            cur = base.prompts[k]
                        if _same(cur, v) if part == "config" else (isinstance(v, str)
                                                                     and cur.strip() == v.strip()):
                            continue
                    except (KeyError, TypeError):
                        pass
                kept[str(k)] = v
            if kept:
                out[part] = dict(sorted(kept.items()))
        elif sec not in (None, {}):
            out[part] = sec  # malformed: kept so that validation reports it
    for k, v in doc.items():
        if k not in ("config", "prompts"):
            out[k] = v
    return dict(sorted(out.items()))


def candidate_id(doc: Any, base: Surface | None = None) -> str:
    return hashlib.sha256(canonical_json(normalise(doc, base)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Candidate:
    overrides: dict
    parent: str | None = None
    note: str = ""

    @property
    def id(self) -> str:
        return candidate_id(self.overrides)

    def doc(self) -> dict:
        return copy.deepcopy(normalise(self.overrides))


@dataclass
class Loaded:
    overrides: dict
    problems: list[str] = field(default_factory=list)
    kind: str = "dict"


def base_surface() -> Surface:
    return schema_mod.load_surface()


def surface_of(overrides: dict, base: Surface | None = None) -> Surface:
    """The surface the overrides give; ``ValueError`` listing every violation."""
    return schema_mod.apply_overrides(base if base is not None else base_surface(), overrides)


def diff_surface(surface: Surface, reference: Surface) -> dict:
    """Overrides that turn ``reference`` into ``surface`` (only values that differ)."""
    config = {}
    for s, values in surface.config.items():
        for k, v in values.items():
            ref = reference.config.get(s, {}).get(k)
            if not _same(ref, v):
                config[f"{s}.{k}"] = v
    prompts = {n: t for n, t in surface.prompts.items()
               if t.strip() != reference.prompts.get(n, "").strip()}
    return normalise({"config": config, "prompts": prompts})


def check_changed_paths(paths: list[str]) -> list[str]:
    """The locked path guard on an explicit list of changed paths (relative to the repository)."""
    return manifest.check_candidate_paths(paths)


def _read_text(p: Path, problems: list[str], rel: str) -> str | None:
    try:
        if p.stat().st_size > MAX_FILE_BYTES:
            problems.append(f"{rel}: larger than {MAX_FILE_BYTES} bytes")
            return None
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        problems.append(f"{rel}: unreadable ({type(e).__name__})")
        return None


def load_dir(directory: str | Path, base: Surface | None = None) -> Loaded:
    """A candidate directory that mirrors ``v2/surface/``: ``default.json`` (config values) and
    ``prompts/<name>.txt``. Every file goes through the locked path guard as if it lived under the
    surface directory; any other file, a symlink leaving the directory or a ``.py`` file is a
    problem. The result is the diff against the packaged surface."""
    base = base if base is not None else base_surface()
    d = Path(directory)
    problems: list[str] = []
    if not d.is_dir():
        return Loaded({}, [f"{directory}: not a directory"], "dir")
    root = d.resolve()
    config: dict[str, Any] = {}
    prompts: dict[str, str] = {}
    files = sorted(p for p in d.rglob("*") if p.is_file() or p.is_symlink())
    guard_paths = []
    for p in files:
        rel = p.relative_to(d).as_posix()
        guard_paths.append(f"{manifest.SURFACE_DIR}/{rel}")
    problems.extend(manifest.check_candidate_paths(guard_paths))
    bad = {v.split(":", 1)[0] for v in problems}
    for p in files:
        rel = p.relative_to(d).as_posix()
        gp = f"{manifest.SURFACE_DIR}/{rel}"
        if gp in bad:
            continue
        if p.is_symlink():
            try:
                p.resolve().relative_to(root)
            except ValueError:
                problems.append(f"{rel}: symlink leaves the candidate directory")
                continue
        if rel == "default.json":
            text = _read_text(p, problems, rel)
            if text is None:
                continue
            try:
                data = json.loads(text)
            except ValueError as e:
                problems.append(f"{rel}: not JSON ({e})")
                continue
            if not isinstance(data, dict):
                problems.append(f"{rel}: expected an object")
                continue
            for section, values in data.items():
                if not isinstance(values, dict):
                    problems.append(f"{rel}: section {section!r} is not an object")
                    continue
                for key, v in values.items():
                    cur = base.config.get(section, {}).get(key, object())
                    if not _same(cur, v):
                        config[f"{section}.{key}"] = v
        elif rel.startswith("prompts/") and rel.count("/") == 1 and rel.endswith(".txt"):
            name = rel[len("prompts/"):-len(".txt")]
            text = _read_text(p, problems, rel)
            if text is None:
                continue
            if name not in base.prompts:
                problems.append(f"{rel}: unknown prompt {name!r}")
            elif text.strip() != base.prompts[name].strip():
                prompts[name] = text.strip()
        else:
            problems.append(f"{rel}: not part of a surface (only default.json and prompts/<name>.txt)")
    return Loaded(normalise({"config": config, "prompts": prompts}), problems, "dir")


def load_candidate(source: Any, base: Surface | None = None) -> Loaded:
    """A candidate from a ``Candidate``, a dict, a JSON file or a directory."""
    if isinstance(source, Candidate):
        return Loaded(source.doc(), [], "candidate")
    if isinstance(source, dict):
        return Loaded(copy.deepcopy(source), [], "dict")
    p = Path(str(source))
    if p.is_dir():
        return load_dir(p, base)
    if p.is_file():
        probs: list[str] = []
        text = _read_text(p, probs, p.name)
        if text is None:
            return Loaded({}, probs, "file")
        try:
            data = json.loads(text)
        except ValueError as e:
            return Loaded({}, [f"{p.name}: not JSON ({e})"], "file")
        if not isinstance(data, dict):
            return Loaded({}, [f"{p.name}: expected an object"], "file")
        return Loaded(data, [], "file")
    return Loaded({}, [f"{source}: no such file or directory"], "file")
