from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from heuresis.model import AsOf, Edge, Event, Scope, Source, Unit
from heuresis.store import Store, fts_query

ALL = Scope()


def ev(id, unit, op, d, text=None, rec="", **kw):
    return Event(id=id, unit_id=unit, op=op, date=d, text=text, recorded_at=rec or d, **kw)


def make(events, units=None, sources=None, edges=()):
    s = Store(":memory:")
    units = units or sorted({e.unit_id for e in events})
    s.add(
        sources=sources or [Source("src")],
        units=[Unit(u, "src", title=f"title {u}") if isinstance(u, str) else u for u in units],
        events=events,
        edges=edges,
    )
    s.rebuild()
    return s


def at(d, rec=None):
    return AsOf(valid=d, recorded=rec)


# ---------------------------------------------------------------------------
# replay
# ---------------------------------------------------------------------------


def test_create_replace_repeal_restore():
    s = make([
        ev("e1", "u", "create", "2020-01-01", "one"),
        ev("e2", "u", "replace", "2021-01-01", "two"),
        ev("e3", "u", "repeal", "2022-01-01"),
        ev("e4", "u", "restore", "2023-01-01"),
        ev("e5", "u", "repeal", "2024-01-01"),
        ev("e6", "u", "restore", "2025-01-01", "three"),
    ])
    vs = s.versions("u")
    assert [(v.seq, v.text, v.valid_from, v.valid_to) for v in vs] == [
        (0, "one", "2020-01-01", "2021-01-01"),
        (1, "two", "2021-01-01", "2022-01-01"),
        (2, "two", "2023-01-01", "2024-01-01"),  # restored without text: last text
        (3, "three", "2025-01-01", None),
    ]
    assert s.text_at("u", at("2019-12-31")) is None
    assert s.text_at("u", at("2020-06-01")).text == "one"
    assert s.text_at("u", at("2022-06-01")) is None
    assert s.text_at("u", at("2023-06-01")).text == "two"
    assert s.text_at("u", at("2030-01-01")).text == "three"
    assert s.versions("nope") == []


def test_half_open_interval_edges():
    s = make([
        ev("e1", "u", "create", "2020-01-01", "old"),
        ev("e2", "u", "replace", "2021-01-01", "new"),
        ev("e3", "u", "repeal", "2022-01-01"),
    ])
    assert s.text_at("u", at("2020-01-01")).text == "old"  # inclusive start
    assert s.text_at("u", at("2020-12-31")).text == "old"
    assert s.text_at("u", at("2021-01-01")).text == "new"  # exclusive end of old
    assert s.text_at("u", at("2021-12-31")).text == "new"
    assert s.text_at("u", at("2022-01-01")) is None
    for d, want in [("2020-12-31", "old"), ("2021-01-01", "new")]:
        got = s.lexical("old new", at(d), ALL, 10)
        assert [p.text for p in got] == [want]
    assert s.lexical("old new", at("2022-01-01"), ALL, 10) == []


def test_replay_is_order_independent_and_deterministic():
    events = [
        ev("e1", "u", "create", "2020-01-01", "a"),
        ev("e2", "u", "replace", "2021-01-01", "b"),
        ev("e3", "u", "replace", "2022-01-01", "c"),
    ]
    a = make(events).versions("u")
    b = make(list(reversed(events))).versions("u")
    assert a == b


@pytest.mark.parametrize(
    "events,needle",
    [
        ([ev("bad", "u", "replace", "2020-01-01", "x")], "'bad'"),
        ([ev("bad", "u", "explode", "2020-01-01", "x")], "unknown op"),
        ([ev("c", "u", "create", "2020-01-01", "x"), ev("bad", "u", "restore", "2021-01-01")],
         "'bad'"),
        ([ev("bad", "u", "restore", "2021-01-01")], "nothing to restore"),
        ([ev("c", "u", "create", "2020-01-01", "x"), ev("bad", "u", "create", "2021-01-01", "y")],
         "'bad'"),
        ([ev("c", "u", "create", "2020-01-01", "x"), ev("r", "u", "repeal", "2021-01-01"),
          ev("bad", "u", "replace", "2022-01-01", "y")], "'bad'"),
        ([ev("bad", "u", "create", "2020-01-01")], "requires text"),
    ],
)
def test_invalid_sequences_name_the_event(events, needle):
    s = Store(":memory:")
    s.add(sources=[Source("src")], units=[Unit("u", "src")], events=events)
    with pytest.raises(ValueError) as ei:
        s.rebuild()
    assert needle in str(ei.value)
    assert "bad" in str(ei.value)


def test_same_day_create_and_replace_drops_empty_version():
    s = make([
        ev("e1", "u", "create", "2020-01-01", "a", rec="2020-01-01T00:00"),
        ev("e2", "u", "replace", "2020-01-01", "b", rec="2020-01-01T01:00"),
    ])
    assert [(v.seq, v.text) for v in s.versions("u")] == [(0, "b")]


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


def test_add_is_idempotent_and_conflicts_raise():
    e = ev("e1", "u", "create", "2020-01-01", "x")
    s = make([e], edges=[Edge("u", "u", "self")])
    before = s.stats()
    s.add(sources=[Source("src")], units=[Unit("u", "src", title="title u")], events=[e],
          edges=[Edge("u", "u", "self")])
    s.rebuild()
    assert s.stats() == before
    assert before == {"sources": 1, "units": 1, "events": 1, "versions": 1, "edges": 1}
    with pytest.raises(ValueError):
        s.add(events=[ev("e1", "u", "create", "2020-01-01", "different")])
    assert s.stats() == before


def test_failed_add_is_atomic():
    s = make([ev("e1", "u", "create", "2020-01-01", "x")])
    with pytest.raises(ValueError):
        s.add(events=[ev("new", "u", "replace", "2021-01-01", "y"),
                      ev("e1", "u", "create", "2020-01-01", "z")])
    assert s.stats()["events"] == 1


def test_queries_rebuild_lazily_after_add():
    s = make([ev("e1", "u", "create", "2020-01-01", "alpha")])
    s.add(events=[ev("e2", "u", "replace", "2021-01-01", "beta")])
    assert [p.text for p in s.lexical("beta", at("2021-06-01"), ALL, 5)] == ["beta"]


# ---------------------------------------------------------------------------
# bitemporal
# ---------------------------------------------------------------------------


def test_bitemporal_correction():
    s = make([
        ev("e1", "u", "create", "2020-01-01", "limit is 10", rec="2020-01-01"),
        ev("e2", "u", "replace", "2022-01-01", "limit is 20", rec="2022-01-01"),
        ev("e3", "u", "correct", "2020-06-01", "limit is 11", rec="2023-05-01T09:00:00"),
    ])
    old = AsOf(valid="2020-06-01", recorded="2023-04-30")
    new = AsOf(valid="2020-06-01", recorded="2023-05-01T09:00:00")
    assert s.text_at("u", old).text == "limit is 10"
    assert s.text_at("u", new).text == "limit is 11"
    assert s.text_at("u", at("2020-06-01")).text == "limit is 11"
    assert s.text_at("u", AsOf(valid="2022-06-01", recorded="2023-04-30")).text == "limit is 20"
    # same validity interval, only the text changed
    v = s.text_at("u", at("2020-06-01"))
    assert (v.valid_from, v.valid_to, v.event_id) == ("2020-01-01", "2022-01-01", "e3")
    # search sees the old text through the older recorded date
    assert [p.text for p in s.lexical("limit", old, ALL, 5)] == ["limit is 10"]
    assert [p.text for p in s.lexical("limit", at("2020-06-01"), ALL, 5)] == ["limit is 11"]
    # versions() as known then
    assert [v.text for v in s.versions("u", AsOf(recorded="2021-01-01"))] == ["limit is 10"]
    assert [v.text for v in s.versions("u", AsOf(recorded="2022-06-01"))] == [
        "limit is 10", "limit is 20"]
    # a corrected-before-recorded date-only as-of covers the whole day
    assert s.text_at("u", AsOf(valid="2020-06-01", recorded="2023-05-01")).text == "limit is 11"
    # history path with dense: vectors for old text exist only if embedded
    s2 = make([ev("e1", "u", "create", "2020-01-01", "aaa", rec="2020-01-01"),
               ev("e2", "u", "correct", "2020-01-01", "bbb", rec="2021-01-01")])
    for _u, _q, _t in s2.missing_vectors("m"):
        pass
    s2.put_vectors("m", [("u", 0, np.array([1.0, 0.0], dtype=np.float32))])
    got = s2.dense(np.array([1.0, 0.0]), "m", AsOf(valid="2020-02-01"), ALL, 3)
    assert [p.text for p in got] == ["bbb"]
    # the old text was never embedded, so the historical view finds nothing dense
    assert s2.dense(np.array([1.0, 0.0]), "m", AsOf(valid="2020-02-01", recorded="2020-06-01"),
                    ALL, 3) == []


# ---------------------------------------------------------------------------
# scope, lexical
# ---------------------------------------------------------------------------


def scoped_store():
    units = [
        Unit("a/1", "s1", kind="law", title="Alpha law"),
        Unit("a/2", "s1", kind="note", title="Alpha note"),
        Unit("b/1", "s2", kind="law", title="Beta law"),
    ]
    events = [ev(f"e{i}", u.id, "create", "2020-01-01", "tax rule applies") for i, u in
              enumerate(units)]
    return make(events, units=units, sources=[Source("s1", coverage=3), Source("s2", coverage=1)])


def test_scope_filters():
    s = scoped_store()
    ids = lambda sc: sorted(p.unit_id for p in s.lexical("tax", at("2021-01-01"), sc, 10))
    assert ids(ALL) == ["a/1", "a/2", "b/1"]
    assert ids(Scope(source_ids=("s2",))) == ["b/1"]
    assert ids(Scope(kinds=("law",))) == ["a/1", "b/1"]
    assert ids(Scope(unit_prefix="a/")) == ["a/1", "a/2"]
    assert ids(Scope(source_ids=("s1",), kinds=("law",), unit_prefix="a")) == ["a/1"]
    assert ids(Scope(source_ids=("zzz",))) == []
    vec = np.array([1.0, 0.0], dtype=np.float32)
    s.put_vectors("m", [(u, 0, vec) for u in ("a/1", "a/2", "b/1")])
    dn = lambda sc: sorted(p.unit_id for p in s.dense(vec, "m", at("2021-01-01"), sc, 10))
    assert dn(Scope(source_ids=("s2",))) == ["b/1"]
    assert dn(Scope(kinds=("note",))) == ["a/2"]
    assert dn(Scope(unit_prefix="b")) == ["b/1"]


def test_passage_fields():
    s = scoped_store()
    p = {p.unit_id: p for p in s.lexical("tax", at("2021-01-01"), ALL, 10)}
    assert p["a/1"].coverage == 3 and p["b/1"].coverage == 1
    assert p["a/1"].title == "Alpha law" and p["a/1"].source_id == "s1"
    assert p["a/1"].valid_from == "2020-01-01" and p["a/1"].valid_to is None
    assert p["a/1"].stage == "lexical" and p["a/1"].certainty == "high"
    assert s.get_source("s2").coverage == 1 and s.get_source("none") is None


def test_lexical_ranking_and_title_match():
    units = [Unit("x", "src", title="invoice"), Unit("y", "src", title="other"),
             Unit("z", "src", title="other")]
    s = make(
        [ev("1", "x", "create", "2020-01-01", "nothing here"),
         ev("2", "y", "create", "2020-01-01", "invoice invoice invoice rules"),
         ev("3", "z", "create", "2020-01-01", "unrelated words")],
        units=units,
    )
    got = s.lexical("invoice", at("2021-01-01"), ALL, 10)
    assert {p.unit_id for p in got} == {"x", "y"}  # title is indexed
    assert all(p.score > 0 for p in got)
    assert got[0].score >= got[1].score
    assert len(s.lexical("invoice", at("2021-01-01"), ALL, 1)) == 1


@pytest.mark.parametrize(
    "q",
    ['', '   ', '"', '""', "AND OR NOT", "foo*", "a:b", "(((", "NEAR(a b)", "x\"y", "-", "'", "^a",
     "\x00", "a OR", "título ção", "💥", "col:val*", "{a}"],
)
def test_fts_query_safety(q):
    s = make([ev("1", "u", "create", "2020-01-01", "alpha beta ação título")])
    got = s.lexical(q, at("2021-01-01"), ALL, 5)
    assert isinstance(got, list)
    assert fts_query(q) == "" or all(t.startswith('"') for t in fts_query(q).split(" OR "))


def test_lexical_accents_fold():
    s = make([ev("1", "u", "create", "2020-01-01", "Legislação tributária")])
    assert len(s.lexical("legislacao", at("2021-01-01"), ALL, 5)) == 1
    assert s.lexical("", at("2021-01-01"), ALL, 5) == []


# ---------------------------------------------------------------------------
# dense
# ---------------------------------------------------------------------------


def test_dense_hand_made_vectors():
    s = make([
        ev("1", "a", "create", "2020-01-01", "north"),
        ev("2", "b", "create", "2020-01-01", "east"),
        ev("3", "c", "create", "2020-01-01", "north east"),
        ev("4", "c", "replace", "2022-01-01", "north east v2"),
    ])
    assert [(u, q, t) for u, q, t in s.missing_vectors("m")] == [
        ("a", 0, "north"), ("b", 0, "east"), ("c", 0, "north east"), ("c", 1, "north east v2")]
    r2 = np.sqrt(0.5)
    s.put_vectors("m", [
        ("a", 0, np.array([1, 0], dtype=np.float32)),
        ("b", 0, np.array([0, 1], dtype=np.float32)),
        ("c", 0, np.array([r2, r2], dtype=np.float32)),
        ("c", 1, np.array([r2, -r2], dtype=np.float32)),
    ])
    assert s.missing_vectors("m") == []
    assert len(s.missing_vectors("other")) == 4
    got = s.dense(np.array([1, 0], dtype=np.float32), "m", at("2021-01-01"), ALL, 10)
    assert [(p.unit_id, p.seq) for p in got] == [("a", 0), ("c", 0), ("b", 0)]
    assert got[0].score == pytest.approx(1.0) and got[1].score == pytest.approx(r2)
    assert all(p.stage == "dense" for p in got)
    got = s.dense(np.array([1, 0], dtype=np.float32), "m", at("2023-01-01"), ALL, 2)
    assert [(p.unit_id, p.seq) for p in got] == [("a", 0), ("c", 1)]
    assert s.dense(np.array([1, 0], dtype=np.float32), "nope", at("2021-01-01"), ALL, 2) == []
    assert s.dense(np.array([1, 0, 0], dtype=np.float32), "m", at("2021-01-01"), ALL, 2) == []
    with pytest.raises(ValueError):
        s.put_vectors("m", [("zzz", 0, np.zeros(2, dtype=np.float32))])


def test_vectors_survive_rebuild_but_follow_text():
    s = make([ev("1", "a", "create", "2020-01-01", "one")])
    s.put_vectors("m", [("a", 0, np.array([1, 0], dtype=np.float32))])
    s.rebuild()
    assert s.missing_vectors("m") == []
    s.add(events=[ev("2", "a", "correct", "2020-01-01", "uno", rec="2021-01-01")])
    assert s.missing_vectors("m") == [("a", 0, "uno")]


# ---------------------------------------------------------------------------
# neighbours
# ---------------------------------------------------------------------------


def test_neighbours_respect_edge_and_version_validity():
    s = make(
        [
            ev("1", "a", "create", "2020-01-01", "source a"),
            ev("2", "b", "create", "2020-01-01", "target b v1"),
            ev("3", "b", "replace", "2022-01-01", "target b v2"),
            ev("4", "c", "create", "2020-01-01", "target c"),
            ev("5", "d", "create", "2023-01-01", "target d"),
        ],
        edges=[
            Edge("a", "b", "cites"),
            Edge("a", "c", "amends", valid_from="2021-01-01", valid_to="2023-01-01"),
            Edge("a", "d", "cites"),
        ],
    )
    n = lambda d, **kw: sorted((p.unit_id, p.text) for p in s.neighbours(["a"], at(d), **kw))
    assert n("2020-06-01") == [("b", "target b v1")]  # c edge not yet valid, d not yet in force
    assert n("2021-06-01") == [("b", "target b v1"), ("c", "target c")]
    assert n("2022-06-01") == [("b", "target b v2"), ("c", "target c")]
    assert n("2023-01-01") == [("b", "target b v2"), ("d", "target d")]  # edge to c ended
    assert n("2021-06-01", types=("amends",)) == [("c", "target c")]
    assert n("2021-06-01", types=("nope",)) == []
    assert s.neighbours([], at("2021-01-01")) == []
    assert s.neighbours(["b"], at("2021-01-01")) == []
    assert all(p.stage == "expand" for p in s.neighbours(["a"], at("2022-06-01")))


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


def test_file_store_round_trip(tmp_path):
    path = str(tmp_path / "s.db")
    s = make([ev("1", "u", "create", "2020-01-01", "persisted text")])
    s.close()
    s = Store(path)
    s.add(sources=[Source("src")], units=[Unit("u", "src", title="t")],
          events=[ev("1", "u", "create", "2020-01-01", "persisted text")])
    s.rebuild()
    s.close()
    s = Store(path)
    assert [p.text for p in s.lexical("persisted", at("2021-01-01"), ALL, 3)] == ["persisted text"]
    s.close()


# ---------------------------------------------------------------------------
# the central invariant, as a property
# ---------------------------------------------------------------------------

BASE = date(2024, 1, 1)
WORDS = ["alpha", "beta", "gamma", "delta", "eps"]


def iso(n):
    return (BASE + timedelta(days=n)).isoformat()


@st.composite
def histories(draw):
    """Valid event histories for a few units. Base events sit on distinct days and are
    recorded at their date; corrections are recorded later and may target any past
    version (on the day it opened or on a day inside it)."""
    n_units = draw(st.integers(1, 3))
    events: list[Event] = []
    counter = 0
    corr_i = 0
    for ui in range(n_units):
        uid = f"u{ui}"
        day = draw(st.integers(0, 5))
        segs: list[list] = []  # [vf, vt or None]
        state = "none"
        for step in range(draw(st.integers(1, 8))):
            text = " ".join(draw(st.lists(st.sampled_from(WORDS), min_size=1, max_size=3)))
            counter += 1
            eid = f"{uid}-{counter}"
            if state == "none":
                op = "create"
            elif state == "in":
                op = draw(st.sampled_from(["replace", "repeal"]))
            else:
                op = "restore"
            day += draw(st.integers(1, 4))
            if op in ("replace", "repeal"):
                segs[-1][1] = day
            if op in ("create", "replace"):
                segs.append([day, None]); state = "in"
            elif op == "restore":
                segs.append([day, None]); state = "in"
                text = text if draw(st.booleans()) else None
            else:
                state = "out"
            events.append(Event(eid, uid, op, iso(day), text if op != "repeal" else None, iso(day)))
        for _ in range(draw(st.integers(0, 3))):
            vf, vt = draw(st.sampled_from(segs))
            hi = (vt - 1) if vt is not None else vf + 10
            cd = draw(st.integers(vf, hi))
            text = " ".join(draw(st.lists(st.sampled_from(WORDS), min_size=1, max_size=3)))
            corr_i += 1
            events.append(Event(f"{uid}-c{corr_i}", uid, "correct", iso(cd), text,
                                (BASE + timedelta(days=400 + corr_i)).isoformat()))
    shuffled = draw(st.permutations(events))
    return list(shuffled)


def naive_text_at(events, unit_id, d, recorded=None):
    """Independent pure-Python replay: text of the unit in force on ``d``."""
    evs = sorted((e for e in events if e.unit_id == unit_id
                  and (recorded is None or e.recorded_at[: len(recorded)] <= recorded)),
                 key=lambda e: (e.date, e.recorded_at, e.id))
    text, open_date, last_text, correct_text = None, None, None, {}
    state = []  # list of [vf, vt, text]
    for e in evs:
        cur = next((s for s in reversed(state)
                    if s[0] <= e.date and (s[1] is None or e.date < s[1])), None)
        if e.op in ("create", "replace"):
            if cur:
                cur[1] = e.date
            state.append([e.date, None, e.text])
        elif e.op == "repeal":
            last_text = cur[2]
            cur[1] = e.date
        elif e.op == "restore":
            state.append([e.date, None, e.text if e.text is not None else last_text])
        elif e.op == "correct":
            cur[2] = e.text
    for vf, vt, t in state:
        if vf <= d and (vt is None or d < vt) and vf != vt:
            return (t, vf, vt)
    return None


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(histories(), st.integers(-3, 60), st.one_of(st.none(), st.integers(0, 500)))
def test_invariant_nothing_outside_validity(events, day, rec_day):
    units = sorted({e.unit_id for e in events})
    s = make(events, units=units)
    d = iso(day)
    rec = None if rec_day is None else (BASE + timedelta(days=rec_day)).isoformat()
    as_of = AsOf(valid=d, recorded=rec)

    expected = {}
    for u in units:
        r = naive_text_at(events, u, d, rec)
        if r is not None:
            expected[u] = r

    # text_at agrees with the naive replay
    for u in units:
        v = s.text_at(u, as_of)
        if u in expected:
            assert (v.text, v.valid_from, v.valid_to) == expected[u], (u, d, rec)
        else:
            assert v is None, (u, d, rec)

    # lexical: only versions in force, and all of them that match
    q = " ".join(WORDS)
    got = s.lexical(q, as_of, ALL, 1000)
    for p in got:
        assert p.valid_from is None or p.valid_from <= d
        assert p.valid_to is None or d < p.valid_to
        assert expected[p.unit_id] == (p.text, p.valid_from, p.valid_to)
    assert sorted(p.unit_id for p in got) == sorted(expected)

    # dense: same, over vectors made for every current version
    rng = np.random.default_rng(0)
    s.put_vectors("m", [(u, q_, rng.normal(size=4).astype(np.float32))
                        for u, q_, _t in s.missing_vectors("m")])
    for p in s.dense(rng.normal(size=4).astype(np.float32), "m", as_of, ALL, 1000):
        assert p.valid_from is None or p.valid_from <= d
        assert p.valid_to is None or d < p.valid_to
        assert p.unit_id in expected
        assert expected[p.unit_id] == (p.text, p.valid_from, p.valid_to)
    s.close()
