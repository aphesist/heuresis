"""The v2 propose loop: evidence, action parsing, prompt layout, search/open/answer turns."""
from __future__ import annotations

from heuresis.llm import CACHE_BREAK, BudgetExceeded
from heuresis.model import AsOf, Event, Passage, Query, Source, StageTrace, Unit, Usage
from heuresis.store import Store
from heuresis.surface.prompts import passage_line
from heuresis.v2.agent import Evidence, build_prompt, parse_actions, propose
from heuresis.v2.locked.schema import apply_overrides, load_surface

SURF = load_surface()


def surf(**over):
    return apply_overrides(SURF, {"config": {k.replace("__", "."): v for k, v in over.items()}})


def ev(id, unit, op, d, text=None):
    return Event(id=id, unit_id=unit, op=op, date=d, text=text, recorded_at=d)


def make_store():
    s = Store(":memory:")
    s.add(sources=[Source("src")],
          units=[Unit(u, "src", title=f"Title {u}") for u in ("a1", "a2", "a3", "a4", "fee")],
          events=[
              ev("e1", "a1", "create", "2019-01-01", "The harbour tariff covers vessels above ten tonnes."),
              ev("e2", "a2", "create", "2019-01-01", "Pilotage charges are levied per movement in the basin."),
              ev("e3", "a3", "create", "2019-01-01", "Mooring dues apply to vessels at the quay overnight."),
              ev("e4", "a4", "create", "2019-01-01", "Orchards produce apples in autumn."),
              ev("e5", "fee", "create", "2019-01-01", "The pilotage fee is 40 units."),
              ev("e6", "fee", "replace", "2022-01-01", "The pilotage fee is 55 units."),
          ])
    s.rebuild()
    return s


class Script:
    id = "script"

    def __init__(self, replies, usd=0.0, cached=0, cache_break=False):
        self.replies, self.usd, self.cached = list(replies), usd, cached
        self.prompts, self.systems = [], []
        if cache_break:
            self.supports_cache_break = True

    def complete(self, system, prompt, *, max_tokens=600):
        self.systems.append(system)
        self.prompts.append(prompt)
        i = len(self.prompts) - 1
        if i >= len(self.replies):
            raise RuntimeError("script exhausted")
        r = self.replies[i]
        if isinstance(r, Exception):
            raise r
        return r, Usage(model="script", tokens_in=len(prompt.split()), tokens_out=len(r.split()),
                        tokens_cached=self.cached, usd=self.usd)


def P(uid, text="text", seq=0, **kw):
    return Passage(unit_id=uid, seq=seq, text=text, title=f"Title {uid}", source_id="src", **kw)


def query(text="Which vessels pay the harbour tariff?", valid="2021-01-01"):
    return Query(text=text, as_of=AsOf(valid=valid))


def run(llm, store=None, q=None, evidence=None, surface=None, afford=None, **kw):
    store = store or make_store()
    trace: list[StageTrace] = []
    ev_ = evidence if evidence is not None else Evidence()
    if evidence is None:
        ev_.add("", [P("a1", "The harbour tariff covers vessels above ten tonnes.")])
    out = propose(llm, q or query(), ev_, [], surface or SURF, store=store, domain=None,
                  embedder=None, trace=trace, afford=afford or (lambda c: True), **kw)
    return out, ev_, trace


# -- Evidence ------------------------------------------------------------------------------

def test_evidence_marks_seen_and_by_mark():
    e = Evidence()
    got = e.add("", [P("a"), P("b")])
    assert [p.mark for p in got] == ["t1", "t2"]
    again = e.add("Search: x", [P("b"), P("c")])        # b was shown: only c is new
    assert [(p.unit_id, p.mark) for p in again] == [("c", "t3")]
    assert [p.mark for p in e.passages] == ["t1", "t2", "t3"]
    assert [lab for lab, _ in e.rounds] == ["", "Search: x"]
    assert e.by_mark("t2").unit_id == "b" and e.by_mark("T3").unit_id == "c" and e.by_mark("t9") is None
    assert e.seen() == {("a", 0), ("b", 0), ("c", 0)}
    # a different version of a shown unit is a new passage
    assert [p.mark for p in e.add("x", [P("a", seq=1)])] == ["t4"]


def test_evidence_fits_drops_and_stops():
    e = Evidence()
    got = e.add("Search: q", [P("a"), P("b"), P("c")], fits=lambda: len(e.passages) <= 2)
    assert [p.unit_id for p in got] == ["a", "b"] and len(e.passages) == 2
    assert ("c", 0) not in e.seen()
    assert e.rounds[0][1] == got


def test_evidence_pop_last_only_first_retrieval():
    e = Evidence()
    e.add("Lookup", [P("l")])
    e.add("Retrieved", [P("a"), P("b")])
    assert e.droppable() and e.pop_last().unit_id == "b"
    assert e.pop_last().unit_id == "a" and not e.droppable()          # lookup is never dropped
    assert [p.unit_id for p in e.passages] == ["l"]
    e.add("Search: q", [P("z")])
    assert not e.droppable()


# -- parse_actions -------------------------------------------------------------------------

def test_parse_actions_forms():
    a = parse_actions("SEARCH: pilotage fees\nOPEN: t2", 3)
    assert (a.searches, a.opens) == (["pilotage fees"], ["t2"])
    a = parse_actions("- `search: Mooring dues.`\n* Open: [t3];\n1. SEARCH: quay overnight?", 3)
    assert a.searches == ["Mooring dues", "quay overnight"] and a.opens == ["t3"]
    a = parse_actions("```\nSEARCH: one\nSEARCH: two\nSEARCH: three\nSEARCH: four\n```", 2)
    assert a.searches == ["one", "two"]
    a = parse_actions("OPEN: a\nOPEN: b\nOPEN: c\nOPEN: d", 3)
    assert a.opens == ["a", "b", "c"]
    assert parse_actions("SEARCH: x\nSEARCH: x", 3).searches == ["x"]
    assert parse_actions("OPEN: art. 8 da Lei 1/2020.", 3).opens == ["art. 8 da Lei 1/2020"]


def test_parse_actions_answer_is_not_actions():
    assert parse_actions("The tariff is X [t1]. You could SEARCH: more.", 3) is None
    assert parse_actions("SEARCH: pilotage\nThe fee is 40 units [t1].", 3) is None   # mixed = answer
    assert parse_actions("ABSTAIN no_source: nothing", 3) is None
    assert parse_actions("", 3) is None and parse_actions("  \n ", 3) is None
    assert parse_actions("SEARCH:", 3) is None
    assert parse_actions("CALL k1 calc {}", 3) is None
    assert parse_actions(None, 3) is None


# -- build_prompt --------------------------------------------------------------------------

def test_build_prompt_layout():
    e = Evidence()
    e.add("", [P("a1", "First text.")])
    e.add("Search: pilotage", [P("a2", "Second text.")])
    e.add("Open: t1", [])
    class T:
        name, description = "calc", "arithmetic"
    p = build_prompt(SURF, query(), e, [T()], 4, feedback="FIX THIS")
    lines = p.splitlines()
    assert lines[0] == "As-of date: 2021-01-01"
    assert lines[1] == "Tools: calc (arithmetic)"
    assert lines[2] == "Question: Which vessels pay the harbour tariff?"
    assert lines[3] == "Passages:"
    assert lines[4] == passage_line("t1", e.passages[0])          # first block unlabeled
    assert lines[5] == "Search: pilotage" and lines[6] == passage_line("t2", e.passages[1])
    assert lines[7] == "Open: t1" and lines[8] == "(nothing new)"
    assert lines[9] == "Turns left: 4."
    assert SURF.prompt("agent_more") in p and SURF.prompt("agent_last") not in p
    assert p.endswith("FIX THIS") and CACHE_BREAK not in p
    last = build_prompt(SURF, query(), e, [], 1)
    assert SURF.prompt("agent_last") in last and "Turns left: 1." in last and "Tools:" not in last
    assert "As-of date: today" in build_prompt(SURF, Query(text="q"), e, [], 2)


def test_build_prompt_cache_break_labels_and_max_sentences():
    e = Evidence()
    e.add("Lookup", [P("l")])
    e.add("Retrieved", [P("a")])
    p = build_prompt(surf(agent__max_sentences=3), query(), e, [], 3, cache_break=True)
    head, _, tail = p.partition(CACHE_BREAK)
    assert "Lookup:" in head and "Retrieved:" in head and "Turns left" not in head
    assert tail.lstrip().startswith("Turns left: 3.")
    assert "Answer in at most 3 short sentences." in tail
    assert "(none)" in build_prompt(SURF, query(), Evidence(), [], 2)
    e2 = Evidence()
    e2.add("", [])
    assert "(none)" in build_prompt(SURF, query(), e2, [], 2)


# -- propose -------------------------------------------------------------------------------

def test_one_turn_answer():
    llm = Script(["The tariff covers vessels above ten tonnes [t1]."])
    (d, err), e, trace = run(llm)
    assert err is None and [s.passage_marks for s in d.sentences] == [["t1"]]
    assert d.usage.model == "script" and d.raw.startswith("The tariff")
    assert [t.stage for t in trace] == ["draft"] and trace[0].n_out == 1
    assert llm.systems == [SURF.prompt("agent_system")]
    assert "Turns left: 6." in llm.prompts[0] and e.turns_used == 1


def test_search_then_answer_and_trace():
    llm = Script(["SEARCH: pilotage charges movement", "Charges are per movement [t2]."],
                 usd=0.01, cached=7)
    (d, err), e, trace = run(llm)
    assert err is None and d.sentences[0].passage_marks == ["t2"]
    assert "Search: pilotage charges movement" in llm.prompts[1]
    assert [p.unit_id for p in e.passages][0] == "a1" and e.by_mark("t2").unit_id == "a2"
    assert llm.prompts[1].count("[t1]") == 1                                # old passage not repeated
    assert [t.stage for t in trace] == ["draft", "search", "draft"]
    assert trace[1].n_out >= 1 and trace[0].usd == 0.01 and trace[0].tokens_in > 0
    assert "cached=7" in trace[0].note and "cached=7" in trace[2].note
    assert "Turns left: 5." in llm.prompts[1]


def test_open_by_mark_and_by_unit_id():
    llm = Script(["OPEN: t1", "OPEN: a4", "Done [t1]."])
    (d, err), e, trace = run(llm)
    assert err is None
    shown = [p.unit_id for p in e.passages]
    assert shown[0] == "a1" and "a2" in shown                              # neighbour of a1 (radius 1)
    assert "a4" in shown
    assert [t.stage for t in trace] == ["draft", "open", "draft", "open", "draft"]
    assert "Open: t1" in llm.prompts[1] and "Open: a4" in llm.prompts[2]


def test_open_unknown_target_is_nothing_new():
    llm = Script(["OPEN: t9", "Done [t1]."])
    (d, err), e, trace = run(llm)
    assert err is None and "(nothing new)" in llm.prompts[1] and trace[1].n_out == 0


def test_several_queries_in_one_reply_capped():
    llm = Script(["SEARCH: pilotage\nSEARCH: mooring dues\nSEARCH: orchards apples\n"
                  "SEARCH: harbour", "Done [t1]."])
    (_d, err), e, trace = run(llm, surface=surf(agent__queries_per_turn=2))
    assert err is None
    assert [t.stage for t in trace] == ["draft", "search", "search", "draft"]
    assert "Search: pilotage" in llm.prompts[1] and "Search: mooring dues" in llm.prompts[1]
    assert "orchards" not in llm.prompts[1].split("Passages:")[1].lower().replace("orchards produce", "")


def test_actions_on_last_turn_end_unsupported():
    llm = Script(["SEARCH: pilotage", "SEARCH: again"])
    (d, err), e, trace = run(llm, surface=surf(agent__max_turns=2))
    assert d is None and err[:2] == ("abstained", "unsupported")
    assert SURF.prompt("agent_last") in llm.prompts[1]
    assert len(llm.prompts) == 2 and "none left" in trace[-1].note


def test_turn_limit_and_repair_turns_share_a_budget():
    llm = Script(["Answer one [t1].", "Answer two [t1]."])
    (d, err), e, _ = run(llm, surface=surf(agent__max_turns=1))
    assert err is None and e.turns_used == 1
    (d2, err2), _, _ = run(llm, evidence=e, surface=surf(agent__max_turns=1))
    assert d2 is None and err2[1] == "unsupported" and len(llm.prompts) == 1   # no call was made
    # `turns` limits one invocation
    llm2 = Script(["SEARCH: pilotage", "Never reached."])
    (d3, err3), _, _ = run(llm2, turns=1)
    assert d3 is None and err3[1] == "unsupported" and len(llm2.prompts) == 1


def test_feedback_is_appended_after_the_instruction():
    llm = Script(["Fixed [t1]."])
    run(llm, feedback="Failed sentences:\n- x")
    assert llm.prompts[0].rstrip().endswith("Failed sentences:\n- x")


def test_decline_is_a_draft():
    (d, err), _, trace = run(Script(["ABSTAIN no_source: nothing relevant"]))
    assert err is None and d.declined == "no_source" and "declined" in trace[0].note


def test_budget_checked_before_each_call():
    calls = []
    def afford(last):
        calls.append(last)
        return len(calls) < 2
    llm = Script(["SEARCH: pilotage", "Never [t1]."], usd=0.5)
    (d, err), _, trace = run(llm, afford=afford)
    assert d is None and err == ("abstained", "budget", "") and len(llm.prompts) == 1
    assert calls == [None, 0.5]                                           # the last cost is passed
    (d, err), _, _ = run(Script([]), afford=lambda c: False)
    assert err[1] == "budget"


def test_budget_exceeded_and_model_error_in_trace():
    (d, err), _, trace = run(Script([BudgetExceeded("cap")]))
    assert d is None and err[1] == "budget" and trace[0].note == "budget exceeded"
    (d, err), _, trace = run(Script([RuntimeError("boom")]))
    assert d is None and err[:2] == ("abstained", "unsupported")
    assert trace[0].stage == "draft" and trace[0].note.startswith("model error")


def test_cache_break_only_when_supported():
    plain, brk = Script(["A [t1]."]), Script(["A [t1]."], cache_break=True)
    run(plain)
    run(brk)
    assert CACHE_BREAK not in plain.prompts[0]
    head, _, tail = brk.prompts[0].partition(CACHE_BREAK)
    assert "Passages:" in head and tail.lstrip().startswith("Turns left")


def test_search_respects_as_of_date_and_exclusion():
    old = Script(["SEARCH: pilotage fee units", "Fee [t2]."])
    _, e_old, _ = run(old, q=query("What is the pilotage fee?", valid="2021-01-01"))
    new = Script(["SEARCH: pilotage fee units", "Fee [t2]."])
    _, e_new, _ = run(new, q=query("What is the pilotage fee?", valid="2023-01-01"))
    assert "40 units" in " ".join(p.text for p in e_old.passages)
    assert "55 units" not in " ".join(p.text for p in e_old.passages)
    assert "55 units" in " ".join(p.text for p in e_new.passages)
    assert "40 units" not in " ".join(p.text for p in e_new.passages)
    for p in e_old.passages:
        assert (p.valid_from is None or p.valid_from <= "2021-01-01") and (
            p.valid_to is None or "2021-01-01" < p.valid_to)


def test_new_passages_that_do_not_fit_are_not_added():
    # 8000 is the schema minimum: pad the question so little room is left for new passages
    s = surf(agent__max_context_chars=8000)
    q = query("pilotage " + "x" * 7700)
    e = Evidence()
    e.add("", [P("a1", "short first passage")])
    llm = Script(["SEARCH: pilotage charges", "Done [t1]."])
    (d, err), e, trace = run(llm, evidence=e, q=q, surface=s)
    assert err is None
    assert all(len(p) < 8001 for p in llm.prompts[:1])
    assert "did not fit" in trace[1].note and len(e.passages) == 1
    assert "(nothing new)" in llm.prompts[1]


def test_first_prompt_drops_first_retrieval_tail_but_never_lookup():
    s = surf(agent__max_context_chars=8000)
    big = "word " * 700                                                 # about 3500 characters
    e = Evidence()
    e.add("Lookup", [P("l", big)])
    e.add("Retrieved", [P("a", big), P("b", big), P("c", big)])
    llm = Script(["Done [t1]."])
    (d, err), e, _ = run(llm, evidence=e, surface=s)
    assert err is None and len(llm.prompts[0]) <= 8000
    assert [p.unit_id for p in e.passages][0] == "l" and "c" not in [p.unit_id for p in e.passages]
    # lookup alone too long: it is kept, nothing else is left to drop
    e2 = Evidence()
    e2.add("Lookup", [P("l", "word " * 2500)])
    e2.add("Retrieved", [P("a", "x")])
    (d, err), e2, _ = run(Script(["Done [t1]."]), evidence=e2, surface=s)
    assert [p.unit_id for p in e2.passages] == ["l"]
