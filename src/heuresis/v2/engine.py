"""EngineV2: the cascade of ``docs/v2-contracts.md`` section 7, end to end.

Stage names written to ``Answer.trace``: ``understand``, ``lookup``, the retrieval stages
(``lexical``, ``expand_terms``, ``dense``, ``edges``), ``retrieve`` (summary), ``draft`` (one
per propose call), ``search`` and ``open`` (one per executed action), ``tools``, ``bind``,
``gates``, ``repair``, ``judge``, ``decide``, ``escalate`` and ``assemble``. Model calls are the
``draft`` and ``judge`` stages: their cost is the cost of the answer.

An instance is not shared between threads (its SQLite connections are per thread): build one
per thread. Nothing global is mutated.
"""
from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import draft as draft_mod
from .. import router as router_mod
from ..domains import get_domain
from ..engine import (
    _DEFAULT_CALL_USD,
    _DEFAULT_TEXT,
    _STATEFUL_DOMAINS,
    NOTE_BUDGET,
    NOTE_MODEL_ERROR,
    Engine,
    _span,
)
from ..fakes import EchoLLM
from ..llm import BudgetExceeded
from ..model import (
    Abstention,
    Answer,
    AsOf,
    Draft,
    Passage,
    Query,
    Scope,
    StageTrace,
)
from ..references import has_resolver
from ..store import Store
from ..surface.config import load_config
from . import agent as agent_mod
from . import bind as bind_mod
from . import repair as repair_mod
from . import retrieve as retrieve_mod
from .locked import calibration as cal_mod
from .locked import decide as decide_mod
from .locked import gates as gates_mod
from .locked import judge as judge_mod
from .locked.schema import load_surface, surface_hash

__all__ = ["EngineV2", "trace_failure"]

CALIBRATION_DIR = Path(__file__).resolve().parent / "calibration"


def trace_failure(trace: list[StageTrace]) -> tuple[str, str] | None:
    """Why an answer's trace shows a failed model call: ``("budget", note)`` for a budget stop,
    ``("model", note)`` for a failed call, in the stages ``draft`` (propose) and ``judge``.
    ``None`` when every model call ran. Same contract as ``heuresis.engine.trace_failure``,
    which does not know the ``judge`` stage."""
    for t in trace:
        if t.stage in ("draft", "judge"):
            if t.note == NOTE_BUDGET:
                return "budget", f"{t.stage}: {t.note}"
            if t.note.startswith(NOTE_MODEL_ERROR):
                return "model", f"{t.stage}: {t.note}"
    return None


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


def _n_pass(claims) -> int:
    """Cited sentences that pass every gate."""
    return sum(1 for c in claims if c.kind != "derived" and not gates_mod.deterministic_failure(c))


@dataclass
class _Run:
    """The outcome of steps 4-10 for one generator."""

    draft: Draft | None = None
    claims: list = field(default_factory=list)
    results: list = field(default_factory=list)
    verdict: Any = None
    decision: Any = None
    #: (status, kind, message): the run ended before a decision (budget, model error).
    err: tuple | None = None
    bound: int = 0
    repairs: int = 0


class EngineV2:
    def __init__(self, store: Store, domain: Any, *, surface=None, llm: Any = None,
                 judge_llm: Any = None, strong_llm: Any = None, embedder: Any = None,
                 classifier: Any = None, calibration: Any = None, policy: Any = None,
                 router_cfg: Any = None, calibration_dataset: str | None = None):
        self.store = store
        self.domain = domain
        self.surface = surface if surface is not None else load_surface(domain=domain.name)
        self.llm = llm if llm is not None else EchoLLM()
        self.judge_llm = judge_llm if judge_llm is not None else self.llm
        self.strong_llm = strong_llm
        self.embedder = embedder
        self.classifier = classifier
        self.policy = policy if policy is not None else decide_mod.load_policy()
        self.router_cfg = router_cfg if router_cfg is not None else load_config().router
        self.surface_hash = surface_hash(self.surface)
        self.calibration_dataset = calibration_dataset
        self.calibration = self._resolve_calibration(calibration)
        self._sql_db: str | None = None

    # -- lifecycle -----------------------------------------------------------

    @classmethod
    def open(cls, path, domain: Any = None, **kw) -> "EngineV2":
        store = Store(str(path))
        try:
            stored = store.meta_get("domain")
            if domain is None:
                dom = get_domain(stored or "text")
            else:
                dom = get_domain(domain) if isinstance(domain, str) else domain
                if stored and stored != dom.name and store.stats().get("units", 0) > 0:
                    raise ValueError(
                        f"database {path} holds domain {stored!r}, not {dom.name!r}")
            if kw.get("surface") is None:
                kw["surface"] = load_surface(domain=dom.name)
            eng = cls(store, dom, **kw)
        except Exception:
            store.close()
            raise
        eng.store.meta_set("domain", dom.name)
        if dom.name in _STATEFUL_DOMAINS:
            for p in eng._paths():
                try:
                    dom.read(p)  # restores the plug-in's corpus state; nothing is stored
                except Exception:
                    pass
        eng._bind_sql_db()
        return eng

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "EngineV2":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # Corpus handling and tool running are the v1 code (they use only ``store``, ``domain``,
    # ``embedder`` and ``_sql_db``, which this class has too).
    _paths = Engine._paths
    _bind_sql_db = Engine._bind_sql_db
    ingest = Engine.ingest
    index = Engine.index
    _tools = Engine._tools
    _run_calls = Engine._run_calls
    _settle_date = Engine._settle_date

    def _resolve_calibration(self, calibration: Any):
        """A calibration is used ONLY when the caller passes one: a ``Calibration``, the path of
        its file, or a directory together with ``calibration_dataset`` (searched with the surface
        hash and that dataset). ``None`` searches nothing."""
        try:
            if calibration is None:
                return None
            if isinstance(calibration, cal_mod.Calibration):
                return calibration
            p = Path(calibration)
            if p.is_file():
                return cal_mod.load(p)
            if p.is_dir() and self.calibration_dataset:
                return cal_mod.find(p, self.surface_hash, self.calibration_dataset)
            return None
        except (OSError, ValueError, TypeError):
            return None

    def _active_calibration(self):
        """The calibration whose threshold applies: its surface hash is the running surface's
        and it certified a threshold."""
        c = self.calibration
        if c is not None and c.surface_hash == self.surface_hash and c.tau is not None:
            return c
        return None

    # -- reading -------------------------------------------------------------

    def _understand(self, question: str, as_of: AsOf | None, scope: Scope | None) -> Query:
        return router_mod.understand(question, cfg=self.router_cfg, rules=self.domain.rules(),
                                     classifier=self.classifier, as_of=as_of, scope=scope)

    def search(self, question: str, as_of: AsOf | None = None, scope: Scope | None = None,
               k: int = 10) -> list[Passage]:
        q, _ = self._settle_date(self._understand(question, as_of, scope), as_of)
        cfg = self.surface.config["retrieve"]
        out: list[Passage] = []
        seen: set[tuple[str, int]] = set()
        if self.surface.get("route", "lookup_direct") and has_resolver(self.domain):
            for p in retrieve_mod.lookup(self.store, self.domain, q.text, q.as_of, q.scope)[0]:
                if (p.unit_id, p.seq) not in seen:
                    seen.add((p.unit_id, p.seq))
                    out.append(p)
        found = retrieve_mod.search(self.store, q, cfg, embedder=self.embedder, k=k,
                                    exclude=seen)
        return (out + found)[:k]

    # -- ask -----------------------------------------------------------------

    def ask(self, question: str, as_of: AsOf | None = None, scope: Scope | None = None,
            budget_usd: float | None = None) -> Answer:
        trace: list[StageTrace] = []
        evidence = agent_mod.Evidence()
        surf = self.surface
        absent: list[str] = []  # named units that exist but have nothing in force at the date
        state: dict[str, Any] = {"run": None, "escalated": False, "query": None}

        def afford(last_cost: float | None) -> bool:
            if budget_usd is None:
                return True
            need = _DEFAULT_CALL_USD if last_cost is None else last_cost
            return sum(t.usd for t in trace) + need <= budget_usd

        def finish(status: str, kind: str | None = None, message: str = "",
                   searched: list[str] | None = None, query: Query | None = None,
                   run: _Run | None = None, text: str = "", grade: float = 0.0,
                   exact: bool = False) -> Answer:
            ab = None
            if kind:
                custom = None
                if query is not None and not exact:
                    try:
                        custom = self.domain.abstention_text(kind, query)
                    except Exception:
                        custom = None
                ab = Abstention(kind, custom or message or _DEFAULT_TEXT.get(kind, kind),
                                searched or [])
            claims = run.claims if run is not None else []
            return Answer(status=status, text=text, claims=claims, grade=grade, abstention=ab,
                          passages=list(evidence.passages),
                          tool_results=run.results if run is not None else [],
                          query=query, trace=trace, meta=self._meta(run, state, claims))

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

        # 2. lookup: provisions the question names, first in the evidence
        if surf.get("route", "lookup_direct") and has_resolver(self.domain):
            t0 = time.perf_counter()
            try:
                lp, refs = retrieve_mod.lookup(self.store, self.domain, query.text, query.as_of,
                                               query.scope)
            except Exception:
                lp, refs = [], []
            got = {p.unit_id for p in lp}
            for r in refs:
                if r.status == "resolved":
                    for uid in r.unit_ids:
                        if (uid not in got and uid not in absent and self.store.has_unit(uid)
                                and retrieve_mod.unit_in_scope(self.store, uid, query.scope)):
                            absent.append(uid)
            if lp:
                evidence.add("Lookup", lp)
            trace.append(StageTrace(
                "lookup", _ms(t0), n_out=len(lp),
                note=(f"refs={len(refs)}" + (f"; not in force at the date: {', '.join(absent)}"
                                              if absent else ""))))

        # 3. retrieve
        t0 = time.perf_counter()
        sub: list[StageTrace] = []
        found = retrieve_mod.search(self.store, query, surf.config["retrieve"],
                                    embedder=self.embedder, trace=sub,
                                    exclude=evidence.seen())
        trace.extend(sub)
        if found:
            evidence.add(agent_mod.FIRST_LABEL if evidence.passages else "", found)
        trace.append(StageTrace("retrieve", _ms(t0), n_out=len(evidence.passages)))
        state["query"] = query
        if not evidence.passages:
            other = self.store.lexical_any_date(query.text, query.scope, 10)
            if absent or other:
                return finish("abstained", "not_valid_at_date", query=query,
                              searched=[*absent, *(_span(p) for p in other)])
            return finish("abstained", "no_source", query=query)
        if all(p.coverage == 0 for p in evidence.passages):
            return finish("abstained", "outside_coverage", query=query,
                          searched=sorted({p.source_id for p in evidence.passages}))

        # 4-10. propose, tools, bind, gates, repair, judge, decide
        tools = self._tools()
        run = self._attempt(self.llm, query, evidence, tools, trace, afford)

        # 11. escalate
        first_kind = self._kind(run)
        if (surf.get("route", "escalate") and self.strong_llm is not None
                and first_kind == "unsupported" and afford(None)):
            state["escalated"] = True
            trace.append(StageTrace("escalate", 0.0, note="strong model after an unsupported abstention"))
            evidence.turns_used, evidence.last_cost = 0, None
            second = self._attempt(self.strong_llm, query, evidence, tools, trace, afford)
            if second.decision is not None and second.decision.status in ("answered", "partial"):
                run = second
                state["escalation_used"] = True
        state["run"] = run

        if run.err is not None:
            kind = run.err[1] if len(run.err) > 1 else "unsupported"
            msg = run.err[2] if len(run.err) > 2 else ""
            kind, msg, searched = self._late(kind, msg, [], absent, trace)
            return finish(run.err[0], kind, msg, searched, query=query, run=run)

        # 12. assemble
        dec = run.decision
        t0 = time.perf_counter()
        text = ""
        if dec.status in ("answered", "partial") and run.draft is not None:
            keep = [run.draft.sentences[i] for i in dec.kept if i < len(run.draft.sentences)]
            text = draft_mod.render(dataclasses.replace(run.draft, sentences=keep), run.results)
        trace.append(StageTrace("assemble", _ms(t0), note=dec.status))
        grade = dec.confidence if dec.status in ("answered", "partial") else 0.0
        if dec.abstention is None:
            return finish(dec.status, query=query, run=run, text=text, grade=grade)
        kind, msg, searched = self._late(dec.abstention.type, dec.abstention.message,
                                         list(dec.abstention.searched), absent, trace)
        divergent = dec.status == "divergent"
        if divergent:  # both sides are named as they are: no custom text, nothing chosen
            kind, msg, searched = dec.abstention.type, dec.abstention.message, dec.abstention.searched
        return finish(dec.status, kind, msg, searched, query=query, run=run, text=text,
                      grade=grade, exact=divergent)

    # -- steps ---------------------------------------------------------------

    @staticmethod
    def _kind(run: _Run) -> str | None:
        if run.err is not None:
            return run.err[1] if len(run.err) > 1 else None
        if run.decision is not None and run.decision.abstention is not None \
                and run.decision.status == "abstained":
            return run.decision.abstention.type
        return None

    @staticmethod
    def _late(kind: str, msg: str, searched: list[str], absent: list[str],
              trace: list[StageTrace]) -> tuple[str, str, list[str]]:
        """A named provision that exists but is not in force at the date turns a final
        ``no_source`` / ``unsupported`` abstention into ``not_valid_at_date`` naming it."""
        if absent and kind in ("no_source", "unsupported", "not_valid_at_date") \
                and not any(t.note.startswith(NOTE_MODEL_ERROR) for t in trace):
            return ("not_valid_at_date",
                    "The provision named in the question is not in force at the requested date.",
                    [*absent, *[s for s in searched if s not in absent]])
        return kind, msg, searched

    def _attempt(self, llm: Any, query: Query, evidence, tools: list, trace: list[StageTrace],
                 afford) -> _Run:
        """Steps 4-10 with one generator model over the evidence so far."""
        surf = self.surface
        run = _Run()
        common = dict(store=self.store, domain=self.domain, embedder=self.embedder,
                      trace=trace, afford=afford)

        d, err = agent_mod.propose(llm, query, evidence, tools, surf, **common)
        if err is not None:
            run.err = err
            return run
        d, results, err = self._tools_step(llm, d, query, evidence, tools, trace, common)
        run.draft, run.results = d, results
        if err is not None:
            run.err = err
            return run
        claims, run.bound = self._check(d, results, query, evidence, trace)

        # 8. repair
        rounds = int(surf.get("repair", "rounds"))
        max_turns = int(surf.get("agent", "max_turns"))
        for r in range(1, rounds + 1):
            failing = [c for c in claims if gates_mod.deterministic_failure(c)]
            if not failing or d.declined:
                break
            left = max_turns - evidence.turns_used
            if left <= 0:
                trace.append(StageTrace("repair", 0.0, note="skipped: no turn left"))
                break
            fb = (surf.prompt("repair") + "\n\n" + repair_mod.feedback(claims))
            t0 = time.perf_counter()
            n0 = len(trace)
            d2, err2 = agent_mod.propose(llm, query, evidence, tools, surf, feedback=fb,
                                         turns=left, **common)
            if err2 is not None:
                # The first draft stands; the failed call must not read as a failed answer.
                for t in trace[n0:]:
                    if t.stage == "draft" and (t.note == NOTE_BUDGET
                                               or t.note.startswith(NOTE_MODEL_ERROR)):
                        t.note = "repair skipped: " + t.note
                trace.append(StageTrace("repair", _ms(t0), note=f"round {r}: {err2[1]}; kept the first draft"))
                break
            d2, results2, err2 = self._tools_step(llm, d2, query, evidence, tools, trace, common)
            if err2 is not None:
                trace.append(StageTrace("repair", _ms(t0), note=f"round {r}: {err2[1]}; kept the first draft"))
                break
            claims2, bound2 = self._check(d2, results2, query, evidence, trace)
            run.repairs += 1
            old_n, new_n = _n_pass(claims), _n_pass(claims2)
            take = new_n >= old_n
            trace.append(StageTrace("repair", _ms(t0), n_out=new_n,
                                    note=f"round {r}: passing {old_n} -> {new_n}; "
                                         + ("kept the new draft" if take else "kept the first draft")))
            if take:
                d, claims, results = d2, claims2, results2
                run.draft, run.results, run.bound = d, results, run.bound + bound2
        run.claims = claims

        # 9. judge
        passing = [c for c in claims if not gates_mod.deterministic_failure(c)]
        verdict = None
        if passing and not d.declined:
            if not afford(evidence.last_cost):
                run.err = ("abstained", "budget", "")
                return run
            t0 = time.perf_counter()
            try:
                verdict = judge_mod.judge(self.judge_llm, query.text, query.as_of.valid, passing,
                                          evidence.passages, results,
                                          max_tokens=int(surf.get("judge", "max_tokens")))
            except BudgetExceeded:
                trace.append(StageTrace("judge", _ms(t0), note=NOTE_BUDGET))
                run.err = ("abstained", "budget", "")
                return run
            except Exception as e:
                trace.append(StageTrace("judge", _ms(t0), note=f"{NOTE_MODEL_ERROR}: {type(e).__name__}"))
                run.err = ("abstained", "unsupported", "The judge call failed.")
                return run
            u = verdict.usage
            evidence.last_cost = u.usd
            cached = int(getattr(u, "tokens_cached", 0) or 0)
            note = (f"answer={verdict.answer or '?'}; sufficient={verdict.sufficient or '?'}; "
                    f"premise={verdict.premise}" if verdict.readable else "unreadable")
            if cached:
                note += f"; cached={cached}"
            trace.append(StageTrace("judge", _ms(t0), u.tokens_in, u.tokens_out, u.usd,
                                    len(passing), note))
        run.verdict = verdict

        # 10. decide
        t0 = time.perf_counter()
        cal = self._active_calibration()
        run.decision = decide_mod.decide(claims, verdict, evidence.passages, query, self.policy,
                                         tau=cal.tau if cal is not None else None,
                                         store=self.store, declined=d.declined,
                                         question=query.text, as_of=query.as_of,
                                         tool_results=results)
        trace.append(StageTrace("decide", _ms(t0), note=run.decision.status))
        return run

    def _tools_step(self, llm, d: Draft, query: Query, evidence, tools: list,
                    trace: list[StageTrace], common: dict):
        """Step 5: run the tool calls. After a ``sql`` call one more propose call (if a turn
        and the budget remain) sees the results, as in v1. Returns (draft, results, err)."""
        results: list = []
        if not d.tool_calls:
            return d, results, None
        t0 = time.perf_counter()
        results = self._run_calls(tools, d.tool_calls)
        ran_sql = any(c.get("tool") == "sql" for c in d.tool_calls if isinstance(c, dict))
        trace.append(StageTrace("tools", _ms(t0), n_out=len(results),
                                note=", ".join(f"{r.mark}:{r.tool}:{'ok' if r.ok else 'fail'}"
                                               for r in results)))
        if ran_sql and int(self.surface.get("agent", "max_turns")) - evidence.turns_used > 0:
            d2, err = agent_mod.propose(llm, query, evidence, tools, self.surface,
                                        feedback=Engine._results_text(results), turns=1, **common)
            if err is not None:
                return d, results, err
            d = d2
            have = {r.mark for r in results}
            extra = [c for c in d.tool_calls
                     if not (isinstance(c, dict) and c.get("mark") in have)]
            if extra:
                results = results + self._run_calls(tools, extra)
        return d, results, None

    def _check(self, d: Draft, results: list, query: Query, evidence, trace: list[StageTrace]):
        """Steps 6-7: bind missing citations, then the deterministic gates."""
        t0 = time.perf_counter()
        notes = bind_mod.bind(d, evidence, self.store, self.domain, query.as_of, query.scope)
        if notes:
            trace.append(StageTrace("bind", _ms(t0), n_out=len(notes), note="; ".join(notes)[:300]))
        t0 = time.perf_counter()
        claims = gates_mod.check(d, evidence.passages, results, self.store, query.as_of,
                                 question=query.text, domain=self.domain)
        nfail = sum(1 for c in claims if gates_mod.deterministic_failure(c))
        trace.append(StageTrace("gates", _ms(t0), n_out=len(claims),
                                note=f"{nfail} sentence(s) failed" if nfail else ""))
        return claims, len(notes)

    def _meta(self, run: _Run | None, state: dict, claims: list) -> dict:
        cal = self._active_calibration()
        dec = run.decision if run is not None else None
        v = run.verdict if run is not None else None
        kept = set(dec.kept) if dec is not None and dec.status != "abstained" else set()
        dropped = []
        for i, c in enumerate(claims):
            if i in kept:
                continue
            if gates_mod.deterministic_failure(c):
                why = gates_mod.failure_reason(c)
            elif c.label == "unsupported":
                why = c.note or "dropped by the judge"
            else:
                why = "withheld: " + (dec.abstention.message if dec is not None
                                      and dec.abstention is not None else "answer not given")
            dropped.append({"text": c.text, "reason": why})
        tau = cal.tau if cal is not None else self.policy.default_tau
        meta: dict = {
            "engine": "v2",
            "surface_hash": self.surface_hash,
            "confidence": dec.confidence if dec is not None else 0.0,
            "tau": tau,
            "calibrated": cal is not None,
            "verdict": {"answer": getattr(v, "answer", "") if v else "",
                        "sufficient": getattr(v, "sufficient", "") if v else "",
                        "premise": getattr(v, "premise", "") if v else "",
                        "conflict": list(v.conflict) if v and v.conflict else None},
            "bound": run.bound if run is not None else 0,
            "repairs": run.repairs if run is not None else 0,
            "escalated": bool(state.get("escalated")),
            "dropped": dropped,
        }
        if state.get("escalation_used"):
            meta["escalation_used"] = True
        if cal is not None:
            meta["calibration"] = {"tau": cal.tau, "alpha": cal.alpha, "delta": cal.delta,
                                   "n_answered": cal.n_answered, "errors": cal.errors,
                                   "upper": cal.upper, "label": cal.label,
                                   "dataset": cal.dataset, "split": cal.split}
        return meta
