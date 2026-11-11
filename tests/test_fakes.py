import numpy as np
import pytest

from heuresis.fakes import EchoLLM, HashEmbedder, OverlapReranker, RuleEntailer
from heuresis.interfaces import LLM, Embedder, Entailer, Reranker
from heuresis.model import Passage
from heuresis.surface import draft_prompt


def test_protocols():
    assert isinstance(HashEmbedder(), Embedder)
    assert isinstance(OverlapReranker(), Reranker)
    assert isinstance(RuleEntailer(), Entailer)
    assert isinstance(EchoLLM(), LLM)


def test_embedder_shape_norm_determinism():
    e = HashEmbedder(64)
    a = e.embed(["tax rate", "interest rate", ""])
    assert a.shape == (3, 64) and a.dtype == np.float32
    assert abs(np.linalg.norm(a[0]) - 1) < 1e-5
    assert np.array_equal(a, HashEmbedder(64).embed(["tax rate", "interest rate", ""]))
    q = e.embed(["tax rate"], is_query=True)[0]
    assert q @ a[0] > q @ e.embed(["weather in Paris"])[0]


def test_reranker():
    r = OverlapReranker()
    s = r.score("tax limit", ["the tax limit is high", "unrelated words"])
    assert s[0] > s[1] and s == r.score("tax limit", ["the tax limit is high", "unrelated words"])


def test_entailer_cases():
    e = RuleEntailer()
    prem = "The annual limit was 4.8 million for small firms."
    hi, number, neg, neg2 = e.entail([
        (prem, "The annual limit was 4.8 million."),
        (prem, "The annual limit was 5 million."),
        (prem, "The annual limit was not 4.8 million."),
        ("The firm is not liable for the fee.", "The firm is liable for the fee."),
    ])
    assert hi >= 0.9
    assert number < 0.2 and neg < 0.2 and neg2 < 0.2
    assert e.entail([(prem, "Pigs fly over oceans")])[0] < 0.3


def test_echo_script_and_zero_cost():
    llm = EchoLLM(["a", "b"])
    (t1, u1), (t2, _) = llm.complete("s", "p"), llm.complete("s", "p")
    assert (t1, t2) == ("a", "b") and u1.usd == 0.0
    with pytest.raises(IndexError):
        llm.complete("s", "p")


def test_echo_extractive_and_abstain():
    ps = [Passage("u", 0, "The limit is 5 million. Other detail.", title="T", mark="t1")]
    prompt = draft_prompt("limit?", "2024-01-01", ps, [])
    text, usage = EchoLLM().complete("s", prompt)
    assert text == "The limit is 5 million. [t1]" and usage.usd == 0.0
    assert text == EchoLLM().complete("s", prompt)[0]
    out, _ = EchoLLM().complete("s", draft_prompt("limit?", "2024-01-01", [], []))
    assert out.startswith("ABSTAIN no_source:")
