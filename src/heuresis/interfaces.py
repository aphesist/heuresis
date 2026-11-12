"""Protocols for the replaceable parts.

Every protocol has a dependency-free implementation in ``heuresis.fakes`` so the
whole engine and its test suite run offline at no cost. Local ONNX models
(``heuresis.models_local``) and the Anthropic client (``heuresis.llm``)
implement the same protocols.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class Reference:
    """A citation found in free text by a domain's resolver.

    ``status`` is ``resolved`` (the cited unit exists: ``unit_ids`` names it), ``norm_only`` (the
    text cites a whole norm that exists, no unit), ``unit_not_found`` (the container exists, the
    unit named does not) or ``container_not_found`` (nothing in the corpus matches the container).
    ``container`` is the id of the containing source when it was found, ``unit`` the unit key as
    written."""

    text: str
    start: int
    end: int
    status: str
    container: str = ""
    unit: str = ""
    unit_ids: tuple[str, ...] = ()
    #: What the text said about the container, e.g. ``{"kind": "lei", "number": "9250", "year": "1995"}``.
    meta: dict = field(default_factory=dict, compare=False, hash=False)


REFERENCE_STATUSES = ("resolved", "norm_only", "unit_not_found", "container_not_found")


@runtime_checkable
class ReferenceResolver(Protocol):
    """OPTIONAL capability of a domain: find the citations of a text and resolve them against
    the store. Domains without it are unaffected (see ``domain_references``)."""

    def resolve_references(self, text: str, store: Any) -> list[Reference]: ...


def domain_references(domain: Any, text: str, store: Any) -> list[Reference]:
    """References found by ``domain``'s optional resolver; nothing when it has none."""
    fn = getattr(domain, "resolve_references", None)
    return list(fn(text, store)) if callable(fn) else []
