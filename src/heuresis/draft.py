"""Drafting: build the prompt, call the model, parse the draft format."""
from __future__ import annotations

import dataclasses
import json
import re
from typing import Any

from .interfaces import LLM, Tool
from .textutil import split_sentences
from .model import ABSTENTIONS, Draft, Passage, Query, Sentence, ToolResult

NOT_CHECKED = "[not checked]"

_MARK_RE = re.compile(r"\[\s*([tkTK]\d+(?:\s*[,;]?\s*[tkTK]\d+)*)\s*\]")
_ITEM_RE = re.compile(r"[tkTK]\d+")
_CALL_RE = re.compile(r"^CALL\s+(\S+)\s+(\S+)\s*(.*)$", re.IGNORECASE)
_ABSTAIN_RE = re.compile(r"^ABSTAIN\b\s*([A-Za-z_]*)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s+")
_PLACEHOLDER_RE = re.compile(r"\{(k\d+)\}")


def _extract_marks(chunk: str) -> tuple[str, list[str], list[str]]:
    t_marks: list[str] = []
    k_marks: list[str] = []
    for m in _MARK_RE.finditer(chunk):
        for item in _ITEM_RE.findall(m.group(1)):
            item = item.lower()
            target = t_marks if item[0] == "t" else k_marks
            if item not in target:
                target.append(item)
    text = _MARK_RE.sub("", chunk)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text, t_marks, k_marks


def parse_draft(raw: str) -> Draft:
    """Parse the draft format. Never raises."""
    d = Draft(raw=raw if isinstance(raw, str) else "")
    try:
        for line in d.raw.splitlines():
            line = line.strip()
            if not line or line.startswith("```"):
                continue
            line = _BULLET_RE.sub("", line).strip()
            if not line:
                continue
            m = _CALL_RE.match(line)
            if m:
                mark, tool, rest = m.group(1).lower(), m.group(2), m.group(3).strip()
                try:
                    args: Any = json.loads(rest) if rest else {}
                    if not isinstance(args, dict):
                        args = {"_error": "arguments must be a JSON object"}
                except ValueError as e:
                    args = {"_error": f"invalid JSON: {e}"}
                d.tool_calls.append({"mark": mark, "tool": tool, "args": args})
                continue
            m = _ABSTAIN_RE.match(line)
            if m:
                kind = m.group(1).lower()
                d.declined = kind if kind in ABSTENTIONS else "unsupported"
                continue
            for chunk in split_sentences(line):
                text, tm, km = _extract_marks(chunk)
                if not re.search(r"\w", text):
                    # marks (or stray punctuation) alone: attach to the previous sentence
                    if d.sentences:
                        prev = d.sentences[-1]
                        prev.passage_marks += [x for x in tm if x not in prev.passage_marks]
                        prev.tool_marks += [x for x in km if x not in prev.tool_marks]
                    continue
                d.sentences.append(Sentence(text, tm, km))
    except Exception:  # defensive: parsing must never raise
        pass
    return d


def render(draft: Draft, tool_results: list[ToolResult]) -> str:
    """Join the sentences, resolve {k} placeholders and append marks as [t1][k1]."""
    by_mark = {r.mark: r for r in tool_results}

    def sub(m: re.Match) -> str:
        r = by_mark.get(m.group(1))
        if r is None or not r.ok:
            return NOT_CHECKED
        return str(r.value)

    out = []
    for s in draft.sentences:
        text = _PLACEHOLDER_RE.sub(sub, s.text)
        marks = "".join(f"[{m}]" for m in (*s.passage_marks, *s.tool_marks))
        out.append(f"{text} {marks}".rstrip())
    return " ".join(out)


def draft(llm: LLM, query: Query, passages: list[Passage], tools: list[Tool], cfg) -> Draft:
    from .surface.prompts import DRAFT_SYSTEM, draft_prompt

    max_sentences = int(getattr(cfg, "max_sentences", 0) or 0)
    kept = []
    for i, p in enumerate(passages, 1):
        kept.append(p if p.mark else dataclasses.replace(p, mark=f"t{i}"))
    prompt = draft_prompt(query.text, query.as_of.valid, kept, tools, max_sentences)
    # Drop the lowest-ranked passages (the tail) until the prompt fits; never cut one.
    while kept and len(prompt) > cfg.max_context_chars:
        kept.pop()
        prompt = draft_prompt(query.text, query.as_of.valid, kept, tools, max_sentences)
    raw, usage = llm.complete(DRAFT_SYSTEM, prompt, max_tokens=cfg.max_tokens)
    d = parse_draft(raw)
    d.raw = raw
    d.usage = usage
    return d
