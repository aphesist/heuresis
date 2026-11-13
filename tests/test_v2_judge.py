import pytest

from heuresis.llm import BudgetExceeded, LLMError
from heuresis.model import Claim, Passage, ToolResult, Usage
from heuresis.v2.locked import judge as J


class Scripted:
    id = "scripted"

    def __init__(self, reply="", exc=None):
        self.reply, self.exc, self.calls = reply, exc, []

    def complete(self, system, prompt, *, max_tokens=600):
        self.calls.append((system, prompt, max_tokens))
        if self.exc:
            raise self.exc
        return self.reply, Usage(model="j", tokens_in=7, usd=0.01)


FULL = "S1: SUPPORTED\nS2: FOLLOWS\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: NONE"


def test_parse_full():
    v = J.parse_verdict(FULL, 2)
    assert v.sentences == {0: "SUPPORTED", 1: "FOLLOWS"}
    assert (v.answer, v.sufficient, v.premise, v.conflict, v.readable) == (
        "DIRECT", "YES", "OK", None, True)
    assert v.raw == FULL


def test_parse_conflict_and_variants():
    v = J.parse_verdict("s1: not supported\nS2 - Partial.\nANSWER: partial\nSUFFICIENT: no\n"
                        "PREMISE: false\nCONFLICT: t2, T5", 2)
    assert v.sentences == {0: "NOT_SUPPORTED", 1: "PARTIAL"}
    assert (v.answer, v.sufficient, v.premise, v.conflict) == ("PARTIAL", "NO", "FALSE", ("t2", "t5"))
    v = J.parse_verdict(FULL.replace("NONE", "t1"), 2)
    assert v.conflict is None  # one mark is not a conflict
    v = J.parse_verdict(FULL.replace("CONFLICT: NONE", "CONFLICT: t1, t1"), 2)
    assert v.conflict is None


def test_missing_sentence_lines_read_as_not_supported():
    v = J.parse_verdict("S1: SUPPORTED\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK", 3)
    assert v.sentences == {0: "SUPPORTED", 1: "NOT_SUPPORTED", 2: "NOT_SUPPORTED"} and v.readable
    # out-of-range index and unknown words are ignored
    v = J.parse_verdict("S9: SUPPORTED\nS1: GREAT\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK", 1)
    assert v.sentences == {0: "NOT_SUPPORTED"}


@pytest.mark.parametrize("raw", ["", "nonsense", "S1: SUPPORTED\nSUFFICIENT: YES",
                                 "S1: SUPPORTED\nANSWER: DIRECT", "ANSWER: MAYBE\nSUFFICIENT: YES",
                                 "ANSWER: DIRECT\nSUFFICIENT: UNSURE"])
def test_unreadable(raw):
    assert J.parse_verdict(raw, 1).readable is False


def test_missing_premise_is_unreadable_missing_conflict_is_none_and_never_raises():
    assert J.parse_verdict("ANSWER: NO\nSUFFICIENT: NO", 0).readable is False
    v = J.parse_verdict("ANSWER: NO\nSUFFICIENT: NO\nPREMISE: OK", 0)
    assert v.premise == "OK" and v.readable and v.sentences == {} and v.conflict is None
    assert J.parse_verdict(None, 2).readable is False


BASE = "S1: SUPPORTED\nANSWER: DIRECT\nSUFFICIENT: YES\n"


def test_premise_false_anywhere_wins():
    for tail in ("PREMISE: FALSE\nPREMISE: OK", "PREMISE: OK\nPREMISE: FALSE", "PREMISE: FALSE."):
        v = J.parse_verdict(BASE + tail, 1)
        assert v.premise == "FALSE" and v.readable, tail


@pytest.mark.parametrize("tail", [
    "PREMISE: OK\nCONFLICT: t1, t2\nCONFLICT: NONE",
    "PREMISE: OK\nCONFLICT: t1, t2\nCONFLICT: t1, t3",
    "PREMISE: OK\nANSWER: NO",
    "PREMISE: OK\nSUFFICIENT: NO",
    "PREMISE: contradicted",
    "PREMISE: the question assumes x, which is FALSE-ish",
    "PREMISE: NOT OK",
    "PREMISE:",
    "PREMISE: OK\nCONFLICT: t1",
    "PREMISE: OK\nS1: NOT_SUPPORTED",
])
def test_contradictory_or_unknown_lines_are_unreadable(tail):
    assert J.parse_verdict(BASE + tail, 1).readable is False


def test_conflict_none_wins_over_what_follows_and_repeats_are_fine():
    v = J.parse_verdict(BASE + "PREMISE: OK\nCONFLICT: NONE (t1 and t2 agree)", 1)
    assert v.conflict is None and v.readable
    v = J.parse_verdict(BASE + "PREMISE: OK\nCONFLICT: none; t1 vs t2 do not conflict", 1)
    assert v.conflict is None and v.readable
    v = J.parse_verdict(BASE + "PREMISE: OK\nPREMISE: OK\nANSWER: DIRECT\nS1: SUPPORTED\n"
                        "CONFLICT: t1, t2\nCONFLICT: t2, t1", 1)
    assert v.readable and set(v.conflict) == {"t1", "t2"}


def passages():
    return [Passage("u1", 0, "Texto A. " * 400, title="Lei X, art. 1", valid_from="2020-01-01",
                    mark="t1"),
            Passage("u2", 0, "Texto B.", title="Lei X, art. 2", mark="t2"),
            Passage("u3", 0, "Texto C não citado.", mark="t3")]


def test_prompt_content():
    claims = [Claim("Vale 5 dias.", ["t1"], ["k1"]), Claim("Logo, vale.", kind="derived"),
              Claim("Outra.", ["t2"])]
    tools = [ToolResult("k1", "calc", {}, True, value=5), ToolResult("k2", "calc", {}, True, value=9)]
    pr = J.judge_prompt("Quanto?", "2021-01-01", claims, passages(), tools, max_chars=100)
    assert J.judge_prompt.__defaults__[0] == 8000
    assert "Question: Quanto?" in pr and "As-of date: 2021-01-01" in pr
    assert "S1 (cited [t1][k1]): Vale 5 dias." in pr
    assert "S2 (derived): Logo, vale." in pr and "S3 (cited [t2])" in pr
    assert "[t1] (Lei X, art. 1; valid 2020-01-01..)" in pr and "[...]" in pr
    assert "[t2] (Lei X, art. 2; valid ..)" in pr
    assert "Texto C" not in pr  # only cited passages
    assert "[k1] calc = 5" in pr and "k2" not in pr
    assert len(pr.split("[t1]")[2]) < 400  # truncated to max_chars
    assert "as-of date: not given" in J.judge_prompt("q", None, [], [], []).lower()
    assert "(none)" in J.judge_prompt("q", None, claims[1:2], [], [])


def test_system_names_the_format():
    for w in ("S<i>: SUPPORTED", "FOLLOWS", "ANSWER: DIRECT", "SUFFICIENT: YES", "PREMISE: OK",
              "CONFLICT: NONE"):
        assert w in J.JUDGE_SYSTEM
    assert set(J.SENTENCE_VERDICTS) == {"SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "FOLLOWS",
                                        "NOT_FOLLOWS"}


def test_judge_makes_one_call_and_records_usage():
    llm = Scripted(FULL)
    claims = [Claim("a.", ["t1"]), Claim("b.", kind="derived")]
    v = J.judge(llm, "q?", "2021-01-01", claims, passages(), [], max_tokens=123)
    assert len(llm.calls) == 1 and llm.calls[0][0] == J.JUDGE_SYSTEM and llm.calls[0][2] == 123
    assert v.readable and v.usage.tokens_in == 7 and v.usage.usd == 0.01


def test_judge_unreadable_reply_and_error_propagation():
    assert J.judge(Scripted("hmm"), "q", None, [Claim("a.", ["t1"])], passages(), []).readable is False
    for exc in (LLMError("x"), BudgetExceeded("y")):
        with pytest.raises(type(exc)):
            J.judge(Scripted(exc=exc), "q", None, [Claim("a.", ["t1"])], passages(), [])


def test_long_passage_shows_head_and_tail():
    text = "HEAD " + "x " * 6000 + "TAIL-FACT 40 units"
    p = [Passage("u", 0, text, mark="t1")]
    pr = J.judge_prompt("q", None, [Claim("a.", ["t1"])], p, [])
    assert "HEAD" in pr and "TAIL-FACT 40 units" in pr and "[...]" in pr
    short = "y " * 3900  # 7800 chars: shown whole by default
    pr = J.judge_prompt("q", None, [Claim("a.", ["t1"])], [Passage("u", 0, short, mark="t1")], [])
    assert "[...]" not in pr
