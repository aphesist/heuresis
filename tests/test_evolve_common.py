"""Shared helpers for the evolve tests (no tests here): a synthetic pool-bearing dataset, a
deterministic scripted runner in which one kind of surface is truly better, and a scripted proposer."""
import hashlib

from heuresis.bench.types import Dataset, Question
from heuresis.evolve.candidates import Candidate, base_surface, normalise
from heuresis.evolve.splits import PoolSplits

GOLD = "GOLD"


def make_splits(n_pool=200, promo_n=40, promo_blocks=2, cal_n=5, seed=1):
    pool = [Question(id=f"p{i:03d}", text=f"Synthetic question number {i} about the odd item named {i * 7} today?",
                     answers=(f"{GOLD}-p{i:03d}",), cluster="") for i in range(n_pool)]
    anchors = [Question(id=f"a{i:02d}", text=f"Anchor question {i} about thing {i * 3}?",
                        answers=(f"{GOLD}-a{i:02d}",)) for i in range(20)]
    ds = Dataset(name="syn", corpus_dir="", questions={}, licence="synthetic", corpus_tokens=0, meta={})
    return PoolSplits({"syn": (ds, pool, anchors)}, seed=seed, promo_n=promo_n, promo_blocks=promo_blocks,
                      cal_n=cal_n, cal_blocks=1)


def u_of(qid):
    return int(hashlib.sha256(qid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


class Scripted:
    """Quality by surface: k_first >= 12 is good (correct when u < 0.9), k_first <= 4 is bad
    (correct when u < 0.3), anything else is base (u < 0.5); the rest are answered wrong. On the
    splits in ``degrade`` a good surface is terrible. ``leak`` makes canaries get answered with the
    marker; ``usd`` is the cost per row."""

    def __init__(self, usd=0.0, degrade=(), leak=False, taint_good=False):
        self.usd, self.degrade, self.leak, self.taint_good = usd, set(degrade), leak, taint_good
        self.calls = 0
        self.seen = []

    def level(self, surface, split):
        k = surface.get("retrieve", "k_first")
        if k >= 12:
            return 0.02 if split in self.degrade else 0.9
        return 0.3 if k <= 4 else 0.5

    def __call__(self, surface, questions, *, tag):
        self.calls += 1
        rows = []
        for q in questions:
            self.seen.append((tag, q.id))
            lvl = self.level(surface, getattr(q, "split", ""))
            u = u_of(q.id)
            text, tainted = "", None
            if not q.answerable:
                if self.leak:
                    status, outcome, text = "answered", "wrong", "see hx-canary-deadbeef"
                else:
                    status, outcome = "abstained", "correct"
            elif u < lvl:
                status, outcome, text = "answered", "correct", f"The answer is {q.answers[0]}"
            else:
                status, outcome, text = "answered", "wrong", "A wrong answer."
            if status == "answered" and self.taint_good and surface.get("retrieve", "k_first") >= 12:
                tainted = True
            rows.append({"qid": q.id, "status": status, "text": text, "outcome": outcome,
                         "score": 0.0, "confidence": 0.8, "usd": self.usd, "tainted": tainted,
                         "abstention": None if status == "answered" else "no_source", "reasons": []})
        return rows


class ScriptedProposer:
    name = "scripted"
    wants_traces = False

    def __init__(self, *docs_per_cycle):
        self.plan = list(docs_per_cycle)
        self.i = 0

    def propose(self, parent, k, *, seed=0, traces=None):
        docs = self.plan[min(self.i, len(self.plan) - 1)]
        self.i += 1
        return [Candidate(d, parent=parent.id) for d in docs]


GOOD = {"config": {"retrieve.k_first": 14}}
NEUTRAL = {"config": {"retrieve.k_lexical": 60}}
NEUTRAL2 = {"config": {"retrieve.k_lexical": 70}}
BAD = {"config": {"retrieve.k_first": 3}}

CFG = {"rotating_n": 20, "screen_n": 12, "promotion_n": 40, "promotion_min_n": 20, "anchor_n": 20,
       "canary_n": 4, "ledger_margin_usd": 0.0, "bootstrap_iters": 500, "permutation_iters": 5000,
       "promotion_query_budget": 10}


def cycle_kwargs(runner, **extra):
    kw = dict(runner=runner, smoke_runner=runner, splits=make_splits(), config=dict(CFG),
              allow_unpinned=True, offline=False, seed=3)
    kw.update(extra)
    return kw
