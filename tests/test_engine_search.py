"""The "search" answer mode (answer.mode = "search") and the "grade" decision mode
(decide.mode = "grade") of the engine."""
import json

import pytest

from heuresis import AsOf, Engine, Scope
from heuresis.llm import BudgetExceeded
from heuresis.model import Usage
from heuresis.surface.config import load_config
from heuresis.surface.prompts import DRAFT_SYSTEM, SEARCH_SYSTEM

SRC = {"id": "s1", "kind": "text", "authority": 1, "coverage": 4}
SRC2 = {"id": "s2", "kind": "text", "authority": 1, "coverage": 4}
UNITS = [
    ("rk", "s1", "Zephyr launch"), ("pi", "s1", "Zephyr pilot"), ("bs", "s1", "Beta base"),
    ("al", "s1", "Alpha base"), ("ot", "s2", "Other source")]
EVENTS = [
    # the launch note changes in 2022: only the new text mentions the Zorblax pad
    ("e1", "rk", "create", "2020-01-01", "The rocket Zephyr was launched from the Alpha base."),
    ("e2", "rk", "replace", "2022-01-01", "The rocket Zephyr was moved to the Zorblax pad."),
    ("e3", "pi", "create", "2020-01-01", "Captain Orlov piloted the rocket Zephyr."),
    ("e4", "bs", "create", "2020-01-01", "Beta base is in Norway."),
    ("e5", "al", "create", "2020-01-01", "Alpha base is in Chile."),
    ("e6", "ot", "create", "2020-01-01", "Another Zephyr fact: Orlov also piloted the Zephyr."),
]


@pytest.fixture
def corpus(tmp_path):
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "sources.jsonl").write_text("\n".join(json.dumps(x) for x in (SRC, SRC2)))
    (d / "units.jsonl").write_text("\n".join(json.dumps(
        {"id": u, "source_id": s, "kind": "passage", "title": t}) for u, s, t in UNITS))
    (d / "events.jsonl").write_text("\n".join(json.dumps(
        {"id": i, "unit_id": u, "op": op, "date": dt, "text": tx, "recorded_at": dt,
         "certainty": "high"}) for i, u, op, dt, tx in EVENTS))
    (d / "edges.jsonl").write_text("")
    return str(d)


class Script:
    """Scripted replies, in order; records every system and prompt it was given."""

    id = "script"

    def __init__(self, replies, usd=0.0):
        self.replies, self.usd = list(replies), usd
        self.systems, self.prompts = [], []

    def complete(self, system, prompt, *, max_tokens=600):
        self.systems.append(system)
        self.prompts.append(prompt)
        r = self.replies[len(self.prompts) - 1]
        if isinstance(r, Exception):
            raise r
        return r, Usage(model="script", tokens_in=len(prompt.split()), tokens_out=len(r.split()),
                        usd=self.usd)


def make(tmp_path, corpus, replies, *, usd=0.0, **cfg):
    c = load_config()
    c.retrieve.rerank_out = cfg.pop("rerank_out", 1)  # a narrow first retrieval: search must add more
    for k, v in cfg.items():
        sec, key = k.split("__")
        setattr(getattr(c, sec), key, v)
    llm = Script(replies, usd)
    tmp_path.mkdir(exist_ok=True)
    eng = Engine.open(str(tmp_path / "e.db"), "jsonl", config=c, llm=llm)
    eng.ingest(corpus)
    return eng, llm


Q = "Where was the rocket Zephyr launched?"


def stages(a):
    return [t.stage for t in a.trace if t.stage in ("draft", "search", "draft_followup")]


def test_default_config_is_search_and_grade():
    c = load_config()
    assert (c.answer.mode, c.answer.max_searches, c.answer.search_k) == ("search", 4, 5)
    assert c.decide.mode == "grade"


def test_answer_on_the_first_turn_costs_one_call(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["The rocket was launched from the Alpha base [t1]."], usd=0.001)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "answered" and len(llm.prompts) == 1
    assert stages(a) == ["draft"] and a.usd == pytest.approx(0.001)
    assert llm.systems == [SEARCH_SYSTEM]
    p = llm.prompts[0]
    assert p.startswith("As-of date: 2021-06-01\n")
    assert "Passages:\n[t1] (Zephyr launch; source: S1; valid 2020-01-01..2022-01-01) " in p
    assert "Searches used: 0 of 4." in p and "reply with exactly one line `SEARCH: <query>`" in p
    assert p.index("Question:") < p.index("Searches used")
    eng.close()


def test_a_search_adds_new_passages_with_continued_marks(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, [
        "SEARCH: Orlov pilot Zephyr",
        "Captain Orlov piloted the rocket [t2]."], usd=0.001)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "answered" and len(llm.prompts) == 2
    assert stages(a) == ["draft", "search", "draft"]
    assert a.usd == pytest.approx(0.002)  # the search itself costs no model money
    second = llm.prompts[1]
    assert "Search 1: Orlov pilot Zephyr\n[t2] (" in second
    assert "Searches used: 1 of 4." in second
    # the passages of the first retrieval are still there, and nothing is listed twice
    assert second.count("[t1] (") == 1 and second.count("(Zephyr launch;") == 1
    assert [p.mark for p in a.passages] == [f"t{i}" for i in range(1, len(a.passages) + 1)]
    pilot = next(p for p in a.passages if p.mark == "t2")
    assert a.citations == [(pilot.unit_id, pilot.seq)]
    note = next(t.note for t in a.trace if t.stage == "search")
    assert note.startswith("1/4: Orlov pilot Zephyr")
    eng.close()


def test_search_text_and_search_marks_after_several_rounds(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Orlov pilot", "SEARCH: Beta base Norway",
                                       "Beta base is in Norway [t3]."], answer__search_k=1)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "answered" and stages(a) == ["draft", "search", "draft", "search", "draft"]
    third = llm.prompts[2]
    assert "Search 1: Orlov pilot" in third and "Search 2: Beta base Norway" in third
    assert third.index("Search 1:") < third.index("[t2]") < third.index("Search 2:") < third.index("[t3]")
    assert "Searches used: 2 of 4." in third
    eng.close()


def test_every_search_is_date_filtered_in_code(tmp_path, corpus):
    # "Zorblax" appears only in the version of the launch note that starts in 2022.
    eng, llm = make(tmp_path, corpus, ["SEARCH: Zorblax pad", "ABSTAIN no_source: nothing."])
    eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert "moved to the Zorblax" not in llm.prompts[1] and "(no new passages)" in llm.prompts[1]
    eng.close()
    eng, llm = make(tmp_path / "later", corpus, ["SEARCH: Zorblax pad",
                                                  "The rocket was moved to the Zorblax pad [t1]."])
    a = eng.ask(Q, as_of=AsOf(valid="2023-01-01"))
    assert "moved to the Zorblax" in llm.prompts[1] or "moved to the Zorblax" in llm.prompts[0]
    assert a.status == "answered"
    eng.close()


def test_every_search_keeps_the_questions_scope(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: another Zephyr fact Orlov", "ABSTAIN no_source: x."])
    eng.ask("Who piloted the Zephyr?", as_of=AsOf(valid="2021-06-01"),
            scope=Scope(source_ids=("s1",)))
    assert "Other source" not in llm.prompts[1] and "Another Zephyr fact" not in llm.prompts[1]
    eng.close()


def test_search_cap_and_the_last_prompt_says_none_remain(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Orlov pilot", "ABSTAIN no_source: not found."],
                    answer__max_searches=1)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.abstention.type == "no_source"
    last = llm.prompts[1]
    assert "Searches used: 1 of 1." in last and "No searches remain." in last
    assert "reply with exactly one line `SEARCH" not in last
    eng.close()


def test_asking_to_search_with_none_left_is_an_unsupported_abstention(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Orlov pilot", "SEARCH: again"], answer__max_searches=1)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "abstained" and a.abstention.type == "unsupported"
    assert len(llm.prompts) == 2 and stages(a) == ["draft", "search", "draft"]
    assert "none left" in a.trace[-1].note and "search requested: again" in a.trace[-1].note
    eng.close()


def test_zero_searches_allowed_means_the_first_search_request_abstains(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: anything"], answer__max_searches=0)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.abstention.type == "unsupported" and len(llm.prompts) == 1
    assert "No searches remain." in llm.prompts[0]
    eng.close()


def test_a_search_that_finds_nothing_new_says_so(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Zephyr launched rocket", "ABSTAIN no_source: x."],
                    rerank_out=8)
    eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert "(no new passages)" in llm.prompts[1]
    eng.close()


def test_budget_is_checked_before_every_call(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Orlov pilot", "never reached"], usd=1.0)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"), budget_usd=1.0)
    assert a.status == "abstained" and a.abstention.type == "budget"
    assert len(llm.prompts) == 1
    eng.close()


def test_a_budget_error_from_the_model_is_a_budget_abstention(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Orlov pilot", BudgetExceeded("cap")])
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.abstention.type == "budget"
    assert a.trace[-1].stage in ("draft",) and a.trace[-1].note == "budget exceeded"
    eng.close()


def test_a_model_failure_mid_search_is_unsupported(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Orlov pilot", RuntimeError("boom")])
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.abstention.type == "unsupported"
    assert a.trace[-1].note.startswith("model error")
    eng.close()


def test_the_answer_length_limit_is_in_the_prompt(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["ABSTAIN no_source: x."], draft__max_sentences=2)
    eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert "Answer in at most 2 short sentences." in llm.prompts[0]
    eng.close()
    eng, llm = make(tmp_path / "b", corpus, ["ABSTAIN no_source: x."])
    eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert "at most" not in llm.prompts[0]
    eng.close()


def test_passages_that_do_not_fit_are_dropped_not_cut_and_not_verified(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["SEARCH: Orlov pilot", "Captain Orlov piloted it [t2]."],
                    draft__max_context_chars=700)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    shown = [ln for ln in llm.prompts[1].splitlines() if ln.startswith("[t")]
    assert len(llm.prompts[1]) <= 700 or len(shown) == 1
    assert [p.mark for p in a.passages] == [ln.split("]")[0][1:] for ln in shown]
    eng.close()


def test_single_mode_is_the_earlier_behaviour(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["The rocket was launched from the Alpha base [t1]."],
                    answer__mode="single", decide__mode="strict")
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "answered" and len(llm.prompts) == 1
    assert llm.systems == [DRAFT_SYSTEM] and "Searches used" not in llm.prompts[0]
    assert [t.stage for t in a.trace if t.stage in ("lexical", "retrieve", "draft", "search")] \
        == ["lexical", "retrieve", "draft"]
    eng.close()


def test_a_tool_sql_follow_up_still_works_in_search_mode(tmp_path, corpus):
    # a calc call (no follow-up) in search mode: the result is filled in and verified
    eng, llm = make(tmp_path, corpus, [
        'CALL k1 calc {"expr": "2 + 3"}\nThe base is {k1} km from the pad [t1][k1].'])
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "answered" and "5" in a.text and a.tool_results[0].ok
    eng.close()


# ---------------------------------------------------------------- decide.mode = "grade"


def test_grade_mode_keeps_a_sentence_the_entailer_rejects_and_grades_it(tmp_path, corpus):
    reply = "The rocket was launched from the Alpha base [t1]. Zebras migrate every spring [t1]."
    eng, llm = make(tmp_path, corpus, [reply], rerank_out=8)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "answered" and "Zebras" in a.text
    assert a.grade < 0.5  # the low entailment of the second sentence is the grade
    assert [c.label for c in a.claims][1] == "partial"
    assert a.citations  # its citations still count
    eng.close()
    eng, llm = make(tmp_path / "s", corpus, [reply], rerank_out=8,
                    answer__mode="single", decide__mode="strict")
    b = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert b.status == "partial" and "Zebras" not in b.text  # the gate removes it
    eng.close()


def test_grade_mode_drops_a_sentence_with_a_missing_mark(tmp_path, corpus):
    reply = "The rocket was launched from the Alpha base [t1]. It is a fact [t9]."
    eng, llm = make(tmp_path, corpus, [reply], rerank_out=8)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "partial" and "fact" not in a.text and "Alpha" in a.text
    eng.close()


def test_grade_mode_drops_a_number_found_in_no_cited_passage(tmp_path, corpus):
    reply = "The rocket was launched from the Alpha base [t1]. It flew 4242 km [t1]."
    eng, llm = make(tmp_path, corpus, [reply], rerank_out=8)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "partial" and "4242" not in a.text
    eng.close()


def test_grade_mode_withholds_when_every_sentence_fails(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["It is a fact [t9]. It is another [t8]."], rerank_out=8)
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "abstained" and a.abstention.type == "unsupported" and a.text == ""
    eng.close()


def test_the_model_abstaining_is_still_an_abstention_in_grade_mode(tmp_path, corpus):
    eng, llm = make(tmp_path, corpus, ["ABSTAIN no_source: the passages do not say."])
    a = eng.ask(Q, as_of=AsOf(valid="2021-06-01"))
    assert a.status == "abstained" and a.abstention.type == "no_source"
    eng.close()
