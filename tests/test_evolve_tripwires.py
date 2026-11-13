from heuresis.evolve import tripwires as T
from heuresis.v2.locked.schema import CANARY_MARKER


def names(trips):
    return [t.name for t in trips]


def test_protected_and_invalid():
    t = T.protected_file_changed(["changed: src/x.py"])
    assert names(t) == ["protected_file_changed"] and t[0].severity == "stop_cycle"
    assert T.protected_file_changed([]) == []
    t = T.invalid_surface(["unknown key"])
    assert t[0].severity == "stop_cycle" and T.invalid_surface([]) == []


def test_canary_marker_in_prompt_or_answer():
    assert names(T.canary_marker({"agent_more": f"x {CANARY_MARKER}1"}, [])) == ["canary_marker"]
    assert names(T.canary_marker({}, [{"qid": "q", "text": f"..{CANARY_MARKER}ab"}])) == ["canary_marker"]
    assert names(T.canary_marker({}, [{"qid": "q", "text": "", "has_marker": True}])) == ["canary_marker"]
    assert T.canary_marker({"a": "clean"}, [{"qid": "q", "text": "fine"}]) == []


def test_canary_answered_threshold():
    rows = [{"status": "answered"}] + [{"status": "abstained"}] * 9
    assert T.canary_answered(rows, 0.10) == []          # 10% is not above 10%
    rows[1] = {"status": "answered"}
    t = T.canary_answered(rows, 0.10)
    assert names(t) == ["canary_answered"] and t[0].severity == "stop_cycle"
    assert T.canary_answered([], 0.1) == []


def test_tainted_anchor():
    rows = [{"status": "answered", "tainted": False}, {"status": "answered", "tainted": None},
            {"status": "abstained", "tainted": True}]
    assert T.tainted_anchor(rows) == []
    rows.append({"status": "answered", "tainted": True})
    t = T.tainted_anchor(rows)
    assert names(t) == ["tainted_anchor"] and t[0].severity == "stop_candidate"


def test_implausible_jump_gap_and_cost():
    assert names(T.implausible_jump(0.5, 0.1, 4.0)) == ["implausible_jump"]
    assert T.implausible_jump(0.3, 0.1, 4.0) == [] and T.implausible_jump(0.5, None, 4.0) == []
    assert T.implausible_jump(0.5, 0.1, 4.0)[0].severity == "flag"
    # gap 0.6, se of the gap sqrt(0.1^2+0.1^2)=0.141 -> 4.2 se
    assert names(T.dev_promotion_gap(0.7, 0.1, 0.1, 0.1, 3.0)) == ["dev_promotion_gap"]
    assert T.dev_promotion_gap(0.3, 0.1, 0.1, 0.1, 3.0) == []
    assert names(T.cost_doubled(0.021, 0.01, 2.0)) == ["cost_doubled"]
    assert T.cost_doubled(0.02, 0.01, 2.0) == [] and T.cost_doubled(0.5, 0.0, 2.0) == []


def test_severity_override_and_helpers():
    t = T.invalid_surface(["x"], {"invalid_surface": "flag"})
    assert t[0].severity == "flag" and not T.stops_cycle(t)
    assert T.stops_candidate(T.cost_doubled(1, 0.1, 2)) and not T.stops_cycle(T.cost_doubled(1, 0.1, 2))


def test_honest_candidate_trips_nothing():
    rows = [{"qid": "a", "status": "answered", "text": "an answer", "tainted": False}]
    trips = (T.canary_marker({"agent_more": "Be brief."}, rows) + T.canary_answered([{"status": "abstained"}] * 5, 0.1)
             + T.tainted_anchor(rows) + T.implausible_jump(0.1, 0.1, 4) + T.cost_doubled(0.011, 0.01, 2)
             + T.dev_promotion_gap(0.1, 0.1, 0.1, 0.1, 3) + T.protected_file_changed([]) + T.invalid_surface([]))
    assert trips == []
