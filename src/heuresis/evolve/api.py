"""The interface an outer optimiser (autopoiesis, a cron job, a person) uses.

``evaluate`` is stateless apart from the row caches, the ledger and (for the promote stage) the
promotion counters; its report never contains a gold answer, a gold unit, a row or a question of the
promotion set. ``reflective_dataset`` gives redacted failure traces for a proposer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from ..bench.ledger import Ledger
from ..v2.locked import manifest
from ..v2.locked import schema as schema_mod
from . import candidates as cand_mod
from .archive import Archive, read_json
from .canaries import contains_marker, is_canary
from .evaluator import STAGES, BenchRunner, Evaluator, load_config
from .splits import SplitSource

STAGE_INFO = {
    "static": "schema validation, path guard, protected-hash check, prompt lint (free)",
    "smoke": "offline run on the packaged fixture with fakes (free)",
    "screen": "small paired sample of the cycle's rotating draw against the champion",
    "dev": "the whole rotating draw, paired, with guard rails of the dev rows",
    "promote": "the sealed promotion block plus anchors: pass or fail and the decision statistics only",
}


@dataclass
class EvalContext:
    """What a paid run needs: real clients and the ledger they charge. Passing one to ``evaluate``
    selects the real benchmark runner; nothing else does."""
    splits: SplitSource
    llm: Any = None
    judge_llm: Any = None
    strong_llm: Any = None
    embedder: Any = None
    ledger: Ledger | None = None
    estimate_usd: float = 0.01
    judge_model: str | None = None


def make_evaluator(workdir: str | Path, *, ledger: Ledger | None = None, context: EvalContext | None = None,
                   runner: Callable | None = None, smoke_runner: Callable | None = None,
                   splits: SplitSource | None = None, config: Mapping | None = None,
                   allow_unpinned: bool = False, root: str | Path | None = None) -> Evaluator:
    judge_model = None
    if context is not None:
        ledger = ledger or context.ledger
        splits = splits or context.splits
        judge_model = context.judge_model or getattr(context.judge_llm, "id", None)
        if runner is None:
            runner = BenchRunner(context.splits, workdir, llm=context.llm, judge_llm=context.judge_llm,
                                 strong_llm=context.strong_llm, embedder=context.embedder,
                                 ledger=ledger, estimate_usd=context.estimate_usd)
    return Evaluator(workdir, runner=runner, smoke_runner=smoke_runner, splits=splits, config=config,
                     ledger=ledger, allow_unpinned=allow_unpinned, root=root,
                     offline=(runner is None and context is None), judge_model=judge_model)


def _resolve(candidate: Any, workdir: str | Path) -> Any:
    """A candidate id of the archive becomes its overrides; anything else is passed through."""
    if isinstance(candidate, str) and len(candidate) == 64 and not Path(candidate).exists():
        row = Archive(workdir).get(candidate)
        if row is not None:
            return row["candidate"]
    return candidate


def describe(root: str | Path | None = None, *, workdir: str | Path | None = None,
             config: Mapping | None = None) -> dict:
    cfg = load_config(config)
    base = cand_mod.base_surface()
    champ = Archive(workdir).champion() if workdir is not None else None
    diffs = manifest.verify_manifest(root)
    return {
        "surface_schema": schema_mod.describe(),
        "champion": {"id": champ["id"] if champ else cand_mod.candidate_id({}),
                     "surface_hash": champ["surface_hash"] if champ else schema_mod.surface_hash(base)},
        "protected_hash": manifest.protected_hash(root),
        "protected_ok": not diffs, "protected_differences": diffs[:10],
        "stages": [{"name": s, "description": STAGE_INFO[s]} for s in STAGES],
        "budget": {"cap_usd_per_cycle": cfg["cap_usd"], "ledger_margin_usd": cfg["ledger_margin_usd"],
                   "modelled_usd_per_question": cfg["estimate_usd_per_question"],
                   "label": "modelled, not measured"},
        "datasets": {"rotating": cfg["rotating_datasets"], "anchors": cfg["anchors"]},
        "constants": {k: cfg[k] for k in ("penalty_t", "rotating_n", "screen_n", "dev_top", "k",
                                          "promotion_n", "promotion_min_n", "promotion_query_budget",
                                          "alpha", "anchor_n", "guard_rails", "tripwires")},
        "nonce_protocol": "heuresis evolve evaluate ... --nonce N prints exactly one line "
                          "'HEURESIS-EVAL N <json>'",
    }


def evaluate(candidate: Any, *, stage: str, workdir: str | Path, ledger: Ledger | None = None,
             context: EvalContext | None = None, runner: Callable | None = None,
             smoke_runner: Callable | None = None, splits: SplitSource | None = None,
             config: Mapping | None = None, allow_unpinned: bool = False,
             root: str | Path | None = None, cycle: int | None = None) -> dict:
    ev = make_evaluator(workdir, ledger=ledger, context=context, runner=runner, smoke_runner=smoke_runner,
                        splits=splits, config=config, allow_unpinned=allow_unpinned, root=root)
    dev = None
    if stage == "promote" and isinstance(candidate, str):
        row = Archive(workdir).get(candidate)
        dev = row["stages"].get("dev") if row else None
    return ev.evaluate(_resolve(candidate, workdir), stage, cycle=cycle, dev=dev)


def promote(candidate_id: str, *, workdir: str | Path, **kw: Any) -> dict:
    """Run the promote stage on an archived candidate and, if it passes, make it the champion."""
    arch = Archive(workdir)
    row = arch.get(candidate_id)
    if row is None:
        raise ValueError(f"unknown candidate {candidate_id}")
    ev = make_evaluator(workdir, **kw)
    ev.new_cost = 0.0
    rep = ev.promote(row["candidate"], dev=row["stages"].get("dev"))
    cyc = arch.state()["cycle"]
    arch.record_stage(candidate_id, "promote", rep, cycle=cyc)
    rep = dict(rep)
    rep["promoted"] = False
    if rep["passed"]:
        arch.set_champion(candidate_id, reason="promoted by command", cycle=cyc, stats=rep["metrics"])
        st = arch.state()
        st["promotions"] += 1
        arch.save_state(st)
        rep["promoted"] = True
    return rep


def rollback(*, workdir: str | Path, to: str | None = None, reason: str = "manual") -> dict:
    arch = Archive(workdir)
    return arch.rollback(to=to, reason=reason, cycle=arch.state()["cycle"])


def status(*, workdir: str | Path) -> dict:
    arch = Archive(workdir)
    st = arch.state()
    rows = arch.rows()
    counts: dict[str, int] = {}
    for r in rows.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    champ = arch.champion()
    spent = Ledger(str(Path(workdir) / "ledger.jsonl"), 0.0).spent
    return {"champion": ({"id": champ["id"], "surface_hash": champ["surface_hash"],
                          "since_cycle": champ.get("since_cycle"), "history": len(champ.get("history", []))}
                         if champ else None),
            "cycle": st["cycle"], "open_cycle": st["open_cycle"], "candidates": len(rows),
            "by_status": counts, "promotion_tests": st["promotion_tests"], "promotions": st["promotions"],
            "promotion_blocks": st["promotion"], "spent_usd": round(spent, 6)}


def reflective_dataset(candidate_id: str, *, workdir: str | Path, limit: int = 20) -> list[dict]:
    """Redacted failure traces of the candidate on rotating dev draws: question, the engine's
    answer, typed outcome, abstention type and reasons. No gold answer, no gold unit, no anchor or
    promotion row (those are stored apart, without text), no canary."""
    arch = Archive(workdir)
    row = arch.get(candidate_id)
    if row is None or not row.get("surface_hash"):
        return []
    doc = read_json(Path(workdir) / "cache" / f"{row['surface_hash'][:32]}.rotating.json", None)
    if not doc:
        return []
    rows = [r for r in doc["rows"].values()
            if not is_canary(r["qid"]) and str(r.get("split", "")).startswith("rot")]
    rows = [r for r in rows if r["outcome"] != "correct"]
    rows.sort(key=lambda r: (0 if r["outcome"] == "wrong" else 1, r["dataset"], r["qid"]))
    out = []
    for r in rows:
        entry = {"qid": r["qid"], "dataset": r["dataset"], "question": r.get("question", ""),
                 "answer": (r.get("text") or "")[:600], "status": r["status"], "outcome": r["outcome"],
                 "abstention": r.get("abstention"), "reasons": list(r.get("reasons") or []),
                 "confidence": r.get("confidence")}
        if any(contains_marker(str(v)) for v in entry.values()):
            continue
        out.append(entry)
        if len(out) >= limit:
            break
    return out
