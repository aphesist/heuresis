"""Phase 2 analysis of the dev re-run with the fixes (dev only; reads run folders and the ledger).
Usage: python3 scripts/dev_fixes/phase2_analysis.py RUN_ROOT [LEDGER] > analysis.md"""
import collections, json, os, random, re, statistics as st, sys

B = sys.argv[1]
LEDGER = sys.argv[2] if len(sys.argv) > 2 else "runs/dev-calibration/ledger.jsonl"
DS = ["musique", "multihoprag", "hoh"]
STEP0_TS = "2026-11-12T03:19:00Z"
out = []
P = out.append


def rows(cfg, d, system=None):
    p = f"{B}/{cfg}/{d}/results.jsonl"
    if not os.path.exists(p):
        return []
    R = [json.loads(l) for l in open(p)]
    return [r for r in R if system is None or r["system"] == system]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower().replace("-", " ")).strip()


def boot(xs, it=2000, seed=0):
    rng = random.Random(seed); n = len(xs)
    m = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(it))
    return m[int(.025 * it)], m[int(.975 * it) - 1]


led = [json.loads(l) for l in open(LEDGER)]
new = [x for x in led if x["ts"] >= STEP0_TS]
P(f"## Spend\n\nLedger total ${sum(x['usd'] for x in led):.4f} over {len(led)} calls; this phase (from step 0) ${sum(x['usd'] for x in new):.4f} over {len(new)} calls.\n")
P("| tag | calls | tokens in | tokens out | USD | hidden-output share | calls cut at max_tokens | stop reasons |\n|---|---|---|---|---|---|---|---|")
by = collections.defaultdict(list)
for x in new:
    by[x["tag"]].append(x)
for t, v in sorted(by.items(), key=lambda kv: -sum(x["usd"] for x in kv[1])):
    tout = sum(x["tokens_out"] for x in v)
    vis = sum(x.get("text_chars", 0) for x in v) / 3.5
    cut = sum(x.get("stop_reason") == "max_tokens" for x in v)
    sr = dict(collections.Counter(x.get("stop_reason", "?") for x in v))
    blocks = collections.Counter(b for x in v for b in x.get("blocks", {}))
    P(f"| {t} | {len(v)} | {sum(x['tokens_in'] for x in v)} | {tout} | {sum(x['usd'] for x in v):.4f} | "
      f"{max(0, 1 - vis / tout) if tout else 0:.0%} | {cut} | {sr} {dict(blocks)} |")
P("\nHidden-output share = 1 - (visible characters / 3.5) / billed output tokens. A share above 0 on a system without thinking blocks is the CONFIDENCE line and format tokens.\n")

# per-dataset tables for main1 (and main2 summary)
for cfg in ("main1",):
    for d in DS:
        R = rows(cfg, d)
        js = json.load(open(f"{B}/{cfg}/{d}/results.json"))
        jd = js.get("judge") or {}
        P(f"\n## {d} (dev, n=100): {cfg}\n")
        P("| system | n | correct | wrong | abstained | errors | penalised [95% CI] | accuracy | coverage | $/q | $/correct | median ms | calls | ans chars | tok in/q | tok out/q | judge: flipped | correct (judge) | penalised (judge) |\n|" + "---|" * 19)
        order = list(dict.fromkeys(list(js["systems"]) + list(js.get("exploratory_systems", []))))
        for s in order:
            v = [r for r in R if r["system"] == s]
            if not v: continue
            n = len(v); c = sum(x["outcome"] == "correct" for x in v); w = sum(x["outcome"] == "wrong" for x in v)
            ps = js["systems"][s]["penalised_score"]; usd = sum(x["usd"] for x in v)
            j = jd.get(s)
            jc = f"{j['flipped']} | {j['counts']['correct']} | {j['penalised_score']['est']:.3f} [{j['penalised_score']['lo']:.3f}, {j['penalised_score']['hi']:.3f}]" if j else "- | - | -"
            P(f"| {s} | {n} | {c} | {w} | {n-c-w} | {sum(x['status']=='error' for x in v)} | {ps['est']:.3f} [{ps['lo']:.3f}, {ps['hi']:.3f}] | {c/n:.2f} | {(c+w)/n:.2f} | {usd/n:.5f} | {(usd/c if c else float('nan')):.5f} | {st.median(x['ms'] for x in v):.0f} | {sum(x['calls'] for x in v)/n:.2f} | {sum(len(x['text'] or '') for x in v)/n:.0f} | {sum(x['tokens_in'] for x in v)/n:.0f} | {sum(x['tokens_out'] for x in v)/n:.0f} | {jc} |")

# engine analysis, main1
P("\n## Engine (main1)\n")
ex_rej, ex_acc = [], []
for d in DS:
    E = rows("main1", d, "engine"); H = {r["qid"]: r for r in rows("main1", d, "hybrid")}
    n = len(E)
    ab = collections.Counter(r["replay"].get("abstention") for r in E if r["outcome"] == "abstained")
    own = sum(1 for r in E if r["outcome"] == "abstained" and not r["replay"].get("claims"))
    ver = sum(1 for r in E if r["outcome"] == "abstained" and r["replay"].get("claims"))
    cut = sum(1 for r in E if "max_tokens" in r.get("stop_reasons", []))
    c = sum(r["outcome"] == "correct" for r in E); w = sum(r["outcome"] == "wrong" for r in E)
    P(f"**{d}**: correct {c}, wrong {w}, abstained {n-c-w}. Abstention types {dict(ab)}; the draft's own ABSTAIN (no claim): {own}; rejected after claim verification: {ver}; rows with a reply cut at the cap: {cut}.")
    b = sum(1 for r in E if r["outcome"] == "correct" and H[r["qid"]]["outcome"] != "correct")
    cc = sum(1 for r in E if r["outcome"] != "correct" and H[r["qid"]]["outcome"] == "correct")
    both = sum(1 for r in E if r["outcome"] == "correct" and H[r["qid"]]["outcome"] == "correct")
    P(f"  Engine vs hybrid correctness: engine-only {b}, hybrid-only {cc}, both {both}; discordance (b+c)/n = {(b+cc)/n:.2f}.")
    for r in E:
        rp = r["replay"]; gold = [norm(a) for a in rp.get("answers") or [] if a]; dr = norm(rp.get("draft_raw"))
        sc = [(round(c_["support"], 3), c_["text"][:110]) for c_ in rp.get("claims", [])]
        if r["outcome"] == "abstained" and rp.get("claims") and gold and any(g and g in dr for g in gold) \
                and all(c_["checks"].get("exists") for c_ in rp["claims"]):
            ex_rej.append((d, r["qid"], rp["answers"][:2], rp.get("abstention"), sc))
        if r["outcome"] == "wrong":
            ex_acc.append((d, r["qid"], rp["answers"][:2], (r["text"] or "")[:150], sc))
pick = lambda L: L if len(L) <= 5 else [L[i] for i in (0, len(L) // 4, len(L) // 2, 3 * len(L) // 4, len(L) - 1)]
P(f"\n### (i) Correct answer rejected after verification (dev; the draft contains a gold string, no truncated claim): {len(ex_rej)} cases; five shown\n")
for e in pick(ex_rej): P(f"- {e[0]} `{e[1]}` gold {e[2]}; `{e[3]}`; claims (support, text): {e[4]}")
P(f"\n### (ii) Wrong answer accepted (dev): {len(ex_acc)} cases; five shown\n")
for e in pick(ex_acc): P(f"- {e[0]} `{e[1]}` gold {e[2]}; \"{e[3]}\"; claims (support, text): {e[4]}")

# arms vs main1 engine
P("\n## Engine A/B arms against main1 (paired per question; penalised-score difference arm - main1 [95% bootstrap CI]; counts correct/wrong/abstained)\n")
P("| arm | scope | main1 engine | arm | difference | calls/q (arm) | USD/q (arm) |\n|---|---|---|---|---|---|---|")
for arm in ("armA-v1", "armB-answersq"):
    for scope in ["pooled"] + DS:
        ds_ = DS if scope == "pooled" else [scope]
        a, m = [], []
        for d in ds_:
            A = {r["qid"]: r for r in rows(arm, d, "engine")}; M = {r["qid"]: r for r in rows("main1", d, "engine")}
            for q in M:
                if q in A: a.append(A[q]); m.append(M[q])
        if not a: continue
        sa = [r["score"] for r in a]; sm = [r["score"] for r in m]; df = [x - y for x, y in zip(sa, sm)]
        lo, hi = boot(df)
        cnt = lambda L: tuple(sum(r["outcome"] == k for r in L) for k in ("correct", "wrong", "abstained"))
        P(f"| {arm} | {scope} | {sum(sm)/len(sm):.3f} {cnt(m)} | {sum(sa)/len(sa):.3f} {cnt(a)} | {sum(df)/len(df):+.3f} [{lo:+.3f}, {hi:+.3f}] | {sum(r['calls'] for r in a)/len(a):.2f} | {sum(r['usd'] for r in a)/len(a):.5f} |")

# run to run
P("\n## Run-to-run variance: main1 vs main2 (identical settings; no seed exists)\n")
P("| system | pooled penalised main1 | main2 | difference main2 - main1 | share of questions whose outcome changed (pooled) | per dataset: difference / changed |\n|---|---|---|---|---|---|")
sys_all = []
for r in rows("main1", "musique"):
    if r["system"] not in sys_all: sys_all.append(r["system"])
for s in sys_all:
    m1 = []; m2 = []; per = []
    for d in DS:
        A = {r["qid"]: r for r in rows("main1", d, s)}; Bm = {r["qid"]: r for r in rows("main2", d, s)}
        qs = [q for q in A if q in Bm]
        if not qs: continue
        x = [A[q] for q in qs]; y = [Bm[q] for q in qs]
        m1 += x; m2 += y
        per.append(f"{d[:4]} {sum(r['score'] for r in y)/len(y) - sum(r['score'] for r in x)/len(x):+.2f} / {sum(a['outcome']!=b['outcome'] for a,b in zip(x,y))/len(x):.0%}")
    if not m1: continue
    P(f"| {s} | {sum(r['score'] for r in m1)/len(m1):.3f} | {sum(r['score'] for r in m2)/len(m2):.3f} | {sum(r['score'] for r in m2)/len(m2) - sum(r['score'] for r in m1)/len(m1):+.3f} | {sum(a['outcome']!=b['outcome'] for a,b in zip(m1,m2))/len(m1):.0%} | {'; '.join(per)} |")

# k sweep
P("\n## k sweep (pooled penalised score (c-w)/n, n=300; thinking off, source shown)\n")
P("| system | k4 | default (k8; agentic 5) | k12 |\n|---|---|---|---|")
for s in ["bm25", "vector", "hybrid", "hybrid_rerank", "agentic"]:
    cells = []
    for cfg in (("agent-k4" if s == "agentic" else "base-k4"), "main1", ("agent-k12" if s == "agentic" else "base-k12")):
        L = [r for d in DS for r in rows(cfg, d, s)]
        cells.append(f"{sum(r['score'] for r in L)/len(L):.3f} ({sum(r['outcome']=='correct' for r in L)}c/{sum(r['outcome']=='wrong' for r in L)}w)" if len(L) == 300 else ("not run" if not L else f"incomplete n={len(L)}"))
    P(f"| {s} | " + " | ".join(cells) + " |")
print("\n".join(out))
