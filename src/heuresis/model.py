"""Shared data model. Every module exchanges these types and nothing else.

Dates are ISO-8601 strings ("2024-03-15" or a full timestamp). They compare
correctly as strings, which keeps the SQLite queries and the Python code on one
representation. Validity intervals are half-open: [valid_from, valid_to).
``None`` means unbounded on that side.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ----------------------------------------------------------------------------
# Corpus
# ----------------------------------------------------------------------------

#: Event operations, replayed in order to compute every version of a unit.
OPS = ("create", "replace", "repeal", "restore", "correct")

#: Certainty of a version, lowest first.
CERTAINTY = ("low", "medium", "high")

#: Coverage grade of a source, 0 (not covered) to 4 (complete and audited).
COVERAGE_MIN, COVERAGE_MAX = 0, 4


@dataclass(frozen=True)
class Source:
    """Where units come from. ``coverage`` caps the grade of any answer that
    relies on this source; ``authority`` orders sources when they conflict
    (higher wins)."""

    id: str
    kind: str = "text"
    authority: int = 0
    coverage: int = COVERAGE_MAX
    licence: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Unit:
    """A stable identity whose text changes over time: a provision, a note, a
    file, a schema card."""

    id: str
    source_id: str
    kind: str = "passage"
    parent_id: str | None = None
    title: str = ""


@dataclass(frozen=True)
class Event:
    """One change to one unit.

    ``date`` is when the change takes effect on the valid-time axis.
    ``recorded_at`` is when the corpus learned of it (transaction time).
    ``axes`` carries any extra named dates a domain declares (for example
    ``{"published": "2023-12-29", "effects": "2024-04-01"}``).

    Semantics:
      create   first text of the unit, valid from ``date``.
      replace  closes the version in force at ``date`` and opens a new one.
      repeal   closes the version in force at ``date``; nothing is in force after.
      restore  reopens the unit from ``date`` with ``text`` if given, otherwise
               with the text of the last version before the repeal.
      correct  the text that was in force at ``date`` should always have read
               ``text``: same validity interval, new text, visible only to
               queries whose ``recorded`` as-of is at or after ``recorded_at``.
    """

    id: str
    unit_id: str
    op: str
    date: str
    text: str | None = None
    recorded_at: str = ""
    evidence: str = ""
    certainty: str = "high"
    axes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Version:
    """One text of one unit over one validity interval, computed by replay."""

    unit_id: str
    seq: int
    text: str
    valid_from: str | None
    valid_to: str | None
    event_id: str
    recorded_at: str = ""
    certainty: str = "high"
    axes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """A typed link that exists in the corpus (never model-extracted by the
    core). Valid over [valid_from, valid_to)."""

    src: str
    dst: str
    type: str = "cites"
    valid_from: str | None = None
    valid_to: str | None = None


# ----------------------------------------------------------------------------
# Query
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class AsOf:
    """The point in time a question is about.

    ``valid``    content must be in force on this date (default: now).
    ``recorded`` only what the corpus knew by this timestamp (default: all).
    ``extra``    as-of values for domain-declared axes.
    """

    valid: str | None = None
    recorded: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Scope:
    """Restricts search before it runs. Empty tuples mean no restriction."""

    source_ids: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    unit_prefix: str = ""


#: Router intents.
INTENTS = ("lookup", "multi_hop", "compute", "table", "out_of_scope")


@dataclass
class Query:
    """A question after the understand stage."""

    text: str
    as_of: AsOf = field(default_factory=AsOf)
    scope: Scope = field(default_factory=Scope)
    intent: str = "lookup"
    confidence: float = 1.0
    #: Set when the router wants to ask the user one question before searching.
    clarify: str | None = None
    #: Which router layer decided: "rules", "classifier" or "default".
    decided_by: str = "default"
    #: True when the question names an explicit date (so as_of.valid came from it).
    dated: bool = False


# ----------------------------------------------------------------------------
# Retrieval, tools, drafting
# ----------------------------------------------------------------------------


@dataclass
class Passage:
    """A version of a unit returned by retrieval."""

    unit_id: str
    seq: int
    text: str
    title: str = ""
    source_id: str = ""
    score: float = 0.0
    #: Stage that last scored it: "lexical", "dense", "fused", "expand", "rerank".
    stage: str = ""
    valid_from: str | None = None
    valid_to: str | None = None
    coverage: int = COVERAGE_MAX
    certainty: str = "high"
    #: Citation mark assigned when the passage is shown to the drafter: "t1", "t2"...
    mark: str = ""


@dataclass
class ToolResult:
    """The outcome of one deterministic tool call."""

    mark: str  # "k1", "k2"...
    tool: str
    args: dict[str, Any]
    ok: bool
    value: Any = None
    #: Human-readable steps, enough to recompute by hand.
    steps: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class Usage:
    """Cost of one model call."""

    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_cached: int = 0
    usd: float = 0.0
    ms: float = 0.0
    #: Why the model stopped ("end_turn", "max_tokens", ...); "" when not reported.
    stop_reason: str = ""
    #: Number of content blocks by type in the reply (e.g. {"thinking": 1, "text": 1}).
    blocks: dict = field(default_factory=dict)
    #: Characters of visible text in the reply (the text blocks only).
    text_chars: int = 0


@dataclass
class Sentence:
    """One sentence of a draft with the marks it cites."""

    text: str
    passage_marks: list[str] = field(default_factory=list)  # ["t1", "t3"]
    tool_marks: list[str] = field(default_factory=list)  # ["k1"]


@dataclass
class Draft:
    """What the drafter produced, already parsed."""

    sentences: list[Sentence] = field(default_factory=list)
    #: Tool calls the drafter requested: [{"mark": "k1", "tool": "calc", "args": {...}}]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    #: Set when the drafter itself declined to answer.
    declined: str | None = None
    raw: str = ""
    usage: Usage = field(default_factory=Usage)


# ----------------------------------------------------------------------------
# Verification and the answer
# ----------------------------------------------------------------------------

#: Per-claim labels.
LABELS = ("supported", "partial", "unsupported")

#: Typed abstentions (knowledge) and operational outcomes.
ABSTENTIONS = (
    "no_source",  # nothing relevant was found
    "not_valid_at_date",  # sources exist but none in force at the as-of date
    "conflict",  # sources of equal authority disagree; shown, not resolved
    "false_premise",  # the question assumes something the sources contradict
    "outside_coverage",  # the corpus declares it does not cover this
    "unsupported",  # a draft was written but failed verification
    "needs_input",  # a datum only the user has is missing
    "tool_failed",  # a required computation could not be done
    "out_of_scope",  # not a question for this corpus
    "budget",  # the cost budget ran out before an answer was verified
)


@dataclass
class Claim:
    """One checked sentence of the answer."""

    text: str
    passage_marks: list[str] = field(default_factory=list)
    tool_marks: list[str] = field(default_factory=list)
    #: Entailment probability from the verifier, 0..1.
    support: float = 0.0
    label: str = "unsupported"
    #: exists / valid_at_date / supported / numbers_traced -> bool
    checks: dict[str, bool] = field(default_factory=dict)
    note: str = ""


@dataclass
class Abstention:
    type: str
    message: str = ""
    #: What was searched, so the user can see the gap.
    searched: list[str] = field(default_factory=list)


@dataclass
class StageTrace:
    stage: str
    ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0
    n_out: int = 0
    note: str = ""


#: Answer statuses.
STATUSES = ("answered", "partial", "abstained", "divergent", "needs_input")


@dataclass
class Answer:
    status: str
    text: str = ""
    claims: list[Claim] = field(default_factory=list)
    #: min(claim support, version certainty, source coverage), 0..1.
    grade: float = 0.0
    abstention: Abstention | None = None
    passages: list[Passage] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    query: Query | None = None
    trace: list[StageTrace] = field(default_factory=list)

    @property
    def usd(self) -> float:
        return sum(t.usd for t in self.trace)

    @property
    def ms(self) -> float:
        return sum(t.ms for t in self.trace)

    @property
    def citations(self) -> list[tuple[str, int]]:
        """(unit_id, seq) for every passage cited by a supported or partial claim."""
        by_mark = {p.mark: p for p in self.passages}
        out: list[tuple[str, int]] = []
        for c in self.claims:
            if c.label == "unsupported":
                continue
            for m in c.passage_marks:
                p = by_mark.get(m)
                if p and (p.unit_id, p.seq) not in out:
                    out.append((p.unit_id, p.seq))
        return out
