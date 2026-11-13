"""The v2 propose loop: the model searches, opens and answers over a growing evidence list.

Reply protocol (plain text): a reply whose every non-empty line is ``SEARCH: <query>`` or
``OPEN: <target>`` is a set of actions; any other reply is an answer in the draft format.
Every action runs with the question's own as-of date and scope (the model never chooses
either). Passages are numbered ``t1..tn`` in the order they are shown and are never cut:
a passage that does not fit ``max_context_chars`` is not added.

Nothing here is global: all state lives in the ``Evidence`` the caller owns.
"""
from __future__ import annotations

import dataclasses
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from ..draft import parse_draft
from ..engine import NOTE_BUDGET, NOTE_MODEL_ERROR
from ..llm import CACHE_BREAK, BudgetExceeded
from ..model import Draft, Passage, Query, StageTrace
from ..surface.prompts import passage_line
from . import retrieve as retrieve_mod

__all__ = ["Evidence", "Actions", "parse_actions", "build_prompt", "propose", "FIRST_LABEL"]

#: Label of the first-retrieval block when a ``Lookup`` block precedes it.
FIRST_LABEL = "Retrieved"
#: Labels of blocks whose passages may be dropped to fit the first prompt (never lookup).
_DROPPABLE = ("", FIRST_LABEL)
_MAX_OPENS = 3


def _key(p: Passage) -> tuple[str, int]:
    return (p.unit_id, p.seq)


@dataclass
class Evidence:
    """Everything shown to the model, in order, with marks ``t1..tn``."""

    passages: list[Passage] = field(default_factory=list)
    rounds: list[tuple[str, list[Passage]]] = field(default_factory=list)
    #: Propose calls made so far for this question (including repair turns).
    turns_used: int = 0
    #: Cost of the last model call, for the budget check.
    last_cost: float | None = None
    #: True once the first prompt has been fitted to the context limit.
    fitted: bool = False

    def __post_init__(self) -> None:
        self._seen: set[tuple[str, int]] = {_key(p) for p in self.passages}

    def add(self, label: str, passages: Iterable[Passage],
            fits: Callable[[], bool] | None = None) -> list[Passage]:
        """Append a block; only passages not shown before are added, each with the next mark.
        With ``fits``, a passage after which ``fits()`` is false is removed and adding stops
        (drop, never cut). Returns the passages added."""
        block: list[Passage] = []
        self.rounds.append((label, block))
        for p in passages:
            if _key(p) in self._seen:
                continue
            q = dataclasses.replace(p, mark=f"t{len(self.passages) + 1}")
            block.append(q)
            self.passages.append(q)
            if fits is not None and not fits():
                block.pop()
                self.passages.pop()
                break
            self._seen.add(_key(q))
        return list(block)

    def by_mark(self, mark: str) -> Passage | None:
        mark = (mark or "").strip().lower()
        for p in self.passages:
            if p.mark == mark:
                return p
        return None

    def seen(self) -> set[tuple[str, int]]:
        return set(self._seen)

    def droppable(self) -> bool:
        return bool(self.rounds) and self.rounds[-1][0] in _DROPPABLE and bool(self.rounds[-1][1])

    def pop_last(self) -> Passage:
        """Remove the last passage of the last block (the lowest-ranked of the newest block)."""
        p = self.rounds[-1][1].pop()
        self.passages.pop()
        self._seen.discard(_key(p))
        return p


@dataclass
class Actions:
    searches: list[str] = field(default_factory=list)
    opens: list[str] = field(default_factory=list)


_BULLET = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s+")
_ACTION = re.compile(r"^(SEARCH|OPEN)\s*:\s*(.+)$", re.IGNORECASE)
_TRAIL = ".,;:!?`'\"”’ "


def _clean_line(line: str) -> str:
    line = line.strip()
    line = _BULLET.sub("", line)
    return line.strip().strip("`*_ ").strip()


def parse_actions(raw: str, max_queries: int) -> Actions | None:
    """The actions of a reply, or None when the reply is an answer. A reply is a set of actions
    only if EVERY non-empty line is an action (a reply that mixes prose and action lines is an
    answer). Tolerates bullets, backticks, case and trailing punctuation. Never raises."""
    try:
        acts = Actions()
        n = 0
        for line in (raw or "").splitlines():
            if not line.strip() or line.strip().startswith("```"):
                continue
            n += 1
            m = _ACTION.match(_clean_line(line))
            if not m:
                return None
            arg = m.group(2).strip().rstrip(_TRAIL).lstrip("`'\"“‘ ").strip()
            if not arg:
                return None
            if m.group(1).upper() == "SEARCH":
                if arg not in acts.searches:
                    acts.searches.append(arg)
            else:
                arg = arg.strip("[]").strip()
                if arg and arg not in acts.opens:
                    acts.opens.append(arg)
        if n == 0 or not (acts.searches or acts.opens):
            return None
        acts.searches = acts.searches[:max(0, int(max_queries))]
        acts.opens = acts.opens[:_MAX_OPENS]
        return acts
    except Exception:
        return None


def _label_line(label: str) -> str:
    return label if ":" in label else label + ":"


def build_prompt(surface, query: Query, evidence: Evidence, tools, turns_left: int,
                 feedback: str = "", *, cache_break: bool = False) -> str:
    """The user prompt of a propose call. Everything up to the end of the evidence is stable
    across turns of one question; ``CACHE_BREAK`` follows it when ``cache_break`` is true."""
    lines = [f"As-of date: {query.as_of.valid or 'today'}"]
    if tools:
        lines.append("Tools: " + "; ".join(f"{t.name} ({t.description})" for t in tools))
    lines.append(f"Question: {query.text}")
    lines.append("Passages:")
    for i, (label, ps) in enumerate(evidence.rounds):
        if label:
            lines.append(_label_line(label))
        if ps:
            lines.extend(passage_line(p.mark, p) for p in ps)
        else:
            lines.append("(none)" if i == 0 and not label else "(nothing new)")
    if not evidence.rounds:
        lines.append("(none)")
    tail = [f"Turns left: {turns_left}."]
    tail.append(surface.prompt("agent_last" if turns_left <= 1 else "agent_more"))
    max_s = int(surface.get("agent", "max_sentences"))
    if max_s > 0:
        tail.append(f"Answer in at most {max_s} short sentences.")
    if feedback:
        tail.append(feedback)
    return "\n".join(lines) + ("\n" + CACHE_BREAK + "\n" if cache_break else "\n") + "\n".join(tail)


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


def _usage_ok(usage) -> bool:
    """A usage object with the numeric fields the loop reads."""
    return all(isinstance(getattr(usage, n, None), (int, float))
               for n in ("tokens_in", "tokens_out", "usd"))


def _call_note(extra: str, usage) -> str:
    cached = int(getattr(usage, "tokens_cached", 0) or 0)
    parts = [x for x in (extra, f"cached={cached}" if cached else "") if x]
    return "; ".join(parts)


def _run_actions(acts: Actions, query: Query, evidence: Evidence, surface, *, store, domain,
                 embedder, trace: list[StageTrace], fits_for: Callable[[], bool]) -> None:
    cfg = surface.config["retrieve"]
    k = int(cfg["search_k"])
    for q in acts.searches:
        t0 = time.perf_counter()
        sub: list[StageTrace] = []
        note = ""
        try:
            found = retrieve_mod.search(store, dataclasses.replace(query, text=q), cfg,
                                        embedder=embedder, trace=sub, k=k,
                                        exclude=evidence.seen())
        except Exception as e:
            found, note = [], f"error: {type(e).__name__}; "
        added = evidence.add(f"Search: {q}", found, fits_for)
        note += (f"{q[:120]}; found={len(found)}; shown={len(added)}"
                 + (f"; {len(found) - len(added)} did not fit" if len(added) < len(found) else ""))
        trace.append(StageTrace("search", _ms(t0), n_out=len(added), note=note))
    for target in acts.opens:
        t0 = time.perf_counter()
        note = ""
        found: list[Passage] = []
        try:
            anchor = evidence.by_mark(target) if re.fullmatch(r"[tT]\d+", target) else None
            if anchor is not None:
                found = retrieve_mod.open_unit(store, anchor.unit_id, query.as_of,
                                               int(cfg["open_radius"]), query.scope)
            else:
                found, _refs = retrieve_mod.lookup(store, domain, target, query.as_of,
                                                   query.scope)
                if not found and store.has_unit(target):
                    found = retrieve_mod.open_unit(store, target, query.as_of,
                                                   int(cfg["open_radius"]), query.scope)
        except Exception as e:
            note = f"error: {type(e).__name__}; "
        fresh = [p for p in found if _key(p) not in evidence.seen()]
        added = evidence.add(f"Open: {target}", fresh, fits_for)
        note += (f"{target[:120]}; found={len(found)}; shown={len(added)}"
                 + (f"; {len(fresh) - len(added)} did not fit" if len(added) < len(fresh) else ""))
        trace.append(StageTrace("open", _ms(t0), n_out=len(added), note=note))


def propose(llm, query: Query, evidence: Evidence, tools, surface, *, store, domain, embedder,
            trace: list[StageTrace], afford: Callable[[float | None], bool],
            feedback: str = "", turns: int | None = None
            ) -> tuple[Draft | None, tuple | None]:
    """The propose loop. Returns ``(draft, None)`` or ``(None, ("abstained", type, message))``.

    ``turns`` limits the model calls of this invocation (default: what is left of
    ``agent.max_turns`` after ``evidence.turns_used``). ``afford`` is checked before every model
    call. Model errors and budget stops end the loop with an abstention and a trace note."""
    max_turns = int(surface.get("agent", "max_turns"))
    remaining = max_turns - evidence.turns_used
    if turns is not None:
        remaining = min(remaining, int(turns))
    if remaining <= 0:
        return None, ("abstained", "unsupported", "No model turn was left.")
    limit = int(surface.get("agent", "max_context_chars"))
    max_q = int(surface.get("agent", "queries_per_turn"))
    max_tokens = int(surface.get("agent", "max_tokens"))
    system = surface.prompt("agent_system")
    cache = bool(getattr(llm, "supports_cache_break", False))

    def build(left: int, *, with_break: bool = False) -> str:
        return build_prompt(surface, query, evidence, tools, left, feedback,
                            cache_break=with_break)

    if not evidence.fitted:
        evidence.fitted = True
        # The first prompt: drop the lowest-ranked first-retrieval passages, never a lookup one.
        while len(build(remaining)) > limit and evidence.droppable():
            evidence.pop_last()

    for i in range(remaining):
        left = remaining - i
        if not afford(evidence.last_cost):
            return None, ("abstained", "budget", "")
        prompt = build(left, with_break=cache)
        t0 = time.perf_counter()
        try:
            raw, usage = llm.complete(system, prompt, max_tokens=max_tokens)
            if not _usage_ok(usage):
                raise TypeError("the model returned no usable usage")
        except BudgetExceeded:
            trace.append(StageTrace("draft", _ms(t0), note=NOTE_BUDGET))
            return None, ("abstained", "budget", "")
        except Exception as e:  # model misbehaviour never propagates
            trace.append(StageTrace("draft", _ms(t0), note=f"{NOTE_MODEL_ERROR}: {type(e).__name__}"))
            return None, ("abstained", "unsupported", "The model call failed.")
        evidence.turns_used += 1
        evidence.last_cost = usage.usd
        raw = raw if isinstance(raw, str) else ""
        acts = parse_actions(raw, max_q)
        if acts is None:
            d = parse_draft(raw)
            d.raw, d.usage = raw, usage
            note = ("declined" if d.declined else "no sentences" if not d.sentences else "")
            trace.append(StageTrace("draft", _ms(t0), usage.tokens_in, usage.tokens_out,
                                    usage.usd, len(d.sentences), _call_note(note, usage)))
            return d, None
        what = f"actions: {len(acts.searches)} search, {len(acts.opens)} open"
        if left <= 1:
            trace.append(StageTrace("draft", _ms(t0), usage.tokens_in, usage.tokens_out,
                                    usage.usd, 0,
                                    _call_note(f"{what}; none left", usage)))
            return None, ("abstained", "unsupported",
                          "The model asked for more evidence with no turn left.")
        trace.append(StageTrace("draft", _ms(t0), usage.tokens_in, usage.tokens_out, usage.usd,
                                0, _call_note(what, usage)))
        _run_actions(acts, query, evidence, surface, store=store, domain=domain,
                     embedder=embedder, trace=trace, fits_for=lambda: len(build(left - 1)) <= limit)
    return None, ("abstained", "unsupported", "No turn was left.")
