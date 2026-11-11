import io
import json
import urllib.error

import pytest

from heuresis.llm import AnthropicLLM, BudgetedLLM, BudgetExceeded, LLMError
from heuresis.model import Usage
from heuresis.pricing import PRICES, price

KEY = "sk-test-secret-123"


class Resp:
    def __init__(self, payload):
        self.b = json.dumps(payload).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


OK = {
    "content": [{"type": "text", "text": "hello [t1]."}],
    "usage": {"input_tokens": 1000, "output_tokens": 100, "cache_read_input_tokens": 500},
}


def http_error(code, retry_after=None):
    h = {"retry-after": retry_after} if retry_after else {}
    return urllib.error.HTTPError("u", code, "x", h, io.BytesIO(b'{"error":"e"}'))


def make(seq, calls, **kw):
    def fake(req, timeout=None):
        calls.append(req)
        item = seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return Resp(item)

    sleeps = []
    llm = AnthropicLLM("claude-haiku-5-5", api_key=KEY, urlopen=fake, sleep=sleeps.append, **kw)
    return llm, sleeps


def test_success_and_usage():
    calls = []
    llm, _ = make([OK], calls)
    text, u = llm.complete("sys", "hi", max_tokens=50)
    assert text == "hello [t1]."
    assert (u.tokens_in, u.tokens_out, u.tokens_cached) == (1000, 100, 500)
    assert u.usd == pytest.approx(price("claude-haiku-5-5", 1000, 100, cached=500))
    r = calls[0]
    assert r.full_url == "https://api.anthropic.com/v1/messages"
    assert r.get_header("X-api-key") == KEY
    assert r.get_header("Anthropic-version") == "2023-06-01"
    body = json.loads(r.data)
    assert body["max_tokens"] == 50 and body["system"] == "sys"


def test_retry_429_then_success_honours_retry_after():
    calls = []
    llm, sleeps = make([http_error(429, "7"), OK], calls)
    text, _ = llm.complete("s", "p")
    assert text and len(calls) == 2 and sleeps == [7.0]


def test_backoff_and_exhausted_500():
    calls = []
    llm, sleeps = make([http_error(500)] * 3, calls, max_retries=2)
    with pytest.raises(LLMError):
        llm.complete("s", "p")
    assert len(calls) == 3 and sleeps == [1.0, 2.0]


def test_non_retryable_400():
    calls = []
    llm, sleeps = make([http_error(400)], calls)
    with pytest.raises(LLMError):
        llm.complete("s", "p")
    assert len(calls) == 1 and not sleeps


def test_missing_key(monkeypatch):
    monkeypatch.delenv("PROJECTS_ANTHROPIC_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)  # must not be used as a fallback
    llm = AnthropicLLM("claude-haiku-5-5", urlopen=lambda *a, **k: pytest.fail("called"))
    with pytest.raises(RuntimeError, match="PROJECTS_ANTHROPIC_KEY") as e:
        llm.complete("s", "p")
    assert KEY not in str(e.value)


def test_key_from_custom_env_read_lazily(monkeypatch):
    monkeypatch.setenv("MY_KEY", KEY)
    calls = []
    llm = AnthropicLLM("claude-haiku-5-5", key_env="MY_KEY",
                       urlopen=lambda r, timeout=None: (calls.append(r), Resp(OK))[1])
    llm.complete("s", "p")
    assert calls[0].get_header("X-api-key") == KEY
    assert KEY not in repr(llm)


def test_base_url_env_ignored(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://evil.example")
    calls = []
    llm, _ = make([OK], calls)
    llm.complete("s", "p")
    assert calls[0].full_url.startswith("https://api.anthropic.com/")
    llm2 = AnthropicLLM("claude-haiku-5-5", base_url="http://localhost:1/")
    assert llm2.base_url == "http://localhost:1"


def test_error_text_has_no_key():
    calls = []
    llm, _ = make([http_error(500)], calls, max_retries=0)
    with pytest.raises(LLMError) as e:
        llm.complete("s", "p")
    assert KEY not in str(e.value) and KEY not in repr(llm)


class Fixed:
    id = "fixed"

    def __init__(self, usd):
        self.usd, self.n = usd, 0

    def complete(self, system, prompt, *, max_tokens=600):
        self.n += 1
        return "x", Usage(usd=self.usd)


def test_budget_blocks_before_call():
    inner = Fixed(0.4)
    b = BudgetedLLM(inner, 0.5)
    b.complete("s", "p")
    b.complete("s", "p")  # total 0.8 >= cap, allowed because 0.4 < 0.5 before
    with pytest.raises(BudgetExceeded):
        b.complete("s", "p")
    assert inner.n == 2 and b.spent == pytest.approx(0.8)


def test_budget_zero_cap():
    inner = Fixed(0.1)
    with pytest.raises(BudgetExceeded):
        BudgetedLLM(inner, 0).complete("s", "p")
    assert inner.n == 0


def test_price_haiku_tiers():
    assert price("claude-haiku-5-5", 100_000, 10_000) == pytest.approx(0.01 + 0.005)
    # one token above the boundary: the whole request moves to the higher tier
    assert price("claude-haiku-5-5", 100_001, 10_000) == pytest.approx(100_001 * 0.5e-6 + 10_000 * 2.5e-6)
    # cached tokens count toward the tier
    assert price("claude-haiku-5-5", 50_000, 0, cached=50_001) == pytest.approx(
        50_000 * 0.5e-6 + 50_001 * 0.05e-6)


def test_price_sonnet_batch_cache():
    assert price("claude-sonnet-5-5", 1_000_000, 1_000_000) == pytest.approx(12.0)
    assert price("claude-sonnet-5-5", 1_000_000, 1_000_000, batch=True) == pytest.approx(6.0)
    assert price("claude-sonnet-5-5", 0, 0, cached=1_000_000) == pytest.approx(0.2)
    assert price("claude-sonnet-5-5", 0, 0, cache_write=1_000_000) == pytest.approx(2.5)
    assert price("claude-sonnet-5-5", 0, 0, cached=1_000_000, batch=True) == pytest.approx(0.1)


def test_price_unknown_and_unverified():
    with pytest.raises(KeyError):
        price("nope", 1, 1)
    with pytest.raises(KeyError):
        price("claude-opus-5-5", 1, 1)
    assert "anthropic-2026-11" in PRICES


def test_temperature_is_sent_when_set_and_defaults_to_zero():
    calls = []
    llm, _ = make([OK, OK, OK], calls)
    llm.complete("s", "p")
    assert llm.temperature == 0.0 and json.loads(calls[0].data)["temperature"] == 0.0
    llm2, _ = make([OK], calls, temperature=0.7)
    llm2.complete("s", "p")
    assert json.loads(calls[-1].data)["temperature"] == 0.7
    llm3, _ = make([OK], calls, temperature=None)
    llm3.complete("s", "p")
    assert "temperature" not in json.loads(calls[-1].data)
