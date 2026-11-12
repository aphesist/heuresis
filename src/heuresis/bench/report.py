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
* an error row (an API or model failure after retries, ``status == "error"``) is read as
  outcome "wrong", score -1, for that system, and the error count is printed per system.
  A restart of the runner retries error rows, so only the ones that remain are counted.
* complete-case analysis: the confirmatory comparisons and the family table use only the
  question ids completed (any row, an error row included) by ALL systems of the
  confirmatory family for that dataset; the report prints that n and the per-system
  completed counts. The per-system tables (1 to 4, 7) use every row of the system.
* paired comparisons pair on those common ids; the engine is the first system in each
  pair. The oracle is a ceiling and is excluded from comparisons.
* primary confirmatory test, on the penalised score: the mean per-question difference
  (engine minus baseline) with a paired bootstrap interval, a two-sided paired sign-flip
  permutation test (cluster-level flips when clusters exist) and its Holm-adjusted
  p-value across every compared baseline of the report. ``family`` repeats the Holm
  adjustment across several reports (datasets). The exact McNemar test on correctness
  is secondary and is kept, with its own Holm adjustment.
* cost per correct answer is also compared as a difference, engine minus baseline, for
  the baselines in ``COST_COMPARE``, with a bootstrap interval that resamples
  questions (or clusters) and keeps each pair together.
* the confirmatory family is the engine against every available system except the
  oracle and except the time-aware variants (suffix ``+asof``). The variants are
  exploratory: they are compared separately, with their own Holm correction, and
  are not part of the confirmatory family.
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
COST_COMPARE = ("agentic", "hybrid")
EXPLORATORY_SUFFIX = "+asof"


def is_exploratory(name: str) -> bool:
    return name.endswith(EXPLORATORY_SUFFIX)


def _as_error_outcome(r: dict) -> dict:
    """An error row read as a wrong answer, with every field the metrics need."""
    row = dict(r)
    row.update({"outcome": "wrong", "correct": False, "score": -1.0, "f1": None})
    row.setdefault("answerable", True)
    row.setdefault("text", "")
    row.setdefault("confidence", 0.0)
    for k in ("usd", "ms", "tokens_in", "tokens_out", "calls", "searches"):
        if row.get(k) is None:
            row[k] = 0
    return row


def load(out_dir: str) -> tuple[dict, list[dict], int]:
    """(manifest, rows, number of error rows). The last row of each (system, question) wins,
    so a retried error is replaced. A remaining error row is kept, as outcome "wrong"
    with ``status == "error"``."""
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
    n_err = sum(1 for r in last.values() if r.get("status") == "error")
    rows = [_as_error_outcome(r) if r.get("status") == "error" else r for r in last.values()]
    return manifest, rows, n_err


def in_family(name: str) -> bool:
    """A system of the confirmatory family (the engine and its baselines)."""
    return name not in EXCLUDED and not is_exploratory(name)


def complete_case(manifest: dict, by: dict[str, list[dict]]) -> dict:
    """The question ids completed by every system of the confirmatory family, and how many
    each system completed. A system the manifest lists as available but that has no row
    counts as having completed none, so the common set is then empty."""
    names = [s["name"] for s in manifest.get("systems", [])
             if s.get("available", True) and in_family(s["name"])]
    names += [s for s in by if in_family(s) and s not in names]
    ids = {s: {r["qid"] for r in by.get(s, [])} for s in names}
    common = set.intersection(*ids.values()) if ids else set()
    return {"systems": names, "common_ids": sorted(common), "n_common": len(common),
            "completed": {s: len(v) for s, v in ids.items()}}


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
    out["errors"] = sum(1 for r in rows if r.get("status") == "error")
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
    stage = [float(r["stage_ms"]) for r in rows if r.get("stage_ms") is not None]
    out["stage_ms_median"] = float(np.median(stage)) if stage else None
    out["mean_answer_chars"] = float(np.mean([len(r.get("text") or "") for r in answered])) if n_ans else None
    out["mean_calls"] = float(np.mean([r["calls"] for r in rows])) if n else None
    out["mean_searches"] = float(np.mean([r["searches"] for r in rows])) if n else None
    out["time_aware"] = bool(rows[0].get("time_aware")) if rows else None
    return out


def paired(ref_rows: list[dict], other_rows: list[dict], iters: int, seed: int,
           cost: bool = False) -> dict | None:
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
    out = {
        "n": n,
        "score_diff": _ci(stats.paired_bootstrap_ci(sa, sb, iters=iters, seed=seed, clusters=_cl(ra))),
        "perm_p": stats.paired_permutation_test(sa, sb, iters=iters, seed=seed, clusters=_cl(ra)),
        "reference_only_correct": only_a, "other_only_correct": only_b,
        "discordance": disc, "mcnemar_p": stats.mcnemar_exact(only_a, only_b),
        "min_detectable_diff": _num(stats.min_detectable_diff(n, disc)) if disc > 0 else None,
    }
    if cost:
        out["cost_per_correct_diff"] = _ci(stats.paired_ratio_diff_ci(
            [float(r["usd"]) for r in ra], [1.0 if c else 0.0 for c in ca],
            [float(r["usd"]) for r in rb], [1.0 if c else 0.0 for c in cb],
            iters=iters, seed=seed, clusters=_cl(ra)))
    return out


def pareto(res: dict) -> dict:
    """Accuracy-cost table: mean cost per question against accuracy and penalised score,
    with a flag for the systems no other system beats on both cost and the measure.
    The oracle (a ceiling) and the exploratory variants are left out."""
    names = [s for s in res["systems"] if s not in EXCLUDED and not is_exploratory(s)]
    rows = {}
    for s in names:
        m = res["systems"][s]
        rows[s] = {"mean_usd": m["cost"]["mean_usd"], "accuracy": m["accuracy"],
                   "penalised_score": m["penalised_score"]["est"]}
    ok = [s for s in names if rows[s]["mean_usd"] is not None and rows[s]["accuracy"] is not None
          and rows[s]["penalised_score"] is not None]
    for key in ("accuracy", "penalised_score"):
        flags = stats.pareto_front([(rows[s]["mean_usd"], rows[s][key]) for s in ok])
        for s in names:
            rows[s][f"pareto_{key}"] = bool(flags[ok.index(s)]) if s in ok else None
    return rows


def build(out_dir: str, iters: int = 10_000, seed: int = 0) -> dict:
    manifest, rows, n_err = load(out_dir)
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["system"], []).append(r)
    order = [s["name"] for s in manifest.get("systems", []) if s["name"] in by]
    order += sorted(set(by) - set(order))
    cc = complete_case(manifest, by)
    common = set(cc["common_ids"])
    res: dict[str, Any] = {
        "banner": BANNER if manifest.get("dry_run") else None,
        "dry_run": bool(manifest.get("dry_run")),
        "dataset": manifest.get("dataset"), "split": manifest.get("split"),
        "n_questions_planned": manifest.get("n_questions"), "error_rows": n_err,
        "complete_case": {k: v for k, v in cc.items() if k != "common_ids"},
        "workers": manifest.get("workers"),
        "locked_hash": manifest.get("locked_hash"), "surface_hash": manifest.get("surface_hash"),
        "prompts_hash": manifest.get("prompts_hash"), "price_table": manifest.get("price_table"),
        "models": manifest.get("models"), "bootstrap_iters": iters, "seed": seed,
        "unavailable": {s["name"]: s["reason"] for s in manifest.get("systems", [])
                        if not s.get("available", True)},
        "systems": {s: system_metrics(by[s], iters, seed) for s in order},
        "paired": {}, "exploratory_paired": {}, "reference": REFERENCE,
        "exploratory_systems": [s for s in order if is_exploratory(s)],
    }
    if REFERENCE in by:
        for key, want in (("paired", False), ("exploratory_paired", True)):
            names, ps = [], []
            for s in order:
                if s == REFERENCE or s in EXCLUDED or is_exploratory(s) != want:
                    continue
                p = paired([r for r in by[REFERENCE] if r["qid"] in common],
                           [r for r in by[s] if r["qid"] in common], iters, seed,
                           cost=(not want and s in COST_COMPARE))
                if p:
                    names.append(s)
                    ps.append(p)
            adj = stats.holm([p["mcnemar_p"] for p in ps])
            adj_perm = stats.holm([p["perm_p"] for p in ps])
            for s, p, q, qp in zip(names, ps, adj, adj_perm):
                p["mcnemar_p_holm"] = q
                p["perm_p_holm"] = qp
                res[key][s] = p
    res["pareto"] = pareto(res)
    jm = judge_metrics(out_dir, by, order, iters, seed)
    if jm:
        res["judge"] = jm
    return res


def judge_metrics(out_dir: str, by: dict[str, list[dict]], order: list[str], iters: int,
                  seed: int) -> dict | None:
    """Secondary, exploratory: the outcomes with the judge's EQUIVALENT verdicts counted as
    correct (``bench.judge``), read from ``judge.jsonl`` beside the results. The primary
    grade in ``systems`` is untouched. ``None`` when there is no judge file."""
    from .judge import load_verdicts
    verd = load_verdicts(out_dir)
    if not verd:
        return None
    out: dict[str, Any] = {}
    for s in order:
        rows = by[s]
        new, flipped, judged, unreadable = [], 0, 0, 0
        for r in rows:
            v = verd.get((s, r["qid"]))
            if v is not None:
                judged += 1
                unreadable += v.get("verdict") is None
            if v is not None and v.get("verdict") == "EQUIVALENT" and r.get("outcome") == "wrong" \
                    and r.get("status") == "answered":
                r = {**r, "outcome": "correct", "correct": True, "score": 1.0}
                flipped += 1
            new.append(r)
        m = system_metrics(new, iters, seed)
        out[s] = {"n": m["n"], "judged": judged, "unreadable": unreadable, "flipped": flipped,
                  "counts": m["counts"], "wilson_correct": m["wilson"]["correct"],
                  "penalised_score": m["penalised_score"]}
    return out


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
        per = ", ".join(f"{s}: {m['errors']}" for s, m in res["systems"].items() if m["errors"])
        L.append(f"Rows with errors (an API or model failure after retries; counted as wrong, "
                 f"retried when the runner restarts): {res['error_rows']} ({per}).")
    cc = res.get("complete_case")
    if cc:
        L.append(f"Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the "
                 f"family table) use the {cc['n_common']} questions completed by all of "
                 f"{', '.join(f'`{s}`' for s in cc['systems'])}. Completed per system: "
                 f"{', '.join(f'{s} {n}' for s, n in cc['completed'].items())}. Tables 1 to 4 and 7 "
                 f"use every question a system completed (column n).")
    for s, why in res["unavailable"].items():
        L.append(f"Not run: `{s}` ({why}).")
    L.append("")
    sysm = {(f"{s} (exploratory)" if is_exploratory(s) else s): m
            for s, m in res["systems"].items()}
    sp = f"split `{res['split']}`"
    L.append(f"## Table 1. Outcomes ({sp}; n per system in column n)")
    L += ["", "| system | n | correct | wrong | abstained | penalised score |", "|---|---|---|---|---|---|"]
    for s, m in sysm.items():
        w = m["wilson"]
        cell = lambda k: f"{_pct(w[k]['p'])} [{_pct(w[k]['lo'])}, {_pct(w[k]['hi'])}]"
        L.append(f"| {s} | {m['n']} | {cell('correct')} | {cell('wrong')} | {cell('abstained')} | "
                 f"{_ci_s(m['penalised_score'])} |")
    jd = res.get("judge")
    if jd:
        L += ["", f"## Table 1b. Secondary, exploratory: judge-assisted grade ({sp})", "",
              "The containment grade of Table 1 is the primary measure and is unchanged. For every answered "
              "row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, "
              "thinking off) was asked whether the answer states the same answer as a gold answer; "
              "EQUIVALENT counts as correct here. The same rule applies to all systems.", "",
              "| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |",
              "|---|---|---|---|---|---|---|"]
        for s, m in sysm.items():
            name = s.replace(" (exploratory)", "")
            j = jd.get(name)
            if not j:
                continue
            w = j["wilson_correct"]
            L.append(f"| {s} | {j['n']} | {j['judged']} | {j['flipped']} | "
                     f"{_pct(w['p'])} [{_pct(w['lo'])}, {_pct(w['hi'])}] | {_ci_s(j['penalised_score'])} | "
                     f"{_ci_s(m['penalised_score'])} |")
    L += ["", f"## Table 2. Selective answering ({sp}; AURC over answered questions, lower is better)",
          "", "| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |",
          "|---|---|---|---|---|---|---|---|"]
    for s, m in sysm.items():
        u = m["unanswerable"]
        L.append(f"| {s} | {m['n']} | {_pct(m['accuracy'])} | {_pct(m['coverage'])} | "
                 f"{_pct(m['selective_accuracy'])} | {_f(m['aurc'])} | "
                 f"{_pct(u['abstain_rate'])} (n={u['n']}) | {_f(m['mean_answer_chars'], 1)} |")
    L += ["", f"## Table 2b. Errors ({sp})", "",
          "An error is an API or model failure after the client's retries. It is counted as a wrong answer "
          "in Table 1 and in every score.", "",
          "| system | n | error rows | of which counted as wrong |", "|---|---|---|---|"]
    for s, m in sysm.items():
        L.append(f"| {s} | {m['n']} | {m['errors']} | {m['errors']} |")
    wk = res.get("workers")
    L += ["", f"## Table 3. Cost and latency ({sp})", "",
          "Latency is wall-clock time around `System.answer`, measured the same way for every system, "
          f"with {wk if wk is not None else 'an unrecorded number of'} concurrent workers: it includes "
          "waiting for the shared model client and for the other workers, so it is indicative only. "
          "The engine's own stage-timing sum is stored separately in each row (`stage_ms`).", "",
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
              "", "Primary test. Score difference = engine minus baseline on the penalised score "
              "(+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a "
              "two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the "
              "family table). The oracle is excluded. Time-aware variants are in Table 6.",
              "", "| baseline | n | score diff | permutation p | Holm p |",
              "|---|---|---|---|---|"]
        for s, p in res["paired"].items():
            L.append(f"| {s} | {p['n']} | {_ci_s(p['score_diff'])} | {_f(p['perm_p'], 4)} | "
                     f"{_f(p['perm_p_holm'], 4)} |")
        L += ["", "Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.",
              "", "| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |",
              "|---|---|---|---|---|---|---|"]
        for s, p in res["paired"].items():
            L.append(f"| {s} | {p['n']} | {p['reference_only_correct']} | "
                     f"{p['other_only_correct']} | {_f(p['mcnemar_p'], 4)} | {_f(p['mcnemar_p_holm'], 4)} | "
                     f"{_f(p['min_detectable_diff'])} |")
        L.append("")
        cc = {s: p["cost_per_correct_diff"] for s, p in res["paired"].items() if "cost_per_correct_diff" in p}
        if cc:
            L += [f"## Table 5b. Cost per correct answer, `{res['reference']}` minus baseline ({sp})", "",
                  "Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the "
                  "engine costs less per correct answer.", "",
                  "| baseline | difference in cost per correct |", "|---|---|"]
            for s, c in cc.items():
                L.append(f"| {s} | {_usd(c['est'])} [{_usd(c['lo'])}, {_usd(c['hi'])}] |")
            L.append("")
    if res.get("exploratory_paired"):
        L += [f"## Table 6. Exploratory: `{res['reference']}` against the time-aware variants "
              f"({sp}; paired on shared questions)",
              "", "The `+asof` systems search as of the question date. They are exploratory: not part "
              "of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.",
              "", "| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |",
              "|---|---|---|---|---|---|---|---|---|"]
        for s, p in res["exploratory_paired"].items():
            L.append(f"| {s} | {p['n']} | {_ci_s(p['score_diff'])} | {_f(p['perm_p'], 4)} | "
                     f"{_f(p['perm_p_holm'], 4)} | {p['reference_only_correct']} | "
                     f"{p['other_only_correct']} | {_f(p['mcnemar_p'], 4)} | "
                     f"{_f(p['min_detectable_diff'])} |")
        L.append("")
    if res.get("pareto"):
        L += [f"## Table 7. Accuracy against cost ({sp})", "",
              "A system is on the frontier for a measure when no other system (oracle and exploratory variants "
              "excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated "
              "price table.", "",
              "| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |",
              "|---|---|---|---|---|---|"]
        yn = lambda v: "n/a" if v is None else ("yes" if v else "no")
        for s, r in res["pareto"].items():
            L.append(f"| {s} | {_usd(r['mean_usd'])} | {_pct(r['accuracy'])} | {yn(r['pareto_accuracy'])} | "
                     f"{_f(r['penalised_score'])} | {yn(r['pareto_penalised_score'])} |")
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


def family(results: Sequence[dict]) -> list[dict]:
    """Holm adjustment of the permutation p-values across several reports (one per
    dataset). Returns one row per (dataset, baseline) of the confirmatory family, each
    with the penalised-score difference, its interval, the permutation p and the
    family-wide Holm p. Time-aware variants are not part of it."""
    rows = [{"dataset": r["dataset"], "baseline": s, "n": p["n"], "score_diff": p["score_diff"],
             "perm_p": p["perm_p"]}
            for r in results for s, p in r["paired"].items()]
    adj = stats.holm([x["perm_p"] for x in rows])
    for x, q in zip(rows, adj):
        x["perm_p_holm_family"] = q
    return rows


def render_family(rows: Sequence[dict], results: Sequence[dict] | None = None) -> str:
    L = [f"# Confirmatory family: {len(rows)} comparisons, Holm across all", "",
         "Penalised score, engine minus baseline; two-sided paired sign-flip permutation test. "
         "Complete-case: each dataset uses only the questions completed by all systems of its "
         "confirmatory family (column n).", ""]
    for r in results or []:
        cc = r.get("complete_case") or {}
        L.append(f"- `{r['dataset']}`: n = {cc.get('n_common')} common questions; completed per system: "
                 f"{', '.join(f'{s} {n}' for s, n in (cc.get('completed') or {}).items())}.")
    if results:
        L.append("")
    L += [
         "| dataset | baseline | n | score diff | permutation p | Holm p (family) |",
         "|---|---|---|---|---|---|"]
    for x in rows:
        L.append(f"| {x['dataset']} | {x['baseline']} | {x['n']} | {_ci_s(x['score_diff'])} | "
                 f"{_f(x['perm_p'], 4)} | {_f(x['perm_p_holm_family'], 4)} |")
    return "\n".join(L) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m heuresis.bench.report")
    ap.add_argument("out_dir", nargs="+", help="one run folder per dataset; with several, a "
                                               "family table with Holm across all is also written")
    ap.add_argument("--iters", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--family-out", default="family.md", help="where the family table goes")
    a = ap.parse_args(argv)
    results = []
    for d in a.out_dir:
        results.append(write(d, a.iters, a.seed))
        print(os.path.join(d, "results.md"))
    if len(results) > 1:
        rows = family(results)
        with open(a.family_out, "w", encoding="utf-8") as fh:
            fh.write(render_family(rows, results))
        print(a.family_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
