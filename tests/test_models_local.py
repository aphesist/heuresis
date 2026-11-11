"""Local ONNX models. Needs the network on first run (model download), so it is
skipped unless HEURESIS_TEST_LOCAL=1."""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np
import pytest

from heuresis.interfaces import Embedder, Entailer, Reranker

pytestmark = pytest.mark.skipif(
    os.environ.get("HEURESIS_TEST_LOCAL") != "1",
    reason="set HEURESIS_TEST_LOCAL=1 to download and run the local models",
)


@pytest.fixture(scope="module")
def embedder():
    from heuresis.models_local import load_embedder
    return load_embedder()


@pytest.fixture(scope="module")
def reranker():
    from heuresis.models_local import load_reranker
    return load_reranker()


@pytest.fixture(scope="module")
def entailer():
    from heuresis.models_local import load_entailer
    return load_entailer()


def test_import_is_light():
    code = ("import sys, heuresis.models_local; "
            "bad = [m for m in ('onnxruntime', 'tokenizers', 'huggingface_hub') "
            "if m in sys.modules]; sys.exit(1 if bad else 0)")
    r = subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONPATH": "src"})
    assert r.returncode == 0


def test_cache_dir_override(monkeypatch, tmp_path):
    from heuresis.models_local import cache_dir
    monkeypatch.setenv("HEURESIS_CACHE", str(tmp_path))
    assert cache_dir() == str(tmp_path)


def test_embedder_shape_and_norm(embedder):
    assert isinstance(embedder, Embedder)
    v = embedder.embed(["one", "two words", "tres palavras em português"] * 7)
    assert v.shape == (21, embedder.dim) and embedder.dim == 384
    assert v.dtype == np.float32
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-4)
    assert embedder.embed([]).shape == (0, 384)


def test_embedder_batch_order_independent(embedder):
    texts = ["short", "a much longer sentence about the tax code of small firms " * 3,
             "medium length text here"]
    together = embedder.embed(texts)
    alone = np.vstack([embedder.embed([t]) for t in texts])
    assert np.allclose(together, alone, atol=1e-4)


@pytest.mark.parametrize("q,good,bad", [
    ("What is the capital of France?", "Paris is the capital of France.",
     "Bananas are rich in potassium."),
    ("Qual é a capital do Brasil?", "Brasília é a capital federal do Brasil.",
     "Bananas são ricas em potássio."),
])
def test_embedder_relevance(embedder, q, good, bad):
    qv = embedder.embed([q], is_query=True)[0]
    dv = embedder.embed([good, bad])
    assert float(dv[0] @ qv) > float(dv[1] @ qv)


@pytest.mark.parametrize("q,good,bad", [
    ("What is the capital of France?", "Paris is the capital of France.",
     "Bananas are rich in potassium."),
    ("Qual é a capital do Brasil?", "Brasília é a capital federal do Brasil.",
     "Bananas são ricas em potássio."),
    ("prazo para recolher o imposto", "O imposto deve ser recolhido até o dia 20 do mês seguinte.",
     "A reunião de condomínio ocorre às terças-feiras."),
])
def test_reranker_relevance(reranker, q, good, bad):
    assert isinstance(reranker, Reranker)
    s = reranker.score(q, [bad, good])
    assert len(s) == 2 and all(isinstance(x, float) for x in s)
    assert s[1] > s[0]


def test_reranker_batching(reranker):
    texts = [f"passage number {i} about taxes" for i in range(40)]
    assert len(reranker.score("taxes", texts)) == 40
    assert reranker.score("taxes", []) == []


def test_entailer_label_mapping(entailer):
    assert isinstance(entailer, Entailer)
    assert entailer.entail([]) == []
    # id2label from config.json: 0 entailment, 1 neutral, 2 contradiction
    assert entailer.entail_index == 0
    premise = "A man is playing a guitar on stage."
    s = entailer.entail([(premise, "A man is playing an instrument."),
                         (premise, "Nobody is playing music.")])
    assert all(0.0 <= x <= 1.0 for x in s)
    assert s[0] > 0.5 > s[1]


@pytest.mark.parametrize("premise,entailed,contradicted", [
    ("The contract was signed by the company in 2020.",
     "The company signed the contract.",
     "The company did not sign the contract."),
    ("A tarifa foi reduzida para 5% a partir de janeiro de 2024.",
     "A tarifa passou a ser de 5% em 2024.",
     "A tarifa não foi reduzida."),
])
def test_entailer_entailed_above_contradicted(entailer, premise, entailed, contradicted):
    a, b = entailer.entail([(premise, entailed), (premise, contradicted)])
    assert a > b
    assert a > 0.5
