"""The model support gate (``verify.support = "llm"``): one call per answer.

After drafting, one model call receives every kept sentence together with the text of the
passages it cites (the versions in force at the as-of date: retrieval only returns those) and
answers SUPPORTED / PARTIAL / NOT_SUPPORTED per sentence. ``NOT_SUPPORTED`` drops the sentence like
any other failed check, ``PARTIAL`` keeps it and lowers the answer's grade, an unreadable verdict
keeps it unchanged. The wording below is deliberately NOT the wording of the benchmark's support
judge (``bench/citations.py``, ``SUPPORT_SYSTEM``); both are the same model family, so their errors
can be correlated: agreement between them is not evidence that a sentence is supported.
"""
from __future__ import annotations

import re
from typing import Sequence

from .model import Claim, Passage

SUPPORT_GATE_SYSTEM = (
    "You are the last check of a system that answers questions from a corpus. You get the draft's "
    "numbered sentences; under each one, the passages it cites. For each sentence decide whether the "
    "cited passages, read as written, back what the sentence asserts.\n"
    "SUPPORTED: every assertion of the sentence is stated by, or follows directly from, the cited "
    "passages.\n"
    "PARTIAL: the main assertion is backed, but the sentence also generalises, adds a detail, or "
    "states a conclusion the passages do not.\n"
    "NOT_SUPPORTED: the passages do not state what the sentence asserts, or say something different.\n"
    "Judge only against the passages shown, never against what you know. Reply with one line per "
    "sentence, exactly `<number>: <VERDICT>`, and nothing else."
)

_LINE = re.compile(r"^\s*(\d+)\s*[:.)-]\s*(SUPPORTED|PARTIAL|NOT[_ ]SUPPORTED)\b", re.I | re.M)
#: support value written to a claim for each verdict (the answer's grade is the lowest of them)
SUPPORT_VALUE = {"SUPPORTED": 0.9, "PARTIAL": 0.4, "NOT_SUPPORTED": 0.0}


def gate_prompt(items: Sequence[tuple[int, Claim, list[Passage]]], as_of: str | None,
                max_chars: int = 2500) -> str:
    """``items``: (number, claim, cited passages)."""
    lines = [f"As-of date: {as_of or 'today'}", ""]
    for n, claim, cited in items:
        lines.append(f"Sentence {n}: {claim.text.strip()}")
        for p in cited:
            body = " ".join(p.text.split())[:max_chars]
            lines.append(f"  Passage [{p.mark}] ({p.title}): {body}")
        lines.append("")
    lines.append("One line per sentence: `<number>: SUPPORTED`, `PARTIAL` or `NOT_SUPPORTED`.")
    return "\n".join(lines)


def parse_gate(raw: str) -> dict[int, str]:
    """Verdict per sentence number; sentences the reply does not settle are absent."""
    out: dict[int, str] = {}
    for m in _LINE.finditer(raw or ""):
        out[int(m.group(1))] = m.group(2).upper().replace(" ", "_")
    return out


def apply_verdicts(items: Sequence[tuple[int, Claim, list[Passage]]], verdicts: dict[int, str]) -> dict[str, int]:
    """Write the verdicts onto the claims; returns the counts (including ``unreadable``)."""
    counts = {"SUPPORTED": 0, "PARTIAL": 0, "NOT_SUPPORTED": 0, "unreadable": 0}
    for n, claim, _ in items:
        v = verdicts.get(n)
        if v is None:
            counts["unreadable"] += 1
            claim.checks["llm_support"] = True
            claim.note = "; ".join(x for x in (claim.note, "llm support: unreadable, kept") if x)
            continue
        counts[v] += 1
        claim.checks["llm_support"] = v != "NOT_SUPPORTED"
        claim.support = SUPPORT_VALUE[v]
        if v == "NOT_SUPPORTED":
            claim.checks["exists"] = False   # dropped by the locked rule like any failed check
            claim.label = "unsupported"
        elif v == "PARTIAL":
            claim.label = "partial"
        else:
            claim.label = "supported"
        claim.note = "; ".join(x for x in (claim.note, f"llm support: {v}") if x)
    return counts
