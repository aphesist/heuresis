"""Deterministic gates, one set per sentence. No model is called here."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ...interfaces import domain_references
from ...locked.verify import parse_number
from ...model import AsOf, Claim, Draft, Passage, ToolResult
from ...references import has_resolver, reference_problems

CHECKS = ("exists", "valid_at_date", "numbers_traced", "references_traced")

_MARK_RE = re.compile(r"\[[tk]\d+\]")
_PLACEHOLDER_RE = re.compile(r"\{(k\d+)\}")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


def _key(d: Decimal) -> str:
    return format(d.normalize(), "f")


def _num_keys(text: str) -> set[str]:
    out = set()
    for m in _NUM_RE.finditer(text or ""):
        v = parse_number(m.group(0))
        if v is not None:
            out.add(_key(v))
    return out


def _render(value: Any) -> str:
    return "" if value is None else str(value)


def _date_of(as_of: AsOf) -> str:
    return (as_of.valid or datetime.now(timezone.utc).date().isoformat())[:10]


def _date_keys(date: str) -> set[str]:
    out = set()
    for part in date.split("-"):
        if part.isdigit():
            out.add(_key(Decimal(part)))
    return out


def _in_force(p: Passage, date: str) -> bool:
    return (p.valid_from is None or p.valid_from <= date) and (
        p.valid_to is None or date < p.valid_to)


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for a, b in spans:
        for i in range(max(a, 0), min(b, len(chars))):
            chars[i] = " "
    return "".join(chars)


def _blank(claim_text: str, kind: str) -> Claim:
    return Claim(text=claim_text, kind=kind,
                 checks={c: False for c in CHECKS}, note="could not be checked")


def _check_cited(s, by_mark, tools, store, as_of, date, question_keys, domain) -> Claim:
    pm, tm = list(s.passage_marks), list(s.tool_marks)
    cited_p = [by_mark[m] for m in pm if m in by_mark]
    cited_t = [tools[m] for m in tm if m in tools and tools[m].ok]
    notes: list[str] = []

    missing = [m for m in pm if m not in by_mark] + [
        m for m in tm if m not in tools or not tools[m].ok]
    exists = not missing
    if missing:
        notes.append("mark not shown or tool result missing: " + ", ".join(missing))

    stale: list[str] = []
    for p in cited_p:
        if store is not None:
            v = store.text_at(p.unit_id, as_of)
            ok = v is not None and v.seq == p.seq
        else:
            ok = _in_force(p, date)
        if not ok:
            stale.append(p.unit_id)
    valid = not stale
    if stale:
        notes.append(f"provision not in force at {date}: " + ", ".join(stale))

    def fill(m: re.Match) -> str:
        t = tools.get(m.group(1))
        return _render(t.value) if t is not None and t.ok else " "

    clean = _MARK_RE.sub("", s.text)
    text = _PLACEHOLDER_RE.sub(fill, clean).strip()

    refs_ok, spans = True, []
    refs: list = []
    if has_resolver(domain):
        refs = domain_references(domain, text, store)
        problems = []
        for r in refs:
            why = reference_problems(r, cited_p)
            if why:
                problems.append(why)
            else:
                spans.append((r.start, r.end))
        refs_ok = not problems
        if problems:
            notes.append("reference problem: " + "; ".join(problems))

    allowed = set(question_keys) | _date_keys(date)
    for p in cited_p:
        allowed |= _num_keys(p.text) | _num_keys(p.title)
    for t in cited_t:
        allowed |= _num_keys(_render(t.value))
    scan = _mask(text, spans).replace(as_of.valid or date, " ")
    untraced = []
    for m in _NUM_RE.finditer(scan):
        v = parse_number(m.group(0))
        if v is not None and _key(v) not in allowed:
            untraced.append(m.group(0))
    if untraced:
        notes.append("number not in the cited passages: " + ", ".join(untraced))

    return Claim(
        text=text, passage_marks=pm, tool_marks=tm, kind="cited",
        checks={"exists": exists, "valid_at_date": valid,
                "numbers_traced": not untraced, "references_traced": refs_ok},
        note="; ".join(notes))


def check(draft: Draft, passages: list[Passage], tool_results: list[ToolResult], store,
          as_of: AsOf, *, question: str = "", domain=None) -> list[Claim]:
    """One ``Claim`` per sentence with the four checks of section 6.1."""
    date = _date_of(as_of)
    sentences = list(getattr(draft, "sentences", []) or [])
    by_mark = {p.mark: p for p in passages or [] if getattr(p, "mark", "")}
    tools = {t.mark: t for t in tool_results or []}
    question_keys = _num_keys(question or "")

    claims: list[Claim | None] = [None] * len(sentences)
    # Pass 1: sentences that cite something.
    for i, s in enumerate(sentences):
        if s.passage_marks or s.tool_marks:
            try:
                claims[i] = _check_cited(s, by_mark, tools, store, as_of, date,
                                         question_keys, domain)
            except Exception as e:  # a failing sentence is the result, never an exception
                claims[i] = _blank(str(getattr(s, "text", "")), "cited")
                claims[i].note = f"could not be checked ({type(e).__name__})"
    passing = [c for c in claims if c is not None and not deterministic_failure(c)]
    base_keys = set(question_keys) | _date_keys(date)
    for c in passing:
        base_keys |= _num_keys(c.text)
    # Pass 2: derived sentences (conclusions that cite nothing).
    for i, s in enumerate(sentences):
        if claims[i] is not None:
            continue
        try:
            text = _PLACEHOLDER_RE.sub(" ", _MARK_RE.sub("", s.text)).strip()
            notes = []
            exists = bool(passing)
            if not exists:
                notes.append("no mark, and no cited sentence of the answer passes the checks")
            untraced = [m.group(0) for m in _NUM_RE.finditer(text.replace(as_of.valid or date, " "))
                        if (v := parse_number(m.group(0))) is not None and _key(v) not in base_keys]
            if untraced:
                notes.append("number not in the question, the date or a cited sentence: "
                             + ", ".join(untraced))
            refs = domain_references(domain, text, store) if has_resolver(domain) else []
            if refs:
                notes.append("a conclusion without marks names a reference: "
                             + "; ".join(r.text for r in refs))
            claims[i] = Claim(
                text=text, kind="derived",
                checks={"exists": exists, "valid_at_date": True,
                        "numbers_traced": not untraced, "references_traced": not refs},
                note="; ".join(notes))
        except Exception as e:
            claims[i] = _blank(str(getattr(s, "text", "")), "derived")
            claims[i].note = f"could not be checked ({type(e).__name__})"
    return [c for c in claims if c is not None]


def deterministic_failure(claim: Claim) -> bool:
    return any(not claim.checks.get(c, True) for c in CHECKS)


def failure_reason(claim: Claim) -> str:
    """A short plain-English reason a sentence failed a gate; empty when it did not."""
    if not deterministic_failure(claim):
        return ""
    if claim.note:
        return claim.note
    parts = {
        "exists": "a cited mark does not exist or the sentence cites nothing",
        "valid_at_date": "a cited provision is not in force at the date",
        "numbers_traced": "a number is not in the cited passages",
        "references_traced": "a named reference is not found or not cited",
    }
    return "; ".join(parts[c] for c in CHECKS if not claim.checks.get(c, True))
