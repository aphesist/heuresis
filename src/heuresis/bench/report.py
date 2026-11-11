"""Turn a run folder into ``results.json`` and ``results.md``.

Definitions
-----------
* correct / wrong / abstained: the outcome triple from ``scoring.outcome`` (an
  abstention on an unanswerable question counts as correct).
* penalised score: +1 correct, 0 abstained, -1 wrong, averaged over questions.
* accuracy = correct / n; coverage = answered / n; selective accuracy = correct
  among answered / answered.
* AURC and the risk-coverage points use the answered questions only, ranked by
  each system's own confidence; risk = wrong / answered so far.
* cost per correct answer = total usd / number of correct outcomes, with a
  bootstrap interval that resamples questions (or clusters).
* paired comparisons use the questions both systems finished; the engine is the
  first system in each pair; the McNemar family (Holm) is every compared baseline.
  The oracle is a ceiling and is excluded from comparisons.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any, Sequence

import numpy as np

from ..locked import scoring
from . import stats

BANNER = "DRY RUN — offline fakes, not a measurement"
REFERENCE = "engine"
EXCLUDED = ("oracle",)


def load(out_dir: str) -> tuple[dict, list[dict], int]:
    manifest: dict = {}
    mp = os.path.join(out_dir, "manifest.json")
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as fh:
            manifest = json.load(fh)
    last: dict[tuple[str, str], dict] = {}
    with open(os.path.join(out_dir, "results.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
                last[(r["system"], r["qid"])] = r
            except (ValueError, KeyError, TypeError):
                continue
    rows = [r for r in last.values() if r.get("status") != "error"]
    return manifest, rows, len(last) - len(rows)


def _cl(rows: Sequence[dict]) -> list[str]:
    return [r.get("cluster") or r["qid"] for r in rows]


def _thin(points: list[tuple[float, float]], cap: int = 100) -> list[list[float]]:
    if len(points) <= cap:
        return [[round(c, 6), round(r, 6)] for c, r in points]
    idx = np.unique(np.linspace(0, len(points) - 1, cap).round().astype(int))
    return [[round(points[i][0], 6), round(points[i][1], 6)] for i in idx]


def _num(x: float) -> float | None:
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else float(x)


def _ci(t: tuple[float, float, float]) -> dict:
    return {"est": _num(t[0]), "lo": _num(t[1]), "hi": _num(t[2])}


def system_metrics(rows: list[dict], iters: int, seed: int) -> dict:
    n = len(rows)
    cnt = {k: sum(1 for r in rows if r["outcome"] == k) for k in ("correct", "wrong", "abstained")}
    out: dict[str, Any] = {"n": n, "counts": cnt, "wilson": {}}
    for k, c in cnt.items():
        lo, hi = stats.wilson_interval(c, n)
        out["wilson"][k] = {"p": c / n if n else None, "lo": lo, "hi": hi}
    scores = [float(r["score"]) for r in rows]
    cl = _cl(rows)
    out["penalised_score"] = _ci(stats.bootstrap_mean_ci(scores, iters=iters, seed=seed, clusters=cl))
    answered = [r for r in rows if r["status"] == "answered"]
    n_ans = len(answered)
    n_ok_ans = sum(1 for r in answered if r["outcome"] == "correct")
    out["accuracy"] = cnt["correct"] / n if n else None
    out["coverage"] = n_ans / n if n else None
    out["selective_accuracy"] = n_ok_ans / n_ans if n_ans else None
    conf = [float(r["confidence"]) for r in answered]
    ok = [r["outcome"] == "correct" for r in answered]
    out["aurc"] = scoring.aurc(conf, ok) if n_ans else None
    out["risk_coverage"] = _thin(scoring.risk_coverage(conf, ok)) if n_ans else []
    un = [r for r in rows if not r.get("answerable", True)]
    out["unanswerable"] = {"n": len(un),
                           "abstain_rate": (sum(1 for r in un if r["status"] != "answered") / len(un))
                           if un else None}
    # citations and retrieval, where gold units exist
    gold_rows = [r for r in rows if r.get("gold_units")]
    cited = [r for r in gold_rows if r["status"] == "answered"]
    if any(r.get("cited_units") for r in rows) and cited:
        pr = [scoring.citation_precision_recall(r["cited_units"], r["gold_units"]) for r in cited]
        out["citation"] = {"n": len(pr), "precision": float(np.mean([p for p, _ in pr])),
                           "recall": float(np.mean([r for _, r in pr]))}
    else:
        out["citation"] = None
    if gold_rows and any(r.get("retrieved_units") for r in rows):
        out["retrieval_recall"] = {"n": len(gold_rows), "value": float(np.mean(
            [scoring.citation_precision_recall(r["retrieved_units"], r["gold_units"])[1]
             for r in gold_rows]))}
    else:
        out["retrieval_recall"] = None
    usd = np.array([float(r["usd"]) for r in rows])
    ms = np.array([float(r["ms"]) for r in rows])
    out["cost"] = {"mean_usd": float(usd.mean()) if n else None, "total_usd": float(usd.sum()),
                   "mean_tokens_in": float(np.mean([r["tokens_in"] for r in rows])) if n else None,
                   "mean_tokens_out": float(np.mean([r["tokens_out"] for r in rows])) if n else None}
    corr = [1.0 if r["outcome"] == "correct" else 0.0 for r in rows]
    out["cost_per_correct"] = _ci(stats.bootstrap_ratio_ci(
        usd, corr, iters=iters, seed=seed, clusters=cl)) if n else _ci((math.nan,) * 3)
    out["latency_ms"] = {"median": float(np.median(ms)) if n else None,
                         "p95": float(np.percentile(ms, 95)) if n else None}
    out["mean_calls"] = float(np.mean([r["calls"] for r in rows])) if n else None
    out["mean_searches"] = float(np.mean([r["searches"] for r in rows])) if n else None
    out["time_aware"] = bool(rows[0].get("time_aware")) if rows else None
    return out


def paired(ref_rows: list[dict], other_rows: list[dict], iters: int, seed: int) -> dict | None:
    a = {r["qid"]: r for r in ref_rows}
    b = {r["qid"]: r for r in other_rows}
    ids = sorted(set(a) & set(b))
    if not ids:
        return None
    ra, rb = [a[i] for i in ids], [b[i] for i in ids]
    sa, sb = [float(r["score"]) for r in ra], [float(r["score"]) for r in rb]
    ca, cb = [r["outcome"] == "correct" for r in ra], [r["outcome"] == "correct" for r in rb]
    only_a, only_b = stats.discordant(ca, cb)
    n = len(ids)
    disc = (only_a + only_b) / n
    return {
        "n": n,
        "score_diff": _ci(stats.paired_bootstrap_ci(sa, sb, iters=iters, seed=seed, clusters=_cl(ra))),
        "reference_only_correct": only_a, "other_only_correct": only_b,
        "discordance": disc, "mcnemar_p": stats.mcnemar_exact(only_a, only_b),
        "min_detectable_diff": _num(stats.min_detectable_diff(n, disc)) if disc > 0 else None,
    }


def build(out_dir: str, iters: int = 10_000, seed: int = 0) -> dict:
    manifest, rows, n_err = load(out_dir)
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["system"], []).append(r)
    order = [s["name"] for s in manifest.get("systems", []) if s["name"] in by]
    order += sorted(set(by) - set(order))
    res: dict[str, Any] = {
        "banner": BANNER if manifest.get("dry_run") else None,
        "dry_run": bool(manifest.get("dry_run")),
        "dataset": manifest.get("dataset"), "split": manifest.get("split"),
        "n_questions_planned": manifest.get("n_questions"), "error_rows": n_err,
        "locked_hash": manifest.get("locked_hash"), "surface_hash": manifest.get("surface_hash"),
        "prompts_hash": manifest.get("prompts_hash"), "price_table": manifest.get("price_table"),
        "models": manifest.get("models"), "bootstrap_iters": iters, "seed": seed,
        "unavailable": {s["name"]: s["reason"] for s in manifest.get("systems", [])
                        if not s.get("available", True)},
        "systems": {s: system_metrics(by[s], iters, seed) for s in order},
        "paired": {}, "reference": REFERENCE,
    }
    if REFERENCE in by:
        names, ps = [], []
        for s in order:
            if s == REFERENCE or s in EXCLUDED:
                continue
            p = paired(by[REFERENCE], by[s], iters, seed)
            if p:
                names.append(s)
                ps.append(p)
        adj = stats.holm([p["mcnemar_p"] for p in ps])
        for s, p, q in zip(names, ps, adj):
            p["mcnemar_p_holm"] = q
            res["paired"][s] = p
    return res


def _pct(x: float | None, d: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def _f(x: float | None, d: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{d}f}"


def _ci_s(c: dict, d: int = 3) -> str:
    return f"{_f(c['est'], d)} [{_f(c['lo'], d)}, {_f(c['hi'], d)}]"


def _usd(x: float | None) -> str:
    return "n/a" if x is None else f"${x:.4f}"


def render(res: dict) -> str:
    L: list[str] = []
    if res["dry_run"]:
        L += [BANNER, ""]
    L.append(f"# Results: {res['dataset']}, split `{res['split']}`")
    L.append("")
    L.append(f"Questions planned: {res['n_questions_planned']}. Bootstrap: {res['bootstrap_iters']} "
             f"resamples, seed {res['seed']}, 95% intervals. Price table: {res['price_table']}.")
    if res["error_rows"]:
        L.append(f"Rows with errors (excluded, retried on restart): {res['error_rows']}.")
    for s, why in res["unavailable"].items():
        L.append(f"Not run: `{s}` ({why}).")
    L.append("")
    sysm = res["systems"]
    sp = f"split `{res['split']}`"
    L.append(f"## Table 1. Outcomes ({sp}; n per system in column n)")
    L += ["", "| system | n | correct | wrong | abstained | penalised score |", "|---|---|---|---|---|---|"]
    for s, m in sysm.items():
        w = m["wilson"]
        cell = lambda k: f"{_pct(w[k]['p'])} [{_pct(w[k]['lo'])}, {_pct(w[k]['hi'])}]"
        L.append(f"| {s} | {m['n']} | {cell('correct')} | {cell('wrong')} | {cell('abstained')} | "
                 f"{_ci_s(m['penalised_score'])} |")
    L += ["", f"## Table 2. Selective answering ({sp}; AURC over answered questions, lower is better)",
          "", "| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable |",
          "|---|---|---|---|---|---|---|"]
    for s, m in sysm.items():
        u = m["unanswerable"]
        L.append(f"| {s} | {m['n']} | {_pct(m['accuracy'])} | {_pct(m['coverage'])} | "
                 f"{_pct(m['selective_accuracy'])} | {_f(m['aurc'])} | "
                 f"{_pct(u['abstain_rate'])} (n={u['n']}) |")
    L += ["", f"## Table 3. Cost and latency ({sp})", "",
          "| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s, m in sysm.items():
        c, cpc = m["cost"], m["cost_per_correct"]
        cpc_s = "n/a" if cpc["est"] is None else \
            f"{_usd(cpc['est'])} [{_usd(cpc['lo'])}, {_usd(cpc['hi'])}]"
        L.append(f"| {s} | {m['n']} | {_usd(c['mean_usd'])} | {_usd(c['total_usd'])} | {cpc_s} | "
                 f"{_f(m['latency_ms']['median'], 1)} | {_f(m['latency_ms']['p95'], 1)} | "
                 f"{_f(m['mean_calls'], 2)} | {_f(m['mean_searches'], 2)} |")
    L += ["", f"## Table 4. Evidence ({sp}; only questions with known gold units)", "",
          "| system | citation n | citation precision | citation recall | retrieval recall (n) |",
          "|---|---|---|---|---|"]
    for s, m in sysm.items():
        c, r = m["citation"], m["retrieval_recall"]
        L.append(f"| {s} | {c['n'] if c else 'n/a'} | {_f(c['precision'] if c else None)} | "
                 f"{_f(c['recall'] if c else None)} | "
                 f"{_f(r['value'] if r else None)} ({r['n'] if r else 'n/a'}) |")
    L += ["", "Only the engine cites units itself; baselines show retrieval recall only.", ""]
    if res["paired"]:
        L += [f"## Table 5. `{res['reference']}` against each baseline ({sp}; paired on shared questions)",
              "", "Score difference = engine minus baseline (penalised score). McNemar is exact, "
              "two-sided, on correct outcomes; Holm adjusts across the rows below. The oracle is excluded.",
              "", "| baseline | n | score diff | engine only | baseline only | McNemar p | Holm p | min detectable diff |",
              "|---|---|---|---|---|---|---|---|"]
        for s, p in res["paired"].items():
            L.append(f"| {s} | {p['n']} | {_ci_s(p['score_diff'])} | {p['reference_only_correct']} | "
                     f"{p['other_only_correct']} | {_f(p['mcnemar_p'], 4)} | {_f(p['mcnemar_p_holm'], 4)} | "
                     f"{_f(p['min_detectable_diff'])} |")
        L.append("")
    if res["dry_run"]:
        L += [BANNER, ""]
    return "\n".join(L)


def write(out_dir: str, iters: int = 10_000, seed: int = 0) -> dict:
    res = build(out_dir, iters=iters, seed=seed)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)  # banner is the first key
    with open(os.path.join(out_dir, "results.md"), "w", encoding="utf-8") as fh:
        fh.write(render(res) + "\n")
    return res


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m heuresis.bench.report")
    ap.add_argument("out_dir")
    ap.add_argument("--iters", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    write(a.out_dir, a.iters, a.seed)
    print(os.path.join(a.out_dir, "results.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
