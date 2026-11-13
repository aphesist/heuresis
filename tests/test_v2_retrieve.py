from __future__ import annotations

import json

from heuresis.domains import get_domain
from heuresis.fakes import HashEmbedder
from heuresis.ingest import ingest
from heuresis.model import AsOf, Event, Passage, Query, Scope, Source, Unit
from heuresis.store import Store
from heuresis.v2.retrieve import _convex, expansion_terms, lookup, open_unit, search

CFG = {"k_lexical": 50, "k_dense": 50, "fusion": "none", "alpha": 0.7, "rrf_k": 60,
       "k_first": 8, "search_k": 5, "prf_terms": 0, "prf_docs": 3, "open_radius": 1,
       "edge_expand": False}

DOCS = {
    "d1": [("2019-01-01", "The harbour tariff covers vessels above ten tonnes, with pilotage fees.")],
    "d2": [("2019-01-01", "Pilotage fees are charged per movement in the harbour basin.")],
    "d3": [("2019-01-01", "Mooring dues apply to vessels at the quay overnight.")],
    "d4": [("2019-01-01", "A lighthouse stands at the harbour mouth.")],
    "d5": [("2019-01-01", "Orchards produce apples in autumn."),
           ("2022-01-01", "Orchards produce pears and apples in autumn.")],
}


def write_corpus(path):
    path.mkdir(parents=True, exist_ok=True)
    units, events = [], []
    for uid, versions in DOCS.items():
        src = "s2" if uid == "d4" else "s1"
        units.append({"id": uid, "source_id": src, "title": f"Title {uid}"})
        for i, (d, t) in enumerate(versions):
            events.append({"id": f"{uid}-{i}", "unit_id": uid,
                           "op": "create" if i == 0 else "replace", "date": d, "text": t,
                           "recorded_at": d})
    (path / "units.jsonl").write_text("\n".join(json.dumps(u) for u in units) + "\n")
    (path / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return str(path)


def make_store(tmp_path):
    s = Store(":memory:")
    ingest(s, write_corpus(tmp_path / "c"), "jsonl")
    return s


def q(text, valid="2021-01-01", scope=None):
    return Query(text=text, as_of=AsOf(valid=valid), scope=scope or Scope())


def test_lexical_only_no_marks_k_and_exclude(tmp_path):
    s = make_store(tmp_path)
    trace = []
    got = search(s, q("harbour pilotage fees"), CFG, trace=trace, k=2)
    assert len(got) == 2 and all(p.mark == "" for p in got)
    assert [t.stage for t in trace] == ["lexical"]
    allp = search(s, q("harbour pilotage fees"), CFG)
    assert len(allp) >= 3
    ex = {(allp[0].unit_id, allp[0].seq)}
    assert allp[0].unit_id not in {p.unit_id for p in search(s, q("harbour pilotage fees"), CFG, exclude=ex)}
    assert search(s, q("harbour"), CFG, trace=None, k=0) == []


def test_as_of_and_scope_pass_through(tmp_path):
    s = make_store(tmp_path)
    old = search(s, q("orchards pears", valid="2020-01-01"), CFG)
    new = search(s, q("orchards pears", valid="2023-01-01"), CFG)
    assert [p.text for p in old] == ["Orchards produce apples in autumn."]
    assert "pears" in new[0].text
    assert search(s, q("orchards", valid="2018-01-01"), CFG) == []
    scoped = search(s, q("harbour", scope=Scope(source_ids=("s2",))), CFG)
    assert [p.unit_id for p in scoped] == ["d4"]


def test_expansion_terms_rules():
    mk = lambda uid, title, text: Passage(unit_id=uid, seq=0, text=text, title=title)
    pool = [mk("a", "Pilotage", "Harbour pilotage fees 2020 are charged by the harbour master"),
            mk("b", "Other", "harbour basin and quay"),
            mk("c", "Third", "unrelated quay words")]
    terms = expansion_terms("What are the Harbour fees?", pool, 5, 1)
    assert "harbour" not in terms and "fees" not in terms      # question terms
    assert "2020" not in terms and "the" not in terms and "are" not in terms
    assert "pilotage" in terms and "master" in terms
    assert terms == expansion_terms("What are the Harbour fees?", pool, 5, 1)
    assert len(expansion_terms("x", pool, 2, 1)) == 2
    assert expansion_terms("x", pool, 0, 1) == [] and expansion_terms("x", [], 3, 1) == []
    # rarer terms outrank terms found in most of the pool
    assert terms.index("pilotage") < terms.index("charged") or "charged" not in terms


def test_expansion_terms_accent_insensitive_and_stopwords():
    mk = lambda t: Passage(unit_id="a", seq=0, text=t, title="")
    pool = [mk("Tributação da renda para as empresas, sobre rendimentos"), mk("outro texto aqui")]
    terms = expansion_terms("tributacao", pool, 10, 2)
    assert "tributação" not in terms           # same as the question term once accents fold
    assert "para" not in terms and "sobre" not in terms and "renda" in terms


def test_prf_second_pass_adds_passages(tmp_path):
    s = make_store(tmp_path)
    cfg = {**CFG, "prf_terms": 3, "prf_docs": 1}
    base = search(s, q("tariff"), CFG)
    trace = []
    got = search(s, q("tariff"), cfg, trace=trace)
    assert [t.stage for t in trace] == ["lexical", "expand_terms"]
    assert base[0].unit_id == got[0].unit_id == "d1"
    assert len(got) > len(base)         # 'pilotage' / 'vessels' pull in d2, d3


def test_dense_fusion_rrf_and_convex(tmp_path):
    s = make_store(tmp_path)
    emb = HashEmbedder()
    s.put_vectors(emb.id, [(u, sq, v) for (u, sq, _t), v in zip(
        s.missing_vectors(emb.id),
        emb.embed([t for (_u, _s, t) in s.missing_vectors(emb.id)]))])
    for mode in ("rrf", "convex"):
        trace = []
        got = search(s, q("harbour pilotage fees"), {**CFG, "fusion": mode}, embedder=emb, trace=trace)
        assert [t.stage for t in trace] == ["lexical", "dense"]
        assert got and all(p.stage == "fused" and p.mark == "" for p in got)
        assert [p.score for p in got] == sorted((p.score for p in got), reverse=True)
    # fusion none ignores the embedder
    got = search(s, q("harbour"), CFG, embedder=emb)
    assert all(p.stage == "lexical" for p in got)


def test_convex_normalisation():
    P = lambda u, sc: Passage(unit_id=u, seq=0, text="", score=sc)
    out = _convex([P("a", 10.0), P("b", 5.0)], [P("b", 0.9), P("c", 0.1)], 0.7)
    sc = {p.unit_id: p.score for p in out}
    assert abs(sc["a"] - 0.7) < 1e-9 and abs(sc["b"] - 0.3) < 1e-9 and sc["c"] == 0.0
    assert out[0].unit_id == "a"
    single = _convex([P("a", 3.0)], [P("a", 0.2)], 0.7)
    assert abs(single[0].score - 1.0) < 1e-9          # one candidate normalises to 1.0 on each side
    assert [p.unit_id for p in _convex([P("a", 2.0), P("b", 2.0)], [], 0.5)] == ["a", "b"]


def test_edge_expand(tmp_path):
    s = make_store(tmp_path)
    from heuresis.model import Edge
    s.add(edges=[Edge("d4", "d3", "cites")])
    trace = []
    got = search(s, q("lighthouse"), {**CFG, "edge_expand": True}, trace=trace)
    assert [p.unit_id for p in got] == ["d4", "d3"]
    assert trace[-1].stage == "edges"
    assert [p.unit_id for p in search(s, q("lighthouse"), CFG)] == ["d4"]


def _legal_store():
    LEI = "urn:lex:br:federal:lei:2020-03-10;1"
    s = Store(":memory:")
    units, events = [], []
    for a in ("1", "2"):
        uid = f"{LEI}!art{a}"
        units.append(Unit(uid, LEI, "article", None, f"Lei Exemplo art {a}"))
        events.append(Event(f"{uid}@a", uid, "create", "2020-03-10", f"Art. {a} texto sintetico", "2020-03-10"))
    events.append(Event("r2", f"{LEI}!art2", "replace", "2023-01-01", "Art. 2 nova redacao sintetica", "2023-01-01"))
    s.add([Source(LEI, "norm", 3, 3, None, {"title": "Lei nº 1, de 10 de março de 2020"})], units, events)
    s.rebuild()
    return s, LEI


def test_lookup_resolves_and_applies_date():
    s, LEI = _legal_store()
    dom = get_domain("legal_br")
    ps, refs = lookup(s, dom, "O art. 2º da Lei nº 1/2020 e o art. 9 da Lei nº 1/2020", AsOf(valid="2021-01-01"))
    assert [p.unit_id for p in ps] == [f"{LEI}!art2"] and ps[0].stage == "lookup"
    assert "sintetico" in ps[0].text and "nova" not in ps[0].text
    assert [r.status for r in refs] == ["resolved", "unit_not_found"]
    ps2, _ = lookup(s, dom, "art. 2 da Lei nº 1/2020", AsOf(valid="2024-01-01"))
    assert "nova" in ps2[0].text
    ps3, refs3 = lookup(s, dom, "art. 2 da Lei nº 1/2020", AsOf(valid="2019-01-01"))
    assert ps3 == [] and refs3[0].status == "resolved"       # resolved but not in force
    assert lookup(s, get_domain("jsonl"), "art. 2 da Lei nº 1/2020", AsOf()) == ([], [])
    assert lookup(s, None, "x", AsOf()) == ([], [])


def test_open_unit_with_neighbours(tmp_path):
    s = make_store(tmp_path)
    got = open_unit(s, "d2", AsOf(valid="2021-01-01"), 1)
    assert [p.unit_id for p in got] == ["d2", "d1", "d3"]
    assert open_unit(s, "d2", AsOf(valid="2021-01-01"), 0)[0].unit_id == "d2"
    assert len(open_unit(s, "d2", AsOf(valid="2021-01-01"), 0)) == 1
    assert open_unit(s, "d5", AsOf(valid="2018-01-01"), 1) == []
