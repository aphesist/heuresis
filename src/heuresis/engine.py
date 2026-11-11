"""The engine: wires understand, retrieve, draft, tools, verify and decide.

Stage names written to ``Answer.trace``: ``understand``, the retrieval stages
(``lexical``, ``dense``, ``expand``, ``rerank``, appended by the cascade),
``retrieve`` (summary), ``draft``, ``tools``, ``draft_followup`` (only after a
``sql`` call), ``verify``, ``decide`` and ``assemble``.
"""
from __future__ import annotations

import dataclasses
import json
import os
import time
from typing import Any

from . import draft as draft_mod
from . import retrieve as retrieve_mod
from . import router as router_mod
from . import tools as tools_mod
from .domains import get_domain
from .fakes import EchoLLM, RuleEntailer
from .ingest import ingest as _ingest
from .llm import BudgetExceeded
from .locked.decide import decide
from .locked.verify import verify as _verify
from .model import (
    Abstention,
    Answer,
    AsOf,
    Claim,
    Passage,
    Query,
    Scope,
    StageTrace,
    ToolResult,
    Version,
)
from .store import Store
from .surface.config import Config, load_config

_DEFAULT_CALL_USD = 0.002
_STATEFUL_DOMAINS = ("tables", "legal_br")

_DEFAULT_TEXT = {
    "no_source": "No relevant source was found.",
    "not_valid_at_date": "Sources exist, but none was in force at the requested date.",
    "conflict": "Sources of equal authority disagree.",
    "false_premise": "The question assumes something the sources contradict.",
    "outside_coverage": "The corpus does not cover this subject.",
    "unsupported": "An answer was drafted but could not be verified.",
    "needs_input": "More information is needed to answer.",
    "tool_failed": "A required computation could not be done.",
    "out_of_scope": "This is not a question for this corpus.",
    "budget": "The cost budget ran out before an answer could be verified.",
}


class _Appender:
    """Wraps an LLM so the prompt carries extra text (the tool results)."""

    def __init__(self, inner: Any, extra: str):
        self.inner, self.extra = inner, extra
        self.id = getattr(inner, "id", "")

    def complete(self, system: str, prompt: str, *, max_tokens: int = 600):
        return self.inner.complete(system, prompt + self.extra, max_tokens=max_tokens)


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


def _span(p: Passage) -> str:
    return f"{p.unit_id} [{p.valid_from or ''}..{p.valid_to or ''})"


class Engine:
    def __init__(self, store: Store, domain: Any, config: Config, llm: Any, embedder: Any,
                 reranker: Any, entailer: Any, classifier: Any):
        self.store = store
        self.domain = domain
        self.config = config
        self.llm = llm
        self.embedder = embedder
        self.reranker = reranker
        self.entailer = entailer
        self.classifier = classifier
        self._sql_db: str | None = None

    # -- lifecycle -----------------------------------------------------------

    @classmethod
    def open(cls, path: str, domain: Any = None, *, config: Config | None = None,
             llm: Any = None, embedder: Any = None, reranker: Any = None,
             entailer: Any = None, classifier: Any = None) -> "Engine":
        store = Store(str(path))
        try:
            stored = store.meta_get("domain")
            if domain is None:
                dom = get_domain(stored or "text")
            else:
                dom = get_domain(domain) if isinstance(domain, str) else domain
                if stored and stored != dom.name and store.stats().get("units", 0) > 0:
                    raise ValueError(
                        f"database {path} holds domain {stored!r}, not {dom.name!r}"
                    )
        except Exception:
            store.close()
            raise
        eng = cls(store, dom, config or load_config(),
                  llm if llm is not None else EchoLLM(), embedder, reranker,
                  entailer if entailer is not None else RuleEntailer(), classifier)
        eng.store.meta_set("domain", dom.name)
        if dom.name in _STATEFUL_DOMAINS:
            for p in eng._paths():
                try:
                    dom.read(p)  # restores the plug-in's corpus state; nothing is stored
                except Exception:
                    pass  # the path may have gone; the rules then simply do not fire
        eng._bind_sql_db()
        return eng

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "Engine":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _paths(self) -> list[str]:
        try:
            v = json.loads(self.store.meta_get("paths") or "[]")
        except ValueError:
            return []
        return [x for x in v if isinstance(x, str)]

    def _bind_sql_db(self) -> None:
        if self.domain.name == "tables":
            paths = self._paths()
            self._sql_db = paths[-1] if paths else None

    # -- corpus --------------------------------------------------------------

    def ingest(self, path: str) -> dict:
        path = os.path.abspath(str(path))
        result = _ingest(self.store, path, self.domain)
        paths = self._paths()
        if path not in paths:
            paths.append(path)
        self.store.meta_set("paths", json.dumps(paths))
        self._bind_sql_db()
        return result

    def index(self, batch: int = 64) -> int:
        if self.embedder is None:
            return 0
        rows = self.store.missing_vectors(self.embedder.id)
        for i in range(0, len(rows), batch):
            chunk = rows[i:i + batch]
            vecs = self.embedder.embed([r[2] for r in chunk])
            self.store.put_vectors(self.embedder.id,
                                   [(r[0], r[1], vecs[j]) for j, r in enumerate(chunk)])
        return len(rows)

    # -- reading -------------------------------------------------------------

    def _understand(self, question: str, as_of: AsOf | None, scope: Scope | None) -> Query:
        return router_mod.understand(question, cfg=self.config.router,
                                     rules=self.domain.rules(), classifier=self.classifier,
                                     as_of=as_of, scope=scope)

    def search(self, question: str, as_of: AsOf | None = None, scope: Scope | None = None,
               k: int = 10) -> list[Passage]:
        q = self._understand(question, as_of, scope)
        cfg = dataclasses.replace(self.config.retrieve, rerank_out=k)
        return retrieve_mod.cascade(self.store, q, cfg, embedder=self.embedder,
                                    reranker=self.reranker, trace=[])

    def verify(self, text: str, passages: list[Passage], as_of: AsOf | None = None) -> list[Claim]:
        d = draft_mod.parse_draft(text)
        ps = [p if p.mark else dataclasses.replace(p, mark=f"t{i}")
              for i, p in enumerate(passages, 1)]
        return _verify(d, ps, [], self.store, as_of or AsOf(), self.entailer, self.config.verify)

    def unit(self, unit_id: str, as_of: AsOf | None = None) -> Version | None:
        return self.store.text_at(unit_id, as_of or AsOf())

    # -- ask -----------------------------------------------------------------

    def _tools(self) -> list[Any]:
        own = list(self.domain.tools())
        names = {t.name for t in own}
        return own + [t for t in tools_mod.default_tools()
                      if t.name not in names and t.name != "sql"]

    def _run_calls(self, tools: list[Any], calls: list[Any]) -> list[ToolResult]:
        out: list[ToolResult] = []
        for i, call in enumerate(calls):
            if isinstance(call, dict) and call.get("tool") == "sql":
                # Arguments are model-written: the database is never taken from them.
                args = call.get("args") if isinstance(call.get("args"), dict) else {}
                mark = call.get("mark") if isinstance(call.get("mark"), str) else f"k{i + 1}"
                has_sql = any(t.name == "sql" for t in tools)
                if self._sql_db is None or not has_sql:
                    shown = {k: v for k, v in args.items() if k != "db"}
                    out.append(ToolResult(mark, "sql", shown, False,
                                          error="no database is known to this engine"))
                    continue
                call = {**call, "args": {**args, "db": self._sql_db}}
            out.extend(tools_mod.run_calls(tools, [call]))
        return out

    @staticmethod
    def _results_text(results: list[ToolResult]) -> str:
        lines = ["", "Tool results:"]
        for r in results:
            body = repr(r.value) if r.ok else f"failed: {r.error}"
            lines.append(f"[{r.mark}] {r.tool}: {body[:2000]}")
        lines.append("Now write the final answer using these results.")
        return "\n".join(lines)

    def ask(self, question: str, as_of: AsOf | None = None, scope: Scope | None = None,
            budget_usd: float | None = None) -> Answer:
        trace: list[StageTrace] = []
        passages: list[Passage] = []
        results: list[ToolResult] = []

        def finish(status: str, kind: str | None = None, message: str = "",
                   searched: list[str] | None = None, query: Query | None = None,
                   claims: list[Claim] | None = None, text: str = "",
                   grade: float = 0.0) -> Answer:
            ab = None
            if kind:
                custom = None
                if query is not None:
                    try:
                        custom = self.domain.abstention_text(kind, query)
                    except Exception:
                        custom = None
                ab = Abstention(kind, custom or message or _DEFAULT_TEXT.get(kind, kind),
                                searched or [])
            return Answer(status=status, text=text, claims=claims or [], grade=grade,
                          abstention=ab, passages=passages, tool_results=results,
                          query=query, trace=trace)

        def afford(last_cost: float | None) -> bool:
            if budget_usd is None:
                return True
            need = _DEFAULT_CALL_USD if last_cost is None else last_cost
            return sum(t.usd for t in trace) + need <= budget_usd

        # 1. understand
        t0 = time.perf_counter()
        query = self._understand(question, as_of, scope)
        trace.append(StageTrace("understand", _ms(t0),
                                note=f"intent={query.intent}; decided_by={query.decided_by}"))
        if query.clarify:
            return finish("needs_input", "needs_input", query.clarify, query=query)
        if query.intent == "out_of_scope":
            return finish("abstained", "out_of_scope", query=query)

        # 2. retrieve
        t0 = time.perf_counter()
        passages = retrieve_mod.cascade(self.store, query, self.config.retrieve,
                                        embedder=self.embedder, reranker=self.reranker,
                                        trace=trace)
        trace.append(StageTrace("retrieve", _ms(t0), n_out=len(passages)))
        if not passages:
            other = self.store.lexical_any_date(query.text, query.scope, 10)
            if other:
                return finish("abstained", "not_valid_at_date", query=query,
                              searched=[_span(p) for p in other])
            return finish("abstained", "no_source", query=query)
        if all(p.coverage == 0 for p in passages):
            return finish("abstained", "outside_coverage", query=query,
                          searched=sorted({p.source_id for p in passages}))

        # 3. draft
        tools = self._tools()
        if not afford(None):
            return finish("abstained", "budget", query=query)
        d, err = self._draft(self.llm, query, passages, tools, trace, "draft")
        if err is not None:
            return finish(*err, query=query)
        last_cost = d.usage.usd

        # 4. tools
        if d.tool_calls:
            t0 = time.perf_counter()
            results = self._run_calls(tools, d.tool_calls)
            ran_sql = any(c.get("tool") == "sql" for c in d.tool_calls if isinstance(c, dict))
            trace.append(StageTrace("tools", _ms(t0), n_out=len(results),
                                    note=", ".join(f"{r.mark}:{r.tool}:{'ok' if r.ok else 'fail'}"
                                                   for r in results)))
            if ran_sql:
                if not afford(last_cost):
                    return finish("abstained", "budget", query=query)
                d2, err = self._draft(_Appender(self.llm, self._results_text(results)), query,
                                      passages, tools, trace, "draft_followup")
                if err is not None:
                    return finish(*err, query=query)
                d = d2
                # Calls in the follow-up run too, but there is no second follow-up.
                have = {r.mark for r in results}
                extra = [c for c in d.tool_calls
                         if not (isinstance(c, dict) and c.get("mark") in have)]
                if extra:
                    results = results + self._run_calls(tools, extra)

        # 5. verify, decide
        t0 = time.perf_counter()
        try:
            claims = _verify(d, passages, results, self.store, query.as_of, self.entailer,
                             self.config.verify)
        except Exception as e:
            trace.append(StageTrace("verify", _ms(t0), note=f"error: {type(e).__name__}"))
            return finish("abstained", "unsupported", "The draft could not be verified.",
                          query=query)
        trace.append(StageTrace("verify", _ms(t0), n_out=len(claims)))
        t0 = time.perf_counter()
        # Conflict/divergence detection is not implemented in this version.
        status, grade, ab = decide(claims, passages, query, self.config.decide, self.store,
                                   declined=d.declined)
        trace.append(StageTrace("decide", _ms(t0), note=status))

        # 6. assemble
        t0 = time.perf_counter()
        text = ""
        if status == "answered":
            text = draft_mod.render(d, results)
        elif status == "partial":
            bad = {c.text for c in claims if c.label == "unsupported"}
            keep = [s for s in d.sentences if s.text not in bad]
            text = draft_mod.render(dataclasses.replace(d, sentences=keep), results)
        trace.append(StageTrace("assemble", _ms(t0)))
        if status in ("answered", "partial"):
            return finish(status, claims=claims, text=text, grade=grade, query=query)
        kind = ab.type if ab else "unsupported"
        return finish(status, kind, ab.message if ab else "", ab.searched if ab else [],
                      query=query, claims=claims)

    def _draft(self, llm: Any, query: Query, passages: list[Passage], tools: list[Any],
               trace: list[StageTrace], stage: str):
        """One model call. Returns (draft, None) or (None, finish-args)."""
        t0 = time.perf_counter()
        try:
            d = draft_mod.draft(llm, query, passages, tools, self.config.draft)
        except BudgetExceeded:
            trace.append(StageTrace(stage, _ms(t0), note="budget exceeded"))
            return None, ("abstained", "budget")
        except Exception as e:  # model misbehaviour never propagates
            trace.append(StageTrace(stage, _ms(t0), note=f"model error: {type(e).__name__}"))
            return None, ("abstained", "unsupported", "The model call failed.")
        u = d.usage
        note = "declined" if d.declined else ("no sentences" if not d.sentences else "")
        trace.append(StageTrace(stage, _ms(t0), u.tokens_in, u.tokens_out, u.usd,
                                len(d.sentences), note))
        return d, None
