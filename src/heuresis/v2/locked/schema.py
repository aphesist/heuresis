"""The surface schema: the only values a candidate may change, and their bounds.

The surface is data (``v2/surface/*.json`` and ``prompts/*.txt``). A candidate can change a
value the schema names, inside its bounds, and a prompt text inside its limits. It cannot add
code, a gate, a judge prompt, a decision threshold or a risk target.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Marker of the canary passages used by the improvement loop; no prompt may contain it.
CANARY_MARKER = "hx-canary-"


@dataclass(frozen=True)
class Field:
    kind: str  # "int" | "float" | "bool" | "enum"
    default: Any
    lo: float | None = None
    hi: float | None = None
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromptSpec:
    max_chars: int
    required: tuple[str, ...] = ()


def _i(default, lo, hi) -> Field:
    return Field("int", default, lo, hi)


SCHEMA: dict[str, dict[str, Field]] = {
    "retrieve": {
        "k_lexical": _i(50, 10, 200),
        "k_dense": _i(50, 10, 200),
        "fusion": Field("enum", "convex", choices=("none", "rrf", "convex")),
        "alpha": Field("float", 0.7, 0.0, 1.0),
        "rrf_k": _i(60, 1, 200),
        "k_first": _i(8, 3, 20),
        "search_k": _i(5, 2, 12),
        "prf_terms": _i(0, 0, 12),
        "prf_docs": _i(3, 1, 10),
        "open_radius": _i(1, 0, 3),
        "edge_expand": Field("bool", False),
    },
    "agent": {
        "max_turns": _i(6, 1, 10),
        "queries_per_turn": _i(3, 1, 4),
        "max_context_chars": _i(40000, 8000, 200000),
        "max_sentences": _i(0, 0, 20),
        "max_tokens": _i(4096, 256, 16000),
    },
    "repair": {"rounds": _i(1, 0, 2)},
    "route": {
        "lookup_direct": Field("bool", True),
        "escalate": Field("bool", False),
    },
    "judge": {"max_tokens": _i(400, 64, 2000)},
}

PROMPTS: dict[str, PromptSpec] = {
    "agent_system": PromptSpec(6000, ("SEARCH:", "OPEN:", "ABSTAIN")),
    "agent_more": PromptSpec(1500),
    "agent_last": PromptSpec(1500),
    "repair": PromptSpec(1500),
}

#: Substrings no prompt may contain (matched lower-cased): the judge's verdict words and the
#: canary marker, so a prompt can neither address the judge nor name a canary.
FORBIDDEN: tuple[str, ...] = (
    "NOT_SUPPORTED",
    "NOT_FOLLOWS",
    "SUFFICIENT:",
    "PREMISE:",
    "CONFLICT:",
    CANARY_MARKER,
)


@dataclass(frozen=True)
class Surface:
    config: dict[str, dict[str, Any]]
    prompts: dict[str, str]

    def get(self, section: str, key: str) -> Any:
        return self.config[section][key]

    def prompt(self, name: str) -> str:
        return self.prompts[name]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _check_value(name: str, f: Field, v: Any) -> list[str]:
    if f.kind == "bool":
        return [] if isinstance(v, bool) else [f"{name}: expected a bool, got {v!r}"]
    if f.kind == "enum":
        return [] if isinstance(v, str) and v in f.choices else [
            f"{name}: {v!r} is not one of {list(f.choices)}"]
    if f.kind == "int":
        if isinstance(v, bool) or not isinstance(v, int):
            return [f"{name}: expected an int, got {v!r}"]
    elif f.kind == "float":
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
            return [f"{name}: expected a number, got {v!r}"]
    else:  # pragma: no cover - schema error
        return [f"{name}: unknown field kind {f.kind!r}"]
    if f.lo is not None and v < f.lo or f.hi is not None and v > f.hi:
        return [f"{name}: {v!r} is outside [{f.lo}, {f.hi}]"]
    return []


def _check_prompt(name: str, text: Any) -> list[str]:
    spec = PROMPTS[name]
    if not isinstance(text, str):
        return [f"prompt {name}: expected text"]
    out: list[str] = []
    if len(text) > spec.max_chars:
        out.append(f"prompt {name}: {len(text)} chars exceeds {spec.max_chars}")
    for req in spec.required:
        if req not in text:
            out.append(f"prompt {name}: missing required {req!r}")
    low = text.lower()
    for bad in FORBIDDEN:
        if bad.lower() in low:
            out.append(f"prompt {name}: contains forbidden {bad!r}")
    return out


def validate(surface: Surface) -> list[str]:
    """Violations of the schema; empty means valid."""
    out: list[str] = []
    cfg = surface.config if isinstance(surface.config, dict) else {}
    for section, values in cfg.items():
        if section not in SCHEMA:
            out.append(f"unknown section {section!r}")
            continue
        if not isinstance(values, dict):
            out.append(f"{section}: expected an object")
            continue
        for key in values:
            if key not in SCHEMA[section]:
                out.append(f"unknown key {section}.{key}")
    for section, fields in SCHEMA.items():
        values = cfg.get(section)
        values = values if isinstance(values, dict) else {}
        for key, f in fields.items():
            if key not in values:
                out.append(f"missing {section}.{key}")
            else:
                out.extend(_check_value(f"{section}.{key}", f, values[key]))
    prompts = surface.prompts if isinstance(surface.prompts, dict) else {}
    for name in prompts:
        if name not in PROMPTS:
            out.append(f"unknown prompt {name!r}")
    for name in PROMPTS:
        if name not in prompts:
            out.append(f"missing prompt {name}")
        else:
            out.extend(_check_prompt(name, prompts[name]))
    return out


def apply_overrides(surface: Surface, candidate: dict) -> Surface:
    """A new surface with ``candidate`` applied; ``ValueError`` listing every violation."""
    problems: list[str] = []
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    for k in candidate:
        if k not in ("config", "prompts"):
            problems.append(f"unknown candidate field {k!r}")
    config = copy.deepcopy(surface.config)
    prompts = dict(surface.prompts)
    cc = candidate.get("config") or {}
    if not isinstance(cc, dict):
        problems.append("candidate.config must be an object")
        cc = {}
    for path, value in cc.items():
        section, _, key = str(path).partition(".")
        if section not in SCHEMA or key not in SCHEMA.get(section, {}):
            problems.append(f"unknown config key {path!r}")
            continue
        config.setdefault(section, {})[key] = value
    cp = candidate.get("prompts") or {}
    if not isinstance(cp, dict):
        problems.append("candidate.prompts must be an object")
        cp = {}
    for name, text in cp.items():
        if name not in PROMPTS:
            problems.append(f"unknown prompt {name!r}")
            continue
        prompts[name] = text
    new = Surface(config, prompts)
    problems.extend(v for v in validate(new) if v not in problems)
    if problems:
        raise ValueError("; ".join(problems))
    return new


def surface_hash(surface: Surface) -> str:
    blob = json.dumps({"config": surface.config, "prompts": surface.prompts},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def describe() -> dict:
    return {
        "config": {
            s: {k: {"kind": f.kind, "default": f.default, "lo": f.lo, "hi": f.hi,
                    "choices": list(f.choices)} for k, f in fields.items()}
            for s, fields in SCHEMA.items()
        },
        "prompts": {n: {"max_chars": p.max_chars, "required": list(p.required)}
                    for n, p in PROMPTS.items()},
        "forbidden": list(FORBIDDEN),
    }


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def default_directory() -> Path:
    return Path(__file__).resolve().parent.parent / "surface"


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot read {path.name}: {e}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected an object")
    return data


def load_surface(directory: str | Path | None = None, *, domain: str | None = None,
                 prompt_set: str | None = None) -> Surface:
    """``default.json``, then ``domain.<domain>.json`` if present, then prompt-set overrides
    (``prompts/<name>.<prompt_set>.txt``). ``ValueError`` if the result is not valid."""
    d = Path(directory) if directory is not None else default_directory()
    config: dict[str, dict[str, Any]] = {
        s: {k: f.default for k, f in fields.items()} for s, fields in SCHEMA.items()}
    layers = [d / "default.json"]
    if domain:
        layers.append(d / f"domain.{domain}.json")
    for i, path in enumerate(layers):
        if not path.is_file():
            if i == 0:
                raise ValueError(f"missing {path}")
            continue
        for section, values in _read_json(path).items():
            if isinstance(values, dict) and isinstance(config.get(section, {}), dict):
                config.setdefault(section, {}).update(values)
            else:
                config[section] = values
    prompts: dict[str, str] = {}
    for name in PROMPTS:
        paths = [d / "prompts" / f"{name}.txt"]
        if prompt_set:
            paths.append(d / "prompts" / f"{name}.{prompt_set}.txt")
        for path in reversed(paths):  # the override wins
            if path.is_file():
                prompts[name] = path.read_text(encoding="utf-8").strip()
                break
    surface = Surface(config, prompts)
    problems = validate(surface)
    if problems:
        raise ValueError("invalid surface: " + "; ".join(problems))
    return surface
