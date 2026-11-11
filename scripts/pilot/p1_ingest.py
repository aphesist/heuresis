"""Item 1: ingest and embed one corpus; record timings. Usage: p1_ingest.py <dataset>"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.ingest import ingest
from heuresis.store import Store
from heuresis.models_local import load_embedder, DEFAULT_EMBEDDER

name = sys.argv[1]
cdir = os.path.join(ROOT, "data", "corpora", name)
os.makedirs(os.path.join(OUT, name), exist_ok=True)
path = db_path(name)
for ext in ("", "-wal", "-shm"):
    if os.path.exists(path + ext):
        os.remove(path + ext)
emb = load_embedder()
st = Store(path)
t0 = time.perf_counter()
counts = ingest(st, cdir, "jsonl")
t_ingest = time.perf_counter() - t0
rows = st.missing_vectors(emb.id)
n = len(rows)
print(name, "ingested", counts, f"{t_ingest:.1f}s; to embed {n}", flush=True)
t1 = time.perf_counter()
done = 0
for i in range(0, n, 64):
    chunk = rows[i:i + 64]
    vecs = emb.embed([r[2] for r in chunk])
    st.put_vectors(emb.id, [(r[0], r[1], vecs[j]) for j, r in enumerate(chunk)])
    done += len(chunk)
    if (i // 64) % 100 == 0:
        el = time.perf_counter() - t1
        print(f"  {done}/{n} {el:.0f}s {done/el:.1f}/s", flush=True)
t_embed = time.perf_counter() - t1
st.close()
size = sum(os.path.getsize(path + e) for e in ("", "-wal", "-shm") if os.path.exists(path + e))
res = {"dataset": name, "embedder": emb.id, "counts": counts, "versions_embedded": n,
       "ingest_s": t_ingest, "embed_s": t_embed, "passages_per_s": n / t_embed,
       "db_bytes": size, "db_mb": size / 1e6}
json.dump(res, open(os.path.join(OUT, name, "p1_ingest.json"), "w"), indent=2)
print(json.dumps(res), flush=True)
