"""Recall of the gold provisions on the dev split at k = 8. Usage: check_recall.py DATA_DIR CORPUS_NAME [hybrid]
BM25 uses the store's lexical search; "hybrid" also needs the embedded store and the default local embedder."""
import json
import sys

from heuresis.bench import brlaw as B
from heuresis.model import AsOf, Query, Scope
from heuresis.store import Store

data, name = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "bm25"
st = Store(f"{data}/db/{name}.db")
qs = [q for q in B.load(data, name).questions["dev"] if q.gold_units]
if mode == "hybrid":
    import dataclasses
    from heuresis import models_local
    from heuresis.retrieve import cascade
    from heuresis.surface.config import load_config
    emb = models_local.load_embedder()
    cfg = dataclasses.replace(load_config().retrieve, early_stop=False, dense=True, rerank=False, expand=False,
                              rewrite=False, second_round=False, rerank_out=8)
hit = rec = 0.0
for q in qs:
    if mode == "hybrid":
        ps = cascade(st, Query(text=q.text, as_of=AsOf(valid=q.as_of)), cfg, embedder=emb, reranker=None, trace=[])
    else:
        ps = st.lexical(q.text, AsOf(valid=q.as_of), Scope(), 8)
    got = {p.unit_id for p in ps}
    g = set(q.gold_units)
    hit += bool(g & got)
    rec += len(g & got) / len(g)
print(json.dumps({"corpus": name, "mode": mode, "dev_questions_with_gold": len(qs),
                  "any_gold_at_8": round(hit / len(qs), 3), "mean_recall_at_8": round(rec / len(qs), 3)}))
