import hashlib
import json

import pytest

from heuresis.bench import datasets, splits
from heuresis.bench.types import Dataset

N = 400
PARAMS = {"n_dev": 10, "n_test": 40, "n_sealed": 20, "seed": 20261111, "stratum": "answerable"}
N_DEV2 = 10


def _rows(n=None):
    n = n or N
    return [{"id": f"q{i:04d}", "text": f"synthetic question {i}", "answers": [f"a{i}"] if i % 5 else [],
             "answerable": bool(i % 5), "as_of": None, "gold_units": [], "cluster": f"c{i % 17}", "kind": ""}
            for i in range(n)]


def make_root(tmp_path, name="pooled", n=None):
    cdir = tmp_path / "data" / "corpora" / name
    cdir.mkdir(parents=True)
    rows = _rows(n)
    (cdir / "questions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (cdir / "MANIFEST.json").write_text(json.dumps({
        "splits": {"params": PARAMS}, "dev2": {"requested": N_DEV2}}))
    return str(tmp_path / "data"), rows


def dataset_for(root, rows, name="pooled"):
    sp = datasets._compute_splits(rows, "answerable", 10, 40, 20, PARAMS["seed"], N_DEV2)
    return Dataset(name=name, corpus_dir="", questions=sp, licence="t", corpus_tokens=1, meta={}), sp


def test_held_out_names_and_the_registration_check(tmp_path):
    for s in ("test", "sealed", "temporal_test", "promo0", "promo12"):
        assert splits.is_held_out(s)
    for s in ("dev", "dev2", "temporal", "rot0", "rot7"):
        assert not splits.is_held_out(s)
    ids = ["b", "a", "c"]
    good = tmp_path / "REG.md"
    good.write_text("split test: " + datasets.ids_hash(ids) + "\n")
    assert splits.registration_ok(ids, str(good)) is None
    assert splits.registration_ok({"question_ids": ids}, str(good)) is None
    assert "not written" in splits.registration_ok(["a", "b", "c"], str(good))  # order matters
    assert "cannot read" in splits.registration_ok(ids, str(tmp_path / "missing.md"))
    assert splits.registration_ok([], str(good))
    assert splits._ids_sha(ids) == hashlib.sha256(b"b\na\nc").hexdigest() == datasets.ids_hash(ids)


def test_the_pool_is_what_no_split_holds(tmp_path):
    root, rows = make_root(tmp_path)
    ds, sp = dataset_for(root, rows)
    used = {q.id for qs in sp.values() for q in qs}
    pool = splits.pool_ids("pooled", root)
    assert len(used) == 80 and len(pool) == N - 80
    assert not used & set(pool) and used | set(pool) == {r["id"] for r in rows}


def test_a_corpus_whose_questions_all_carry_a_split_has_no_pool(tmp_path):
    cdir = tmp_path / "data" / "corpora" / "legal"
    cdir.mkdir(parents=True)
    rows = [{**r, "split": "dev" if i < 5 else "test"} for i, r in enumerate(_rows()[:20])]
    (cdir / "questions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (cdir / "MANIFEST.json").write_text("{}")
    assert splits.pool_ids("legal", str(tmp_path / "data")) == []
    with pytest.raises(ValueError, match="0 questions remain"):
        splits.rotating("legal", 0, root=str(tmp_path / "data"))
    with pytest.raises(ValueError, match="0 ids left"):
        splits.promotion("legal", 0, root=str(tmp_path / "data"))


KW = dict(promo_n=40, promo_blocks=2, cal_n=40, cal_blocks=1)


def test_rotating_cycles_are_disjoint_from_each_other_and_from_every_promotion_block(tmp_path):
    root, rows = make_root(tmp_path)
    pool = set(splits.pool_ids("pooled", root))
    promos = [splits.promotion("pooled", k, 40, root=root) for k in range(2)]
    assert all(len(p) == 40 for p in promos) and not set(promos[0]) & set(promos[1])
    cycles = [splits.rotating("pooled", c, 20, root=root, **KW) for c in range(10)]  # (320 - 80 - 40) / 20
    seen: set[str] = set()
    for c in cycles:
        assert len(c) == 20 and len(set(c)) == 20 and set(c) <= pool
        assert not seen & set(c)
        seen |= set(c)
    cal = splits.calibration("pooled", 0, 40, root=root, promo_n=40, promo_blocks=2, cal_blocks=1)
    assert len(cal) == 40 and not set(cal) & seen and all(not set(cal) & set(p) for p in promos)
    for p in promos:
        assert not seen & set(p)
    assert seen | set(promos[0]) | set(promos[1]) | set(cal) == pool  # nothing is lost
    assert splits.rotating("pooled", 3, 20, root=root, **KW) == cycles[3]  # a pure function
    with pytest.raises(ValueError, match=r"0 questions remain.*cycle 10"):
        splits.rotating("pooled", 10, 20, root=root, **KW)


def test_order_is_by_hash_and_seed_changes_it(tmp_path):
    root, _ = make_root(tmp_path)
    c = splits.rotating("pooled", 0, 20, root=root, **KW)
    key = lambda i: hashlib.sha256(f"{splits.SEED}:rot:{i}".encode()).hexdigest()
    assert c == sorted(c, key=key)
    assert splits.rotating("pooled", 0, 20, root=root, seed=7, **KW) != c
    p = splits.promotion("pooled", 0, 40, root=root)
    pool_order = sorted(splits.pool_ids("pooled", root),
                        key=lambda i: hashlib.sha256(f"{splits.SEED}:promo:{i}".encode()).hexdigest())
    assert p == pool_order[:40] and splits.promotion("pooled", 1, 40, root=root) == pool_order[40:80]


def test_rotating_keeps_the_answerable_share_of_the_pool(tmp_path):
    root, rows = make_root(tmp_path)
    ans = {r["id"]: r["answerable"] for r in rows}
    rest = [i for i in splits.pool_ids("pooled", root)]
    share = sum(not ans[i] for i in rest) / len(rest)
    for c in range(4):
        d = splits.rotating("pooled", c, 20, root=root, **KW)
        assert abs(sum(not ans[i] for i in d) - 20 * share) <= 2


def test_exclude_and_too_small_pools(tmp_path):
    root, _ = make_root(tmp_path)
    first = splits.rotating("pooled", 0, 20, root=root, **KW)
    again = splits.rotating("pooled", 0, 20, root=root, exclude=first, **KW)
    assert not set(first) & set(again)
    with pytest.raises(ValueError, match=r"\d+ ids left for promotion block 1, 400 are needed"):
        splits.promotion("pooled", 1, 400, root=root)
    with pytest.raises(ValueError, match="not reserved"):
        splits.promotion("pooled", 2, 40, root=root)
    with pytest.raises(ValueError, match="remain in the pool"):
        splits.rotating("pooled", 0, 300, root=root, **KW)


def test_load_split_resolves_own_splits_and_rotating_and_promotion_names(tmp_path):
    root, rows = make_root(tmp_path, n=2000)  # the defaults (promotion 2 x 300, calibration 400, draws of 100) need a bigger pool
    ds, sp = dataset_for(root, rows)
    assert splits.load_split(ds, "dev", root) == sp["dev"]
    rot = splits.load_split(ds, "rot2", root)
    assert [q.id for q in rot] == splits.rotating("pooled", 2, root=root) and len(rot) == 100
    assert rot[0].text.startswith("synthetic question") and rot[0].id.startswith("q")
    promo = splits.load_split(ds, "promo1", root)
    assert [q.id for q in promo] == splits.promotion("pooled", 1, root=root) and len(promo) == 300
    assert not {q.id for q in rot} & {q.id for q in promo}
    assert not {q.id for q in rot} & {q.id for qs in sp.values() for q in qs}
    cal = splits.load_split(ds, "cal0", root)
    assert len(cal) == 400 and not splits.is_held_out("cal0")
    assert not {q.id for q in cal} & ({q.id for q in rot} | {q.id for q in promo})
    with pytest.raises(ValueError, match="remain in the pool"):
        splits.load_split(ds, "rot9", root)  # 1920 - 600 - 400 = 920: nine cycles of 100, then 20 are left
    with pytest.raises(ValueError, match="not reserved"):
        splits.calibration("pooled", 1, root=root)
    with pytest.raises(ValueError, match="unknown split"):
        splits.load_split(ds, "nonsense", root)
