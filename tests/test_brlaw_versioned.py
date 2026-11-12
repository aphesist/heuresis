"""The versioned tier's parsers, on synthetic pages shaped like the Câmara's (no network)."""
from heuresis.bench import brlaw_versioned as V

COMPILED = """<html><body>
<p>LEI Nº 7, DE 3 DE FEVEREIRO DE 2001</p>
<p>CAPÍTULO I</p>
<p>Art. 1º Texto novo sintético do primeiro artigo.
(<a href="x/lei-9-1-maio-2005-111-norma-pl.html">Redação dada pela Lei nº 9, de 1/5/2005</a>)</p>
<p>Art. 2º Texto sintético sem alteração. (Vide Lei nº 3, de 1/1/2000)</p>
<p>Art. 3º (Revogado pela Lei nº 9, de 1/5/2005)</p>
<p>Art. 4º Texto com duas leis. (Redação dada pela Lei nº 9, de 1/5/2005) (Parágrafo acrescido pela Lei nº 11, de 2/6/2007)</p>
</body></html>"""

NORMA = """<html><body><p>EMENTA: x</p>
<p>Texto - Publicação Original Diário Oficial da União - Seção 1 - 4/2/2001, Página 5 (Publicação Original)</p>
<p>Vide Norma(s): Lei Ordinária nº 9 de 1 de Maio de 2005 (Poder Legislativo) - (Alteração). Art. 1º .<a href="../../../fed/lei/2005/lei-9-1-maio-2005-111-norma-pl.html">x</a></p>
</body></html>"""


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parse_articles_keeps_text_and_strips_annotations(tmp_path):
    arts = V.parse_articles(V.page_lines(_write(tmp_path, "c.html", COMPILED)))
    assert list(arts) == ["1", "2", "3", "4"]
    a1 = arts["1"]
    assert a1["clean"] == "Art. 1º Texto novo sintético do primeiro artigo."
    assert "Redação dada pela Lei nº 9, de 1/5/2005" in a1["annotations"][0]["text"]
    assert a1["annotations"][0]["hrefs"] and "lei-9-1-maio-2005" in a1["annotations"][0]["hrefs"][0]
    assert arts["2"]["clean"].endswith("sem alteração.")
    assert len(arts["4"]["annotations"]) == 2


def test_publication_date_and_vide_map(tmp_path):
    lines = V.page_lines(_write(tmp_path, "n.html", NORMA))
    assert V.publication_date(lines) == "2001-02-04"
    m = V.vide_map(lines, "https://example.org/legin/fed/lei/2001/lei-7-3-fevereiro-2001-1-norma-pl.html")
    assert m == {("lei", "9", "2005-05-01"): "https://example.org/legin/fed/lei/2005/lei-9-1-maio-2005-111-norma-pl.html"}


def test_annotation_acts_and_entry_into_force():
    assert V.annotation_acts("(Redação dada pela Lei Complementar nº 4, de 1/5/2005)") == {("lei.complementar", "4", "2005-05-01")}
    assert len(V.annotation_acts("(Redação dada pela Lei nº 9, de 1/5/2005 e pela Lei nº 11, de 2/6/2007)")) == 2
    pub = "2005-05-02"
    assert V.entry_into_force(["Esta Lei entra em vigor na data de sua publicação."], pub)[:2] == (pub, "high")
    assert V.entry_into_force(["Esta Lei entra em vigor em 1º de janeiro de 2006."], pub)[:2] == ("2006-01-01", "high")
    # a period ("cento e vinte dias") is not computed: the date stays unsettled
    assert V.entry_into_force(["Esta Lei entra em vigor após decorridos cento e vinte dias de sua publicação."], pub)[0] is None
    assert V.entry_into_force(["Êste Decreto-lei entrará em vigor na data de sua publicação, revogadas as disposições."], pub)[:2] == (pub, "high")
    assert V.entry_into_force(["O presente decreto-lei entrará em vigor na data de sua publicação."], pub)[:2] == (pub, "high")
    assert V.entry_into_force(["sem cláusula"], pub)[0] is None
    # "produzindo efeitos: I - ...; II - a partir de ..." has no single date for the act
    deferred = ["Esta Lei entra em vigor na data de sua publicação, produzindo efeitos: I - nessa data, em relação aos arts. 1º; II - a partir de 1º de janeiro de 2006, em relação aos demais."]
    assert V.entry_into_force(deferred, pub)[0] is None


def test_sibling_urls():
    u = "https://www2.camara.leg.br/legin/fed/lei/1995/lei-9250-26-dezembro-1995-362566-normaatualizada-pl.html"
    assert V.sibling(u, "norma").endswith("-362566-norma-pl.html")
    assert V.sibling(u, "orig").endswith("-362566-publicacaooriginal-1-pl.html")
    pe = "https://x/legin/fed/declei/1940-1949/decreto-lei-5452-1-maio-1943-415500-normaatualizada-pe.html"
    assert V.sibling(pe, "norma").endswith("-norma-pe.html")


def test_select_provisions_is_deterministic_and_spreads_over_acts():
    prov = [{"unit": f"u{i}", "act": f"a{i % 5}"} for i in range(50)]
    sel = V.select_provisions(prov, 10)
    assert len(sel) == 10 and sel == V.select_provisions(list(reversed(prov)), 10)
    assert len({p["act"] for p in sel}) == 5 and {p["act"] for p in sel} == {f"a{i}" for i in range(5)}
    assert V.select_provisions(prov, None) is prov


def test_unused_candidates_form_the_held_out_selection():
    prov = [{"unit": f"u{i}", "act": f"a{i % 7}"} for i in range(70)]
    main = V.select_provisions(prov, 10)
    keep = {p["unit"] for p in main}
    unused = [p for p in prov if p["unit"] not in keep]
    test = V.select_provisions(unused, 20)
    assert len(test) == 20 and not {p["unit"] for p in test} & keep
    assert V.select_provisions(unused, 500) == unused   # all of them when under the cap
