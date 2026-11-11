import math

import numpy as np
import pytest

from heuresis.bench import stats


def test_wilson_8_of_10():
    lo, hi = stats.wilson_interval(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
    assert stats.wilson_interval(0, 10)[0] == 0.0 and stats.wilson_interval(10, 10)[1] == 1.0
    assert stats.wilson_interval(0, 0) == (0.0, 1.0)


def test_mcnemar_exact():
    assert stats.mcnemar_exact(1, 5) == pytest.approx(14 / 64)
    assert stats.mcnemar_exact(0, 5) == pytest.approx(2 / 32)
    assert stats.mcnemar_exact(3, 3) == 1.0 and stats.mcnemar_exact(0, 0) == 1.0
    assert stats.discordant([1, 1, 0, 0], [1, 0, 1, 0]) == (1, 1)


def test_holm():
    assert stats.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert stats.holm([0.5]) == [0.5]
    assert stats.holm([0.4, 0.4]) == pytest.approx([0.8, 0.8])


def test_bootstrap_mean_and_pair():
    vals = [1.0] * 30 + [0.0] * 10
    m, lo, hi = stats.bootstrap_mean_ci(vals, iters=2000, seed=1)
    assert m == pytest.approx(0.75) and lo < 0.75 < hi
    assert stats.bootstrap_mean_ci(vals, iters=2000, seed=1) == (m, lo, hi)  # seeded
    d, dlo, dhi = stats.paired_bootstrap_ci([1] * 20, [0] * 20, iters=500)
    assert (d, dlo, dhi) == (1.0, 1.0, 1.0)


def test_cluster_bootstrap_is_wider_with_correlated_clusters():
    vals = [1.0] * 20 + [0.0] * 20
    clusters = ["a"] * 20 + ["b"] * 20
    _, lo, hi = stats.bootstrap_mean_ci(vals, iters=2000, seed=0)
    _, clo, chi = stats.bootstrap_mean_ci(vals, iters=2000, seed=0, clusters=clusters)
    assert (chi - clo) > (hi - lo)
    assert clo == 0.0 and chi == 1.0


def test_ratio_bootstrap():
    cost = [1.0, 2.0, 3.0, 2.0]
    ok = [1.0, 0.0, 1.0, 1.0]
    est, lo, hi = stats.bootstrap_ratio_ci(cost, ok, iters=2000)
    assert est == pytest.approx(8 / 3) and lo <= est <= hi
    assert math.isnan(stats.bootstrap_ratio_ci([1.0], [0.0], iters=50)[0])
    assert all(math.isnan(x) for x in stats.bootstrap_ratio_ci([], [])[:1])


def test_min_detectable_diff_is_consistent():
    d = stats.min_detectable_diff(400, 0.2)
    assert 0.0 < d < 0.2
    assert stats.required_n(d, 0.2) == pytest.approx(400, rel=1e-3)
    assert stats.min_detectable_diff(1600, 0.2) < d  # more data, finer
    assert stats.min_detectable_diff(400, 0.4) > d     # more discordance, coarser
    assert math.isnan(stats.min_detectable_diff(3, 0.1))


def test_permutation_test_exact_hand_values():
    # all four differences are +1: only the all-plus and all-minus assignments reach |sum| = 4
    assert stats.paired_permutation_test([1, 1, 1, 1], [0, 0, 0, 0]) == pytest.approx(2 / 16)
    # differences 2, 1, -1: sums over sign assignments are 4, 2, 2, 0, 0, -2, -2, -4
    assert stats.paired_permutation_test([2, 1, 0], [0, 0, 1]) == pytest.approx(6 / 8)
    # symmetric in its arguments (two-sided) and blind to zero differences
    assert stats.paired_permutation_test([0, 0, 1, 1, 1, 1], [0, 0, 0, 0, 0, 0]) == pytest.approx(2 / 16)
    assert stats.paired_permutation_test([0, 0, 0, 0], [1, 1, 1, 1]) == pytest.approx(2 / 16)
    assert stats.paired_permutation_test([3, 3], [3, 3]) == 1.0
    assert math.isnan(stats.paired_permutation_test([], []))
    with pytest.raises(ValueError):
        stats.paired_permutation_test([1], [1, 2])


def test_permutation_test_clusters_flip_together():
    a, b = [1, 1, 1, 1], [0, 0, 0, 0]
    # two clusters with sums 2 and 2: assignments give |sum| 4, 0, 0, 4 -> p = 2/4
    assert stats.paired_permutation_test(a, b, clusters=["x", "x", "y", "y"]) == pytest.approx(0.5)
    assert stats.paired_permutation_test(a, b, clusters=["x", "x", "y", "y"]) > \
        stats.paired_permutation_test(a, b)


def test_permutation_test_monte_carlo_is_seeded_and_close():
    a = [1.0] * 60 + [0.0] * 20
    b = [0.0] * 80
    p1 = stats.paired_permutation_test(a, b, iters=4000, seed=3)
    assert p1 == stats.paired_permutation_test(a, b, iters=4000, seed=3)
    assert 0 < p1 <= 1 / 1000 + 1e-9  # 60 equal-sign differences: truth is 2 / 2**60, floor is 1 / (iters + 1)
    assert p1 == pytest.approx(1 / 4001)
    # a null-looking sample is not significant
    rng = np.random.default_rng(0)
    x = rng.integers(0, 2, 200).astype(float)
    y = rng.integers(0, 2, 200).astype(float)
    assert stats.paired_permutation_test(x, y, iters=4000, seed=1) > 0.05


def test_paired_ratio_diff():
    est, lo, hi = stats.paired_ratio_diff_ci([1, 1], [1, 1], [2, 2], [1, 1], iters=200)
    assert (est, lo, hi) == (-1.0, -1.0, -1.0)
    # pairs are kept together: question 1 costs 1 vs 4, question 2 costs 3 vs 2; both correct for both
    est, lo, hi = stats.paired_ratio_diff_ci([1, 3], [1, 1], [4, 2], [1, 1], iters=2000, seed=2)
    assert est == pytest.approx(2.0 - 3.0) and lo <= est <= hi
    assert math.isnan(stats.paired_ratio_diff_ci([1], [0], [1], [1], iters=10)[0])
    assert math.isnan(stats.paired_ratio_diff_ci([], [], [], [])[0])
    with pytest.raises(ValueError):
        stats.paired_ratio_diff_ci([1], [1], [1, 2], [1, 1])


def test_pareto_front():
    # (cost, quality): c is dominated by a (cheaper and better); ties are not dominated
    assert stats.pareto_front([(1, 5), (3, 5), (2, 7), (2, 7)]) == [True, False, True, True]
    assert stats.pareto_front([]) == []
