"""Types shared by the benchmark packages."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    answers: tuple[str, ...]          # gold answers; empty for unanswerable
    answerable: bool = True
    as_of: str | None = None          # valid-time date the question is about
    gold_units: tuple[str, ...] = ()  # unit ids of supporting passages, when known
    cluster: str = ""                 # e.g. source document, for clustered statistics
    kind: str = ""                    # question type label, for breakdowns


@dataclass(frozen=True)
class Dataset:
    name: str
    corpus_dir: str                   # a folder in the `jsonl` domain format
    questions: dict[str, tuple[Question, ...]]   # split name -> questions; splits: "dev", "test", "sealed"
    licence: str
    corpus_tokens: int                # approximate size, to decide whether long-context fits
    meta: dict
