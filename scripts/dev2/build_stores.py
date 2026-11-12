"""Build and embed one SQLite store per dataset with the default local embedder, once, so
that every dev2 run can start from a copy (``bench.run`` ingests and embeds into
``<out>/store.sqlite`` only what is missing). Usage: build_stores.py <dataset>...
Output: runs/stores/<dataset>/store.sqlite (not committed). Costs nothing: no paid call."""
import json, os, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from heuresis.ingest import ingest
from heuresis.models_local import load_embedder
from heuresis.store import Store

for name in sys.argv[1:]:
    cdir = os.path.join(ROOT, "data", "corpora", name)
    out = os.path.join(ROOT, "runs", "stores", name)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "store.sqlite")
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(path + ext):
            os.remove(path + ext)
    emb = load_embedder()
    st = Store(path)
    t0 = time.perf_counter()
    counts = ingest(st, cdir, "jsonl")
    rows = st.missing_vectors(emb.id)
    print(name, "ingested", counts, f"{time.perf_counter() - t0:.0f}s; to embed {len(rows)}", flush=True)
    t1, done = time.perf_counter(), 0
    for i in range(0, len(rows), 64):
        chunk = rows[i:i + 64]
        vecs = emb.embed([r[2] for r in chunk])
        st.put_vectors(emb.id, [(r[0], r[1], vecs[j]) for j, r in enumerate(chunk)])
        done += len(chunk)
        if (i // 64) % 100 == 0:
            print(f"  {done}/{len(rows)} {time.perf_counter() - t1:.0f}s", flush=True)
    st.close()
    res = {"dataset": name, "embedder": emb.id, "counts": counts, "versions_embedded": len(rows),
           "embed_s": time.perf_counter() - t1}
    json.dump(res, open(os.path.join(out, "build.json"), "w"), indent=2)
    print(json.dumps(res), flush=True)
