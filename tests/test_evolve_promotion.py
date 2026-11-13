import itertools
import math

import numpy as np

from heuresis.evolve import promotion as P
from heuresis.evolve.splits import PromotionBook


def rows(outcomes, **extra):
    return [{"qid": f"q{i:03d}", "status": "abstained" if o == "abstained" else "answered", "outcome": o,
             "usd": 0.01, "tainted": None, **extra} for i, o in enumerate(outcomes)]


def test_row_score_and_normalisation():
    assert P.row_score({"outcome": "wrong"}, 0.75) == -3.0 and P.row_score({"outcome": "correct"}) == 1.0
    assert P.normalised_score(-3.0) == 0.0 and P.normalised_score(1.0) == 1.0


def brute_one_sided(d):
    d = [x for x in d if abs(x) > 1e-12]
    obs = sum(d)
    hits = 0
    for signs in itertools.product((1, -1), repeat=len(d)):
        if sum(s * x for s, x in zip(signs, d)) >= obs - 1e-9:
            hits += 1
    return hits / 2 ** len(d)


def test_one_sided_p_is_half_the_two_sided_and_matches_brute_force():
    rng = np.random.default_rng(0)
    for _ in range(5):
        d = rng.integers(-3, 5, size=9).astype(float)
        a, b = list(d), [0.0] * 9
        p = P.one_sided_p(a, b, iters=10_000)
        if d.mean() > 0:
            assert math.isclose(p, brute_one_sided(d), abs_tol=1e-12)
        else:
            assert p == 1.0
    assert P.one_sided_p([1.0] * 8, [0.0] * 8, iters=10_000) == 1 / 256
    assert P.one_sided_p([0.0] * 5, [0.0] * 5) == 1.0 and P.one_sided_p([], []) == 1.0


def test_paired_detects_a_real_gain_and_not_noise():
    cand = rows(["correct"] * 20 + ["wrong"] * 5)
    champ = rows(["wrong"] * 10 + ["correct"] * 10 + ["wrong"] * 5)
    p = P.paired(cand, champ, iters=500, perm_iters=5000, seed=1)
    assert p["n"] == 25 and p["diff"] > 0 and p["p_one_sided"] < 0.01 and p["lower_bound"] > 0
    q = P.paired(champ, champ, iters=200)
    assert q["diff"] == 0 and q["p_one_sided"] == 1.0
    assert P.paired([], [])["n"] == 0


def test_alignment_by_question_id():
    a = rows(["correct", "wrong", "correct"])
    b = rows(["wrong", "wrong"])
    ca, cb = P.align(a, b)
    assert [r["qid"] for r in ca] == ["q000", "q001"] == [r["qid"] for r in cb]


def test_alpha_schedule():
    alpha = 0.05
    levels = [P.alpha_t(alpha, t, 0) for t in range(1, 2001)]
    assert all(x > 0 for x in levels)
    assert all(levels[i] > levels[i + 1] for i in range(len(levels) - 1))   # decreasing in t
    assert sum(levels) <= alpha + 1e-12                                     # at most alpha with no promotion
    assert math.isclose(sum(P.gamma(t) for t in range(1, 200_000)), 1.0, abs_tol=1e-4)
    assert P.alpha_t(alpha, 3, 2) == 3 * P.alpha_t(alpha, 3, 0)             # more promotions, more level
    assert P.alpha_t(alpha, 1, 0) < alpha


def test_guard_rails():
    cfg = {"error_rate_points": 0.02, "coverage_points": 0.05, "cost_ratio": 1.25, "anchor_score_se": 2.0}
    base = rows(["correct"] * 10 + ["wrong"] * 2)
    same = rows(["correct"] * 10 + ["wrong"] * 2)
    r = P.guard_rails(same, base, [], [], cfg)
    assert P.rails_ok(r)
    worse = rows(["correct"] * 8 + ["wrong"] * 4)
    assert not P.guard_rails(worse, base, [], [], cfg)["error_rate"]["ok"]
    abst = rows(["correct"] * 5 + ["abstained"] * 7)
    assert not P.guard_rails(abst, base, [], [], cfg)["coverage"]["ok"]
    dear = rows(["correct"] * 10 + ["wrong"] * 2, usd=0.02)
    assert not P.guard_rails(dear, base, [], [], cfg)["cost"]["ok"]
    taint = rows(["correct"] * 10, tainted=True)
    assert not P.guard_rails(same, base, taint, taint, cfg)["no_tainted_anchor"]["ok"]
    a_good = [{**r, "dataset": "d", "split": "s"} for r in rows(["correct"] * 20)]
    a_bad = [{**r, "dataset": "d", "split": "s"} for r in rows(["wrong", "correct"] * 10)]
    assert not P.guard_rails(same, base, a_bad, a_good, cfg)["anchor_score"]["ok"]
    assert P.guard_rails(same, base, a_good, a_bad, cfg)["anchor_score"]["ok"]


def test_decisions():
    p = {"n": 30, "diff": 0.5, "se": 0.1, "lower_bound": 0.2, "level": 0.9, "p_one_sided": 0.001}
    ok_rails = {"x": {"ok": True, "detail": ""}}
    assert P.decide_screen(p)[0] and P.decide_dev(p, ok_rails)[0] and P.decide_promotion(p, 0.01, ok_rails)[0]
    assert not P.decide_screen({**p, "diff": -0.5})[0]
    assert P.decide_screen({**p, "diff": -0.1})[0]            # below zero but not by 2 se
    assert not P.decide_dev({**p, "lower_bound": -0.1}, ok_rails)[0]
    assert not P.decide_dev(p, {"x": {"ok": False, "detail": ""}})[0]
    assert not P.decide_promotion({**p, "p_one_sided": 0.2}, 0.01, ok_rails)[0]


def test_winners_curse_note():
    n = P.winners_curse_note(300, 20, 0.03)
    assert n["approx_inflation"] > 0.05 and "promotion-set" in n["note"]


def test_promotion_book_retires_a_block_after_its_budget():
    state = {}
    book = PromotionBook(state, 3)
    assert [book.consume("d") for _ in range(7)] == [0, 0, 0, 1, 1, 1, 2]
    assert book.block("d") == 2 and book.queries("d") == 1 and state["promotion"]["d"]["retired"] == [0, 1]
