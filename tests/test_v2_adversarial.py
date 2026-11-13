"""Regression tests for the defects of the adversarial review of the v2 answer pipeline.
Invented text only. Each test is a former reproduction script turned into an assertion."""
from __future__ import annotations

import pytest

from heuresis.model import AsOf, Draft, Event, Passage, Scope, Sentence, Source, Unit, Usage
from heuresis.store import Store
from heuresis.v2.agent import Evidence
from heuresis.v2.bind import bind
from heuresis.v2.locked import judge as J
from heuresis.v2.retrieve import lookup, open_unit
from test_v2_engine import (D21, LEI, OK, Q, Script, ev, legal_store, make, text_store,
                            verdict)

QUAY = "When does the quay open for vessels?"
CONFLICT = "ANSWER: PARTIAL\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: t1, t2"


def ask(gen, jd=None, q=Q, as_of=D21, store=None, scope=None, **kw):
    g = Script(gen if isinstance(gen, list) else [gen])
    j = Script(jd if isinstance(jd, list) else [jd if jd is not None else verdict("SUPPORTED")])
    a = make(store=store, gen=g, judge=j, **kw).ask(q, as_of=as_of, scope=scope)
    return a, g, j


def failed(a):
    return [k for c in a.claims for k, v in c.checks.items() if not v]


# -- 1. tool marks and placeholders (t2, t3, t18) ------------------------------------------------

def test_tool_only_sentence_is_derived_and_laundering_fails():
    a, _, _ = ask('CALL k1 calc {"expr": "99"}\nThe pilotage fee is {k1} units [k1].')
    assert a.status == "abstained"
    assert a.claims[0].kind == "derived" and "numbers_traced" in failed(a)
    assert "k1" in a.claims[0].note and "99" in a.claims[0].note


def test_failed_or_missing_tool_never_reaches_the_answer():
    for gen in ('CALL k1 calc {"expr": "2+"}\nThe pilotage fee is {k1} units [t1].',
                'The pilotage fee is {k9} units [t1].',
                'CALL k1 calc {"expr": "2+"}\nThe pilotage fee is 40 units [t1].\nTotal is {k1}.',
                'CALL k1 calc {"expr": "2+"}\nThe pilotage fee is 40 units [t1].\nTotal is 3 [k1].'):
        a, _, _ = ask(gen, [verdict("SUPPORTED", "FOLLOWS")])
        assert not a.claims[-1].checks["exists"], gen
        assert "[not checked]" not in a.text and all("[not checked]" not in c.text for c in a.claims)
        assert all(c.label == "unsupported" for c in a.claims[-1:])


def test_derived_placeholder_is_filled_for_the_judge_and_args_are_traced():
    a, _, j = ask('CALL k1 calc {"expr": "40 + 40"}\nThe pilotage fee is 40 units [t1].\n'
                  'Twice that is {k1} units.', [verdict("SUPPORTED", "FOLLOWS")])
    assert a.status == "answered" and "Twice that is 80 units." in j.prompts[0]
    assert "80" in a.text and "{k1}" not in a.text
    # invented operands
    a, _, j = ask('CALL k1 calc {"expr": "99999"}\nThe pilotage fee is 40 units [t1].\n'
                  'So the grand total is {k1} units.', [verdict("SUPPORTED")])
    assert a.status == "partial" and "99999" not in a.text
    assert a.claims[1].kind == "derived" and not a.claims[1].checks["numbers_traced"]
    assert "k1" in a.claims[1].note
    assert "99999" not in j.prompts[0]  # the judge never saw the invented value
    a, _, _ = ask('CALL k1 calc {"expr": "40*1000"}\nThe pilotage fee is 40 units [t1].\n'
                  'Over the period it totals {k1}.', [verdict("SUPPORTED")])
    assert a.status == "partial" and "1000" in a.claims[1].note


def test_cited_sentence_with_a_tool_value_needs_traced_arguments():
    a, _, _ = ask('CALL k1 calc {"expr": "99"}\nThe pilotage fee is {k1} units [t1][k1].')
    assert a.status == "abstained" and "numbers_traced" in failed(a)
    a, _, _ = ask('CALL k1 calc {"expr": "40"}\nThe pilotage fee is {k1} units [t1][k1].')
    assert a.status == "answered" and "40 units" in a.text


def test_duplicate_or_colliding_tool_marks_fail_closed():
    a, _, _ = ask('CALL k1 calc {"expr": "99"}\nCALL k1 calc {"expr": "2+"}\n'
                  'The pilotage fee is 99 units [k1] and 40 [t1].')
    assert a.status == "abstained"
    a, _, _ = ask('CALL t1 calc {"expr": "99"}\nThe pilotage fee is 99 units [t1].')
    assert a.status == "abstained"


# -- 4. the number gate (t3, t10, t16) -----------------------------------------------------------

@pytest.mark.parametrize("sentence,ok", [
    ("The pilotage fee is 1 units [t1].", False),
    ("The pilotage fee is 31 units [t1].", False),
    ("The pilotage fee is 12 units [t1].", False),
    ("The pilotage fee is 4 0 units [t1].", False),
    ("The pilotage fee is 4e1 units [t1].", False),
    ("The pilotage fee is 55 units [t1].", False),
    ("The pilotage fee is 5⁵ units [t1].", False),
    ("The pilotage fee is 40 units on 31/12/2021 [t1].", True),
    ("The pilotage fee is 40 units on 2021-12-31 [t1].", True),
    ("The pilotage fee is 40 units in 2021 [t1].", True),
    ("The pilotage fee is 40 units on day 31 of 12 2021 [t1].", True),
    ("The pilotage fee is 40 units on day 31 [t1].", False),
])
def test_as_of_date_digits_and_malformed_numbers(sentence, ok):
    a, _, _ = ask(sentence, as_of=AsOf(valid="2021-12-31"))
    assert (a.status == "answered") is ok, (sentence, a.claims[0].note)


def test_no_as_of_date_means_no_date_digits_and_no_clock():
    for n in ("13", "11", "2026"):
        a, _, _ = ask(f"The pilotage fee is {n} units [t1].", as_of=None, q=Q)
        assert not a.claims or "numbers_traced" in failed(a), n


def test_number_words_are_left_to_the_judge():
    # stated limit: numbers written in words are not detected by the code
    a, _, _ = ask("The pilotage fee is fifty-five units [t1].")
    assert a.status == "answered"


LEGAL_Q = "Qual é a taxa de embarque?"
LD = AsOf(valid="2021-01-01")


def legal(gen, jd=None):
    g = Script([gen] if isinstance(gen, str) else gen)
    j = Script(jd or [verdict("SUPPORTED")])
    return make(legal_store(), gen=g, judge=j, domain="legal_br").ask(LEGAL_Q, as_of=LD)


def test_reference_digits_are_not_masked():
    a = legal("Conforme o art. 1º da Lei nº 1/2020, a taxa de embarque é cobrada por viagem [t1].")
    assert a.status == "answered", [c.note for c in a.claims]
    a = legal("Conforme o art. 1º, § 7º, inciso XII da Lei nº 1/2020, a taxa de embarque é cobrada "
              "por viagem [t1].")
    assert a.status == "abstained" and "7" in a.claims[0].note
    a = legal("Conforme o art. 99 da Lei nº 1/2020, a taxa de embarque é cobrada por viagem [t1].")
    assert a.status == "abstained"
    a = legal("A taxa de embarque é cobrada por viagem segundo a Lei nº 2/2021 [t1].")
    assert a.status == "abstained"


# -- 2. derived numbers after the judge (t13, t18) -----------------------------------------------

def test_derived_number_of_a_judge_dropped_sentence_is_dropped():
    a, _, _ = ask("The tariff covers 40 vessels [t1]. Mooring dues apply overnight [t4]. "
                  "So the pilotage fee is 40 units.",
                  [verdict("NOT_SUPPORTED", "SUPPORTED", "FOLLOWS")])
    assert a.status == "partial" and "40" not in a.text
    assert "number from a removed sentence" in a.claims[2].note and a.claims[2].label == "unsupported"
    assert any("number from a removed sentence" in d["reason"] or d["reason"] for d in a.meta["dropped"])


# -- 3. divergent (t6) ---------------------------------------------------------------------------

def test_divergent_keeps_no_sentence_and_names_both_sides():
    a, _, _ = ask("The quay opens at dawn [t1]. The quay opens at noon [t2].",
                  [verdict("SUPPORTED", "SUPPORTED", tail=CONFLICT)], q=QUAY)
    assert a.status == "divergent" and a.text == "" and a.grade == 0.0
    assert a.abstention.type == "conflict"
    assert "Quay hours one" in a.abstention.message and "Quay hours two" in a.abstention.message
    assert "2019-01-01" in a.abstention.message
    assert len(a.abstention.searched) == 2 and "Quay hours one" in a.abstention.searched[0]
    assert all(c.label for c in a.claims)
    assert a.meta["confidence"] == 0.0


def test_conflict_with_a_side_nobody_cited_is_not_divergent():
    tail = "ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: t1, t2"
    a, _, _ = ask("The quay opens at dawn [t1].", [verdict("SUPPORTED", tail=tail)], q=QUAY)
    assert a.status == "answered"
    # the second side's sentence failed a gate: the judge never saw that passage
    a, _, _ = ask("The quay opens at dawn [t1]. The quay opens at 9 [t2].",
                  [verdict("SUPPORTED", tail=tail)], q=QUAY)
    assert a.status == "partial" and a.text.startswith("The quay opens at dawn")
    for t in ("CONFLICT: t1, t1", "CONFLICT: t1, t99", "CONFLICT: t1, t5"):
        a, _, _ = ask("The quay opens at dawn [t1].",
                      [verdict("SUPPORTED", tail=tail.replace("CONFLICT: t1, t2", t))], q=QUAY)
        assert a.status != "divergent"


def test_divergent_message_is_not_replaced_by_the_domain_text():
    a, _, _ = ask("The quay opens at dawn [t1]. The quay opens at noon [t2].",
                  [verdict("SUPPORTED", "SUPPORTED", tail=CONFLICT)], q=QUAY, store=text_store())
    assert "Quay hours one" in a.abstention.message


# -- 5. the judge parser (t4, t6) ----------------------------------------------------------------

@pytest.mark.parametrize("tail,status,kind", [
    ("ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: FALSE\nPREMISE: OK\nCONFLICT: NONE", "abstained", "false_premise"),
    ("ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nPREMISE: FALSE\nCONFLICT: NONE", "abstained", "false_premise"),
    ("ANSWER: DIRECT\nANSWER: NO\nSUFFICIENT: YES\nPREMISE: OK", "abstained", "unsupported"),
    ("ANSWER: DIRECT\nSUFFICIENT: YES\nSUFFICIENT: NO\nPREMISE: OK", "abstained", "unsupported"),
    ("ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: t1, t2\nCONFLICT: NONE", "abstained", "unsupported"),
    ("ANSWER: DIRECT\nSUFFICIENT: YES", "abstained", "unsupported"),
    ("ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: maybe", "abstained", "unsupported"),
    ("ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: NONE (t1 and t2 agree)", "answered", None),
    ("ANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK", "answered", None),
])
def test_judge_parser_fails_closed(tail, status, kind):
    a, _, _ = ask("The quay opens at dawn [t1].", [verdict("SUPPORTED", tail=tail)], q=QUAY)
    assert a.status == status and (kind is None or a.abstention.type == kind)


def test_two_verdicts_for_the_same_sentence_are_unreadable():
    v = J.parse_verdict("S1: SUPPORTED\nS1: NOT_SUPPORTED\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK", 1)
    assert v.readable is False


def test_long_passage_tail_reaches_the_judge():
    s = Store(":memory:")
    s.add(sources=[Source("src", coverage=4, authority=1)], units=[Unit("big", "src", title="Long rule")],
          events=[ev("e", "big", "create", "2019-01-01",
                     "Pilotage preamble. " + "Lorem ipsum harbour text. " * 120
                     + "The pilotage fee is 40 units.")])
    s.rebuild()
    a, _, j = ask("The pilotage fee is 40 units [t1].", store=s)
    assert a.status == "answered" and "The pilotage fee is 40 units." in j.prompts[0]
    assert len(a.passages[0].text) > 2500


# -- 6. scope (t8) -------------------------------------------------------------------------------

def ids(a):
    return [(p.unit_id, p.source_id) for p in a.passages]


def test_open_never_brings_an_out_of_scope_passage():
    s = text_store()
    sc = Scope(source_ids=("src",))
    a, _, _ = ask(["OPEN: c2", "The quay opens at noon [t1]."], store=s, scope=sc)
    assert all(src == "src" for _, src in ids(a)) and ("c2", "src2") not in ids(a)
    sc2 = Scope(source_ids=("src2",))
    a, _, _ = ask(["OPEN: c1", "The pilotage fee is 40 units [t1]."], store=s, scope=sc2)
    assert all(src == "src2" for _, src in ids(a))
    # adjacency never crosses the scope: opening c1 (src) in scope src2 shows nothing of src
    a, _, _ = ask(["OPEN: t1", "The quay opens at noon [t1]."], store=s, scope=sc2)
    assert all(src == "src2" for _, src in ids(a))


def test_scope_kinds_and_prefix():
    s = Store(":memory:")
    s.add([Source("src", "norm", 3, 3, None, {})],
          [Unit("a!art1", "src", "article", None, "Art 1"), Unit("a!sec1", "src", "section", None, "Sec 1")],
          [Event("e1", "a!art1", "create", "2020-01-01", "texto um", "2020-01-01"),
           Event("e2", "a!sec1", "create", "2020-01-01", "texto dois", "2020-01-01")])
    s.rebuild()
    d = AsOf(valid="2021-01-01")
    assert [p.unit_id for p in open_unit(s, "a!art1", d, 3, Scope(kinds=("article",)))] == ["a!art1"]
    assert open_unit(s, "a!sec1", d, 3, Scope(kinds=("article",))) == []
    assert open_unit(s, "a!sec1", d, 3, Scope(unit_prefix="a!art")) == []
    assert len(open_unit(s, "a!art1", d, 3)) == 2


def test_lookup_and_bind_drop_out_of_scope_units():
    s = legal_store()
    from heuresis.domains import get_domain
    dom = get_domain("legal_br")
    d = AsOf(valid="2021-01-01")
    text = "Conforme o art. 1º da Lei nº 1/2020."
    assert len(lookup(s, dom, text, d)[0]) == 1
    assert lookup(s, dom, text, d, Scope(source_ids=("other",)))[0] == []
    assert len(lookup(s, dom, text, d, Scope(source_ids=(LEI,)))[0]) == 1
    # binding
    ev1 = Evidence()
    ev1.add("", [s.passage_at(f"{LEI}!art2", d)])
    dr = Draft(sentences=[Sentence("O art. 1º da Lei nº 1/2020 trata disso.", ["t1"])])
    assert bind(dr, ev1, s, dom, d, Scope(kinds=("section",))) == []
    assert dr.sentences[0].passage_marks == ["t1"] and len(ev1.passages) == 1
    assert len(bind(dr, ev1, s, dom, d, Scope(kinds=("article",)))) == 1


def test_engine_question_scope_reaches_lookup_and_bind():
    gen = ["Conforme o art. 2º da Lei nº 1/2020, a taxa de embarque é cobrada por viagem [t1]."]
    a = make(legal_store(), gen=Script(gen), judge=Script([verdict("SUPPORTED")]),
             domain="legal_br").ask(LEGAL_Q, as_of=LD, scope=Scope(source_ids=("elsewhere",)))
    assert a.passages == [] or all(p.source_id == "elsewhere" for p in a.passages)
    assert a.status == "abstained"


# -- 7. confidence discount (t18) ----------------------------------------------------------------

def test_gate_failure_discounts_confidence():
    a, _, _ = ask("The pilotage fee is 40 units [t1]. The tariff costs 77 units [t1].")
    assert a.status == "partial" and a.grade == pytest.approx(0.72)


# -- 8. robustness (t7) --------------------------------------------------------------------------

class Weird:
    id = "weird"

    def __init__(self, out):
        self.out = out

    def complete(self, system, prompt, *, max_tokens=600):
        return self.out


class NoFields:
    pass


@pytest.mark.parametrize("out", [("The pilotage fee is 40 units [t1].", None),
                                 ("The pilotage fee is 40 units [t1].", NoFields()), None, ("ok",)])
def test_generator_with_no_usage_ends_in_model_error(out):
    a = make(gen=Weird(out), judge=Script([verdict("SUPPORTED")])).ask(Q, as_of=D21)
    assert a.status == "abstained" and a.abstention.type == "unsupported"
    assert any(t.stage == "draft" and t.note.startswith("model error") for t in a.trace)


@pytest.mark.parametrize("out", [(None, Usage()), ("S1: SUPPORTED\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK", None),
                                 ("S1: SUPPORTED\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK", NoFields()),
                                 None, 5])
def test_judge_with_no_usage_is_unreadable_or_a_model_error(out):
    a = make(gen=Script(["The pilotage fee is 40 units [t1]."]), judge=Weird(out)).ask(Q, as_of=D21)
    assert a.status == "abstained" and a.abstention.type == "unsupported" and a.text == ""
