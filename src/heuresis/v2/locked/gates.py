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
    """The date the validity gate uses (today when none was given)."""
    return (as_of.valid or datetime.now(timezone.utc).date().isoformat())[:10]


def _as_of_parts(as_of_valid: str | None) -> tuple[str, str, str] | None:
    """(year, month, day) of the as-of date as given by the caller; ``None`` when not given or
    not a full ISO date. Today's date is never used here: the number gates must not depend on
    the day they run."""
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", (as_of_valid or "").strip()[:10])
    return (m.group(1), m.group(2), m.group(3)) if m else None


def _date_patterns(parts: tuple[str, str, str]) -> list[re.Pattern]:
    y, mo, d = (re.escape(str(int(parts[0]))), re.escape(str(int(parts[1]))),
                re.escape(str(int(parts[2]))))
    return [
        re.compile(rf"(?<!\d){y}-0?{mo}-0?{d}(?!\d)"),
        re.compile(rf"(?<!\d)0?{d}[/.\-]0?{mo}[/.\-]{y}(?!\d)"),
    ]


def untraced_numbers(text: str, allowed: set[str], as_of_valid: str | None = None) -> list[str]:
    """The numbers written in digits in ``text`` that are not in ``allowed`` (keys of
    ``_num_keys``). The as-of date is allowed in its usual renderings (ISO, dd/mm/yyyy) and its
    year alone; its day and month numbers only when the year also occurs in ``text``. With no
    as-of date, no date digits are allowed."""
    text = text or ""
    parts = _as_of_parts(as_of_valid)
    extra: set[str] = set()
    scan = text
    if parts is not None:
        for pat in _date_patterns(parts):
            scan = pat.sub(" ", scan)
        year = _key(Decimal(parts[0]))
        extra.add(year)
        if year in _num_keys(text):
            extra |= {_key(Decimal(parts[1])), _key(Decimal(parts[2]))}
    out = []
    for m in _NUM_RE.finditer(scan):
        v = parse_number(m.group(0))
        if v is not None and _key(v) not in allowed and _key(v) not in extra:
            out.append(m.group(0))
    return out


def numbers_of(text: str) -> set[str]:
    """Number keys of the numbers written in digits in ``text``."""
    return _num_keys(text)


def _flatten(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if k != "db":
                _flatten(v, out)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _flatten(v, out)
    elif value is not None:
        out.append(str(value))


def tool_arg_untraced(t: ToolResult, allowed: set[str], as_of_valid: str | None) -> list[str]:
    """The numbers in the arguments of tool call ``t`` that are not in ``allowed`` (nor the
    as-of date by the rule of ``untraced_numbers``)."""
    parts: list[str] = []
    _flatten(getattr(t, "args", None), parts)
    return untraced_numbers(" ; ".join(parts), allowed, as_of_valid)


def allowed_tool_keys(tool_results, allowed: set[str], as_of_valid: str | None) -> set[str]:
    """Number keys of the values of the ok tool results whose arguments are all traced to
    ``allowed`` (rule: a tool value is used only if every number in its call is traced)."""
    out: set[str] = set()
    for t in tool_results or ():
        if getattr(t, "ok", False) and not tool_arg_untraced(t, allowed, as_of_valid):
            out |= _num_keys(_render(t.value))
    return out


def _in_force(p: Passage, date: str) -> bool:
    return (p.valid_from is None or p.valid_from <= date) and (
        p.valid_to is None or date < p.valid_to)


def _blank(claim_text: str, kind: str) -> Claim:
    return Claim(text=claim_text, kind=kind,
                 checks={c: False for c in CHECKS}, note="could not be checked")


def _tool_uses(s, tools) -> tuple[list[str], list[str]]:
    """(marks of tools the sentence uses, those among them that are missing or not ok): its
    ``[kN]`` marks and its ``{kN}`` placeholders."""
    used = list(dict.fromkeys([*s.tool_marks, *_PLACEHOLDER_RE.findall(s.text or "")]))
    bad = [m for m in used if m not in tools or not tools[m].ok]
    return used, bad


def _eval(s, by_mark, tools, store, as_of, date, question_keys, domain, extra_keys) -> Claim:
    """One sentence. A sentence with a passage mark is ``cited``; any other is ``derived`` (it
    may carry tool marks). ``extra_keys`` are the numbers of cited sentences that pass the
    gates; they only trace tool arguments (and the numbers of a derived sentence)."""
    cited = bool(s.passage_marks)
    pm, tm = list(s.passage_marks), list(s.tool_marks)
    cited_p = [by_mark[m] for m in pm if m in by_mark]
    notes: list[str] = []
    asv = as_of.valid

    used, bad_tools = _tool_uses(s, tools)
    missing = [m for m in pm if m not in by_mark] + bad_tools
    exists = not missing
    if missing:
        notes.append("mark not shown or tool result missing: " + ", ".join(missing))
    if not cited:
        if not extra_keys_present(extra_keys):
            exists = False
            notes.append("no mark, and no cited sentence of the answer passes the checks")

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

    text = _PLACEHOLDER_RE.sub(fill, _MARK_RE.sub("", s.text)).strip()

    refs_ok = True
    refs: list = []
    if has_resolver(domain):
        refs = domain_references(domain, text, store)
        if cited:
            problems = [w for r in refs if (w := reference_problems(r, cited_p))]
            refs_ok = not problems
            if problems:
                notes.append("reference problem: " + "; ".join(problems))
        elif refs:
            refs_ok = False
            notes.append("a conclusion without marks names a reference: "
                         + "; ".join(r.text for r in refs))

    # what the arguments of the tool calls may be traced to
    trace_keys = set(question_keys) | set(extra_keys)
    for p in cited_p:
        trace_keys |= _num_keys(p.text) | _num_keys(p.title)
    allowed = set(question_keys) | set(extra_keys) if not cited else set(question_keys)
    for p in cited_p:
        allowed |= _num_keys(p.text) | _num_keys(p.title) | _num_keys(p.unit_id)
    arg_bad: list[str] = []
    for m in used:
        t = tools.get(m)
        if t is None or not t.ok:
            continue
        un = tool_arg_untraced(t, trace_keys, asv)
        if un:
            arg_bad.append(f"tool {m} ({t.tool}) argument not traced: " + ", ".join(un))
        else:
            allowed |= _num_keys(_render(t.value))
    notes += arg_bad

    untraced = untraced_numbers(text, allowed, asv)
    if untraced:
        notes.append(("number not in the cited passages: " if cited else
                      "number not in the question, the date or a cited sentence: ")
                     + ", ".join(untraced))
    return Claim(
        text=text, passage_marks=pm, tool_marks=tm, kind="cited" if cited else "derived",
        checks={"exists": exists, "valid_at_date": valid,
                "numbers_traced": not untraced and not arg_bad, "references_traced": refs_ok},
        note="; ".join(notes))


def extra_keys_present(extra) -> bool:
    return bool(getattr(extra, "has_passing", False))


class _Keys(set):
    """Number keys of the passing cited sentences, plus whether there is any such sentence."""

    has_passing = False


def check(draft: Draft, passages: list[Passage], tool_results: list[ToolResult], store,
          as_of: AsOf, *, question: str = "", domain=None) -> list[Claim]:
    """One ``Claim`` per sentence with the four checks of section 6.1."""
    date = _date_of(as_of)
    sentences = list(getattr(draft, "sentences", []) or [])
    by_mark = {p.mark: p for p in passages or [] if getattr(p, "mark", "")}
    tools = {t.mark: t for t in tool_results or []}
    question_keys = _num_keys(question or "")

    def one(i: int, extra: _Keys) -> Claim:
        s = sentences[i]
        try:
            return _eval(s, by_mark, tools, store, as_of, date, question_keys, domain, extra)
        except Exception as e:  # a failing sentence is the result, never an exception
            c = _blank(str(getattr(s, "text", "")), "cited" if s.passage_marks else "derived")
            c.note = f"could not be checked ({type(e).__name__})"
            return c

    cited_idx = [i for i, s in enumerate(sentences) if s.passage_marks]
    claims: dict[int, Claim] = {}
    passing: dict[int, set[str]] = {}
    # Cited sentences: a fixed point. A tool argument may be traced to another cited sentence
    # that passes; the walk starts from nothing, so every pass is grounded in the passages.
    pending = list(cited_idx)
    changed = True
    while changed:
        changed = False
        for i in list(pending):
            extra = _Keys()
            for j, ks in passing.items():
                if j != i:
                    extra |= ks
            c = one(i, extra)
            claims[i] = c
            if not deterministic_failure(c):
                passing[i] = _num_keys(c.text)
                pending.remove(i)
                changed = True
    base = _Keys()
    for ks in passing.values():
        base |= ks
    base.has_passing = bool(passing)
    for i in range(len(sentences)):
        if i not in claims:
            claims[i] = one(i, base)
    return [claims[i] for i in range(len(sentences))]


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
