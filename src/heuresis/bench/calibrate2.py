"""Fit the confidence threshold of ``engine2`` from dev runs (``docs/design-v2.md`` section d).

``python -m heuresis.bench.calibrate2 RUN_DIR [RUN_DIR ...] --label {containment,judge} [--out PATH]``

Reads the ``engine2`` rows of run folders (written by ``bench.run`` with a ``--split`` that is NOT held
out: ``dev``, ``dev2``, ``temporal``, ``cal<k>``, ``rot<c>``), takes each row's confidence from its ``replay`` payload
and decides whether the answer was wrong, then calls ``v2.locked.calibration.fit`` with the owner's policy
(``v2.locked.decide.load_policy``): walking from the strictest threshold to the loosest, a threshold is
accepted while the Clopper-Pearson upper bound of the error rate among answered questions is at most
alpha. It prints the table and writes a ``Calibration`` file (default
``src/heuresis/v2/calibration/<dataset>-<surface hash[:12]>.json``) plus a ``.table.md`` beside it.

* ``--label containment``: wrong = the answered row's containment grade is not correct (``outcome``);
  unanswerable questions answered are wrong. The label of the English datasets.
* ``--label judge``: wrong unless the containment grade is correct or ``judge.jsonl`` of the run folder
  holds the verdict EQUIVALENT for the row (``bench.judge``). A model's label, not a human's.

Thresholds below the threshold the run already applied (its ``tau``) are not directly observable: a row
the engine held back for its confidence was not answered. Such rows carry their confidence in
``replay.confidence`` and the sentences the engine would have given in ``replay.candidate_text``; with
``--label containment`` those are graded here, so the walk can go below the run's tau. With
``--label judge`` nobody judged them, so only thresholds at or above the run's tau are evaluable. The
table says which are which.

Held-out run folders are refused.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

from . import report, splits
from .judge import load_verdicts

__all__ = ["collect", "calibrate", "render_table", "default_out", "main"]

LABELS = {"containment": "containment", "judge": "judge_equivalent"}
EPS = 1e-9


def default_out(dataset: str, surface_hash: str) -> Path:
    import heuresis.v2 as v2
    return Path(v2.__file__).resolve().parent / "calibration" / f"{dataset}-{surface_hash[:12]}.json"


def collect(run_dir: str, label: str, *, questions: Callable[[dict], dict[str, Any]] | None = None) -> dict:
    """The rows of one run folder as ``{"conf": [...], "wrong": [...], "n_questions": n, "taus": [...],
    "held_back": k, "ungraded": m, "manifest": {...}}``. ``questions(manifest)`` returns ``{qid: Question}``;
    it is called only when rows held back by the threshold have to be graded (containment)."""
    if label not in LABELS:
        raise ValueError(f"unknown label {label!r}")
    manifest, rows, _ = report.load(run_dir)
    split = manifest.get("split") or ""
    if splits.is_held_out(split):
        raise ValueError(f"{run_dir}: split {split!r} is held out; calibration reads dev splits only")
    verdicts = load_verdicts(run_dir) if label == "judge" else {}
    mine = [r for r in rows if r.get("system") == "engine2" and r.get("status") != "error"]
    conf: list[float] = []
    wrong: list[bool] = []
    taus: list[float] = []
    held, ungraded = 0, 0
    qs: dict[str, Any] | None = None
    for r in mine:
        rp = r.get("replay") or {}
        c = rp.get("confidence", r.get("confidence"))
        if c is None:
            continue
        if r.get("status") == "answered":
            ok = r.get("outcome") == "correct" or (
                label == "judge" and (verdicts.get(("engine2", r["qid"])) or {}).get("verdict") == "EQUIVALENT")
            conf.append(float(c))
            wrong.append(not ok)
            if isinstance(rp.get("tau"), (int, float)):
                taus.append(float(rp["tau"]))
        elif rp.get("below_tau"):
            held += 1
            text = rp.get("candidate_text") or ""
            if label != "containment" or not text:
                ungraded += 1
                continue
            if qs is None:
                qs = questions(manifest) if questions else {}
            q = qs.get(r["qid"])
            if q is None:
                ungraded += 1
                continue
            from .run import grade
            conf.append(float(c))
            wrong.append(grade(q, "answered", text)["outcome"] != "correct")
            if isinstance(rp.get("tau"), (int, float)):
                taus.append(float(rp["tau"]))
    return {"conf": conf, "wrong": wrong, "n_questions": len(mine), "taus": taus, "held_back": held,
            "ungraded": ungraded, "manifest": manifest}


def calibrate(runs: Sequence[dict], label: str, policy: Any) -> dict:
    """Fit over the collected runs. Returns the fit, the table with an ``evaluable`` flag per grid step,
    the run's tau and the numbers for the ``Calibration`` file."""
    from ..v2.locked import calibration as cal
    conf = [c for r in runs for c in r["conf"]]
    wrong = [w for r in runs for w in r["wrong"]]
    n_q = sum(r["n_questions"] for r in runs)
    taus = [t for r in runs for t in r["taus"]]
    run_tau = max(taus) if taus else policy.default_tau
    ungraded = sum(r["ungraded"] for r in runs)
    # Below the run's tau only containment-graded held-back rows can say anything, and only if none
    # of them was left ungraded.
    below_ok = label == "containment" and ungraded == 0
    grid = sorted(policy.grid, reverse=True)
    evaluable = {t: (t >= run_tau - EPS or below_ok) for t in grid}
    fit = cal.fit(conf, wrong, alpha=policy.alpha, delta=policy.delta,
                  grid=[t for t in grid if evaluable[t]], min_answers=policy.min_calibration_answers)
    visited = {row["tau"]: row for row in fit["table"]}
    table = []
    for t in grid:
        if not evaluable[t]:
            table.append({"tau": t, "evaluable": False, "n_answered": None, "errors": None, "upper": None,
                          "accepted": None, "coverage": None})
            continue
        row = visited.get(t)
        if row is None:  # the walk stopped before this threshold
            n = sum(1 for c in conf if c >= t)
            table.append({"tau": t, "evaluable": True, "n_answered": n,
                          "errors": sum(w for c, w in zip(conf, wrong) if c >= t), "upper": None,
                          "accepted": None, "coverage": n / n_q if n_q else 0.0, "walk_stopped": True})
        else:
            table.append({"tau": t, "evaluable": True, "n_answered": row["n_answered"], "errors": row["errors"],
                          "upper": row["upper"], "accepted": row["accepted"],
                          "coverage": row["n_answered"] / n_q if n_q else 0.0})
    return {"fit": fit, "table": table, "run_tau": run_tau, "n_questions": n_q, "below_ok": below_ok,
            "ungraded": ungraded, "n_rows": len(conf)}


def render_table(res: dict, *, label: str, dataset: str, split: str, surface_hash: str, policy: Any) -> str:
    f = res["fit"]
    L = [f"engine2 calibration: dataset {dataset}, split {split}, surface {surface_hash[:12]}, label "
         f"{LABELS[label]}", f"policy: alpha {policy.alpha}, delta {policy.delta}, at least "
         f"{policy.min_calibration_answers} answered rows for a step; questions {res['n_questions']}, "
         f"rows with a confidence {res['n_rows']}", f"the runs applied tau = {res['run_tau']}",
         ("thresholds below it are evaluable: held-back rows were graded by containment"
          if res["below_ok"] else
          "thresholds below it are NOT evaluable from these rows"
          + (f" ({res['ungraded']} held-back rows could not be graded)" if res["ungraded"] else
             " (the judge label has no verdict for rows the engine did not answer)")),
         "", "| tau | evaluable | answered | errors | upper bound | accepted | coverage |",
         "|---|---|---|---|---|---|---|"]
    for r in res["table"]:
        if not r["evaluable"]:
            L.append(f"| {r['tau']} | no | | | | | |")
            continue
        up = "" if r["upper"] is None else f"{r['upper']:.4f}"
        acc = "walk stopped" if r.get("walk_stopped") else ("" if r["accepted"] is None
                                                            else ("yes" if r["accepted"] else "no"))
        L.append(f"| {r['tau']} | yes | {r['n_answered']} | {r['errors']} | {up} | {acc} | "
                 f"{100 * r['coverage']:.1f}% |")
    tau = f["tau"]
    L += ["", f"selected tau: {tau if tau is not None else 'none (nothing certified; the engine keeps default_tau)'}"]
    if tau is not None:
        L.append(f"answered {f['n_answered']}, errors {f['errors']}, upper bound {f['upper']:.4f} "
                 f"(at most alpha = {policy.alpha} with confidence {1 - policy.delta:.2f})")
    return "\n".join(L) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m heuresis.bench.calibrate2", description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir", nargs="+")
    ap.add_argument("--label", choices=sorted(LABELS), required=True)
    ap.add_argument("--out", default=None, help="the calibration file (default "
                                                "src/heuresis/v2/calibration/<dataset>-<surface hash[:12]>.json)")
    ap.add_argument("--data-root", default="data", help="where the corpora are (rot<c> splits, held-back rows)")
    a = ap.parse_args(argv)
    from ..v2.locked import calibration as cal
    from ..v2.locked.decide import load_policy
    policy = load_policy()

    def questions(manifest: dict) -> dict[str, Any]:
        from . import run as run_mod
        ds = run_mod._load_dataset(manifest["dataset"])
        return {q.id: q for q in splits.load_split(ds, manifest["split"], root=a.data_root)}

    runs, manifests = [], []
    for d in a.run_dir:
        try:
            r = collect(d, a.label, questions=questions)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except OSError as e:
            print(f"error: {d}: {e}", file=sys.stderr)
            return 2
        m = r["manifest"]
        if not m.get("v2_surface_hash"):
            print(f"error: {d}: the manifest has no v2_surface_hash (no engine2 in this run)", file=sys.stderr)
            return 2
        if m.get("dry_run"):
            print(f"warning: {d} is a dry run (offline fakes): the fit is not a measurement", file=sys.stderr)
        runs.append(r)
        manifests.append(m)
    if len({m["dataset"] for m in manifests}) != 1 or len({m["v2_surface_hash"] for m in manifests}) != 1:
        print("error: the run folders must share one dataset and one engine2 surface hash", file=sys.stderr)
        return 2
    dataset, sh = manifests[0]["dataset"], manifests[0]["v2_surface_hash"]
    split = "+".join(sorted({m["split"] for m in manifests}))
    res = calibrate(runs, a.label, policy)
    text = render_table(res, label=a.label, dataset=dataset, split=split, surface_hash=sh, policy=policy)
    print(text, end="")
    f = res["fit"]
    n_q = res["n_questions"]
    c = cal.Calibration(
        tau=f["tau"], alpha=policy.alpha, delta=policy.delta, n_questions=n_q, n_answered=int(f["n_answered"]),
        errors=int(f["errors"]), upper=float(f["upper"]), coverage=(f["n_answered"] / n_q if n_q else 0.0),
        surface_hash=sh, dataset=dataset, split=split, label=LABELS[a.label],
        created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    out = Path(a.out) if a.out else default_out(dataset, sh)
    cal.save(c, out)
    out.with_suffix(".table.md").write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
