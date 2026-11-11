"""Protocols for the replaceable parts.

Every protocol has a dependency-free implementation in ``heuresis.fakes`` so the
whole engine and its test suite run offline at no cost. Local ONNX models
(``heuresis.models_local``) and the Anthropic client (``heuresis.llm``)
implement the same protocols.
"""
from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

import numpy as np

from .model import Edge, Event, Query, Source, ToolResult, Unit, Usage


@runtime_checkable
class Embedder(Protocol):
    id: str
    dim: int

    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        """Return a float32 array of shape (len(texts), dim), L2-normalised."""
        ...


@runtime_checkable
class Reranker(Protocol):
    id: str

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        """Relevance of each text to the query; higher is better."""
        ...


@runtime_checkable
class Entailer(Protocol):
    id: str

    def entail(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        """For each (premise, hypothesis), the probability in 0..1 that the
        premise supports the hypothesis."""
        ...


@runtime_checkable
class LLM(Protocol):
    id: str

    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 600
    ) -> tuple[str, Usage]:
        """One completion. Implementations record cost in the returned Usage."""
        ...


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str

    def run(self, mark: str, args: dict[str, Any]) -> ToolResult:
        """Deterministic. Never raises: failures come back with ok=False."""
        ...


class Rule(Protocol):
    """A zero-cost router rule. Returns None when it does not apply, otherwise
    a dict of Query fields to set, e.g. {"intent": "compute"}."""

    def __call__(self, text: str) -> dict[str, Any] | None: ...


class Domain(Protocol):
    """A plug-in: everything specific to one kind of corpus."""

    name: str
    #: Extra named time axes beyond valid and recorded, e.g. ("published", "effects").
    axes: tuple[str, ...]

    def read(
        self, path: str
    ) -> tuple[list[Source], list[Unit], list[Event], list[Edge]]:
        """Turn a path (folder, repository, database) into corpus objects.
        Must be deterministic and idempotent: the same input yields the same
        ids, so ingesting twice changes nothing."""
        ...

    def rules(self) -> list[Rule]: ...

    def tools(self) -> list[Tool]: ...

    def abstention_text(self, kind: str, query: Query) -> str | None:
        """Domain wording for an abstention type, or None for the default."""
        ...
