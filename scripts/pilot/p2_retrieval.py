"""Item 2: retrieval-only measurement on the dev split. Usage: p2_retrieval.py <dataset>
Systems: a bm25, b dense, c bm25+dense RRF, d c + rerank (50->8), e engine default cascade.
No language model is involved."""
import dataclasses, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.bench.stats import wilson_interval
from heuresis.model import AsOf, Query, Scope
from heuresis.retrieve import cascade, rrf
from heuresis.store import Store
from heuresis.models_local import load_embedder, load_reranker
from heuresis.surface.config import load_config

name = sys.argv[1]
K = 8
ds, qs = load_dev(name)
cfg = load_config().retrieve
emb, rr = load_embedder(), load_reranker()
st = Store(db_path(name))
modes = ["dated", "today"] if name == "hoh" else ["none"]
SCOPE = Scope()
print(name, "dev n =", len(qs), "answerable with gold:", sum(1 for q in qs if q.answerable and q.gold_units), flush=True)


def asof(q, mode):
    return AsOf(valid=q.as_of) if mode == "dated" and q.as_of else AsOf()


def run_a(q, a):
    return st.lexical(q.text, a, SCOPE, K), None


def run_b(q, a):
    v = emb.embed([q.text], is_query=True)[0]
    return st.dense(v, emb.id, a, SCOPE, K), None


def run_c(q, a):
    lex = st.lexical(q.text, a, SCOPE, cfg.k_lexical)
    v = emb.embed([q.text], is_query=True)[0]
    den = st.dense(v, emb.id, a, SCOPE, cfg.k_dense)
    return rrf([lex, den], k=cfg.rrf_k)[:K], None


def run_d(q, a):
    c = dataclasses.replace(cfg, early_stop=False, dense=True, rerank=True, expand=False,
                            rewrite=False, second_round=False, rerank_out=K)
    return cascade(st, Query(text=q.text, as_of=a), c, embedder=emb, reranker=rr, trace=[]), None


def run_e(q, a):
    tr = []
    ps = cascade(st, Query(text=q.text, as_of=a), cfg, embedder=emb, reranker=rr, trace=tr)
    fired = tr[0].note.split("; ", 1)[1].startswith("early stop:")
    return ps, {"fired": fired, "note": tr[0].note}


SYS = {"a_bm25": run_a, "b_dense": run_b, "c_rrf": run_c, "d_rerank": run_d, "e_cascade": run_e}
# warm-up (not timed): load pages, JIT-ish caches
for q in qs[:2]:
    for f in SYS.values():
        f(q, asof(q, modes[0]))

out = {"dataset": name, "n_dev": len(qs), "k": K, "results": {}}
for mode in modes:
    for sname, fn in SYS.items():
        recs = []
        for q in qs:
            a = asof(q, mode)
            t0 = time.perf_counter()
            ps, extra = fn(q, a)
            ms = (time.perf_counter() - t0) * 1000
            units = [p.unit_id for p in ps]
            r = {"qid": q.id, "answerable": q.answerable, "ms": ms, "units": units,
                 "gold": list(q.gold_units), "extra": extra}
            if q.answerable and q.gold_units:
                g = set(q.gold_units)
                r["any"] = bool(g & set(units))
                r["all"] = g <= set(units)
                if name == "hoh":
                    gu = q.gold_units[0]
                    want = st.text_at(gu, AsOf(valid=q.as_of))
                    r["in_force_seq"] = None if want is None else want.seq
                    got = [p.seq for p in ps if p.unit_id == gu]
                    r["got_seqs"] = got
                    r["version_ok"] = want is not None and want.seq in got
                    r["kind"] = q.kind
            recs.append(r)
        out["results"][f"{mode}/{sname}"] = recs
        scored = [r for r in recs if "any" in r]
        n = len(scored)
        anyc = sum(r["any"] for r in scored); allc = sum(r["all"] for r in scored)
        msg = f"{mode}/{sname}: n={n} any={anyc} all={allc} ms/query={sum(r['ms'] for r in recs)/len(recs):.0f}"
        if name == "hoh":
            msg += f" version_ok={sum(r['version_ok'] for r in scored)}"
        print(msg, flush=True)
json.dump(out, open(os.path.join(OUT, name, "p2_retrieval.json"), "w"))
print("done", flush=True)
