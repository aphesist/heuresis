"""Builders of the brlaw corpus: splitting, repeal dates, flat-text articles, questions, merge.
Synthetic text only: nothing here is a legal provision."""
import json

from heuresis.bench import brlaw as B

URN = "urn:lex:br:federal:lei:2001-02-03;7"
MD = """---
titulo: "Lei nº 7 de 03/02/2001"
urn: "urn:lex:br:federal:lei:2001-02-03;7"
data: 2001-02-03
---
# Lei nº 7 de 03/02/2001

TEXTO SINTÉTICO DE TESTE

#### CAPÍTULO I

**Art. 1º** Primeiro dispositivo sintético.

I - item um;

**Art. 2º** Segundo dispositivo sintético, que cita:

"Art. 9º Texto citado, não é artigo desta norma."

**Art. 3.** *(Revogado pela Lei nº 8, de 4/5/2004)*

**Art. 4º** *(Revogado pela Medida Provisória nº 9, de 1/1/2005, convertida na Lei nº 10, de 2/2/2005)*

**Art. 5º-A.** Quinto A sintético.

## ATO DAS DISPOSIÇÕES CONSTITUCIONAIS TRANSITÓRIAS

**Art. 1º** Transitório sintético.
"""


def test_header_and_articles():
    hdr, body = B.parse_header(MD)
    assert hdr["urn"] == URN and hdr["data"] == "2001-02-03"
    arts = B.split_md_articles(body)
    keys = [(p, k) for p, k, _ in arts]
    assert keys == [("art", "1"), ("art", "2"), ("art", "3"), ("art", "4"), ("art", "5-A"), ("adct", "1")]
    # the quoted article stays inside art. 2 and the list item inside art. 1
    assert "Art. 9º Texto citado" in arts[1][2] and "I - item um" in arts[0][2]


def test_markdown_units_repeal_dates():
    hdr, body = B.parse_header(MD)
    rows = list(B.markdown_units(URN, hdr["titulo"], body, "2001-02-03", URN, evidence="ev"))
    by = {r["unit"]["id"].split("!")[1]: r for r in rows}
    assert set(by) == {"art1", "art2", "art3", "art4", "art5-A", "adct1"}
    r3, r4 = by["art3"], by["art4"]
    assert r3["repealed"] and r3["events"][1]["op"] == "repeal" and r3["events"][1]["date"] == "2004-05-04"
    assert r3["events"][0]["certainty"] == "low" and r3["events"][1]["certainty"] == "high"
    # two different dates (the provisional measure and its conversion) and no "a partir de": unknown
    assert r4["repeal_unknown"] and len(r4["events"]) == 1
    assert not by["art1"]["repealed"] and by["art1"]["events"][0]["certainty"] == "high"


def test_repeal_info():
    assert B.repeal_info("(Revogado pela Lei nº 1, de 4/5/2004)") == ("2004-05-04", "high")
    assert B.repeal_info("(Revogado pela Lei nº 1, de 4/5/2004, em vigor a partir de 1º/1/2005)") == ("2005-01-01", "high")
    assert B.repeal_info("(Revogado pela Lei nº 1)")[0] is None
    assert B.repeal_info("(Revogado pela Lei nº 1, de 31/2/2004)")[0] is None  # not a date


def test_long_article_is_chunked():
    text = "Art. 1º " + "\n".join(f"§ {i} " + "x" * 900 for i in range(30))
    parts = B.chunk_text(text, 8000)
    assert len(parts) > 1 and all(len(p) <= 8000 for p in parts)
    assert B.unit_id(URN, "1", 2) == URN + "!art1!p2"


def test_flat_articles_skip_quoted_and_cited():
    text = ('LEI Nº 7, DE 3 DE FEVEREIRO DE 2001 Art. 1º Altera a Lei X, que passa a vigorar assim: "Art. 9º Citado." (NR) '
            'Art. 2º Conforme o art. 1º desta Lei. § 1º Algo. Art. 3º Terceiro. Art. 3º-A Terceiro A. '
            'Art. 4º Fim. Brasília, 3 de fevereiro de 2001 FULANO')
    arts = B.split_flat_articles(text)
    assert [k for k, _ in arts] == ["1", "2", "3", "3-A", "4"]
    assert "Art. 9º Citado" in arts[0][1]
    assert "Brasília" not in arts[-1][1]


def test_flat_units_without_articles_become_a_document():
    rows = list(B.flat_units("urn:lex:br:rfb:parecer:2020-01-01;5", "Parecer 5", "texto sem artigos", "2020-01-01",
                             "s", evidence="e"))
    assert len(rows) == 1 and rows[0]["unit"]["id"].endswith("!doc") and rows[0]["unit"]["kind"] == "document"


def test_parse_norm_head_uses_file_number_and_falls_back():
    head = "Subchefia ... Vide Lei nº 8.212, de 24 de julho de 1991 ... LEI Nº 11.196, DE 21 DE NOVEMBRO DE 2005 Institui"
    h = B.parse_norm_head(head, "Lei nº 11.196.txt")
    assert (h["kind"], h["number"], h["date"], h["date_source"]) == ("lei", "11196", "2005-11-21", "text")
    h = B.parse_norm_head("sem data", "Instrução Normativa RFB nº 2.178.txt",
                          "Instrução Normativa RFB nº 2.178, de 5 de março de 2024")
    assert (h["kind"], h["authority"], h["date"], h["date_source"]) == (
        "instrucao.normativa", "rfb", "2024-03-05", "dataset_title")
    assert B.parse_norm_head("sem data", "Lei nº 5.txt") is None


def test_gold_article_keys():
    assert B.gold_article_keys("8º") == ["8"]
    assert B.gold_article_keys("15-A") == ["15-A"]
    assert B.gold_article_keys("10 a 13") == ["10", "11", "12", "13"]
    assert B.gold_article_keys("Capítulo III") == [] and B.gold_article_keys("1 a 900") == []


def test_split_is_deterministic_and_sized():
    rows = [{"id": f"q{i}"} for i in range(250)]
    a, b = B.split_taxqa(rows), B.split_taxqa(list(reversed(rows)))
    assert [r["id"] for r in a["dev"]] == [r["id"] for r in b["dev"]]
    assert len(a["dev"]) == 100 and len(a["test"]) == 150
    assert not {r["id"] for r in a["dev"]} & {r["id"] for r in a["test"]}


def test_temporal_questions_from_version_pairs():
    prov = [{"unit": URN + "!art1", "title": "Lei nº 7", "article": "1", "op": "replace", "change_date": "2010-05-01",
             "versions": []},
            {"unit": URN + "!art2", "title": "Lei nº 7", "article": "2", "op": "repeal", "change_date": "2012-01-01",
             "versions": []}]
    qs = {q["id"].rsplit("-", 2)[-2] + q["id"][-6:]: q for q in B.temporal_questions(prov)}
    rows = B.temporal_questions(prov)
    assert len(rows) == 4
    before, after, rb, ra = rows
    assert before["as_of"] == "2010-04-30" and before["gold_units"] == [URN + "!art1#v0"]
    assert after["as_of"] == "2010-05-01" and after["gold_units"] == [URN + "!art1#v1"]
    assert ra["answerable"] is False and ra["gold_units"] == [] and rb["answerable"] is True
    assert "30/04/2010" in before["text"] and not before["answers"]


def _tier(path, sources, units, events):
    path.mkdir(parents=True)
    for name, rows in (("sources", sources), ("units", units), ("events", events)):
        (path / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_merge_drops_duplicate_norms_and_prefers_versioned(tmp_path):
    def mk(urn):
        return {"id": urn, "kind": "norm", "authority": 3, "coverage": 3, "meta": {}}

    def un(uid, src):
        return {"id": uid, "source_id": src, "kind": "article", "parent_id": None, "title": uid}

    def ev(uid, text, d="2001-01-01"):
        return {"id": f"{uid}@{d}", "unit_id": uid, "op": "create", "date": d, "text": text, "recorded_at": d,
                "evidence": "e", "certainty": "high", "axes": {}}
    a, b, c = "urn:lex:br:federal:lei:2001-01-01;1", "urn:lex:br:federal:lei:2001-01-01;2", "urn:lex:br:federal:lei:1990-01-01;3"
    _tier(tmp_path / "tax", [mk(a)], [un(a + "!art1", a), un(a + "!art2", a)], [ev(a + "!art1", "tax1"), ev(a + "!art2", "tax2")])
    _tier(tmp_path / "versioned", [mk(a)], [un(a + "!art2", a)], [ev(a + "!art2", "v1"), {**ev(a + "!art2", "v2", "2005-01-01"), "op": "replace"}])
    _tier(tmp_path / "federal", [mk(a), mk(b), mk(c)],
          [un(a + "!art1", a), un(b + "!art1", b), un(c + "!art1", c)],
          [ev(a + "!art1", "fed-a"), ev(b + "!art1", "fed-b"), ev(c + "!art1", "fed-c", "1990-01-01")])
    cnt = B.merge_tiers(str(tmp_path), str(tmp_path / "out"))
    units = {json.loads(l)["id"] for l in open(tmp_path / "out" / "units.jsonl")}
    assert units == {a + "!art1", a + "!art2", b + "!art1", c + "!art1"}
    texts = {json.loads(l)["unit_id"]: [] for l in open(tmp_path / "out" / "events.jsonl")}
    evs = [json.loads(l) for l in open(tmp_path / "out" / "events.jsonl")]
    assert [e["text"] for e in evs if e["unit_id"] == a + "!art2"] == ["v1", "v2"]  # versioned wins
    assert [e["text"] for e in evs if e["unit_id"] == a + "!art1"] == ["tax1"]  # the tax copy of a norm wins
    assert cnt["federal"]["norms"] == 2 and cnt["versioned"]["units"] == 1
    cnt2 = B.merge_tiers(str(tmp_path), str(tmp_path / "out2"), federal_keep=B.core_filter)
    assert cnt2["federal"]["norms"] == 1  # only b (1995 or later)... c is 1990, a is a duplicate


def test_core_filter():
    assert B.core_filter("urn:lex:br:federal:lei:1995-01-01;1") and not B.core_filter("urn:lex:br:federal:lei:1994-12-31;1")
    assert B.core_filter("urn:lex:br:federal:constituicao:1988-10-05;1988")


def test_canonical_title_and_acronyms():
    h = {"kind": "lei", "number": "11196", "date": "2005-11-21"}
    assert B.canonical_title(h) == "Lei nº 11.196, de 21 de novembro de 2005"
    assert B._explicit_acronyms("Código Tributário Nacional (CTN)") == ["CTN"]
    assert B._explicit_acronyms("Regulamento - RIR/2018, aprovado") == ["RIR/2018"]
