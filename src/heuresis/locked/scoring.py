"""Answer normalisation, scoring, risk-coverage and citation metrics."""
from __future__ import annotations

import math
import re
import string
import unicodedata
from collections import Counter
from typing import Callable, Iterable, Sequence

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = set(string.punctuation)


def normalize_answer(s: str, fold_accents: bool = False) -> str:
    """SQuAD normalisation: lowercase, strip punctuation and English articles,
    collapse whitespace. ``fold_accents`` also removes diacritics (Portuguese)."""
    s = s.lower()
    if fold_accents:
        s = "".join(
            ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch)
        )
    s = "".join(ch for ch in s if ch not in _PUNCT)
    s = _ARTICLES.sub(" ", s)
    return " ".join(s.split())


def exact_match(pred: str, gold: str, fold_accents: bool = False) -> float:
    return float(normalize_answer(pred, fold_accents) == normalize_answer(gold, fold_accents))


def token_f1(pred: str, gold: str, fold_accents: bool = False) -> float:
    p = normalize_answer(pred, fold_accents).split()
    g = normalize_answer(gold, fold_accents).split()
    if not p or not g:
        return float(p == g)
    common = sum((Counter(p) & Counter(g)).values())
    if common == 0:
        return 0.0
    prec, rec = common / len(p), common / len(g)
    return 2 * prec * rec / (prec + rec)


def best_over_golds(
    metric: Callable[..., float], pred: str, golds: Iterable[str], **kw
) -> float:
    """Maximum of ``metric(pred, gold)`` over the gold answers (0.0 if none)."""
    return max((metric(pred, g, **kw) for g in golds), default=0.0)


_SCORES = {"correct": 1.0, "abstained": 0.0, "wrong": -1.0}


def penalised_score(outcome: str) -> float:
    try:
        return _SCORES[outcome]
    except KeyError:
        raise ValueError(f"unknown outcome: {outcome!r}") from None


def penalty_score(outcome: str, t: float) -> float:
    """+1 correct, 0 abstained, -t/(1-t) wrong; t in [0, 1)."""
    if not 0.0 <= t < 1.0:
        raise ValueError("t must satisfy 0 <= t < 1")
    if outcome == "wrong":
        return -t / (1 - t)
    return penalised_score(outcome)


def risk_coverage(confidences: Sequence[float], correct: Sequence[bool]) -> list[tuple[float, float]]:
    """Answer in order of decreasing confidence (ties keep input order); after k
    answers, coverage = k/n and risk = errors/k."""
    if len(confidences) != len(correct):
        raise ValueError("confidences and correct must have the same length")
    n = len(confidences)
    order = sorted(range(n), key=lambda i: -confidences[i])
    out, errors = [], 0
    for k, i in enumerate(order, 1):
        errors += 0 if correct[i] else 1
        out.append((k / n, errors / k))
    return out


def aurc(confidences: Sequence[float], correct: Sequence[bool]) -> float:
    """Area under the risk-coverage curve: the mean risk over the n coverage
    points (0.0 for no data). Lower is better."""
    curve = risk_coverage(confidences, correct)
    return sum(r for _, r in curve) / len(curve) if curve else 0.0


def selective_accuracy_at(
    confidences: Sequence[float], correct: Sequence[bool], coverage: float
) -> float:
    """Accuracy over the most confident ceil(coverage * n) answers."""
    n = len(confidences)
    if n == 0:
        return 0.0
    k = min(n, max(1, math.ceil(coverage * n - 1e-9)))
    order = sorted(range(n), key=lambda i: -confidences[i])[:k]
    return sum(1 for i in order if correct[i]) / k


def citation_precision_recall(cited: Iterable, gold_supporting: Iterable) -> tuple[float, float]:
    """Precision = cited that are gold / cited; recall = gold that are cited / gold.
    Empty cited: precision 1.0 only if gold is empty too. Empty gold: recall 1.0."""
    c, g = set(cited), set(gold_supporting)
    hit = len(c & g)
    precision = hit / len(c) if c else (1.0 if not g else 0.0)
    recall = hit / len(g) if g else 1.0
    return precision, recall


def outcome(answer_status: str, is_correct: bool | None, answerable: bool) -> str:
    """Answerable: answered+correct "correct", abstained "abstained", answered+wrong
    "wrong". Unanswerable: abstained "correct", answered "wrong". Statuses
    "answered" and "partial" count as answering; all others as abstaining."""
    answered = answer_status in ("answered", "partial")
    if not answerable:
        return "wrong" if answered else "correct"
    if not answered:
        return "abstained"
    return "correct" if is_correct else "wrong"
