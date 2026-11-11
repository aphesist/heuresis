"""The mutable configuration surface: one dataclass per pipeline stage."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from importlib import resources
from typing import Any


@dataclass
class RouterCfg:
    ask_threshold: float = 0.6
    default_intent: str = "lookup"


@dataclass
class RetrieveCfg:
    k_lexical: int = 50
    k_dense: int = 50
    rrf_k: int = 60
    rerank_in: int = 50
    rerank_out: int = 8
    early_stop: bool = True
    early_stop_margin: float = 0.35
    dense: bool = True
    expand: bool = False
    expand_hops: int = 1
    rerank: bool = False
    rewrite: bool = False
    second_round: bool = False


@dataclass
class DraftCfg:
    model: str = "claude-haiku-5-5"
    max_tokens: int = 600
    max_context_chars: int = 24000
    max_sentences: int = 0


@dataclass
class VerifyCfg:
    support_threshold: float = 0.5
    partial_threshold: float = 0.3
    atomic_claims: bool = False


@dataclass
class DecideCfg:
    min_supported_fraction: float = 1.0
    partial_fraction: float = 0.5
    conflict_margin: float = 0.1


@dataclass
class Config:
    router: RouterCfg = field(default_factory=RouterCfg)
    retrieve: RetrieveCfg = field(default_factory=RetrieveCfg)
    draft: DraftCfg = field(default_factory=DraftCfg)
    verify: VerifyCfg = field(default_factory=VerifyCfg)
    decide: DecideCfg = field(default_factory=DecideCfg)


def config_to_dict(cfg: Config) -> dict[str, Any]:
    return asdict(cfg)


def _build(cls: type, d: Any, where: str) -> Any:
    if not isinstance(d, dict):
        raise ValueError(f"{where or 'config'}: expected an object, got {type(d).__name__}")
    known = {f.name: f for f in fields(cls)}
    unknown = sorted(set(d) - set(known))
    if unknown:
        raise ValueError(f"unknown config key(s) in {where or 'config'}: {', '.join(unknown)}")
    kwargs: dict[str, Any] = {}
    for name, value in d.items():
        default = getattr(cls(), name)
        path = f"{where}.{name}" if where else name
        if is_dataclass(default):
            kwargs[name] = _build(type(default), value, path)
        else:
            kwargs[name] = value
    return cls(**kwargs)


def config_from_dict(d: dict[str, Any]) -> Config:
    """Build a Config; missing keys keep defaults, unknown keys raise ValueError."""
    return _build(Config, d, "")


def load_config(path: str | None = None) -> Config:
    """Load a JSON config; None loads the packaged default.json."""
    if path is None:
        text = resources.files("heuresis.surface").joinpath("default.json").read_text("utf-8")
    else:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    return config_from_dict(json.loads(text))
