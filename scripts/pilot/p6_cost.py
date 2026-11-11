"""Item 6: cost model from the measured dry-run prompt sizes. Pure arithmetic, no model calls.
Assumptions (all stated in docs/pilot-dev.md): tokens = chars / 3.5; 120 output tokens per call;
$0.10 / $0.50 per million input / output tokens; 500 test questions; a request whose prompt
exceeds 100,000 tokens is priced at 5x (input and output); Batch API = 50% off."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa

CPT, OUT_TOK, P_IN, P_OUT, NQ, BIG, MULT = 3.5, 120, 0.10, 0.50, 500, 100_000, 5.0
SINGLE = ("closed_book", "bm25", "vector", "hybrid_rerank", "oracle")  # one call, batchable


def cost_of(call_chars_per_q):
    """call_chars_per_q: list over questions of list of per-call char counts."""
    tot_in = tot_calls = usd = 0.0
    for calls in call_chars_per_q:
        for c in calls:
            t = c / CPT
            m = MULT if t > BIG else 1.0
            usd += m * (t * P_IN + OUT_TOK * P_OUT) / 1e6
            tot_in += t; tot_calls += 1
    n = len(call_chars_per_q)
    return {"tokens_in_per_q": tot_in / n, "calls_per_q": tot_calls / n,
            "usd_per_q": usd / n, "usd_500": usd / n * NQ}


res = {"constants": {"chars_per_token": CPT, "output_tokens_per_call": OUT_TOK, "usd_per_m_in": P_IN,
                     "usd_per_m_out": P_OUT, "questions": NQ, "big_request_tokens": BIG, "big_mult": MULT},
       "datasets": {}}
for d in DATASETS:
    cc = json.load(open(os.path.join(OUT, d, "dryrun", "call_chars.json")))
    by_sys = {}
    for k, v in cc.items():
        s, _ = k.split("|", 1)
        by_sys.setdefault(s, []).append(v)
    ag = json.load(open(os.path.join(OUT, d, "p3b_agentic.json")))
    rows = {}
    for s, lst in by_sys.items():
        if s == "agentic":
            continue  # replaced by the analytic scenarios below
        rows[s] = cost_of(lst)
    # agentic scenarios: need per-question per-call chars; re-derive from stored per-q totals only if present
    for sc in ("1", "2", "4"):
        per_call = ag["searches"][sc].get("per_q_calls")
        rows[f"agentic_{sc}search"] = cost_of(per_call)
    res["datasets"][d] = rows
tot = {}
for d, rows in res["datasets"].items():
    for s, r in rows.items():
        tot[s] = tot.get(s, 0.0) + r["usd_500"]
res["total_three_datasets_usd"] = tot
res["batch_saving_usd"] = {s: 0.5 * tot[s] for s in SINGLE if s in tot}
res["batch_saving_total_usd"] = sum(res["batch_saving_usd"].values())
json.dump(res, open(os.path.join(OUT, "p6_cost.json"), "w"), indent=1)
print(json.dumps(res["total_three_datasets_usd"], indent=1))
