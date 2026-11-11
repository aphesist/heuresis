"""Tests for the retrieval cascade (stand-in store) and one real-store check."""
from __future__ import annotations

import numpy as np
import pytest

from heuresis.model import AsOf, Event, Passage, Query, Scope, Source, StageTrace, Unit
from heuresis.retrieve import cascade, lexical_margin, rrf
from heuresis.surface.config import RetrieveCfg


def P(uid, seq=1, score=0.0, stage="", text=None):
    return Passage(unit_id=uid, seq=seq, text=text or f"text of {uid}", score=score,
                   stage=stage)


class FakeStore:
    """Stand-in exposing lexical / dense / neighbours with the contract signatures."""

    def __init__(self, lexical=(), dense=(), links=None):
        self._lex, self._dense, self._links = list(lexical), list(dense), links or {}
        self.calls = []

    def lexical(self, text, as_of, scope, k):
        self.calls.append(("lexical", text, k))
        return list(self._lex[:k])

    def dense(self, vec, embedder_id, as_of, scope, k):
        self.calls.append(("dense", embedder_id, k))
        return list(self._dense[:k])

    def neighbours(self, unit_ids, as_of, types=()):
        self.calls.append(("neighbours", tuple(unit_ids)))
        out = []
        for u in unit_ids:
            out += [P(n, score=0.9) for n in self._links.get(u, [])]
        return out


class FakeEmbedder:
    id = "fake-emb"
    dim = 4

    def __init__(self):
        self.seen = []

    def embed(self, texts, *, is_query=False):
        self.seen.append(is_query)
        return np.ones((len(texts), self.dim), dtype=np.float32) / 2


class LenReranker:
    """Scores a text by its length, so the longest text wins."""

    id = "len"

    def score(self, query, texts):
        return [float(len(t)) for t in texts]


def cfg(**kw):
    base = dict(early_stop=False, expand=False, rerank_out=8, rerank_in=50)
    base.update(kw)
    return RetrieveCfg(**base)


def run(store, query=None, c=None, **kw):
    trace: list[StageTrace] = []
    out = cascade(store, query or Query(text="q"), c or cfg(), trace=trace, **kw)
    return out, trace


def stages(trace):
    return [t.stage for t in trace]


# ---------------------------------------------------------------------------- rrf


def test_rrf_hand_computed():
    a = [P("A"), P("B"), P("C")]
    b = [P("B"), P("D"), P("A")]
    out = rrf([a, b], k=60)
    # A: 1/61 + 1/63 ; B: 1/62 + 1/61 ; C: 1/63 ; D: 1/62
    want = {
        "B": 1 / 62 + 1 / 61,
        "A": 1 / 61 + 1 / 63,
        "D": 1 / 62,
        "C": 1 / 63,
    }
    assert [p.unit_id for p in out] == ["B", "A", "D", "C"]
    for p in out:
        assert p.score == pytest.approx(want[p.unit_id])
        assert p.stage == "fused"


def test_rrf_keyed_by_unit_and_seq_and_pure():
    a = [P("A", 1, score=5.0, stage="lexical")]
    b = [P("A", 2, score=1.0, stage="dense"), P("A", 1)]
    out = rrf([a, b], k=10)
    assert {(p.unit_id, p.seq) for p in out} == {("A", 1), ("A", 2)}
    assert out[0].seq == 1  # appears in both lists
    assert a[0].stage == "lexical" and a[0].score == 5.0  # input untouched


def test_rrf_empty_and_single():
    assert rrf([]) == []
    assert rrf([[], []]) == []
    out = rrf([[P("A"), P("B")]], k=60)
    assert [p.unit_id for p in out] == ["A", "B"]


# ------------------------------------------------------------------ lexical only


def test_lexical_only_without_models():
    store = FakeStore(lexical=[P("A", score=3), P("B", score=2)])
    out, trace = run(store)
    assert [p.unit_id for p in out] == ["A", "B"]
    assert stages(trace) == ["lexical"]
    assert [c[0] for c in store.calls] == ["lexical"]


def test_lexical_gets_query_text_and_k():
    store = FakeStore(lexical=[P("A", score=1)])
    run(store, Query(text="hello"), cfg(k_lexical=7))
    assert store.calls[0] == ("lexical", "hello", 7)


def test_empty_results():
    out, trace = run(FakeStore())
    assert out == []
    assert trace[0].n_out == 0


# ---------------------------------------------------------------- marks and dedup


def test_marks_truncation_and_dedup():
    lex = [P("A", score=9), P("A", score=8), P("B", score=7), P("C", score=6),
           P("D", score=5)]
    out, _ = run(FakeStore(lexical=lex), c=cfg(rerank_out=3))
    assert [p.unit_id for p in out] == ["A", "B", "C"]
    assert [p.mark for p in out] == ["t1", "t2", "t3"]


def test_same_unit_different_seq_kept():
    out, _ = run(FakeStore(lexical=[P("A", 1, 2), P("A", 2, 1)]))
    assert [(p.unit_id, p.seq) for p in out] == [("A", 1), ("A", 2)]


# ------------------------------------------------------------------------- dense


def test_dense_on_fuses_and_traces():
    store = FakeStore(lexical=[P("A", score=3), P("B", score=2)],
                      dense=[P("C", score=.9), P("B", score=.8)])
    emb = FakeEmbedder()
    out, trace = run(store, embedder=emb)
    assert emb.seen == [True]  # embedded as a query
    assert [c[0] for c in store.calls] == ["lexical", "dense"]
    assert store.calls[1][1] == "fake-emb"
    assert out[0].unit_id == "B"  # in both lists
    assert {p.unit_id for p in out} == {"A", "B", "C"}
    assert all(p.stage == "fused" for p in out)
    assert stages(trace) == ["lexical", "dense"]
    assert trace[1].n_out == 3


def test_dense_off_by_switch_or_missing_embedder():
    store = FakeStore(lexical=[P("A", score=1)], dense=[P("C")])
    emb = FakeEmbedder()
    out, trace = run(store, c=cfg(dense=False), embedder=emb)
    assert emb.seen == [] and stages(trace) == ["lexical"]
    assert [p.unit_id for p in out] == ["A"]
    out, trace = run(store, c=cfg(dense=True), embedder=None)
    assert stages(trace) == ["lexical"]


def test_rrf_k_comes_from_cfg():
    store = FakeStore(lexical=[P("A", score=1)], dense=[P("A")])
    out, _ = run(store, c=cfg(rrf_k=10), embedder=FakeEmbedder())
    assert out[0].score == pytest.approx(2 / 11)


# ------------------------------------------------------------------------ expand


def test_expand_appends_below_fused_and_dedups():
    store = FakeStore(lexical=[P("A", score=3), P("B", score=2)],
                      links={"A": ["X", "B"], "B": ["Y"]})
    out, trace = run(store, c=cfg(expand=True))
    assert [p.unit_id for p in out] == ["A", "B", "X", "Y"]
    assert [p.stage for p in out][2:] == ["expand", "expand"]
    assert stages(trace) == ["lexical", "expand"]
    assert trace[1].n_out == 4


def test_expand_hops():
    links = {"A": ["X"], "X": ["Z"]}
    one, _ = run(FakeStore(lexical=[P("A", score=1)], links=links),
                 c=cfg(expand=True, expand_hops=1))
    two, _ = run(FakeStore(lexical=[P("A", score=1)], links=links),
                 c=cfg(expand=True, expand_hops=2))
    assert [p.unit_id for p in one] == ["A", "X"]
    assert [p.unit_id for p in two] == ["A", "X", "Z"]


def test_expand_uses_only_top_rerank_out_units():
    lex = [P(f"U{i}", score=10 - i) for i in range(6)]
    store = FakeStore(lexical=lex, links={"U5": ["FAR"]})
    out, _ = run(store, c=cfg(expand=True, rerank_out=3))
    assert [c for c in store.calls if c[0] == "neighbours"] == [
        ("neighbours", ("U0", "U1", "U2"))]
    assert "FAR" not in {p.unit_id for p in out}


def test_expand_off():
    store = FakeStore(lexical=[P("A", score=1)], links={"A": ["X"]})
    out, trace = run(store, c=cfg(expand=False))
    assert [p.unit_id for p in out] == ["A"]
    assert "expand" not in stages(trace)


# ------------------------------------------------------------------------ rerank


def test_rerank_on_sorts_and_stages():
    lex = [P("A", score=3, text="aa"), P("B", score=2, text="bbbbbb"),
           P("C", score=1, text="cccc")]
    out, trace = run(FakeStore(lexical=lex), reranker=LenReranker())
    assert [p.unit_id for p in out] == ["B", "C", "A"]
    assert all(p.stage == "rerank" for p in out)
    assert out[0].score == 6.0
    assert stages(trace) == ["lexical", "rerank"]


def test_rerank_off_by_switch_or_missing():
    lex = [P("A", score=3, text="aa"), P("B", score=2, text="bbbbbb")]
    out, trace = run(FakeStore(lexical=lex), c=cfg(rerank=False), reranker=LenReranker())
    assert [p.unit_id for p in out] == ["A", "B"] and stages(trace) == ["lexical"]
    out, trace = run(FakeStore(lexical=lex), c=cfg(rerank=True), reranker=None)
    assert [p.unit_id for p in out] == ["A", "B"]


def test_rerank_scores_only_top_rerank_in():
    class Counting(LenReranker):
        n = 0

        def score(self, query, texts):
            Counting.n = len(texts)
            return super().score(query, texts)

    lex = [P(f"U{i}", score=10 - i, text="x" * (i + 1)) for i in range(6)]
    out, _ = run(FakeStore(lexical=lex), c=cfg(rerank_in=3, rerank_out=6),
                 reranker=Counting())
    assert Counting.n == 3
    assert [p.unit_id for p in out][:3] == ["U2", "U1", "U0"]
    assert [p.unit_id for p in out][3:] == ["U3", "U4", "U5"]  # unscored tail kept


def test_full_pipeline_order_of_traces():
    store = FakeStore(lexical=[P("A", score=3)], dense=[P("B")], links={"A": ["X"]})
    out, trace = run(store, c=cfg(expand=True), embedder=FakeEmbedder(),
                     reranker=LenReranker())
    assert stages(trace) == ["lexical", "dense", "expand", "rerank"]
    assert all(t.ms >= 0 for t in trace)
    assert [p.mark for p in out] == [f"t{i}" for i in range(1, len(out) + 1)]


# -------------------------------------------------------------------- early stop


def confident_lexical():
    # margin = (10 - 1) / 10 = 0.9 at rerank_out=3
    return [P("A", score=10), P("B", score=5), P("C", score=1), P("D", score=0.5)]


def test_lexical_margin_formula():
    lex = confident_lexical()
    assert lexical_margin(lex, 3) == pytest.approx(0.9)
    assert lexical_margin(lex, 2) == pytest.approx(0.5)
    assert lexical_margin(lex, 99) == pytest.approx(0.95)  # last item
    assert lexical_margin([P("A", score=3)], 3) == 0.0
    assert lexical_margin([], 3) == 0.0
    assert lexical_margin([P("A", score=0), P("B", score=0)], 2) == 0.0


def test_early_stop_triggers_and_is_recorded():
    store = FakeStore(lexical=confident_lexical(), dense=[P("Z")], links={"A": ["X"]})
    emb, rer = FakeEmbedder(), LenReranker()
    out, trace = run(store, c=cfg(early_stop=True, early_stop_margin=0.35, rerank_out=3,
                                  expand=True, rerank=False),
                     embedder=emb, reranker=rer)
    assert emb.seen == []  # no query embedded
    assert [c[0] for c in store.calls] == ["lexical"]
    assert [p.unit_id for p in out] == ["A", "B", "C"]
    assert stages(trace) == ["lexical", "dense", "expand"]
    assert "early stop" in trace[0].note and "margin" in trace[0].note
    assert trace[1].note == "skipped: early stop"
    assert trace[2].note == "skipped: early stop"
    assert trace[1].ms == 0 and trace[1].n_out == 4


def test_early_stop_still_reranks():
    lex = [P("A", score=10, text="a"), P("B", score=5, text="bbb"),
           P("C", score=1, text="cc"), P("D", score=.5, text="d")]
    out, trace = run(FakeStore(lexical=lex),
                     c=cfg(early_stop=True, rerank_out=3), reranker=LenReranker())
    assert [p.unit_id for p in out] == ["B", "C", "A"]
    assert stages(trace) == ["lexical", "rerank"]


def test_early_stop_not_triggered_when_margin_small():
    lex = [P("A", score=10), P("B", score=9.5), P("C", score=9), P("D", score=8)]
    store = FakeStore(lexical=lex, dense=[P("Z")])
    out, trace = run(store, c=cfg(early_stop=True, rerank_out=3), embedder=FakeEmbedder())
    assert "dense" in [c[0] for c in store.calls]
    assert "continue" in trace[0].note
    assert stages(trace) == ["lexical", "dense"] and trace[1].note != "skipped: early stop"


def test_early_stop_threshold_is_inclusive():
    # margin exactly 0.5 with threshold 0.5
    lex = [P("A", score=10), P("B", score=5)]
    store = FakeStore(lexical=lex, dense=[P("Z")])
    run(store, c=cfg(early_stop=True, early_stop_margin=0.5, rerank_out=2),
        embedder=FakeEmbedder())
    assert [c[0] for c in store.calls] == ["lexical"]


def test_early_stop_off_never_stops():
    store = FakeStore(lexical=confident_lexical(), dense=[P("Z")])
    _, trace = run(store, c=cfg(early_stop=False, rerank_out=3), embedder=FakeEmbedder())
    assert [c[0] for c in store.calls] == ["lexical", "dense"]
    assert "early stop off" in trace[0].note


def test_multi_hop_never_early_stops():
    store = FakeStore(lexical=confident_lexical(), dense=[P("Z")], links={"A": ["X"]})
    q = Query(text="q", intent="multi_hop")
    out, trace = run(store, q, cfg(early_stop=True, rerank_out=3, expand=True),
                     embedder=FakeEmbedder())
    assert [c[0] for c in store.calls] == ["lexical", "dense", "neighbours"]
    assert "multi_hop" in trace[0].note
    assert stages(trace) == ["lexical", "dense", "expand"]
    assert all("skipped" not in t.note for t in trace)


def test_scope_and_as_of_passed_through():
    seen = {}

    class S(FakeStore):
        def lexical(self, text, as_of, scope, k):
            seen["lex"] = (as_of, scope)
            return []

        def dense(self, vec, embedder_id, as_of, scope, k):
            seen["dense"] = (as_of, scope)
            return []

    q = Query(text="q", as_of=AsOf(valid="2020-01-01"), scope=Scope(source_ids=("s",)))
    run(S(), q, cfg(), embedder=FakeEmbedder())
    assert seen["lex"] == seen["dense"] == (q.as_of, q.scope)


# --------------------------------------------------------------- real store check


def test_integration_real_store():
    store_mod = pytest.importorskip("heuresis.store")
    from heuresis.fakes import HashEmbedder, OverlapReranker

    store = store_mod.Store(":memory:")
    texts = {
        "u1": "The annual limit for small companies is 4.8 million reais.",
        "u2": "Bananas are rich in potassium and grow in warm climates.",
        "u3": "Invoices must be issued within five days of the sale.",
    }
    store.add(
        sources=[Source(id="s")],
        units=[Unit(id=u, source_id="s") for u in texts],
        events=[Event(id=f"e-{u}", unit_id=u, op="create", date="2020-01-01",
                      text=t, recorded_at="2020-01-01") for u, t in texts.items()],
    )
    store.rebuild()
    emb = HashEmbedder()
    rows = store.missing_vectors(emb.id)
    vecs = emb.embed([r[2] for r in rows])
    store.put_vectors(emb.id, [(r[0], r[1], v) for r, v in zip(rows, vecs)])
    q = Query(text="limit for small companies", as_of=AsOf(valid="2024-01-01"))
    trace: list[StageTrace] = []
    out = cascade(store, q, RetrieveCfg(), embedder=emb, reranker=OverlapReranker(),
                  trace=trace)
    assert out and out[0].unit_id == "u1"
    assert [p.mark for p in out] == [f"t{i}" for i in range(1, len(out) + 1)]
    assert trace[0].stage == "lexical"
    # as-of invariant: nothing is in force before the create date
    early = Query(text="limit for small companies", as_of=AsOf(valid="2019-01-01"))
    assert cascade(store, early, RetrieveCfg(), embedder=emb, trace=[]) == []
    store.close()
