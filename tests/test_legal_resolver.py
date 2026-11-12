"""Free-text citation resolver, the references_traced gate and the optional-resolver protocol.
Synthetic norms ("Lei nº 1", "Código de Teste") only."""
import pytest

from heuresis.domains import get_domain
from heuresis.domains.legal_br import acronym_of, explicit_acronyms, fold
from heuresis.interfaces import Reference, domain_references
from heuresis.model import Claim, Event, Passage, Source, Unit
from heuresis.references import reference_problems, trace_claims
from heuresis.store import Store

LEI = "urn:lex:br:federal:lei:2020-03-10;1"
LEI2 = "urn:lex:br:federal:lei:1999-01-01;250"
COD = "urn:lex:br:federal:lei:1966-10-25;5172"
IN = "urn:lex:br:rfb:instrucao.normativa:2024-03-05;2178"
DEC = "urn:lex:br:federal:decreto:2018-11-22;9580"
CF = "urn:lex:br:federal:constituicao:1988-10-05;1988"


@pytest.fixture
def store():
    st = Store(":memory:")
    srcs = [Source(LEI, "norm", 3, 3, None, {"title": "Lei nº 1, de 10 de março de 2020"}),
            Source(LEI2, "norm", 3, 3, None, {"title": "Lei nº 250, de 1º de janeiro de 1999"}),
            Source(COD, "norm", 3, 3, None, {"title": "Lei nº 5.172", "names": ["Código de Teste Nacional (CTN)"],
                                             "aliases": ["CTN"]}),
            Source(IN, "norm", 3, 3, None, {"title": "Instrução Normativa RFB nº 2.178"}),
            Source(DEC, "norm", 3, 3, None, {"title": "Decreto nº 9.580", "aliases": ["RIR/2018"]}),
            Source(CF, "norm", 5, 3, None, {"title": "Constituição", "names": ["Constituição Federal de 1988"]}),
            Source("doc:other", "text", 0, 3, None, {})]
    units, events = [], []
    for urn, arts in ((LEI, ["1", "2", "8"]), (LEI2, ["1"]), (COD, ["43"]), (IN, ["2"]), (DEC, ["677"]), (CF, ["153"])):
        for a in arts:
            uid = f"{urn}!art{a}"
            units.append(Unit(uid, urn, "article", None, f"{urn} art {a}"))
            events.append(Event(f"{uid}@2000", uid, "create", "2000-01-01", f"texto do art. {a}", "2000-01-01"))
    st.add(srcs, units, events)
    st.rebuild()
    return st


def refs(store, text):
    return [(r.status, r.unit, r.container) for r in get_domain("legal_br").resolve_references(text, store)]


def test_article_then_norm(store):
    assert refs(store, "art. 8º, II, da Lei nº 1/2020") == [("resolved", "8", LEI)]
    assert refs(store, "os arts. 1º, 2º e 8º da Lei 1, de 2020") == [("resolved", "1", LEI), ("resolved", "2", LEI), ("resolved", "8", LEI)]


def test_norm_then_article_and_aliases(store):
    assert refs(store, "Lei 1, de 2020, art. 2") == [("resolved", "2", LEI)]
    assert refs(store, "CTN, art. 43") == [("resolved", "43", COD)]
    assert refs(store, "Constituição, art. 153, III") == [("resolved", "153", CF)]
    assert refs(store, "Constituição Federal, art. 153") == [("resolved", "153", CF)]
    assert refs(store, "Decreto nº 9.580/2018 (RIR/2018), art. 677") == [("resolved", "677", DEC)]
    assert refs(store, "IN RFB nº 2.178/2024, art. 2º") == [("resolved", "2", IN)]
    assert refs(store, "Instrução Normativa RFB nº 2.178, de 5 de março de 2024, art. 2º") == [("resolved", "2", IN)]


def test_not_found_statuses(store):
    assert refs(store, "Lei nº 1/2020, art. 999") == [("unit_not_found", "999", LEI)]
    assert refs(store, "Lei nº 1/2021, art. 1")[0][0] == "container_not_found"  # wrong year
    assert refs(store, "Lei nº 777/2020, art. 1")[0][0] == "container_not_found"
    r = get_domain("legal_br").resolve_references("Lei nº 777/2020, art. 1", store)[0]
    assert r.meta == {"kind": "lei", "number": "777", "year": "2020"} and r.unit_ids == ()
    assert refs(store, "Lei nº 1/2020 trata disso") == [("norm_only", "", LEI)]


def test_two_citations_and_bare_articles(store):
    out = refs(store, "O art. 8º da Lei nº 1/2020 e o art. 1º da Lei nº 250/1999 tratam disso.")
    assert out == [("resolved", "8", LEI), ("resolved", "1", LEI2)]
    assert refs(store, "O art. 5º trata disso.") == []   # no norm named: nothing to resolve
    assert refs(store, "Em 2020 houve 3 leis.") == []


def test_fold_keeps_length_and_acronyms():
    s = "Constituição, órgão ÇÃ"
    assert len(fold(s)) == len(s) and fold(s).startswith("constituicao")
    assert acronym_of("Código de Processo Civil") == "CPC" and acronym_of("Altera a legislação") == ""
    assert explicit_acronyms("Código Tributário Nacional (CTN)") == ["CTN"]


def test_protocol_default_finds_nothing(store):
    class Plain:  # a domain without a resolver
        name = "plain"
    assert domain_references(Plain(), "art. 8º da Lei nº 1/2020", store) == []
    assert [r.status for r in domain_references(get_domain("legal_br"), "Lei nº 1/2020, art. 1", store)] == ["resolved"]
    assert not hasattr(get_domain("jsonl"), "resolve_references")


def _passage(uid, mark):
    return Passage(unit_id=uid, seq=0, text="t", source_id=uid.split("!")[0], mark=mark)


def test_reference_problems():
    cited = [_passage(LEI + "!art8", "t1")]
    ok = Reference("x", 0, 1, "resolved", LEI, "8", (LEI + "!art8",))
    other = Reference("x", 0, 1, "resolved", LEI, "2", (LEI + "!art2",))
    assert reference_problems(ok, cited) == ""
    assert "does not cite" in reference_problems(other, cited)
    assert "does not exist" in reference_problems(Reference("x", 0, 1, "unit_not_found", LEI, "9"), cited) or \
        "unit does not" in reference_problems(Reference("x", 0, 1, "unit_not_found", LEI, "9"), cited)
    assert "no such source" in reference_problems(Reference("x", 0, 1, "container_not_found"), cited)
    assert reference_problems(Reference("x", 0, 1, "norm_only", LEI), cited) == ""
    assert reference_problems(Reference("x", 0, 1, "norm_only", COD), cited) != ""
    chunk = [_passage(LEI + "!art8!p2", "t1")]  # a chunk of a long article counts as the article
    assert reference_problems(ok, chunk) == ""


def test_trace_claims_marks_failures_and_skips_plain_domains(store):
    ps = [_passage(LEI + "!art8", "t1"), _passage(LEI + "!art2", "t2")]
    good = Claim("Conforme o art. 8º da Lei nº 1/2020 [t1].", passage_marks=["t1"])
    uncited = Claim("Conforme o art. 2º da Lei nº 1/2020 [t1].", passage_marks=["t1"])
    invented = Claim("Conforme o art. 99 da Lei nº 1/2020 [t1].", passage_marks=["t1"])
    plain = Claim("Sem referência nenhuma [t1].", passage_marks=["t1"])
    claims = [good, uncited, invented, plain]
    assert trace_claims(claims, ps, get_domain("legal_br"), store) == 2
    assert good.checks["references_traced"] and plain.checks["references_traced"]
    assert not uncited.checks["references_traced"] and uncited.checks["exists"] is False
    assert "references_traced" in invented.note
    class Plain:
        name = "plain"
    c = Claim("art. 99 da Lei nº 1/2020 [t1]", passage_marks=["t1"])
    assert trace_claims([c], ps, Plain(), store) == 0 and "references_traced" not in c.checks
