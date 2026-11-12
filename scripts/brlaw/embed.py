"""Ingest a corpus into a store and embed it (default local model). Usage: embed.py CORPUS_DIR DB"""
import sys
import time

from heuresis import models_local
from heuresis.domains import get_domain
from heuresis.ingest import ingest
from heuresis.store import Store

corpus, db = sys.argv[1], sys.argv[2]
t = time.time()
st = Store(db)
print(ingest(st, corpus, get_domain("legal_br")), f"ingest {time.time() - t:.0f}s", flush=True)
emb = models_local.load_embedder()
rows = st.missing_vectors(emb.id)
print("to embed", len(rows), flush=True)
t = time.time()
for i in range(0, len(rows), 32):
    ch = rows[i:i + 32]
    v = emb.embed([r[2] for r in ch])
    st.put_vectors(emb.id, [(r[0], r[1], v[j]) for j, r in enumerate(ch)])
    if (i // 32) % 100 == 0:
        print(i, f"{time.time() - t:.0f}s", flush=True)
print("done", len(rows), f"embed {time.time() - t:.0f}s", flush=True)
