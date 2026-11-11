"""Drafting prompt. This is the main token cost: keep it compact."""
from __future__ import annotations

from typing import Any, Sequence

from ..model import ABSTENTIONS, Passage

DRAFT_SYSTEM = (
    "Answer ONLY from the numbered passages. Never use outside knowledge.\n"
    "Format, one item per line:\n"
    "- Write short sentences. End EVERY sentence with the marks of the passages "
    "that support it, like [t1] or [t1][t2].\n"
    "- Never do arithmetic or date math yourself. Request it before the answer with "
    'a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write '
    "{k1} where the result goes and add the mark [k1] to that sentence.\n"
    "- Use the as-of date you are given; passages show their validity as "
    "(title; valid from..to).\n"
    "- If the passages do not answer the question, write only "
    "`ABSTAIN <type>: <reason>` with type one of: " + ", ".join(ABSTENTIONS) + "."
)


def _span(p: Passage) -> str:
    return f"valid {p.valid_from or ''}..{p.valid_to or ''}"


def draft_prompt(
    question: str,
    as_of: str | None,
    passages: Sequence[Passage],
    tools: Sequence[Any] = (),
) -> str:
    lines = [f"As-of date: {as_of or 'today'}"]
    if tools:
        lines.append("Tools: " + "; ".join(f"{t.name} ({t.description})" for t in tools))
    lines.append("Passages:")
    if passages:
        for i, p in enumerate(passages, 1):
            mark = p.mark or f"t{i}"
            text = " ".join(p.text.split())
            lines.append(f"[{mark}] ({p.title}; {_span(p)}) {text}")
    else:
        lines.append("(none)")
    lines.append(f"Question: {question}")
    return "\n".join(lines)
