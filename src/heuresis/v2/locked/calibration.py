"""Risk-controlled confidence threshold: exact Clopper-Pearson bound, fixed-sequence walk."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


def _cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), 0 < p < 1, summed in log space."""
    lp, lq = math.log(p), math.log1p(-p)
    base = math.lgamma(n + 1)
    total = 0.0
    for i in range(k + 1):
        total += math.exp(base - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
    return min(1.0, total)


def clopper_pearson_upper(errors: int, n: int, delta: float) -> float:
    """One-sided exact upper confidence bound, at level ``1 - delta``, of an error rate with
    ``errors`` errors in ``n`` trials: the ``p`` with ``P(X <= errors | p) = delta``."""
    if n <= 0:
        return 1.0
    if errors >= n:
        return 1.0
    if errors < 0:
        raise ValueError("errors must be >= 0")
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if mid <= 0.0 or mid >= 1.0:
            break
        if _cdf(errors, n, mid) > delta:
            lo = mid
        else:
            hi = mid
    return hi


@dataclass(frozen=True)
class Calibration:
    tau: float | None
    alpha: float
    delta: float
    n_questions: int
    n_answered: int
    errors: int
    upper: float
    coverage: float
    surface_hash: str
    dataset: str
    split: str
    label: str
    created: str


def fit(confidences: Sequence[float], wrong: Sequence[bool], *, alpha: float, delta: float,
        grid: Sequence[float], min_answers: int) -> dict:
    """Fixed-sequence walk from the strictest threshold to the loosest. Returns ``tau`` (the
    loosest accepted threshold, or ``None``), ``n_answered``, ``errors``, ``upper`` at that
    threshold and a ``table`` with one row per grid step."""
    if len(confidences) != len(wrong):
        raise ValueError("confidences and wrong must have the same length")
    rows = list(zip(confidences, (bool(w) for w in wrong)))
    table: list[dict] = []
    best = None
    for tau in sorted(grid, reverse=True):
        sel = [w for c, w in rows if c >= tau]
        n, errs = len(sel), sum(sel)
        row = {"tau": tau, "n_answered": n, "errors": errs, "upper": None, "accepted": None}
        if n < min_answers:
            table.append(row)
            continue
        up = clopper_pearson_upper(errs, n, delta)
        row["upper"], row["accepted"] = up, up <= alpha
        table.append(row)
        if up > alpha:
            break
        best = row
    if best is None:
        return {"tau": None, "n_answered": 0, "errors": 0, "upper": 1.0, "table": table}
    return {"tau": best["tau"], "n_answered": best["n_answered"], "errors": best["errors"],
            "upper": best["upper"], "table": table}


def save(cal: Calibration, path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(cal), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load(path) -> Calibration:
    return Calibration(**json.loads(Path(path).read_text(encoding="utf-8")))


def find(directory, surface_hash: str, dataset: str | None = None) -> Calibration | None:
    """The newest calibration file in ``directory`` whose surface hash (and dataset, if given)
    matches; ``None`` when there is none."""
    d = Path(directory)
    if not d.is_dir():
        return None
    best: tuple[str, str, Calibration] | None = None
    for f in sorted(d.glob("*.json")):
        try:
            cal = load(f)
        except (OSError, ValueError, TypeError):
            continue
        if cal.surface_hash != surface_hash or (dataset is not None and cal.dataset != dataset):
            continue
        key = (cal.created, f.name)
        if best is None or key > best[:2]:
            best = (cal.created, f.name, cal)
    return best[2] if best else None
