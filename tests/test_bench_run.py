import json
import os

from heuresis.bench import report
from heuresis.bench.ledger import Ledger
from heuresis.bench.run import grade, is_correct, run, select_questions
from heuresis.bench.systems import build_context, build_systems
from heuresis.locked.guard import locked_hash
from test_bench_common import Recorder, make_dataset, questions


def _registration():
    """A registration file for the synthetic `test` split (the held-out guard of `main`)."""
    import hashlib
    import tempfile
    ids = [q.id for q in questions()[:4]]
    path = os.path.join(tempfile.mkdtemp(), "REGISTRATION.md")
    with open(path, "w") as fh:
        fh.write("split test ids sha256: " + hashlib.sha256("\n".join(ids).encode()).hexdigest() + "\n")
    return path


REG = _registration()


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


def test_dry_run_ledger_never_stops_a_free_run(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    # cap 0 and the default margin 1.0: a paid run would stop at once
    lg = Ledger(str(tmp_path / "l.jsonl"), cap_usd=0.0, margin_usd=1.0)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), ledger=lg, estimate_usd=0.02)
    systems = build_systems(ctx, ["closed_book", "bm25", "engine"])
    st = run(ds, "dev", systems, out, lg, workers=2, dry_run=True)
    assert st["stopped"] is None and st["written"] == 36 and st["errors"] == 0
    assert lg.spent == 0.0
    assert lg.margin_usd == 0.0 and lg.dry_run
    # a paid run keeps the margin: cap 0 with margin 1.0 stops at once
    paid = Ledger(str(tmp_path / "l2.jsonl"), cap_usd=0.0, margin_usd=1.0)
    ctx2 = build_context(ds, str(tmp_path / "s2.sqlite"), ledger=paid)
    st2 = run(ds, "dev", build_systems(ctx2, ["closed_book"]), str(tmp_path / "out2"), paid,
              workers=1)
    assert st2["stopped"] == "budget" and st2["written"] == 0 and paid.margin_usd == 1.0


def test_cli_dry_run_uses_margin_zero_and_variants(tmp_path, monkeypatch):
    from heuresis.bench import run as R
    ds = make_dataset(tmp_path)
    monkeypatch.setattr(R, "_load_dataset", lambda name: ds)
    out = str(tmp_path / "cli")
    assert R.main(["--dataset", "tiny", "--out", out, "--cap", "0", "--workers", "2",
                   "--systems", "bm25,hybrid,agentic,engine", "--time-aware-variants"]) == 0
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["ledger"]["margin_usd"] == 0.0 and man["last_run"]["stopped"] is None
    names = [s["name"] for s in man["systems"]]
    assert names == ["bm25", "hybrid", "agentic", "engine", "bm25+asof", "hybrid+asof", "agentic+asof"]
    assert len(rows(out)) == 7 * 12
    res = report.write(out, iters=100)
    assert set(res["paired"]) == {"bm25", "hybrid", "agentic"}
    assert set(res["exploratory_paired"]) == {"bm25+asof", "hybrid+asof", "agentic+asof"}


# ----------------------------------------------------------------------------
# Errors treated alike, latency, paid-run guards, provenance
# ----------------------------------------------------------------------------

import time

import pytest

from heuresis.bench.systems import EngineSystem
from heuresis.llm import BudgetExceeded as LLMBudgetExceeded


class Switch:
    """A reply function that fails on demand, as an API outage after retries would."""

    def __init__(self):
        self.fail = True

    def __call__(self, system, prompt):
        if self.fail:
            raise RuntimeError("API outage after retries")
        return "ok\nCONFIDENCE: 60"


def test_model_failure_is_an_error_row_for_every_system_and_is_retried(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    sw = Switch()
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=Recorder(sw))
    systems = build_systems(ctx, ["closed_book", "bm25", "agentic", "engine"])
    st = run(ds, "test", systems, out, None, workers=2)
    rs = rows(out)
    assert st["errors"] == 16 and st["written"] == 16
    assert {r["status"] for r in rs} == {"error"}
    for name in ("closed_book", "bm25", "agentic", "engine"):
        mine = [r for r in rs if r["system"] == name]
        assert len(mine) == 4 and all(r["error"] and r["outcome"] == "error" for r in mine)
        assert all(r["cluster"] is not None and "answerable" in r for r in mine)
    assert any("model failure" in r["error"] for r in rs if r["system"] == "engine")
    # a restart retries all of them, and only them
    sw.fail = False
    st2 = run(ds, "test", systems, out, None, workers=2)
    assert st2["written"] == 16 and st2["errors"] == 0
    _, rr, n_err = report.load(out)
    assert n_err == 0 and len(rr) == 16 and all(r["status"] != "error" for r in rr)


def test_remaining_error_rows_count_as_wrong_and_are_printed_per_system(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=Recorder(Switch()))
    run(ds, "test", build_systems(ctx, ["bm25", "engine"]), out, None, workers=1)
    res = report.build(out, iters=200)
    for name in ("bm25", "engine"):
        m = res["systems"][name]
        assert m["errors"] == 4 and m["counts"]["wrong"] == 4 and m["n"] == 4
        assert m["penalised_score"]["est"] == -1.0 and m["coverage"] == 0.0
    assert res["error_rows"] == 8
    md = report.render(res)
    assert "bm25: 4" in md and "engine: 4" in md and "counted as wrong" in md


def test_engine_budget_stop_is_neither_an_error_nor_a_row(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    rec = Recorder(lambda s, p: "ok\nCONFIDENCE: 60", usd=0.4)
    lg = Ledger(str(tmp_path / "l.jsonl"), cap_usd=0.5, margin_usd=0.0)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec, ledger=lg, estimate_usd=0.4)
    st = run(ds, "dev", build_systems(ctx, ["engine"]), out, lg, workers=1)
    assert st["stopped"] == "budget" and st["errors"] == 0
    assert all(r["status"] != "error" and "budget" not in r["note"] for r in rows(out))
    assert len(rows(out)) < 12
    # the same at the system level: the engine raises like a baseline whose call is refused
    ctx2 = build_context(ds, str(tmp_path / "s2.sqlite"), llm=rec,
                         ledger=Ledger(str(tmp_path / "l2.jsonl"), cap_usd=0.1, margin_usd=0.0),
                         estimate_usd=0.4)
    with pytest.raises(LLMBudgetExceeded):
        EngineSystem(ctx2).answer(questions()[0])


def test_engine_system_turns_a_model_failure_into_an_error_result(tmp_path):
    ds = make_dataset(tmp_path)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=Recorder(Switch()))
    r = EngineSystem(ctx).answer(questions()[0])
    assert r.error.startswith("model failure") and r.status == "abstained"
    ok = EngineSystem(build_context(ds, str(tmp_path / "s2.sqlite"))).answer(questions()[0])
    assert ok.error == "" and ok.replay["verified"]


def test_latency_is_wall_clock_around_answer_for_every_system(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")

    def slow(system, prompt):
        time.sleep(0.03)
        return "ok\nCONFIDENCE: 60"

    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=Recorder(slow))
    run(ds, "test", build_systems(ctx, ["closed_book", "engine"]), out, None, workers=2)
    for r in rows(out):
        assert r["ms"] >= 25, r["system"]
        if r["system"] == "engine":
            # the stage sum is read from several separate clock reads (and the retrieve stage
            # repeats its sub-stages' time), so under CPU load it can exceed the wall clock by a few ms
            assert r["stage_ms"] is not None and r["stage_ms"] <= r["ms"] + 15
        else:
            assert r["stage_ms"] is None
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["workers"] == 2 and "2 concurrent workers" in man["latency_note"]
    assert "2 concurrent workers" in report.render(report.build(out, iters=100))


def test_manifest_records_model_provenance(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    run(ds, "test", build_systems(ctx, ["closed_book"]), out, None, workers=1, dry_run=True)
    man = json.load(open(os.path.join(out, "manifest.json")))
    prov = man["model_provenance"]
    assert prov["generator"] == {"id": "echo", "temperature": None, "thinking": None,
                                 "max_tokens": 600, "note": "offline fake"}
    for role, mid in (("embedder", "hash-256"), ("reranker", "overlap"), ("entailer", "rules")):
        assert prov[role]["id"] == mid and prov[role]["note"] == "offline fake"


def _paid_env(tmp_path, monkeypatch):
    from heuresis import llm as llm_mod, models_local
    from heuresis.bench import run as R
    from heuresis.fakes import HashEmbedder, OverlapReranker, RuleEntailer
    from heuresis.model import Usage

    made = []

    class Spy(llm_mod.AnthropicLLM):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            made.append(self)

        def complete(self, system, prompt, *, max_tokens=600):  # never touches the network
            return "ok\nCONFIDENCE: 50", Usage(model=self.model, tokens_in=10, tokens_out=5,
                                                usd=0.0001)

    monkeypatch.setattr(llm_mod, "AnthropicLLM", Spy)
    monkeypatch.setattr(models_local, "load_embedder", lambda *a, **k: HashEmbedder())
    monkeypatch.setattr(models_local, "load_reranker", lambda *a, **k: OverlapReranker())
    monkeypatch.setattr(models_local, "load_entailer", lambda *a, **k: RuleEntailer())
    ds = make_dataset(tmp_path)
    monkeypatch.setattr(R, "_load_dataset", lambda name: ds)
    return R, made


def test_paid_run_without_ledger_is_refused(tmp_path, monkeypatch, capsys):
    R, made = _paid_env(tmp_path, monkeypatch)
    monkeypatch.setenv("PROJECTS_ANTHROPIC_KEY", "sk-secret-value")
    out = str(tmp_path / "out")
    assert R.main(["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--paid", "--cap", "5",
                   "--out", out, "--systems", "closed_book"]) == 2
    assert "--ledger" in capsys.readouterr().err
    assert not os.path.exists(out) and not made
    # a dry run needs no shared ledger
    assert R.main(["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--out", out,
                   "--systems", "closed_book"]) == 0


def test_paid_run_reads_the_default_key_variable_and_prints_only_its_name(tmp_path, monkeypatch, capsys):
    R, made = _paid_env(tmp_path, monkeypatch)
    monkeypatch.setenv("PROJECTS_ANTHROPIC_KEY", "sk-secret-value")
    out, ledger = str(tmp_path / "out"), str(tmp_path / "shared.jsonl")
    assert R.main(["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--paid", "--cap", "5", "--ledger", ledger,
                   "--out", out, "--systems", "closed_book", "--workers", "1"]) == 0
    cap = capsys.readouterr()
    assert made[0].key_env == "PROJECTS_ANTHROPIC_KEY" and made[0].temperature is None
    assert "PROJECTS_ANTHROPIC_KEY" in cap.err and "https://api.anthropic.com" in cap.err
    assert "sk-secret-value" not in cap.out + cap.err
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert "sk-secret-value" not in json.dumps(man)
    assert man["ledger"]["path"] == ledger and man["dry_run"] is False
    assert man["model_provenance"]["generator"] == {
        "id": "claude-haiku-5-5", "temperature": None, "thinking": {"type": "disabled"},
        "max_tokens": 600,
        "note": "not sent: the model rejects the parameter; sampling is the API default"}
    assert made[0].thinking == {"type": "disabled"}
    assert os.path.getsize(ledger) > 0


def test_thinking_flag_default_restores_the_model_default(tmp_path, monkeypatch):
    R, made = _paid_env(tmp_path, monkeypatch)
    monkeypatch.setenv("PROJECTS_ANTHROPIC_KEY", "sk-x")
    out, ledger = str(tmp_path / "out"), str(tmp_path / "l.jsonl")
    assert R.main(["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--paid", "--cap", "5", "--ledger", ledger,
                   "--out", out, "--systems", "closed_book", "--workers", "1",
                   "--thinking", "default"]) == 0
    assert made[0].thinking is None
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["model_provenance"]["generator"]["thinking"] is None


def test_rows_and_ledger_record_stop_reason_and_blocks(tmp_path):
    from heuresis.bench.ledger import Ledger
    from heuresis.model import Usage
    from heuresis.bench.systems import add_call_record
    led = Ledger(str(tmp_path / "l.jsonl"), 5.0, 0.0)
    led.charge(Usage(model="claude-haiku-5-5", tokens_in=10, tokens_out=600, usd=0.0003,
                     stop_reason="max_tokens", blocks={"thinking": 1}, text_chars=0), "closed_book")
    led.charge(Usage(model="claude-haiku-5-5", usd=0.0), "old")  # no stop reason: old row shape
    rows = [json.loads(x) for x in open(led.path)]
    assert rows[0]["stop_reason"] == "max_tokens" and rows[0]["blocks"] == {"thinking": 1}
    assert rows[0]["text_chars"] == 0 and "stop_reason" not in rows[1]
    tot = Usage()
    add_call_record(tot, Usage(stop_reason="end_turn", blocks={"text": 1}, text_chars=20))
    add_call_record(tot, Usage(stop_reason="max_tokens", blocks={"thinking": 1, "text": 1}, text_chars=5))
    assert tot.stop_reason == "end_turn,max_tokens"
    assert tot.blocks == {"text": 2, "thinking": 1} and tot.text_chars == 25


def test_paid_run_key_env_can_be_renamed_and_must_be_set_before_any_work(tmp_path, monkeypatch, capsys):
    R, made = _paid_env(tmp_path, monkeypatch)
    monkeypatch.delenv("PROJECTS_ANTHROPIC_KEY", raising=False)
    monkeypatch.delenv("MY_BENCH_KEY", raising=False)
    monkeypatch.setattr(R, "_load_dataset", lambda name: pytest.fail("work started"))
    out, ledger = str(tmp_path / "out"), str(tmp_path / "l.jsonl")
    base = ["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--paid", "--cap", "5", "--ledger", ledger,
            "--out", out, "--systems", "closed_book", "--workers", "1"]
    assert R.main(base) == 2
    assert "PROJECTS_ANTHROPIC_KEY" in capsys.readouterr().err
    assert R.main(base + ["--key-env", "MY_BENCH_KEY"]) == 2
    err = capsys.readouterr().err
    assert "MY_BENCH_KEY" in err and not made and not os.path.exists(out) and not os.path.exists(ledger)
    # set: it is read from the renamed variable only
    monkeypatch.undo()
    R, made = _paid_env(tmp_path, monkeypatch)
    monkeypatch.delenv("PROJECTS_ANTHROPIC_KEY", raising=False)
    monkeypatch.setenv("MY_BENCH_KEY", "sk-other-secret")
    assert R.main(base + ["--key-env", "MY_BENCH_KEY"]) == 0
    cap = capsys.readouterr()
    assert made[0].key_env == "MY_BENCH_KEY" and "MY_BENCH_KEY" in cap.err
    assert "sk-other-secret" not in cap.out + cap.err


def test_set_overrides_a_config_value_and_the_manifest_records_it(tmp_path, monkeypatch, capsys):
    R, made = _paid_env(tmp_path, monkeypatch)
    out = str(tmp_path / "out")
    assert R.main(["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--out", out, "--systems", "engine",
                   "--set", "draft.prompt=v1", "--set", "verify.answers_question=true"]) == 0
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["engine_config"]["draft"]["prompt"] == "v1"
    assert man["engine_config"]["verify"]["answers_question"] is True
    base = json.load(open(os.path.join(str(tmp_path / "o2"), "manifest.json"))) if R.main(
        ["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--out", str(tmp_path / "o2"), "--systems", "engine"]) == 0 else None
    assert base["engine_config"]["draft"]["prompt"] == "v2" and base["surface_hash"] != man["surface_hash"]
    for bad in ("draft.nope=1", "nosection.x=1", "draft=1", "draft.prompt"):
        assert R.main(["--dataset", "tiny", "--split", "test", "--registered-run", REG, "--out", str(tmp_path / "o3"),
                       "--set", bad]) == 2


def test_manifest_records_each_engines_effective_config(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    run(ds, "dev2", build_systems(ctx, ["bm25", "engine", "engine_single"]), out, None, workers=2,
        dry_run=True, limit=3)
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["split"] == "dev2"
    ec = man["engine_configs"]
    assert set(ec) == {"engine", "engine_single"}
    assert (ec["engine"]["answer"]["mode"], ec["engine"]["decide"]["mode"]) == ("search", "grade")
    assert (ec["engine_single"]["answer"]["mode"], ec["engine_single"]["decide"]["mode"]) == ("single", "strict")
    assert ec["engine"]["draft"]["max_sentences"] == 2 and man["engine_config"] == ec["engine"]
    by = {s["name"]: s for s in man["systems"]}
    assert by["engine_single"]["exploratory"] is True and by["engine"]["exploratory"] is False
    assert by["engine"]["answer_mode"] == "search" and by["engine_single"]["answer_mode"] == "single"
    names = {r["system"] for r in rows(out)}
    assert names == {"bm25", "engine", "engine_single"}


# --- held-out guard, rotating splits, engine2 flags ---------------------------------------------


def _dry(R, tmp_path, *extra, split="test", systems="closed_book", out="o"):
    return R.main(["--dataset", "tiny", "--split", split, "--out", str(tmp_path / out), "--systems", systems,
                   "--workers", "1", *extra])


def test_held_out_splits_need_a_matching_registration_even_in_a_dry_run(tmp_path, monkeypatch, capsys):
    R, made = _paid_env(tmp_path, monkeypatch)
    wrong = tmp_path / "WRONG.md"
    wrong.write_text("sha256 0000\n")
    for extra in ([], ["--registered-run", str(wrong)], ["--registered-run", str(tmp_path / "none.md")]):
        assert _dry(R, tmp_path, *extra) == 2
        assert "held out" in capsys.readouterr().err
        assert not os.path.exists(tmp_path / "o")
    assert _dry(R, tmp_path, "--registered-run", REG) == 0
    man = json.load(open(os.path.join(str(tmp_path / "o"), "manifest.json")))
    assert man["split"] == "test" and len(man["split_ids_sha256"]) == 64 and man["split_ids_sha256"] in open(REG).read()
    assert _dry(R, tmp_path, split="dev", out="o2") == 0  # a dev split needs nothing
    # a paid run is refused before any client exists
    monkeypatch.setenv("PROJECTS_ANTHROPIC_KEY", "sk-x")
    assert _dry(R, tmp_path, "--paid", "--cap", "5", "--ledger", str(tmp_path / "l.jsonl"), out="o3") == 2
    assert not made and not os.path.exists(tmp_path / "o3")


def test_promotion_sets_are_never_readable_from_the_cli(tmp_path, monkeypatch, capsys):
    R, made = _paid_env(tmp_path, monkeypatch)
    assert _dry(R, tmp_path, "--registered-run", REG, split="promo0") == 2
    assert "promotion" in capsys.readouterr().err and not os.path.exists(tmp_path / "o")


def test_a_rotating_split_is_drawn_from_the_pool_and_run(tmp_path, monkeypatch):
    from test_bench_splits import make_root
    R, made = _paid_env(tmp_path, monkeypatch)
    root, rows = make_root(tmp_path, name="tiny", n=2000)
    out = str(tmp_path / "rot")
    assert R.main(["--dataset", "tiny", "--split", "rot1", "--data-root", root, "--out", out,
                   "--systems", "closed_book", "--limit", "5", "--workers", "1"]) == 0
    man = json.load(open(os.path.join(out, "manifest.json")))
    from heuresis.bench import splits
    ids = splits.rotating("tiny", 1, root=root)
    assert man["split"] == "rot1" and set(man["question_ids"]) <= set(ids) and man["n_questions"] == 5
    assert man["split_ids_sha256"] == splits._ids_sha(ids)
    assert R.main(["--dataset", "tiny", "--split", "rot99", "--data-root", root, "--out", str(tmp_path / "r9"),
                   "--systems", "closed_book"]) == 2  # the pool has no cycle 99
    out2 = str(tmp_path / "cal")  # a calibration block is not held out: it runs without a registration
    assert R.main(["--dataset", "tiny", "--split", "cal0", "--data-root", root, "--out", out2,
                   "--systems", "closed_book", "--limit", "3", "--workers", "1"]) == 0
    assert json.load(open(os.path.join(out2, "manifest.json")))["n_questions"] == 3


def test_engine2_flags_surface_candidate_and_calibration(tmp_path, monkeypatch, capsys):
    R, made = _paid_env(tmp_path, monkeypatch)
    hashes = {}
    for tag, extra in (("base", []), ("set", ["--v2-set", "agent.max_turns=2"]),
                       ("both", ["--v2-set", "agent.max_turns=2", "--v2-candidate", None])):
        if extra and extra[-1] is None:
            cand = tmp_path / "cand.json"
            cand.write_text(json.dumps({"config": {"retrieve.k_first": 5}, "prompts": {}}))
            extra = extra[:-1] + [str(cand)]
        assert _dry(R, tmp_path, *extra, split="dev", systems="engine2", out=tag) == 0
        man = json.load(open(os.path.join(str(tmp_path / tag), "manifest.json")))
        assert len(man["protected_hash"]) == 64 and man["judge_model"] == "echo" and man["v2_cache"] is False
        hashes[tag] = man["v2_surface_hash"]
    assert len(set(hashes.values())) == 3
    for bad in (["--v2-set", "agent.max_turns=99"], ["--v2-set", "nope.key=1"], ["--v2-set", "novalue"],
                ["--v2-candidate", str(tmp_path / "missing.json")], ["--v2-calibration", str(tmp_path / "no.json")]):
        assert _dry(R, tmp_path, *bad, split="dev", systems="engine2", out="bad") == 2
        assert "error" in capsys.readouterr().err
    assert not os.path.exists(tmp_path / "bad")


def test_engine2_paid_clients_judge_strong_and_cache(tmp_path, monkeypatch):
    R, made = _paid_env(tmp_path, monkeypatch)
    monkeypatch.setenv("PROJECTS_ANTHROPIC_KEY", "sk-x")
    out, ledger = str(tmp_path / "out"), str(tmp_path / "l.jsonl")
    assert R.main(["--dataset", "tiny", "--split", "dev", "--paid", "--cap", "5", "--ledger", ledger, "--out", out,
                   "--systems", "engine2", "--workers", "1", "--limit", "2", "--thinking", "default",
                   "--judge-model", "claude-haiku-5-5", "--strong-model", "claude-haiku-5-5",
                   "--v2-cache"]) == 0
    assert len(made) == 5  # generator, support gate, judge, strong, cached engine2 generator
    assert made[0].cache is False and made[0].thinking is None
    assert made[2].thinking == {"type": "disabled"} and made[2].cache is False  # judge
    assert made[3].cache is False and made[3].thinking is None                  # strong: generator's thinking
    assert made[4].cache is True and made[4].thinking is None                   # engine2 generator
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["v2_cache"] is True and man["judge_model"] == "claude-haiku-5-5" == man["strong_model"]
    from heuresis.v2.locked.decide import load_policy
    assert man["judge_model_policy"] == load_policy().judge_model and man["judge_is_policy_model"] is False
    # no --judge-model: the judge is the policy's model, not the generator
    made.clear()
    out3 = str(tmp_path / "out3")
    assert R.main(["--dataset", "tiny", "--split", "dev", "--paid", "--cap", "5", "--ledger", ledger, "--out", out3,
                   "--systems", "engine2", "--workers", "1", "--limit", "1"]) == 0
    assert made[2].model == load_policy().judge_model and made[2].thinking == {"type": "disabled"}
    m3 = json.load(open(os.path.join(out3, "manifest.json")))
    assert m3["judge_is_policy_model"] is True and m3["judge_model"] == load_policy().judge_model
    tags = {json.loads(x)["tag"] for x in open(ledger)}
    assert "engine2" in tags and "engine" not in tags  # the fake reply never reaches the judge
