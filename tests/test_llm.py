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


def http_400(text):
    return urllib.error.HTTPError("u", 400, "x", {}, io.BytesIO(text.encode()))


def test_temperature_default_sends_none_and_explicit_is_sent():
    calls = []
    llm, _ = make([OK], calls)
    llm.complete("s", "p")
    assert llm.temperature is None and llm.temperature_sent is False
    assert "temperature" not in json.loads(calls[0].data)
    llm2, _ = make([OK], calls, temperature=0.0)
    llm2.complete("s", "p")
    assert llm2.temperature_sent is True
    assert json.loads(calls[-1].data)["temperature"] == 0.0
    llm3, _ = make([OK], calls, temperature=0.7)
    llm3.complete("s", "p")
    assert json.loads(calls[-1].data)["temperature"] == 0.7


def test_temperature_400_falls_back_once_and_is_remembered():
    calls = []
    err = http_400('{"error":{"message":"`temperature` is deprecated for this model."}}')
    llm, sleeps = make([err, OK, OK], calls, temperature=0.0)
    text, _ = llm.complete("s", "p")
    assert text == "hello [t1]." and llm.temperature_sent is False
    assert "temperature" in json.loads(calls[0].data)
    assert "temperature" not in json.loads(calls[1].data)
    assert sleeps == []
    llm.complete("s", "p")
    assert len(calls) == 3 and "temperature" not in json.loads(calls[2].data)


def test_other_400_is_not_retried():
    calls = []
    llm, _ = make([http_400('{"error":"max_tokens too large"}'), OK], calls, temperature=0.0)
    with pytest.raises(LLMError):
        llm.complete("s", "p")
    assert len(calls) == 1 and llm.temperature_sent is True


def test_thinking_setting_is_sent_and_stop_reason_and_blocks_are_recorded():
    calls = []
    reply = {
        "content": [{"type": "thinking", "thinking": "hmm", "signature": "s"},
                    {"type": "text", "text": "ans"}],
        "stop_reason": "max_tokens",
        "usage": {"input_tokens": 10, "output_tokens": 600},
    }
    llm, _ = make([reply], calls, thinking={"type": "disabled"})
    text, u = llm.complete("s", "p")
    assert json.loads(calls[0].data)["thinking"] == {"type": "disabled"}
    assert text == "ans" and u.text_chars == 3
    assert u.stop_reason == "max_tokens" and u.blocks == {"thinking": 1, "text": 1}


def test_thinking_default_sends_no_field():
    calls = []
    llm, _ = make([OK], calls)
    llm.complete("s", "p")
    assert "thinking" not in json.loads(calls[0].data)
    assert llm.thinking_sent is False


# ---------------------------------------------------------------------------
# cache break (v2 contracts section 8)
# ---------------------------------------------------------------------------

from heuresis.llm import CACHE_BREAK


def _body(calls):
    return json.loads(calls[0].data.decode())


def test_cache_off_payload_unchanged_and_marker_stripped():
    calls = []
    llm, _ = make([OK, OK], calls)
    assert llm.supports_cache_break is False
    llm.complete("sys", "plain prompt")
    b = _body(calls)
    assert b["system"] == "sys"
    assert b["messages"] == [{"role": "user", "content": "plain prompt"}]
    calls.clear()
    llm.complete("sys", "stable" + CACHE_BREAK + "volatile")
    assert _body(calls)["messages"][0]["content"] == "stablevolatile"


def test_cache_on_splits_at_last_marker():
    calls = []
    llm, _ = make([OK], calls, cache=True)
    assert llm.supports_cache_break is True
    llm.complete("sys", "a" + CACHE_BREAK + "b" + CACHE_BREAK + "c")
    b = _body(calls)
    eph = {"type": "ephemeral"}
    assert b["system"] == [{"type": "text", "text": "sys", "cache_control": eph}]
    assert b["messages"][0]["content"] == [
        {"type": "text", "text": "ab", "cache_control": eph},
        {"type": "text", "text": "c"},
    ]


def test_cache_on_without_marker_is_single_plain_block():
    calls = []
    llm, _ = make([OK], calls, cache=True)
    llm.complete("sys", "no marker")
    assert _body(calls)["messages"][0]["content"] == [{"type": "text", "text": "no marker"}]


def test_cache_write_tokens_are_priced():
    calls = []
    payload = {"content": [{"type": "text", "text": "x"}],
               "usage": {"input_tokens": 100, "output_tokens": 10,
                         "cache_creation_input_tokens": 400, "cache_read_input_tokens": 0}}
    llm, _ = make([payload], calls, cache=True)
    _t, u = llm.complete("s", "p")
    assert u.usd == pytest.approx(price("claude-haiku-5-5", 100, 10, cached=0, cache_write=400))
    assert u.usd > price("claude-haiku-5-5", 100, 10)


def test_error_message_has_status_and_api_message_but_not_key():
    calls = []
    err = http_400('{"type":"error","error":{"type":"invalid_request_error","message":"bad max_tokens"}}')
    llm, _ = make([err], calls)
    with pytest.raises(LLMError) as ei:
        llm.complete("s", "p")
    msg = str(ei.value)
    assert "400" in msg and "invalid_request_error" in msg and "bad max_tokens" in msg
    assert KEY not in msg and "x-api-key" not in msg.lower()


def test_error_message_is_truncated():
    calls = []
    llm, _ = make([http_400(json.dumps({"error": {"type": "t", "message": "m" * 1000}}))], calls)
    with pytest.raises(LLMError) as ei:
        llm.complete("s", "p")
    assert len(str(ei.value)) < 330


def test_thinking_400_falls_back_once_and_is_remembered():
    calls = []
    err = http_400('{"error":{"type":"invalid_request_error","message":"thinking is not supported"}}')
    llm, sleeps = make([err, OK, OK], calls, thinking={"type": "disabled"})
    assert llm.thinking_sent is True
    text, _ = llm.complete("s", "p")
    assert text == "hello [t1]." and llm.thinking_sent is False
    assert json.loads(calls[0].data)["thinking"] == {"type": "disabled"}
    assert "thinking" not in json.loads(calls[1].data)
    assert sleeps == []
    llm.complete("s", "p")
    assert len(calls) == 3 and "thinking" not in json.loads(calls[2].data)


def test_thinking_fallback_keeps_temperature():
    calls = []
    err = http_400('{"error":{"message":"thinking not allowed"}}')
    llm, _ = make([err, OK], calls, thinking={"type": "disabled"}, temperature=0.0)
    llm.complete("s", "p")
    assert json.loads(calls[1].data)["temperature"] == 0.0


def test_other_400_with_thinking_is_not_retried():
    calls = []
    llm, _ = make([http_400('{"error":{"message":"max_tokens too large"}}'), OK], calls,
                  thinking={"type": "disabled"})
    with pytest.raises(LLMError):
        llm.complete("s", "p")
    assert len(calls) == 1 and llm.thinking_sent is True
