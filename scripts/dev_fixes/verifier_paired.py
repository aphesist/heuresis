"""Paired comparison of the candidate supports at the DEFAULT thresholds (0.5, 0.3), per
dataset and pooled, from the cache written by verifier_replay.py. Dev only, no model call.
Usage: HF_HUB_OFFLINE=1 python3 scripts/dev_fixes/verifier_paired.py RUN_ROOT CACHE_JSON"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import verifier_replay as V

root, cache_path = sys.argv[1], sys.argv[2]
items = V.load_rows(root)
cache = json.load(open(cache_path))
scores = [[V.claim_scores(r["replay"], c, cache) for c in r["replay"].get("claims", [])] for d, r, cfg in items]
base = "C1_current"
per = {c: V.penalised(items, scores, c, 0.5, 0.3) for c in V.CANDS}
def counts(xs): return (sum(x == 1 for x in xs), sum(x == -1 for x in xs), sum(x == 0 for x in xs))
rng = random.Random(1)
def ci(xs, it=4000):
    n = len(xs); m = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(it))
    return m[int(.025 * it)], m[int(.975 * it) - 1]
print("counts at (0.5,0.3): correct/wrong/abstained, pooled and per dataset; paired difference vs C1_current [95% CI]")
for c in V.CANDS:
    row = []
    for scope in ("pooled", "musique", "multihoprag", "hoh"):
        idx = [i for i, (d, _, _) in enumerate(items) if scope == "pooled" or d == scope]
        xs = [per[c][i] for i in idx]; ds = [per[c][i] - per[base][i] for i in idx]
        lo, hi = ci(ds)
        row.append(f"{scope}: {counts(xs)} diff {sum(ds)/len(ds):+.3f} [{lo:+.3f},{hi:+.3f}]")
    print(c.ljust(26), " | ".join(row))
print("\nC3t_max_window_title vs C4_lexical (paired):")
for scope in ("pooled", "musique", "multihoprag", "hoh"):
    idx = [i for i, (d, _, _) in enumerate(items) if scope == "pooled" or d == scope]
    ds = [per["C3t_max_window_title"][i] - per["C4_lexical"][i] for i in idx]
    lo, hi = ci(ds); print(f"  {scope}: {sum(ds)/len(ds):+.3f} [{lo:+.3f},{hi:+.3f}]")
