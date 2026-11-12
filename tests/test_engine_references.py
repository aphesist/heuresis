"""The references_traced gate inside the engine: a sentence may only name what it cites."""
import json

import pytest

from heuresis import AsOf, Engine
from heuresis.model import Usage

LEI = "urn:lex:br:federal:lei:2020-03-10;1"


class Script:
    id = "script"

    def __init__(self, replies):
        self.replies, self.n = list(replies), 0

    def complete(self, system, prompt, *, max_tokens=600):
        r = self.replies[min(self.n, len(self.replies) - 1)]
        self.n += 1
        return r, Usage(model="script", tokens_in=10, tokens_out=10, usd=0.0)


@pytest.fixture
def corpus(tmp_path):
    d = tmp_path / "c"
    d.mkdir()
    rows = {
        "sources.jsonl": [{"id": LEI, "kind": "norm", "authority": 3, "coverage": 4,
                           "meta": {"title": "Lei nº 1, de 10 de março de 2020"}}],
        "units.jsonl": [{"id": LEI + "!art1", "source_id": LEI, "kind": "article", "title": "Lei nº 1, de 10 de março de 2020 — Art. 1"},
                        {"id": LEI + "!art2", "source_id": LEI, "kind": "article", "title": "Lei nº 1, de 10 de março de 2020 — Art. 2"}],
        "events.jsonl": [
            {"id": "a", "unit_id": LEI + "!art1", "op": "create", "date": "2020-03-10",
             "text": "Art. 1º O zorblax sintético é obrigatório.", "recorded_at": "2020-03-10"},
            {"id": "b", "unit_id": LEI + "!art2", "op": "create", "date": "2020-03-10",
             "text": "Art. 2º O quibblet sintético é facultativo.", "recorded_at": "2020-03-10"}],
        "edges.jsonl": [],
    }
    for name, rs in rows.items():
        (d / name).write_text("\n".join(json.dumps(r) for r in rs), encoding="utf-8")
    return str(d)


def ask(corpus, tmp_path, reply, **kw):
    eng = Engine.open(str(tmp_path / "s.db"), "legal_br", llm=Script([reply]), **kw)
    eng.ingest(corpus)
    ans = eng.ask("O zorblax é obrigatório?", as_of=AsOf(valid="2021-01-01"))
    eng.close()
    return ans


def cited_mark(corpus, tmp_path):
    """The mark the engine gives to the art. 1 passage for this question."""
    eng = Engine.open(str(tmp_path / "p.db"), "legal_br")
    eng.ingest(corpus)
    ps = eng.search("O zorblax é obrigatório?", as_of=AsOf(valid="2021-01-01"))
    eng.close()
    return ps[0].unit_id, ps[0].mark


def test_traced_reference_is_kept(corpus, tmp_path):
    uid, _ = cited_mark(corpus, tmp_path)
    assert uid.endswith("!art1")
    ans = ask(corpus, tmp_path, "Sim, conforme o art. 1º da Lei nº 1/2020 [t1].")
    assert ans.status == "answered" and "art. 1º" in ans.text
    assert all(c.checks.get("references_traced") for c in ans.claims)


def test_reference_to_an_uncited_provision_is_dropped(corpus, tmp_path):
    ans = ask(corpus, tmp_path, "Sim, conforme o art. 2º da Lei nº 1/2020 [t1].")  # art. 2 exists, but t1 is art. 1
    assert ans.status == "abstained" and ans.text == ""
    assert ans.claims[0].checks["references_traced"] is False and "does not cite" in ans.claims[0].note


def test_invented_reference_is_dropped_and_the_rest_kept(corpus, tmp_path):
    ans = ask(corpus, tmp_path, "Sim, conforme o art. 1º da Lei nº 1/2020 [t1].\nTambém vale o art. 99 da Lei nº 1/2020 [t1].")
    assert ans.status == "partial"
    assert "art. 1º" in ans.text and "art. 99" not in ans.text
    assert [c.checks["references_traced"] for c in ans.claims] == [True, False]


def test_a_nonexistent_norm_is_dropped(corpus, tmp_path):
    ans = ask(corpus, tmp_path, "Sim, conforme a Lei nº 777/2020, art. 1 [t1].")
    assert ans.status == "abstained"


def test_gate_can_be_switched_off(corpus, tmp_path):
    ans = ask(corpus, tmp_path, "Sim, conforme o art. 2º desta lei [t1].", references_traced=False)
    assert all("references_traced" not in c.checks for c in ans.claims)
    on = ask(corpus, tmp_path, "Sim, conforme o art. 2º da Lei nº 1, de 10 de março de 2020 [t1].")
    assert on.claims[0].checks["references_traced"] is False


def test_the_label_lets_a_sentence_cite_by_number_and_year(corpus, tmp_path):
    """"Lei nº 1/2020" has numbers that are in the passage's label, not in the provision's words."""
    ans = ask(corpus, tmp_path, "Sim, conforme o art. 1º da Lei nº 1/2020 [t1].")
    assert ans.claims[0].checks["numbers_traced"] is True


def test_domains_without_a_resolver_are_unaffected(tmp_path):
    d = tmp_path / "t"
    d.mkdir()
    (d / "a.md").write_text("# Alfa\nO zorblax é obrigatório conforme o art. 99 da Lei nº 1/2020.\n", encoding="utf-8")
    eng = Engine.open(str(tmp_path / "t.db"), "text", llm=Script(["Sim, conforme o art. 99 da Lei nº 1/2020 [t1]."]))
    eng.ingest(str(d))
    ans = eng.ask("O zorblax é obrigatório?")
    eng.close()
    assert ans.status == "answered" and all("references_traced" not in c.checks for c in ans.claims)
