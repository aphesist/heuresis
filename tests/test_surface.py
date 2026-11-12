import json

import pytest

from heuresis.model import ABSTENTIONS, Passage
from heuresis.surface import (
    DRAFT_SYSTEM, Config, config_from_dict, config_to_dict, draft_prompt, load_config,
)


def test_default_json_round_trips_to_defaults():
    cfg = load_config()
    assert cfg == Config()
    assert config_from_dict(config_to_dict(cfg)) == cfg
    assert cfg.retrieve.rerank_out == 8 and cfg.draft.model == "claude-haiku-5-5"


def test_load_from_path_and_partial(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"retrieve": {"k_lexical": 7}}))
    cfg = load_config(str(p))
    assert cfg.retrieve.k_lexical == 7 and cfg.retrieve.k_dense == 50


def test_unknown_keys_raise():
    with pytest.raises(ValueError):
        config_from_dict({"bogus": 1})
    with pytest.raises(ValueError):
        config_from_dict({"retrieve": {"nope": 1}})


def test_prompt_contents():
    ps = [Passage("u1", 0, "The limit is 5.", title="Art 1", valid_from="2020-01-01", mark="t1")]
    out = draft_prompt("What is the limit?", "2024-03-15", ps, [])
    assert "[t1] (Art 1; valid 2020-01-01..) The limit is 5." in out
    assert "2024-03-15" in out and "What is the limit?" in out
    for kw in ("ONLY", "CALL k1 calc", "{k1}", "ABSTAIN <type>"):
        assert kw in DRAFT_SYSTEM
    assert all(a in DRAFT_SYSTEM for a in ABSTENTIONS)


def test_max_sentences_instruction():
    from heuresis.surface.config import DraftCfg

    ps = [Passage("u1", 0, "The limit is 5.", title="Art 1", mark="t1")]
    assert DraftCfg().max_sentences == 0
    assert "at most" not in draft_prompt("Q?", None, ps, [])
    assert "at most" not in draft_prompt("Q?", None, ps, [], max_sentences=0)
    out = draft_prompt("Q?", None, ps, [], max_sentences=2)
    assert out.splitlines()[-1] == "Answer in at most 2 short sentences."


def test_drafting_prompt_v2_is_default_and_v1_stays_selectable():
    from heuresis.draft import draft as run_draft
    from heuresis.model import Query
    from heuresis.surface import DRAFT_SYSTEM_V1, DRAFT_SYSTEM_V2, draft_system

    assert DRAFT_SYSTEM is DRAFT_SYSTEM_V2 and draft_system() == DRAFT_SYSTEM_V2
    assert draft_system("v1") == DRAFT_SYSTEM_V1 and DRAFT_SYSTEM_V1 != DRAFT_SYSTEM_V2
    # v1 is the first instruction, verbatim: it abstains whenever the passages do not answer
    assert "If the passages do not answer the question, write only" in DRAFT_SYSTEM_V1
    assert "combine facts" not in DRAFT_SYSTEM_V1
    # v2 asks for the answer first, for combining passages, and for abstaining only then
    for kw in ("combine facts from two or more passages", "State the answer in the first sentence",
               "ALL the passages that support it", "Only if the answer is not in the passages"):
        assert kw in DRAFT_SYSTEM_V2
    for text in (DRAFT_SYSTEM_V1, DRAFT_SYSTEM_V2):  # same format rules in both
        for kw in ("ONLY", "CALL k1 calc", "{k1}", "ABSTAIN <type>"):
            assert kw in text
        assert all(a in text for a in ABSTENTIONS)
    with pytest.raises(ValueError):
        draft_system("v3")
    assert load_config().draft.prompt == "v2"

    seen = []

    class Spy:
        def complete(self, system, prompt, *, max_tokens=600):
            from heuresis.model import Usage
            seen.append(system)
            return "ABSTAIN unsupported: x", Usage()

    cfg = load_config()
    ps = [Passage("u1", 0, "The limit is 5.", title="Art 1", mark="t1")]
    run_draft(Spy(), Query("q"), ps, [], cfg.draft)
    cfg.draft.prompt = "v1"
    run_draft(Spy(), Query("q"), ps, [], cfg.draft)
    assert seen == [DRAFT_SYSTEM_V2, DRAFT_SYSTEM_V1]
    from heuresis.bench import systems as S
    a = S.surface_hash(load_config())
    assert S.surface_hash(cfg) != a  # the choice of prompt is part of the surface hash


def test_source_label_and_the_one_shared_passage_line():
    from heuresis.bench import systems as S
    from heuresis.surface.prompts import passage_line, source_label

    assert source_label("multihoprag:sporting-news") == "Sporting News"
    assert source_label("multihoprag:the_age") == "The Age"
    assert source_label("cnbc") == "Cnbc"          # no colon: the id itself, capitalised
    assert source_label("") == "" and source_label(":") == ":"   # nothing readable: the id
    p = Passage("u1", 0, "Some  text\nhere.", title="Art 1", valid_from="2020-01-01", mark="t1",
                source_id="multihoprag:sporting-news")
    line = "[t1] (Art 1; source: Sporting News; valid 2020-01-01..) Some text here."
    assert passage_line("t1", p) == line
    # the engine's draft prompt and the baselines' prompts render the same line
    assert line in draft_prompt("Q?", None, [p], [])
    assert line in S.passages_prompt("Q?", [p])
    assert S._passage_line("t1", p) == line
    # no source id: no source part
    q = Passage("u2", 0, "x", title="T", mark="t2")
    assert passage_line("t2", q) == "[t2] (T; valid ..) x"


def test_search_prompt_and_system():
    from heuresis.surface.prompts import SEARCH_LAST, SEARCH_MORE, SEARCH_SYSTEM, passage_line, search_prompt

    def p(mark, text, src="web:site-a"):
        return Passage("u" + mark, 0, text, title="T" + mark, source_id=src, mark=mark,
                       valid_from="2020-01-01")

    first = [p("t1", "First fact."), p("t2", "Second fact.")]
    rounds = [("", first), ("who is X", [p("t3", "Third fact.")]), ("again", [])]
    out = search_prompt("Q?", "2021-05-05", rounds, 2, 4)
    lines = out.splitlines()
    assert lines[0] == "As-of date: 2021-05-05" and lines[1] == "Passages:"
    assert lines[2] == passage_line("t1", first[0])  # the one shared rendering
    assert "Search 1: who is X" in lines and "Search 2: again" in lines
    assert lines[lines.index("Search 2: again") + 1] == "(no new passages)"
    assert lines.index("Search 1: who is X") + 1 == lines.index(passage_line("t3", rounds[1][1][0]))
    assert lines[-3:] == ["Question: Q?", "Searches used: 2 of 4.", SEARCH_MORE]
    assert search_prompt("Q?", None, rounds[:1], 0, 4).splitlines()[-1] == SEARCH_LAST
    assert search_prompt("Q?", None, [], 4, 4).splitlines()[1:3] == ["Passages:", "(none)"]
    assert "As-of date: today" in search_prompt("Q?", None, rounds[:1], 4, 4)
    assert search_prompt("Q?", None, rounds[:1], 4, 4, max_sentences=2).splitlines()[-2] == \
        "Answer in at most 2 short sentences."
    # the system text states the contract of both outputs
    for kw in ("SEARCH: <query>", "first sentence", "CALL k1 calc", "ABSTAIN <type>", "[t1][t2]"):
        assert kw in SEARCH_SYSTEM
    assert all(a in SEARCH_SYSTEM for a in ABSTENTIONS)


def test_config_has_the_answer_block_and_the_decide_mode():
    from heuresis.surface import config_from_dict, config_to_dict, load_config

    c = load_config()
    assert (c.answer.mode, c.answer.max_searches, c.answer.search_k, c.decide.mode) == \
        ("search", 4, 5, "grade")
    assert config_to_dict(c)["answer"] == {"mode": "search", "max_searches": 4, "search_k": 5}
    d = config_to_dict(c)
    d["answer"]["mode"], d["decide"]["mode"] = "single", "strict"
    c2 = config_from_dict(d)
    assert (c2.answer.mode, c2.decide.mode) == ("single", "strict")
    with pytest.raises(ValueError):
        config_from_dict({"answer": {"nope": 1}})
    # a config written before the redesign (no answer block, no decide.mode) gets the defaults
    old = {k: v for k, v in config_to_dict(c).items() if k != "answer"}
    del old["decide"]["mode"]
    assert config_from_dict(old).answer.mode == "search" and config_from_dict(old).decide.mode == "grade"
