"""The systems under comparison, behind one interface.

Every system shares ONE generator LLM, ONE answer-format instruction, ONE output
cap (``config.draft.max_tokens``) and ONE corpus (a SQLite store built from the
dataset's corpus folder with the ``jsonl`` domain). The prompts below are the
pre-registered ones: changing any of them changes ``prompts_hash()``.

SQLite connections cannot cross threads, so each worker thread opens its own
connection to the same database file (``BenchContext.store`` / ``.engine``).
"""
from __future__ import annotations

import dataclasses
import hashlib
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from ..domains.jsonl import read_jsonl_folder
from ..fakes import EchoLLM
from ..ingest import ingest
from ..model import Answer, AsOf, Passage, Query, Scope, StageTrace, Usage
from ..retrieve import cascade
from ..store import Store
from ..surface.config import Config, load_config
from .ledger import Ledger, LedgerLLM
from .types import Dataset, Question

__all__ = [
    "ANSWER_FORMAT", "SYSTEM_NAMES", "Result", "System", "BenchContext", "build_context",
    "build_systems", "parse_reply", "prompts_hash", "prepare_corpus",
]

ANSWER_FORMAT = (
    "Answer in at most two short sentences; if the information is not sufficient, "
    "reply exactly ABSTAIN; end with a line `CONFIDENCE: <0-100>`."
)
CLOSED_SYSTEM = "Answer the question from your own knowledge. " + ANSWER_FORMAT
PASSAGES_SYSTEM = (
    "Answer ONLY from the passages provided; do not use outside knowledge. " + ANSWER_FORMAT
)
LONG_SYSTEM = (
    "Answer ONLY from the documents provided; do not use outside knowledge. " + ANSWER_FORMAT
)
AGENT_SYSTEM = (
    "You answer questions about a document collection with a search tool. To search, "
    "reply with exactly one line `SEARCH: <query>` and nothing else. You may search at "
    "most {n} times; after that you must answer. When you answer, use ONLY the passages "
    "found; do not use outside knowledge. " + ANSWER_FORMAT
)
AGENT_MORE = "Reply with exactly one line `SEARCH: <query>` to search again, or answer now."
AGENT_LAST = "No searches remain. Answer now."

SYSTEM_NAMES = ("closed_book", "bm25", "vector", "hybrid_rerank", "agentic",
                "long_context", "engine", "oracle")

_CONF = re.compile(r"^\s*CONFIDENCE\s*:\s*(\d+(?:\.\d+)?)\s*%?\s*$", re.I | re.M)
_SEARCH = re.compile(r"^\s*SEARCH\s*:\s*(.+?)\s*$", re.I)


def prompts_hash() -> str:
    parts = [ANSWER_FORMAT, CLOSED_SYSTEM, PASSAGES_SYSTEM, LONG_SYSTEM, AGENT_SYSTEM,
             AGENT_MORE, AGENT_LAST]
    return hashlib.sha256("\n\x00".join(parts).encode("utf-8")).hexdigest()


@dataclass
class Result:
    status: str                       # "answered" | "abstained"
    text: str = ""
    confidence: float = 0.5           # 0..1
    cited_units: tuple[str, ...] = ()  # units the system itself cited (engine only)
    usage: Usage = field(default_factory=Usage)   # tokens in/out and usd, summed
    ms: float = 0.0
    calls: int = 0                    # model calls
    searches: int = 0
    retrieved_units: tuple[str, ...] = ()  # units shown to the generator, in order
    note: str = ""


def parse_reply(raw: str) -> tuple[str, bool, float]:
    """(answer text without the CONFIDENCE line, abstained, confidence 0..1)."""
    conf = 0.5
    m = list(_CONF.finditer(raw))
    if m:
        conf = min(1.0, max(0.0, float(m[-1].group(1)) / 100.0))
    text = _CONF.sub("", raw).strip()
    head = re.sub(r"[^A-Za-z]+", " ", text).strip().upper()
    abstained = head.startswith("ABSTAIN") or head == ""
    return text, abstained, conf


# ----------------------------------------------------------------------------
# Context: shared models and corpus
# ----------------------------------------------------------------------------


def prepare_corpus(corpus_dir: str, db_path: str, embedder: Any) -> dict:
    """Ingest the corpus folder (jsonl domain) into ``db_path`` and embed it."""
    st = Store(db_path)
    try:
        counts = ingest(st, corpus_dir, "jsonl")
        rows = st.missing_vectors(embedder.id) if embedder is not None else []
        for i in range(0, len(rows), 64):
            chunk = rows[i:i + 64]
            vecs = embedder.embed([r[2] for r in chunk])
            st.put_vectors(embedder.id, [(r[0], r[1], vecs[j]) for j, r in enumerate(chunk)])
        counts["embedded"] = len(rows)
        return counts
    finally:
        st.close()


class BenchContext:
    def __init__(self, dataset: Dataset, db_path: str, *, llm: Any, embedder: Any,
                 reranker: Any, entailer: Any = None, config: Config | None = None,
                 ledger: Ledger | None = None, estimate_usd: float = 0.01):
        self.dataset = dataset
        self.db_path = str(db_path)
        self.llm = llm
        self.embedder = embedder
        self.reranker = reranker
        self.entailer = entailer
        self.config = config or load_config()
        self.ledger = ledger
        self.estimate_usd = estimate_usd
        self._tls = threading.local()
        self._open_lock = threading.Lock()
        self._llms: dict[str, Any] = {}

    @property
    def max_tokens(self) -> int:
        return self.config.draft.max_tokens

    def llm_for(self, tag: str) -> Any:
        """The shared generator, metered under ``tag`` when a ledger is set."""
        if self.ledger is None:
            return self.llm
        if tag not in self._llms:
            self._llms[tag] = LedgerLLM(self.llm, self.ledger, tag, self.estimate_usd)
        return self._llms[tag]

    def store(self) -> Store:
        st = getattr(self._tls, "store", None)
        if st is None:
            with self._open_lock:
                st = Store(self.db_path)
            self._tls.store = st
        return st

    def engine(self):
        eng = getattr(self._tls, "engine", None)
        if eng is None:
            from ..engine import Engine  # imported late: the engine is optional for baselines
            with self._open_lock:
                eng = Engine.open(self.db_path, "jsonl", config=self.config,
                                  llm=self.llm_for("engine"), embedder=self.embedder,
                                  reranker=self.reranker, entailer=self.entailer)
            self._tls.engine = eng
        return eng

    def models(self) -> dict:
        return {
            "generator": getattr(self.llm, "id", ""),
            "embedder": getattr(self.embedder, "id", None),
            "reranker": getattr(self.reranker, "id", None),
            "entailer": getattr(self.entailer, "id", None),
        }


def build_context(dataset: Dataset, db_path: str, *, llm: Any = None, embedder: Any = None,
                  reranker: Any = None, entailer: Any = None, config: Config | None = None,
                  ledger: Ledger | None = None, estimate_usd: float = 0.01,
                  prepare: bool = True) -> BenchContext:
    """Defaults to the offline fakes. Ingests and embeds the corpus into ``db_path``."""
    from ..fakes import HashEmbedder, OverlapReranker, RuleEntailer
    ctx = BenchContext(
        dataset, db_path,
        llm=llm if llm is not None else EchoLLM(),
        embedder=embedder if embedder is not None else HashEmbedder(),
        reranker=reranker if reranker is not None else OverlapReranker(),
        entailer=entailer if entailer is not None else RuleEntailer(),
        config=config, ledger=ledger, estimate_usd=estimate_usd,
    )
    if prepare:
        prepare_corpus(dataset.corpus_dir, db_path, ctx.embedder)
    return ctx


# ----------------------------------------------------------------------------
# Prompt helpers
# ----------------------------------------------------------------------------


def _span(p: Passage) -> str:
    return f"valid {p.valid_from or ''}..{p.valid_to or ''}"


def _passage_line(mark: str, p: Passage) -> str:
    return f"[{mark}] ({p.title}; {_span(p)}) {' '.join(p.text.split())}"


def _fit(passages: list[Passage], max_chars: int) -> list[Passage]:
    out, used = [], 0
    for p in passages:
        used += len(p.text) + len(p.title) + 40
        if out and used > max_chars:
            break
        out.append(p)
    return out


def passages_prompt(question: str, passages: list[Passage], as_of: str | None = None,
                    header: str = "Passages:") -> str:
    lines = []
    if as_of:
        lines.append(f"As-of date: {as_of}")
    lines.append(header)
    if passages:
        lines += [_passage_line(f"t{i}", p) for i, p in enumerate(passages, 1)]
    else:
        lines.append("(none)")
    lines.append(f"Question: {question}")
    return "\n".join(lines)


class _Meter:
    """Totals the model calls of one answer."""

    def __init__(self, llm: Any, max_tokens: int):
        self.llm, self.max_tokens = llm, max_tokens
        self.usage = Usage(model=getattr(llm, "id", ""))
        self.calls = 0
        self.searches = 0

    def call(self, system: str, prompt: str) -> str:
        text, u = self.llm.complete(system, prompt, max_tokens=self.max_tokens)
        self.calls += 1
        self.usage.tokens_in += u.tokens_in
        self.usage.tokens_out += u.tokens_out
        self.usage.tokens_cached += u.tokens_cached
        self.usage.usd += u.usd
        self.usage.ms += u.ms
        return text


# ----------------------------------------------------------------------------
# Systems
# ----------------------------------------------------------------------------


class System:
    name = "system"
    available = True
    reason = ""
    time_aware = False
    cites = False

    def __init__(self, ctx: BenchContext, *, time_aware: bool = False):
        self.ctx = ctx
        self.time_aware = time_aware

    def describe(self) -> dict:
        return {"name": self.name, "available": self.available, "reason": self.reason,
                "time_aware": self.time_aware, **self.params()}

    def params(self) -> dict:
        return {}

    def as_of(self, q: Question) -> AsOf:
        """Baselines search as of today unless built time-aware."""
        return AsOf(valid=q.as_of) if (self.time_aware and q.as_of) else AsOf()

    def answer(self, question: Question) -> Result:
        if not self.available:
            raise RuntimeError(f"system {self.name} is not available: {self.reason}")
        t0 = time.perf_counter()
        res = self._answer(question)
        if self.name != "engine":
            res.ms = (time.perf_counter() - t0) * 1000.0
        return res

    def _answer(self, q: Question) -> Result:  # pragma: no cover - abstract
        raise NotImplementedError

    # shared tail: one generation call over a prepared prompt
    def _generate(self, system: str, prompt: str, passages: list[Passage],
                  searches: int = 0) -> Result:
        m = _Meter(self.ctx.llm_for(self.name), self.ctx.max_tokens)
        raw = m.call(system, prompt)
        return self._finish(raw, m, passages, searches)

    @staticmethod
    def _finish(raw: str, m: _Meter, passages: list[Passage], searches: int,
                note: str = "") -> Result:
        text, abstained, conf = parse_reply(raw)
        return Result(status="abstained" if abstained else "answered", text=text,
                      confidence=conf, usage=m.usage, calls=m.calls, searches=searches,
                      retrieved_units=tuple(dict.fromkeys(p.unit_id for p in passages)),
                      note=note)


class ClosedBook(System):
    name = "closed_book"

    def _answer(self, q: Question) -> Result:
        return self._generate(CLOSED_SYSTEM, f"Question: {q.text}", [])


class _Retrieving(System):
    def __init__(self, ctx: BenchContext, *, k: int = 8, time_aware: bool = False):
        super().__init__(ctx, time_aware=time_aware)
        self.k = k

    def params(self) -> dict:
        return {"k": self.k}

    def retrieve(self, text: str, q: Question, k: int | None = None) -> list[Passage]:
        raise NotImplementedError

    def _answer(self, q: Question) -> Result:
        ps = _fit(self.retrieve(q.text, q), self.ctx.config.draft.max_context_chars)
        ps = [dataclasses.replace(p, mark=f"t{i}") for i, p in enumerate(ps, 1)]
        prompt = passages_prompt(q.text, ps, q.as_of if self.time_aware else None)
        return self._generate(PASSAGES_SYSTEM, prompt, ps, searches=1)


class BM25(_Retrieving):
    name = "bm25"

    def retrieve(self, text, q, k=None):
        return self.ctx.store().lexical(text, self.as_of(q), Scope(), k or self.k)


class Vector(_Retrieving):
    name = "vector"

    def retrieve(self, text, q, k=None):
        vec = self.ctx.embedder.embed([text], is_query=True)[0]
        return self.ctx.store().dense(vec, self.ctx.embedder.id, self.as_of(q), Scope(),
                                      k or self.k)


class HybridRerank(_Retrieving):
    name = "hybrid_rerank"

    def retrieve(self, text, q, k=None):
        cfg = dataclasses.replace(
            self.ctx.config.retrieve, early_stop=False, dense=True, rerank=True,
            expand=False, rewrite=False, second_round=False, rerank_out=k or self.k)
        query = Query(text=text, as_of=self.as_of(q))
        return cascade(self.ctx.store(), query, cfg, embedder=self.ctx.embedder,
                       reranker=self.ctx.reranker, trace=[])


class Agentic(HybridRerank):
    name = "agentic"

    def __init__(self, ctx: BenchContext, *, k: int = 5, max_actions: int = 4,
                 time_aware: bool = False):
        super().__init__(ctx, k=k, time_aware=time_aware)
        self.max_actions = max_actions

    def params(self) -> dict:
        return {"k": self.k, "max_actions": self.max_actions}

    def _answer(self, q: Question) -> Result:
        n = self.max_actions
        m = _Meter(self.ctx.llm_for(self.name), self.ctx.max_tokens)
        system = AGENT_SYSTEM.format(n=n)
        seen: dict[tuple[str, int], Passage] = {}
        blocks: list[str] = []
        shown: list[Passage] = []
        raw, note = "", ""
        head = [f"Question: {q.text}"]
        if self.time_aware and q.as_of:
            head.insert(0, f"As-of date: {q.as_of}")
        for turn in range(n + 1):
            left = n - m.searches
            prompt = "\n".join(
                head + [f"Searches used: {m.searches} of {n}."] + blocks
                + [AGENT_MORE if left > 0 else AGENT_LAST])
            raw = m.call(system, prompt)
            first = next((ln for ln in raw.splitlines() if ln.strip()), "")
            sm = _SEARCH.match(first)
            if sm is None:
                return self._finish(raw, m, shown, m.searches)
            if left <= 0:  # the model asked to search with no actions left
                note = "action cap reached without an answer"
                return Result(status="abstained", text="", confidence=0.0, usage=m.usage,
                              calls=m.calls, searches=m.searches, note=note,
                              retrieved_units=tuple(dict.fromkeys(p.unit_id for p in shown)))
            query_text = sm.group(1)
            m.searches += 1
            found = _fit(self.retrieve(query_text, q), self.ctx.config.draft.max_context_chars)
            lines = [f"Search {m.searches}: {query_text}", "Passages:"]
            new = 0
            for p in found:
                key = (p.unit_id, p.seq)
                if key in seen:
                    continue
                seen[key] = p
                shown.append(p)
                new += 1
                lines.append(_passage_line(f"t{len(shown)}", p))
            if not new:
                lines.append("(no new passages)")
            blocks.append("\n".join(lines))
        return Result(status="abstained", text="", confidence=0.0, usage=m.usage,
                      calls=m.calls, searches=m.searches, note="loop ended")  # unreachable


class LongContext(System):
    name = "long_context"

    def __init__(self, ctx: BenchContext, *, limit_tokens: int = 90_000, time_aware: bool = False):
        super().__init__(ctx, time_aware=time_aware)
        self.limit_tokens = limit_tokens
        n = ctx.dataset.corpus_tokens
        if n >= limit_tokens:
            self.available = False
            self.reason = f"corpus is about {n} tokens, limit is {limit_tokens}"
        self._unit_ids: list[str] | None = None
        self._cache: dict[str | None, list[Passage]] = {}
        self._lock = threading.Lock()

    def params(self) -> dict:
        return {"limit_tokens": self.limit_tokens}

    def _docs(self, q: Question) -> list[Passage]:
        key = q.as_of if self.time_aware else None
        with self._lock:
            if self._unit_ids is None:
                _, units, _, _ = read_jsonl_folder(self.ctx.dataset.corpus_dir)
                self._unit_ids = sorted(u.id for u in units)
            if key not in self._cache:
                st, asof, docs = self.ctx.store(), self.as_of(q), []
                for uid in self._unit_ids:
                    v = st.text_at(uid, asof)
                    if v is not None:
                        docs.append(Passage(unit_id=uid, seq=v.seq, text=v.text,
                                            title=uid, valid_from=v.valid_from,
                                            valid_to=v.valid_to))
                self._cache[key] = docs
            return self._cache[key]

    def _answer(self, q: Question) -> Result:
        docs = self._docs(q)
        prompt = passages_prompt(q.text, docs, q.as_of if self.time_aware else None,
                                 header="Documents:")
        return self._generate(LONG_SYSTEM, prompt, docs)


class Oracle(System):
    name = "oracle"
    time_aware = True

    def __init__(self, ctx: BenchContext, **_: Any):
        super().__init__(ctx, time_aware=True)

    def _answer(self, q: Question) -> Result:
        st, ps = self.ctx.store(), []
        for uid in q.gold_units:
            v = st.text_at(uid, AsOf(valid=q.as_of)) if q.as_of else st.text_at(uid, AsOf())
            if v is None:
                vs = st.versions(uid)
                v = vs[-1] if vs else None
            if v is not None:
                ps.append(Passage(unit_id=uid, seq=v.seq, text=v.text, title=uid,
                                  valid_from=v.valid_from, valid_to=v.valid_to))
        prompt = passages_prompt(q.text, ps, q.as_of)
        return self._generate(PASSAGES_SYSTEM, prompt, ps)


class EngineSystem(System):
    name = "engine"
    cites = True

    def __init__(self, ctx: BenchContext, **_: Any):
        super().__init__(ctx, time_aware=True)

    def _answer(self, q: Question) -> Result:
        ans: Answer = self.ctx.engine().ask(q.text, as_of=AsOf(valid=q.as_of) if q.as_of else None)
        tr: list[StageTrace] = ans.trace
        usage = Usage(model=getattr(self.ctx.llm, "id", ""),
                      tokens_in=sum(t.tokens_in for t in tr),
                      tokens_out=sum(t.tokens_out for t in tr), usd=ans.usd, ms=ans.ms)
        searches = sum(1 for t in tr if t.stage == "lexical") or (1 if tr else 0)
        return Result(
            status="answered" if ans.status in ("answered", "partial") else "abstained",
            text=ans.text, confidence=min(1.0, max(0.0, float(ans.grade))),
            cited_units=tuple(dict.fromkeys(u for u, _ in ans.citations)),
            usage=usage, ms=ans.ms,
            calls=sum(1 for t in tr if t.tokens_in > 0 or t.tokens_out > 0),
            searches=searches,
            retrieved_units=tuple(dict.fromkeys(p.unit_id for p in ans.passages)),
            note=f"engine status={ans.status}"
                 + (f"; abstention={ans.abstention.type}" if ans.abstention else ""))


_CLASSES: dict[str, Callable[..., System]] = {
    "closed_book": ClosedBook, "bm25": BM25, "vector": Vector, "hybrid_rerank": HybridRerank,
    "agentic": Agentic, "long_context": LongContext, "engine": EngineSystem, "oracle": Oracle,
}


def build_systems(ctx: BenchContext, names: tuple[str, ...] | list[str] = SYSTEM_NAMES, *,
                  k: int = 8, agent_k: int = 5, max_actions: int = 4,
                  time_aware: bool = False, long_context_limit: int = 90_000) -> list[System]:
    """Build the named systems. ``time_aware`` applies to baselines 2-6 only."""
    out: list[System] = []
    for n in names:
        if n not in _CLASSES:
            raise ValueError(f"unknown system {n!r}; known: {', '.join(SYSTEM_NAMES)}")
        if n == "closed_book":
            s = ClosedBook(ctx)
        elif n in ("bm25", "vector", "hybrid_rerank"):
            s = _CLASSES[n](ctx, k=k, time_aware=time_aware)
        elif n == "agentic":
            s = Agentic(ctx, k=agent_k, max_actions=max_actions, time_aware=time_aware)
        elif n == "long_context":
            s = LongContext(ctx, limit_tokens=long_context_limit, time_aware=time_aware)
        else:
            s = _CLASSES[n](ctx)
        out.append(s)
    return out
