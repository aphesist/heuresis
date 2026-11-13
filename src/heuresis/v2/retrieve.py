"""v2 retrieval: lexical first, optional term expansion, optional dense fusion, optional edges.

Every call takes the date and scope from the ``Query`` (never from the model) and the store
applies both inside SQL. Passages returned here carry no marks: the caller's evidence
assigns them.
"""
from __future__ import annotations

import math
import re
import time
import unicodedata
from dataclasses import replace
from typing import Any, Iterable

from ..interfaces import Reference, domain_references
from ..model import AsOf, Passage, Query, Scope, StageTrace
from ..retrieve import rrf

__all__ = ["search", "lookup", "open_unit", "expansion_terms", "unit_in_scope", "in_scope"]

_STOP = frozenset("""
about above after again against also among because been before being below between both but
could did does doing down during each from further have having here hers herself himself into
itself just more most myself once only other ought ours ourselves over same should some such
than that their theirs them themselves then there these they this those through under until
very was were what when where which while whom why will with would your yours yourself
yourselves shall may might must can cannot per via within without upon
ainda algum alguma algumas alguns ante apos aquela aquelas aquele aqueles aquilo assim
com como contra cada dele dela deles delas depois desde dessa desse desta deste dos das
ela elas ele eles entre essa essas esse esses esta estas este estes estao foi foram fosse
havia isso isto mais mas mesmo meu minha muito nas nao nem nos nossa nosso num numa pela
pelas pelo pelos pelas para pode podem por qual quais quando que quem sao sem sera seu sua
suas seus sobre tambem tem tendo ter uma umas uns voce voces
""".split())


def _fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"
    )


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _key(p: Passage) -> tuple[str, int]:
    return (p.unit_id, p.seq)


def _dedup(passages: Iterable[Passage]) -> list[Passage]:
    seen: set[tuple[str, int]] = set()
    out: list[Passage] = []
    for p in passages:
        if _key(p) not in seen:
            seen.add(_key(p))
            out.append(p)
    return out


def unit_in_scope(store, unit_id: str, scope: Scope | None) -> bool:
    """True when ``unit_id`` lies inside ``scope`` (source ids, unit kinds, id prefix). An empty
    scope allows everything; a unit that cannot be looked up is outside any non-empty scope."""
    if scope is None or not (scope.source_ids or scope.kinds or scope.unit_prefix):
        return True
    if scope.unit_prefix and not unit_id.startswith(scope.unit_prefix):
        return False
    if not (scope.source_ids or scope.kinds):
        return True
    try:
        row = store._con.execute("SELECT source_id, kind FROM units WHERE id=?",
                                 (unit_id,)).fetchone()
    except Exception:
        return False
    if row is None:
        return False
    if scope.source_ids and row[0] not in scope.source_ids:
        return False
    return not scope.kinds or row[1] in scope.kinds


def in_scope(store, p: Passage, scope: Scope | None) -> bool:
    return unit_in_scope(store, p.unit_id, scope)


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


def expansion_terms(question: str, passages: list[Passage], n_terms: int,
                    n_docs: int) -> list[str]:
    """Corpus-vocabulary terms to add to the question.

    ``passages`` is the whole first-pass pool, best first; the candidate terms come from the
    titles and text of its top ``n_docs``. Score = term frequency in those passages times
    ``log(pool / (1 + pool passages containing the term))``. Question terms (accent-
    insensitive), stop words, tokens under 4 characters and digit-only tokens are dropped.
    Ties break by term, so the result is deterministic.
    """
    if n_terms <= 0 or n_docs <= 0 or not passages:
        return []
    banned = {_fold(t) for t in _tokens(question)}

    def ok(tok: str) -> bool:
        f = _fold(tok)
        return len(tok) >= 4 and not tok.isdigit() and f not in _STOP and f not in banned

    def toks(p: Passage) -> list[str]:
        return [t for t in _tokens(f"{p.title} {p.text}") if ok(t)]

    pool = len(passages)
    df: dict[str, int] = {}
    for p in passages:
        for f in {_fold(t) for t in toks(p)}:
            df[f] = df.get(f, 0) + 1
    tf: dict[str, int] = {}
    shown: dict[str, str] = {}
    for p in passages[:n_docs]:
        for t in toks(p):
            f = _fold(t)
            tf[f] = tf.get(f, 0) + 1
            shown.setdefault(f, t)
    scored = [(-(n * math.log(pool / (1 + df.get(f, 0)))), shown[f]) for f, n in tf.items()]
    scored.sort()
    return [t for _s, t in scored[:n_terms]]


def _convex(lex: list[Passage], dense: list[Passage], alpha: float) -> list[Passage]:
    def norm(lst: list[Passage]) -> dict[tuple[str, int], float]:
        if not lst:
            return {}
        lo = min(p.score for p in lst)
        hi = max(p.score for p in lst)
        if hi <= lo:
            return {_key(p): 1.0 for p in lst}
        return {_key(p): (p.score - lo) / (hi - lo) for p in lst}

    nl, nd = norm(lex), norm(dense)
    first: dict[tuple[str, int], Passage] = {}
    for p in [*lex, *dense]:
        first.setdefault(_key(p), p)
    scores = {key: alpha * nl.get(key, 0.0) + (1.0 - alpha) * nd.get(key, 0.0) for key in first}
    order = sorted(first, key=lambda key: -scores[key])  # stable: first-seen on ties
    return [replace(first[key], score=scores[key], stage="fused") for key in order]


def search(store, query: Query, cfg: dict, *, embedder=None, trace: list | None = None,
           k: int | None = None, exclude: set[tuple[str, int]] = frozenset()) -> list[Passage]:
    """Passages for ``query`` in force at ``query.as_of`` within ``query.scope``, at most
    ``k`` (default ``cfg["k_first"]``), none of them in ``exclude``, without marks."""
    k = int(cfg["k_first"]) if k is None else int(k)
    rrf_k = int(cfg.get("rrf_k", 60))
    as_of, scope = query.as_of, query.scope

    t0 = time.perf_counter()
    current = _dedup(store.lexical(query.text, as_of, scope, int(cfg["k_lexical"])))
    if trace is not None:
        trace.append(StageTrace(stage="lexical", ms=_ms(t0), n_out=len(current)))

    n_terms = int(cfg.get("prf_terms", 0))
    if n_terms > 0 and current:
        t0 = time.perf_counter()
        terms = expansion_terms(query.text, current, n_terms, int(cfg.get("prf_docs", 3)))
        added = 0
        if terms:
            second = _dedup(store.lexical(query.text + " " + " ".join(terms), as_of, scope,
                                          int(cfg["k_lexical"])))
            merged = rrf([current, second], k=rrf_k)
            added = len({_key(p) for p in merged} - {_key(p) for p in current})
            current = merged
        if trace is not None:
            trace.append(StageTrace(stage="expand_terms", ms=_ms(t0), n_out=len(current),
                                    note=f"terms={' '.join(terms)}; added={added}"))

    fusion = cfg.get("fusion", "none")
    if fusion != "none" and embedder is not None:
        t0 = time.perf_counter()
        vec = embedder.embed([query.text], is_query=True)[0]
        dense = _dedup(store.dense(vec, embedder.id, as_of, scope, int(cfg["k_dense"])))
        if fusion == "convex":
            current = _convex(current, dense, float(cfg.get("alpha", 0.7)))
        else:
            current = rrf([current, dense], k=rrf_k)
        if trace is not None:
            trace.append(StageTrace(stage="dense", ms=_ms(t0), n_out=len(current),
                                    note=f"dense={len(dense)}; fused by {fusion}"))

    current = [p for p in current if _key(p) not in exclude]
    out = current[:k]

    if cfg.get("edge_expand") and out:
        t0 = time.perf_counter()
        seen = {_key(p) for p in current} | set(exclude)
        extra: list[Passage] = []
        for p in store.neighbours([p.unit_id for p in out], as_of):
            if _key(p) not in seen and in_scope(store, p, scope):
                seen.add(_key(p))
                extra.append(replace(p, stage="expand", score=0.0))
        out = (out + extra)[:k]
        if trace is not None:
            trace.append(StageTrace(stage="edges", ms=_ms(t0), n_out=len(out),
                                    note=f"neighbours={len(extra)}"))
    return [replace(p, mark="") for p in out]


def lookup(store, domain, text: str, as_of: AsOf, scope: Scope | None = None
           ) -> tuple[list[Passage], list[Reference]]:
    """Provisions the text names, as in force at ``as_of`` and inside ``scope``; and the
    references found."""
    refs = domain_references(domain, text, store) if domain is not None else []
    out: list[Passage] = []
    seen: set[str] = set()
    for r in refs:
        if r.status != "resolved":
            continue
        for uid in r.unit_ids:
            if uid in seen:
                continue
            seen.add(uid)
            p = store.passage_at(uid, as_of)
            if p is not None and in_scope(store, p, scope):
                out.append(p)
    return out, refs


def open_unit(store, unit_id: str, as_of: AsOf, radius: int,
              scope: Scope | None = None) -> list[Passage]:
    """The unit in force at ``as_of`` followed by its neighbours, all inside ``scope``; empty
    when nothing is in force or the unit is out of scope (the neighbours are then not shown
    either)."""
    if not unit_in_scope(store, unit_id, scope):
        return []
    p = store.passage_at(unit_id, as_of)
    if p is None:
        return []
    return [replace(p, stage="open"),
            *[q for q in store.adjacent(unit_id, as_of, radius) if in_scope(store, q, scope)]]
