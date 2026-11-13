import json

import pytest

from heuresis.domains import get_domain
from heuresis.ingest import ingest
from heuresis.model import AsOf, Draft, Passage, Sentence, ToolResult
from heuresis.store import Store
from heuresis.v2.locked import gates as G

LEI = "urn:lex:br:federal:lei:2020-03-10;1"
A1, A2, A3 = LEI + "!art1", LEI + "!art2", LEI + "!art3"


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("c")
    rows = {
        "sources.jsonl": [{"id": LEI, "kind": "norm", "authority": 3, "coverage": 4,
                           "meta": {"title": "Lei nº 1, de 10 de março de 2020"}}],
        "units.jsonl": [{"id": u, "source_id": LEI, "kind": "article",
                         "title": f"Lei nº 1, de 10 de março de 2020 — Art. {n}"}
                        for u, n in ((A1, 1), (A2, 2), (A3, 3))],
        "events.jsonl": [
            {"id": "a", "unit_id": A1, "op": "create", "date": "2020-03-10",
             "text": "Art. 1º O zorblax sintético é obrigatório em 30 dias.", "recorded_at": "2020-03-10"},
            {"id": "b", "unit_id": A2, "op": "create", "date": "2020-03-10",
             "text": "Art. 2º O quibblet sintético é facultativo.", "recorded_at": "2020-03-10"},
            {"id": "c", "unit_id": A2, "op": "replace", "date": "2022-01-01",
             "text": "Art. 2º O quibblet sintético é vedado.", "recorded_at": "2022-01-01"},
            {"id": "e", "unit_id": A3, "op": "create", "date": "2023-05-01",
             "text": "Art. 3º O plinth sintético dura 15 dias.", "recorded_at": "2023-05-01"}],
        "edges.jsonl": [],
    }
    for name, rs in rows.items():
        (d / name).write_text("\n".join(json.dumps(r) for r in rs), encoding="utf-8")
    dom = get_domain("legal_br")
    store = Store(str(d / "s.db"))
    ingest(store, str(d), dom)
    yield store, dom
    store.close()


def P(store, unit, mark, date="2021-01-01"):
    v = store.text_at(unit, AsOf(valid=date))
    return Passage(unit, v.seq, v.text, title=store.passage_at(unit, AsOf(valid=date)).title,
                   source_id=LEI, valid_from=v.valid_from, valid_to=v.valid_to, mark=mark)


def S(text, p=(), k=()):
    return Sentence(text, list(p), list(k))


def run(world, sentences, passages, tools=(), question="", date="2021-01-01", domain=None):
    store, dom = world
    return G.check(Draft(sentences=sentences), passages, list(tools), store, AsOf(valid=date),
                   question=question, domain=dom if domain is True else domain)


def test_cited_sentence_passes(world):
    store, _ = world
    c, = run(world, [S("O zorblax é obrigatório em 30 dias.", ["t1"])], [P(store, A1, "t1")])
    assert c.kind == "cited" and c.checks == dict.fromkeys(G.CHECKS, True)
    assert not G.deterministic_failure(c) and G.failure_reason(c) == ""


def test_exists_missing_mark_and_failed_tool(world):
    store, _ = world
    c, = run(world, [S("O zorblax.", ["t9"])], [P(store, A1, "t1")])
    assert not c.checks["exists"] and "t9" in G.failure_reason(c)
    bad = ToolResult("k1", "calc", {}, ok=False, error="x")
    c, = run(world, [S("Vale {k1}.", ["t1"], ["k1"])], [P(store, A1, "t1")], [bad])
    assert not c.checks["exists"]
    c, = run(world, [S("Vale 5.", [], ["k2"])], [], [bad])
    assert not c.checks["exists"]


def test_valid_at_date_uses_the_store(world):
    store, _ = world
    old = P(store, A2, "t1", "2021-01-01")  # seq 0, replaced from 2022-01-01
    c, = run(world, [S("O quibblet é facultativo.", ["t1"])], [old], date="2023-01-01")
    assert not c.checks["valid_at_date"] and c.checks["exists"]
    assert "not in force" in G.failure_reason(c)
    # a passage that lies about its validity is still caught
    lying = P(store, A2, "t1", "2021-01-01")
    lying.valid_to = None
    c, = run(world, [S("O quibblet é facultativo.", ["t1"])], [lying], date="2023-01-01")
    assert not c.checks["valid_at_date"]
    # unit not yet in force
    early = Passage(A3, 0, "Art. 3º O plinth sintético dura 15 dias.", mark="t1")
    c, = run(world, [S("O plinth dura 15 dias.", ["t1"])], [early], date="2021-01-01")
    assert not c.checks["valid_at_date"]


def test_valid_without_store_uses_passage_interval():
    p = Passage("u", 0, "Vale 5 dias.", valid_from="2020-01-01", valid_to="2021-01-01", mark="t1")
    d = Draft(sentences=[S("Vale 5 dias.", ["t1"])])
    assert G.check(d, [p], [], None, AsOf(valid="2020-06-01"))[0].checks["valid_at_date"]
    assert not G.check(d, [p], [], None, AsOf(valid="2021-06-01"))[0].checks["valid_at_date"]


def test_numbers_traced(world):
    store, _ = world
    p = [P(store, A1, "t1")]
    ok, = run(world, [S("Vale 30 dias.", ["t1"])], p)
    assert ok.checks["numbers_traced"]
    bad, = run(world, [S("Vale 45 dias.", ["t1"])], p)
    assert not bad.checks["numbers_traced"] and "45" in G.failure_reason(bad)
    # in the question, in the as-of date (any part and the full string)
    q, = run(world, [S("Em 45 dias.", ["t1"])], p, question="E se forem 45 dias?")
    assert q.checks["numbers_traced"]
    d, = run(world, [S("Em 2021-01-01 e em 1 de janeiro de 2021 vale.", ["t1"])], p)
    assert d.checks["numbers_traced"]
    d, = run(world, [S("Em 2022 vale.", ["t1"])], p)
    assert not d.checks["numbers_traced"]
    # passage title numbers count (Art. 1, Lei nº 1)
    t, = run(world, [S("O art. 1 fala.", ["t1"])], p)
    assert t.checks["numbers_traced"]
    # decimal formats normalise
    r = ToolResult("k1", "calc", {}, ok=True, value="1.200,5")
    c, = run(world, [S("Soma {k1}.", ["t1"], ["k1"])], p, [r])
    assert c.checks["numbers_traced"] and "1.200,5" in c.text
    c, = run(world, [S("Soma 1200.5.", ["t1"], ["k1"])], p, [r])
    assert c.checks["numbers_traced"]
    c, = run(world, [S("Soma 99.", ["t1"], ["k1"])], p, [r])
    assert not c.checks["numbers_traced"]


def test_numbers_inside_resolved_reference_are_skipped(world):
    store, _ = world
    p = [P(store, A1, "t1")]
    p[0].title = ""  # 10 and 2020 are then in neither the text nor the title
    s = "O art. 1º da Lei nº 1, de 10 de março de 2020, fixa 30 dias."
    c, = run(world, [S(s, ["t1"])], p, domain=True)
    assert c.checks["references_traced"] and c.checks["numbers_traced"]
    # without a resolver the same sentence has untraced numbers
    c, = run(world, [S(s, ["t1"])], p)
    assert not c.checks["numbers_traced"] and c.checks["references_traced"]
    # a number outside the reference still fails
    c, = run(world, [S("O art. 1º da Lei nº 1, de 10 de março de 2020, fixa 31 dias.", ["t1"])],
             p, domain=True)
    assert not c.checks["numbers_traced"]


def test_references_traced(world):
    store, _ = world
    p1 = P(store, A1, "t1")
    p2 = P(store, A2, "t2")
    c, = run(world, [S("O art. 2º da Lei 1/2020 diz algo.", ["t1"])], [p1, p2], domain=True)
    assert not c.checks["references_traced"] and "does not cite" in G.failure_reason(c)
    c, = run(world, [S("O art. 2º da Lei 1/2020 diz algo.", ["t2"])], [p1, p2], domain=True)
    assert c.checks["references_traced"]
    c, = run(world, [S("O art. 9º da Lei 1/2020 diz algo.", ["t1"])], [p1], domain=True)
    assert not c.checks["references_traced"] and "unit does not" in G.failure_reason(c)
    c, = run(world, [S("A Lei nº 7, de 1 de março de 2020 diz.", ["t1"])], [p1], domain=True)
    assert not c.checks["references_traced"] and "no such source" in G.failure_reason(c)
    assert G.deterministic_failure(c)


def test_derived_sentence_rules(world):
    store, _ = world
    p = [P(store, A1, "t1")]
    cited = S("O zorblax é obrigatório em 30 dias.", ["t1"])
    c1, c2 = run(world, [cited, S("Logo, 30 dias bastam.")], p)
    assert c2.kind == "derived" and c1.kind == "cited"
    assert c2.checks == dict.fromkeys(G.CHECKS, True)
    # number from a passing cited sentence, the question and the date are allowed; others not
    _, c = run(world, [cited, S("Logo, 31 dias.")], p)
    assert not c.checks["numbers_traced"]
    _, c = run(world, [cited, S("Logo, 31 dias.")], p, question="São 31 dias?")
    assert c.checks["numbers_traced"]
    _, c = run(world, [cited, S("Em 2021 vale.")], p)
    assert c.checks["numbers_traced"]
    # no reference of any kind
    _, c = run(world, [cited, S("Logo, o art. 1º da Lei 1/2020 vale.")], p, domain=True)
    assert not c.checks["references_traced"] and G.deterministic_failure(c)
    _, c = run(world, [cited, S("Logo, o art. 1º da Lei 1/2020 vale.")], p)
    assert c.checks["references_traced"]  # no resolver


def test_derived_needs_a_passing_cited_sentence(world):
    store, _ = world
    p = [P(store, A1, "t1")]
    c, = run(world, [S("Logo, vale.")], p)
    assert not c.checks["exists"] and "no cited sentence" in G.failure_reason(c)
    # the only cited sentence fails its number gate
    a, b = run(world, [S("Vale 99 dias.", ["t1"]), S("Logo, vale.")], p)
    assert not a.checks["numbers_traced"] and not b.checks["exists"]
    # a number only a failing cited sentence has is not allowed in the derived one
    a, ok, d = run(world, [S("Vale 99 dias.", ["t1"]), S("Vale 30 dias.", ["t1"]),
                           S("Logo, 99 dias.")], p)
    assert not d.checks["numbers_traced"]
    # derived sentences never depend on other derived sentences
    _, d1, d2 = run(world, [S("Vale 30 dias.", ["t1"]), S("Logo, vale."), S("Logo, 7 dias.")], p)
    assert d1.checks["numbers_traced"] and not d2.checks["numbers_traced"]


def test_check_never_raises_on_malformed_input():
    class Weird:
        text = None
        passage_marks = None
        tool_marks = None

    out = G.check(Draft(sentences=[Weird(), S("ok.", ["t1"])]), [Passage("u", 0, "x", mark="t1")],
                  [], None, AsOf(valid="2020-01-01"))
    assert len(out) == 2
    assert all(isinstance(c.checks, dict) for c in out)
    assert G.deterministic_failure(out[0])
    assert G.check(Draft(), [], [], None, AsOf()) == []


class BrokenStore:
    def text_at(self, *a):
        raise RuntimeError("boom")


def test_store_error_is_a_failing_sentence():
    p = Passage("u", 0, "x", mark="t1")
    c, = G.check(Draft(sentences=[S("x.", ["t1"])]), [p], [], BrokenStore(), AsOf(valid="2020-01-01"))
    assert G.deterministic_failure(c) and "could not be checked" in c.note


def test_failure_reason_without_note():
    from heuresis.model import Claim
    c = Claim("x", checks={"exists": True, "valid_at_date": True, "numbers_traced": False,
                           "references_traced": False})
    r = G.failure_reason(c)
    assert "number" in r and "reference" in r
    assert G.failure_reason(Claim("x", checks=dict.fromkeys(G.CHECKS, True))) == ""
    assert not G.deterministic_failure(Claim("x"))
