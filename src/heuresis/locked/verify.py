"""Claim verification: four checks per sentence."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from ..model import AsOf, Claim, Draft, Passage, Sentence, ToolResult

_MARK_RE = re.compile(r"\[[tk]\d+\]")
_PLACEHOLDER_RE = re.compile(r"\{(k\d+)\}")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
_AND_RE = re.compile(r"\s+and\s+", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------


def parse_number(token: str) -> Decimal | None:
    """Normalise "1,200.50", "1.200,50", "4.8", "1.200" to a Decimal.

    Both separators present: the last one is the decimal mark. One separator
    repeated: thousands. One separator once: thousands if exactly three digits
    follow and one to three non-zero-leading digits precede it, else decimal.
    """
    s = token.strip()
    if "." in s and "," in s:
        dec = "." if s.rfind(".") > s.rfind(",") else ","
        thou = "," if dec == "." else "."
        s = s.replace(thou, "").replace(dec, ".")
    else:
        for sep in (".", ","):
            n = s.count(sep)
            if n == 0:
                continue
            if n > 1:
                s = s.replace(sep, "")
            else:
                before, after = s.split(sep)
                if len(after) == 3 and 1 <= len(before) <= 3 and not before.startswith("0"):
                    s = before + after
                else:
                    s = before + "." + after
    try:
        return Decimal(s).normalize()
    except InvalidOperation:
        return None


def _key(d: Decimal) -> str:
    return format(d.normalize(), "f")


def extract_numbers(text: str) -> list[Decimal]:
    out = []
    for m in _NUM_RE.finditer(text):
        v = parse_number(m.group(0))
        if v is not None:
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _in_force(p: Passage, date: str) -> bool:
    return (p.valid_from is None or p.valid_from <= date) and (
        p.valid_to is None or date < p.valid_to
    )


def _render_value(value: Any) -> str:
    return "" if value is None else str(value)


def _split_atomic(text: str) -> list[str]:
    """Split on semicolons, then on " and " when both sides have >= 3 words."""
    pieces: list[str] = []
    for part in re.split(r"\s*;\s*", text):
        part = part.strip()
        if not part:
            continue
        cur = part
        out: list[str] = []
        while True:
            m = None
            for cand in _AND_RE.finditer(cur):
                left, right = cur[: cand.start()], cur[cand.end():]
                if len(left.split()) >= 3 and len(right.split()) >= 3:
                    m = cand
                    break
            if m is None:
                out.append(cur)
                break
            out.append(cur[: m.start()])
            cur = cur[m.end():]
        pieces.extend(p.strip() for p in out if p.strip())
    return pieces or [text]


def _expand(sentence: Sentence, atomic: bool) -> list[Sentence]:
    if not atomic:
        return [sentence]
    clean = _MARK_RE.sub("", sentence.text)
    pieces = _split_atomic(clean)
    if len(pieces) == 1:
        return [sentence]
    return [Sentence(p, list(sentence.passage_marks), list(sentence.tool_marks)) for p in pieces]


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def verify(draft, passages, tool_results, store, as_of: AsOf, entailer, cfg) -> list[Claim]:
    by_mark = {p.mark: p for p in passages if p.mark}
    tools = {t.mark: t for t in tool_results}
    date = as_of.valid or _today()
    year = date[:4]

    sentences: list[Sentence] = []
    for s in draft.sentences:
        sentences.extend(_expand(s, cfg.atomic_claims))

    claims: list[Claim] = []
    pairs: list[tuple[str, str]] = []
    pair_idx: list[int] = []
    notes: list[list[str]] = []

    for s in sentences:
        pm = list(s.passage_marks)
        tm = list(s.tool_marks)
        cited_p = [by_mark[m] for m in pm if m in by_mark]
        cited_t = [tools[m] for m in tm if m in tools and tools[m].ok]
        note: list[str] = []

        # exists
        missing = [m for m in pm if m not in by_mark] + [
            m for m in tm if m not in tools or not tools[m].ok
        ]
        exists = bool(pm or tm) and not missing
        if not (pm or tm):
            note.append("no citation marks")
        elif missing:
            note.append("unresolved mark(s): " + ", ".join(missing))

        # valid_at_date
        stale: list[str] = []
        for p in cited_p:
            if store is not None:
                v = store.text_at(p.unit_id, as_of)
                ok = v is not None and v.seq == p.seq
            else:
                ok = _in_force(p, date)
            if not ok:
                stale.append(f"{p.unit_id}@{p.seq}")
        valid = not stale
        if stale:
            note.append(f"not in force at {date}: " + ", ".join(stale))

        # text with tool placeholders filled
        def fill(m: re.Match) -> str:
            t = tools.get(m.group(1))
            return _render_value(t.value) if t is not None and t.ok else m.group(0)

        text = _MARK_RE.sub("", s.text)
        hypothesis = _PLACEHOLDER_RE.sub(fill, text).strip()

        # numbers_traced
        allowed = set()
        for p in cited_p:
            allowed.update(_key(v) for v in extract_numbers(p.text))
        for t in cited_t:
            allowed.update(_key(v) for v in extract_numbers(_render_value(t.value)))
        ignore_text = hypothesis
        if as_of.valid:
            ignore_text = ignore_text.replace(as_of.valid, " ")
        untraced = []
        for m in _NUM_RE.finditer(ignore_text):
            tok = m.group(0)
            if tok == year:
                continue
            v = parse_number(tok)
            if v is not None and _key(v) not in allowed:
                untraced.append(tok)
        traced = not untraced
        if untraced:
            note.append("number(s) not traced: " + ", ".join(untraced))

        claims.append(
            Claim(
                text=hypothesis,
                passage_marks=pm,
                tool_marks=tm,
                support=0.0,
                label="unsupported",
                checks={
                    "exists": exists,
                    "valid_at_date": valid,
                    "supported": False,
                    "numbers_traced": traced,
                },
                note="",
            )
        )
        notes.append(note)

        if cited_p or cited_t:
            premise = "\n".join(
                [p.text for p in cited_p]
                + [_render_value(t.value) for t in cited_t]
            )
            pairs.append((premise, hypothesis))
            pair_idx.append(len(claims) - 1)

    if pairs:
        scores = entailer.entail(pairs)
        for i, sc in zip(pair_idx, scores):
            claims[i].support = float(sc)

    for c, note in zip(claims, notes):
        if c.support >= cfg.support_threshold:
            label = "supported"
        elif c.support >= cfg.partial_threshold:
            label = "partial"
        else:
            label = "unsupported"
        c.checks["supported"] = label == "supported"
        c.label = label
        if not (c.checks["exists"] and c.checks["valid_at_date"] and c.checks["numbers_traced"]):
            c.label = "unsupported"
        elif label == "partial":
            note.append("partial support")
        elif label == "unsupported":
            note.append("low support")
        c.note = "; ".join(note)
    return claims
