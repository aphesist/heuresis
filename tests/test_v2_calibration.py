import math

import pytest

from heuresis.v2.locked import calibration as C

GRID = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]


def test_known_bounds():
    assert 0.049 < C.clopper_pearson_upper(0, 45, 0.1) < 0.05
    assert 0.049 < C.clopper_pearson_upper(1, 77, 0.1) < 0.05
    assert 0.049 < C.clopper_pearson_upper(0, 59, 0.05) < 0.05
    # closed form for zero errors
    assert C.clopper_pearson_upper(0, 100, 0.05) == pytest.approx(1 - 0.05 ** (1 / 100), abs=1e-9)


def test_edges_and_monotonicity():
    assert C.clopper_pearson_upper(5, 5, 0.1) == 1.0
    assert C.clopper_pearson_upper(0, 0, 0.1) == 1.0
    ups = [C.clopper_pearson_upper(e, 200, 0.1) for e in range(0, 20)]
    assert ups == sorted(ups)
    with pytest.raises(ValueError):
        C.clopper_pearson_upper(-1, 10, 0.1)


def test_large_n_is_accurate():
    # zero errors: closed form; one-sided bound must exceed the point estimate
    assert C.clopper_pearson_upper(0, 2000, 0.1) == pytest.approx(1 - 0.1 ** (1 / 2000), abs=1e-9)
    up = C.clopper_pearson_upper(100, 2000, 0.1)
    assert 0.05 < up < 0.06
    # the defining equation holds
    assert C._cdf(100, 2000, up) == pytest.approx(0.1, abs=1e-6)


def rows(n_ok, n_bad, conf):
    return [conf] * (n_ok + n_bad), [False] * n_ok + [True] * n_bad


def test_fit_walk_accepts_loosest_certified():
    conf, wrong = [], []
    for c, ok, bad in ((0.95, 50, 0), (0.75, 50, 0), (0.55, 50, 30)):
        c_, w_ = rows(ok, bad, c)
        conf += c_
        wrong += w_
    r = C.fit(conf, wrong, alpha=0.05, delta=0.1, grid=GRID, min_answers=45)
    assert r["tau"] == 0.6 and r["n_answered"] == 100 and r["errors"] == 0
    assert r["upper"] <= 0.05
    by_tau = {row["tau"]: row for row in r["table"]}
    assert by_tau[0.6]["accepted"] is True and by_tau[0.5]["accepted"] is False
    assert 0.4 not in by_tau  # the walk stopped at the first failure


def test_fit_none_when_nothing_certified():
    conf, wrong = rows(30, 20, 0.95)
    r = C.fit(conf, wrong, alpha=0.05, delta=0.1, grid=GRID, min_answers=45)
    assert r["tau"] is None and r["n_answered"] == 0 and r["upper"] == 1.0


def test_fit_min_answers_skips_step_but_continues():
    c1, w1 = rows(20, 0, 0.95)  # too few at 0.9: skipped
    c2, w2 = rows(40, 0, 0.55)
    r = C.fit(c1 + c2, w1 + w2, alpha=0.05, delta=0.1, grid=GRID, min_answers=45)
    assert r["tau"] == 0.3 and r["n_answered"] == 60
    assert [row["accepted"] for row in r["table"][:4]] == [None] * 4  # 0.9 .. 0.6
    assert r["table"][0]["upper"] is None
    r = C.fit(c1, w1, alpha=0.05, delta=0.1, grid=GRID, min_answers=45)
    assert r["tau"] is None


def test_fit_grid_order_irrelevant_and_length_check():
    conf, wrong = rows(60, 0, 0.8)
    a = C.fit(conf, wrong, alpha=0.05, delta=0.1, grid=GRID, min_answers=45)
    b = C.fit(conf, wrong, alpha=0.05, delta=0.1, grid=GRID[::-1], min_answers=45)
    assert a["tau"] == b["tau"] == 0.3
    with pytest.raises(ValueError):
        C.fit([0.5], [], alpha=0.05, delta=0.1, grid=GRID, min_answers=1)


def cal(**kw):
    base = dict(tau=0.7, alpha=0.05, delta=0.1, n_questions=200, n_answered=120, errors=1,
                upper=0.04, coverage=0.6, surface_hash="h1", dataset="ds", split="dev",
                label="containment", created="2026-01-01T00:00:00")
    base.update(kw)
    return C.Calibration(**base)


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "sub" / "c.json"
    C.save(cal(), p)
    assert C.load(p) == cal()
    C.save(cal(tau=None), p)
    assert C.load(p).tau is None


def test_find(tmp_path):
    assert C.find(tmp_path / "nothing", "h1") is None
    assert C.find(tmp_path, "h1") is None
    C.save(cal(created="2026-01-01"), tmp_path / "a.json")
    C.save(cal(created="2026-02-01", tau=0.6), tmp_path / "b.json")
    C.save(cal(surface_hash="other", created="2027-01-01"), tmp_path / "c.json")
    C.save(cal(dataset="ds2", created="2026-03-01", tau=0.5), tmp_path / "d.json")
    (tmp_path / "bad.json").write_text("{oops")
    (tmp_path / "odd.json").write_text('{"x": 1}')
    assert C.find(tmp_path, "h1").tau == 0.5  # newest across datasets
    assert C.find(tmp_path, "h1", "ds").tau == 0.6
    assert C.find(tmp_path, "h1", "ds2").tau == 0.5
    assert C.find(tmp_path, "h1", "zzz") is None
    assert C.find(tmp_path, "nomatch") is None
