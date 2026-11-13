"""Proposers of the improvement loop. They return candidates; they never choose the parent (the
archive does, in fixed code) and never see gold answers or promotion data.

* ``PerturbProposer(seed)``: no model. Changes one to three schema values inside their bounds; never
  produces an invalid candidate (each child is validated with the locked ``apply_overrides``).
* ``ReflectiveProposer(llm)``: a model reads the schema, the parent's prompts and the redacted
  reflective dataset (failure traces) and replies with a JSON candidate (the GEPA pattern). Output is
  parsed defensively; anything invalid gives no candidate. It is never called unless an LLM is
  injected, so nothing here can spend money offline.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any, Sequence

from ..bench.ledger import BudgetExceeded
from ..v2.locked import schema as schema_mod
from ..v2.locked.schema import Surface
from . import candidates as cand_mod
from .candidates import Candidate


@dataclass(frozen=True)
class Parent:
    id: str
    overrides: dict
    surface: Surface


def merge_overrides(parent: dict, delta: dict) -> dict:
    """The parent's overrides with ``delta`` applied on top (config keys and prompt names)."""
    out = {"config": dict((parent or {}).get("config") or {}),
           "prompts": dict((parent or {}).get("prompts") or {})}
    for part in ("config", "prompts"):
        if isinstance(delta.get(part), dict):
            out[part].update(delta[part])
    return out


def _new_value(rng: random.Random, f: schema_mod.Field, current: Any) -> Any:
    if f.kind == "bool":
        return not current
    if f.kind == "enum":
        return rng.choice([c for c in f.choices if c != current] or list(f.choices))
    lo, hi = float(f.lo), float(f.hi)
    if f.kind == "int":
        lo_i, hi_i = int(lo), int(hi)
        for _ in range(20):
            if rng.random() < 0.7:  # a small step
                step = max(1, (hi_i - lo_i) // 10)
                v = min(hi_i, max(lo_i, int(current) + rng.choice((-1, 1)) * rng.randint(1, step)))
            else:
                v = rng.randint(lo_i, hi_i)
            if v != current:
                return v
        return lo_i if current != lo_i else hi_i
    for _ in range(20):
        v = round(rng.uniform(lo, hi), 2)
        if v != current:
            return v
    return lo if current != lo else hi


class PerturbProposer:
    name = "perturb"
    wants_traces = False

    def __init__(self, seed: int = 0, max_changes: int = 3):
        self.seed = int(seed)
        self.max_changes = max(1, min(3, int(max_changes)))

    def propose(self, parent: Parent, k: int, *, seed: int = 0, traces: Any = None) -> list[Candidate]:
        rng = random.Random(f"perturb:{self.seed}:{seed}:{parent.id}")
        base = cand_mod.base_surface()
        keys = [(s, key) for s, fields in schema_mod.SCHEMA.items() for key in fields]
        out: list[Candidate] = []
        seen = {parent.id}
        for _ in range(60 * max(1, k)):
            if len(out) >= k:
                break
            m = rng.randint(1, self.max_changes)
            chosen = rng.sample(keys, m)
            delta = {}
            for s, key in chosen:
                delta[f"{s}.{key}"] = _new_value(rng, schema_mod.SCHEMA[s][key], parent.surface.config[s][key])
            doc = cand_mod.normalise(merge_overrides(parent.overrides, {"config": delta}), base)
            cid = cand_mod.candidate_id(doc)
            if cid in seen:
                continue
            try:
                cand_mod.surface_of(doc, base)
            except ValueError:  # cannot happen: values are drawn inside the bounds
                continue
            seen.add(cid)
            out.append(Candidate(doc, parent=parent.id, note="perturb: " + ", ".join(sorted(delta))))
        return out


# ---------------------------------------------------------------------------------------------


def extract_json_objects(raw: str) -> list[str]:
    """Balanced ``{...}`` substrings of ``raw`` in order (string-aware), for defensive parsing."""
    out, depth, start, in_str, esc = [], 0, -1, False, False
    for i, ch in enumerate(raw or ""):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = depth > 0
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                out.append(raw[start:i + 1])
    return out


def parse_candidate(raw: str) -> dict | None:
    """The first JSON object in ``raw`` that has only the fields ``config`` and ``prompts`` (at
    least one non-empty), or None."""
    for blob in extract_json_objects(raw):
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        if not isinstance(data, dict) or not data:
            continue
        if set(data) - {"config", "prompts"}:
            continue
        if not (data.get("config") or data.get("prompts")):
            continue
        if not all(isinstance(data.get(p, {}), dict) for p in ("config", "prompts")):
            continue
        return data
    return None


SYSTEM = ("You improve the configuration and prompts of a question-answering engine that answers "
          "only from retrieved sources and refuses when it cannot support an answer. You change only "
          "values listed in the schema, inside their bounds. Reply with one JSON object and nothing "
          "else: {\"config\": {\"section.key\": value}, \"prompts\": {\"name\": \"text\"}}, listing only "
          "the values you change.")


class ReflectiveProposer:
    name = "reflective"
    wants_traces = True

    def __init__(self, llm: Any, *, max_tokens: int = 1500, max_traces: int = 12):
        self.llm = llm
        self.max_tokens = max_tokens
        self.max_traces = max_traces

    def build_prompt(self, parent: Parent, traces: Sequence[dict]) -> str:
        d = schema_mod.describe()
        schema_lines = []
        for s, keys in d["config"].items():
            for key, f in keys.items():
                bounds = f"choices {f['choices']}" if f["kind"] == "enum" else (
                    "bool" if f["kind"] == "bool" else f"{f['kind']} in [{f['lo']}, {f['hi']}]")
                schema_lines.append(f"- {s}.{key}: {bounds}; current {parent.surface.config[s][key]!r}")
        prompts = "\n".join(f"### prompt {n} (max {d['prompts'][n]['max_chars']} chars, must contain "
                            f"{d['prompts'][n]['required']})\n{t}" for n, t in parent.surface.prompts.items())
        shown = [{k: t.get(k) for k in ("question", "answer", "status", "outcome", "abstention", "reasons")}
                 for t in list(traces)[:self.max_traces]]
        trace_text = "\n".join(json.dumps(t, ensure_ascii=False) for t in shown) or "(no failures to show)"
        return (f"Values you may change:\n" + "\n".join(schema_lines) + "\n\nCurrent prompts:\n" + prompts
                + "\n\nFailures of the current version (question, the engine's answer, typed outcome, "
                  "reasons; gold answers are never shown):\n" + trace_text
                + "\n\nPropose one change that should reduce these failures without making the engine "
                  "answer more questions it cannot support. Reply with the JSON object only.")

    def propose(self, parent: Parent, k: int, *, seed: int = 0, traces: Sequence[dict] | None = None
                ) -> list[Candidate]:
        base = cand_mod.base_surface()
        prompt = self.build_prompt(parent, traces or [])
        out: list[Candidate] = []
        seen = {parent.id}
        for _ in range(max(1, k)):
            try:
                raw, _usage = self.llm.complete(SYSTEM, prompt, max_tokens=self.max_tokens)
            except BudgetExceeded:
                raise
            except Exception:
                break
            delta = parse_candidate(raw if isinstance(raw, str) else "")
            if delta is None:
                continue
            doc = cand_mod.normalise(merge_overrides(parent.overrides, delta), base)
            try:
                cand_mod.surface_of(doc, base)
            except ValueError:
                continue
            cid = cand_mod.candidate_id(doc)
            if cid in seen:
                continue
            seen.add(cid)
            out.append(Candidate(doc, parent=parent.id, note="reflective"))
        return out
