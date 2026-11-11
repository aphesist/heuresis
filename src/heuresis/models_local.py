"""Optional local models over ONNX Runtime, run on CPU.

Install the extra to use this module::

    pip install "heuresis[local]"      # onnxruntime, tokenizers, huggingface_hub

Importing this module is free: it imports neither onnxruntime nor tokenizers nor
huggingface_hub and touches no network. Everything heavy happens inside
``load_embedder`` / ``load_reranker`` / ``load_entailer``, which download the
ONNX file once and cache it under ``~/.cache/heuresis`` (override with the
``HEURESIS_CACHE`` environment variable).

Default models. All three have an official ONNX export in the model repository
(file ``onnx/model.onnx``, fp32) and a ``tokenizer.json``. Licences and sizes
were read on the model cards / repository file listings; the three models were
loaded and exercised in this environment.

| Role     | Model id                                           | Licence    | ONNX size | Output           | ONNX file URL |
|----------|----------------------------------------------------|------------|-----------|------------------|---------------|
| embedder | intfloat/multilingual-e5-small                     | MIT        | 470 MB    | 384-d, L2-norm   | https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx/model.onnx |
| reranker | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1         | Apache-2.0 | 471 MB    | 1 logit per pair | https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1/resolve/main/onnx/model.onnx |
| entailer | MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli    | MIT        | 428 MB    | 3 logits (NLI)   | https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli/resolve/main/onnx/model.onnx |

Notes.

* Embedder: e5 expects the prefixes ``"query: "`` and ``"passage: "``; they are
  added here (``is_query`` selects the prefix). Mean pooling over the attention
  mask, then L2 normalisation. Multilingual (100 languages, Portuguese included).
* Reranker: trained on mMARCO (MS MARCO machine-translated into 14 languages,
  Portuguese included). ``score`` returns the raw relevance logit (higher is
  better); it is not a probability and is not bounded.
* Entailer: trained on MNLI and XNLI. Portuguese is not one of the 15 XNLI
  languages, so its Portuguese behaviour comes from the multilingual encoder's
  cross-lingual transfer; it is checked in the tests but is the weakest of the
  three on Portuguese. Label mapping: the model's ``config.json`` has
  ``id2label = {0: entailment, 1: neutral, 2: contradiction}``. The output is
  ``softmax(logits)[entailment]``. Verified on two hand examples (premise
  "A man is playing a guitar on stage." -> hypothesis "A man is playing an
  instrument." scores high; hypothesis "Nobody is playing music." scores low).
  The mapping is read from ``config.json`` at load time and the loader refuses
  a model with no label that starts with "entail".
"""
from __future__ import annotations

import json
import os
from typing import Sequence

import numpy as np

DEFAULT_EMBEDDER = "intfloat/multilingual-e5-small"
DEFAULT_RERANKER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
DEFAULT_ENTAILER = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"

_EXTRA_HINT = (
    "Local models need optional dependencies: pip install 'heuresis[local]' "
    "(onnxruntime, tokenizers, huggingface_hub)."
)


def cache_dir() -> str:
    """Directory where downloaded models are cached."""
    d = os.environ.get("HEURESIS_CACHE") or os.path.join(
        os.path.expanduser("~"), ".cache", "heuresis"
    )
    return d


def _import_deps():
    try:
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
        import huggingface_hub  # noqa: F401
    except ImportError as e:  # pragma: no cover - depends on environment
        raise ImportError(f"{_EXTRA_HINT} Missing: {e.name}") from e
    return onnxruntime, tokenizers, huggingface_hub


class _OnnxModel:
    """An ONNX session plus its tokenizer, with length-sorted batching."""

    def __init__(self, name: str, max_length: int = 512, batch_size: int = 16,
                 threads: int | None = None):
        ort, tokenizers, hub = _import_deps()
        self.name = name
        self.max_length = max_length
        self.batch_size = batch_size
        root = os.path.join(cache_dir(), "hub")
        os.makedirs(root, exist_ok=True)
        onnx_path = hub.hf_hub_download(name, "onnx/model.onnx", cache_dir=root)
        tok_path = hub.hf_hub_download(name, "tokenizer.json", cache_dir=root)
        cfg_path = hub.hf_hub_download(name, "config.json", cache_dir=root)
        with open(cfg_path, encoding="utf-8") as f:
            self.config = json.load(f)
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads or os.cpu_count() or 1
        so.log_severity_level = 3
        self.session = ort.InferenceSession(
            onnx_path, sess_options=so, providers=["CPUExecutionProvider"]
        )
        self._input_names = [i.name for i in self.session.get_inputs()]
        self.tokenizer = tokenizers.Tokenizer.from_file(tok_path)
        pad_id = self.tokenizer.token_to_id("<pad>")
        if pad_id is None:
            pad_id = 0
        self.tokenizer.enable_padding(pad_id=pad_id, pad_token="<pad>")
        self.tokenizer.enable_truncation(max_length=max_length)

    def _run(self, encodings) -> tuple[list[np.ndarray], np.ndarray]:
        ids = np.array([e.ids for e in encodings], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._input_names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        return self.session.run(None, feeds), mask

    def _batches(self, items: list, lengths: list[int]):
        """Yield (indices, items) in length-sorted batches."""
        order = sorted(range(len(items)), key=lambda i: lengths[i])
        for s in range(0, len(order), self.batch_size):
            idx = order[s:s + self.batch_size]
            yield idx, [items[i] for i in idx]


class LocalEmbedder(_OnnxModel):
    """e5-style bi-encoder. Implements ``heuresis.interfaces.Embedder``."""

    def __init__(self, name: str = DEFAULT_EMBEDDER, **kw):
        super().__init__(name, **kw)
        self.id = f"onnx:{name}"
        self.dim = int(self.config.get("hidden_size", 0))

    def embed(self, texts: Sequence[str], *, is_query: bool = False) -> np.ndarray:
        texts = list(texts)
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        if not texts:
            return out
        prefix = "query: " if is_query else "passage: "
        items = [prefix + t for t in texts]
        for idx, batch in self._batches(items, [len(t) for t in items]):
            enc = self.tokenizer.encode_batch(batch)
            (hidden,), mask = self._run(enc)
            m = mask[:, :, None].astype(np.float32)
            pooled = (hidden * m).sum(axis=1) / np.maximum(m.sum(axis=1), 1.0)
            norm = np.linalg.norm(pooled, axis=1, keepdims=True)
            out[idx] = (pooled / np.maximum(norm, 1e-12)).astype(np.float32)
        return out


class LocalReranker(_OnnxModel):
    """Cross-encoder relevance scorer. Implements ``Reranker``."""

    def __init__(self, name: str = DEFAULT_RERANKER, **kw):
        super().__init__(name, **kw)
        self.id = f"onnx:{name}"

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        texts = list(texts)
        out = [0.0] * len(texts)
        pairs = [(query, t) for t in texts]
        for idx, batch in self._batches(pairs, [len(t) for _, t in pairs]):
            (logits,), _ = self._run(self.tokenizer.encode_batch(batch))
            logits = np.asarray(logits).reshape(len(batch), -1)[:, 0]
            for i, v in zip(idx, logits):
                out[i] = float(v)
        return out


class LocalEntailer(_OnnxModel):
    """NLI cross-encoder. Implements ``Entailer``."""

    def __init__(self, name: str = DEFAULT_ENTAILER, **kw):
        super().__init__(name, **kw)
        self.id = f"onnx:{name}"
        id2label = self.config.get("id2label") or {}
        self.entail_index = None
        for k, v in id2label.items():
            if str(v).lower().startswith("entail"):
                self.entail_index = int(k)
        if self.entail_index is None:
            raise ValueError(f"{name}: no 'entailment' label in config.json id2label")

    def entail(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        pairs = list(pairs)
        out = [0.0] * len(pairs)
        for idx, batch in self._batches(pairs, [len(a) + len(b) for a, b in pairs]):
            (logits,), _ = self._run(self.tokenizer.encode_batch(batch))
            z = np.asarray(logits, dtype=np.float64)
            z = z - z.max(axis=1, keepdims=True)
            p = np.exp(z)
            p = p / p.sum(axis=1, keepdims=True)
            for i, v in zip(idx, p[:, self.entail_index]):
                out[i] = float(v)
        return out


def load_embedder(name: str = DEFAULT_EMBEDDER, **kw) -> LocalEmbedder:
    """Load a local ONNX embedder (downloads on first use)."""
    return LocalEmbedder(name, **kw)


def load_reranker(name: str = DEFAULT_RERANKER, **kw) -> LocalReranker:
    """Load a local ONNX cross-encoder reranker (downloads on first use)."""
    return LocalReranker(name, **kw)


def load_entailer(name: str = DEFAULT_ENTAILER, **kw) -> LocalEntailer:
    """Load a local ONNX NLI entailer (downloads on first use)."""
    return LocalEntailer(name, **kw)
