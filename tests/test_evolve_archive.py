import random

import pytest

from heuresis.evolve.archive import Archive, sigmoid


def _add(arch, doc, parent, cycle=1):
    cid = arch.add_candidate(doc, parent, cycle=cycle)
    arch.admit(cid, cycle=cycle)
    return cid


def test_append_only_and_folded_rows(tmp_path):
    a = Archive(tmp_path)
    root = a.ensure_champion()["id"]
    c = _add(a, {"config": {"retrieve.k_first": 10}}, root)
    a.record_stage(c, "static", {"passed": True}, cycle=1)
    a.record_stage(c, "screen", {"passed": False}, cycle=1)
    a.set_status(c, "rejected_screen", "worse", cycle=1)
    n_lines = len(a.path.read_text().splitlines())
    r = a.get(c)
    assert r["status"] == "rejected_screen" and set(r["stages"]) == {"static", "screen"} and r["parent"] == root
    assert a.add_candidate({"config": {"retrieve.k_first": 10}}, root, cycle=2) == c  # not duplicated
    assert len(a.path.read_text().splitlines()) == n_lines
    assert a.children(root) == 1


def test_parent_selection_weights_and_determinism(tmp_path):
    a = Archive(tmp_path)
    root = a.ensure_champion()["id"]
    hi = _add(a, {"config": {"retrieve.k_first": 10}}, root)
    lo = _add(a, {"config": {"retrieve.k_first": 11}}, root)
    a.set_score(hi, 0.95, cycle=1)
    a.set_score(lo, 0.05, cycle=1)
    picks = [a.select_parent(random.Random(i)) for i in range(400)]
    assert picks.count(hi) > picks.count(lo) * 5
    assert picks == [a.select_parent(random.Random(i)) for i in range(400)]
    # many children lower the weight
    for i in range(6):
        _add(a, {"config": {"retrieve.k_first": 12, "retrieve.search_k": 2 + i}}, hi)
    p2 = [a.select_parent(random.Random(i)) for i in range(400)]
    assert p2.count(hi) < picks.count(hi)
    assert sigmoid(0) == 0.5


def test_unadmitted_is_never_a_parent(tmp_path):
    a = Archive(tmp_path)
    root = a.ensure_champion()["id"]
    c = a.add_candidate({"config": {"retrieve.k_first": 10}}, root, cycle=1)  # not admitted
    assert all(a.select_parent(random.Random(i)) != c for i in range(50))


def test_champion_history_and_rollback(tmp_path):
    a = Archive(tmp_path)
    root = a.ensure_champion()["id"]
    c1 = _add(a, {"config": {"retrieve.k_first": 10}}, root)
    c2 = _add(a, {"config": {"retrieve.k_first": 12}}, c1)
    a.set_champion(c1, reason="t", cycle=1)
    a.set_champion(c2, reason="t", cycle=2)
    ch = a.champion()
    assert ch["id"] == c2 and [h["id"] for h in ch["history"]] == [root, c1]
    out = a.rollback(reason="test", cycle=3)
    assert out["to"] == c1 and a.champion()["id"] == c1 and a.champion()["rollbacks"][0]["from"] == c2
    assert a.get(c2)["status"] == "rolled_back"
    a.rollback(to=root, reason="again", cycle=3)
    assert a.champion()["id"] == root
    with pytest.raises(ValueError):
        a.rollback(cycle=3)


def test_state_roundtrip_and_no_tmp_left(tmp_path):
    a = Archive(tmp_path)
    s = a.state()
    s["promotions"] = 2
    a.save_state(s)
    assert Archive(tmp_path).state()["promotions"] == 2
    assert not list(tmp_path.glob("*.tmp"))
