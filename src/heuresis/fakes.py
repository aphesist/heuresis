"""Deterministic, offline, zero-cost implementations of the interface protocols."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Sequence

import numpy as np

from .model import Usage
from .textutil import split_sentences

_TOKEN = re.compile(r"\w+", re.UNICODE)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_NEGATIONS = frozenset(
    "not no never none cannot without nor nao nunca nenhum nenhuma sem jamais".split()
)
_STOP = frozenset(
    "a an the of to in on at is are was were be been by for and or as it its this that "
    "with from which who what when where how do does did has have had will would shall "
    "o os as um uma de do da dos das em no na nos nas por para e ou que se foi sao".split()
)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".").rstrip(".") for n in _NUMBER.findall(text)}


def _stem(tok: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(tok) > len(suf) + 3 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


def _content(text: str) -> set[str]:
    return {
        _stem(t) for t in _tokens(text)
        if t not in _STOP and t not in _NEGATIONS and not t.isdigit()
    }


def _negated(text: str) -> bool:
    low = text.lower().replace("n't", " not")
    return any(t in _NEGATIONS for t in _tokens(low))


class HashEmbedder:
    """Hashed character n-gram embedder."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim
        self.id = f"hash-{dim}"

    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            s = f" {' '.join(_tokens(text))} "
            for n in (3, 4):
                for j in range(len(s) - n + 1):
                    h = hashlib.md5(s[j : j + n].encode("utf-8")).digest()
                    idx = int.from_bytes(h[:4], "little") % self.dim
                    out[i, idx] += 1.0 if h[4] & 1 else -1.0
            norm = float(np.linalg.norm(out[i]))
            if norm > 0:
                out[i] /= norm
        return out


class OverlapReranker:
    """Scores by the fraction of query content tokens found in the text."""

    id = "overlap"

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        q = _content(query)
        if not q:
            return [0.0 for _ in texts]
        return [len(q & _content(t)) / len(q) for t in texts]


class RuleEntailer:
    """Token containment, with number and negation mismatch forcing a low score."""

    id = "rules"

    def entail(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        return [self._one(p, h) for p, h in pairs]

    @staticmethod
    def _one(premise: str, hypothesis: str) -> float:
        hyp = _content(hypothesis)
        if not hyp:
            return 0.0
        if _numbers(hypothesis) - _numbers(premise):
            return 0.05
        if _negated(premise) != _negated(hypothesis):
            return 0.1
        return 0.05 + 0.9 * len(hyp & _content(premise)) / len(hyp)


_PASSAGE_LINE = re.compile(r"^\[(t\d+)\] \(([^)]*)\) (.*)$")


class EchoLLM:
    """Scripted replies in order, or an extractive draft from the first passage."""

    id = "echo"

    def __init__(self, script: Sequence[str] | None = None) -> None:
        self.script = list(script) if script is not None else None
        self._n = 0

    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 600
    ) -> tuple[str, Usage]:
        if self.script is not None:
            if self._n >= len(self.script):
                raise IndexError("EchoLLM script exhausted")
            text = self.script[self._n]
            self._n += 1
        else:
            text = self._extract(prompt)
        usage = Usage(model=self.id, tokens_in=len(prompt.split()), tokens_out=len(text.split()))
        return text, usage

    @staticmethod
    def _extract(prompt: str) -> str:
        for line in prompt.splitlines():
            m = _PASSAGE_LINE.match(line)
            if m:
                mark, body = m.group(1), m.group(3).strip()
                sents = split_sentences(body)
                first = sents[0] if sents else body
                if first and first[-1] not in ".!?":
                    first += "."
                return f"{first} [{mark}]"
        return "ABSTAIN no_source: no passages were provided."
