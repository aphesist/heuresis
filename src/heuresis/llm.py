"""Anthropic messages client on the standard library, plus a budget wrapper."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .model import Usage
from .pricing import price


class LLMError(RuntimeError):
    """The model call failed (after retries where they apply)."""


class BudgetExceeded(RuntimeError):
    """The running cost has reached the cap; no further call is made."""


_RETRY_STATUS = {429, 529} | set(range(500, 600))


class AnthropicLLM:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        key_env: str = "PROJECTS_ANTHROPIC_KEY",
        base_url: str = "https://api.anthropic.com",
        timeout: float = 60,
        max_retries: int = 4,
        *,
        urlopen: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] | None = None,
        temperature: float | None = None,
    ):
        self.id = model
        #: Sampling temperature sent in every request; ``None`` (the default) sends none.
        self.temperature = temperature
        #: Whether requests carry ``temperature``; turns False if the API rejects it.
        self.temperature_sent = temperature is not None
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.key_env = key_env
        self._api_key = api_key
        self._urlopen = urlopen or urllib.request.urlopen
        self._sleep = sleep or time.sleep

    def __repr__(self) -> str:  # never expose the key
        return f"AnthropicLLM(model={self.model!r})"

    def _key(self) -> str:
        if not self._api_key:
            key = os.environ.get(self.key_env, "")
            if not key:
                raise RuntimeError(
                    f"environment variable {self.key_env} is not set; "
                    "export it or pass api_key to AnthropicLLM"
                )
            self._api_key = key
        return self._api_key

    @staticmethod
    def _delay(attempt: int, headers: Any) -> float:
        delay = min(2.0**attempt, 30.0)
        if headers is not None:
            ra = headers.get("retry-after") if hasattr(headers, "get") else None
            if ra:
                try:
                    delay = max(0.0, min(float(ra), 120.0))
                except ValueError:
                    pass
        return delay

    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 600
    ) -> tuple[str, Usage]:
        key = self._key()
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        base = dict(payload)
        if self.temperature_sent:
            payload["temperature"] = float(self.temperature)
        body = json.dumps(payload).encode("utf-8")
        t0 = time.perf_counter()
        last = "unknown error"
        attempt = -1
        while attempt < self.max_retries:
            attempt += 1
            req = urllib.request.Request(
                self.base_url + "/v1/messages",
                data=body,
                method="POST",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            headers = None
            try:
                with self._urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                return self._finish(payload, t0)
            except urllib.error.HTTPError as e:
                headers = e.headers
                try:
                    detail = e.read().decode("utf-8", "replace")[:300]
                except Exception:
                    detail = ""
                last = f"HTTP {e.code}: {detail}"
                if (e.code == 400 and self.temperature_sent
                        and "temperature" in detail.lower()):
                    # The model rejects the parameter: drop it for good and retry once.
                    self.temperature_sent = False
                    body = json.dumps(base).encode("utf-8")
                    attempt -= 1
                    continue
                if e.code not in _RETRY_STATUS:
                    raise LLMError(last) from None
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = f"network error: {type(e).__name__}"
            if attempt < self.max_retries:
                self._sleep(self._delay(attempt, headers))
        raise LLMError(f"giving up after {self.max_retries + 1} attempts: {last}")

    def _finish(self, payload: dict, t0: float) -> tuple[str, Usage]:
        text = "".join(
            b.get("text", "")
            for b in payload.get("content", [])
            if isinstance(b, dict) and b.get("type") == "text"
        )
        u = payload.get("usage") or {}
        tin = int(u.get("input_tokens") or 0)
        tout = int(u.get("output_tokens") or 0)
        cread = int(u.get("cache_read_input_tokens") or 0)
        cwrite = int(u.get("cache_creation_input_tokens") or 0)
        try:
            usd = price(self.model, tin, tout, cached=cread, cache_write=cwrite)
        except KeyError:
            usd = 0.0
        usage = Usage(
            model=self.model,
            tokens_in=tin,
            tokens_out=tout,
            tokens_cached=cread,
            usd=usd,
            ms=(time.perf_counter() - t0) * 1000.0,
        )
        return text, usage


class BudgetedLLM:
    """Wraps any LLM; refuses to call once the spent total has reached ``cap_usd``."""

    def __init__(self, inner: Any, cap_usd: float):
        self.inner = inner
        self.cap_usd = cap_usd
        self.spent = 0.0
        self.id = getattr(inner, "id", "")

    @property
    def remaining(self) -> float:
        return max(0.0, self.cap_usd - self.spent)

    def complete(
        self, system: str, prompt: str, *, max_tokens: int = 600
    ) -> tuple[str, Usage]:
        if self.spent >= self.cap_usd:
            raise BudgetExceeded(
                f"budget of ${self.cap_usd:.4f} reached (spent ${self.spent:.4f})"
            )
        text, usage = self.inner.complete(system, prompt, max_tokens=max_tokens)
        self.spent += usage.usd
        return text, usage
