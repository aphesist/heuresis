"""The model judge: one call per answer, over the sentences that passed the gates.

The prompt and the parser are locked. The judge LLM is passed in by the caller and should be a
different model, or at least a different configuration (thinking off, short output), from the
generator. Model errors (``LLMError``, ``BudgetExceeded``) propagate; any parse problem gives
``readable = False``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ...model import Claim, Passage, ToolResult, Usage

SENTENCE_VERDICTS = ("SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "FOLLOWS", "NOT_FOLLOWS")

JUDGE_SYSTEM = (
    "You are a strict checker of an answer written from source passages. You are given a "
    "question, the as-of date, the numbered sentences S1..Sn of the answer and, for each "
    "cited sentence, the passages and tool values it cites. Use ONLY the text shown; use no "
    "outside knowledge.\n"
    "Reply with exactly these lines and nothing else, one per line:\n"
    "- For each cited sentence: `S<i>: SUPPORTED`, `S<i>: PARTIAL` or `S<i>: NOT_SUPPORTED`. "
    "SUPPORTED means the cited passages state all of what the sentence states. PARTIAL means "
    "they state part of it. NOT_SUPPORTED means they do not state it, or state the opposite.\n"
    "- For each derived sentence: `S<i>: FOLLOWS` or `S<i>: NOT_FOLLOWS`. FOLLOWS means it "
    "follows from the supported sentences alone, adding nothing.\n"
    "- `ANSWER: DIRECT`, `ANSWER: PARTIAL` or `ANSWER: NO`: does the answer text answer the "
    "question that was asked, as of the date (directly, partly, not at all)?\n"
    "- `SUFFICIENT: YES` or `SUFFICIENT: NO`: do the passages shown contain enough to settle "
    "the question?\n"
    "- `PREMISE: OK` or `PREMISE: FALSE`: FALSE if the passages contradict something the "
    "question assumes.\n"
    "- `CONFLICT: NONE`, or `CONFLICT: t<a>, t<b>` naming two passages, both shown as in "
    "force, that give incompatible rules or facts for the question.\n"
    "Do not explain. Do not add any other line."
)


@dataclass
class Verdict:
    #: 0-based position in the list of judged sentences (S1 is position 0) -> verdict word.
    sentences: dict[int, str] = field(default_factory=dict)
    answer: str = ""  # "DIRECT" | "PARTIAL" | "NO"
    sufficient: str = ""  # "YES" | "NO"
    premise: str = "OK"  # "OK" | "FALSE"
    conflict: tuple[str, str] | None = None
    readable: bool = False
    raw: str = ""
    usage: Usage = field(default_factory=Usage)


def _cut(text: str, n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[:n].rstrip() + " [...]"


def judge_prompt(question: str, as_of: str | None, claims: list[Claim],
                 passages: list[Passage], tool_results: list[ToolResult],
                 max_chars: int = 2500) -> str:
    by_mark = {p.mark: p for p in passages if p.mark}
    tools = {t.mark: t for t in tool_results}
    out = [f"Question: {question}", f"As-of date: {as_of or 'not given'}", "", "Answer sentences:"]
    shown_p: list[Passage] = []
    shown_t: list[ToolResult] = []
    for i, c in enumerate(claims, 1):
        if c.kind == "derived" or not (c.passage_marks or c.tool_marks):
            out.append(f"S{i} (derived): {c.text}")
            continue
        marks = "".join(f"[{m}]" for m in (*c.passage_marks, *c.tool_marks))
        out.append(f"S{i} (cited {marks}): {c.text}")
        for m in c.passage_marks:
            p = by_mark.get(m)
            if p is not None and p not in shown_p:
                shown_p.append(p)
        for m in c.tool_marks:
            t = tools.get(m)
            if t is not None and t.ok and t not in shown_t:
                shown_t.append(t)
    out += ["", "Cited passages:"]
    for p in shown_p:
        span = f"valid {p.valid_from or ''}..{p.valid_to or ''}"
        title = f"{p.title}; " if p.title else ""
        out.append(f"[{p.mark}] ({title}{span}) {_cut(p.text, max_chars)}")
    if not shown_p:
        out.append("(none)")
    if shown_t:
        out += ["", "Cited tool values:"]
        out += [f"[{t.mark}] {t.tool} = {t.value}" for t in shown_t]
    return "\n".join(out)


_S_RE = re.compile(r"^\s*S\s*(\d+)\s*[:\-]\s*([A-Za-z_ ]+?)\s*[.]?\s*$", re.I)
_KV_RE = re.compile(r"^\s*(ANSWER|SUFFICIENT|PREMISE|CONFLICT)\s*:\s*(.*?)\s*$", re.I)
_MARK_RE = re.compile(r"\bt\d+\b", re.I)


def _norm(word: str) -> str:
    return re.sub(r"[\s\-]+", "_", word.strip()).upper()


def parse_verdict(raw: str, n: int) -> Verdict:
    """Parse the reply; never raises. Sentence lines not seen read as ``NOT_SUPPORTED``."""
    v = Verdict(raw=raw if isinstance(raw, str) else "")
    try:
        seen: dict[int, str] = {}
        answer = sufficient = None
        for line in v.raw.splitlines():
            line = line.strip().strip("`").strip("*- ").strip()
            m = _S_RE.match(line)
            if m:
                word = _norm(m.group(2))
                idx = int(m.group(1)) - 1
                if word in SENTENCE_VERDICTS and 0 <= idx < n and idx not in seen:
                    seen[idx] = word
                continue
            m = _KV_RE.match(line)
            if not m:
                continue
            key, val = m.group(1).upper(), m.group(2)
            word = _norm(val.split()[0].strip(".,;")) if val.split() else ""
            if key == "ANSWER" and word in ("DIRECT", "PARTIAL", "NO") and answer is None:
                answer = word
            elif key == "SUFFICIENT" and word in ("YES", "NO") and sufficient is None:
                sufficient = word
            elif key == "PREMISE" and word in ("OK", "FALSE"):
                v.premise = word
            elif key == "CONFLICT":
                marks = []
                for x in _MARK_RE.findall(val):
                    x = x.lower()
                    if x not in marks:
                        marks.append(x)
                v.conflict = (marks[0], marks[1]) if len(marks) >= 2 else None
        v.sentences = {i: seen.get(i, "NOT_SUPPORTED") for i in range(n)}
        v.answer, v.sufficient = answer or "", sufficient or ""
        v.readable = answer is not None and sufficient is not None
    except Exception:
        v.readable = False
    return v


def judge(llm, question, as_of, claims, passages, tool_results, *, max_tokens=400) -> Verdict:
    """One call on ``claims`` (the sentences that passed the gates, in order)."""
    prompt = judge_prompt(question, as_of, claims, passages, tool_results)
    raw, usage = llm.complete(JUDGE_SYSTEM, prompt, max_tokens=max_tokens)
    v = parse_verdict(raw, len(claims))
    v.usage = usage
    return v
