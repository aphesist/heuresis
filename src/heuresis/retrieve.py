"""The retrieval cascade: cheapest stage first, stop early when it is confident.

Order: lexical, early-stop test, dense + reciprocal rank fusion, graph expansion,
rerank. Each stage that runs appends one ``StageTrace``; a stage that the early
stop skipped appends one with note ``"skipped: early stop"``.

Early-stop confidence
---------------------
Let ``s1`` be the lexical score at rank 1 and ``sR`` the score at rank
``R = cfg.rerank_out`` (the last item if the list is shorter than R). Then::

    margin = (s1 - sR) / s1        if s1 > 0 and the list has at least 2 items
    margin = 0                     otherwise

The list is confident when ``margin >= cfg.early_stop_margin``. In words: the
best hit stands well clear of the hits that would still make the final cut, so
adding a second retriever is unlikely to change what is returned. The test
assumes higher scores are better and non-negative (the store converts BM25 to
that convention). It is never applied to ``query.intent == "multi_hop"``, where
the answer needs documents a lexical match on the question does not reach.

When the early stop fires, the retrieval legs (dense and expand) are skipped.
The rerank stage, if enabled, still runs over the lexical list.
"""
from __future__ import annotations

import time
from dataclasses import replace
from typing import Sequence

from .model import Passage, Query, StageTrace

__all__ = ["rrf", "cascade", "lexical_margin"]


def _key(p: Passage) -> tuple[str, int]:
    return (p.unit_id, p.seq)


def rrf(lists: Sequence[Sequence[Passage]], k: int = 60) -> list[Passage]:
    """Reciprocal rank fusion keyed by (unit_id, seq).

    ``score(d) = sum over lists of 1 / (k + rank)`` with rank starting at 1.
    Returns new passages (inputs are not modified) with ``stage="fused"`` and
    the fused score, best first; ties keep first-seen order. The passage fields
    other than stage and score come from the first list that contains it.
    """
    scores: dict[tuple[str, int], float] = {}
    first: dict[tuple[str, int], Passage] = {}
    for lst in lists:
        seen: set[tuple[str, int]] = set()
        rank = 0
        for p in lst:
            key = _key(p)
            if key in seen:
                continue
            seen.add(key)
            rank += 1
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            first.setdefault(key, p)
    order = sorted(scores, key=lambda key: -scores[key])  # stable: first-seen on ties
    return [replace(first[key], score=scores[key], stage="fused") for key in order]


def lexical_margin(passages: Sequence[Passage], rerank_out: int) -> float:
    """Normalised gap between rank 1 and rank ``rerank_out``; see module doc."""
    if len(passages) < 2:
        return 0.0
    s1 = passages[0].score
    if s1 <= 0:
        return 0.0
    sr = passages[min(rerank_out, len(passages)) - 1].score
    return (s1 - sr) / s1


def _dedup(passages: Sequence[Passage]) -> list[Passage]:
    seen: set[tuple[str, int]] = set()
    out: list[Passage] = []
    for p in passages:
        if _key(p) not in seen:
            seen.add(_key(p))
            out.append(p)
    return out


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


def cascade(store, query: Query, cfg, *, embedder=None, reranker=None,
            trace: list[StageTrace]) -> list[Passage]:
    """Run the cascade and return at most ``cfg.rerank_out`` passages, marked
    ``t1..tn``. Works with ``embedder=None`` and ``reranker=None`` (lexical only).
    """
    # 1. lexical
    t0 = time.perf_counter()
    current = _dedup(store.lexical(query.text, query.as_of, query.scope, cfg.k_lexical))
    margin = lexical_margin(current, cfg.rerank_out)

    # 2. early-stop test
    stopped = False
    if not cfg.early_stop:
        decision = "early stop off"
    elif query.intent == "multi_hop":
        decision = "no early stop: multi_hop"
    elif margin >= cfg.early_stop_margin:
        stopped = True
        decision = f"early stop: margin {margin:.3f} >= {cfg.early_stop_margin}"
    else:
        decision = f"continue: margin {margin:.3f} < {cfg.early_stop_margin}"
    trace.append(StageTrace(stage="lexical", ms=_ms(t0), n_out=len(current),
                            note=f"margin={margin:.3f}; {decision}"))

    # 3. dense + RRF
    if cfg.dense and embedder is not None:
        if stopped:
            trace.append(StageTrace(stage="dense", n_out=len(current),
                                    note="skipped: early stop"))
        else:
            t0 = time.perf_counter()
            vec = embedder.embed([query.text], is_query=True)[0]
            dense = _dedup(store.dense(vec, embedder.id, query.as_of, query.scope,
                                       cfg.k_dense))
            current = rrf([current, dense], k=cfg.rrf_k)
            trace.append(StageTrace(stage="dense", ms=_ms(t0), n_out=len(current),
                                    note=f"dense={len(dense)}; fused by rrf k={cfg.rrf_k}"))

    # 4. expand
    if cfg.expand:
        if stopped:
            trace.append(StageTrace(stage="expand", n_out=len(current),
                                    note="skipped: early stop"))
        else:
            t0 = time.perf_counter()
            seen = {_key(p) for p in current}
            frontier = [p.unit_id for p in current[:cfg.rerank_out]]
            visited = set(frontier)
            added = 0
            for _ in range(max(cfg.expand_hops, 0)):
                if not frontier:
                    break
                nxt: list[str] = []
                for p in store.neighbours(frontier, query.as_of):
                    if _key(p) in seen:
                        continue
                    seen.add(_key(p))
                    # Score 0.0 marks "reached by link, not by score"; order is
                    # what matters: these sit below every fused passage.
                    current.append(replace(p, stage="expand", score=0.0))
                    added += 1
                    if p.unit_id not in visited:
                        visited.add(p.unit_id)
                        nxt.append(p.unit_id)
                frontier = nxt
            trace.append(StageTrace(stage="expand", ms=_ms(t0), n_out=len(current),
                                    note=f"added={added}; hops={cfg.expand_hops}"))

    # 5. rerank
    if cfg.rerank and reranker is not None:
        t0 = time.perf_counter()
        head, tail = current[:cfg.rerank_in], current[cfg.rerank_in:]
        scores = reranker.score(query.text, [p.text for p in head]) if head else []
        ranked = sorted(zip(head, scores), key=lambda ps: -ps[1])  # stable
        current = [replace(p, score=float(s), stage="rerank") for p, s in ranked] + tail
        trace.append(StageTrace(stage="rerank", ms=_ms(t0), n_out=len(current),
                                note=f"scored={len(head)}"))

    final = _dedup(current)[:cfg.rerank_out]
    return [replace(p, mark=f"t{i}") for i, p in enumerate(final, 1)]
