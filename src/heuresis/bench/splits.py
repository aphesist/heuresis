"""Held-out guard and rotating draws from the unused question pools.

Held-out splits (``test``, ``sealed``, ``temporal_test`` and every ``promo*``) are read only by a
registered run: ``registration_ok`` says whether a registration file contains the sha256 of the
split's ordered question ids (the hash the dataset loaders and ``bench.judge`` use).

A dataset's own splits (dev, test, sealed, dev2; see ``bench.datasets``) are cut from the full
question file ``<root>/corpora/<name>/questions.jsonl``. What none of them holds is the POOL
(MultiHop-RAG: about 1,550 questions; HoH: about 110,000; MuSiQue: none; the legal corpora: none).
Two kinds of draw come from the pool, by hash, so the same call always gives the same ids:

* ``promotion(name, k)``: the k-th block (300 ids) of the pool ordered by
  ``sha256(f"{seed}:promo:{id}")``. Read only by the improvement loop's evaluator.
* ``rotating(name, c)``: cycle c's 100 ids, ordered by ``sha256(f"{seed}:rot:{id}")``, from the pool
  WITHOUT the reserved promotion ids (the first ``PROMO_RESERVED`` blocks), stratified like the dataset's
  own splits (per stratum, proportional, largest remainder; each cycle continues where the last one
  stopped in every stratum). Draws of different cycles are disjoint from each other and from every
  reserved promotion block.

``calibration(name, k)``: the k-th block (400 ids) of the pool minus the promotion blocks, ordered by
``sha256(seed:cal:id)``; precedence in the pool is promotion, then calibration, then rotating.
``load_split(dataset, name)`` resolves ``rot<c>``, ``cal<k>`` and ``promo<k>`` in addition to the dataset's own splits.
No question text is ever printed here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Iterable, Sequence

from .types import Dataset, Question

__all__ = ["HELD_OUT", "SEED", "PROMO_N", "PROMO_RESERVED", "CAL_N", "CAL_RESERVED", "is_held_out",
           "registration_ok", "pool_ids", "rotating", "promotion", "calibration", "load_split"]

HELD_OUT = ("test", "sealed", "temporal_test")
SEED = 20261113
#: Size of a promotion block, and how many blocks are reserved (never drawn by ``rotating``).
PROMO_N = 300
PROMO_RESERVED = 2
#: Calibration blocks (``cal<k>``): 400 ids each, taken from the pool after the promotion blocks and before the
#: rotating draws; ``CAL_RESERVED`` blocks are kept out of ``rotating``. Not held out.
CAL_N = 400
CAL_RESERVED = 1
_CAL = re.compile(r"^cal(\d+)$")
_ROT = re.compile(r"^rot(\d+)$")
_PROMO = re.compile(r"^promo(\d+)$")


def is_held_out(split: str) -> bool:
    """True for the splits only a registered run (or the loop's evaluator) may read."""
    return split in HELD_OUT or split.startswith("promo")


def _ids_sha(ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def registration_ok(manifest_or_ids: Any, registration_path: str) -> str | None:
    """``None`` when the registration file's text contains the sha256 of the split's ordered question
    ids (newline-joined, in the order of the dataset's loader: pass ``[q.id for q in
    dataset.questions[split]]``; a manifest dict is read through its ``question_ids``); else the reason."""
    ids = manifest_or_ids.get("question_ids") if isinstance(manifest_or_ids, dict) else manifest_or_ids
    if not ids:
        return "no question ids to check against the registration"
    try:
        with open(registration_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return f"cannot read the registration {registration_path}: {e}"
    if _ids_sha(list(ids)) not in text:
        return f"the sha256 of the split's ordered question ids is not written in {registration_path}"
    return None


# ----------------------------------------------------------------------------
# Pools
# ----------------------------------------------------------------------------


def _corpus_dir(name: str, root: str) -> str:
    return os.path.join(root, "corpora", name)


def _rows(name: str, root: str) -> list[dict]:
    path = os.path.join(_corpus_dir(name, root), "questions.jsonl")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _manifest(name: str, root: str) -> dict:
    from .datasets import _read_manifest
    return _read_manifest(_corpus_dir(name, root)) or {}


def _questions(rows: Iterable[dict]) -> dict[str, Question]:
    from .datasets import _row_to_q
    return {r["id"]: _row_to_q(r) for r in rows}


def _stratum_of(manifest: dict):
    from .datasets import STRATUM
    key = (manifest.get("splits") or {}).get("params", {}).get("stratum", "answerable")
    return STRATUM.get(key, STRATUM["answerable"])


def _in_a_split(rows: list[dict], manifest: dict) -> set[str]:
    """Ids of the questions that are in one of the dataset's own splits."""
    if any("split" in r for r in rows):  # the legal corpora store each question with its split
        return {r["id"] for r in rows if r.get("split")}
    from .datasets import N_DEV2, _compute_splits
    params = (manifest.get("splits") or {}).get("params")
    if not params:
        raise ValueError("MANIFEST.json has no split parameters; cannot tell which questions are in a split")
    n_dev2 = (manifest.get("dev2") or {}).get("requested", N_DEV2)
    splits = _compute_splits(rows, params["stratum"], params["n_dev"], params["n_test"],
                             params["n_sealed"], params["seed"], n_dev2)
    return {q.id for qs in splits.values() for q in qs}


def pool_ids(name: str, root: str = "data") -> list[str]:
    """Ids of the questions of ``name`` that are in none of its splits, in file order."""
    rows = _rows(name, root)
    used = _in_a_split(rows, _manifest(name, root))
    return [r["id"] for r in rows if r["id"] not in used]


def _key(seed: int, tag: str, qid: str) -> str:
    return hashlib.sha256(f"{seed}:{tag}:{qid}".encode("utf-8")).hexdigest()


def _promo_order(pool: Sequence[str], seed: int) -> list[str]:
    return sorted(pool, key=lambda i: _key(seed, "promo", i))


def _after_promotion(pool: Sequence[str], seed: int, promo_n: int, promo_blocks: int) -> list[str]:
    reserved = set(_promo_order(pool, seed)[:promo_blocks * promo_n])
    return [i for i in pool if i not in reserved]


def calibration(name: str, k: int, n: int = CAL_N, *, root: str = "data", seed: int = SEED,
                promo_n: int = PROMO_N, promo_blocks: int = PROMO_RESERVED,
                cal_blocks: int = CAL_RESERVED) -> list[str]:
    """The k-th calibration block: ids ``[k*n, (k+1)*n)`` of the pool WITHOUT the reserved promotion ids, ordered
    by ``sha256(seed:cal:id)``. Disjoint from every promotion block and (``rotating`` skips them) from every
    rotating draw. Only the first ``cal_blocks`` blocks exist. ``ValueError`` if the pool is too small."""
    if k < 0 or k >= cal_blocks:
        raise ValueError(f"calibration block {k} is not reserved (blocks 0..{cal_blocks - 1})")
    rest = _after_promotion(pool_ids(name, root), seed, promo_n, promo_blocks)
    order = sorted(rest, key=lambda i: _key(seed, "cal", i))
    block = order[k * n:(k + 1) * n]
    if len(block) < n:
        raise ValueError(f"{name}: the pool has {max(0, len(order) - k * n)} ids left for calibration block "
                         f"{k} after the promotion blocks, {n} are needed")
    return block


def promotion(name: str, k: int, n: int = PROMO_N, *, root: str = "data", seed: int = SEED,
              promo_blocks: int = PROMO_RESERVED) -> list[str]:
    """The k-th promotion block: ids ``[k*n, (k+1)*n)`` of the pool ordered by ``sha256(seed:promo:id)``.
    Only the first ``promo_blocks`` blocks exist (they are the ones ``rotating`` leaves alone); a
    pool too small for the block raises ``ValueError`` saying how many ids remain."""
    if k < 0 or k >= promo_blocks:
        raise ValueError(f"promotion block {k} is not reserved (blocks 0..{promo_blocks - 1}); "
                         "rotating draws could overlap it")
    order = _promo_order(pool_ids(name, root), seed)
    block = order[k * n:(k + 1) * n]
    if len(block) < n:
        raise ValueError(f"{name}: the pool has {max(0, len(order) - k * n)} ids left for promotion block "
                         f"{k}, {n} are needed")
    return block


def rotating(name: str, cycle: int, n: int = 100, *, root: str = "data", seed: int = SEED,
             exclude: Iterable[str] = (), promo_n: int = PROMO_N,
             promo_blocks: int = PROMO_RESERVED, cal_n: int = CAL_N,
             cal_blocks: int = CAL_RESERVED) -> list[str]:
    """Cycle ``cycle``'s ``n`` ids (ordered by ``sha256(seed:rot:id)``): the pool minus the reserved
    promotion ids and ``exclude``, ordered by the same hash, stratified, and cut so that each cycle takes
    the next ``n`` (``cycle * n`` were taken before it). ``ValueError`` if fewer than ``n`` remain."""
    if cycle < 0:
        raise ValueError("cycle must be >= 0")
    from .datasets import _allocate
    pool = pool_ids(name, root)
    after = _after_promotion(pool, seed, promo_n, promo_blocks)
    reserved = set(pool) - set(after)
    cal = sorted(after, key=lambda i: _key(seed, "cal", i))[:cal_blocks * cal_n]
    reserved |= set(cal)
    drop = reserved | set(exclude)
    rest = [i for i in pool if i not in drop]
    left = len(rest) - cycle * n
    if left < n:
        raise ValueError(f"{name}: {max(0, left)} questions remain in the pool for rotating cycle {cycle} "
                         f"({len(rest)} after the {len(reserved)} reserved for promotion and calibration"
                         f"{' and the excluded' if exclude else ''}), {n} are needed")
    rows = _rows(name, root)
    keep = set(rest)
    qs = _questions(r for r in rows if r["id"] in keep)
    stratum = _stratum_of(_manifest(name, root))
    strata: dict[Any, list[str]] = {}
    for i in sorted(rest, key=lambda i: _key(seed, "rot", i)):
        strata.setdefault(stratum(qs[i]), []).append(i)
    weights = {s: len(v) for s, v in strata.items()}
    pointer = {s: 0 for s in strata}
    picked: list[str] = []
    for _ in range(cycle + 1):
        picked = []
        remaining = {s: len(strata[s]) - pointer[s] for s in strata}
        for s, c in _allocate(n, remaining, weights).items():
            picked.extend(strata[s][pointer[s]:pointer[s] + c])
            pointer[s] += c
    return sorted(picked, key=lambda i: _key(seed, "rot", i))


def load_split(dataset: Dataset, split_name: str, root: str = "data") -> tuple[Question, ...]:
    """The questions of a split of ``dataset``: one of its own, or ``rot<c>`` / ``promo<k>``."""
    m_rot, m_promo, m_cal = _ROT.match(split_name), _PROMO.match(split_name), _CAL.match(split_name)
    if m_rot or m_promo or m_cal:
        ids = (rotating(dataset.name, int(m_rot.group(1)), root=root) if m_rot
               else calibration(dataset.name, int(m_cal.group(1)), root=root) if m_cal
               else promotion(dataset.name, int(m_promo.group(1)), root=root))
        want = set(ids)
        by_id = _questions(r for r in _rows(dataset.name, root) if r["id"] in want)
        return tuple(by_id[i] for i in ids)
    if split_name not in dataset.questions:
        raise ValueError(f"unknown split {split_name!r}; have {sorted(dataset.questions)} "
                         "and rot<c> / promo<k> for a dataset with a pool")
    return dataset.questions[split_name]
