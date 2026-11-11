from heuresis.draft import draft, parse_draft, render
from heuresis.fakes import EchoLLM
from heuresis.model import AsOf, Passage, Query, ToolResult
from heuresis.surface.config import DraftCfg


def test_parse_basic():
    raw = (
        'CALL k1 calc {"expr": "1200 * 0.06"}\n'
        "The limit was R$ 4.8 million [t1]. It rose later [t2][t3].\n"
        "The tax due is {k1} [t2][k1].\n"
    )
    d = parse_draft(raw)
    assert d.tool_calls == [{"mark": "k1", "tool": "calc", "args": {"expr": "1200 * 0.06"}}]
    assert [s.text for s in d.sentences] == [
        "The limit was R$ 4.8 million.", "It rose later.", "The tax due is {k1}."]
    assert d.sentences[0].passage_marks == ["t1"]
    assert d.sentences[1].passage_marks == ["t2", "t3"]
    assert d.sentences[2].passage_marks == ["t2"] and d.sentences[2].tool_marks == ["k1"]
    assert d.raw == raw


def test_abstain():
    assert parse_draft("ABSTAIN no_source: nothing covers this.").declined == "no_source"
    assert parse_draft("ABSTAIN weird: hm").declined == "unsupported"
    assert parse_draft("ABSTAIN").declined == "unsupported"


def test_robust_forms():
    raw = "```\n- Fee is 5 [t1, t2]. Next [t3] one here.\n* Another [t1]\n1. Third thing [k2].\n```"
    d = parse_draft(raw)
    assert d.sentences[0].passage_marks == ["t1", "t2"]
    assert d.sentences[1].text == "Next one here." and d.sentences[1].passage_marks == ["t3"]
    assert d.sentences[2].text == "Another" and d.sentences[3].tool_marks == ["k2"]


def test_marks_after_period_and_orphan_marks():
    d = parse_draft("Fact one. [t1] Fact two. [t2]\n[t3]")
    assert [s.text for s in d.sentences] == ["Fact one.", "Fact two."]
    assert d.sentences[1].passage_marks == ["t2", "t3"]


def test_malformed_call_and_never_raises():
    d = parse_draft("CALL k1 calc {bad json\nCALL k2 calc [1]\nCALL k3 dates")
    assert "_error" in d.tool_calls[0]["args"] and "_error" in d.tool_calls[1]["args"]
    assert d.tool_calls[2]["args"] == {}
    for junk in ("", "\n\n", "[[[", None, "{k1}", "]]] [t1"):
        parse_draft(junk)  # type: ignore[arg-type]


def test_render():
    d = parse_draft("Tax is {k1} [t2][k1].\nOther is {k9} [t1].\nBad is {k2}.")
    res = [ToolResult("k1", "calc", {}, True, value="72"),
           ToolResult("k2", "calc", {}, False, error="boom")]
    out = render(d, res)
    assert out == "Tax is 72. [t2][k1] Other is [not checked]. [t1] Bad is [not checked]."


def passages(n, size=100):
    return [Passage("u%d" % i, 1, ("word " * (size // 5)).strip(), title="T%d" % i,
                    mark="t%d" % i) for i in range(1, n + 1)]


def test_draft_with_echo():
    llm = EchoLLM(["Answer here [t1]."])
    q = Query("what?", as_of=AsOf(valid="2024-01-01"))
    d = draft(llm, q, passages(2), [], DraftCfg())
    assert d.sentences[0].passage_marks == ["t1"]
    assert d.raw == "Answer here [t1]." and d.usage.model == "echo"


def test_draft_truncates_lowest_ranked_first():
    seen = []

    class Spy:
        id = "spy"

        def complete(self, system, prompt, *, max_tokens=600):
            seen.append((prompt, max_tokens))
            from heuresis.model import Usage
            return "ABSTAIN no_source: x", Usage()

    ps = passages(10, 400)
    cfg = DraftCfg(max_context_chars=1500, max_tokens=77)
    d = draft(Spy(), Query("q"), ps, [], cfg)
    prompt, mt = seen[0]
    assert mt == 77 and len(prompt) <= 1500 and d.declined == "no_source"
    assert "[t1]" in prompt and "[t10]" not in prompt
    present = [i for i in range(1, 11) if f"[t{i}]" in prompt]
    assert present == list(range(1, len(present) + 1))  # a prefix, whole passages
    assert all(("word " * 80).strip() in prompt for _ in present)  # never cut mid-text


def test_marks_before_and_after_terminator():
    for raw in ("The limit is 5 million [t1].", "The limit is 5 million. [t1]"):
        d = parse_draft(raw)
        assert len(d.sentences) == 1
        assert d.sentences[0].text == "The limit is 5 million."
        assert d.sentences[0].passage_marks == ["t1"]


def test_two_sentences_one_line_own_marks():
    d = parse_draft("First fact holds. [t1] Second fact holds [t2][k1]. Third. [t3]")
    assert [s.text for s in d.sentences] == ["First fact holds.", "Second fact holds.", "Third."]
    assert [s.passage_marks for s in d.sentences] == [["t1"], ["t2"], ["t3"]]
    assert d.sentences[1].tool_marks == ["k1"]


def test_echo_default_output_parses():
    q = Query("limit?")
    d = draft(EchoLLM(), q, passages(2), [], DraftCfg())
    assert d.sentences and d.sentences[0].passage_marks


def test_draft_passes_max_sentences():
    class Rec:
        id = "rec"

        def complete(self, system, prompt, *, max_tokens=600):
            self.prompt = prompt
            return "ABSTAIN no_source: x.", None

    for n, expect in ((0, False), (3, True)):
        llm = Rec()
        draft(llm, Query("limit?"), passages(1), [], DraftCfg(max_sentences=n))
        assert ("Answer in at most 3 short sentences." in llm.prompt) is expect
