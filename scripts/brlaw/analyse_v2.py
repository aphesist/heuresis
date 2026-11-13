"""Analysis of the second legal comparison (PREREGISTRATION-legal-v2.md, sections 4-7): six systems,
reference ``engine2``. The first run's script, ``analyse_heldout.py``, is left as it was (it reproduces the
registered first run and runs its whole analysis on import, so its functions cannot be imported); the
helpers it defines by hand are the ones ``heuresis.bench.stats`` has (exact McNemar, Holm, Wilson), imported
here, and its seed, resample count and bootstrap quantile rule are repeated unchanged.

Usage: analyse_v2.py RUN_ROOT OUT_JSON [--systems a,b,...] [--reference engine2] [--db STORE.sqlite]
(a root holding several runs skips those without ``citations.jsonl``, e.g. English runs; they are listed under
``skipped_folders``)

RUN_ROOT is one run folder or a folder of run folders (any names; the set is named by the manifest's
``split``, else by the folder name). Each folder is what ``bench.run`` + ``bench.citations`` (+ ``bench.judge``,
optionally ``citation_support.jsonl``) leave behind. Free: nothing here calls a model. ``--db`` is the full corpus
store used for ``bench.citations``; with it the version in force (H4) is scored per question and paired, without it
only the counts of ``citations_summary.json`` are shown. Nothing printed is a question or an answer text.

Per set: complete cases over the systems present; per system coverage, tainted (strict and covered-only), useful
answers (answered, not tainted, judged EQUIVALENT; only when ``judge.jsonl`` exists), cost split into generator and
judge; H3 (exact McNemar of the reference against each baseline and the 1-point non-inferiority against ``engine``,
Holm over that family across all sets); H1 (reference minus every other system, non-inferiority against ``agentic``
with a 3-point margin, superiority over ``engine``, Holm over those two); H6 (cost per useful answer, paired
bootstrap); H4 (dated sets); the reference's gate and judge drops by reason from the rows' ``replay`` payloads."""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import sys
from typing import Any, Callable, Sequence

from heuresis.bench import citations as C
from heuresis.bench import report
from heuresis.bench.stats import holm, mcnemar_exact, wilson_interval

SEED, ITERS = 20261112, 5000
SYSTEMS = ["closed_book", "hybrid", "agentic", "agentic+asof", "engine", "engine2"]
REFERENCE = "engine2"
H3_MARGIN, H1_MARGIN = 0.01, 0.03
V1 = "engine"
FORCE_COMPARATOR = "agentic"       # H1 (i)
H4_COMPARATOR = "agentic+asof"     # H4
CHECK_TEXT = {  # gates.failure_reason texts -> check names (v2/locked/gates.py)
    "a cited mark does not exist or the sentence cites nothing": "exists",
    "a cited provision is not in force at the date": "valid_at_date",
    "a number is not in the cited passages": "numbers_traced",
    "a named reference is not found or not cited": "references_traced",
}


# --------------------------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------------------------


def wilson(k: int, n: int) -> list | None:
    if n == 0:
        return None
    lo, hi = wilson_interval(k, n)
    return [round(k / n, 4), round(lo, 4), round(hi, 4)]


def boot_means(vals: Sequence[float], seed: int = SEED, iters: int = ITERS) -> list[float]:
    rnd = random.Random(seed)
    n = len(vals)
    return sorted(sum(vals[rnd.randrange(n)] for _ in range(n)) / n for _ in range(iters))


def boot_ci(vals: Sequence[float], lo_q: float = 0.025, hi_q: float = 0.975, iters: int = ITERS) -> list | None:
    """[mean, lower, upper] with the first script's quantile rule; None on no data."""
    if not vals:
        return None
    ms = boot_means(vals, iters=iters)
    return [round(sum(vals) / len(vals), 4), round(ms[int(lo_q * iters)], 4), round(ms[int(hi_q * iters) - 1], 4)]


def boot_p_le(vals: Sequence[float], bound: float) -> float | None:
    """One-sided bootstrap p-value for H0: mean <= bound (share of resampled means at or below it, never 0)."""
    if not vals:
        return None
    ms = boot_means(vals)
    return round((1 + sum(m <= bound for m in ms)) / (ITERS + 1), 6)


def boot_p_ge(vals: Sequence[float], bound: float) -> float | None:
    """One-sided bootstrap p-value for H0: mean >= bound."""
    if not vals:
        return None
    ms = boot_means(vals)
    return round((1 + sum(m >= bound for m in ms)) / (ITERS + 1), 6)


def binom_cdf(k: int, n: int) -> float:
    import math
    return sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n if n else 1.0


def ratio_diff_ci(cost_a: Sequence[float], use_a: Sequence[int], cost_b: Sequence[float], use_b: Sequence[int]) -> list | None:
    """Paired bootstrap of (cost / useful answers) of A minus that of B; resamples with no useful answer are skipped."""
    n = len(cost_a)
    if not n or not sum(use_a) or not sum(use_b):
        return None
    rnd = random.Random(SEED)
    ds = []
    for _ in range(ITERS):
        idx = [rnd.randrange(n) for _ in range(n)]
        ua, ub = sum(use_a[i] for i in idx), sum(use_b[i] for i in idx)
        if ua and ub:
            ds.append(sum(cost_a[i] for i in idx) / ua - sum(cost_b[i] for i in idx) / ub)
    if not ds:
        return None
    ds.sort()
    point = sum(cost_a) / sum(use_a) - sum(cost_b) / sum(use_b)
    return [round(point, 5), round(ds[int(0.025 * len(ds))], 5), round(ds[min(len(ds) - 1, int(0.975 * len(ds)))], 5)]


# --------------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------------


def _jsonl(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def discover(root: str) -> list[str]:
    if os.path.exists(os.path.join(root, "results.jsonl")):
        return [root]
    return [os.path.join(root, d) for d in sorted(os.listdir(root))
            if os.path.exists(os.path.join(root, d, "results.jsonl"))]


def load_run(folder: str) -> dict:
    manifest, rows, _ = report.load(folder)
    cpath = os.path.join(folder, C.CITATIONS_FILE)
    if not os.path.exists(cpath):
        raise SystemExit(f"{folder}: no {C.CITATIONS_FILE}; run bench.citations on it first")
    an = {(a["system"], a["qid"]): a for a in _jsonl(cpath)}
    judge: dict = {}
    jp = os.path.join(folder, "judge.jsonl")
    has_judge = os.path.exists(jp)
    if has_judge:
        judge = {(r["system"], r["qid"]): r.get("verdict") for r in _jsonl(jp)}
    support: dict = {}
    sp = os.path.join(folder, C.SUPPORT_FILE)
    if os.path.exists(sp):
        for r in _jsonl(sp):
            support.setdefault((r["system"], r["qid"]), []).append(r.get("verdict"))
    summary: dict = {}
    smp = os.path.join(folder, C.SUMMARY_FILE)
    if os.path.exists(smp):
        with open(smp, encoding="utf-8") as fh:
            summary = json.load(fh)
    return {"folder": folder, "manifest": manifest, "rows": {(r["system"], r["qid"]): r for r in rows},
            "an": an, "judge": judge, "has_judge": has_judge, "support": support, "summary": summary}


def set_name(run: dict) -> str:
    return str(run["manifest"].get("split") or os.path.basename(os.path.normpath(run["folder"])))


# --------------------------------------------------------------------------------------------
# Replay payload of the reference system
# --------------------------------------------------------------------------------------------


def _category(reason: str, claim: dict | None) -> str:
    if reason.startswith("withheld"):
        return "withheld (answer not given)"
    checks = (claim or {}).get("checks") or {}
    failed = [c for c, ok in checks.items() if not ok]
    if failed:
        return "gate: " + "+".join(sorted(failed))
    for text, name in CHECK_TEXT.items():
        if text in reason:
            return "gate: " + name
    if (claim is not None and claim.get("label") == "unsupported") or "judge" in reason:
        return "judge: unsupported"
    return "other"


def replay_summary(rows: Sequence[dict]) -> dict:
    """Gate and judge drops by reason from ``replay.claims[*].checks/note`` and ``replay.meta`` (no passage text)."""
    out: dict[str, Any] = {"rows_with_replay": 0, "rows": len(rows)}
    status, abst = collections.Counter(), collections.Counter()
    labels, fails, reasons = collections.Counter(), collections.Counter(), collections.Counter()
    verdict = {"answer": collections.Counter(), "sufficient": collections.Counter()}
    raw = collections.Counter()
    dropped = claims_n = below = escalated = repairs = 0
    for r in rows:
        rp = r.get("replay")
        if not isinstance(rp, dict):
            continue
        out["rows_with_replay"] += 1
        status[rp.get("status")] += 1
        if rp.get("abstention"):
            abst[rp["abstention"]] += 1
        below += bool(rp.get("below_tau"))
        meta = rp.get("meta") or {}
        escalated += bool(meta.get("escalated"))
        repairs += int(meta.get("repairs") or 0)
        v = meta.get("verdict") or {}
        for k in verdict:
            if v.get(k):
                verdict[k][v[k]] += 1
        cl = rp.get("claims") or []
        claims_n += len(cl)
        by_text = {c.get("text"): c for c in cl}
        for c in cl:
            labels[c.get("label")] += 1
            for name, ok in (c.get("checks") or {}).items():
                if not ok:
                    fails[name] += 1
        for d in meta.get("dropped") or []:
            dropped += 1
            reason = str(d.get("reason", ""))
            reasons[_category(reason, by_text.get(d.get("text")))] += 1
            raw[reason[:60]] += 1
    out.update({"status": dict(status), "abstention_types": dict(abst), "below_tau": below,
                "claims": claims_n, "claim_labels": dict(labels), "claims_failing_check": dict(fails),
                "dropped_claims": dropped, "dropped_by_reason": dict(reasons.most_common()),
                "dropped_reason_texts_top10": dict(raw.most_common(10)),
                "judge_verdicts": {k: dict(v) for k, v in verdict.items()},
                "escalated": escalated, "repairs_total": repairs})
    return out


def judge_usd(row: dict) -> float | None:
    rp = row.get("replay")
    if not isinstance(rp, dict):
        return None
    st = (rp.get("raw_usage_by_stage") or {}).get("judge")
    return float(st.get("usd", 0.0)) if st else 0.0


# --------------------------------------------------------------------------------------------
# Dated questions (H4)
# --------------------------------------------------------------------------------------------


def temporal_flags(run: dict, systems: Sequence[str], complete: Sequence[str], store: Any) -> dict[str, dict[str, str]]:
    """Per system and question, ``C.temporal_outcome`` computed from the run's answer text and citation analysis."""
    out: dict[str, dict[str, str]] = {s: {} for s in systems}
    for s in systems:
        for q in complete:
            a, r = run["an"][(s, q)], run["rows"][(s, q)]
            row = {"status": a["status"], "answerable": a.get("answerable", True), "cluster": a.get("cluster", ""),
                   "gold_units": a.get("gold_units") or [], "analysis": a["analysis"], "text": r.get("text", "")}
            out[s][q] = C.temporal_outcome(row, store)["outcome"]
    return out


def h4(run: dict, systems: Sequence[str], complete: Sequence[str], ref: str, store: Any) -> dict:
    cmp_ = H4_COMPARATOR
    if store is None:
        counts = (run["summary"].get("temporal") or {})
        return {"paired": False, "note": "no --db: counts of citations_summary.json (all rows, unpaired), no test",
                "outcomes": counts}
    flags = temporal_flags(run, systems, complete, store)
    out: dict[str, Any] = {"paired": True, "outcomes": {s: dict(collections.Counter(flags[s].values())) for s in systems}}
    if cmp_ in flags and ref in flags:
        g = {s: [int(flags[s][q] == "gold_version") for q in complete] for s in (ref, cmp_)}
        b = sum(1 for x, y in zip(g[ref], g[cmp_]) if x and not y)   # reference only
        c = sum(1 for x, y in zip(g[ref], g[cmp_]) if y and not x)   # comparator only
        fewer = sum(g[ref]) < sum(g[cmp_])
        p_fewer = binom_cdf(b, b + c)
        out["vs_" + cmp_] = {
            "gold_version": {ref: sum(g[ref]), cmp_: sum(g[cmp_]), "n": len(complete)},
            "reference_only": b, "comparator_only": c, "p_mcnemar_two_sided": mcnemar_exact(b, c),
            "p_one_sided_reference_fewer": round(p_fewer, 6),
            "diff_reference_minus_comparator": boot_ci([x - y for x, y in zip(g[ref], g[cmp_])]),
            "superseded_wording": {s: sum(flags[s][q] == "other_version" for q in complete) for s in (ref, cmp_)},
            "h4_not_supported": bool(fewer and p_fewer < 0.05)}
    return out


# --------------------------------------------------------------------------------------------
# One set
# --------------------------------------------------------------------------------------------


def analyse_set(run: dict, systems: Sequence[str], ref: str, covers: Callable | None, store: Any = None) -> dict:
    rows, an, judge = run["rows"], run["an"], run["judge"]
    present = [s for s in systems if any(k[0] == s for k in rows)]
    missing = [s for s in systems if s not in present]
    if ref not in present:
        raise SystemExit(f"{run['folder']}: the reference system {ref!r} has no rows")
    qids = sorted({q for (_, q) in rows})
    ok = lambda s, q: (s, q) in rows and rows[(s, q)]["status"] in ("answered", "abstained") and (s, q) in an
    complete = [q for q in qids if all(ok(s, q) for s in present)]
    R: dict[str, Any] = {"folder": run["folder"], "questions": len(qids), "complete_cases": len(complete),
                         "systems_present": present, "systems_missing": missing,
                         "errors": {s: sum(1 for q in qids if (s, q) in rows and rows[(s, q)]["status"] == "error") for s in present},
                         "systems": {}}
    R["error_flag_over_2pct"] = [s for s in present if qids and R["errors"][s] / len(qids) > 0.02]
    if not complete:
        R["note"] = "no complete case; nothing else computed"
        return R
    tainted, tcov, useful, cost_gen, cost_judge = {}, {}, {}, {}, {}
    for s in present:
        a_ans = [an[(s, q)] for q in complete if an[(s, q)]["status"] == "answered"]
        tn = {q: int(an[(s, q)]["status"] == "answered" and C.is_tainted(an[(s, q)]["analysis"])) for q in complete}
        tc = {q: int(an[(s, q)]["status"] == "answered" and C.is_tainted(an[(s, q)]["analysis"], covers)) for q in complete}
        tainted[s], tcov[s] = tn, tc
        refs = [x for a in a_ans for x in a["analysis"]["refs"]]
        chk = [x for x in refs if x["status"] in ("resolved", "unit_not_found", "container_not_found")]
        res_ = [x for x in refs if x["status"] == "resolved"]
        rr = [rows[(s, q)] for q in complete]
        n = len(complete)
        usd = sum(r["usd"] for r in rr)
        jd = [judge_usd(r) for r in rr]
        j_known = s == ref and all(x is not None for x in jd)
        cost_judge[s] = [x or 0.0 for x in jd] if s == ref else [0.0] * n
        cost_gen[s] = [r["usd"] - j for r, j in zip(rr, cost_judge[s])]
        d: dict[str, Any] = {
            "answered": len(a_ans), "abstained": n - len(a_ans), "coverage": wilson(len(a_ans), n),
            "tainted_all": [sum(tn.values()), n, wilson(sum(tn.values()), n)],
            "tainted_answered": [sum(tn.values()), len(a_ans), wilson(sum(tn.values()), len(a_ans))],
            "tainted_covered_only_all": [sum(tc.values()), n, wilson(sum(tc.values()), n)],
            "refs_per_answer": round(len(refs) / len(a_ans), 2) if a_ans else None,
            "norm_not_found": [sum(x["status"] == "container_not_found" for x in refs), len(chk)],
            "article_not_found": [sum(x["status"] == "unit_not_found" for x in refs), len(chk)],
            "not_in_force": [sum(x["in_force"] is False for x in res_), len(res_)],
            "no_reference": [sum(a["analysis"]["n_refs"] == 0 for a in a_ans), len(a_ans)],
            "usd": round(usd, 4), "usd_per_question": round(usd / n, 5),
            "usd_generator": round(sum(cost_gen[s]), 4), "usd_judge": round(sum(cost_judge[s]), 4) if (s != ref or j_known) else None,
            "usd_per_question_generator": round(sum(cost_gen[s]) / n, 5),
            "usd_per_question_judge": round(sum(cost_judge[s]) / n, 5) if (s != ref or j_known) else None,
            "calls_mean": round(sum(r.get("calls", 0) for r in rr) / n, 2),
            "searches_mean": round(sum(r.get("searches", 0) for r in rr) / n, 2),
            "latency_ms_median": sorted(r.get("ms", 0) for r in rr)[n // 2],
        }
        if run["has_judge"]:
            u = {q: int(an[(s, q)]["status"] == "answered" and not tn[q] and judge.get((s, q)) == "EQUIVALENT") for q in complete}
            useful[s] = u
            d["equivalent_answers"] = sum(1 for q in complete if judge.get((s, q)) == "EQUIVALENT")
            d["useful"] = [sum(u.values()), n, wilson(sum(u.values()), n)]
            d["usd_per_useful"] = round(usd / sum(u.values()), 5) if sum(u.values()) else None
            d["usd_per_useful_generator"] = round(sum(cost_gen[s]) / sum(u.values()), 5) if sum(u.values()) else None
            d["usd_per_useful_judge"] = round(sum(cost_judge[s]) / sum(u.values()), 5) if sum(u.values()) and (s != ref or j_known) else None
        sv = [v for q in complete for v in run["support"].get((s, q), []) if v]
        d["support"] = [sum(x == "SUPPORTED" for x in sv), len(sv), wilson(sum(x == "SUPPORTED" for x in sv), len(sv))]
        R["systems"][s] = d

    others = [s for s in present if s != ref]
    baselines = [s for s in others if s != V1]
    prim: dict[str, Any] = {}
    for variant, T in (("strict", tainted), ("covered_only", tcov)):
        block: dict[str, Any] = {}
        for s in others:
            b = sum(1 for q in complete if T[ref][q] and not T[s][q])   # reference tainted only
            c = sum(1 for q in complete if T[s][q] and not T[ref][q])   # other tainted only
            block[s] = {"reference_only_tainted": b, "other_only_tainted": c, "p_raw": mcnemar_exact(b, c),
                        "diff_reference_minus_other": boot_ci([T[ref][q] - T[s][q] for q in complete]),
                        "in_holm_family": variant == "strict" and s in baselines}
        prim[variant] = block
    if V1 in present:
        for variant, T in (("strict", tainted), ("covered_only", tcov)):
            diff = [T[ref][q] - T[V1][q] for q in complete]
            upper = boot_ci(diff, 0.05, 0.95)[2]
            prim[variant][V1]["non_inferiority"] = {
                "upper_one_sided_95": upper, "margin": H3_MARGIN, "non_inferior": upper < H3_MARGIN,
                "p_one_sided": boot_p_ge(diff, H3_MARGIN), "in_holm_family": variant == "strict"}
    R["tainted"] = prim

    if run["has_judge"]:
        R["useful_diffs"] = {}
        for s in others:
            diff = [useful[ref][q] - useful[s][q] for q in complete]
            R["useful_diffs"][s] = {"diff_reference_minus_system": boot_ci(diff),
                                    "lower_one_sided_95": boot_ci(diff, 0.05, 0.95)[1]}
        h1: dict[str, Any] = {}
        pvals = []
        if FORCE_COMPARATOR in present:
            diff = [useful[ref][q] - useful[FORCE_COMPARATOR][q] for q in complete]
            lo = boot_ci(diff, 0.05, 0.95)[1]
            h1["non_inferior_to_" + FORCE_COMPARATOR] = {"lower_one_sided_95": lo, "margin": -H1_MARGIN, "holds": lo > -H1_MARGIN,
                                                         "p_one_sided": boot_p_le(diff, -H1_MARGIN)}
            pvals.append(("non_inferior_to_" + FORCE_COMPARATOR, h1["non_inferior_to_" + FORCE_COMPARATOR]["p_one_sided"]))
        if V1 in present:
            diff = [useful[ref][q] - useful[V1][q] for q in complete]
            ci = boot_ci(diff)
            h1["superior_to_" + V1] = {"diff_ci95": ci, "holds": ci[1] > 0, "p_one_sided": boot_p_le(diff, 0.0)}
            pvals.append(("superior_to_" + V1, h1["superior_to_" + V1]["p_one_sided"]))
        for (name, _), adj in zip(pvals, holm([p for _, p in pvals])):
            h1[name]["p_holm"] = round(adj, 6)
        R["h1"] = h1
        h6: dict[str, Any] = {}
        for s in (V1, FORCE_COMPARATOR):
            if s in present:
                h6[f"{ref}_minus_{s}"] = {
                    "usd_per_useful_diff": ratio_diff_ci([r["usd"] for r in (rows[(ref, q)] for q in complete)],
                                                        [useful[ref][q] for q in complete],
                                                        [r["usd"] for r in (rows[(s, q)] for q in complete)],
                                                        [useful[s][q] for q in complete])}
        R["h6"] = h6
    if set_name(run).startswith("temporal"):
        R["h4"] = h4(run, present, complete, ref, store)
    R["reference_replay"] = replay_summary([rows[(ref, q)] for q in complete])
    return R


# --------------------------------------------------------------------------------------------
# Whole analysis
# --------------------------------------------------------------------------------------------


def analyse(root: str, systems: Sequence[str] = SYSTEMS, ref: str = REFERENCE, store: Any = None,
            covers: Callable | None = None) -> dict:
    if covers is None:
        from heuresis.domains import get_domain
        covers = get_domain("legal_br").covers
    folders = discover(root)
    if not folders:
        raise SystemExit(f"{root}: no run folder (a folder with results.jsonl)")
    res: dict[str, Any] = {"reference": ref, "systems": list(systems), "sets": {}, "seed": SEED, "bootstrap_iters": ITERS,
                           "skipped_folders": []}
    if len(folders) > 1:   # a root holding other runs too (English datasets, ablations): only those with citations are legal runs
        res["skipped_folders"] = [f for f in folders if not os.path.exists(os.path.join(f, C.CITATIONS_FILE))]
        folders = [f for f in folders if f not in res["skipped_folders"]]
        if not folders:
            raise SystemExit(f"{root}: no run folder with {C.CITATIONS_FILE}; run bench.citations first")
    for f in folders:
        run = load_run(f)
        name = set_name(run)
        if name in res["sets"]:
            name = os.path.basename(os.path.normpath(f))
        res["sets"][name] = analyse_set(run, systems, ref, covers, store)
    # Holm over the H3 family: every baseline's McNemar and the non-inferiority against v1, on every set
    fam = []
    for name, R in res["sets"].items():
        strict = (R.get("tainted") or {}).get("strict", {})
        for s, v in strict.items():
            if v.get("in_holm_family"):
                fam.append((name, s, "p_raw", v))
            if "non_inferiority" in v:
                fam.append((name, s, "non_inferiority", v["non_inferiority"]))
    pv = [(v["p_raw"] if k == "p_raw" else v["p_one_sided"]) for _, _, k, v in fam]
    adj = holm([p for p in pv if p is not None]) if pv else []
    it = iter(adj)
    for (name, s, k, v), p in zip(fam, pv):
        if p is None:
            continue
        a = round(next(it), 6)
        v["p_holm"] = a
        v["significant_holm_0.05"] = a < 0.05
        if k == "p_raw":
            ref_rate = res["sets"][name]["systems"][ref]["tainted_all"][0]
            oth_rate = res["sets"][name]["systems"][s]["tainted_all"][0]
            v["reference_tainted_lower"] = ref_rate < oth_rate
    res["holm_family_size"] = len(adj)
    return res


def summary_lines(res: dict) -> list[str]:
    out = []
    for name, R in res["sets"].items():
        out.append(f"set {name}: {R['complete_cases']} complete cases of {R['questions']}; systems {', '.join(R['systems_present'])}"
                   + (f"; missing {', '.join(R['systems_missing'])}" if R["systems_missing"] else ""))
        for s, d in R.get("systems", {}).items():
            u = f" useful {d['useful'][0]}" if "useful" in d else ""
            out.append(f"  {s:13s} answered {d['answered']:4d} tainted {d['tainted_all'][0]:3d}{u}  US${d['usd_per_question']:.5f}/question")
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analysis of the six-system legal comparison (free).")
    ap.add_argument("run_root")
    ap.add_argument("out_json")
    ap.add_argument("--systems", default=",".join(SYSTEMS))
    ap.add_argument("--reference", default=REFERENCE)
    ap.add_argument("--db", default=None, help="the full corpus store of bench.citations; scores H4 per question")
    a = ap.parse_args(argv)
    store = None
    if a.db:
        from heuresis.store import Store
        store = Store(a.db)
    try:
        res = analyse(a.run_root, [s for s in a.systems.split(",") if s], a.reference, store)
    finally:
        if store is not None:
            store.close()
    with open(a.out_json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("\n".join(summary_lines(res)))
    print("written", a.out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
