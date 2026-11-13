"""Paired statistics, the online promotion schedule and the guard rails of the improvement loop.

Everything here is a pure function of rows (dicts with ``qid``, ``status``, ``outcome``, ``usd``,
``tainted``...) and the loop's constants. Per-question score is the penalised score with a wrong
answer costing ``t / (1 - t)`` (``locked.scoring.penalty_score``); the comparison is always paired
by question id with the champion.

* ``paired``: the paired difference and its standard error, the one-sided paired sign-flip p-value
  and the one-sided bootstrap lower bound. The p-value reuses ``bench.stats.paired_permutation_test``
  (two-sided on the absolute mean). Under the null the sign-flip distribution of the mean is
  symmetric, so for an observed mean above zero ``P(S >= obs) = P(S <= -obs)`` and the two-sided
  value is exactly twice the one-sided one; hence ``p_one = p_two / 2``. For a mean at or below zero
  the one-sided value for "better than the champion" is not small and is reported as 1.0.
* ``alpha_t``: the online false-discovery schedule ``alpha_t = alpha * gamma_t * (promotions + 1)``
  with ``gamma_t = 6 / (pi^2 t^2)``, which sums to 1 over t.
* ``guard_rails``: the checks of design (f) with their margins.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from ..bench import stats
from ..locked.scoring import penalty_score

DEFAULT_PENALTY_T = 0.75


def row_score(row: Mapping, t: float = DEFAULT_PENALTY_T) -> float:
    return penalty_score(str(row.get("outcome", "wrong")), t)


def normalised_score(mean_score: float, t: float = DEFAULT_PENALTY_T) -> float:
    """The mean penalised score mapped to [0, 1] (parent selection works on this scale)."""
    w = t / (1 - t)
    return (mean_score + w) / (1 + w)


def metrics(rows: Sequence[Mapping], t: float = DEFAULT_PENALTY_T) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0, "score": 0.0, "answered": 0, "coverage": 0.0, "error_rate": 0.0,
                "cost_per_question": 0.0, "tainted": 0}
    answered = [r for r in rows if r.get("status") == "answered"]
    wrong = [r for r in answered if r.get("outcome") == "wrong"]
    return {
        "n": n,
        "score": sum(row_score(r, t) for r in rows) / n,
        "answered": len(answered),
        "coverage": len(answered) / n,
        "error_rate": (len(wrong) / len(answered)) if answered else 0.0,
        "cost_per_question": sum(float(r.get("usd") or 0.0) for r in rows) / n,
        "tainted": sum(1 for r in answered if r.get("tainted") is True),
    }


def align(a_rows: Sequence[Mapping], b_rows: Sequence[Mapping]) -> tuple[list[Mapping], list[Mapping]]:
    """Rows of both runs for the question ids they share, in id order."""
    ia = {str(r["qid"]): r for r in a_rows}
    ib = {str(r["qid"]): r for r in b_rows}
    keys = sorted(set(ia) & set(ib))
    return [ia[k] for k in keys], [ib[k] for k in keys]


def _units(d: np.ndarray, clusters: Sequence | None) -> np.ndarray:
    if clusters is None:
        u = d
    else:
        _, inv = np.unique(np.asarray([str(c) for c in clusters]), return_inverse=True)
        u = np.bincount(inv, weights=d)
    return u[np.abs(u) > 1e-12]


def one_sided_p(a: Sequence[float], b: Sequence[float], *, iters: int = 10_000, seed: int = 0,
                clusters: Sequence | None = None) -> float:
    """One-sided paired sign-flip p-value for "mean(a - b) > 0", from the two-sided test."""
    if len(a) == 0:
        return 1.0
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if float(d.mean()) <= 1e-12:
        return 1.0
    p2 = stats.paired_permutation_test(a, b, iters=iters, seed=seed, clusters=clusters)
    m = len(_units(d, clusters))
    if 2 ** m <= iters:  # exact enumeration: P(S >= obs) = P(S <= -obs) = p2 / 2
        return min(1.0, p2 / 2.0)
    return min(1.0, (p2 * (iters + 1) / 2.0 + 0.5) / (iters + 1))  # hits / 2 + 1 over iters + 1


def paired(cand_rows: Sequence[Mapping], champ_rows: Sequence[Mapping], *,
           t: float = DEFAULT_PENALTY_T, level: float = 0.90, iters: int = 2000,
           perm_iters: int = 10_000, seed: int = 0, use_clusters: bool = True) -> dict:
    """The candidate against the champion on the questions both answered."""
    ca, cb = align(cand_rows, champ_rows)
    n = len(ca)
    if n == 0:
        return {"n": 0, "mean_candidate": 0.0, "mean_champion": 0.0, "diff": 0.0, "se": None,
                "p_one_sided": 1.0, "lower_bound": None, "level": level}
    a = [row_score(r, t) for r in ca]
    b = [row_score(r, t) for r in cb]
    d = np.asarray(a) - np.asarray(b)
    se = float(d.std(ddof=1) / math.sqrt(n)) if n > 1 else None
    clusters = None
    if use_clusters and all(r.get("cluster") for r in ca):
        clusters = [r["cluster"] for r in ca]
    _, lo, _hi = stats.paired_bootstrap_ci(a, b, iters=iters, alpha=2 * (1 - level), seed=seed,
                                           clusters=clusters)
    return {"n": n, "mean_candidate": float(np.mean(a)), "mean_champion": float(np.mean(b)),
            "diff": float(d.mean()), "se": se,
            "p_one_sided": one_sided_p(a, b, iters=perm_iters, seed=seed, clusters=clusters),
            "lower_bound": None if lo != lo else float(lo), "level": level}


# ---------------------------------------------------------------------------------------------
# The online schedule
# ---------------------------------------------------------------------------------------------


def gamma(t: int) -> float:
    """``6 / (pi^2 t^2)``: positive, decreasing, sums to 1 over t = 1, 2, ..."""
    if t < 1:
        raise ValueError("t starts at 1")
    return 6.0 / (math.pi ** 2 * t * t)


def alpha_t(alpha: float, t: int, promotions_so_far: int) -> float:
    """Level of the t-th promotion test ever made: ``alpha * gamma_t * (promotions so far + 1)``."""
    return alpha * gamma(t) * (promotions_so_far + 1)


def winners_curse_note(n: int, n_candidates: int, se: float | None = None) -> dict:
    """Selection inflates the dev score of the best of ``n_candidates``; only the promotion-set
    result is recorded as the gain. ``approx_inflation`` is ``se * sqrt(2 ln m)``, a rough upper
    figure for the best of m noise-only candidates (design (f) quotes about 0.06 at n = 300, m = 20)."""
    approx = None
    if se and n_candidates > 1:
        approx = float(se * math.sqrt(2 * math.log(n_candidates)))
    return {"note": "dev scores of selected candidates are biased upward; the gain recorded for a "
                    "promoted candidate is its promotion-set difference only",
            "n": n, "candidates": n_candidates, "approx_inflation": approx}


# ---------------------------------------------------------------------------------------------
# Guard rails and decisions
# ---------------------------------------------------------------------------------------------


def _rail(ok: bool, detail: str) -> dict:
    return {"ok": bool(ok), "detail": detail}


def guard_rails(cand_rows: Sequence[Mapping], champ_rows: Sequence[Mapping],
                cand_anchor_rows: Sequence[Mapping], champ_anchor_rows: Sequence[Mapping],
                cfg: Mapping[str, Any], *, t: float = DEFAULT_PENALTY_T, min_pairs: int = 5,
                seed: int = 0) -> dict[str, dict]:
    """The guard rails of design (f), each ``{"ok", "detail"}``. ``cfg`` is the ``guard_rails``
    section of ``config.json``. Rows must exclude canaries."""
    rails: dict[str, dict] = {}
    ca, cb = align(cand_rows, champ_rows)
    mc, mb = metrics(ca, t), metrics(cb, t)
    # 1. no answer with a fabricated or out-of-force citation on any anchor question
    bad = sum(1 for r in cand_anchor_rows if r.get("status") == "answered" and r.get("tainted") is True)
    rails["no_tainted_anchor"] = _rail(bad == 0, f"{bad} tainted answer(s) on {len(cand_anchor_rows)} "
                                                 f"anchor rows")
    # 2. error rate among answered not higher by more than the margin
    m_err = float(cfg.get("error_rate_points", 0.02))
    d_err = mc["error_rate"] - mb["error_rate"]
    rails["error_rate"] = _rail(d_err <= m_err + 1e-12,
                                f"error rate {mc['error_rate']:.3f} against {mb['error_rate']:.3f}")
    # 3. coverage not lower by more than the margin
    m_cov = float(cfg.get("coverage_points", 0.05))
    d_cov = mb["coverage"] - mc["coverage"]
    rails["coverage"] = _rail(d_cov <= m_cov + 1e-12,
                              f"coverage {mc['coverage']:.3f} against {mb['coverage']:.3f}")
    # 4. cost per question not higher by more than the ratio
    ratio = float(cfg.get("cost_ratio", 1.25))
    cc, cch = mc["cost_per_question"], mb["cost_per_question"]
    rails["cost"] = _rail(cch <= 0 or cc <= ratio * cch + 1e-12,
                          f"cost per question {cc:.5f} against {cch:.5f}")
    # 5. no anchor group lower than the champion's by more than k standard errors
    k = float(cfg.get("anchor_score_se", 2.0))
    groups: dict[tuple, list] = {}
    for r in cand_anchor_rows:
        groups.setdefault((r.get("dataset", ""), r.get("split", "")), []).append(r)
    worst = None
    failed = []
    for key, rs in sorted(groups.items()):
        champ_g = [r for r in champ_anchor_rows if (r.get("dataset", ""), r.get("split", "")) == key]
        p = paired(rs, champ_g, t=t, iters=200, perm_iters=200, seed=seed)
        if p["n"] < min_pairs or p["se"] is None:
            continue
        z = p["diff"] / p["se"] if p["se"] > 0 else (0.0 if p["diff"] == 0 else math.copysign(math.inf, p["diff"]))
        worst = z if worst is None else min(worst, z)
        if z < -k:
            failed.append(f"{key[0]}/{key[1]}")
    rails["anchor_score"] = _rail(not failed, ("lower on " + ", ".join(failed)) if failed else
                                  ("no anchor rows" if not groups else
                                   f"worst anchor difference {worst:.1f} standard errors"
                                   if worst is not None else "too few anchor pairs"))
    return rails


def rails_ok(rails: Mapping[str, Mapping]) -> bool:
    return all(r["ok"] for r in rails.values())


def decide_screen(p: Mapping, *, reject_se: float = 2.0, min_pairs: int = 5) -> tuple[bool, str]:
    """A filter, not a decision: out only when clearly worse (difference below zero by more than
    ``reject_se`` standard errors)."""
    if p["n"] < min_pairs or p["se"] is None:
        return True, "too few pairs to reject"
    if p["diff"] < 0 and (p["se"] == 0 or p["diff"] < -reject_se * p["se"]):
        return False, f"clearly worse than the champion ({p['diff']:.3f}, se {p['se']:.3f})"
    return True, "not clearly worse"


def decide_dev(p: Mapping, rails: Mapping[str, Mapping], *, min_pairs: int = 5) -> tuple[bool, str]:
    if p["n"] < min_pairs:
        return False, "too few pairs"
    if not p["diff"] > 0:
        return False, f"paired difference {p['diff']:.3f} is not positive"
    lb = p["lower_bound"]
    if lb is None or not lb > 0:
        return False, f"{int(p['level'] * 100)}% one-sided lower bound {lb} is not above zero"
    failed = [n for n, r in rails.items() if not r["ok"]]
    if failed:
        return False, "guard rail(s) failed: " + ", ".join(failed)
    return True, "positive difference, lower bound above zero, guard rails hold"


def decide_promotion(p: Mapping, level: float, rails: Mapping[str, Mapping], *,
                     min_pairs: int = 5) -> tuple[bool, str]:
    if p["n"] < min_pairs:
        return False, "too few pairs"
    if not p["diff"] > 0:
        return False, f"paired difference {p['diff']:.3f} is not positive"
    if not p["p_one_sided"] <= level:
        return False, f"one-sided p {p['p_one_sided']:.4f} is above the level {level:.5f}"
    failed = [n for n, r in rails.items() if not r["ok"]]
    if failed:
        return False, "guard rail(s) failed: " + ", ".join(failed)
    return True, f"one-sided p {p['p_one_sided']:.4f} at level {level:.5f}, guard rails hold"
