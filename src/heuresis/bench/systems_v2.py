"""The ``engine2`` benchmark system: the v2 engine (``heuresis.v2.engine.EngineV2``) behind the
harness's ``System`` interface.

It is built exactly like ``EngineSystem`` where that makes sense (same date handling, same row
fields, same budget rule) and differs where the contract says so (``docs/v2-contracts.md``):
its own generator (``BenchContext.v2_llm_for``), a judge model and an optional strong model, the
surface from ``BenchContext.v2_surface`` (else the packaged one for the dataset's domain and
prompt set) and an optional calibration. The generator is NOT wrapped in ``LegalPrompts``: v2 has
its own Portuguese prompts through ``prompt_set``.

The ``replay`` payload holds what is needed to read a run offline without any passage text:
status, confidence, the engine's ``meta``, the abstention type, per claim the text, kind, label,
support, checks and marks, per passage its mark, unit, version, validity and trust fields, and the
tokens per stage. ``bench.calibrate2`` reads ``confidence`` from it.
"""
from __future__ import annotations

import json
import threading
from typing import Any

from ..model import Answer, AsOf, StageTrace, Usage
from .ledger import BudgetExceeded
from .systems import BenchContext, Result, System, _Tap, add_call_record
from .types import Question

__all__ = ["EngineV2System", "SEARCH_STAGES", "replay_payload"]

#: Trace stages that ran a query against the store.
SEARCH_STAGES = ("retrieve", "search", "open", "lookup")
BELOW_TAU = "below the confidence threshold"


class _V2Tap(_Tap):
    """A ``_Tap`` that reports the wrapped model's ``supports_cache_break`` (the engine only
    inserts the cache marker for a client that says it can use it)."""

    @property
    def supports_cache_break(self) -> bool:
        return bool(getattr(self.inner, "supports_cache_break", False))


def _jsonable(x: Any) -> Any:
    return json.loads(json.dumps(x, default=str))


def _usage_by_stage(trace: list[StageTrace]) -> dict:
    out: dict[str, dict] = {}
    for t in trace:
        o = out.setdefault(t.stage, {"n": 0, "tokens_in": 0, "tokens_out": 0, "usd": 0.0})
        o["n"] += 1
        o["tokens_in"] += t.tokens_in
        o["tokens_out"] += t.tokens_out
        o["usd"] += t.usd
    return out


def replay_payload(ans: Answer) -> dict:
    """The offline record of one answer (no passage text)."""
    meta = _jsonable(ans.meta or {})
    conf = meta.get("confidence")
    conf = float(ans.grade) if not isinstance(conf, (int, float)) else float(conf)
    below = bool(ans.abstention and BELOW_TAU in (ans.abstention.message or ""))
    out = {
        "engine": "v2", "status": ans.status, "confidence": conf, "meta": meta,
        "abstention": ans.abstention.type if ans.abstention else None,
        "tau": meta.get("tau"), "below_tau": below,
        "claims": [{"text": c.text, "kind": c.kind, "label": c.label, "support": float(c.support),
                    "checks": {k: bool(v) for k, v in c.checks.items()}, "note": c.note,
                    "passage_marks": list(c.passage_marks), "tool_marks": list(c.tool_marks)}
                   for c in ans.claims],
        "passages": [{"mark": p.mark, "unit_id": p.unit_id, "seq": p.seq, "valid_from": p.valid_from,
                      "valid_to": p.valid_to, "coverage": p.coverage, "certainty": p.certainty,
                      "stage": p.stage} for p in ans.passages],
        "raw_usage_by_stage": _usage_by_stage(ans.trace),
    }
    if below:
        # What the engine would have answered without the threshold: the sentences it kept. It lets
        # ``bench.calibrate2`` label rows the threshold held back (it is answer text, not a passage).
        out["candidate_text"] = " ".join(c.text for c in ans.claims if c.label in ("supported", "partial"))
    return out


class EngineV2System(System):
    name = "engine2"
    cites = True

    def __init__(self, ctx: BenchContext, **_: Any):
        super().__init__(ctx, time_aware=True)
        self._tls = threading.local()
        self._lock = threading.RLock()
        self._surface_obj: Any = None
        self._calibration_obj: Any = None
        self._calibration_loaded = False

    # --- configuration -------------------------------------------------------------------

    def _domain(self) -> str:
        return self.ctx.dataset.meta.get("domain", "jsonl")

    def surface(self) -> Any:
        with self._lock:
            if self._surface_obj is None:
                s = getattr(self.ctx, "v2_surface", None)
                if s is None:
                    from ..v2.locked.schema import load_surface
                    s = load_surface(domain=self._domain(),
                                     prompt_set=self.ctx.dataset.meta.get("prompt_set"))
                self._surface_obj = s
            return self._surface_obj

    def surface_hash(self) -> str:
        from ..v2.locked.schema import surface_hash
        return surface_hash(self.surface())

    def calibration(self) -> Any:
        """The calibration the engine will consider: the one given to the context (a ``Calibration`` or the
        path of its file), else the newest file of ``v2/calibration/`` for this surface and dataset; None when there is none. The engine uses it only if its surface hash matches."""
        with self._lock:
            if not self._calibration_loaded:
                from ..v2.locked import calibration as cal_mod
                c = getattr(self.ctx, "v2_calibration", None)
                if isinstance(c, (str, bytes)) or hasattr(c, "__fspath__"):
                    c = cal_mod.load(c)
                elif c is None:
                    # the newest file for this surface AND this dataset (the engine's own lookup does not
                    # filter by dataset: three English datasets share one surface hash)
                    from ..v2.engine import CALIBRATION_DIR
                    c = cal_mod.find(CALIBRATION_DIR, self.surface_hash(), self.ctx.dataset.name)
                self._calibration_obj, self._calibration_loaded = c, True
            return self._calibration_obj

    def params(self) -> dict:
        cal = self.calibration()
        used = cal is not None and cal.surface_hash == self.surface_hash() and cal.tau is not None
        return {"surface_hash": self.surface_hash(), "calibration_file": bool(used),
                "calibration_tau": cal.tau if used else None}

    def manifest_info(self) -> dict:
        """What the run manifest records about ``engine2``."""
        try:
            from ..v2.locked.manifest import protected_hash
            prot: str | None = protected_hash()
        except Exception:  # not a source checkout
            prot = None
        try:
            from ..v2.locked.decide import load_policy
            policy_judge: str | None = load_policy().judge_model or None
        except Exception:
            policy_judge = None
        judge_id = getattr(self.ctx.judge_llm_for(), "id", "")
        return {"v2_surface_hash": self.surface_hash(), "protected_hash": prot,
                "judge_model": judge_id, "judge_model_policy": policy_judge,
                "judge_is_policy_model": judge_id == policy_judge,
                "strong_model": getattr(self.ctx.strong_llm_for(), "id", None),
                "v2_cache": bool(getattr(self.ctx.v2_llm_for(), "supports_cache_break", False))}

    def _calibration_arg(self) -> Any:
        """What the engine is given: the calibration chosen here, or, when there is none for this surface and
        dataset, a path that holds no file (``None`` would make the engine look in ``v2/calibration/`` by
        surface hash alone and could pick up another dataset's file)."""
        from pathlib import Path
        cal = self.calibration()
        return cal if cal is not None else Path(self.ctx.db_path + ".no-calibration")

    # --- one engine and its model taps per worker thread --------------------------------------

    def _engine(self):
        eng = getattr(self._tls, "engine", None)
        if eng is None:
            from ..v2.engine import EngineV2  # imported late: the engine is optional for baselines
            ctx = self.ctx
            taps = {"gen": _V2Tap(ctx.v2_llm_for()), "judge": _V2Tap(ctx.judge_llm_for())}
            strong = ctx.strong_llm_for()
            taps["strong"] = _V2Tap(strong) if strong is not None else None
            with ctx._open_lock:
                eng = EngineV2.open(
                    ctx.db_path, self._domain(), surface=self.surface(), llm=taps["gen"],
                    judge_llm=taps["judge"], strong_llm=taps["strong"], embedder=ctx.embedder,
                    calibration=self._calibration_arg())
            self._tls.engine, self._tls.taps = eng, taps
        return eng, self._tls.taps

    # --- answering ------------------------------------------------------------------------------

    def _answer(self, q: Question) -> Result:
        from ..v2.engine import trace_failure
        eng, taps = self._engine()
        for t in taps.values():
            if t is not None:
                t.reset()
        ans: Answer = eng.ask(q.text, as_of=AsOf(valid=q.as_of) if q.as_of else None)
        tr: list[StageTrace] = ans.trace
        fail = trace_failure(tr)
        if fail is not None and fail[0] == "budget":
            # Same as a baseline whose call is refused: the run stops and no row is written.
            raise BudgetExceeded(f"engine2: {fail[1]}")
        usage = Usage(model=getattr(self.ctx.v2_llm_for(), "id", ""),
                      tokens_in=sum(t.tokens_in for t in tr),
                      tokens_out=sum(t.tokens_out for t in tr), usd=ans.usd, ms=ans.ms)
        for t in taps.values():
            for u in (t.usages if t is not None else []):
                add_call_record(usage, u)
                usage.tokens_cached += u.tokens_cached
        searches = sum(1 for t in tr if t.stage in SEARCH_STAGES)
        return Result(
            status="answered" if ans.status in ("answered", "partial") else "abstained",
            text=ans.text, confidence=min(1.0, max(0.0, float(ans.grade))),
            cited_units=tuple(dict.fromkeys(u for u, _ in ans.citations)),
            usage=usage, stage_ms=ans.ms,
            calls=sum(1 for t in tr if t.tokens_in > 0 or t.tokens_out > 0),
            searches=searches,
            retrieved_units=tuple(dict.fromkeys(p.unit_id for p in ans.passages)),
            note=f"engine2 status={ans.status}"
                 + (f"; abstention={ans.abstention.type}" if ans.abstention else ""),
            error=("" if fail is None else f"{fail[0]} failure: {fail[1]}"),
            replay=replay_payload(ans))
