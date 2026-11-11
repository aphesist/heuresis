import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from heuresis.domains import get_domain
from heuresis.domains.legal_br import extract_references
from heuresis.ingest import ingest
from heuresis.model import AsOf, Query, Scope

FIX = Path(__file__).parent / "fixtures" / "domains"
NORM = "urn:lex:br:federal:lei:2020-03-10;1"


def write(p: Path, text: str, mtime: float | None = None):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(p, (mtime, mtime))


# ---------------------------------------------------------------- text


@pytest.fixture
def notes(tmp_path):
    root = tmp_path / "notes"
    write(root / "a.md", "---\ndate: 2023-05-01\n---\n# Alpha\nintro text\n\n## Setup\nsetup body see [[b]] and [more](sub/c.md#deep-dive).\n\n## Usage\nusage body\n", 1_600_000_000)
    write(root / "b.md", "# Beta\nbeta body with [back](a.md#setup)\n", 1_600_000_000)
    write(root / "sub" / "c.md", "# C\n\n## Deep dive\ncontent\n", 1_600_000_000)
    write(root / "plain.txt", "first paragraph.\n\nsecond paragraph.\n" + ("x" * 700 + "\n\n") * 3, 1_600_000_000)
    write(root / "new.md", "---\ndate: 2024-01-01\nsupersedes: b.md\n---\n# Beta v2\nnew beta\n")
    return root


def test_text_deterministic_and_ids(notes):
    d = get_domain("text")
    r1, r2 = d.read(str(notes)), d.read(str(notes))
    assert r1 == r2
    ids = {u.id for u in r1[1]}
    assert "text:a.md#alpha" in ids
    assert "text:a.md#alpha/setup" in ids
    assert "text:sub/c.md#c/deep-dive" in ids
    titles = {u.id: u.title for u in r1[1]}
    assert titles["text:a.md#alpha/setup"] == "Alpha > Setup"
    assert len(r1[0]) == 1


def test_text_dates(notes):
    _, units, events, _ = get_domain("text").read(str(notes))
    ev = {e.unit_id: e for e in events if e.op == "create"}
    assert ev["text:a.md#alpha"].date == "2023-05-01"
    assert ev["text:b.md#beta"].date == "2020-09-13"  # mtime 1_600_000_000


def test_text_paragraph_splitting(notes):
    _, units, events, _ = get_domain("text").read(str(notes))
    chunks = [e for e in events if e.unit_id.startswith("text:plain.txt#")]
    assert len(chunks) >= 2
    assert all(len(e.text) <= 1200 for e in chunks)


def test_text_links_to_edges(notes):
    _, _, _, edges = get_domain("text").read(str(notes))
    pairs = {(e.src, e.dst) for e in edges}
    assert all(e.type == "cites" for e in edges)
    assert ("text:a.md#alpha/setup", "text:b.md#beta") in pairs
    assert ("text:a.md#alpha/setup", "text:sub/c.md#c/deep-dive") in pairs
    assert ("text:b.md#beta", "text:a.md#alpha/setup") in pairs


def test_text_supersedes(notes):
    _, _, events, _ = get_domain("text").read(str(notes))
    rep = [e for e in events if e.op == "repeal"]
    assert [(e.unit_id, e.date) for e in rep] == [("text:b.md#beta", "2024-01-01")]


# ---------------------------------------------------------------- git


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args],
                   cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")

    def commit(msg, when):
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                        "commit", "-q", "-m", msg], cwd=r, check=True, capture_output=True, env=env)

    (r / "a.txt").write_text("one\n")
    (r / "bin.dat").write_bytes(b"\x00\x01\x02")
    (r / "big.txt").write_text("y" * 250_000)
    _git(r, "add", "-A")
    commit("c1", "2024-01-10T12:00:00+00:00")
    (r / "a.txt").write_text("two\n")
    _git(r, "add", "-A")
    commit("c2", "2024-02-10T12:00:00+00:00")
    _git(r, "rm", "-q", "a.txt")
    commit("c3", "2024-03-10T12:00:00+00:00")
    return r


def test_git_history(repo):
    src, units, events, _ = get_domain("git").read(str(repo))
    assert [u.id for u in units] == ["git:a.txt"]
    ev = [(e.op, e.date, e.text) for e in events]
    assert ev == [("create", "2024-01-10", "one\n"), ("replace", "2024-02-10", "two\n"),
                  ("repeal", "2024-03-10", None)]
    assert all(len(e.evidence) == 40 for e in events)
    assert events[0].recorded_at.startswith("2024-01-10")
    assert get_domain("git").read(str(repo)) == (src, units, events, [])


def test_git_commit_cap(repo):
    _, _, events, _ = get_domain("git", max_commits=1).read(str(repo))
    assert events == []  # only the deletion commit, of a file never seen


# ---------------------------------------------------------------- tables


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "shop.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE orders (id INTEGER, customer TEXT, total REAL)")
    con.executemany("INSERT INTO orders VALUES (?,?,?)", [(i, f"c{i}", i * 1.5) for i in range(5)])
    con.commit()
    con.close()
    return p


def test_tables_cards_and_rule(db):
    d = get_domain("tables")
    _, units, events, _ = d.read(str(db))
    assert [(u.id, u.kind) for u in units] == [("table:shop.orders", "schema")]
    text = events[0].text
    assert "orders" in text and "customer (TEXT)" in text and "Rows: 5" in text
    assert text.count("Sample ") == 3
    assert d.read(str(db)) == d.read(str(db))
    rule = d.rules()[0]
    assert rule("how many rows has the orders table?") == {"intent": "table"}
    assert rule("what is the weather") is None
    assert isinstance(d.tools(), list)


# ---------------------------------------------------------------- jsonl


def _corpus(tmp_path, **files):
    for name, rows in files.items():
        (tmp_path / f"{name}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return str(tmp_path)


def test_jsonl_roundtrip(tmp_path):
    p = _corpus(tmp_path,
                units=[{"id": "u1", "source_id": "s"}],
                events=[{"id": "e1", "unit_id": "u1", "op": "create", "date": "2020-01-01", "text": "hi"}])
    s, u, e, ed = get_domain("jsonl").read(p)
    assert (s, ed) == ([], []) and u[0].id == "u1" and e[0].text == "hi"


@pytest.mark.parametrize("bad, needle", [
    ({"id": "e1", "unit_id": "u1", "op": "bogus", "date": "2020-01-01"}, "events.jsonl:2"),
    ({"id": "e1", "unit_id": "u1", "op": "create", "date": "2020-01-01", "text": "x", "zzz": 1}, "unknown"),
    ({"id": "e1", "unit_id": "u1", "op": "create", "text": "x"}, "missing field 'date'"),
    ({"id": "e1", "unit_id": "u1", "op": "create", "date": "2020-01-01"}, "requires text"),
])
def test_jsonl_errors(tmp_path, bad, needle):
    good = {"id": "e0", "unit_id": "u1", "op": "create", "date": "2020-01-01", "text": "x"}
    p = _corpus(tmp_path, units=[{"id": "u1", "source_id": "s"}], events=[good, bad])
    with pytest.raises(ValueError) as ei:
        get_domain("jsonl").read(p)
    assert "events.jsonl:2" in str(ei.value) and needle in str(ei.value)


def test_jsonl_bad_json_and_missing(tmp_path):
    (tmp_path / "units.jsonl").write_text("{not json}\n")
    (tmp_path / "events.jsonl").write_text("")
    with pytest.raises(ValueError, match=r"units.jsonl:1"):
        get_domain("jsonl").read(str(tmp_path))
    (tmp_path / "units.jsonl").unlink()
    with pytest.raises(ValueError, match="units.jsonl"):
        get_domain("jsonl").read(str(tmp_path))


# ---------------------------------------------------------------- legal_br


def test_legal_br_read_rules_texts():
    d = get_domain("legal_br")
    assert d.axes == ("published", "effects")
    s, u, e, ed = d.read(str(FIX / "legal_br"))
    assert len(u) == 3 and len(e) == 7 and len(ed) == 1
    assert e[3].axes["published"] != e[3].date
    refs = extract_references("O art. 18, § 5º da LC 123/2006 e Lei Exemplo nº 1/2020")
    assert refs["articles"] == ["18"] and refs["paragraphs"] == ["5"]
    assert [n["year"] for n in refs["norms"]] == ["2006", "2020"]
    rule = d.rules()[0]
    assert rule("O que diz o art. 2 da Lei Exemplo nº 1/2020?") == {"scope": Scope(unit_prefix=NORM)}
    assert rule("art. 18 da LC 123/2006") is None  # norm not in corpus
    assert "vigor" in d.abstention_text("not_valid_at_date", Query("x"))
    assert d.abstention_text("nonexistent", Query("x")) is None


# ---------------------------------------------------------------- store


def _store():
    mod = pytest.importorskip("heuresis.store")
    return mod.Store(":memory:")


def test_ingest_idempotent(notes):
    st = _store()
    c = ingest(st, str(notes), get_domain("text"))
    before = st.stats()
    assert c["units"] > 0
    ingest(st, str(notes), get_domain("text"))
    assert st.stats() == before


def test_legal_br_history_in_store():
    st = _store()
    ingest(st, str(FIX / "legal_br"), get_domain("legal_br"))
    a2, a3 = f"{NORM}!art2", f"{NORM}!art3"

    def at(uid, d, rec=None):
        v = st.text_at(uid, AsOf(valid=d, recorded=rec))
        return v.text if v else None

    assert "alfa" in at(a2, "2021-01-01")
    assert at(a2, "2020-01-01") is None
    assert at(a2, "2022-07-01").endswith("nova redação corrigida.")
    assert at(a2, "2022-07-01", "2022-12-31").endswith("nova redação.")  # before the correction was recorded
    assert at(a3, "2023-01-01") is not None
    assert at(a3, "2024-08-01") is None
    assert at(a3, "2025-10-01") == at(a3, "2023-01-01")
