"""Side-by-side: thinking disabled (main1) vs thinking default with a 4096-token cap
(thinking-default). Dev only; reads run folders. Usage: python3 thinking_compare.py RUN_ROOT"""
import collections, json, os, random, sys

B = sys.argv[1]
DS = ["musique", "multihoprag", "hoh"]
SYS = ["closed_book", "bm25", "hybrid", "hybrid+asof", "agentic", "engine"]
COND = {"off": "main1", "default": "thinking-default"}


def rows(cfg, d):
    p = f"{B}/{cfg}/{d}/results.jsonl"
    last = {}
    for l in open(p):
        r = json.loads(l); last[(r["system"], r["qid"])] = r
    return last


def verdicts(cfg, d):
    p = f"{B}/{cfg}/{d}/judge.jsonl"
    out = {}
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l); out[(r["system"], r["qid"])] = r.get("verdict")
    return out


def with_judge(r, v):
    if v is not None and v == "EQUIVALENT" and r["outcome"] == "wrong" and r["status"] == "answered":
        return {**r, "outcome": "correct", "score": 1.0}
    return r


def boot(xs, it=2000, seed=0):
    rng = random.Random(seed); n = len(xs)
    m = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(it))
    return m[int(.025 * it)], m[int(.975 * it) - 1]


data = {}
for c, cfg in COND.items():
    for d in DS:
        R = rows(cfg, d); V = verdicts(cfg, d)
        for (s, q), r in R.items():
            data[(c, d, s, q)] = (r, with_judge(r, V.get((s, q))))
out = []; P = out.append
cnt = lambda L, k: sum(x["outcome"] == k for x in L)
P("## Thinking disabled (main1) vs thinking default with a 4096-token cap: per dataset and system (n = 100)\n")
P("c/w/a = correct / wrong / abstained under the containment grade; pen = penalised score (c - w)/n; J = the same with the judge-assisted grade.\n")
P("| dataset | system | off: c/w/a | off: pen | off: pen J | default: c/w/a | default: pen | default: pen J |\n|---|---|---|---|---|---|---|---|")


def cell(c, d, s, pooled=False):
    L = [v for (cc, dd, ss, q), v in data.items() if cc == c and ss == s and (pooled or dd == d)]
    if not L: return ("-", "-", "-")
    P0 = [a for a, b in L]; J0 = [b for a, b in L]; n = len(L)
    return (f"{cnt(P0,'correct')}/{cnt(P0,'wrong')}/{cnt(P0,'abstained')}", f"{(cnt(P0,'correct')-cnt(P0,'wrong'))/n:+.3f}", f"{(cnt(J0,'correct')-cnt(J0,'wrong'))/n:+.3f}")


for d in DS + ["pooled"]:
    for s in SYS:
        cells = [cell(c, d, s, d == "pooled") for c in COND]
        P(f"| {d} | {s} | {' | '.join(cells[0])} | {' | '.join(cells[1])} |")

P("\n## Paired differences (penalised score, engine minus system, per question) under each condition [95% bootstrap CI]; primary grade and judge-assisted grade\n")
P("| scope | pair | off primary | off judge | default primary | default judge |\n|---|---|---|---|---|---|")
for scope in DS + ["pooled"]:
    for other in ("hybrid", "agentic"):
        res = {}
        for grade in (0, 1):
            for c in COND:
                diffs = []
                for d in (DS if scope == "pooled" else [scope]):
                    for (cc, dd, s, q), v in data.items():
                        if cc == c and dd == d and s == "engine" and (c, d, other, q) in data:
                            diffs.append(v[grade]["score"] - data[(c, d, other, q)][grade]["score"])
                lo, hi = boot(diffs) if diffs else (0, 0)
                res[(grade, c)] = f"{sum(diffs)/max(len(diffs),1):+.3f} [{lo:+.3f}, {hi:+.3f}]"
        P(f"| {scope} | engine - {other} | {res[(0,'off')]} | {res[(1,'off')]} | {res[(0,'default')]} | {res[(1,'default')]} |")

P("\n## Cost, tokens and truncation (pooled over the three datasets)\n")
P("| system | condition | $/question | $/correct (primary) | output tokens / call | visible tokens / call (chars/3.5) | hidden share | replies cut at the cap | calls |\n|---|---|---|---|---|---|---|---|---|")
for s in SYS:
    for c in COND:
        L = [v[0] for (cc, dd, ss, q), v in data.items() if cc == c and ss == s]
        if not L: continue
        n = len(L); calls = sum(r["calls"] for r in L); usd = sum(r["usd"] for r in L)
        tout = sum(r["tokens_out"] for r in L); vis = sum(r.get("text_chars", 0) for r in L) / 3.5
        cut = sum(z == "max_tokens" for r in L for z in r.get("stop_reasons", []))
        corr = cnt(L, "correct")
        P(f"| {s} | {c} | {usd/n:.5f} | {usd/corr if corr else float('nan'):.5f} | {tout/calls:.0f} | {vis/calls:.0f} | {max(0,1-vis/tout):.0%} | {cut} | {calls} |")
print("\n".join(out))
