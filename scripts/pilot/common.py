"""Shared helpers for the zero-cost dev-split pilot. No model API is ever called."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

OUT = os.path.join(ROOT, "runs", "pilot-dev")
DATASETS = ("musique", "multihoprag", "hoh")


def db_path(name: str) -> str:
    return os.path.join(OUT, name, "store.sqlite")


def load_dev(name: str):
    """Load a dataset and return (dataset, dev questions). Only the dev split is read."""
    from heuresis.bench.datasets import load
    ds = load(name, root=os.path.join(ROOT, "data"))
    return ds, tuple(sorted(ds.questions["dev"], key=lambda q: q.id))
