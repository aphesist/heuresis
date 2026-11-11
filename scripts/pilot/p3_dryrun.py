"""Item 3: harness end to end in dry-run (EchoLLM, $0) on dev; measure prompt sizes.
Usage: p3_dryrun.py <dataset>. Uses the local ONNX models (retrieval/verification only);
the generator is the offline EchoLLM, so no paid API is touched."""
import json, os, sys, threading, time
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.fakes import EchoLLM
from heuresis.bench import systems as S
from heuresis.bench.ledger import Ledger
from heuresis.bench.run import run
from heuresis.bench import report
from heuresis.bench.systems import build_context, build_systems, SYSTEM_NAMES
from heuresis.models_local import load_embedder, load_reranker, load_entailer
from heuresis.surface.config import load_config

name = sys.argv[1]
ds, qs = load_dev(name)
out = os.path.join(OUT, name, "dryrun")
os.makedirs(out, exist_ok=True)
for f in ("results.jsonl", "manifest.json", "ledger.jsonl"):
    if os.path.exists(os.path.join(out, f)):
        os.remove(os.path.join(out, f))


class Recorder(EchoLLM):
    """EchoLLM that logs the characters of every call, attributed to (system, question)."""
    def __init__(self):
        super().__init__()
        self.cur = threading.local()
        self.calls = []
    def complete(self, system, prompt, *, max_tokens=600):
        key = getattr(self.cur, "key", None)
        self.calls.append((key, len(system), len(prompt)))
        return super().complete(system, prompt, max_tokens=max_tokens)


rec = Recorder()
orig = S.System.answer
def answer(self, q):
    rec.cur.key = (self.name, q.id)
    return orig(self, q)
S.System.answer = answer

cfg = load_config()
ctx = build_context(ds, db_path(name), llm=rec, embedder=load_embedder(), reranker=load_reranker(),
                    entailer=load_entailer(), config=cfg, ledger=Ledger(os.path.join(out, "ledger.jsonl"), 100.0),
                    prepare=False)
systems = build_systems(ctx, SYSTEM_NAMES)
t0 = time.perf_counter()
stats = run(ds, "dev", systems, out, ctx.ledger, workers=1, dry_run=True)
wall = time.perf_counter() - t0
print("run stats", stats, f"wall {wall:.0f}s", flush=True)
rep = report.build(out, iters=200, seed=0)
report.write(out, iters=200, seed=0)

per = {}
for key, sl, pl in rec.calls:
    per.setdefault(key, []).append(sl + pl)
json.dump({f"{k[0]}|{k[1]}": v for k, v in per.items()}, open(os.path.join(out, "call_chars.json"), "w"))
json.dump({"wall_s": wall, "stats": stats,
           "unavailable": {s.name: s.reason for s in systems if not s.available},
           "models": ctx.models()}, open(os.path.join(out, "p3_meta.json"), "w"), indent=1)
print("done", flush=True)
