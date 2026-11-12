"""The ``references_traced`` gate: a sentence may only name what it cites.

Every reference that a domain's resolver finds in an answer sentence (a statute and article, a
case, a file and line...) must resolve to a unit that the sentence cites by mark, i.e. a unit the
model was shown. A sentence that names a unit it does not cite, or one that does not exist in the
store, fails. Domains without a resolver are not checked (see ``interfaces.domain_references``).
The module is domain-agnostic: it only uses ``Reference`` and the passages' unit and source ids.
"""
from __future__ import annotations

from typing import Any, Iterable

from .interfaces import Reference, domain_references
from .model import Claim, Passage


def has_resolver(domain: Any) -> bool:
    return callable(getattr(domain, "resolve_references", None))


def _cited(claim: Claim, passages: Iterable[Passage]) -> list[Passage]:
    marks = set(claim.passage_marks)
    return [p for p in passages if p.mark in marks]


def reference_problems(ref: Reference, cited: list[Passage]) -> str:
    """Why ``ref`` is not traced to the cited passages; empty when it is."""
    if ref.status == "container_not_found":
        return f"{ref.text!r}: no such source in the corpus"
    if ref.status == "unit_not_found":
        return f"{ref.text!r}: the source exists, the unit does not"
    if ref.status == "norm_only":
        if any(p.source_id == ref.container for p in cited):
            return ""
        return f"{ref.text!r}: names a source none of the cited passages belongs to"
    base = ref.unit_ids
    for p in cited:
        if any(p.unit_id == u or p.unit_id.startswith(u + "!") for u in base):
            return ""
    return f"{ref.text!r}: names a unit the sentence does not cite"


def trace_claims(claims: list[Claim], passages: list[Passage], domain: Any, store: Any) -> int:
    """Check ``references_traced`` on every claim; returns how many claims failed.

    A failing claim gets ``checks["references_traced"] = False`` and ``checks["exists"] = False``:
    the locked decision rule drops a sentence whose ``exists`` check fails, so this reuses it
    without touching the locked files (the ``references_traced`` key keeps the real reason, and
    the note says which reference failed)."""
    if not has_resolver(domain):
        return 0
    failed = 0
    for c in claims:
        refs = domain_references(domain, c.text, store)
        cited = _cited(c, passages)
        problems = [x for x in (reference_problems(r, cited) for r in refs) if x]
        c.checks["references_traced"] = not problems
        if problems:
            failed += 1
            c.checks["exists"] = False
            c.note = "; ".join(x for x in (c.note, "references_traced: " + "; ".join(problems)) if x)
    return failed
