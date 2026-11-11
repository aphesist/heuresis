"""Item 5: crude, LLM-free check of the local entailer on gold-vs-random passages (dev only).
Usage: p5_verifier.py <dataset>. A proxy only: statements are built from gold answers, not
drafted by a model."""
import json, os, random, re, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.bench.stats import wilson_interval
from heuresis.model import AsOf
from heuresis.store import Store
from heuresis.models_local import load_entailer
from heuresis.surface.config import load_config

name = sys.argv[1]
ds, qs = load_dev(name)
ent = load_entailer()
st = Store(db_path(name))
rng = random.Random(20261111)
THR = load_config().verify.support_threshold
nver = st._con.execute("SELECT MAX(id) FROM versions").fetchone()[0]

_REW = re.compile(r"^(?:what|who)\s+(is|was|are|were)\s+(?:the\s+)?(.+?)\s*\?*$", re.I)
def declarative(q, ans):
    """Minimal rewrite 'What is X?' -> 'X is <ans>.' ; None when the rule does not apply."""
    m = _REW.match(q.strip())
    if not m or len(m.group(2).split()) > 18:
        return None
    return f"The {m.group(2)} {m.group(1).lower()} {ans}."

def norm(s): return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())

def gold_text(q):
    best = None
    for g in q.gold_units:
        v = st.text_at(g, AsOf(valid=q.as_of)) if q.as_of else st.text_at(g, AsOf())
        if v is None:
            continue
        if best is None:
            best = (g, v.text)
        if norm(q.answers[0]) in norm(v.text):
            return g, v.text
    return best

def random_text(exclude):
    while True:
        r = st._con.execute("SELECT unit_id, text FROM versions WHERE id=?", (rng.randint(1, nver),)).fetchone()
        if r and r[0] not in exclude:
            return r[1]

rows = []
for q in qs:
    if not (q.answerable and q.gold_units and q.answers):
        continue
    gt = gold_text(q)
    if gt is None:
        continue
    ans = q.answers[0]
    rows.append({"qid": q.id, "gold_unit": gt[0], "gold": gt[1], "rand": random_text(set(q.gold_units)),
                 "ans": ans, "s_qa": f"{q.text} {ans}", "s_decl": declarative(q.text, ans)})
n = len(rows)
print(name, "pairs n =", n, "declarative rewrites:", sum(r["s_decl"] is not None for r in rows), flush=True)

def auroc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))

def summarise(pos, neg):
    b = np.random.default_rng(0)
    boots = []
    for _ in range(1000):
        ip, ineg = b.integers(0, len(pos), len(pos)), b.integers(0, len(neg), len(neg))
        boots.append(auroc(np.asarray(pos)[ip], np.asarray(neg)[ineg]))
    d = lambda x: {"n": len(x), "mean": float(np.mean(x)), "q1": float(np.percentile(x, 25)),
                   "median": float(np.median(x)), "q3": float(np.percentile(x, 75))}
    ge = lambda x: sum(v >= THR for v in x)
    return {"matched": d(pos), "mismatched": d(neg), "auroc": auroc(pos, neg),
            "auroc_ci95_bootstrap": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "matched_ge_thr": [ge(pos), len(pos), *wilson_interval(ge(pos), len(pos))],
            "mismatched_ge_thr": [ge(neg), len(neg), *wilson_interval(ge(neg), len(neg))],
            "threshold": THR}

out = {"dataset": name, "n_pairs": n, "entailer": ent.id}
t0 = time.perf_counter(); npairs = 0
for label, key in (("S2_question_plus_answer", "s_qa"), ("S1_declarative", "s_decl")):
    sel = [r for r in rows if r[key] is not None]
    if len(sel) < 5:
        out[label] = {"n": len(sel), "note": "too few"}; continue
    pos = ent.entail([(r["gold"], r[key]) for r in sel])
    neg = ent.entail([(r["rand"], r[key]) for r in sel])
    npairs += 2 * len(sel)
    out[label] = summarise(pos, neg)
dt = time.perf_counter() - t0
out["throughput_pairs_per_s"] = npairs / dt
# containment of the gold answer string in the passage (no model)
cm = sum(norm(r["ans"]) in norm(r["gold"]) for r in rows)
cr = sum(norm(r["ans"]) in norm(r["rand"]) for r in rows)
out["containment"] = {"gold_passage": [cm, n, *wilson_interval(cm, n)],
                      "random_passage": [cr, n, *wilson_interval(cr, n)]}
json.dump(out, open(os.path.join(OUT, name, "p5_verifier.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
