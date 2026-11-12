"""Phase B analysis of a brlaw run folder: citation integrity with Wilson intervals, paired differences,
cost, the engine gate's drops. Usage: analyse.py RUN_DIR FULL_DB CORE_DB OUT_JSON  (free; no model call)."""
import collections
import json
import math
import random
import statistics
import sys

from heuresis.bench import citations as C
from heuresis.domains import get_domain
from heuresis.model import Claim, Passage
from heuresis.references import reference_problems
from heuresis.store import Store

run_dir, full_db, core_db, out = sys.argv[1:5]
rows = [json.loads(l) for l in open(f"{run_dir}/results.jsonl")]
dom = get_domain("legal_br")
covers = dom.covers
an = [json.loads(l) for l in open(f"{run_dir}/citations.jsonl")]
amap = {(a["system"], a["qid"]): a for a in an}
rmap = {(r["system"], r["qid"]): r for r in rows}
systems = sorted({r["system"] for r in rows})
done = set.intersection(*[{r["qid"] for r in rows if r["system"] == s and r["status"] in ("answered", "abstained")} for s in systems])


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 4), round(max(0, c - h), 4), round(min(1, c + h), 4)]


def boot(vals, iters=2000, seed=1):
    rnd = random.Random(seed)
    n = len(vals)
    ms = sorted(sum(vals[rnd.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return [round(sum(vals) / n, 4), round(ms[int(.025 * iters)], 4), round(ms[int(.975 * iters) - 1], 4)]


res = {"complete_cases": len(done), "systems": {}}
for s in systems:
    ra = [amap[(s, q)] for q in sorted(done)]
    ans = [a for a in ra if a["status"] == "answered"]
    refs = [x for a in ans for x in a["analysis"]["refs"]]
    chk = [x for x in refs if x["status"] in ("resolved", "unit_not_found", "container_not_found")]
    resolved = [x for x in refs if x["status"] == "resolved"]
    taint = lambda cov: sum(C.is_tainted(a["analysis"], cov) for a in ans)
    rr = [rmap[(s, q)] for q in sorted(done)]
    d = {
        "n": len(ra), "answered": len(ans), "abstained": len(ra) - len(ans),
        "tainted_strict": [taint(None), len(ans), wilson(taint(None), len(ans))],
        "tainted_covered_only": [taint(covers), len(ans), wilson(taint(covers), len(ans))],
        "refs_per_answer": round(len(refs) / len(ans), 2) if ans else None, "refs": len(refs),
        "container_not_found": [sum(x["status"] == "container_not_found" for x in refs), len(chk)],
        "unit_not_found": [sum(x["status"] == "unit_not_found" for x in refs), len(chk)],
        "unit_not_found_incomplete_container": sum(bool(x["status"] == "unit_not_found" and x["meta"].get("container_incomplete")) for x in refs),
        "resolved_not_in_force": [sum(x["in_force"] is False for x in resolved), len(resolved)],
        "resolved_and_in_force": [sum(x["in_force"] is True for x in resolved), len(chk)],
        "norm_only": sum(x["status"] == "norm_only" for x in refs),
        "no_reference": [sum(a["analysis"]["n_refs"] == 0 for a in ans), len(ans)],
        "usd_per_question": round(sum(r["usd"] for r in rr) / len(rr), 5), "usd_total": round(sum(r["usd"] for r in rr), 4),
        "calls_mean": round(statistics.mean(r["calls"] for r in rr), 2), "searches_mean": round(statistics.mean(r["searches"] for r in rr), 2),
        "latency_ms_median": round(statistics.median(r["ms"] for r in rr)),
        "score_mean": boot([r["score"] for r in rr]) if "score" in rr[0] else None,
        "outcomes": dict(collections.Counter(r["outcome"] for r in rr)),
    }
    res["systems"][s] = d
# paired differences engine - other
st = Store(full_db)
tw = C.summarise_temporal([amap[(s, q)] | {"kind": rmap[(s, q)].get("kind")} for s in systems for q in done], st)
res["temporal_outcomes"] = tw
res["paired_vs_engine"] = {}
for s in systems:
    if s == "engine":
        continue
    t_s = [1.0 if (amap[("engine", q)]["status"] == "answered" and C.is_tainted(amap[("engine", q)]["analysis"])) else 0.0 for q in sorted(done)]
    t_o = [1.0 if (amap[(s, q)]["status"] == "answered" and C.is_tainted(amap[(s, q)]["analysis"])) else 0.0 for q in sorted(done)]
    sc_e = [rmap[("engine", q)].get("score", 0) for q in sorted(done)]
    sc_o = [rmap[(s, q)].get("score", 0) for q in sorted(done)]
    res["paired_vs_engine"][s] = {"tainted_rate_diff_per_question": boot([a - b for a, b in zip(t_s, t_o)]),
                                  "score_diff": boot([a - b for a, b in zip(sc_e, sc_o)])}
# engine gate: re-run it on the stored drafts (offline)
core = Store(core_db)
gate = {"engine_rows": 0, "sentences": 0, "gate_failures": 0, "gate_only_failures": 0, "examples": []}
for q in sorted(done):
    r = rmap[("engine", q)]
    rp = r.get("replay") or {}
    if not rp.get("claims"):
        continue
    gate["engine_rows"] += 1
    ps = [Passage(unit_id=p["unit_id"], seq=p["seq"], text="", title=p["title"], source_id=p["source_id"], mark=p["mark"]) for p in rp["passages"]]
    for c in rp["claims"]:
        gate["sentences"] += 1
        cl = Claim(c["text"], passage_marks=c["passage_marks"])
        cited = [p for p in ps if p.mark in set(c["passage_marks"])]
        bad = [(x, reference_problems(x, cited)) for x in dom.resolve_references(c["text"], core)]
        bad = [(x, w) for x, w in bad if w]
        if bad:
            gate["gate_failures"] += 1
            other_ok = c["checks"]["valid_at_date"] and c["checks"]["numbers_traced"]
            gate["gate_only_failures"] += bool(other_ok)
            if len(gate["examples"]) < 12:
                gate["examples"].append({"qid": q, "sentence": c["text"][:300], "reference": bad[0][0].text, "status": bad[0][0].status,
                                         "why": bad[0][1], "other_checks_pass": bool(other_ok)})
res["engine_gate"] = gate
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({s: {k: v[k] for k in ("answered", "tainted_strict", "tainted_covered_only", "usd_per_question")} for s, v in res["systems"].items()}, indent=1))
print(json.dumps(gate, ensure_ascii=False)[:600]); print(res["paired_vs_engine"]); print(tw)
