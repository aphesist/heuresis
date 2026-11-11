"""Small text helpers shared by several stages."""
from __future__ import annotations

import re

# A run of sentence-ending punctuation, optionally followed by citation marks such as
# "[t1][k2]", and then whitespace or the end of the text.
_END_RE = re.compile(
    r"([.!?]+)((?:\s*\[\s*[tkTK]\d+(?:\s*[,;]?\s*[tkTK]\d+)*\s*\])*)(?=\s|$)"
)

# Tokens (lowercase, without the final period) after which a period never ends a sentence.
_ABBREVIATIONS = frozenset(
    "art arts n nº no inc par al cf vs dr sr sra mr mrs ms st".split()
)
_ORDINAL_RE = re.compile(r"\d+[ºª°]$")
_DOTTED_RE = re.compile(r"^(?:[A-Za-z]\.)+[A-Za-z]$")  # e.g. "e.g", "i.e", "U.S"
_INITIAL_RE = re.compile(r"^[A-Z]$")
_NEXT_WORD_RE = re.compile(r"\s*(\S)")


def _token_before(text: str, end: int) -> str:
    start = end
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    return text[start:end].lstrip("([{\"'“‘«")


def _is_boundary(text: str, dot: int, after: int) -> bool:
    """Decide whether the single period at ``dot`` ends a sentence."""
    token = _token_before(text, dot)
    nxt = _NEXT_WORD_RE.match(text, after)
    next_char = nxt.group(1) if nxt else ""
    if token.lower() == "etc":
        return not next_char.islower()
    if token.lower() in _ABBREVIATIONS:
        return False
    if _ORDINAL_RE.search(token):
        return not next_char.islower()
    if _DOTTED_RE.match(token) or _INITIAL_RE.match(token):
        return False
    if token and token[-1].isdigit() and next_char.isdigit():
        return False
    return True


def split_sentences(text: str) -> list[str]:
    """Split ``text`` into sentences.

    A period does not end a sentence after a known abbreviation (``art.``, ``Dr.``,
    ``e.g.``, ``U.S.``), after a single capital initial, between digits (``4.8``,
    ``1.200``), after an ordinal marker followed by a lowercase letter (``2º. e``), or
    after ``etc.`` followed by a lowercase letter. Citation marks that trail the
    punctuation stay with their sentence. Pieces are stripped; empty ones are dropped.
    """
    parts: list[str] = []
    pos = 0
    for m in _END_RE.finditer(text):
        puncts = m.group(1)
        if puncts == "." and not _is_boundary(text, m.start(1), m.end()):
            continue
        parts.append(text[pos : m.end()])
        pos = m.end()
    if pos < len(text):
        parts.append(text[pos:])
    return [p.strip() for p in parts if p.strip()]
