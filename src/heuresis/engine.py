"""The engine: wires understand, retrieve, draft, tools, verify and decide.

Stage names written to ``Answer.trace``: ``understand``, the retrieval stages
(``lexical``, ``dense``, ``expand``, ``rerank``, appended by the cascade),
``retrieve`` (summary), ``draft``, ``tools``, ``draft_followup`` (only after a
``sql`` call), ``verify``, ``decide`` and ``assemble``. In the ``search`` answer mode
every model turn is a ``draft`` stage (one per turn; a turn that asks for a search says so
in its note) and every search the model asks for is a ``search`` stage, so the cost of an
answer is the sum of its stages.
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
from .locked.decide import decide, deterministic_failure
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

#: Trace notes that mark why a stage failed. ``Engine.ask`` turns a model failure into
#: an "unsupported" abstention (library behaviour); these prefixes make it detectable.
NOTE_BUDGET = "budget exceeded"
NOTE_MODEL_ERROR = "model error"
NOTE_VERIFY_ERROR = "error"

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


def trace_failure(trace: list[StageTrace]) -> tuple[str, str] | None:
    """Why an answer's trace shows a failed stage: ``("budget", note)`` for a budget
    stop, ``("model", note)`` for a failed model call (the generator) and
    ``("verifier", note)`` for a failed verification (the local entailer). ``None`` when
    every stage ran. A budget stop is not a failure of the model."""
    for t in trace:
        if t.stage in ("draft", "draft_followup", "answers_question"):
            if t.note == NOTE_BUDGET:
                return "budget", f"{t.stage}: {t.note}"
            if t.note.startswith(NOTE_MODEL_ERROR):
                return "model", f"{t.stage}: {t.note}"
        elif t.stage == "verify" and t.note.startswith(NOTE_VERIFY_ERROR):
            return "verifier", f"verify: {t.note}"
    return None


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

    def _settle_date(self, query: Query, as_of: AsOf | None) -> tuple[Query, str]:
        """Keep a question-extracted as-of date only when it can mean "the state at that
        date": the corpus must hold history and the date must not precede it. Otherwise
        the date is just a fact named in the question; search as of today instead. A
        caller-supplied ``as_of`` is never touched. Returns (query, trace note)."""
        if as_of is not None or not query.dated or query.as_of.valid is None:
            return query, ""
        d = query.as_of.valid
        prof = self.store.time_profile()
        if not prof["versioned"]:
            why = "the corpus has no version history"
        elif prof["min_valid_from"] is not None and d < prof["min_valid_from"]:
            why = f"it is earlier than the first version ({prof['min_valid_from']})"
        else:
            return query, ""
        new = dataclasses.replace(query, as_of=dataclasses.replace(query.as_of, valid=None),
                                  dated=False)
        return new, f"question date {d} not used as as-of ({why}); as-of = today"

    def search(self, question: str, as_of: AsOf | None = None, scope: Scope | None = None,
               k: int = 10) -> list[Passage]:
        q, _ = self._settle_date(self._understand(question, as_of, scope), as_of)
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
        query, date_note = self._settle_date(query, as_of)
        trace.append(StageTrace("understand", _ms(t0),
                                note=f"intent={query.intent}; decided_by={query.decided_by}"
                                     + (f"; {date_note}" if date_note else "")))
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

        # 3. draft (one call over one retrieval) or search (the model may ask for more)
        tools = self._tools()
        if self.config.answer.mode == "search":
            d, err, followup = self._answer_search(query, passages, tools, trace, afford)
            if err is not None:
                return finish(*err, query=query)
        else:
            if not afford(None):
                return finish("abstained", "budget", query=query)
            d, err = self._draft(self.llm, query, passages, tools, trace, "draft")
            if err is not None:
                return finish(*err, query=query)

            def followup(llm: Any):
                return self._draft(llm, query, passages, tools, trace, "draft_followup")
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
                d2, err = followup(_Appender(self.llm, self._results_text(results)))
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
            trace.append(StageTrace("verify", _ms(t0), note=f"{NOTE_VERIFY_ERROR}: {type(e).__name__}"))
            return finish("abstained", "unsupported", "The draft could not be verified.",
                          query=query)
        trace.append(StageTrace("verify", _ms(t0), n_out=len(claims)))
        t0 = time.perf_counter()
        # Conflict/divergence detection is not implemented in this version.
        status, grade, ab = decide(claims, passages, query, self.config.decide, self.store,
                                   declined=d.declined)
        graded = getattr(self.config.decide, "mode", "strict") == "grade"
        if graded and status in ("answered", "partial"):
            # Entailment only grades here: a sentence kept despite low support is marked
            # "partial" (not "unsupported") so that its citations still count.
            for c in claims:
                if c.label == "unsupported" and not deterministic_failure(c):
                    c.label = "partial"
                    c.note = "; ".join(x for x in (c.note, "low support: graded, not removed") if x)
        trace.append(StageTrace("decide", _ms(t0), note=status))

        # 6. assemble
        t0 = time.perf_counter()
        text = ""
        if status == "answered":
            text = draft_mod.render(d, results)
        elif status == "partial":
            bad = {c.text for c in claims
                   if (deterministic_failure(c) if graded else c.label == "unsupported")}
            keep = [s for s in d.sentences if s.text not in bad]
            text = draft_mod.render(dataclasses.replace(d, sentences=keep), results)
        trace.append(StageTrace("assemble", _ms(t0)))
        if status in ("answered", "partial") and getattr(self.config.verify, "answers_question", False):
            verdict, err = self._answers_question(question, text, trace)
            if err is not None:
                return finish(*err, query=query, claims=claims)
            if verdict is False:
                return finish("abstained", "unsupported",
                              "The answer does not state what the question asks for.",
                              query=query, claims=claims)
        if status in ("answered", "partial"):
            return finish(status, claims=claims, text=text, grade=grade, query=query)
        kind = ab.type if ab else "unsupported"
        return finish(status, kind, ab.message if ab else "", ab.searched if ab else [],
                      query=query, claims=claims)

    def _answers_question(self, question: str, text: str, trace: list[StageTrace]):
        """The optional stage: one model call, YES or NO. Returns (verdict, finish-args):
        verdict is False only for a clear NO; an unreadable reply keeps the answer."""
        from .surface.prompts import ANSWERS_QUESTION_SYSTEM, answers_question_prompt
        t0 = time.perf_counter()
        try:
            raw, u = self.llm.complete(ANSWERS_QUESTION_SYSTEM,
                                       answers_question_prompt(question, text), max_tokens=10)
        except BudgetExceeded:
            trace.append(StageTrace("answers_question", _ms(t0), note=NOTE_BUDGET))
            return None, ("abstained", "budget")
        except Exception as e:
            trace.append(StageTrace("answers_question", _ms(t0),
                                    note=f"{NOTE_MODEL_ERROR}: {type(e).__name__}"))
            return None, ("abstained", "unsupported", "The model call failed.")
        word = (raw or "").strip().upper().split()[:1]
        verdict = False if word and word[0].startswith("NO") else True
        note = "answers_question: " + ("NO" if verdict is False else "YES" if word and word[0].startswith("YES")
                                       else "unreadable, kept")
        trace.append(StageTrace("answers_question", _ms(t0), u.tokens_in, u.tokens_out, u.usd, 0, note))
        return verdict, None

    def _draft(self, llm: Any, query: Query, passages: list[Passage], tools: list[Any],
               trace: list[StageTrace], stage: str):
        """One model call. Returns (draft, None) or (None, finish-args)."""
        return self._turn(stage, trace,
                          lambda: draft_mod.draft(llm, query, passages, tools, self.config.draft))

    def _turn(self, stage: str, trace: list[StageTrace], call: Any):
        """Run one model call (``call()`` returns a Draft) and trace it. Returns
        (draft, None) or (None, finish-args); a model failure never propagates."""
        t0 = time.perf_counter()
        try:
            d = call()
        except BudgetExceeded:
            trace.append(StageTrace(stage, _ms(t0), note=NOTE_BUDGET))
            return None, ("abstained", "budget")
        except Exception as e:  # model misbehaviour never propagates
            trace.append(StageTrace(stage, _ms(t0), note=f"{NOTE_MODEL_ERROR}: {type(e).__name__}"))
            return None, ("abstained", "unsupported", "The model call failed.")
        u = d.usage
        asked = draft_mod.parse_search(d.raw)
        note = (f"search requested: {asked[:80]}" if asked
                else "declined" if d.declined else ("no sentences" if not d.sentences else ""))
        trace.append(StageTrace(stage, _ms(t0), u.tokens_in, u.tokens_out, u.usd,
                                len(d.sentences), note))
        return d, None

    def _answer_search(self, query: Query, passages: list[Passage], tools: list[Any],
                       trace: list[StageTrace], afford: Any):
        """The ``search`` answer mode. ``passages`` is the first retrieval (marks t1..tn);
        it is replaced, in place, by every passage the model was shown, in order, so the
        verifier sees exactly what the model saw. Returns (draft, None, followup) or
        (None, finish-args, None); ``followup(llm)`` repeats the last turn with an extended
        prompt (after a ``sql`` call) and returns what ``_turn`` returns."""
        from .surface.prompts import SEARCH_SYSTEM, search_prompt
        acfg, dcfg = self.config.answer, self.config.draft
        max_s = max(0, int(acfg.max_searches))
        max_sent = int(getattr(dcfg, "max_sentences", 0) or 0)
        rounds: list[tuple[str, list[Passage]]] = [("", list(passages))]
        shown = {(p.unit_id, p.seq) for p in passages}
        n_shown = len(passages)

        def build(left: int) -> str:
            return search_prompt(query.text, query.as_of.valid, rounds, left, max_s, tools,
                                 max_sent)

        # The first retrieval is fitted as in single mode: the tail is dropped, never cut.
        while rounds[0][1] and len(build(max_s)) > dcfg.max_context_chars:
            rounds[0][1].pop()
        left, last_cost = max_s, None
        while True:
            if not afford(last_cost):
                return None, ("abstained", "budget"), None
            prompt = build(left)
            d, err = self._turn("draft", trace, lambda: draft_mod.draft_from_prompt(
                self.llm, SEARCH_SYSTEM, prompt, dcfg))
            if err is not None:
                return None, err, None
            last_cost = d.usage.usd
            asked = draft_mod.parse_search(d.raw)
            if asked is None:
                passages[:] = [p for _, ps in rounds for p in ps]

                def followup(llm: Any, _prompt: str = prompt):
                    return self._turn("draft_followup", trace, lambda: draft_mod.draft_from_prompt(
                        llm, SEARCH_SYSTEM, _prompt, dcfg))
                return d, None, followup
            if left <= 0:
                trace[-1].note += "; none left"
                return None, ("abstained", "unsupported",
                              "The model asked to search with no searches left."), None
            t0 = time.perf_counter()
            sub: list[StageTrace] = []
            wide = dataclasses.replace(self.config.retrieve,
                                       rerank_out=int(acfg.search_k) + len(shown))
            found = retrieve_mod.cascade(self.store, dataclasses.replace(query, text=asked),
                                         wide, embedder=self.embedder,
                                         reranker=self.reranker, trace=sub)
            new: list[Passage] = []
            for p in found:
                if (p.unit_id, p.seq) in shown or len(new) >= int(acfg.search_k):
                    continue
                new.append(dataclasses.replace(p, mark=f"t{n_shown + len(new) + 1}"))
            kept: list[Passage] = []
            rounds.append((asked, kept))
            for p in new:  # drop, never cut: stop at the first passage that no longer fits
                kept.append(p)
                if len(build(left - 1)) > dcfg.max_context_chars:
                    kept.pop()
                    break
            for p in kept:
                shown.add((p.unit_id, p.seq))
            n_shown += len(kept)
            left -= 1
            trace.append(StageTrace(
                "search", _ms(t0), n_out=len(kept),
                note=f"{max_s - left}/{max_s}: {asked[:120]}; found={len(found)}; new={len(new)}; "
                     f"shown={len(kept)}; " + "; ".join(f"{t.stage}: {t.note}" for t in sub)[:200]))
