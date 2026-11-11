import pytest

from heuresis.locked.scoring import (
    aurc, best_over_golds, citation_precision_recall, exact_match, normalize_answer,
    outcome, penalised_score, penalty_score, risk_coverage, selective_accuracy_at, token_f1,
)


def test_normalize():
    assert normalize_answer("The  Quick, Brown Fox!") == "quick brown fox"
    assert normalize_answer("São Paulo") == "são paulo"
    assert normalize_answer("São Paulo", fold_accents=True) == "sao paulo"


def test_em_f1():
    assert exact_match("The Cat.", "cat") == 1.0
    assert exact_match("Ação", "acao") == 0.0
    assert exact_match("Ação", "acao", fold_accents=True) == 1.0
    assert token_f1("x b c", "b c d") == pytest.approx(2 / 3)
    assert token_f1("x", "y") == 0.0
    assert token_f1("", "") == 1.0 and token_f1("", "zebra") == 0.0
    assert best_over_golds(token_f1, "b c", ["a", "b c d", "b c"]) == 1.0
    assert best_over_golds(exact_match, "z", []) == 0.0


def test_penalised():
    assert [penalised_score(o) for o in ("correct", "abstained", "wrong")] == [1, 0, -1]
    assert penalty_score("wrong", 0.5) == -1.0
    assert penalty_score("wrong", 0.75) == pytest.approx(-3.0)
    assert penalty_score("wrong", 0.0) == 0.0
    assert penalty_score("correct", 0.9) == 1.0 and penalty_score("abstained", 0.9) == 0.0
    with pytest.raises(ValueError):
        penalty_score("wrong", 1.0)
    with pytest.raises(ValueError):
        penalised_score("maybe")


def test_risk_coverage_and_aurc():
    conf = [0.6, 0.9, 0.7, 0.8]
    ok = [True, True, False, True]
    curve = risk_coverage(conf, ok)
    assert curve == [(0.25, 0.0), (0.5, 0.0), (0.75, pytest.approx(1 / 3)), (1.0, 0.25)] or [
        (c, pytest.approx(r)) for c, r in curve
    ] == [(0.25, 0.0), (0.5, 0.0), (0.75, pytest.approx(1 / 3)), (1.0, pytest.approx(0.25))]
    assert aurc(conf, ok) == pytest.approx((1 / 3 + 0.25) / 4)
    assert aurc([], []) == 0.0
    assert aurc([0.9, 0.1], [True, True]) == 0.0


def test_selective_accuracy():
    conf = [0.9, 0.8, 0.7, 0.6]
    ok = [True, True, False, True]
    assert selective_accuracy_at(conf, ok, 0.5) == 1.0
    assert selective_accuracy_at(conf, ok, 0.75) == pytest.approx(2 / 3)
    assert selective_accuracy_at(conf, ok, 1.0) == 0.75


def test_citations():
    assert citation_precision_recall(["a", "b"], ["a", "c"]) == (0.5, 0.5)
    assert citation_precision_recall([], ["a"]) == (0.0, 0.0)
    assert citation_precision_recall([], []) == (1.0, 1.0)
    assert citation_precision_recall(["a"], []) == (0.0, 1.0)


def test_outcome():
    assert outcome("answered", True, True) == "correct"
    assert outcome("partial", True, True) == "correct"
    assert outcome("answered", False, True) == "wrong"
    assert outcome("abstained", None, True) == "abstained"
    assert outcome("abstained", None, False) == "correct"
    assert outcome("answered", False, False) == "wrong"
    assert outcome("answered", None, False) == "wrong"
