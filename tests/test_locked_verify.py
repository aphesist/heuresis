import pytest

from heuresis.locked.verify import extract_numbers, parse_number, verify
from heuresis.model import AsOf, Draft, Sentence, ToolResult
from heuresis.surface.config import VerifyCfg


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


ASOF = AsOf(valid="2024-03-15")


def run(sentences, passages=None, tools=(), store=None, score=0.9, cfg=None, as_of=ASOF):
    d = Draft(sentences=sentences)
    ent = FixedEntailer(score)
    cl = verify(d, passages if passages is not None else [passage()], list(tools), store, as_of, ent, cfg or VerifyCfg())
    return cl, ent


def test_all_checks_pass():
    cl, _ = run([Sentence("The limit is 1,200.50 euros.", ["t1"])])
    c = cl[0]
    assert c.label == "supported" and all(c.checks.values()) and c.note == ""


def test_exists_fails_without_marks_and_unresolved():
    cl, ent = run([Sentence("No cite here.", [])])
    assert not cl[0].checks["exists"] and cl[0].label == "unsupported"
    assert ent.calls == []
    cl, _ = run([Sentence("The limit is 1,200.50 euros.", ["t9"])])
    assert not cl[0].checks["exists"] and "t9" in cl[0].note


def test_valid_at_date_fallback_to_passage_interval():
    p = passage(valid_from="2024-01-01", valid_to="2024-03-01")
    cl, _ = run([Sentence("The limit is 1,200.50 euros.", ["t1"])], [p])
    assert not cl[0].checks["valid_at_date"] and cl[0].label == "unsupported"
    p = passage(valid_from="2024-01-01", valid_to="2024-04-01")
    cl, _ = run([Sentence("The limit is 1,200.50 euros.", ["t1"])], [p])
    assert cl[0].checks["valid_at_date"]


def test_valid_at_date_uses_store_seq():
    s = Sentence("The limit is 1,200.50 euros.", ["t1"])
    cl, _ = run([s], store=StubStore({"u1": version(seq=1)}))
    assert cl[0].checks["valid_at_date"]
    cl, _ = run([s], store=StubStore({"u1": version(seq=2)}))
    assert not cl[0].checks["valid_at_date"]
    cl, _ = run([s], store=StubStore({}))
    assert not cl[0].checks["valid_at_date"]


@pytest.mark.parametrize("score,label", [(0.5, "supported"), (0.49, "partial"), (0.3, "partial"), (0.29, "unsupported")])
def test_label_thresholds(score, label):
    cl, _ = run([Sentence("The limit is 1,200.50 euros.", ["t1"])], score=score)
    assert cl[0].label == label
    assert cl[0].checks["supported"] == (label == "supported")


def test_numbers_traced_fail_forces_unsupported():
    cl, _ = run([Sentence("The limit is 999 euros.", ["t1"])])
    c = cl[0]
    assert not c.checks["numbers_traced"] and c.label == "unsupported" and "999" in c.note


def test_number_normalisation():
    assert parse_number("1,200.50") == parse_number("1.200,50") == parse_number("1200.50")
    assert parse_number("1.200") == 1200
    assert parse_number("4.8") == parse_number("4,8")
    assert parse_number("1,200,000") == 1200000
    assert extract_numbers("up 6% to R$ 1.200,50") == [6, parse_number("1200.50")]
    cl, _ = run([Sentence("The limit is 1.200,50 euros.", ["t1"])])
    assert cl[0].checks["numbers_traced"]
    cl, _ = run([Sentence("It rose 6%.", ["t1"])], [passage(text="Rise of 6 % was seen.")])
    assert cl[0].checks["numbers_traced"]


def test_years_and_marks_ignored():
    p = passage(text="The rate applies.")
    cl, _ = run([Sentence("In 2024 the rate applies [t1].", ["t1"])], [p])
    assert cl[0].checks["numbers_traced"]
    cl, _ = run([Sentence("In 2023 the rate applies.", ["t1"])], [p])
    assert not cl[0].checks["numbers_traced"]


def test_tool_values_traced_and_substituted():
    tr = ToolResult(mark="k1", tool="calc", args={}, ok=True, value="72.00")
    p = passage(text="The base is 1200 and the rate is 6%.")
    cl, ent = run([Sentence("The tax is {k1}.", ["t1"], ["k1"])], [p], [tr])
    c = cl[0]
    assert c.checks["numbers_traced"] and c.checks["exists"]
    assert "72.00" in c.text
    assert "72.00" in ent.calls[0][0] and "72.00" in ent.calls[0][1]
    # a number not from the tool nor the passage fails
    cl, _ = run([Sentence("The tax is 73.", ["t1"], ["k1"])], [p], [tr])
    assert not cl[0].checks["numbers_traced"]


def test_tool_only_and_failed_tool():
    tr = ToolResult(mark="k1", tool="calc", args={}, ok=True, value=5)
    cl, _ = run([Sentence("The answer is {k1}.", [], ["k1"])], [], [tr])
    assert cl[0].label == "supported"
    bad = ToolResult(mark="k1", tool="calc", args={}, ok=False, error="x")
    cl, _ = run([Sentence("The answer is {k1}.", [], ["k1"])], [], [bad])
    assert not cl[0].checks["exists"]


def test_atomic_splitting():
    s = Sentence("The limit is 1,200.50 euros; the fee is 3 percent and the term is long enough.", ["t1"])
    cl, _ = run([s], cfg=VerifyCfg(atomic_claims=True))
    assert [c.text for c in cl] == [
        "The limit is 1,200.50 euros",
        "the fee is 3 percent",
        "the term is long enough.",
    ]
    assert all(c.passage_marks == ["t1"] for c in cl)
    cl, _ = run([s])
    assert len(cl) == 1


def test_atomic_does_not_split_short_and():
    cl, _ = run([Sentence("Tom and Jerry won 1,200.50.", ["t1"])], cfg=VerifyCfg(atomic_claims=True))
    assert len(cl) == 1


class NamedEntityEntailer:
    """Entails only when the premise contains every capitalised word of the hypothesis,
    like an NLI model that calls a claim neutral when it names something the premise lacks."""
    id = "named"

    def __init__(self):
        self.calls = []

    def entail(self, pairs):
        import re
        self.calls.extend(pairs)
        out = []
        for prem, hyp in pairs:
            names = re.findall(r"\b[A-Z][a-z]+\b", hyp)
            out.append(0.97 if all(n in prem for n in names) and "3,767" in prem else 0.01)
        return out


def _horicon(cfg):
    p = Passage(unit_id="u1", seq=1, mark="t1", source_id="s1", title="Horicon",
                text="The town lies in Dodge County. The population was 3,767 at the census. "
                     "Other facts follow here.")
    d = Draft(sentences=[Sentence("Horicon had 3,767 people.", ["t1"])])
    ent = NamedEntityEntailer()
    return verify(d, [p], [], None, AsOf(valid=None), ent, cfg)[0], ent


def test_default_scores_title_prefixed_sentence_windows_and_takes_the_best():
    assert VerifyCfg().support == "window_title"
    c, ent = _horicon(VerifyCfg())
    assert c.support == pytest.approx(0.97) and c.label == "supported"
    prems = [a for a, _ in ent.calls]
    assert all(p.startswith("Horicon. ") for p in prems)
    # three sentences: windows of 1, 2 and 3 sentences
    assert len(prems) == 3 + 2 + 1
    assert "Horicon. The population was 3,767 at the census." in prems
    assert len(ent.calls) > 1 and len({h for _, h in ent.calls}) == 1


def test_current_support_mode_is_the_first_version_and_stays_selectable():
    c, ent = _horicon(VerifyCfg(support="current"))
    assert len(ent.calls) == 1 and not ent.calls[0][0].startswith("Horicon")
    assert c.support == pytest.approx(0.01) and c.label == "unsupported"


def test_window_mode_without_title_and_with_tool_values():
    p = Passage(unit_id="u1", seq=1, mark="t1", source_id="s1", title="", text="The base is 1200.")
    t = ToolResult(mark="k1", tool="calc", args={}, ok=True, value="72.00")
    ent = FixedEntailer(0.8)
    d = Draft(sentences=[Sentence("The tax is {k1}.", ["t1"], ["k1"])])
    verify(d, [p], [t], None, AsOf(valid=None), ent, VerifyCfg())
    assert ent.calls == [("The base is 1200.\n72.00", "The tax is 72.00.")]
