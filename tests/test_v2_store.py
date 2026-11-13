from __future__ import annotations

from datetime import date, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from heuresis.model import AsOf, Event, Scope, Source, Unit
from heuresis.store import Store


def ev(id, unit, op, d, text=None, rec=""):
    return Event(id=id, unit_id=unit, op=op, date=d, text=text, recorded_at=rec or d)


def make(events, units, sources=None, unit_source=None):
    s = Store(":memory:")
    s.add(
        sources=sources or [Source("src"), Source("other", coverage=2)],
        units=[Unit(u, (unit_source or {}).get(u, "src"), title=f"title {u}") for u in units],
        events=events,
    )
    s.rebuild()
    return s


def test_passage_at_fields_and_none():
    s = make([ev("e1", "a", "create", "2020-01-01", "one"),
              ev("e2", "a", "replace", "2021-01-01", "two"),
              ev("e3", "a", "repeal", "2022-01-01")], ["a"])
    p = s.passage_at("a", AsOf(valid="2020-06-01"))
    assert (p.text, p.title, p.source_id, p.stage) == ("one", "title a", "src", "lookup")
    assert (p.valid_from, p.valid_to) == ("2020-01-01", "2021-01-01")
    assert s.passage_at("a", AsOf(valid="2021-06-01")).text == "two"
    assert s.passage_at("a", AsOf(valid="2019-01-01")) is None
    assert s.passage_at("a", AsOf(valid="2023-01-01")) is None
    assert s.passage_at("missing", AsOf(valid="2021-06-01")) is None


def test_adjacent_order_radius_and_exclusion():
    ids = ["u1", "u2", "u3", "u4", "u5"]
    s = make([ev(f"e{u}", u, "create", "2020-01-01", f"text {u}") for u in ids], ids)
    got = s.adjacent("u3", AsOf(valid="2021-01-01"), 1)
    assert [p.unit_id for p in got] == ["u2", "u4"] and {p.stage for p in got} == {"open"}
    assert [p.unit_id for p in s.adjacent("u3", AsOf(valid="2021-01-01"), 5)] == [
        "u1", "u2", "u4", "u5"]
    assert [p.unit_id for p in s.adjacent("u1", AsOf(valid="2021-01-01"), 2)] == ["u2", "u3"]
    assert s.adjacent("u3", AsOf(valid="2021-01-01"), 0) == []
    assert s.adjacent("nope", AsOf(valid="2021-01-01"), 1) == []


def test_adjacent_same_source_only_and_skips_not_in_force():
    s = make(
        [ev("e1", "a", "create", "2020-01-01", "a"),
         ev("e2", "b", "create", "2020-01-01", "b"),
         ev("e3", "c", "create", "2023-01-01", "c"),   # not yet in force in 2021
         ev("e4", "d", "create", "2020-01-01", "d"),
         ev("e5", "x", "create", "2020-01-01", "x")],
        ["a", "b", "x", "c", "d"], unit_source={"x": "other"})
    got = s.adjacent("a", AsOf(valid="2021-01-01"), 2)
    assert [p.unit_id for p in got] == ["b", "d"]          # x is another source, c not in force
    assert [p.unit_id for p in s.adjacent("a", AsOf(valid="2024-01-01"), 2)] == ["b", "c"]


def test_as_of_recorded_hides_later_knowledge():
    s = make([ev("e1", "a", "create", "2020-01-01", "old", rec="2020-01-01"),
              ev("e2", "a", "correct", "2020-01-01", "fixed", rec="2023-01-01"),
              ev("e3", "b", "create", "2020-01-01", "bee", rec="2020-01-01"),
              ev("e4", "c", "create", "2020-01-01", "cee", rec="2023-01-01")],
             ["a", "b", "c"])
    early = AsOf(valid="2021-01-01", recorded="2022-01-01")
    late = AsOf(valid="2021-01-01", recorded="2024-01-01")
    assert s.passage_at("a", early).text == "old"
    assert s.passage_at("a", late).text == "fixed"
    assert s.passage_at("a", AsOf(valid="2021-01-01")).text == "fixed"
    assert s.passage_at("c", early) is None
    assert [p.unit_id for p in s.adjacent("b", early, 3)] == ["a"]
    assert [p.unit_id for p in s.adjacent("b", late, 3)] == ["a", "c"]
    assert [p.text for p in s.adjacent("b", early, 3)] == ["old"]


# --- property: nothing outside the validity interval ------------------------------------

BASE = date(2020, 1, 1)


def iso(n):
    return (BASE + timedelta(days=n)).isoformat()


@st.composite
def histories(draw):
    events, n = [], 0
    for u in ("u1", "u2", "u3", "u4"):
        days = sorted(draw(st.lists(st.integers(0, 50), min_size=1, max_size=4, unique=True)))
        ops = ["create"] + [draw(st.sampled_from(["replace", "repeal", "restore", "correct"]))
                            for _ in days[1:]]
        state = "live"
        for d, op in zip(days, ops):
            if op == "repeal":
                state = "repealed"
                events.append(ev(f"e{n}", u, op, iso(d), None, rec=iso(d + draw(st.integers(0, 5)))))
            elif op == "restore" and state != "live":
                state = "live"
                events.append(ev(f"e{n}", u, op, iso(d), f"t{n}", rec=iso(d)))
            elif op in ("create", "replace", "correct") or op == "restore":
                events.append(ev(f"e{n}", u, "create" if op == "create" else "replace",
                                 iso(d), f"t{n}", rec=iso(d + draw(st.integers(0, 5)))))
            n += 1
    return events


@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(histories(), st.integers(-3, 60), st.one_of(st.none(), st.integers(0, 70)))
def test_invariant_passage_at_and_adjacent_stay_in_validity(events, day, rec_day):
    units = ["u1", "u2", "u3", "u4"]
    try:
        s = make(events, units)
    except Exception:
        return  # a generated history that replay rejects is not what is under test
    d = iso(day)
    rec = None if rec_day is None else iso(rec_day)
    as_of = AsOf(valid=d, recorded=rec)
    for u in units:
        v = s.text_at(u, as_of)
        p = s.passage_at(u, as_of)
        if v is None:
            assert p is None
        else:
            assert p is not None and (p.text, p.valid_from, p.valid_to) == (
                v.text, v.valid_from, v.valid_to)
        assert p is None or p.valid_from is None or p.valid_from <= d
        assert p is None or p.valid_to is None or d < p.valid_to
        for r in (1, 2, 3):
            for q in s.adjacent(u, as_of, r):
                assert q.unit_id != u
                assert q.valid_from is None or q.valid_from <= d
                assert q.valid_to is None or d < q.valid_to
                tv = s.text_at(q.unit_id, as_of)
                assert tv is not None and tv.text == q.text
    s.close()
