"""Citation binding with an invented norm store (no real legal text)."""
from __future__ import annotations

import pytest

from heuresis.domains import get_domain
from heuresis.model import AsOf, Draft, Event, Passage, Sentence, Source, Unit
from heuresis.store import Store
from heuresis.v2.agent import Evidence
from heuresis.v2.bind import bind

LEI = "urn:lex:br:federal:lei:2020-03-10;1"


@pytest.fixture
def store():
    st = Store(":memory:")
    st.add([Source(LEI, "norm", 3, 3, None, {"title": "Lei nº 1, de 10 de março de 2020"})],
           [Unit(f"{LEI}!art{a}", LEI, "article", None, f"{LEI} art {a}") for a in ("1", "2", "8")],
           [Event("e1", f"{LEI}!art1", "create", "2020-03-10", "texto do artigo um", "2020-03-10"),
            Event("e2", f"{LEI}!art2", "create", "2020-03-10", "texto do artigo dois", "2020-03-10"),
            Event("e8a", f"{LEI}!art8", "create", "2020-03-10", "texto antigo do artigo oito", "2020-03-10"),
            Event("e8b", f"{LEI}!art8", "replace", "2023-01-01", "texto novo do artigo oito", "2023-01-01")])
    st.rebuild()
    return st


DOM = get_domain("legal_br")


def shown(store, uid, date="2021-01-01"):
    return store.passage_at(uid, AsOf(valid=date))


def draft_of(*sents):
    return Draft(sentences=[Sentence(t, list(m)) for t, m in sents])


def test_binds_named_provision_not_shown(store):
    ev = Evidence()
    ev.add("", [shown(store, f"{LEI}!art1")])
    d = draft_of(("O art. 8º da Lei nº 1/2020 trata disso.", ["t1"]))
    notes = bind(d, ev, store, DOM, AsOf(valid="2021-01-01"))
    assert d.sentences[0].passage_marks == ["t1", "t2"]
    assert ev.by_mark("t2").unit_id == f"{LEI}!art8" and ev.by_mark("t2").text.startswith("texto antigo")
    assert [lab for lab, _ in ev.rounds] == ["", "Bound"]
    assert len(notes) == 1 and "t2" in notes[0]


def test_bound_version_is_the_one_in_force_at_the_date(store):
    ev = Evidence()
    d = draft_of(("O art. 8º da Lei nº 1/2020 trata disso.", []))
    bind(d, ev, store, DOM, AsOf(valid="2024-01-01"))
    assert ev.passages[0].text.startswith("texto novo")


def test_already_cited_or_shown_is_not_added_twice(store):
    ev = Evidence()
    ev.add("", [shown(store, f"{LEI}!art8"), shown(store, f"{LEI}!art2")])
    d = draft_of(("O art. 8º da Lei nº 1/2020 trata disso.", ["t1"]),         # cited: nothing to do
                 ("O art. 2º da Lei nº 1/2020 também.", ["t1"]))              # shown, not cited
    notes = bind(d, ev, store, DOM, AsOf(valid="2021-01-01"))
    assert d.sentences[0].passage_marks == ["t1"]
    assert d.sentences[1].passage_marks == ["t1", "t2"] and len(ev.passages) == 2
    assert len(notes) == 1


def test_missing_reference_is_not_bound(store):
    ev = Evidence()
    ev.add("", [shown(store, f"{LEI}!art1")])
    d = draft_of(("O art. 999 da Lei nº 1/2020 trata disso.", ["t1"]),        # unit does not exist
                 ("O art. 1º da Lei nº 77/2020 trata disso.", ["t1"]))        # norm does not exist
    notes = bind(d, ev, store, DOM, AsOf(valid="2021-01-01"))
    assert notes == [] and len(ev.passages) == 1
    assert [s.passage_marks for s in d.sentences] == [["t1"], ["t1"]]


def test_unit_not_in_force_is_not_bound(store):
    ev = Evidence()
    d = draft_of(("O art. 1º da Lei nº 1/2020 trata disso.", []))
    notes = bind(d, ev, store, DOM, AsOf(valid="2019-01-01"))                 # before creation
    assert notes == [] and ev.passages == [] and d.sentences[0].passage_marks == []


def test_no_resolver_is_a_noop(store):
    class Plain:
        name = "plain"
    ev = Evidence()
    d = draft_of(("O art. 8º da Lei nº 1/2020 trata disso.", []))
    assert bind(d, ev, store, Plain(), AsOf(valid="2021-01-01")) == []
    assert bind(d, ev, store, None, AsOf(valid="2021-01-01")) == []
    assert ev.passages == []
