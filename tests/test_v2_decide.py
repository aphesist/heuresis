import json

import pytest

from heuresis.model import AsOf, Claim, Passage, Query, Source, Version
from heuresis.v2.locked import decide as D
from heuresis.v2.locked.judge import Verdict

POL = D.load_policy()
OK = dict(exists=True, valid_at_date=True, numbers_traced=True, references_traced=True)


def cl(text="x.", marks=("t1",), kind="cited", **bad):
    checks = {**OK, **{k: False for k in bad}}
    return Claim(text, list(marks), kind=kind, checks=checks)


def ps(**kw):
    return [Passage("u1", 0, "A", title="T1", source_id="s1", mark="t1", **kw),
            Passage("u2", 0, "B", title="T2", source_id="s2", mark="t2")]


def V(sent=("SUPPORTED",), answer="DIRECT", sufficient="YES", premise="OK", conflict=None,
      readable=True):
    return Verdict({i: w for i, w in enumerate(sent)}, answer, sufficient, premise, conflict,
                   readable)


Q = Query("q?", AsOf(valid="2021-01-01"))


class FakeStore:
    def __init__(self, auth=None, in_force=True):
        self.auth = auth or {}
        self.in_force = in_force

    def text_at(self, unit, as_of):
        return Version(unit, 0, "x", None, None, "e") if self.in_force else None

    def get_source(self, sid):
        return Source(sid, authority=self.auth[sid]) if sid in self.auth else None


def test_policy_loads():
    assert (POL.alpha, POL.delta, POL.default_tau, POL.min_calibration_answers) == (0.05, 0.1, 0.5, 45)
    assert POL.grid == (0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3)
    assert POL.values["SUPPORTED"] == 0.9 and POL.values["dropped"] == 0.8


def test_policy_from_path(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"alpha": 0.1, "delta": 0.2, "default_tau": 0.3, "grid": [0.5],
                             "min_calibration_answers": 10, "values": {"SUPPORTED": 1}}))
    assert D.load_policy(p).grid == (0.5,)


# 1 declined
def test_1_declined():
    d = D.decide([cl()], V(), ps(), Q, POL, declined="false_premise")
    assert d.status == "abstained" and d.abstention.type == "false_premise" and d.kept == []
    assert d.abstention.searched == ["T1", "T2"]
    # declined wins even with no passages
    assert D.decide([], None, [], Q, POL, declined="conflict").abstention.type == "conflict"


# 2 empty
def test_2_no_passages_no_claims():
    assert D.decide([cl()], V(), [], Q, POL).abstention.type == "no_source"
    d = D.decide([], V(), ps(), Q, POL)
    assert d.abstention.type == "unsupported"


# 3 gates
def test_3_gate_failures():
    d = D.decide([cl(numbers_traced=1)], V(), ps(), Q, POL)
    assert d.abstention.type == "unsupported"
    d = D.decide([cl(valid_at_date=1)], V(), ps(), Q, POL)
    assert d.abstention.type == "not_valid_at_date"
    d = D.decide([cl(valid_at_date=1), cl(exists=1)], V(), ps(), Q, POL)
    assert d.abstention.type == "unsupported"
    d = D.decide([cl(valid_at_date=1), cl("c.", (), "derived", exists=1)], V(), ps(), Q, POL)
    assert d.abstention.type == "not_valid_at_date"  # a derived sentence does not matter


def test_3_failing_claim_is_never_kept():
    claims = [cl("a."), cl("b.", numbers_traced=1)]
    d = D.decide(claims, V(), ps(), Q, POL)
    assert d.status == "partial" and d.kept == [0]
    assert claims[1].label == "unsupported" and claims[1].support == 0.0


# 4 judge
def test_4_unreadable_or_missing_verdict():
    for v in (None, V(readable=False)):
        d = D.decide([cl()], v, ps(), Q, POL)
        assert d.abstention.type == "unsupported" and "judge unreadable" in d.reasons


# 5 premise
def test_5_false_premise():
    d = D.decide([cl()], V(premise="FALSE"), ps(), Q, POL)
    assert d.abstention.type == "false_premise" and d.status == "abstained"


# 6 conflict
def two_claims():
    return [cl("a.", ("t1",)), cl("b.", ("t2",))]


def test_6_conflict_equal_authority():
    v = V(("SUPPORTED", "SUPPORTED"), conflict=("t1", "t2"))
    cs = two_claims()
    d = D.decide(cs, v, ps(), Q, POL, store=FakeStore({"s1": 3, "s2": 3}))
    assert d.status == "divergent" and d.abstention.type == "conflict"
    assert [c.label for c in cs] == ["supported", "supported"]
    assert "T1" in d.abstention.message and "T2" in d.abstention.message
    assert d.abstention.searched == ["T1 [..)", "T2 [..)"]
    assert d.kept == [] and d.confidence == 0.0
    # no store: treated as equal
    assert D.decide(two_claims(), v, ps(), Q, POL).status == "divergent"
    # unknown source: authority 0 == 0
    assert D.decide(two_claims(), v, ps(), Q, POL, store=FakeStore()).status == "divergent"


def test_6_conflict_ignored_cases():
    v = V(("SUPPORTED", "SUPPORTED"), conflict=("t1", "t2"))
    # unequal authority: the higher source rules
    d = D.decide(two_claims(), v, ps(), Q, POL, store=FakeStore({"s1": 3, "s2": 5}))
    assert d.status == "answered"
    # a mark that does not exist
    v9 = V(("SUPPORTED", "SUPPORTED"), conflict=("t1", "t9"))
    assert D.decide(two_claims(), v9, ps(), Q, POL).status == "answered"
    # same unit
    same = ps()
    same[1] = Passage("u1", 1, "B", mark="t2", source_id="s1")
    assert D.decide(two_claims(), v, same, Q, POL).status == "answered"
    # one of them not in force at the date
    assert D.decide(two_claims(), v, ps(), Q, POL, store=FakeStore(in_force=False)).status != "divergent"
    # without a store the passages' own interval decides
    old = ps()
    old[0].valid_to = "2020-01-01"
    assert D.decide(two_claims(), v, old, Q, POL).status == "answered"


def test_6_divergent_keeps_nothing_and_labels_every_claim():
    claims = two_claims() + [cl("c.", (), "derived"), cl("d.", ("t1",), numbers_traced=True)]
    v = V(("SUPPORTED", "NOT_SUPPORTED", "FOLLOWS"), conflict=("t1", "t2"))
    d = D.decide(claims, v, ps(), Q, POL, tau=0.0)
    assert d.status == "divergent" and d.kept == [] and d.confidence == 0.0
    assert all(c.label for c in claims)
    assert [c.label for c in claims[:3]] == ["supported", "unsupported", "supported"]


def test_6_conflict_needs_both_marks_cited_by_claims_that_passed_the_gates():
    v = V(("SUPPORTED",), conflict=("t1", "t2"))
    # t2 is in the evidence but no passing claim cites it
    d = D.decide([cl("a.", ("t1",))], v, ps(), Q, POL)
    assert d.status == "answered"
    # the claim citing t2 failed a gate: the judge never saw that passage
    claims = [cl("a.", ("t1",)), cl("b.", ("t2",), numbers_traced=True)]
    d = D.decide(claims, v, ps(), Q, POL)
    assert d.status == "partial" and d.kept == [0]
    # a derived claim does not count as citing
    d = D.decide([cl("a.", ("t1",)), cl("b.", ("t2",), "derived")], V(("SUPPORTED", "FOLLOWS"),
                 conflict=("t1", "t2")), ps(), Q, POL)
    assert d.status == "answered"


def test_6_conflict_span_in_the_message():
    p = ps()
    p[0].valid_from, p[1].title, p[1].valid_to = "2020-01-01", "", "2030-01-01"
    d = D.decide(two_claims(), V(("SUPPORTED", "SUPPORTED"), conflict=("t1", "t2")), p, Q, POL)
    assert "T1 [2020-01-01..)" in d.abstention.message and "u2 [..2030-01-01)" in d.abstention.message


# 7 sentence verdicts
def test_7_drops_and_labels():
    claims = [cl("a."), cl("b."), cl("c."), cl("d.", (), "derived"), cl("e.", (), "derived")]
    v = V(("SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "FOLLOWS", "NOT_FOLLOWS"))
    d = D.decide(claims, v, ps(), Q, POL, tau=0.0)
    assert d.status == "partial" and d.kept == [0, 1, 3]
    assert [c.label for c in claims] == ["supported", "partial", "unsupported", "supported", "unsupported"]
    assert claims[0].support == 0.9 and claims[1].support == 0.5 and claims[2].support == 0.0
    assert "dropped" in claims[2].note and any("c." in r for r in d.reasons)


def test_7_derived_needs_follows_and_cited_needs_support():
    # a derived sentence marked SUPPORTED (wrong word) is not kept; a cited FOLLOWS is dropped
    claims = [cl("a."), cl("d.", (), "derived")]
    d = D.decide(claims, V(("SUPPORTED", "SUPPORTED")), ps(), Q, POL, tau=0.0)
    assert d.kept == [0]
    d = D.decide([cl("a.")], V(("FOLLOWS",)), ps(), Q, POL, tau=0.0)
    assert d.abstention.type == "unsupported"


def test_7_no_cited_kept():
    d = D.decide([cl("a."), cl("d.", (), "derived")], V(("NOT_SUPPORTED", "FOLLOWS")), ps(), Q, POL)
    assert d.status == "abstained" and d.abstention.type == "unsupported"


def test_7_verdict_positions_skip_gate_failures():
    claims = [cl("bad", numbers_traced=1), cl("good.")]
    d = D.decide(claims, V(("SUPPORTED",)), ps(), Q, POL)
    assert d.status == "partial" and d.kept == [1] and claims[1].label == "supported"


# 8 answer / sufficient
def test_8_answer_and_sufficient():
    d = D.decide([cl()], V(answer="NO"), ps(), Q, POL)
    assert d.abstention.type == "unsupported" and "does not answer" in d.abstention.message
    d = D.decide([cl()], V(answer="PARTIAL", sufficient="NO"), ps(), Q, POL)
    assert d.abstention.type == "no_source"
    d = D.decide([cl()], V(answer="DIRECT", sufficient="NO"), ps(), Q, POL, tau=0.0)
    assert d.status == "answered"  # DIRECT overrides SUFFICIENT: NO (confidence takes the hit)
    assert d.confidence == 0.5
    # ANSWER NO is checked before the sufficiency rule
    assert D.decide([cl()], V(answer="NO", sufficient="NO"), ps(), Q, POL).abstention.type == "unsupported"


# 9 confidence
def test_9_confidence_components():
    c = [cl()]
    f = lambda v, p=None: D.confidence(c, [0], v, p or ps(), POL)  # noqa: E731
    assert f(V()) == 0.9
    assert f(V(("PARTIAL",))) == 0.5
    assert f(V(answer="PARTIAL")) == 0.6
    assert f(V(sufficient="NO")) == 0.5
    low = ps()
    low[0].certainty = "low"
    assert f(V(), low) == 0.33
    med = ps()
    med[0].certainty = "medium"
    assert f(V(), med) == 0.66
    cov = ps()
    cov[0].coverage = 2
    assert f(V(), cov) == 0.5
    cov[0].coverage = 0
    assert f(V(), cov) == 0.0
    # only passages cited by kept claims count
    other = ps()
    other[1].certainty = "low"
    assert f(V(), other) == 0.9
    assert D.confidence(c, [], V(), ps(), POL) == 0.0


def test_9_dropped_multiplier_and_min_over_kept():
    claims = [cl("a."), cl("b."), cl("c.")]
    v = V(("SUPPORTED", "PARTIAL", "NOT_SUPPORTED"))
    assert D.confidence(claims, [0, 1], v, ps(), POL) == pytest.approx(0.5 * 0.8)
    v = V(("SUPPORTED", "SUPPORTED", "SUPPORTED"))
    assert D.confidence(claims, [0, 1, 2], v, ps(), POL) == 0.9


# 10 threshold
def test_10_threshold():
    v = V(("PARTIAL",))  # confidence 0.5
    d = D.decide([cl()], v, ps(), Q, POL)  # default tau 0.5: not below
    assert d.status == "answered" and d.confidence == 0.5 and d.abstention is None
    d = D.decide([cl()], v, ps(), Q, POL, tau=0.51)
    assert d.status == "abstained" and d.abstention.type == "unsupported"
    assert "below the confidence threshold" in d.reasons[0] and d.confidence == 0.5
    assert D.decide([cl()], V(("PARTIAL",), answer="PARTIAL"), ps(), Q, POL, tau=0.55).status == "abstained"
    assert D.decide([cl()], V(), ps(), Q, POL, tau=0.9).status == "answered"
    assert D.decide([cl()], V(), ps(), Q, POL, tau=0.91).status == "abstained"


# 11 answered / partial
def test_11_answered_and_partial():
    claims = [cl("a."), cl("b.")]
    d = D.decide(claims, V(("SUPPORTED", "SUPPORTED")), ps(), Q, POL)
    assert d.status == "answered" and d.kept == [0, 1] and d.confidence == 0.9
    claims = [cl("a."), cl("b.")]
    d = D.decide(claims, V(("SUPPORTED", "NOT_SUPPORTED")), ps(), Q, POL)
    assert d.status == "partial" and d.kept == [0] and d.confidence == pytest.approx(0.72)


# 7 (item 2): numbers of derived sentences after the judge
def test_derived_number_from_a_removed_sentence_is_dropped():
    claims = [cl("Vale 30 dias."), cl("Vale 40 dias."), cl("Logo, 40 dias.", (), "derived")]
    d = D.decide(claims, V(("SUPPORTED", "NOT_SUPPORTED", "FOLLOWS")), ps(), Q, POL, tau=0.0)
    assert d.kept == [0] and claims[2].label == "unsupported"
    assert "number from a removed sentence" in claims[2].note
    assert any("number from a removed sentence" in r for r in d.reasons)
    # the number is allowed again when the cited sentence is kept, or the question has it
    claims = [cl("Vale 30 dias."), cl("Vale 40 dias."), cl("Logo, 40 dias.", (), "derived")]
    d = D.decide(claims, V(("SUPPORTED", "SUPPORTED", "FOLLOWS")), ps(), Q, POL, tau=0.0)
    assert d.kept == [0, 1, 2]
    claims = [cl("Vale 30 dias."), cl("Logo, 40 dias.", (), "derived")]
    d = D.decide(claims, V(("SUPPORTED", "FOLLOWS")), ps(), Query("São 40 dias?", AsOf(valid="2021-01-01")),
                 POL, tau=0.0)
    assert d.kept == [0, 1]
    # explicit question keyword and the as-of date (year, full date)
    claims = [cl("Vale 30 dias."), cl("Logo, 2021 e 2021-01-01 e 45.", (), "derived")]
    d = D.decide(claims, V(("SUPPORTED", "FOLLOWS")), ps(), Q, POL, tau=0.0, question="45?",
                 as_of=AsOf(valid="2021-01-01"))
    assert d.kept == [0, 1]
    # no as-of date: date digits are not free
    claims = [cl("Vale 30 dias."), cl("Logo, em 2021.", (), "derived")]
    d = D.decide(claims, V(("SUPPORTED", "FOLLOWS")), ps(), Q, POL, tau=0.0, as_of=AsOf())
    assert d.kept == [0]


def test_derived_tool_value_needs_traced_arguments_against_kept_sentences():
    from heuresis.model import ToolResult
    good = ToolResult("k1", "calc", {"expr": "30 + 30"}, ok=True, value=60)
    claims = [cl("Vale 30 dias."), cl("Logo, 60 dias.", (), "derived")]
    d = D.decide(claims, V(("SUPPORTED", "FOLLOWS")), ps(), Q, POL, tau=0.0, tool_results=[good])
    assert d.kept == [0, 1]
    # the operand 30 came from a sentence the judge dropped
    claims = [cl("Vale 30 dias."), cl("Vale 31 dias."), cl("Logo, 61 dias.", (), "derived")]
    inv = ToolResult("k1", "calc", {"expr": "31 + 30"}, ok=True, value=61)
    d = D.decide(claims, V(("SUPPORTED", "NOT_SUPPORTED", "FOLLOWS")), ps(), Q, POL, tau=0.0,
                 tool_results=[inv])
    assert d.kept == [0]
    # no tool results given: the value is not allowed
    claims = [cl("Vale 30 dias."), cl("Logo, 60 dias.", (), "derived")]
    assert D.decide(claims, V(("SUPPORTED", "FOLLOWS")), ps(), Q, POL, tau=0.0).kept == [0]


# 9 (item 7): the dropped factor applies to any claim not kept
def test_9_dropped_factor_for_a_gate_failure_too():
    claims = [cl("a."), cl("b.", numbers_traced=True)]
    d = D.decide(claims, V(("SUPPORTED",)), ps(), Q, POL, tau=0.0)
    assert d.status == "partial" and d.confidence == pytest.approx(0.9 * 0.8)
    assert D.decide([cl("a.")], V(("SUPPORTED",)), ps(), Q, POL).confidence == 0.9
