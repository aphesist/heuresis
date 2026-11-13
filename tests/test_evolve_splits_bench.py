"""BenchSplits over a synthetic pool-bearing dataset: calibration and rotating draws come from bench.splits."""
import pytest

from heuresis.bench import splits as bs
from heuresis.evolve.splits import BenchSplits, SplitExhausted
from test_bench_splits import dataset_for, make_root


@pytest.fixture
def src(tmp_path):
    root, rows = make_root(tmp_path, n=2000)  # 1920 in the pool: 2 x 300 promotion, 400 calibration, 920 rotating
    ds, sp = dataset_for(root, rows)
    s = BenchSplits(root, ["pooled"], {"pooled": ["dev"]})
    s._cache["pooled"] = ds
    return s, root, sp


def test_calibration_is_bench_splits_calibration(src):
    s, root, _ = src
    cal = s.calibration("pooled", 0, 50)
    assert [q.id for q in cal] == bs.calibration("pooled", 0, root=root)[:50]
    assert all(q.split == "cal0" and q.dataset == "pooled" for q in cal)
    with pytest.raises(SplitExhausted):
        s.calibration("pooled", 1, 50)       # only CAL_RESERVED blocks exist
    with pytest.raises(SplitExhausted):
        s.calibration("pooled", 0, 401)


def test_rotating_draws_never_touch_calibration_or_promotion(src):
    s, root, sp = src
    cal = {q.id for q in s.calibration("pooled", 0, 400)}
    promo = {q.id for b in range(bs.PROMO_RESERVED) for q in s.promotion("pooled", b, 300)}
    assert len(cal) == 400 and len(promo) == 600 and not cal & promo
    own = {q.id for qs in sp.values() for q in qs}
    seen: set[str] = set()
    for c in range(1, 10):                    # nine draws of 100 fit in 920
        ids = {q.id for q in s.rotating("pooled", c, 100)}
        assert len(ids) == 100 and not ids & (cal | promo | own | seen)
        seen |= ids
    with pytest.raises(SplitExhausted):
        s.rotating("pooled", 10, 100)


def test_capacity_states_the_real_limits(src):
    s, _, _ = src
    cap = s.capacity("pooled", 10)
    assert cap == {"pool": 1920, "promotion_queries": 20, "rotating_cycles": 9}
    with pytest.raises(SplitExhausted):
        s.promotion("pooled", bs.PROMO_RESERVED, 150)   # no third block
