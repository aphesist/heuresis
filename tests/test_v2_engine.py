"""EngineV2 end to end with scripted generator and judge models (offline)."""
from __future__ import annotations

import json
import threading

import pytest

from heuresis.domains import get_domain
from heuresis.llm import BudgetExceeded, LLMError
from heuresis.model import AsOf, Event, Source, Unit, Usage
from heuresis.store import Store
from heuresis.surface.prompts import passage_line
from heuresis.v2 import EngineV2
from heuresis.v2.engine import trace_failure
from heuresis.v2.locked import calibration as cal_mod
from heuresis.v2.locked.schema import apply_overrides, load_surface, surface_hash

LEI = "urn:lex:br:federal:lei:2020-03-10;1"
OK = "ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: NONE"


def verdict(*words, tail=OK):
    return "\n".join([f"S{i}: {w}" for i, w in enumerate(words, 1)] + [tail])


class Script:
    """Scripted replies in order (a callable reply gets the prompt); records every prompt."""

    id = "script"

    def __init__(self, replies, usd=0.0, cached=0):
        self.replies, self.usd, self.cached = list(replies), usd, cached
        self.prompts, self.systems = [], []

    def complete(self, system, prompt, *, max_tokens=600):
        self.systems.append(system)
        self.prompts.append(prompt)
        i = len(self.prompts) - 1
        if i >= len(self.replies):
            raise RuntimeError("script exhausted")
        r = self.replies[i]
        r = r(prompt) if callable(r) else r
        if isinstance(r, Exception):
            raise r
        return r, Usage(model="script", tokens_in=len(prompt.split()), tokens_out=len(r.split()),
                        tokens_cached=self.cached, usd=self.usd)


def ev(id, unit, op, d, text=None):
    return Event(id=id, unit_id=unit, op=op, date=d, text=text, recorded_at=d)


def text_store(coverage=4):
    s = Store(":memory:")
    s.add(sources=[Source("src", coverage=coverage, authority=1), Source("src2", coverage=coverage, authority=1)],
          units=[Unit("a1", "src", title="Harbour tariff"), Unit("a2", "src", title="Pilotage basis"),
                 Unit("a3", "src", title="Mooring"), Unit("fee", "src", title="Pilotage fee"),
                 Unit("c1", "src", title="Quay hours one"), Unit("c2", "src2", title="Quay hours two")],
          events=[
              ev("e1", "a1", "create", "2019-01-01", "The harbour tariff covers vessels above ten tonnes."),
              ev("e2", "a2", "create", "2019-01-01", "Pilotage charges are levied per movement in the basin."),
              ev("e3", "a3", "create", "2019-01-01", "Mooring dues apply to vessels at the quay overnight."),
              ev("e5", "fee", "create", "2019-01-01", "The pilotage fee is 40 units."),
              ev("e6", "fee", "replace", "2022-01-01", "The pilotage fee is 55 units."),
              ev("e7", "c1", "create", "2019-01-01", "The quay opens at dawn for vessels."),
              ev("e8", "c2", "create", "2019-01-01", "The quay opens at noon for vessels."),
          ])
    s.rebuild()
    return s


def legal_store():
    s = Store(":memory:")
    s.add([Source(LEI, "norm", 3, 3, None, {"title": "Lei nº 1, de 10 de março de 2020"})],
          [Unit(f"{LEI}!art{a}", LEI, "article", None, f"{LEI} art {a}") for a in ("1", "2", "5", "8")],
          [ev("l1", f"{LEI}!art1", "create", "2020-03-10", "Taxa de embarque cobrada por viagem."),
           ev("l2", f"{LEI}!art2", "create", "2020-03-10", "Isenção da taxa de embarque para estudantes."),
           ev("l5", f"{LEI}!art5", "create", "2023-01-01", "Regime novo da taxa de embarque."),
           ev("l8a", f"{LEI}!art8", "create", "2020-03-10", "Prazo antigo de recolhimento da taxa."),
           ev("l8b", f"{LEI}!art8", "replace", "2023-01-01", "Prazo novo de recolhimento da taxa.")])
    s.rebuild()
    return s


def make(store=None, gen=None, judge=None, strong=None, domain="text", over=None, **kw):
    store = store or text_store()
    surface = load_surface(domain=domain)
    if over:
        surface = apply_overrides(surface, {"config": {k.replace("__", "."): v for k, v in over.items()}})
    return EngineV2(store, get_domain(domain), surface=surface, llm=gen, judge_llm=judge,
                    strong_llm=strong, **kw)


Q = "What is the pilotage fee?"
D21, D23 = AsOf(valid="2021-01-01"), AsOf(valid="2023-06-01")


def stages(a):
    return [t.stage for t in a.trace]


# -- the answer path -----------------------------------------------------------------------

def test_one_turn_answer_and_bookkeeping():
    gen = Script(["The pilotage fee is 40 units [t1]."], usd=0.01)
    jd = Script([verdict("SUPPORTED")], usd=0.004)
    a = make(gen=gen, judge=jd).ask(Q, as_of=D21)
    assert a.status == "answered" and a.abstention is None
    assert a.text == "The pilotage fee is 40 units. [t1]"
    assert a.passages[0].unit_id == "fee" and a.passages[0].mark == "t1"
    c = a.claims[0]
    assert (c.label, c.kind, c.passage_marks, c.support) == ("supported", "cited", ["t1"], 0.9)
    assert all(c.checks.values())
    assert a.grade == 0.9
    assert abs(a.usd - 0.014) < 1e-9
    assert stages(a)[0] == "understand" and "lexical" in stages(a) and "retrieve" in stages(a)
    assert stages(a)[-4:] == ["gates", "judge", "decide", "assemble"]
    assert [t.stage for t in a.trace if t.usd] == ["draft", "judge"]
    j = next(t for t in a.trace if t.stage == "judge")
    assert j.tokens_in > 0 and j.tokens_out > 0
    m = a.meta
    assert m["engine"] == "v2" and m["calibrated"] is False and m["tau"] == 0.5
    assert m["verdict"] == {"answer": "DIRECT", "sufficient": "YES", "premise": "OK", "conflict": None}
    assert (m["bound"], m["repairs"], m["escalated"], m["dropped"]) == (0, 0, False, [])
    assert m["confidence"] == 0.9 and len(m["surface_hash"]) == 64 and "calibration" not in m
    assert len(gen.prompts) == 1 and len(jd.prompts) == 1
    assert a.query.as_of.valid == "2021-01-01"


def test_cached_tokens_are_in_the_notes():
    gen, jd = Script(["The pilotage fee is 40 units [t1]."], cached=9), Script([verdict("SUPPORTED")], cached=3)
    a = make(gen=gen, judge=jd).ask(Q, as_of=D21)
    notes = {t.stage: t.note for t in a.trace}
    assert "cached=9" in notes["draft"] and "cached=3" in notes["judge"]


def test_judge_defaults_to_the_generator():
    gen = Script(["The pilotage fee is 40 units [t1].", verdict("SUPPORTED")])
    a = make(gen=gen).ask(Q, as_of=D21)
    assert a.status == "answered" and len(gen.prompts) == 2
    assert gen.systems[0] != gen.systems[1]


def test_search_action_then_answer_passages_equal_what_was_shown():
    gen = Script(["SEARCH: mooring dues quay\nSEARCH: pilotage basis movement",
                  "Mooring dues apply at the quay overnight [t2]."])
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask("Which dues apply overnight?", as_of=D21)
    assert a.status == "answered" and a.claims[0].passage_marks == ["t2"] or a.status == "answered"
    last = gen.prompts[-1]
    for p in a.passages:
        assert passage_line(p.mark, p) in last                       # everything shown is in Answer.passages
    shown_marks = {ln.split("]")[0][1:] for ln in last.splitlines() if ln.startswith("[t")}
    assert shown_marks == {p.mark for p in a.passages}
    assert [p.mark for p in a.passages] == [f"t{i}" for i in range(1, len(a.passages) + 1)]
    assert [t.stage for t in a.trace].count("search") == 2
    assert [t.stage for t in a.trace].count("draft") == 2


def test_open_by_mark_and_by_reference():
    gen = Script(["OPEN: t1", "Done [t1]."])
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert "Open: t1" in gen.prompts[1] and any(t.stage == "open" for t in a.trace)
    # by reference: the legal domain resolves the named article
    gen2 = Script(["OPEN: art. 2º da Lei nº 1/2020", "A taxa tem isenção [t3]."])
    a2 = make(legal_store(), gen=gen2, judge=Script([verdict("SUPPORTED")]), domain="legal_br",
              over={"route__lookup_direct": False, "retrieve__k_first": 3}
              ).ask("Qual é a taxa de embarque?", as_of=AsOf(valid="2021-01-01"))
    assert "Open: art. 2º da Lei nº 1/2020" in gen2.prompts[1]
    assert any(p.unit_id == f"{LEI}!art2" for p in a2.passages)


def test_actions_on_the_last_turn_are_unsupported():
    gen = Script(["SEARCH: mooring", "SEARCH: more"])
    jd = Script([])
    a = make(gen=gen, judge=jd, over={"agent__max_turns": 2}).ask(Q, as_of=D21)
    assert a.status == "abstained" and a.abstention.type == "unsupported"
    assert len(gen.prompts) == 2 and jd.prompts == []


def test_several_queries_one_reply_and_turn_count():
    gen = Script(["SEARCH: mooring\nSEARCH: harbour tariff\nSEARCH: pilotage basis", "Done [t1]."])
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert [t.stage for t in a.trace].count("search") == 3 and a.status == "answered"


# -- lookup and binding --------------------------------------------------------------------

def test_lookup_direct_puts_the_named_provision_first():
    q = "O que dispõe o art. 8º da Lei nº 1/2020 sobre o prazo?"
    gen = Script(["O prazo é o novo [t1]."])
    a = make(legal_store(), gen=gen, judge=Script([verdict("SUPPORTED")]),
             domain="legal_br").ask(q, as_of=AsOf(valid="2024-01-01"))
    assert a.passages[0].unit_id == f"{LEI}!art8" and a.passages[0].mark == "t1"
    assert a.passages[0].text.startswith("Prazo novo")
    assert "lookup" in stages(a) and "Lookup:" in gen.prompts[0]
    off = Script(["x"])
    a2 = make(legal_store(), gen=off, judge=Script([]), domain="legal_br",
              over={"route__lookup_direct": False}).ask(q, as_of=AsOf(valid="2024-01-01"))
    assert "lookup" not in stages(a2) and "Lookup:" not in off.prompts[0]


def test_binding_adds_a_mark_and_the_sentence_passes_references_traced():
    q = "Qual taxa é cobrada por viagem?"
    gen = Script(["O art. 8º da Lei nº 1/2020 fixa o prazo da taxa [t1]."])
    a = make(legal_store(), gen=gen, judge=Script([verdict("SUPPORTED")]), domain="legal_br",
             over={"route__lookup_direct": False, "retrieve__k_first": 3}
             ).ask(q, as_of=AsOf(valid="2024-01-01"))
    assert a.status == "answered", a.abstention
    c = a.claims[0]
    assert c.checks["references_traced"] and len(c.passage_marks) == 2
    bound = a.passages[-1]
    assert bound.unit_id == f"{LEI}!art8" and bound.mark == c.passage_marks[-1]
    assert a.meta["bound"] == 1 and any(t.stage == "bind" for t in a.trace)
    assert a.text.endswith(f"[{c.passage_marks[0]}][{bound.mark}]")


def test_reference_that_does_not_exist_is_not_bound_and_the_sentence_is_removed():
    q = "Qual é a taxa de embarque?"
    gen = Script(["A taxa é cobrada por viagem [t1]. O art. 999 da Lei nº 1/2020 fixa o prazo [t1]."])
    a = make(legal_store(), gen=gen, judge=Script([verdict("SUPPORTED")]), domain="legal_br",
             over={"route__lookup_direct": False, "repair__rounds": 0}
             ).ask(q, as_of=AsOf(valid="2021-01-01"))
    assert a.status == "partial" and "999" not in a.text and a.meta["bound"] == 0
    bad = a.claims[1]
    assert not bad.checks["references_traced"] and bad.label == "unsupported"
    assert a.meta["dropped"][0]["text"].startswith("O art. 999") and "reference" in a.meta["dropped"][0]["reason"]


# -- repair --------------------------------------------------------------------------------

def test_repair_fixes_a_sentence_with_no_mark():
    gen = Script(["The pilotage fee is 40 units.", "The pilotage fee is 40 units [t1]."])
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert a.status == "answered" and a.meta["repairs"] == 1
    assert "Your previous answer:" in gen.prompts[1] and "Failed sentences:" in gen.prompts[1]
    assert load_surface().prompt("repair")[:30] in gen.prompts[1]
    assert [t.stage for t in a.trace if t.stage == "repair"] == ["repair"]
    assert "Turns left: 5." in gen.prompts[1]


def test_repair_keeps_the_better_draft_ties_go_to_the_new_one():
    good = "The pilotage fee is 40 units [t1]. The fee is 41 units [t1]."
    gen = Script([good, "The fee is 41 units [t1]."])                      # new draft: 0 passing < 1
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert a.status == "partial" and a.text.startswith("The pilotage fee is 40")
    note = next(t.note for t in a.trace if t.stage == "repair")
    assert "kept the first draft" in note
    gen2 = Script([good, "The pilotage fee is 40 units [t1]. The fee is 42 units [t1]."])
    a2 = make(gen=gen2, judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert "kept the new draft" in next(t.note for t in a2.trace if t.stage == "repair")   # 1 vs 1: tie


def test_repair_skipped_when_no_turns_remain():
    gen = Script(["The pilotage fee is 40 units."])
    a = make(gen=gen, judge=Script([]), over={"agent__max_turns": 1}).ask(Q, as_of=D21)
    assert len(gen.prompts) == 1 and a.status == "abstained" and a.abstention.type == "unsupported"
    assert next(t.note for t in a.trace if t.stage == "repair").startswith("skipped")
    a2 = make(gen=Script(["The pilotage fee is 40 units."]), judge=Script([]),
              over={"repair__rounds": 0}).ask(Q, as_of=D21)
    assert "repair" not in stages(a2)


def test_repair_turn_may_search_when_turns_remain_and_counts_against_max_turns():
    gen = Script(["The pilotage fee is 40 units.", "SEARCH: mooring dues",
                  "The pilotage fee is 40 units [t1]."])
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")]), over={"agent__max_turns": 3}).ask(Q, as_of=D21)
    assert a.status == "answered" and len(gen.prompts) == 3
    assert "Turns left: 2." in gen.prompts[1] and "Turns left: 1." in gen.prompts[2]


def test_failed_repair_call_does_not_read_as_a_failed_answer():
    gen = Script(["The pilotage fee is 40 units [t1]. The fee is 41 units [t1].", RuntimeError("down")])
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert a.status == "partial" and trace_failure(a.trace) is None


# -- judge and decision --------------------------------------------------------------------

def test_derived_conclusion_follows_or_not():
    reply = "The pilotage fee is 40 units [t1]. So the fee is stated."
    a = make(gen=Script([reply]), judge=Script([verdict("SUPPORTED", "FOLLOWS")])).ask(Q, as_of=D21)
    assert a.status == "answered" and a.text.endswith("So the fee is stated.")
    assert [c.kind for c in a.claims] == ["cited", "derived"] and a.claims[1].label == "supported"
    b = make(gen=Script([reply]), judge=Script([verdict("SUPPORTED", "NOT_FOLLOWS")])).ask(Q, as_of=D21)
    assert b.status == "partial" and b.text == "The pilotage fee is 40 units. [t1]"
    assert b.claims[1].label == "unsupported" and b.meta["dropped"][0]["text"] == "So the fee is stated."
    assert abs(b.grade - 0.72) < 1e-9


def test_judge_verdicts_map_to_typed_outcomes():
    def ask(tail, *words):
        return make(gen=Script(["The pilotage fee is 40 units [t1]."]),
                    judge=Script([verdict(*words, tail=tail)])).ask(Q, as_of=D21)
    a = ask("ANSWER: NO\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: NONE", "SUPPORTED")
    assert a.status == "abstained" and a.abstention.type == "unsupported" and a.text == ""
    a = ask("ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: FALSE\nCONFLICT: NONE", "SUPPORTED")
    assert a.abstention.type == "false_premise"
    a = ask("ANSWER: PARTIAL\nSUFFICIENT: NO\nPREMISE: OK\nCONFLICT: NONE", "SUPPORTED")
    assert a.abstention.type == "no_source"
    a = ask(OK, "NOT_SUPPORTED")
    assert a.abstention.type == "unsupported" and a.claims[0].label == "unsupported"


def test_verified_conflict_is_divergent():
    gen = Script(["The quay opens at dawn [t1]. The quay opens at noon [t2]."])
    jd = Script([verdict("SUPPORTED", "SUPPORTED", tail="ANSWER: PARTIAL\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: t1, t2")])
    a = make(gen=gen, judge=jd).ask("When does the quay open?", as_of=D21)
    assert a.status == "divergent" and a.abstention.type == "conflict"
    assert {p.unit_id for p in a.passages[:2]} == {"c1", "c2"}
    assert a.meta["verdict"]["conflict"] == ["t1", "t2"]


def test_unreadable_judge_abstains():
    a = make(gen=Script(["The pilotage fee is 40 units [t1]."]), judge=Script(["I cannot say."])
             ).ask(Q, as_of=D21)
    assert a.status == "abstained" and a.abstention.type == "unsupported"
    assert a.meta["verdict"]["answer"] == "" and trace_failure(a.trace) is None


def test_model_decline_skips_the_judge():
    jd = Script([])
    a = make(gen=Script(["ABSTAIN no_source: nothing here"]), judge=jd).ask(Q, as_of=D21)
    assert a.status == "abstained" and a.abstention.type == "no_source" and jd.prompts == []


def test_tool_value_is_filled_in_the_text():
    gen = Script(['CALL k1 calc {"expr": "40 * 2"}\nTwice the fee, {k1} units, is charged [t1][k1].'])
    a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert a.status == "answered", (a.abstention, [c.note for c in a.claims])
    assert "80" in a.text and "{k1}" not in a.text and a.tool_results[0].ok
    assert any(t.stage == "tools" for t in a.trace)


# -- calibration ---------------------------------------------------------------------------

def cal_for(surface, tau, **kw):
    return cal_mod.Calibration(tau=tau, alpha=0.05, delta=0.1, n_questions=100, n_answered=60,
                               errors=1, upper=0.049, coverage=0.6,
                               surface_hash=surface_hash(surface), dataset="toy", split="dev",
                               label="containment", created="2026-01-01", **kw)


def run_cal(calibration):
    eng = make(gen=Script(["The pilotage fee is 40 units [t1]."]), judge=Script([verdict("SUPPORTED")]),
               calibration=calibration)
    return eng.ask(Q, as_of=D21)


def test_calibration_tau_applies_only_when_the_surface_hash_matches(tmp_path):
    s = load_surface(domain="text")
    a = run_cal(cal_for(s, 0.95))                      # confidence 0.9 < 0.95
    assert a.status == "abstained" and a.abstention.type == "unsupported"
    assert a.meta["calibrated"] is True and a.meta["tau"] == 0.95
    assert a.meta["calibration"] == {"tau": 0.95, "alpha": 0.05, "delta": 0.1, "n_answered": 60,
                                     "errors": 1, "upper": 0.049, "label": "containment",
                                     "dataset": "toy", "split": "dev"}
    other = cal_mod.Calibration(**{**cal_for(s, 0.95).__dict__, "surface_hash": "0" * 64})
    b = run_cal(other)
    assert b.status == "answered" and b.meta["calibrated"] is False and b.meta["tau"] == 0.5
    assert "calibration" not in b.meta
    c = run_cal(cal_for(s, 0.3))
    assert c.status == "answered" and c.meta["calibrated"] and c.meta["tau"] == 0.3
    # nothing certified: the default threshold applies
    assert run_cal(cal_for(s, None)).meta["calibrated"] is False
    # a directory path is searched with the surface hash
    cal_mod.save(cal_for(s, 0.95), tmp_path / "cal" / "a.json")
    d = run_cal(str(tmp_path / "cal"))
    assert d.status == "abstained" and d.meta["calibrated"] is True
    assert run_cal(str(tmp_path / "missing")).meta["calibrated"] is False


def test_default_calibration_lookup_tolerates_a_missing_directory():
    eng = make(gen=Script(["x"]))
    assert eng.calibration is None or eng.calibration.surface_hash == eng.surface_hash


# -- budget and failures -------------------------------------------------------------------

def test_budget_stop_before_the_judge():
    gen = Script(["The pilotage fee is 40 units [t1]."], usd=0.01)
    jd = Script([verdict("SUPPORTED")])
    a = make(gen=gen, judge=jd).ask(Q, as_of=D21, budget_usd=0.005)
    assert a.status == "abstained" and a.abstention.type == "budget" and jd.prompts == []
    assert make(gen=Script([]), judge=Script([])).ask(Q, as_of=D21, budget_usd=0.0).abstention.type == "budget"
    ok = make(gen=Script(["The pilotage fee is 40 units [t1]."], usd=0.01), judge=Script([verdict("SUPPORTED")], usd=0.01)
              ).ask(Q, as_of=D21, budget_usd=1.0)
    assert ok.status == "answered"


def test_budget_exceeded_from_the_wrapper_is_a_budget_stop():
    a = make(gen=Script([BudgetExceeded("cap")]), judge=Script([])).ask(Q, as_of=D21)
    assert a.abstention.type == "budget" and trace_failure(a.trace)[0] == "budget"
    b = make(gen=Script(["The pilotage fee is 40 units [t1]."]), judge=Script([BudgetExceeded("cap")])
             ).ask(Q, as_of=D21)
    assert b.abstention.type == "budget" and trace_failure(b.trace) == ("budget", "judge: budget exceeded")


def test_model_errors_abstain_unsupported():
    a = make(gen=Script([LLMError("down")]), judge=Script([])).ask(Q, as_of=D21)
    assert a.status == "abstained" and a.abstention.type == "unsupported"
    assert trace_failure(a.trace)[0] == "model" and next(t for t in a.trace if t.stage == "draft").note.startswith("model error")
    b = make(gen=Script(["The pilotage fee is 40 units [t1]."]), judge=Script([ValueError("bad")])
             ).ask(Q, as_of=D21)
    assert b.abstention.type == "unsupported" and trace_failure(b.trace)[0] == "model"
    assert trace_failure([]) is None


# -- retrieval exits -----------------------------------------------------------------------

def test_no_source_not_valid_at_date_and_outside_coverage():
    a = make(gen=Script([]), judge=Script([])).ask("zzzz qqqq", as_of=D21)
    assert a.abstention.type == "no_source"
    b = make(gen=Script([]), judge=Script([])).ask(Q, as_of=AsOf(valid="2018-01-01"))
    assert b.abstention.type == "not_valid_at_date" and b.abstention.searched
    c = make(text_store(coverage=0), gen=Script([]), judge=Script([])).ask(Q, as_of=D21)
    assert c.abstention.type == "outside_coverage"


def test_named_provision_not_in_force_is_not_valid_at_date_naming_it():
    uid = f"{LEI}!art5"
    q = "Segundo o art. 5º da Lei nº 1/2020, qual é o regime da taxa de embarque?"
    # nothing else can be answered: the model declines
    a = make(legal_store(), gen=Script(["ABSTAIN no_source: nada encontrado"]), judge=Script([]),
             domain="legal_br").ask(q, as_of=AsOf(valid="2021-01-01"))
    assert a.status == "abstained" and a.abstention.type == "not_valid_at_date"
    assert uid in a.abstention.searched
    # nothing in the corpus at all at that date: the named unit still wins
    b = make(legal_store(), gen=Script([]), judge=Script([]), domain="legal_br"
             ).ask(q, as_of=AsOf(valid="2019-01-01"))
    assert b.abstention.type == "not_valid_at_date" and uid in b.abstention.searched
    # in force later: the same question is answered
    c = make(legal_store(), gen=Script(["O regime novo está no art. 5º da Lei nº 1/2020 [t1]."]),
             judge=Script([verdict("SUPPORTED")]), domain="legal_br").ask(q, as_of=AsOf(valid="2024-01-01"))
    assert c.status == "answered" and c.passages[0].unit_id == uid


# -- as-of date ----------------------------------------------------------------------------

def test_as_of_selects_the_version_in_force():
    def gen(prompt):
        return "The pilotage fee is 40 units [t1]." if "40 units" in prompt else "The pilotage fee is 55 units [t1]."
    old = make(gen=Script([gen]), judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    new = make(gen=Script([gen]), judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D23)
    assert old.status == new.status == "answered"
    assert "40 units" in old.text and old.passages[0].valid_to == "2022-01-01"
    assert "55 units" in new.text and new.passages[0].valid_from == "2022-01-01"
    assert old.passages[0].seq != new.passages[0].seq
    # a sentence stating the version that is not in force fails the number gate
    bad = make(gen=Script(["The pilotage fee is 40 units [t1].", "The pilotage fee is 40 units [t1]."]),
               judge=Script([])).ask(Q, as_of=D23)
    assert bad.status == "abstained" and not bad.claims[0].checks["numbers_traced"]


def test_a_search_never_surfaces_a_version_not_in_force():
    for date in ("2021-01-01", "2023-06-01"):
        gen = Script(["SEARCH: pilotage fee units", "The pilotage fee is stated [t1]."])
        a = make(gen=gen, judge=Script([verdict("SUPPORTED")])).ask("What do the tariff rules say?", as_of=AsOf(valid=date))
        assert a.passages
        for p in a.passages:
            assert (p.valid_from is None or p.valid_from <= date) and (p.valid_to is None or date < p.valid_to)
        fees = [p for p in a.passages if p.unit_id == "fee"]
        assert len(fees) == 1 and ("40" if date < "2022" else "55") in fees[0].text


# -- escalation ----------------------------------------------------------------------------

def test_escalation_with_a_strong_model_replaces_an_unsupported_result():
    weak = Script(["ABSTAIN unsupported: cannot tell"])
    strong = Script(["The pilotage fee is 40 units [t1]."])
    jd = Script([verdict("SUPPORTED")])
    a = make(gen=weak, judge=jd, strong=strong, over={"route__escalate": True}).ask(Q, as_of=D21)
    assert a.status == "answered" and a.meta["escalated"] is True
    assert "escalate" in stages(a) and len(strong.prompts) == 1
    assert [p.mark for p in a.passages] == [f"t{i}" for i in range(1, len(a.passages) + 1)]
    assert passage_line("t1", a.passages[0]) in strong.prompts[0]        # the evidence is reused
    # not on when the surface says no, when no strong model is given, or when the type differs
    off = make(gen=Script(["ABSTAIN unsupported: x"]), judge=Script([]), strong=Script([]))
    assert off.ask(Q, as_of=D21).meta["escalated"] is False
    nostrong = make(gen=Script(["ABSTAIN unsupported: x"]), judge=Script([]), over={"route__escalate": True})
    assert nostrong.ask(Q, as_of=D21).meta["escalated"] is False
    other = make(gen=Script(["ABSTAIN no_source: x"]), judge=Script([]), strong=Script([]),
                 over={"route__escalate": True})
    assert other.ask(Q, as_of=D21).meta["escalated"] is False


def test_failed_escalation_keeps_the_first_abstention():
    a = make(gen=Script(["ABSTAIN unsupported: x"]), judge=Script([]),
             strong=Script(["ABSTAIN unsupported: still"]), over={"route__escalate": True}).ask(Q, as_of=D21)
    assert a.status == "abstained" and a.meta["escalated"] is True
    b = make(gen=Script(["ABSTAIN unsupported: x"]), judge=Script([]), strong=Script([RuntimeError("no")]),
             over={"route__escalate": True}).ask(Q, as_of=D21)
    assert b.status == "abstained" and b.abstention.type == "unsupported"


# -- open, ingest, threads -----------------------------------------------------------------

def write_corpus(d):
    d.mkdir()
    (d / "sources.jsonl").write_text(json.dumps({"id": "s1", "kind": "text", "authority": 1, "coverage": 4}))
    (d / "units.jsonl").write_text(json.dumps({"id": "fee", "source_id": "s1", "kind": "passage", "title": "Pilotage fee"}))
    (d / "events.jsonl").write_text(json.dumps({"id": "e1", "unit_id": "fee", "op": "create", "date": "2019-01-01",
                                                  "text": "The pilotage fee is 40 units.", "recorded_at": "2019-01-01"}))
    (d / "edges.jsonl").write_text("")
    return str(d)


def test_open_ingest_domain_rules_and_per_thread_engines(tmp_path):
    db = str(tmp_path / "e.db")
    corpus = write_corpus(tmp_path / "corpus")
    eng = EngineV2.open(db, "jsonl", llm=Script(["The pilotage fee is 40 units [t1]."]),
                        judge_llm=Script([verdict("SUPPORTED")]))
    try:
        assert eng.ingest(corpus) and eng.index() == 0
        assert eng.surface.config == load_surface(domain="jsonl").config
        a = eng.ask(Q, as_of=D21)
        assert a.status == "answered"
        assert [p.unit_id for p in eng.search(Q, as_of=D21, k=3)] == ["fee"]
    finally:
        eng.close()
    with pytest.raises(ValueError):
        EngineV2.open(db, "legal_br")                                  # the store holds jsonl
    out = {}

    def work():
        e = EngineV2.open(db, llm=Script(["The pilotage fee is 40 units [t1]."]),
                          judge_llm=Script([verdict("SUPPORTED")]))     # domain from the store
        try:
            out["status"] = e.ask(Q, as_of=D21).status
            out["domain"] = e.domain.name
        finally:
            e.close()
    t = threading.Thread(target=work)
    t.start()
    t.join()
    assert out == {"status": "answered", "domain": "jsonl"}


def test_two_questions_do_not_share_state():
    eng = make(gen=Script(["SEARCH: pilotage basis movement", "Done [t1].", "The pilotage fee is 40 units [t1]."]),
               judge=Script([verdict("SUPPORTED"), verdict("SUPPORTED")]))
    a = eng.ask("Which dues apply overnight?", as_of=D21)
    b = eng.ask(Q, as_of=D21)
    assert len(a.passages) > 1 and [p.mark for p in b.passages][0] == "t1"
    assert b.passages[0].unit_id == "fee"
    assert b.trace is not a.trace and "search" not in stages(b)
