"""Append-only spend ledger that survives restarts, and an LLM wrapper that uses it.

One JSON object per line. The ledger is the single source of truth for what the
benchmark has spent: ``spent`` is recomputed from the file when it is opened.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from ..fakes import EchoLLM
from ..llm import BudgetExceeded
from ..model import Usage
from ..pricing import price

__all__ = ["Ledger", "LedgerLLM", "BudgetExceeded"]


class Ledger:
    def __init__(self, path: str, cap_usd: float, margin_usd: float = 1.0,
                 dry_run: bool = False):
        self.path = str(path)
        #: A dry run is offline and costs $0: no safety margin, and ``check`` never stops it.
        self.dry_run = bool(dry_run)
        if self.dry_run:
            margin_usd = 0.0
        self.cap_usd = float(cap_usd)
        self.margin_usd = float(margin_usd)
        self._lock = threading.RLock()
        self._spent = 0.0
        self._calls = 0
        d = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(d, exist_ok=True)
        if os.path.exists(self.path):
            with open(self.path, "rb") as fh:
                data = fh.read()
            if data and not data.endswith(b"\n"):  # a torn last line: keep it apart
                with open(self.path, "ab") as fh:
                    fh.write(b"\n")
            for line in data.decode("utf-8", "replace").splitlines():
                try:
                    row = json.loads(line)
                    self._spent += float(row["usd"])
                    self._calls += 1
                except (ValueError, KeyError, TypeError):
                    continue

    @property
    def spent(self) -> float:
        with self._lock:
            return self._spent

    @property
    def calls(self) -> int:
        with self._lock:
            return self._calls

    @property
    def remaining(self) -> float:
        """Budget left before the safety margin (never negative)."""
        with self._lock:
            return max(0.0, self.cap_usd - self.margin_usd - self._spent)

    def check(self, estimated_usd: float = 0.0) -> None:
        with self._lock:
            if self.dry_run:
                return
            if self._spent + estimated_usd > self.cap_usd - self.margin_usd:
                raise BudgetExceeded(
                    f"spent ${self._spent:.4f} + estimated ${estimated_usd:.4f} would pass "
                    f"cap ${self.cap_usd:.2f} - margin ${self.margin_usd:.2f}"
                )

    def charge(self, usage: Usage, tag: str) -> None:
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tag": tag,
            "model": usage.model,
            "tokens_in": usage.tokens_in,
            "tokens_out": usage.tokens_out,
            "tokens_cached": usage.tokens_cached,
            "usd": float(usage.usd),
        }
        if usage.stop_reason:  # recorded per call when the API reports it
            row["stop_reason"] = usage.stop_reason
            row["blocks"] = dict(usage.blocks)
            row["text_chars"] = int(usage.text_chars)
        line = json.dumps(row, sort_keys=True) + "\n"
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
            self._spent += float(usage.usd)
            self._calls += 1

    def by_tag(self) -> dict[str, float]:
        out: dict[str, float] = {}
        with self._lock, open(self.path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    out[r["tag"]] = out.get(r["tag"], 0.0) + float(r["usd"])
                except (ValueError, KeyError, TypeError):
                    continue
        return out


def _is_offline(llm: Any) -> bool:
    return isinstance(llm, EchoLLM) or bool(getattr(llm, "offline", False))


class LedgerLLM:
    """Checks the ledger before each call and charges it after."""

    def __init__(self, inner: Any, ledger: Ledger, tag: str, estimate_usd: float):
        self.inner = inner
        self.ledger = ledger
        self.tag = tag
        self.estimate_usd = float(estimate_usd)
        self.id = getattr(inner, "id", "")
        self.offline = _is_offline(inner)
        if not self.offline:
            try:
                price(self.id, 0, 0)
            except KeyError:
                raise ValueError(
                    f"model {self.id!r} has no verified price in heuresis.pricing; "
                    "refusing to run it under a spend cap"
                ) from None

    def complete(self, system: str, prompt: str, *, max_tokens: int = 600) -> tuple[str, Usage]:
        self.ledger.check(self.estimate_usd)
        text, usage = self.inner.complete(system, prompt, max_tokens=max_tokens)
        self.ledger.charge(usage, self.tag)
        return text, usage
