import json
import re
import sqlite3
from pathlib import Path

import pytest

from heuresis import Engine, AsOf, Scope, Answer, load_config, __version__
from heuresis.fakes import EchoLLM
from heuresis.llm import BudgetExceeded
from heuresis.model import Usage

FIX = Path(__file__).parent / "fixtures" / "domains" / "legal_br"
URN = "urn:lex:br:federal:lei:2020-03-10;1!"
ART2, ART3 = URN + "art2", URN + "art3"


class BodyLLM:
    """Answers with the body of the first passage, cited [t1]."""

    id = "body"

    def __init__(self):
        self.calls = 0

    def complete(self, system, prompt, *, max_tokens=600):
        self.calls += 1
        for line in prompt.splitlines():
            m = re.match(r"^\[t1\] \([^)]*\) (?:Art\. \d+º )?(.*)$", line)
            if m:
                return f"{m.group(1)} [t1]", Usage(model="body")
        return "ABSTAIN no_source: nothing.", Usage(model="body")


class CountingLLM:
    id = "count"

    def __init__(self, reply="x [t1]", usd=0.0):
        self.calls, self.reply, self.usd = 0, reply, usd

    def complete(self, system, prompt, *, max_tokens=600):
        self.calls += 1
        return self.reply, Usage(model="count", usd=self.usd)


@pytest.fixture
def legal(tmp_path):
    e = Engine.open(str(tmp_path / "l.db"), "legal_br", llm=BodyLLM())
    e.ingest(str(FIX))
    yield e
    e.close()


def ask2(e, **asof):
    return e.ask("texto sintético redação", as_of=AsOf(**asof), scope=Scope(unit_prefix=ART2))


def test_exports():
    assert __version__ and load_config() and Answer and Scope


def test_valid_time_and_recorded(legal):
    a = ask2(legal, valid="2021-01-01")
    assert a.status == "answered" and "alfa" in a.text
    assert a.citations == [(ART2, 0)]
    a = ask2(legal, valid="2023-01-01", recorded="2022-12-31")
    assert "beta, nova redação." in a.text and "corrigida" not in a.text
    assert a.citations == [(ART2, 1)]
    a = ask2(legal, valid="2023-01-01", recorded="2023-03-01")
    assert "corrigida" in a.text and a.citations == [(ART2, 1)]
    a = ask2(legal, valid="2023-01-01")
    assert "corrigida" in a.text


def test_not_valid_at_date(legal):
    a = legal.ask("texto sintético gama", as_of=AsOf(valid="2025-01-01"),
                  scope=Scope(unit_prefix=ART3))
    assert a.status == "abstained" and a.abstention.type == "not_valid_at_date"
    assert any(ART3 in s and "2024-07-01" in s for s in a.abstention.searched)
    assert a.text == ""


def test_no_source(legal):
    a = legal.ask("zzzz qqqq inexistente")
    assert a.abstention.type == "no_source" and a.status == "abstained"


def test_outside_coverage(tmp_path):
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "a.md").write_text("Quarterly revenue grew strongly.")
    e = Engine.open(str(tmp_path / "t.db"))
    e.ingest(str(d))
    e.store._con.execute("UPDATE sources SET coverage=0")
    e.store._con.commit()
    a = e.ask("quarterly revenue")
    assert a.abstention and a.abstention.type == "outside_coverage"
    e.close()


@pytest.fixture
def text_engine(tmp_path):
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "rate.md").write_text("The standard rate is 6 percent on the base of 1200.")
    e = Engine.open(str(tmp_path / "t.db"))
    e.ingest(str(d))
    yield e
    e.close()


def scripted(e, *replies):
    e.llm = EchoLLM(list(replies))
    return e.ask("What is the standard rate on the base?")


def test_unsupported_number_dropped(text_engine):
    a = scripted(text_engine, "The standard rate is 6 percent [t1]. The base is 9999 [t1].")
    assert a.status in ("partial", "abstained")
    assert "9999" not in a.text
    assert any(c.label == "unsupported" for c in a.claims)
    if a.status == "partial":
        assert "6 percent" in a.text


def test_tool_filled_and_traced(text_engine):
    a = scripted(text_engine,
                 'CALL k1 calc {"expr": "1200 * 0.06"}\n'
                 "The standard rate is 6 percent on the base of 1200, giving {k1} [t1][k1].")
    assert a.status == "answered", a.claims
    assert "72" in a.text and "{k1}" not in a.text
    assert a.claims[0].checks["numbers_traced"]
    assert a.tool_results[0].ok


def test_nonexistent_mark(text_engine):
    a = scripted(text_engine, "The standard rate is 6 percent [t9].")
    assert a.status == "abstained" and a.text == ""
    assert not a.claims[0].checks["exists"]


def test_abstain_draft(text_engine):
    a = scripted(text_engine, "ABSTAIN no_source: nothing covers this.")
    assert a.status == "abstained" and a.abstention.type == "no_source"


def test_malformed_draft_and_model_error(text_engine):
    a = scripted(text_engine, "")
    assert a.status == "abstained" and a.abstention.type == "unsupported"

    class Boom:
        id = "boom"

        def complete(self, *a, **k):
            raise RuntimeError("down")

    text_engine.llm = Boom()
    a = text_engine.ask("What is the standard rate on the base?")
    assert a.abstention.type == "unsupported"
    assert any("model error" in t.note for t in a.trace)

    class Over(Boom):
        def complete(self, *a, **k):
            raise BudgetExceeded("cap")

    text_engine.llm = Over()
    assert text_engine.ask("What is the standard rate on the base?").abstention.type == "budget"


def make_db(path, rows):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE sales (region TEXT, amount INTEGER)")
    con.executemany("INSERT INTO sales VALUES (?,?)", rows)
    con.commit()
    con.close()


def test_sql_binding(tmp_path):
    mine, other = tmp_path / "mine.sqlite", tmp_path / "other.sqlite"
    make_db(mine, [("north", 111)])
    make_db(other, [("north", 999)])
    call = {"db": str(other), "query": "SELECT amount FROM sales"}
    llm = EchoLLM(["CALL k1 sql " + json.dumps(call) + "\nThe amount is {k1} [t1][k1].",
                   "The sales table is described [t1]."])
    e = Engine.open(str(tmp_path / "e.db"), "tables", llm=llm)
    e.ingest(str(mine))
    a = e.ask("What is the amount in the sales table?")
    r = a.tool_results[0]
    assert r.ok and r.value["rows"] == [[111]]
    assert r.args["db"] == str(mine.resolve()) or r.args["db"] == str(mine)
    # one follow-up draft happened
    assert [t.stage for t in a.trace].count("draft_followup") == 1
    e.close()
    # a reopened database still knows its path
    e = Engine.open(str(tmp_path / "e.db"), "tables", llm=EchoLLM(
        ["CALL k1 sql " + json.dumps(call) + "\nok [t1]", "ok [t1]"]))
    assert e.ask("amount in sales table").tool_results[0].value["rows"] == [[111]]
    e.close()


def test_sql_without_known_db(text_engine):
    other = text_engine.store.path + ".x"
    make_db(other, [("a", 1)])
    # a text domain has no sql tool: the call fails instead of using the supplied path
    a = scripted(text_engine,
                 "CALL k1 sql " + json.dumps({"db": other, "query": "SELECT 1"}) +
                 "\nThe standard rate is 6 percent [t1].")
    assert a.tool_results and not a.tool_results[0].ok
    # force the path where the tool exists but no db is known
    text_engine._sql_db = None
    r = text_engine._run_calls(text_engine._tools() + [__import__("heuresis.tools", fromlist=["x"]).SqlTool()],
                               [{"mark": "k1", "tool": "sql", "args": {"db": other, "query": "SELECT 1"}}])
    assert not r[0].ok


def test_ask_back(text_engine):
    cl = lambda text: ("lookup", 0.2)
    text_engine.classifier = cl
    llm = CountingLLM()
    text_engine.llm = llm
    # two intents collide so the classifier decides
    a = text_engine.ask("How much is the total rate on the base of 1200 and how does it compare?")
    assert a.status == "needs_input" and a.abstention.type == "needs_input"
    assert a.abstention.message and llm.calls == 0


def test_budget(text_engine):
    llm = CountingLLM()
    text_engine.llm = llm
    a = text_engine.ask("What is the standard rate?", budget_usd=0)
    assert a.abstention.type == "budget" and llm.calls == 0
    a = text_engine.ask("What is the standard rate?", budget_usd=1.0)
    assert llm.calls == 1


def test_reopen_scope_rule(tmp_path):
    p = str(tmp_path / "r.db")
    e = Engine.open(p, "legal_br")
    e.ingest(str(FIX))
    q = "O que diz o art. 2 da Lei 1/2020?"
    n1 = e.search(q)
    e.close()
    e = Engine.open(p, "legal_br")
    assert e.domain._norms
    assert e.search(q) == n1
    e.close()
    e = Engine.open(p, "legal_br")
    qq = e._understand("Lei 1/2020 texto", None, None)
    assert qq.scope.unit_prefix.startswith("urn:lex:br:federal:lei:2020-03-10;1")
    e.close()


def test_reopen_tolerates_missing_path(tmp_path):
    p = str(tmp_path / "r.db")
    src = tmp_path / "copy"
    src.mkdir()
    for f in FIX.iterdir():
        (src / f.name).write_text(f.read_text())
    e = Engine.open(p, "legal_br")
    e.ingest(str(src))
    e.close()
    for f in src.iterdir():
        f.unlink()
    src.rmdir()
    Engine.open(p, "legal_br").close()


def test_trace_order_and_usd(text_engine):
    text_engine.llm = CountingLLM("The standard rate is 6 percent [t1].", usd=0.01)
    a = text_engine.ask("What is the standard rate on the base?")
    stages = [t.stage for t in a.trace]
    assert stages[0] == "understand"
    order = ["understand", "lexical", "retrieve", "draft", "verify", "decide", "assemble"]
    idx = [stages.index(s) for s in order]
    assert idx == sorted(idx)
    assert a.usd == pytest.approx(sum(t.usd for t in a.trace)) == pytest.approx(0.01)


def test_verify_search_unit_index(text_engine):
    ps = text_engine.search("standard rate", k=3)
    assert ps and ps[0].mark == "t1"
    claims = text_engine.verify("The standard rate is 6 percent [t1].", ps)
    assert claims[0].label == "supported"
    assert text_engine.unit(ps[0].unit_id).text
    assert text_engine.index() == 0
    from heuresis.fakes import HashEmbedder
    text_engine.embedder = HashEmbedder()
    assert text_engine.index(batch=1) == 1 and text_engine.index() == 0
    with text_engine as e:
        assert e is text_engine
    text_engine.store = type("S", (), {"close": lambda s: None})()


def test_store_additions(tmp_path):
    from heuresis.store import Store
    s = Store(str(tmp_path / "s.db"))
    assert s.meta_get("a") is None
    s.meta_set("a", "1")
    s.meta_set("a", "2")
    assert s.meta_get("a") == "2"
    s.close()
    s = Store(str(tmp_path / "s.db"))
    assert s.meta_get("a") == "2"
    s.close()

    e = Engine.open(str(tmp_path / "l.db"), "legal_br")
    e.ingest(str(FIX))
    st = e.store
    q = "texto sintético gama"
    assert st.lexical(q, AsOf(valid="2025-01-01"), Scope(unit_prefix=ART3), 5) == []
    found = st.lexical_any_date(q, Scope(unit_prefix=ART3), 5)
    assert {p.unit_id for p in found} == {ART3}
    assert all(p.unit_id.startswith(ART2) for p in st.lexical_any_date("texto", Scope(unit_prefix=ART2), 9))
    e.close()


def test_open_domain_default_uses_stored(tmp_path):
    p = str(tmp_path / "d.db")
    e = Engine.open(p)
    assert e.domain.name == "text"
    e.close()
    e = Engine.open(p, "legal_br")  # empty database: any domain may be chosen
    assert e.domain.name == "legal_br"
    e.ingest(str(FIX))
    e.close()
    e = Engine.open(p)
    assert e.domain.name == "legal_br"
    e.close()
    Engine.open(p, "legal_br").close()
    with pytest.raises(ValueError, match="legal_br.*text|text.*legal_br"):
        Engine.open(p, "text")


# ------------------------------------------------------ question dates vs corpus history


BARDOLI = "When did the person who launched the Bardoli Satyagraha on 4th february 1928 die?"


def _undated_engine(tmp_path):
    from heuresis.model import Event, Source, Unit
    e = Engine.open(str(tmp_path / "u.db"), llm=EchoLLM())
    e.store.add(sources=[Source("s")], units=[Unit("u1", "s", title="Bardoli")],
                events=[Event(id="e1", unit_id="u1", op="create", date="1970-01-01",
                              text="Vallabhbhai Patel launched the Bardoli Satyagraha and "
                                   "died in 1950.", recorded_at="1970-01-01")])
    e.store.rebuild()
    return e


def test_date_in_question_on_unversioned_corpus_is_not_an_as_of(tmp_path):
    e = _undated_engine(tmp_path)
    a = e.ask(BARDOLI)
    assert a.status == "answered", a.abstention
    assert a.query.dated is False and a.query.as_of.valid is None
    note = next(t.note for t in a.trace if t.stage == "understand")
    assert "1928-02-04" in note and "no version history" in note
    assert e.search(BARDOLI) and e.search(BARDOLI)[0].unit_id == "u1"
    # a caller-supplied as_of is never discarded, even when nothing is in force then
    b = e.ask(BARDOLI, as_of=AsOf(valid="1928-02-04"))
    assert b.abstention and b.abstention.type == "not_valid_at_date"
    assert b.query.as_of.valid == "1928-02-04"
    e.close()


def test_date_before_the_first_version_is_discarded(legal):
    # versioned corpus whose first version starts 2020-03-10
    a = legal.ask("texto sintético gama em 4 de fevereiro de 1928", scope=Scope(unit_prefix=ART3))
    assert a.query.dated is False and a.query.as_of.valid is None
    assert "earlier than the first version" in next(
        t.note for t in a.trace if t.stage == "understand")


def test_date_inside_the_range_of_a_versioned_corpus_still_applies(legal):
    assert legal.store.time_profile()["versioned"] is True
    a = legal.ask("texto sintético redação em 1 de janeiro de 2021", scope=Scope(unit_prefix=ART2))
    assert a.query.dated is True and a.query.as_of.valid == "2021-01-01"
    assert a.status == "answered" and "alfa" in a.text
    assert "not used as as-of" not in next(t.note for t in a.trace if t.stage == "understand")
    p = legal.search("texto sintético redação em 1 de janeiro de 2021", scope=Scope(unit_prefix=ART2))
    assert [x.seq for x in p] == [0]
