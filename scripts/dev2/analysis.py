"""Analysis of the dev2 runs (calibration data, not results). Usage: analysis.py runs/dev2 > out.md
Reads runs/dev2/{off,default}/{musique,multihoprag,hoh}/{results.jsonl,judge.jsonl,manifest.json}."""
import json, os, sys, random, statistics
from collections import Counter

ROOT = sys.argv[1]
CONDS = ("off", "default")
DS = ("musique", "multihoprag", "hoh")
SYS = ["closed_book", "bm25", "hybrid", "hybrid_rerank", "agentic", "engine", "engine_single",
       "hybrid+asof", "agentic+asof"]
rng = random.Random(1)

def rows(c, d):
    p = os.path.join(ROOT, c, d)
    last = {}
    for l in open(os.path.join(p, "results.jsonl")):
        r = json.loads(l); last[(r["system"], r["qid"])] = r
    verd = {}
    jp = os.path.join(p, "judge.jsonl")
    if os.path.exists(jp):
        for l in open(jp):
            r = json.loads(l); verd[(r["system"], r["qid"])] = r.get("verdict")
    out = {}
    for (s, q), r in last.items():
        r = dict(r)
        if r.get("status") == "error":
            r.update(outcome="wrong", score=-1.0, usd=r.get("usd") or 0)
        r["jscore"] = 1.0 if (verd.get((s, q)) == "EQUIVALENT" and r.get("outcome") == "wrong"
                              and r.get("status") == "answered") else r.get("score", 0.0)
        r["jcorrect"] = r["outcome"] == "correct" or r["jscore"] == 1.0
        out.setdefault(s, {})[q] = r
    return out

DATA = {(c, d): rows(c, d) for c in CONDS for d in DS if os.path.exists(os.path.join(ROOT, c, d, "results.jsonl"))}

def boot(xs, n=2000):
    if not xs: return (float("nan"),) * 3
    m = sum(xs) / len(xs); ms = []
    for _ in range(n):
        ms.append(sum(rng.choice(xs) for _ in xs) / len(xs))
    ms.sort(); return m, ms[int(.025 * n)], ms[int(.975 * n)]

def fmt(t): return f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"

def counts(rs, key="outcome"):
    c = Counter(r[key] for r in rs); return c["correct"], c["wrong"], c["abstained"]

def scope_rows(c, scope):
    ds = DS if scope == "pooled" else (scope,)
    return {s: {(d, q): r for d in ds if (c, d) in DATA for q, r in DATA[(c, d)].get(s, {}).items()} for s in SYS}

L = ["# dev2 analysis (calibration data on the dev2 split, n = 100 per dataset; NOT benchmark results)", ""]
for c in CONDS:
    if not any(k[0] == c for k in DATA): continue
    L += [f"## Condition `{c}` ({'thinking disabled' if c == 'off' else 'default thinking, draft.max_tokens 4096'})", ""]
    L += ["| scope | system | n | c/w/a | penalised [95% CI] | c/w/a (judge) | penalised (judge) | $/q | $/correct | calls | searches | median ms |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for scope in DS + ("pooled",):
        R = scope_rows(c, scope)
        for s in SYS:
            rs = list(R[s].values())
            if not rs: continue
            cw = counts(rs)
            jc = (sum(r["jcorrect"] for r in rs), sum(1 for r in rs if r["outcome"] == "wrong" and r["jscore"] != 1.0 and r["status"] != "abstained") , sum(1 for r in rs if r["outcome"] == "abstained"))
            pen = boot([r["score"] for r in rs]); jpen = sum(r["jscore"] for r in rs) / len(rs)
            usd = sum(r.get("usd") or 0 for r in rs)
            L.append(f"| {scope} | {s} | {len(rs)} | {cw[0]}/{cw[1]}/{cw[2]} | {fmt(pen)} | {jc[0]}/{cw[1]-(jc[0]-cw[0])}/{cw[2]} | {jpen:+.3f} | {usd/len(rs):.5f} | {usd/max(cw[0],1):.5f} | {statistics.mean(r.get('calls') or 0 for r in rs):.2f} | {statistics.mean(r.get('searches') or 0 for r in rs):.2f} | {statistics.median(r.get('ms') or 0 for r in rs):.0f} |")
    L += ["", "### Paired differences (penalised score, engine minus X; 95% bootstrap CI), primary / judge-assisted", "", "| scope | pair | primary | judge |", "|---|---|---|---|"]
    for scope in DS + ("pooled",):
        R = scope_rows(c, scope)
        for x in ("hybrid", "agentic", "hybrid+asof", "agentic+asof", "engine_single"):
            ks = [k for k in R["engine"] if k in R.get(x, {})]
            if not ks: continue
            L.append(f"| {scope} | engine - {x} | {fmt(boot([R['engine'][k]['score'] - R[x][k]['score'] for k in ks]))} | {fmt(boot([R['engine'][k]['jscore'] - R[x][k]['jscore'] for k in ks]))} |")
    # engine details
    L += ["", "### Engine details", ""]
    for scope in DS + ("pooled",):
        R = scope_rows(c, scope); E = list(R["engine"].values())
        if not E: continue
        one = sum(1 for r in E if r["calls"] == 1) / len(E)
        ms_ = statistics.mean(r["searches"] - 1 for r in E)
        ab = Counter((r.get("replay") or {}).get("abstention") for r in E if r["status"] == "abstained")
        ab_ans = Counter((r.get("replay") or {}).get("abstention") for r in E if r["status"] == "abstained" and r["answerable"])
        drops = Counter(); ncl = 0; nrows = 0; part = 0
        for r in E:
            rp = r.get("replay") or {}
            if not rp.get("verified"): continue
            nrows += 1
            for cl in rp["claims"]:
                ncl += 1
                for k, v in cl["checks"].items():
                    if not v:
                        if k == "exists":
                            drops["exists_uncited" if not (cl["passage_marks"] or cl["tool_marks"]) else "exists_unresolved_mark"] += 1
                        drops[k] += 1
        ans = [r for r in E if r["status"] == "answered"]
        ans.sort(key=lambda r: -r["confidence"])
        def acc_at(frac):
            k = max(1, round(frac * len(ans))); top = ans[:k]
            return sum(r["outcome"] == "correct" for r in top) / k if ans else float("nan")
        # AURC over answered (risk = wrong share among top-k, averaged over k)
        aurc = float("nan")
        if ans:
            w = 0; tot = 0
            for i, r in enumerate(ans, 1):
                w += r["outcome"] == "wrong"; tot += w / i
            aurc = tot / len(ans)
        trunc = sum(1 for r in E for sr in r.get("stop_reasons", []) if sr == "max_tokens")
        L.append(f"- **{scope}** (n={len(E)}): answered in one call {one:.0%}; mean model searches {ms_:.2f}; abstention types (all) {dict(ab)}; on answerable {dict(ab_ans)}; claims checked {ncl} in {nrows} verified answers, failing `exists` {drops['exists']} (no mark at all {drops['exists_uncited']}, mark that does not exist {drops['exists_unresolved_mark']}), `valid_at_date` {drops['valid_at_date']}, `numbers_traced` {drops['numbers_traced']}; answered {len(ans)}, AURC (answered, by grade) {aurc:.3f}, accuracy at 50% / 80% of answered by grade {acc_at(.5):.2f} / {acc_at(.8):.2f}; replies cut at max_tokens {trunc}")
    # truncation / errors all systems
    tr = Counter(); er = Counter()
    for (cc, d), D_ in DATA.items():
        if cc != c: continue
        for s, qs in D_.items():
            for r in qs.values():
                er[s] += r.get("status") == "error"
                tr[s] += sum(1 for sr in r.get("stop_reasons", []) if sr == "max_tokens")
    L += ["", f"Zero-truncation check (calls stopped at max_tokens, per system): {dict(tr)}; error rows: {dict(er)}", ""]

# as-of check on hoh (engine passages must be in force at the question date)
for c in CONDS:
    if (c, "hoh") not in DATA: continue
    bad = tot = 0
    for r in DATA[(c, "hoh")].get("engine", {}).values():
        a = r.get("as_of")
        for p in (r.get("replay") or {}).get("passages", []):
            tot += 1
            if a and not ((p["valid_from"] is None or p["valid_from"] <= a) and (p["valid_to"] is None or a < p["valid_to"])): bad += 1
    L.append(f"As-of check, hoh, condition {c}: {tot} passages shown to the engine (all searches), {bad} not in force at the question date.")

# examples
L += ["", "## Examples (dev2 only; engine, thinking disabled)", ""]
c = "off"
for kind, pred in (("wrong answers", lambda r: r["outcome"] == "wrong"), ("abstentions on answerable questions", lambda r: r["status"] == "abstained" and r["answerable"])):
    L += [f"### Engine {kind}", ""]
    n = 0
    for d, cap in zip(DS, (2, 2, 1)):
        if (c, d) not in DATA: continue
        m = 0
        for q, r in sorted(DATA[(c, d)].get("engine", {}).items()):
            if pred(r) and m < cap:
                m += 1
                rp = r.get("replay") or {}
                L.append(f"- `{q}` ({d}); gold {rp.get('answers')}; status {r['status']}; note `{r.get('note')}`; calls {r['calls']}; grade {r['confidence']:.2f}; text: {r['text'][:300]!r}; draft replies: {[x[:160] for x in rp.get('draft_raws', [])]}")
                n += 1
    L.append("")

# comparison of the two conditions
L += ["", "## Both conditions side by side (penalised score, primary / judge-assisted; c/w/a)", "", "| scope | system | off | default |", "|---|---|---|---|"]
for scope in DS + ("pooled",):
    for sy in SYS:
        cells = []
        for c in CONDS:
            rs = list(scope_rows(c, scope)[sy].values()) if any(k[0] == c for k in DATA) else []
            if not rs: cells.append("n/a"); continue
            cw = counts(rs)
            cells.append(f"{cw[0]}/{cw[1]}/{cw[2]}: {sum(r['score'] for r in rs)/len(rs):+.3f} / {sum(r['jscore'] for r in rs)/len(rs):+.3f}")
        L.append(f"| {scope} | {sy} | {cells[0]} | {cells[1]} |")
print("\n".join(L))
