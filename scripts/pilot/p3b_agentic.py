"""Item 3b: analytic prompt size of the `agentic` system for 1, 2 and 4 searches, built with the
REAL prompt-assembly code and real passage lengths. A scripted offline LLM issues the searches;
search i returns ranks 5(i-1)+1..5i of the hybrid+rerank list (so each search brings 5 new
passages). Search text = the question itself (a real agent's queries may be shorter).
Usage: p3b_agentic.py <dataset>"""
import json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.fakes import EchoLLM
from heuresis.bench import systems as S
from heuresis.bench.systems import build_context, HybridRerank
from heuresis.models_local import load_embedder, load_reranker
from heuresis.surface.config import load_config

name = sys.argv[1]
ds, qs = load_dev(name)


class Rec(EchoLLM):
    def __init__(self, script):
        super().__init__(script)
        self.chars = []
    def complete(self, system, prompt, *, max_tokens=600):
        self.chars.append(len(system) + len(prompt))
        return super().complete(system, prompt, max_tokens=max_tokens)


class Staged(S.Agentic):
    def retrieve(self, text, q, k=None):
        self._i += 1
        return self._pool[5 * (self._i - 1):5 * self._i]


ctx = build_context(ds, db_path(name), llm=EchoLLM(), embedder=load_embedder(), reranker=load_reranker(),
                    config=load_config(), prepare=False)
hy = S.HybridRerank(ctx, k=20)
out = {"dataset": name, "n": len(qs), "assumption": "search i returns ranks 5(i-1)+1..5i; query text = question; final reply abstains",
       "searches": {}}
pools = {q.id: hy.retrieve(q.text, q, 20) for q in qs}
for s in (1, 2, 4):
    tot, calls, percall = [], [], []
    for q in qs:
        script = [f"SEARCH: {q.text}"] * s + ["ABSTAIN\nCONFIDENCE: 0"]
        ctx.llm = Rec(script)
        ag = Staged(ctx, k=5, max_actions=4)
        ag._pool, ag._i = pools[q.id], 0
        r = ag.answer(q)
        tot.append(sum(ctx.llm.chars)); calls.append(r.calls); percall.append(list(ctx.llm.chars))
    a = np.array(tot)
    out["searches"][str(s)] = {"mean_chars": float(a.mean()), "p95_chars": float(np.percentile(a, 95)),
                          "mean_calls": float(np.mean(calls)), "per_q_calls": percall}
    print(name, s, {k: v for k, v in out["searches"][str(s)].items() if k != 'per_q_calls'}, flush=True)
json.dump(out, open(os.path.join(OUT, name, "p3b_agentic.json"), "w"), indent=1)
