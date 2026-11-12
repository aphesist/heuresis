"""The registered analysis of the held-out run (PREREGISTRATION-legal.md, sections 4-6).
Usage: analyse_heldout.py HELDOUT_DIR OUT_JSON   (HELDOUT_DIR holds test/ and temporal_test/ run folders; free)"""
import json
import math
import os
import random
import sys

from heuresis.bench import citations as C
from heuresis.domains import get_domain

root, out = sys.argv[1:3]
SEED, ITERS = 20261112, 5000
covers = get_domain("legal_br").covers
SYS = ["closed_book", "hybrid", "agentic", "agentic+asof", "engine"]
BASE = [s for s in SYS if s != "engine"]


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 4), round(max(0, c - h), 4), round(min(1, c + h), 4)]


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def boot_ci(vals, lo_q=0.025, hi_q=0.975):
    rnd = random.Random(SEED)
    n = len(vals)
    ms = sorted(sum(vals[rnd.randrange(n)] for _ in range(n)) / n for _ in range(ITERS))
    return [round(sum(vals) / n, 4), round(ms[int(lo_q * ITERS)], 4), round(ms[int(hi_q * ITERS) - 1], 4)]


def load(split):
    d = f"{root}/{split}"
    rows = {}
    for l in open(f"{d}/results.jsonl"):
        r = json.loads(l)
        rows[(r["system"], r["qid"])] = r
    an = {}
    for l in open(f"{d}/citations.jsonl"):
        a = json.loads(l)
        an[(a["system"], a["qid"])] = a
    judge = {}
    if os.path.exists(f"{d}/judge.jsonl"):
        for l in open(f"{d}/judge.jsonl"):
            r = json.loads(l)
            judge[(r["system"], r["qid"])] = r["verdict"]
    return rows, an, judge


res = {"sets": {}}
holm_in = []
for split in ("test", "temporal_test"):
    rows, an, judge = load(split)
    qids = sorted({q for (_, q) in rows})
    ok = lambda s, q: (s, q) in rows and rows[(s, q)]["status"] in ("answered", "abstained")
    complete = [q for q in qids if all(ok(s, q) for s in SYS)]
    R = {"questions": len(qids), "complete_cases": len(complete), "errors": {s: sum(1 for q in qids if (s, q) in rows and rows[(s, q)]["status"] == "error") for s in SYS},
         "systems": {}}
    tainted = {}
    useful = {}
    for s in SYS:
        a_ans = [an[(s, q)] for q in complete if an[(s, q)]["status"] == "answered"]
        tn = {q: int(an[(s, q)]["status"] == "answered" and C.is_tainted(an[(s, q)]["analysis"])) for q in complete}
        tc = {q: int(an[(s, q)]["status"] == "answered" and C.is_tainted(an[(s, q)]["analysis"], covers)) for q in complete}
        tainted[s] = tn
        refs = [x for a in a_ans for x in a["analysis"]["refs"]]
        chk = [x for x in refs if x["status"] in ("resolved", "unit_not_found", "container_not_found")]
        res_ = [x for x in refs if x["status"] == "resolved"]
        rr = [rows[(s, q)] for q in complete]
        d = {
            "answered": len(a_ans), "abstained": len(complete) - len(a_ans), "coverage": wilson(len(a_ans), len(complete)),
            "tainted_all": [sum(tn.values()), len(complete), wilson(sum(tn.values()), len(complete))],
            "tainted_answered": [sum(tn.values()), len(a_ans), wilson(sum(tn.values()), len(a_ans))],
            "tainted_covered_only_all": [sum(tc.values()), len(complete), wilson(sum(tc.values()), len(complete))],
            "refs_per_answer": round(len(refs) / len(a_ans), 2) if a_ans else None,
            "norm_not_found": [sum(x["status"] == "container_not_found" for x in refs), len(chk)],
            "article_not_found": [sum(x["status"] == "unit_not_found" for x in refs), len(chk)],
            "article_not_found_stub_container": sum(bool(x["status"] == "unit_not_found" and x["meta"].get("container_incomplete")) for x in refs),
            "not_in_force": [sum(x["in_force"] is False for x in res_), len(res_)],
            "no_reference": [sum(a["analysis"]["n_refs"] == 0 for a in a_ans), len(a_ans)],
            "usd": round(sum(r["usd"] for r in rr), 4), "usd_per_question": round(sum(r["usd"] for r in rr) / len(rr), 5),
            "calls_mean": round(sum(r["calls"] for r in rr) / len(rr), 2), "searches_mean": round(sum(r["searches"] for r in rr) / len(rr), 2),
            "latency_ms_median": sorted(r["ms"] for r in rr)[len(rr) // 2],
        }
        if split == "test":
            u = {q: int(an[(s, q)]["status"] == "answered" and not tn[q] and judge.get((s, q)) == "EQUIVALENT") for q in complete}
            useful[s] = u
            d["equivalent_answers"] = sum(1 for q in complete if judge.get((s, q)) == "EQUIVALENT")
            d["useful"] = [sum(u.values()), len(complete), wilson(sum(u.values()), len(complete))]
            d["usd_per_useful"] = round(d["usd"] / sum(u.values()), 5) if sum(u.values()) else None
        R["systems"][s] = d
    # support shares
    sup = {}
    if os.path.exists(f"{root}/{split}/citation_support.jsonl"):
        for l in open(f"{root}/{split}/citation_support.jsonl"):
            r = json.loads(l)
            if r["verdict"] and r["qid"] in set(complete):
                sup.setdefault(r["system"], []).append(r["verdict"])
    for s in SYS:
        v = sup.get(s, [])
        R["systems"][s]["support"] = [sum(x == "SUPPORTED" for x in v), len(v), wilson(sum(x == "SUPPORTED" for x in v), len(v))]
    if split == "temporal_test":
        tw = C.summarise_temporal([{**an[(s, q)], "kind": rows[(s, q)].get("kind")} for s in SYS for q in complete], None) if False else None
    # primary family
    R["primary"] = {}
    for s in BASE:
        b = sum(1 for q in complete if tainted["engine"][q] and not tainted[s][q])   # engine tainted only
        c = sum(1 for q in complete if tainted[s][q] and not tainted["engine"][q])   # baseline tainted only
        p = mcnemar_exact(b, c)
        diff = [tainted["engine"][q] - tainted[s][q] for q in complete]
        R["primary"][s] = {"engine_only_tainted": b, "baseline_only_tainted": c, "p_raw": p, "diff_engine_minus_baseline": boot_ci(diff)}
        holm_in.append((split, s, p))
    if split == "test":
        R["non_inferiority"] = {}
        for s in BASE:
            diff = [useful["engine"][q] - useful[s][q] for q in complete]
            m, lo95_two, hi = boot_ci(diff)
            m1, lo_one, _ = boot_ci(diff, 0.05, 0.95)
            R["non_inferiority"][s] = {"diff_engine_minus_system": m, "ci95_two_sided": [lo95_two, hi], "lower_one_sided_95": lo_one,
                                       "non_inferior_margin_0.10": lo_one > -0.10}
    res["sets"][split] = R
# Holm over the 8
order = sorted(holm_in, key=lambda t: t[2])
m = len(order)
adj, run = {}, 0.0
for i, (split, s, p) in enumerate(order):
    run = max(run, min(1.0, (m - i) * p))
    adj[(split, s)] = run
for split in res["sets"]:
    for s in BASE:
        res["sets"][split]["primary"][s]["p_holm"] = round(adj[(split, s)], 6)
        res["sets"][split]["primary"][s]["significant_holm_0.05"] = adj[(split, s)] < 0.05
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print("written", out)
