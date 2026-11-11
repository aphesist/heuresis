from types import SimpleNamespace

from heuresis.locked.decide import decide
from heuresis.model import Claim, Query, Source
from heuresis.surface.config import DecideCfg


from heuresis.model import Passage, Version


class StubStore:
    def __init__(self, versions=None, sources=None):
        self.versions = versions or {}
        self.sources = sources or {}

    def text_at(self, unit_id, as_of):
        return self.versions.get(unit_id)

    def get_source(self, source_id):
        return self.sources.get(source_id)


class FixedEntailer:
    id = "fixed"

    def __init__(self, score=0.9):
        self.score = score
        self.calls = []

    def entail(self, pairs):
        self.calls.extend(pairs)
        return [self.score] * len(pairs)


def passage(unit="u1", seq=1, text="The limit is 1,200.50 euros.", mark="t1", **kw):
    return Passage(unit_id=unit, seq=seq, text=text, mark=mark, source_id=kw.pop("source_id", "s1"), **kw)


def version(unit="u1", seq=1):
    return Version(unit_id=unit, seq=seq, text="", valid_from=None, valid_to=None, event_id="e")


Q = Query("q")


def claim(label="supported", support=0.9, marks=("t1",), note="", **checks):
    ck = {"exists": True, "valid_at_date": True, "supported": label == "supported", "numbers_traced": True}
    ck.update(checks)
    return Claim("x", list(marks), [], support, label, ck, note)


def test_declined():
    st, g, ab = decide([], [passage()], Q, DecideCfg(), declined="out_of_scope")
    assert (st, g, ab.type) == ("abstained", 0.0, "out_of_scope")


def test_no_passages():
    st, g, ab = decide([claim()], [], Q, DecideCfg())
    assert (st, g, ab.type) == ("abstained", 0.0, "no_source")


def test_answered_and_grade_arithmetic():
    ps = [passage(certainty="medium", coverage=3, title="Doc A")]
    st, g, ab = decide([claim(support=0.9)], ps, Q, DecideCfg())
    assert st == "answered" and ab is None
    assert g == min(0.9, 0.66, 0.75)
    ps = [passage(certainty="high", coverage=4)]
    assert decide([claim(support=0.8), claim(support=0.6)], ps, Q, DecideCfg())[1] == 0.6
    ps = [passage(certainty="low", coverage=4)]
    assert decide([claim(support=0.8)], ps, Q, DecideCfg())[1] == 0.33
    ps = [passage(coverage=1)]
    assert decide([claim(support=0.8)], ps, Q, DecideCfg())[1] == 0.25


def test_partial():
    cl = [claim(), claim("unsupported", 0.1, marks=("t2",))]
    ps = [passage(), passage(unit="u2", mark="t2", coverage=1)]
    st, g, ab = decide(cl, ps, Q, DecideCfg())
    assert st == "partial" and ab is None
    assert g == 0.9  # unsupported sentence's citations do not lower the grade


def test_min_supported_fraction_relaxed():
    cl = [claim(), claim(), claim("unsupported", 0.1)]
    st, _, _ = decide(cl, [passage()], Q, DecideCfg(min_supported_fraction=0.6))
    assert st == "answered"


def test_unsupported_abstention_with_searched():
    cl = [claim("unsupported", 0.1), claim("unsupported", 0.1), claim()]
    ps = [passage(title="Doc A"), passage(unit="u9", mark="t2", title="")]
    st, g, ab = decide(cl, ps, Q, DecideCfg())
    assert (st, g, ab.type) == ("abstained", 0.0, "unsupported")
    assert ab.searched == ["Doc A", "u9"]


def test_no_claims_is_unsupported():
    assert decide([], [passage()], Q, DecideCfg())[2].type == "unsupported"


def test_not_valid_at_date():
    cl = [claim("unsupported", 0.9, valid_at_date=False)]
    st, g, ab = decide(cl, [passage()], Q, DecideCfg())
    assert (st, g, ab.type) == ("abstained", 0.0, "not_valid_at_date")
    cl = [claim("unsupported", 0.9, valid_at_date=False, numbers_traced=False)]
    assert decide(cl, [passage()], Q, DecideCfg())[2].type == "unsupported"


def _conflict_setup(auth_a=1, auth_b=1):
    ps = [passage("u1", mark="t1", source_id="sa"), passage("u2", mark="t2", source_id="sb")]
    cl = [claim(marks=("t1",), note="conflict: number mismatch"), claim(marks=("t2",), note="conflict")]
    store = StubStore(sources={"sa": Source("sa", authority=auth_a), "sb": Source("sb", authority=auth_b)})
    return cl, ps, store


def test_divergent():
    cl, ps, store = _conflict_setup()
    st, g, ab = decide(cl, ps, Q, DecideCfg(), store)
    assert st == "divergent" and ab.type == "conflict" and g > 0


def test_divergent_never_without_store_or_equal_authority_or_distinct_units():
    cl, ps, store = _conflict_setup()
    assert decide(cl, ps, Q, DecideCfg())[0] == "answered"
    cl, ps, store = _conflict_setup(auth_a=2, auth_b=1)
    assert decide(cl, ps, Q, DecideCfg(), store)[0] == "answered"
    cl, ps, store = _conflict_setup()
    ps[1].unit_id = "u1"
    assert decide(cl, ps, Q, DecideCfg(), store)[0] == "answered"
