"""Which datasets the loop evolves on, the cycle's rotating draw, the promotion block, the anchors.

A thin layer over ``heuresis.bench.splits`` (the real pools; imported only when ``BenchSplits`` is
used) plus ``PoolSplits``, a synthetic or packaged pool with the same behaviour (used by the tests
and by the offline fixture). Everything is deterministic given the seed.

* Rotating dev: cycle ``c`` takes the next ``n`` ids of the pool ordered by hash, from the front;
  draws of different cycles never overlap.
* Promotion block ``b``: ``n`` ids from the back of the same ordering; the blocks reserved at the
  back are never reachable by a rotating draw. A block is retired after ``promotion_query_budget``
  promotion queries (``PromotionBook``) and the next one is used.
* Anchors: fixed dev sets already seen in design, used for guard rails only. A held-out split name
  (``bench.splits.is_held_out``) is refused here.

Nothing here prints a question; the evaluator never returns rows of the promotion tier.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..bench.types import Dataset, Question

FIXTURE_DIR = Path(__file__).resolve().parent / "fixture"


class SplitExhausted(Exception):
    """No fresh draw or promotion block is left."""


@dataclass(frozen=True)
class PoolQuestion(Question):
    """A benchmark question that knows its dataset and the split it was drawn from."""

    dataset: str = ""
    split: str = ""


def to_pool(q: Question, dataset: str, split: str) -> PoolQuestion:
    return PoolQuestion(id=q.id, text=q.text, answers=q.answers, answerable=q.answerable,
                        as_of=q.as_of, gold_units=q.gold_units, cluster=q.cluster, kind=q.kind,
                        dataset=dataset, split=split)


def _key(seed: int, tag: str, qid: str) -> str:
    return hashlib.sha256(f"{seed}:{tag}:{qid}".encode("utf-8")).hexdigest()


def assert_disjoint(*groups: Iterable[Question]) -> None:
    seen: set[tuple[str, str]] = set()
    for g in groups:
        ids = {(getattr(q, "dataset", ""), q.id) for q in g}
        if ids & seen:
            raise AssertionError("draws overlap")
        seen |= ids


class SplitSource:
    """What the evaluator needs from the data side."""

    def rotating_names(self) -> list[str]:  # pragma: no cover - interface
        raise NotImplementedError

    def dataset(self, name: str) -> Dataset:  # pragma: no cover
        raise NotImplementedError

    def rotating(self, name: str, cycle: int, n: int) -> list[PoolQuestion]:  # pragma: no cover
        raise NotImplementedError

    def promotion(self, name: str, block: int, n: int) -> list[PoolQuestion]:  # pragma: no cover
        raise NotImplementedError

    def anchors(self) -> list[PoolQuestion]:  # pragma: no cover
        raise NotImplementedError

    def calibration(self, name: str, block: int, n: int) -> list[PoolQuestion]:  # pragma: no cover
        raise NotImplementedError


class PoolSplits(SplitSource):
    """Pools held in memory: ``{name: (dataset, pool_questions, anchor_questions)}``."""

    def __init__(self, specs: Mapping[str, tuple[Dataset, Sequence[Question], Sequence[Question]]],
                 *, seed: int = 0, promo_n: int = 300, promo_blocks: int = 2,
                 cal_n: int = 0, cal_blocks: int = 0):
        self.specs = dict(specs)
        self.seed = int(seed)
        self.promo_n = int(promo_n)
        self.promo_blocks = int(promo_blocks)
        self.cal_n = int(cal_n)
        self.cal_blocks = int(cal_blocks)
        self._order = {name: sorted(pool, key=lambda q: _key(self.seed, "pool", q.id))
                       for name, (_, pool, _) in self.specs.items()}

    def rotating_names(self) -> list[str]:
        return list(self.specs)

    def dataset(self, name: str) -> Dataset:
        return self.specs[name][0]

    def rotating(self, name: str, cycle: int, n: int) -> list[PoolQuestion]:
        order = self._order[name]
        usable = len(order) - self.promo_blocks * self.promo_n - self.cal_blocks * self.cal_n
        if cycle < 1 or cycle * n > usable:
            raise SplitExhausted(f"{name}: no rotating draw {cycle} of {n} left "
                                 f"({max(0, usable)} usable questions)")
        return [to_pool(q, name, f"rot{cycle}") for q in order[(cycle - 1) * n:cycle * n]]

    def promotion(self, name: str, block: int, n: int) -> list[PoolQuestion]:
        order = self._order[name]
        if block < 0 or block >= self.promo_blocks or len(order) < self.promo_blocks * n:
            raise SplitExhausted(f"{name}: promotion block {block} does not exist")
        hi = len(order) - block * self.promo_n
        return [to_pool(q, name, f"promo{block}") for q in order[hi - self.promo_n:hi][:n]]

    def calibration(self, name: str, block: int, n: int) -> list[PoolQuestion]:
        """Calibration block ``block``: carved behind the promotion blocks, before the rotating draws."""
        order = self._order[name]
        if block < 0 or block >= self.cal_blocks:
            raise SplitExhausted(f"{name}: calibration block {block} does not exist")
        hi = len(order) - self.promo_blocks * self.promo_n - block * self.cal_n
        return [to_pool(q, name, f"cal{block}") for q in order[hi - self.cal_n:hi][:n]]

    def anchors(self) -> list[PoolQuestion]:
        out: list[PoolQuestion] = []
        for name, (_, _, anchors) in self.specs.items():
            out += [to_pool(q, name, "anchor") for q in anchors]
        return out


class BenchSplits(SplitSource):
    """The real pools through ``heuresis.bench.splits`` (data under ``root``). Used by paid runs only."""

    def __init__(self, root: str = "data", datasets: Sequence[str] = ("multihoprag", "hoh"),
                 anchors: Mapping[str, Sequence[str]] | None = None, *, rotating_n: int = 100,
                 promo_n: int = 300):
        self.root = root
        self.names = list(datasets)
        self.anchor_cfg = {k: list(v) for k, v in (anchors or {}).items()}
        self._cache: dict[str, Dataset] = {}
        self.rotating_n = rotating_n
        self.promo_n = promo_n

    def rotating_names(self) -> list[str]:
        return list(self.names)

    def dataset(self, name: str) -> Dataset:
        if name not in self._cache:
            from ..bench import datasets as ds_mod
            self._cache[name] = ds_mod.load(name, self.root)
        return self._cache[name]

    def _load(self, name: str, split: str) -> tuple[Question, ...]:
        from ..bench import splits as bs
        try:
            return bs.load_split(self.dataset(name), split, self.root)
        except ValueError as e:
            raise SplitExhausted(str(e)) from None

    def rotating(self, name: str, cycle: int, n: int) -> list[PoolQuestion]:
        qs = self._load(name, f"rot{cycle - 1}")
        if n > len(qs):
            raise SplitExhausted(f"{name}: a rotating draw has {len(qs)} questions, {n} asked")
        return [to_pool(q, name, f"rot{cycle}") for q in qs[:n]]

    def promotion(self, name: str, block: int, n: int) -> list[PoolQuestion]:
        qs = self._load(name, f"promo{block}")
        if n > len(qs):
            raise SplitExhausted(f"{name}: a promotion block has {len(qs)} questions, {n} asked")
        return [to_pool(q, name, f"promo{block}") for q in qs[:n]]

    def calibration(self, name: str, block: int, n: int) -> list[PoolQuestion]:
        """Calibration block ``block`` (``cal<k>``): ``bench.splits.calibration`` through ``load_split``. The
        ids are never recomputed here; ``bench.splits.rotating`` and ``promotion`` already keep them apart."""
        qs = self._load(name, f"cal{block}")
        if n > len(qs):
            raise SplitExhausted(f"{name}: a calibration block has {len(qs)} questions, {n} asked")
        return [to_pool(q, name, f"cal{block}") for q in qs[:n]]

    def capacity(self, name: str, promotion_query_budget: int) -> dict[str, int]:
        """What the pool of ``name`` can serve, from ``bench.splits`` constants and ``pool_ids``: promotion
        queries (``PROMO_RESERVED`` blocks of ``promotion_query_budget`` queries each) and rotating cycles
        (the pool less the promotion and calibration blocks, in draws of 100)."""
        from ..bench import splits as bs
        pool = len(bs.pool_ids(name, self.root))
        rest = pool - bs.PROMO_RESERVED * bs.PROMO_N - bs.CAL_RESERVED * bs.CAL_N
        return {"pool": pool, "promotion_queries": bs.PROMO_RESERVED * int(promotion_query_budget),
                "rotating_cycles": max(0, rest // 100)}

    def anchors(self) -> list[PoolQuestion]:
        from ..bench import splits as bs
        out: list[PoolQuestion] = []
        for name, names in self.anchor_cfg.items():
            for s in names:
                if bs.is_held_out(s) or s.startswith(("rot", "promo", "cal")):
                    raise ValueError(f"{name}/{s} is not an anchor split (held-out or drawn)")
                out += [to_pool(q, name, f"anchor:{s}") for q in self._load(name, s)]
        return out


class PromotionBook:
    """Which promotion block is current per dataset and how many queries it has served. The counters
    live in the loop's ``state.json`` (``state["promotion"]``); a block is retired after ``budget``
    queries and the next block is used."""

    def __init__(self, state: dict, budget: int):
        self.state = state.setdefault("promotion", {})
        self.budget = int(budget)

    def block(self, dataset: str) -> int:
        return int(self.state.get(dataset, {}).get("block", 0))

    def queries(self, dataset: str) -> int:
        return int(self.state.get(dataset, {}).get("queries", 0))

    def consume(self, dataset: str) -> int:
        """Count one query on the current block; returns the block that served it."""
        e = self.state.setdefault(dataset, {"block": 0, "queries": 0, "retired": []})
        served = int(e["block"])
        e["queries"] = int(e["queries"]) + 1
        if e["queries"] >= self.budget:
            e.setdefault("retired", []).append(served)
            e["block"], e["queries"] = served + 1, 0
        return served


# ---------------------------------------------------------------------------------------------
# The packaged fixture: an invented corpus and questions with a pool
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureData:
    dataset: Dataset
    pool: tuple[Question, ...]
    anchors: tuple[Question, ...]
    smoke: tuple[Question, ...]


def load_fixture(directory: str | Path | None = None, name: str = "fixture") -> FixtureData:
    d = Path(directory) if directory is not None else FIXTURE_DIR
    groups: dict[str, list[Question]] = {"pool": [], "anchor": [], "smoke": []}
    with open(d / "questions.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            groups[r.get("split", "pool")].append(Question(
                id=r["id"], text=r["text"], answers=tuple(r.get("answers", ())),
                answerable=bool(r.get("answerable", True)), as_of=r.get("as_of"),
                gold_units=tuple(r.get("gold_units", ())), cluster=r.get("cluster", ""),
                kind=r.get("kind", "")))
    ds = Dataset(name=name, corpus_dir=str(d), licence="invented content, no licence needed",
                 corpus_tokens=2000, meta={},
                 questions={k: tuple(v) for k, v in groups.items()})
    return FixtureData(ds, tuple(groups["pool"]), tuple(groups["anchor"]), tuple(groups["smoke"]))


def fixture_splits(*, seed: int = 0, promo_n: int = 8, promo_blocks: int = 2, cal_n: int = 6,
                   cal_blocks: int = 1) -> PoolSplits:
    fx = load_fixture()
    return PoolSplits({fx.dataset.name: (fx.dataset, fx.pool, fx.anchors)}, seed=seed, promo_n=promo_n,
                      promo_blocks=promo_blocks, cal_n=cal_n, cal_blocks=cal_blocks)
