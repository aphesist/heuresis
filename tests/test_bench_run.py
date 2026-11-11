import json
import os

from heuresis.bench import report
from heuresis.bench.ledger import Ledger
from heuresis.bench.run import grade, is_correct, run, select_questions
from heuresis.bench.systems import build_context, build_systems
from heuresis.locked.guard import locked_hash
from test_bench_common import Recorder, make_dataset, questions


def rows(out):
    with open(os.path.join(out, "results.jsonl")) as fh:
        return [json.loads(x) for x in fh]


def test_grading_rules():
    assert is_correct("The river is 120 Kilometres long [t1].", ("120 kilometres",))
    assert not is_correct("It has 1200 pupils", ("120",))  # token boundary
    assert is_correct("Fundação em 1850.", ("fundacao",))   # accent folding
    q = questions()[0]
    assert grade(q, "answered", "120 kilometres")["outcome"] == "correct"
    assert grade(q, "answered", "far")["outcome"] == "wrong"
    assert grade(q, "abstained", "")["outcome"] == "abstained"
    un = questions()[8]
    assert grade(un, "abstained", "")["outcome"] == "correct"
    assert grade(un, "answered", "anything")["score"] == -1.0


def test_select_questions_deterministic():
    qs = list(questions())
    a = select_questions(qs[::-1], 5, seed=3)
    assert a == select_questions(qs, 5, seed=3) and len(a) == 5
    assert [q.id for q in a] == sorted(q.id for q in a)
    assert select_questions(qs, None, 0) == sorted(qs, key=lambda q: q.id)


def test_run_writes_manifest_and_rows(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    lg = Ledger(str(tmp_path / "l.jsonl"), 10.0)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), ledger=lg)
    systems = build_systems(ctx, ["closed_book", "bm25", "engine", "long_context"])
    st = run(ds, "dev", systems, out, lg, workers=3, dry_run=True)
    assert st["written"] == 48 and st["stopped"] is None
    rs = rows(out)
    assert {(r["system"], r["qid"]) for r in rs} == {(s.name, q.id) for s in systems for q in questions()}
    assert all(r["outcome"] in ("correct", "wrong", "abstained") for r in rs)
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["locked_hash"] == locked_hash() and man["dry_run"] is True
    assert man["price_table"] == "anthropic-2026-11" and man["surface_hash"] and man["config"]
    assert man["models"]["generator"] == "echo" and man["models"]["embedder"] == "hash-256"
    assert {s["name"]: s["time_aware"] for s in man["systems"]}["engine"] is True
    # limit picks a deterministic subset; a second run of the same folder skips everything
    assert run(ds, "dev", systems, out, lg, workers=2, dry_run=True)["written"] == 0


def test_resume_and_budget_stop(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    rec = Recorder(lambda s, p: "ok\nCONFIDENCE: 60", usd=0.4)
    lg = Ledger(str(tmp_path / "l1.jsonl"), cap_usd=1.0, margin_usd=0.0)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec, ledger=lg, estimate_usd=0.4)
    systems = build_systems(ctx, ["closed_book", "bm25"])
    st = run(ds, "dev", systems, out, lg, workers=1)
    assert st["stopped"] == "budget" and st["written"] == 2
    assert len(rows(out)) == 2 and lg.spent == 0.8
    assert os.path.exists(os.path.join(out, "manifest.json"))
    assert json.load(open(os.path.join(out, "manifest.json")))["last_run"]["stopped"] == "budget"
    # torn last line from a crash is tolerated
    with open(os.path.join(out, "results.jsonl"), "a") as fh:
        fh.write('{"system": "bm25", "qid"')
    lg2 = Ledger(str(tmp_path / "l2.jsonl"), cap_usd=100.0)
    ctx2 = build_context(ds, str(tmp_path / "s.sqlite"), llm=Recorder(lambda s, p: "ok\nCONFIDENCE: 60"),
                         ledger=lg2)
    st2 = run(ds, "dev", build_systems(ctx2, ["closed_book", "bm25"]), out, lg2, workers=2)
    assert st2["skipped"] == 2 and st2["written"] == 22 and st2["stopped"] is None
    keys = [(r["system"], r["qid"]) for r in rows_ok(out)]
    assert len(keys) == len(set(keys)) == 24


def rows_ok(out):
    good = []
    for line in open(os.path.join(out, "results.jsonl")):
        try:
            good.append(json.loads(line))
        except ValueError:
            pass
    return good


def test_failing_system_is_recorded_and_retried(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    calls = {"n": 0}

    def flaky(s, p):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return "ok\nCONFIDENCE: 60"

    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=Recorder(flaky))
    systems = build_systems(ctx, ["closed_book"])
    st = run(ds, "test", systems, out, None, workers=1)
    assert st["errors"] == 1 and st["written"] == 4
    st = run(ds, "test", systems, out, None, workers=1)
    assert st["written"] == 1  # only the failed one is retried
    _, rs, n_err = report.load(out)
    assert len(rs) == 4 and n_err == 0
