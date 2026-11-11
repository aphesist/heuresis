"""Statistics for paired comparisons: standard library and NumPy only.

The Wilson interval, the exact McNemar test and the Holm correction follow the
same definitions as the statistics module of the sibling project contraprova
(same owner, Apache-2.0), re-implemented here; the bootstrap and the power
calculation are new.
"""
from __future__ import annotations

import math
from statistics import NormalDist
from typing import Sequence

import numpy as np

__all__ = [
    "wilson_interval", "mcnemar_exact", "discordant", "bootstrap_ratio_ci",
    "bootstrap_mean_ci", "paired_bootstrap_ci", "holm", "min_detectable_diff",
    "paired_permutation_test", "paired_ratio_diff_ci", "pareto_front",
]


def _z(alpha: float) -> float:
    return NormalDist().inv_cdf(1 - alpha / 2)


def wilson_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a proportion (default 95%). n=0 gives (0, 1)."""
    if n <= 0:
        return 0.0, 1.0
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    z = _z(alpha)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo = 0.0 if successes == 0 else max(0.0, centre - half)
    hi = 1.0 if successes == n else min(1.0, centre + half)
    return lo, hi


def mcnemar_exact(a_only: int, b_only: int) -> float:
    """Exact two-sided McNemar p from the discordant counts (binomial, p=0.5)."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def discordant(a: Sequence[bool], b: Sequence[bool]) -> tuple[int, int]:
    """(a right and b wrong, b right and a wrong) over paired outcomes."""
    if len(a) != len(b):
        raise ValueError("paired sequences must have equal length")
    return (sum(1 for x, y in zip(a, b) if x and not y),
            sum(1 for x, y in zip(a, b) if y and not x))


def bootstrap_ratio_ci(
    num: Sequence[float], den: Sequence[float], *, iters: int = 10_000,
    alpha: float = 0.05, seed: int = 0, clusters: Sequence | None = None,
) -> tuple[float, float, float]:
    """Ratio of sums ``sum(num)/sum(den)`` with a percentile bootstrap interval.

    Units (or clusters, when given) are resampled with replacement. Resamples whose
    denominator is zero are dropped. Returns (estimate, low, high); NaN where
    undefined.
    """
    num_a = np.asarray(num, dtype=float)
    den_a = np.asarray(den, dtype=float)
    if num_a.shape != den_a.shape:
        raise ValueError("num and den must have the same length")
    n = len(num_a)
    if n == 0:
        return math.nan, math.nan, math.nan
    if clusters is None:
        sn, sd = num_a, den_a
    else:
        if len(clusters) != n:
            raise ValueError("clusters must have one label per unit")
        _, inv = np.unique(np.asarray([str(c) for c in clusters]), return_inverse=True)
        sn = np.bincount(inv, weights=num_a)
        sd = np.bincount(inv, weights=den_a)
    est = float(num_a.sum() / den_a.sum()) if den_a.sum() != 0 else math.nan
    m = len(sn)
    rng = np.random.default_rng(seed)
    chunk = max(1, 2_000_000 // m)
    out = []
    done = 0
    while done < iters:
        c = min(chunk, iters - done)
        idx = rng.integers(0, m, size=(c, m))
        with np.errstate(divide="ignore", invalid="ignore"):
            out.append(sn[idx].sum(axis=1) / sd[idx].sum(axis=1))
        done += c
    vals = np.concatenate(out)
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return est, math.nan, math.nan
    lo, hi = np.quantile(vals, [alpha / 2, 1 - alpha / 2])
    return est, float(lo), float(hi)


def bootstrap_mean_ci(
    values: Sequence[float], *, iters: int = 10_000, alpha: float = 0.05,
    seed: int = 0, clusters: Sequence | None = None,
) -> tuple[float, float, float]:
    """Mean with a percentile bootstrap interval: (mean, low, high)."""
    if len(values) == 0:
        return math.nan, math.nan, math.nan
    return bootstrap_ratio_ci(values, np.ones(len(values)), iters=iters, alpha=alpha,
                              seed=seed, clusters=clusters)


def paired_bootstrap_ci(
    a: Sequence[float], b: Sequence[float], *, iters: int = 10_000, alpha: float = 0.05,
    seed: int = 0, clusters: Sequence | None = None,
) -> tuple[float, float, float]:
    """Mean of ``a - b`` per question with a percentile bootstrap interval."""
    if len(a) != len(b):
        raise ValueError("paired sequences must have equal length")
    diffs = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    return bootstrap_mean_ci(diffs, iters=iters, alpha=alpha, seed=seed, clusters=clusters)


def paired_permutation_test(
    a: Sequence[float], b: Sequence[float], *, iters: int = 10_000, seed: int = 0,
    clusters: Sequence | None = None,
) -> float:
    """Two-sided paired sign-flip permutation test on the mean of ``a - b``.

    Under the null the sign of each per-question difference is exchangeable. The
    statistic is the absolute mean difference; the p-value is the share of sign
    assignments whose statistic is at least as large as the observed one.

    With ``clusters``, the differences are summed within each cluster and the signs
    are flipped per cluster, so questions of one cluster always move together.
    Units whose difference is zero cannot change the statistic and are dropped.

    When the remaining units number ``m`` and ``2**m <= iters`` every sign
    assignment is enumerated and the p-value is exact. Otherwise ``iters`` random
    assignments are drawn (seeded) and the p-value is ``(hits + 1) / (iters + 1)``,
    which is never zero. No difference at all gives 1.0.
    """
    if len(a) != len(b):
        raise ValueError("paired sequences must have equal length")
    if len(a) == 0:
        return math.nan
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if clusters is None:
        units = d
    else:
        if len(clusters) != len(d):
            raise ValueError("clusters must have one label per unit")
        _, inv = np.unique(np.asarray([str(c) for c in clusters]), return_inverse=True)
        units = np.bincount(inv, weights=d)
    units = units[np.abs(units) > 1e-12]
    m = len(units)
    if m == 0:
        return 1.0
    obs = abs(float(units.sum()))
    tol = 1e-9 * max(1.0, obs)
    if 2**m <= iters:
        codes = np.arange(2**m, dtype=np.int64)
        bits = (codes[:, None] >> np.arange(m, dtype=np.int64)[None, :]) & 1
        sums = np.abs(((1 - 2 * bits) * units[None, :]).sum(axis=1))
        return float(np.count_nonzero(sums >= obs - tol) / 2**m)
    rng = np.random.default_rng(seed)
    hits = 0
    done = 0
    chunk = max(1, 2_000_000 // m)
    while done < iters:
        c = min(chunk, iters - done)
        signs = rng.integers(0, 2, size=(c, m)) * 2 - 1
        hits += int(np.count_nonzero(np.abs((signs * units).sum(axis=1)) >= obs - tol))
        done += c
    return (hits + 1) / (iters + 1)


def paired_ratio_diff_ci(
    num_a: Sequence[float], den_a: Sequence[float], num_b: Sequence[float],
    den_b: Sequence[float], *, iters: int = 10_000, alpha: float = 0.05, seed: int = 0,
    clusters: Sequence | None = None,
) -> tuple[float, float, float]:
    """Difference of two ratios of sums, ``sum(num_a)/sum(den_a) - sum(num_b)/sum(den_b)``,
    with a percentile bootstrap interval.

    The four sequences are paired by position: each resample draws questions (or
    clusters) once and uses them for both ratios, so the pairing is kept. Resamples
    in which either denominator is zero are dropped. Returns (estimate, low, high);
    NaN where undefined. Used for the difference in cost per correct answer.
    """
    arrs = [np.asarray(x, dtype=float) for x in (num_a, den_a, num_b, den_b)]
    n = len(arrs[0])
    if any(len(x) != n for x in arrs):
        raise ValueError("all four sequences must have the same length")
    if n == 0:
        return math.nan, math.nan, math.nan
    if clusters is None:
        sums = arrs
    else:
        if len(clusters) != n:
            raise ValueError("clusters must have one label per unit")
        _, inv = np.unique(np.asarray([str(c) for c in clusters]), return_inverse=True)
        sums = [np.bincount(inv, weights=x) for x in arrs]
    na, da, nb, db = sums
    est = math.nan
    if arrs[1].sum() != 0 and arrs[3].sum() != 0:
        est = float(arrs[0].sum() / arrs[1].sum() - arrs[2].sum() / arrs[3].sum())
    m = len(na)
    rng = np.random.default_rng(seed)
    chunk = max(1, 2_000_000 // m)
    out = []
    done = 0
    while done < iters:
        c = min(chunk, iters - done)
        idx = rng.integers(0, m, size=(c, m))
        with np.errstate(divide="ignore", invalid="ignore"):
            out.append(na[idx].sum(axis=1) / da[idx].sum(axis=1)
                       - nb[idx].sum(axis=1) / db[idx].sum(axis=1))
        done += c
    vals = np.concatenate(out)
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return est, math.nan, math.nan
    lo, hi = np.quantile(vals, [alpha / 2, 1 - alpha / 2])
    return est, float(lo), float(hi)


def pareto_front(points: Sequence[tuple[float, float]]) -> list[bool]:
    """For ``(cost, quality)`` points, True where no other point is at least as good on
    both (lower cost, higher quality) and strictly better on one."""
    out = []
    for i, (c, q) in enumerate(points):
        dominated = any(
            j != i and c2 <= c and q2 >= q and (c2 < c or q2 > q)
            for j, (c2, q2) in enumerate(points)
        )
        out.append(not dominated)
    return out


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, in input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def required_n(delta: float, discordance: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Pairs needed to detect a difference ``delta`` in two paired proportions when a
    share ``discordance`` of pairs disagree (normal approximation to McNemar)."""
    if not 0 < delta <= discordance <= 1:
        raise ValueError("need 0 < delta <= discordance <= 1")
    za, zb = _z(alpha), NormalDist().inv_cdf(power)
    return (za * math.sqrt(discordance) + zb * math.sqrt(discordance - delta * delta)) ** 2 / delta**2


def min_detectable_diff(
    n: int, discordance: float, alpha: float = 0.05, power: float = 0.8
) -> float:
    """Smallest paired difference in proportions detectable with ``n`` pairs, a
    discordance rate and the given alpha and power. NaN if none is detectable."""
    if n <= 0 or not 0 < discordance <= 1:
        return math.nan
    if required_n(discordance, discordance, alpha, power) > n:
        return math.nan
    lo, hi = 1e-9, discordance  # required_n decreases in delta
    for _ in range(100):
        mid = (lo + hi) / 2
        if required_n(mid, discordance, alpha, power) > n:
            lo = mid
        else:
            hi = mid
    return hi
