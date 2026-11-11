"""Item 6: re-measure the default cascade (rerank off) on the dev split, reusing the stores
built by p1_ingest.py. Usage: p8_cascade_norerank.py [dataset ...] (default: all three).
Retrieval only, k = 8, default Query (no router); no language model is involved. Writes
runs/pilot-dev/<dataset>/p8_cascade_norerank.json and prints a markdown table."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.bench.stats import wilson_interval
from heuresis.model import AsOf, Query
from heuresis.models_local import load_embedder, load_reranker
from heuresis.retrieve import cascade
from heuresis.store import Store
from heuresis.surface.config import load_config

K = 8
cfg = load_config().retrieve
assert cfg.rerank is False and cfg.rerank_out == K, cfg
emb = load_embedder()
reranker = load_reranker()  # passed in on purpose: with rerank off it must stay unused


def frac(c, n):
    lo, hi = wilson_interval(c, n)
    return f"{c}/{n} = {100 * c / n:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}]" if n else "n/a"


rows = []
for name in (sys.argv[1:] or list(DATASETS)):
    ds, qs = load_dev(name)
    st = Store(db_path(name))
    modes = ["dated", "today"] if name == "hoh" else ["none"]
    out = {"dataset": name, "n_dev": len(qs), "k": K, "results": {}}
    for mode in modes:
        def asof(q):
            return AsOf(valid=q.as_of) if mode == "dated" and q.as_of else AsOf()
        for q in qs[:2]:  # warm-up, not timed
            cascade(st, Query(text=q.text, as_of=asof(q)), cfg, embedder=emb, reranker=reranker, trace=[])
        recs = []
        for q in qs:
            tr = []
            t0 = time.perf_counter()
            ps = cascade(st, Query(text=q.text, as_of=asof(q)), cfg, embedder=emb,
                         reranker=reranker, trace=tr)
            ms = (time.perf_counter() - t0) * 1000
            assert not any(t.stage == "rerank" for t in tr)
            fired = tr[0].note.split("; ", 1)[1].startswith("early stop:")
            units = {p.unit_id for p in ps}
            r = {"qid": q.id, "ms": ms, "fired": fired}
            if q.answerable and q.gold_units:
                g = set(q.gold_units)
                r["any"], r["all"] = bool(g & units), g <= units
            recs.append(r)
        out["results"][mode] = recs
        sc = [r for r in recs if "any" in r]
        fi, nf = [r for r in sc if r["fired"]], [r for r in sc if not r["fired"]]
        label = name if name != "hoh" else f"hoh, as-of {'question date' if mode == 'dated' else 'today'}"
        rows.append((label, len(sc), frac(sum(r["any"] for r in sc), len(sc)),
                     frac(sum(r["all"] for r in sc), len(sc)),
                     f"{sum(r['fired'] for r in recs)}/{len(recs)}",
                     frac(sum(r["any"] for r in fi), len(fi)), frac(sum(r["any"] for r in nf), len(nf)),
                     f"{sum(r['ms'] for r in recs) / len(recs):.0f}"))
        print(rows[-1], flush=True)
    json.dump(out, open(os.path.join(OUT, name, "p8_cascade_norerank.json"), "w"))

print()
print("| dataset | scored | any gold @8 | all gold @8 | early stop fired (of 100) | any @8 when fired | any @8 when not | ms / query |")
print("|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| " + " | ".join(map(str, r)) + " |")
