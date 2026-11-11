"""Generic exchange format: a folder of JSON-lines files."""
from __future__ import annotations

import dataclasses
import json
import os

from ..model import CERTAINTY, COVERAGE_MAX, COVERAGE_MIN, OPS, Edge, Event, Source, Unit

FILES = (
    ("sources.jsonl", Source, False),
    ("units.jsonl", Unit, True),
    ("events.jsonl", Event, True),
    ("edges.jsonl", Edge, False),
)


def _check(cls, obj: dict, where: str):
    fields = {f.name: f for f in dataclasses.fields(cls)}
    unknown = set(obj) - set(fields)
    if unknown:
        raise ValueError(f"{where}: unknown field(s) {sorted(unknown)}")
    for name, f in fields.items():
        required = f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        if required and name not in obj:
            raise ValueError(f"{where}: missing field {name!r}")
    for name, v in obj.items():
        t = str(fields[name].type)
        if name in ("axes", "meta"):
            if not isinstance(v, dict):
                raise ValueError(f"{where}: field {name!r} must be an object")
        elif name in ("authority", "coverage"):
            if isinstance(v, bool) or not isinstance(v, int):
                raise ValueError(f"{where}: field {name!r} must be an integer")
        elif "None" in t:
            if v is not None and not isinstance(v, str):
                raise ValueError(f"{where}: field {name!r} must be a string or null")
        elif not isinstance(v, str):
            raise ValueError(f"{where}: field {name!r} must be a string")
    if cls is Event:
        if obj["op"] not in OPS:
            raise ValueError(f"{where}: op must be one of {OPS}, got {obj['op']!r}")
        if obj["op"] in ("create", "replace", "correct") and obj.get("text") is None:
            raise ValueError(f"{where}: op {obj['op']!r} requires text")
        if obj.get("certainty", "high") not in CERTAINTY:
            raise ValueError(f"{where}: certainty must be one of {CERTAINTY}")
    if cls is Source and not COVERAGE_MIN <= obj.get("coverage", COVERAGE_MAX) <= COVERAGE_MAX:
        raise ValueError(f"{where}: coverage must be {COVERAGE_MIN}..{COVERAGE_MAX}")


def read_jsonl_folder(path: str):
    out = []
    for fname, cls, required in FILES:
        fp = os.path.join(path, fname)
        if not os.path.exists(fp):
            if required:
                raise ValueError(f"{fname}: file is required but missing in {path}")
            out.append([])
            continue
        rows = []
        with open(fp, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                where = f"{fname}:{n}"
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{where}: invalid JSON ({e.msg})") from None
                if not isinstance(obj, dict):
                    raise ValueError(f"{where}: row must be a JSON object")
                _check(cls, obj, where)
                rows.append(cls(**obj))
        out.append(rows)
    return tuple(out)


class JsonlDomain:
    name = "jsonl"
    axes: tuple[str, ...] = ()

    def read(self, path: str):
        return read_jsonl_folder(path)

    def rules(self):
        return []

    def tools(self):
        return []

    def abstention_text(self, kind, query):
        return None
