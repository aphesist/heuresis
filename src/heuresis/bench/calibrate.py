"""Calibrate the two verification thresholds on dev without paying for another model call.

A run folder written by ``bench.run`` keeps, for each engine row, what is needed to redo
the labelling and the decision offline (``row["replay"]``): the raw draft, the passages
shown (unit id, seq, mark, text, coverage, certainty, validity), the tool results and, per
claim, the entailment score BEFORE thresholding together with the checks that do not
depend on a threshold (``exists``, ``valid_at_date``, ``numbers_traced``). Drafts do not
depend on the thresholds, so :func:`replay` re-applies ``locked.verify``'s labelling rule
and ``locked.decide.decide`` to those stored scores. No model and no entailer is called.

* :func:`grid` evaluates the penalised score of the engine at every pair of thresholds
  (each 0.1 .. 0.9 in steps of 0.1, ``partial <= support``: 45 pairs), pooled over the run
  folders given, and returns the table and the argmax.
* Tie-break (PREREGISTRATION.md section 8.1, still marked **proposed** there; kept as
  written): among pairs with the same pooled score, the higher ``support_threshold``,
  then the higher ``partial_threshold`` (the more conservative setting).
* Only the dev splits (``dev``, and ``dev2`` since the redesign). :func:`grid` and the command
  line refuse a run folder whose manifest split is not the one asked for, and any other split
  (``test``, ``sealed``) outright.

Command line: ``python -m heuresis.bench.calibrate RUN_DIR [RUN_DIR ...]``.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
from typing import Any, Sequence

from .. import draft as draft_mod
from ..locked.decide import decide, deterministic_failure
from ..model import Claim, Passage, ToolResult
from ..surface.config import Config, config_from_dict, load_config
from . import report
from .run import grade
from .types import Question

__all__ = ["replay", "grid", "THRESHOLDS", "TIE_BREAK", "CalibrationRefused", "main"]

#: 0.1 .. 0.9 in steps of 0.1.
THRESHOLDS = tuple(i / 10 for i in range(1, 10))
TIE_BREAK = ("ties go to the higher support threshold, then the higher partial threshold "
             "(PREREGISTRATION.md section 8.1, proposed)")


class CalibrationRefused(ValueError):
    """The run folder is not a dev run, or holds no replayable engine rows."""


def _decide_cfg(cfg: Any):
    return getattr(cfg, "decide", cfg)


def _label(support: float, support_threshold: float, partial_threshold: float,
           checks: dict) -> str:
    """The labelling rule of ``locked.verify.verify``, from a stored score."""
    if support >= support_threshold:
        label = "supported"
    elif support >= partial_threshold:
        label = "partial"
    else:
        label = "unsupported"
    if not (checks.get("exists", True) and checks.get("valid_at_date", True)
            and checks.get("numbers_traced", True)):
        return "unsupported"
    return label


def replay(row: dict, support_threshold: float, partial_threshold: float,
           cfg: Config) -> tuple[str, str, float]:
    """(engine status, answer text, grade) the engine would have returned for this stored
    row at the given thresholds. ``cfg`` supplies the decision settings (``cfg.decide``).
    A row whose engine stopped before verification (no source, out of scope, a budget stop)
    does not depend on the thresholds and is returned as it was."""
    rp = row.get("replay")
    if not rp:
        raise ValueError(f"row ({row.get('system')}, {row.get('qid')}) has no replay payload; "
                         "it was written by a runner that did not store drafts")
    if not rp.get("verified"):
        return rp["engine_status"], row.get("text", ""), float(rp.get("grade", 0.0))

    passages = [Passage(unit_id=p["unit_id"], seq=p["seq"], text=p["text"], title=p.get("title", ""),
                        source_id=p.get("source_id", ""), valid_from=p.get("valid_from"),
                        valid_to=p.get("valid_to"), coverage=p["coverage"],
                        certainty=p["certainty"], mark=p["mark"]) for p in rp["passages"]]
    results = [ToolResult(mark=r["mark"], tool=r["tool"], args=r.get("args") or {}, ok=r["ok"],
                          value=r["value_text"], error=r.get("error", ""))
               for r in rp["tool_results"]]
    claims = []
    for c in rp["claims"]:
        label = _label(float(c["support"]), support_threshold, partial_threshold, c["checks"])
        claims.append(Claim(text=c["text"], passage_marks=list(c["passage_marks"]),
                            tool_marks=list(c["tool_marks"]), support=float(c["support"]),
                            label=label, checks=dict(c["checks"])))
    d = draft_mod.parse_draft(rp.get("draft_raw", ""))
    status, g, _ab = decide(claims, passages, None, _decide_cfg(cfg), None, declined=d.declined)
    text = ""
    if status == "answered":
        text = draft_mod.render(d, results)
    elif status == "partial":
        graded = getattr(_decide_cfg(cfg), "mode", "strict") == "grade"
        bad = {c.text for c in claims
               if (deterministic_failure(c) if graded else c.label == "unsupported")}
        keep = [s for s in d.sentences if s.text not in bad]
        text = draft_mod.render(dataclasses.replace(d, sentences=keep), results)
    return status, text, g


def run_status(engine_status: str) -> str:
    """The runner's two statuses: both ``answered`` and ``partial`` count as answering."""
    return "answered" if engine_status in ("answered", "partial") else "abstained"


def _question(row: dict) -> Question:
    rp = row.get("replay") or {}
    return Question(id=row["qid"], text="", answers=tuple(rp.get("answers") or ()),
                    answerable=bool(row.get("answerable", True)))


def outcome_of(row: dict, status: str, text: str) -> dict:
    """The graded outcome (``run.grade``) of a replayed engine status and text."""
    return grade(_question(row), run_status(status), text)


#: Splits that calibration and replay may read: the tuning splits, never test or sealed.
CALIBRATION_SPLITS = ("dev", "dev2")


def _load_dev(out_dirs: Sequence[str], split: str,
              system: str = "engine") -> list[tuple[dict, Config, str]]:
    if split not in CALIBRATION_SPLITS:
        raise CalibrationRefused(
            f"calibration uses the dev splits {CALIBRATION_SPLITS} only, not {split!r}")
    items: list[tuple[dict, Config, str]] = []
    for d in out_dirs:
        manifest, rows, _ = report.load(d)
        if manifest.get("split") != split:
            raise CalibrationRefused(
                f"{d}: manifest split is {manifest.get('split')!r}, not {split!r}; refusing")
        own = (manifest.get("engine_configs") or {}).get(system) or manifest.get("engine_config")
        cfg = config_from_dict(own) if own else load_config()
        for r in rows:
            if r.get("system") != system:
                continue
            if r.get("split", "dev") != split:
                raise CalibrationRefused(f"{d}: a row of split {r.get('split')!r}; refusing")
            items.append((r, cfg, d))
    if not items:
        raise CalibrationRefused(f"no {system} rows in the given run folders")
    return items


def grid(out_dir: str | Sequence[str], split: str = "dev",
         system: str = "engine") -> tuple[list[dict], dict]:
    """Penalised score of the engine at every threshold pair, pooled over the run folders.

    Returns ``(table, best)``. ``table`` has one dict per pair (45), in ascending
    (support, partial) order, with ``support``, ``partial``, ``n``, ``score`` (mean of
    +1 / 0 / -1 over every engine question of every folder), ``sum``, ``correct``,
    ``wrong``, ``abstained`` and ``errors`` (error rows count as wrong at every pair).
    ``best`` is the argmax with the tie-break of :data:`TIE_BREAK`; it also carries
    ``packaged`` (the row at the packaged pair, when it is in the grid) and ``tie_break``.
    """
    dirs = [out_dir] if isinstance(out_dir, str) else list(out_dir)
    items = _load_dev(dirs, split, system)
    cache: dict[tuple[int, str, str], dict] = {}
    table: list[dict] = []
    for s in THRESHOLDS:
        for p in THRESHOLDS:
            if p > s:
                continue
            tot = {"correct": 0, "wrong": 0, "abstained": 0}
            total, errors = 0.0, 0
            for i, (row, cfg, _d) in enumerate(items):
                if row.get("status") == "error":
                    tot["wrong"] += 1
                    total -= 1.0
                    errors += 1
                    continue
                status, text, _g = replay(row, s, p, cfg)
                key = (i, run_status(status), text)
                g = cache.get(key)
                if g is None:
                    g = cache[key] = outcome_of(row, status, text)
                tot[g["outcome"]] += 1
                total += g["score"]
            n = len(items)
            table.append({"support": s, "partial": p, "n": n, "sum": total, "score": total / n,
                          **tot, "errors": errors})
    best = max(table, key=lambda r: (r["sum"], r["support"], r["partial"]))
    packaged = next((r for r in table if (r["support"], r["partial"]) == (0.5, 0.3)), None)
    return table, {**best, "packaged": packaged, "tie_break": TIE_BREAK}


def render(table: Sequence[dict], best: dict, dirs: Sequence[str]) -> str:
    L = ["# Verification thresholds on dev (offline replay, no model call)", "",
         f"Run folders: {', '.join(dirs)}. Engine questions pooled: {table[0]['n']}.", "",
         "| support | partial | correct | wrong | abstained | penalised score |",
         "|---|---|---|---|---|---|"]
    for r in table:
        L.append(f"| {r['support']:.1f} | {r['partial']:.1f} | {r['correct']} | {r['wrong']} | "
                 f"{r['abstained']} | {r['score']:.4f} |")
    L += ["", f"Argmax: support_threshold {best['support']:.1f}, partial_threshold "
              f"{best['partial']:.1f}, penalised score {best['score']:.4f} (n = {best['n']}).",
          f"Tie-break: {best['tie_break']}."]
    pk = best.get("packaged")
    if pk:
        L.append(f"Packaged pair (0.5, 0.3): penalised score {pk['score']:.4f}.")
    return "\n".join(L)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m heuresis.bench.calibrate",
                                 description="Grid of the two verification thresholds, replayed "
                                             "from stored drafts. Dev run folders only.")
    ap.add_argument("run_dir", nargs="+", help="run folders written by heuresis.bench.run on dev")
    ap.add_argument("--split", default="dev", choices=CALIBRATION_SPLITS,
                    help="the split of the run folders (default: dev)")
    ap.add_argument("--system", default="engine", choices=("engine", "engine_single"),
                    help="which engine's rows to replay (default: engine; the thresholds only "
                         "matter for engine_single, whose decision mode is strict)")
    a = ap.parse_args(argv)
    try:
        table, best = grid(a.run_dir, a.split, a.system)
    except CalibrationRefused as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    drys = [d for d in a.run_dir if report.load(d)[0].get("dry_run")]
    if drys:
        print(report.BANNER + f" ({', '.join(drys)})")
    print(render(table, best, a.run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
