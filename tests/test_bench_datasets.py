"""Tests for the benchmark dataset loaders. Synthetic raw data only, unless
HEURESIS_TEST_DATA=1 (then the real, already built corpora are checked)."""
import json
import os
import random

import pytest

from heuresis.bench import datasets as D
from heuresis.bench.types import Question

REAL = os.environ.get("HEURESIS_TEST_DATA") == "1"
DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")


def _qs(n_ans=70, n_null=30):
    out = [Question(id=f"q{i}", text=f"question {i}", answers=("a",)) for i in range(n_ans)]
    out += [
        Question(id=f"n{i}", text=f"null {i}", answers=(), answerable=False)
        for i in range(n_null)
    ]
    return out


# ---------------------------------------------------------------- splits


def test_splits_disjoint_sizes_and_order_independent():
    qs = _qs()
    a = D.split_questions(qs, n_dev=10, n_test=40, n_sealed=20)
    assert [len(a[k]) for k in ("dev", "test", "sealed")] == [10, 40, 20]
    ids = [q.id for k in a for q in a[k]]
    assert len(ids) == len(set(ids)) == 70
    shuffled = qs[:]
    random.Random(1).shuffle(shuffled)
    b = D.split_questions(shuffled, n_dev=10, n_test=40, n_sealed=20)
    assert {k: [q.id for q in v] for k, v in a.items()} == {
        k: [q.id for q in v] for k, v in b.items()
    }


def test_splits_depend_on_seed():
    qs = _qs()
    a = D.split_questions(qs, n_dev=10, n_test=40, n_sealed=20, seed=1)
    b = D.split_questions(qs, n_dev=10, n_test=40, n_sealed=20, seed=2)
    assert [q.id for q in a["test"]] != [q.id for q in b["test"]]


def test_splits_preserve_unanswerable_fraction():
    a = D.split_questions(_qs(), n_dev=10, n_test=40, n_sealed=20)  # 30% null
    for name, want in (("dev", 3), ("test", 12), ("sealed", 6)):
        assert sum(not q.answerable for q in a[name]) == want


def test_splits_small_pool_fills_dev_then_test():
    qs = _qs(8, 2)
    a = D.split_questions(qs, n_dev=6, n_test=500, n_sealed=300)
    assert len(a["dev"]) == 6 and len(a["test"]) == 4 and len(a["sealed"]) == 0
    tiny = D.split_questions(_qs(3, 0), n_dev=10, n_test=10, n_sealed=10)
    assert [len(tiny[k]) for k in ("dev", "test", "sealed")] == [3, 0, 0]


def test_splits_reject_duplicate_ids():
    q = Question(id="x", text="t", answers=("a",))
    with pytest.raises(ValueError):
        D.split_questions([q, q])


def test_order_key_is_sha256_of_seed_and_id():
    import hashlib

    assert D.order_key(7, "abc") == hashlib.sha256(b"7:abc").hexdigest()


# ---------------------------------------------------------------- passages


def test_split_passages_short_text_is_whole():
    assert D.split_passages("one two three") == ["one two three"]


def test_split_passages_respects_paragraphs_and_size():
    paras = [" ".join(f"w{p}_{i}" for i in range(90)) for p in range(8)]
    out = D.split_passages("\n\n".join(paras))
    assert len(out) > 1
    for o in out:
        assert 1 <= len(o.split()) <= 300
    # nothing lost and paragraph boundaries are never cut (each paragraph fits whole)
    assert " ".join(" ".join(out).split()) == " ".join(" ".join(paras).split())
    for p in paras:
        assert any(p in o for o in out)


def test_split_passages_cuts_long_paragraph_at_sentences():
    sent = "This is a sentence with exactly ten words in it ok. "
    text = sent * 80  # 880 words, one paragraph
    out = D.split_passages(text)
    assert all(len(o.split()) <= 250 for o in out)
    assert all(o.rstrip().endswith("ok.") for o in out)
    assert 3 <= len(out) <= 6


def test_locate_fact():
    ps = ["alpha beta gamma", "the quick brown fox jumps", "delta"]
    assert D.locate_fact(ps, "Quick, brown FOX") == (1, True)
    i, exact = D.locate_fact(ps, "brown cat jumps")
    assert (i, exact) == (1, False)


# ---------------------------------------------------------------- synthetic builds


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _musique_raw(root, n=40):
    corpus, qs = [], []
    for i in range(n):
        for j in range(3):
            corpus.append({"title": f"T{i}_{j}", "text": f"text of paragraph {i} {j} about topic{i}"})
        qs.append({
            "id": f"2hop__{i}_{i + 1}",
            "question": f"what is topic{i}?",
            "answer": f"ans{i}",
            "answer_aliases": [f"alias{i}"],
            "answerable": True,
            "paragraphs": [
                {"idx": j, "title": f"T{i}_{j}",
                 "paragraph_text": f"text of paragraph {i} {j} about topic{i}",
                 "is_supporting": j == 1}
                for j in range(3)
            ],
        })
    d = os.path.join(root, "raw", "musique")
    _write(os.path.join(d, "musique.json"), qs)
    _write(os.path.join(d, "musique_corpus.json"), corpus)


def _mhr_raw(root, n_art=12, n_q=60):
    arts, qs = [], []
    for i in range(n_art):
        body = "\n\n".join(" ".join(f"art{i}p{p}w{k}" for k in range(120)) for p in range(4))
        arts.append({"title": f"Article {i}", "author": None, "source": f"Outlet {i % 3}",
                     "published_at": f"2023-1{i % 3}-0{1 + i % 9}T10:30:00+00:00",
                     "category": "tech", "url": f"https://x.test/{i}", "body": body})
    for k in range(n_q):
        null = k % 5 == 0
        i = k % n_art
        qs.append({"query": f"query {k}", "answer": "Insufficient information." if null else f"a{k}",
                   "question_type": "null_query" if null else "inference_query",
                   "evidence_list": [] if null else [
                       {"title": f"Article {i}", "fact": f"art{i}p2w5 art{i}p2w6"}]})
    d = os.path.join(root, "raw", "multihoprag")
    _write(os.path.join(d, "MultiHopRAG.json"), qs)
    _write(os.path.join(d, "corpus.json"), arts)


def _sizes(root, name, **kw):
    ds = D.load(name, root, **kw)
    return ds, {k: len(v) for k, v in ds.questions.items()}


def test_musique_build_manifest_and_idempotence(tmp_path):
    root = str(tmp_path)
    _musique_raw(root)
    ds, sizes = _sizes(root, "musique", n_dev=5, n_test=20, n_sealed=10)
    assert sizes == {"dev": 5, "test": 20, "sealed": 10}
    q = ds.questions["dev"][0]
    assert q.id.startswith("musique:2hop__") and q.kind == "2hop"
    assert len(q.gold_units) == 1 and q.gold_units[0].startswith("musique:") and q.gold_units[0].endswith("#0")
    assert q.answers[0].startswith("ans") and q.answers[1].startswith("alias")
    man_path = os.path.join(ds.corpus_dir, "MANIFEST.json")
    man = json.load(open(man_path))
    assert man["source"]["revision"] == D.SPECS["musique"]["revision"]
    for f, h in man["files"].items():
        assert D.sha256_file(os.path.join(ds.corpus_dir, f)) == h
    ids = {k: [q.id for q in v] for k, v in ds.questions.items()}
    assert man["splits"]["question_ids_sha256"]["test"] == D.ids_hash(ids["test"])
    assert ds.corpus_tokens == man["corpus_tokens"] > 0
    # idempotent: second load does not rewrite and returns the same splits
    mtime = os.path.getmtime(man_path)
    ds2 = D.load("musique", root, n_dev=5, n_test=20, n_sealed=10)
    assert os.path.getmtime(man_path) == mtime
    assert {k: [q.id for q in v] for k, v in ds2.questions.items()} == ids
    # other sizes do not touch the manifest
    ds3 = D.load("musique", root, n_dev=2, n_test=3, n_sealed=1)
    assert [len(ds3.questions[k]) for k in ("dev", "test", "sealed")] == [2, 3, 1]
    assert os.path.getmtime(man_path) == mtime
    assert D.available(root)["musique"] == "built"


def test_tampered_corpus_is_rebuilt(tmp_path):
    root = str(tmp_path)
    _musique_raw(root, 10)
    cdir = D.build("musique", root, n_dev=2, n_test=3, n_sealed=1)
    good = D.sha256_file(os.path.join(cdir, "units.jsonl"))
    with open(os.path.join(cdir, "units.jsonl"), "a") as fh:
        fh.write("garbage\n")
    assert D.available(root)["musique"] == "raw_downloaded"
    D.build("musique", root, n_dev=2, n_test=3, n_sealed=1)
    assert D.sha256_file(os.path.join(cdir, "units.jsonl")) == good


def test_multihoprag_build_null_dates_and_ingest(tmp_path):
    root = str(tmp_path)
    _mhr_raw(root)
    ds, sizes = _sizes(root, "multihoprag", n_dev=6, n_test=20, n_sealed=10)
    assert sizes == {"dev": 6, "test": 20, "sealed": 10}
    all_q = [q for v in ds.questions.values() for q in v]
    nulls = [q for q in all_q if not q.answerable]
    assert nulls and all(q.answers == () and q.gold_units == () for q in nulls)
    # 20% null overall, preserved in every split
    for name, want in (("dev", 1), ("test", 4), ("sealed", 2)):
        assert sum(not q.answerable for q in ds.questions[name]) == want
    ans = next(q for q in all_q if q.answerable)
    assert ans.gold_units and ans.gold_units[0].startswith("multihoprag:a") and "#" in ans.gold_units[0]
    # the gold passage is the one holding the fact (paragraph 2 of the article)
    events = [json.loads(line) for line in open(os.path.join(ds.corpus_dir, "events.jsonl"))]
    by_unit = {e["unit_id"]: e for e in events}
    assert "p2w5" in by_unit[ans.gold_units[0]]["text"]
    e = events[0]
    assert e["op"] == "create" and len(e["date"]) == 10 and "published" in e["axes"]
    # article title is kept on every passage unit
    units = [json.loads(line) for line in open(os.path.join(ds.corpus_dir, "units.jsonl"))]
    assert all(u["title"].startswith("Article ") for u in units)
    # offline ingest into the store
    from heuresis.ingest import ingest
    from heuresis.model import AsOf, Scope
    from heuresis.store import Store

    st = Store(":memory:")
    counts = ingest(st, ds.corpus_dir, "jsonl")
    assert counts["units"] == len(units) > 0
    hits = st.lexical("art3p2w5", AsOf(), Scope(), 5)
    assert hits and hits[0].unit_id.startswith("multihoprag:")
    # an article is not visible before it was published
    assert st.lexical("art3p2w5", AsOf(valid="2000-01-01"), Scope(), 5) == []


def test_hoh_build_versions_and_as_of(tmp_path):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    rows = []
    for i in range(40):
        rows.append({
            "question": f"how many things does item {i} have?",
            "answer": f"{i + 100}",
            "last_modified_time": __import__("datetime").datetime(2024, 11, 1),
            "evidence": f"Item {i} has {i + 100} things.",
            "outdated_infos": [{"answer": f"{i}", "evidence": f"Item {i} has {i} things.",
                                "last_modified_time": "2024-09-01"}],
            "document": {"id": str(1000 + i // 2), "title": f"Doc {i // 2}"},
        })
    root = str(tmp_path)
    d = os.path.join(root, "raw", "hoh")
    os.makedirs(d)
    pq.write_table(pa.Table.from_pylist(rows), os.path.join(d, "hoh_qas_240601_241201.parquet"))
    ds, sizes = _sizes(root, "hoh", n_dev=5, n_test=10, n_sealed=5)
    assert sizes == {"dev": 5, "test": 10, "sealed": 5}
    events = [json.loads(line) for line in open(os.path.join(ds.corpus_dir, "events.jsonl"))]
    ops = sorted({e["op"] for e in events})
    assert ops == ["create", "replace"]
    q = ds.questions["test"][0]
    assert q.as_of in ("2024-09-01", "2024-11-01") and q.kind in ("outdated", "current")
    from heuresis.ingest import ingest
    from heuresis.model import AsOf, Scope
    from heuresis.store import Store

    st = Store(":memory:")
    ingest(st, ds.corpus_dir, "jsonl")
    p = st.lexical(q.text, AsOf(valid=q.as_of), Scope(), 5)
    got = [x for x in p if x.unit_id == q.gold_units[0]]
    assert got and q.answers[0] in got[0].text
    # unit ids: hoh:<doc>#<n> with n counting records inside a document
    assert {u for e in events for u in [e["unit_id"]]} >= {"hoh:1000#0", "hoh:1000#1"}


def test_unavailable_and_unknown():
    assert D.available(os.path.join("nonexistent_root"))["lawinforce_ecfr"].startswith("unavailable:")
    with pytest.raises(RuntimeError):
        D.load("fiscalqa_pro", "nonexistent_root")
    with pytest.raises(KeyError):
        D.load("nope", "nonexistent_root")


# ---------------------------------------------------------------- real data


@pytest.mark.skipif(not REAL, reason="set HEURESIS_TEST_DATA=1 with built corpora")
@pytest.mark.parametrize("name", ["musique", "multihoprag", "hoh"])
def test_real_dataset(name):
    ds = D.load(name, DATA_ROOT)
    assert [len(ds.questions[k]) for k in ("dev", "test", "sealed")] == [100, 500, 300]
    ids = [q.id for k in ds.questions for q in ds.questions[k]]
    assert len(ids) == len(set(ids)) == 900
    man = json.load(open(ds.meta["manifest"]))
    for f, h in man["files"].items():
        assert D.sha256_file(os.path.join(ds.corpus_dir, f)) == h
    if name == "multihoprag":
        assert man["counts"]["unanswerable"] == 301
        frac = 301 / 2556
        for k, v in ds.questions.items():
            assert abs(sum(not q.answerable for q in v) / len(v) - frac) < 0.02
        assert man["counts"]["sources"] > 1
    if name == "musique":
        assert man["counts"]["questions"] == 1000 and man["counts"]["units"] == 11656
        assert all(q.gold_units for v in ds.questions.values() for q in v)
    if name == "hoh":
        assert all(q.as_of and q.gold_units for v in ds.questions.values() for q in v)
