"""The decision rule: answered, partial, divergent or abstained."""
from __future__ import annotations

from ..model import Abstention, Claim, Passage

_CERT = {"low": 0.33, "medium": 0.66, "high": 1.0}


def _cited(claims: list[Claim], passages: list[Passage]) -> list[Passage]:
    by_mark = {p.mark: p for p in passages if p.mark}
    out: list[Passage] = []
    for c in claims:
        for m in c.passage_marks:
            p = by_mark.get(m)
            if p is not None and p not in out:
                out.append(p)
    return out


def _grade(kept: list[Claim], passages: list[Passage]) -> float:
    if not kept:
        return 0.0
    parts = [min(c.support for c in kept)]
    cited = _cited(kept, passages)
    if cited:
        parts.append(min(_CERT.get(p.certainty, 0.0) for p in cited))
        parts.append(min(p.coverage for p in cited) / 4)
    return max(0.0, min(1.0, min(parts)))


def _searched(passages: list[Passage]) -> list[str]:
    return [p.title or p.unit_id for p in passages]


def _units(claim: Claim, by_mark: dict[str, Passage]) -> set[str]:
    return {by_mark[m].unit_id for m in claim.passage_marks if m in by_mark}


def _has_conflict(claims, passages, store) -> bool:
    """Two supported claims citing different units, both noted "conflict", from
    sources of equal authority (when the store knows them). Never otherwise."""
    if store is None:
        return False
    by_mark = {p.mark: p for p in passages if p.mark}
    flagged = [c for c in claims if c.label == "supported" and "conflict" in c.note.lower()]
    for i, a in enumerate(flagged):
        for b in flagged[i + 1:]:
            ua, ub = _units(a, by_mark), _units(b, by_mark)
            if not ua or not ub or ua == ub:
                continue
            auth = []
            for c in (a, b):
                srcs = []
                for m in c.passage_marks:
                    p = by_mark.get(m)
                    s = store.get_source(p.source_id) if p is not None else None
                    srcs.append(s.authority if s is not None else 0)
                auth.append(max(srcs) if srcs else 0)
            if auth[0] == auth[1]:
                return True
    return False


def deterministic_failure(claim: Claim) -> bool:
    """True when a claim fails a check that does not depend on a model's judgement: a cited
    mark that does not exist, a cited version not in force at the as-of date, or a number
    found in no cited passage or tool result. A sentence with no marks at all has no cited
    mark to fail; it is not a deterministic failure here (it simply has no support, so its
    grade is 0), although its numbers still have to be traced."""
    ch = claim.checks
    cited = bool(claim.passage_marks or claim.tool_marks)
    unresolved = cited and not ch.get("exists", True)
    return bool(unresolved or not ch.get("valid_at_date", True)
                or not ch.get("numbers_traced", True))


def _abstain_unverifiable(claims, searched):
    failing = [c for c in claims if deterministic_failure(c)]
    if failing and all(
        not c.checks.get("valid_at_date", True)
        and c.checks.get("exists", True)
        and c.checks.get("numbers_traced", True)
        for c in failing
    ):
        return (
            "abstained",
            0.0,
            Abstention("not_valid_at_date", "No cited source was in force at the date.", searched),
        )
    return "abstained", 0.0, Abstention("unsupported", "The draft could not be verified.", searched)


def decide(claims, passages, query, cfg, store=None, *, declined: str | None = None):
    """Return (status, grade, abstention).

    ``cfg.mode == "strict"``: a sentence below the support threshold is removed and too many
    removals withhold the answer. ``"grade"`` (the default): only deterministic failures
    (:func:`deterministic_failure`) remove a sentence, and the answer is withheld only when
    every sentence fails one or the model itself abstained; entailment support does not
    remove anything, it sets the grade."""
    searched = _searched(passages)
    if declined:
        return "abstained", 0.0, Abstention(declined, "The drafter declined to answer.", searched)
    if not passages:
        return "abstained", 0.0, Abstention("no_source", "No relevant source was found.", searched)
    if not claims:
        return "abstained", 0.0, Abstention("unsupported", "The draft made no checkable claim.", searched)

    if _has_conflict(claims, passages, store):
        kept = [c for c in claims if c.label != "unsupported"]
        return (
            "divergent",
            _grade(kept, passages),
            Abstention("conflict", "Sources of equal authority disagree.", searched),
        )

    if getattr(cfg, "mode", "strict") == "grade":
        kept = [c for c in claims if not deterministic_failure(c)]
        if not kept:
            return _abstain_unverifiable(claims, searched)
        status = "answered" if len(kept) == len(claims) else "partial"
        return status, _grade(kept, passages), None

    supported = [c for c in claims if c.label == "supported"]
    frac = len(supported) / len(claims)
    if frac >= cfg.min_supported_fraction:
        return "answered", _grade(supported, passages), None
    if frac >= cfg.partial_fraction:
        kept = [c for c in claims if c.label != "unsupported"]
        return "partial", _grade(kept, passages), None

    failing = [c for c in claims if c.label == "unsupported"]
    if failing and all(
        not c.checks.get("valid_at_date", True)
        and c.checks.get("exists", True)
        and c.checks.get("numbers_traced", True)
        for c in failing
    ):
        return (
            "abstained",
            0.0,
            Abstention("not_valid_at_date", "No cited source was in force at the date.", searched),
        )
    return "abstained", 0.0, Abstention("unsupported", "The draft could not be verified.", searched)
