"""Citation binding: a provision a sentence names, that exists in force and is not cited by a
mark, is added to the evidence and cited by the sentence. A reference that does not resolve, or
resolves to a unit with nothing in force at the date, is left alone (the gate fails it)."""
from __future__ import annotations

from ..interfaces import domain_references
from ..model import AsOf, Draft
from ..references import has_resolver

__all__ = ["bind"]


def _cited(unit_ids, passages) -> bool:
    return any(p.unit_id == u or p.unit_id.startswith(u + "!") for p in passages for u in unit_ids)


def bind(draft: Draft, evidence, store, domain, as_of: AsOf) -> list[str]:
    """Add the missing citations to ``draft`` in place; returns one note per binding."""
    notes: list[str] = []
    if not has_resolver(domain):
        return notes
    for s in draft.sentences:
        try:
            refs = domain_references(domain, s.text, store)
        except Exception:
            continue
        for r in refs:
            if r.status != "resolved" or not r.unit_ids:
                continue
            cited = [p for p in (evidence.by_mark(m) for m in s.passage_marks) if p is not None]
            if _cited(r.unit_ids, cited):
                continue
            for uid in r.unit_ids:
                p = store.passage_at(uid, as_of)
                if p is None:
                    continue
                shown = next((q for q in evidence.passages
                              if (q.unit_id, q.seq) == (p.unit_id, p.seq)), None)
                if shown is None:
                    added = evidence.add("Bound", [p])
                    shown = added[0] if added else None
                if shown is None:
                    continue
                if shown.mark not in s.passage_marks:
                    s.passage_marks.append(shown.mark)
                notes.append(f"bound {shown.mark} ({uid}) to: {s.text[:60]}")
                break
    return notes
