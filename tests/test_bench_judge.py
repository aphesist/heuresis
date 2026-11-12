import json
import os

import pytest

from heuresis.bench import judge, report
from heuresis.bench.run import run
from heuresis.bench.systems import build_context, build_systems
from heuresis.model import Usage
from test_bench_common import Recorder, make_dataset


def make_run(tmp_path, split="dev"):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    # every system answers, wrongly in the containment grader's eyes for most questions
    llm = Recorder(lambda s, p: "It is the thing described in the text, roughly.\nCONFIDENCE: 60")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=llm)
    run(ds, split, build_systems(ctx, ["closed_book", "bm25"]), out, None, workers=1, dry_run=True)
    return ds, out


class Judge:
    id = "judge"

    def __init__(self, verdict=lambda prompt: "EQUIVALENT"):
        self.verdict, self.prompts = verdict, []

    def complete(self, system, prompt, *, max_tokens=600):
        self.prompts.append(prompt)
        assert system == judge.JUDGE_SYSTEM and max_tokens <= 20
        return self.verdict(prompt), Usage(model="judge", tokens_in=40, tokens_out=2, usd=0.0001,
                                           stop_reason="end_turn")


def test_parse_verdict():
    p = judge.parse_verdict
    assert p("EQUIVALENT") == "EQUIVALENT" and p(" equivalent\n") == "EQUIVALENT"
    assert p("NOT_EQUIVALENT") == "NOT_EQUIVALENT" and p("not equivalent") == "NOT_EQUIVALENT"
    assert p("maybe") is None and p("") is None


def test_only_answered_wrong_answerable_rows_are_judged_and_the_primary_grade_is_untouched(tmp_path):
    ds, out = make_run(tmp_path)
    before = open(os.path.join(out, "results.jsonl")).read()
    qs = {q.id: q for q in ds.questions["dev"]}
    llm = Judge(lambda prompt: "EQUIVALENT" if "How long is the Beta river?" in prompt else "NOT_EQUIVALENT")
    st = judge.judge_folder(out, qs, llm, workers=1)
    _, rows, _ = report.load(out)
    want = [r for r in rows if r["status"] == "answered" and r["answerable"] and r["outcome"] == "wrong"]
    assert st["candidates"] == len(want) == st["judged"] and len(want) > 0
    assert not any(q in p for p in llm.prompts for q in ("Omega", "Sigma", "Kappa"))  # unanswerable
    v = judge.load_verdicts(out)
    assert set(v) == {(r["system"], r["qid"]) for r in want}
    assert {x["verdict"] for x in v.values()} == {"EQUIVALENT", "NOT_EQUIVALENT"}
    assert all(x["stop_reason"] == "end_turn" for x in v.values())
    assert open(os.path.join(out, "results.jsonl")).read() == before  # never overwritten
    # the prompt carries the question, the gold answers and the answer without marks
    assert "Gold answers: 120 kilometres" in next(p for p in llm.prompts if "Beta river" in p)
    # resumable: a second pass judges nothing
    n = len(llm.prompts)
    st2 = judge.judge_folder(out, qs, llm, workers=1)
    assert st2["judged"] == 0 and st2["already"] == st["candidates"] and len(llm.prompts) == n


def test_report_adds_secondary_columns_and_leaves_the_primary_ones(tmp_path):
    ds, out = make_run(tmp_path)
    plain = report.build(out, iters=50)
    assert "judge" not in plain
    qs = {q.id: q for q in ds.questions["dev"]}
    judge.judge_folder(out, qs, Judge(), workers=1)
    res = report.build(out, iters=50)
    for s in ("closed_book", "bm25"):
        j = res["judge"][s]
        assert j["flipped"] == j["judged"] > 0
        assert res["systems"][s]["counts"] == plain["systems"][s]["counts"]  # primary unchanged
        assert j["counts"]["correct"] == plain["systems"][s]["counts"]["correct"] + j["flipped"]
        assert j["counts"]["wrong"] == plain["systems"][s]["counts"]["wrong"] - j["flipped"]
        assert j["penalised_score"]["est"] > res["systems"][s]["penalised_score"]["est"]
    md = report.render(res)
    assert "Table 1b" in md and "judge-assisted" in md and "exploratory" in md


def test_dev_only_and_dry_run_and_paid_needs_the_ledger(tmp_path, capsys, monkeypatch):
    ds, out = make_run(tmp_path, split="test")
    qs = {q.id: q for q in ds.questions["test"]}
    with pytest.raises(ValueError):
        judge.judge_folder(out, qs, Judge())
    assert judge.main([out]) == 2  # refused on the command line too
    ds2, out2 = make_run(tmp_path / "d")
    from heuresis.bench import run as R
    monkeypatch.setattr(R, "_load_dataset", lambda name: ds2)
    assert judge.main([out2]) == 0  # no --paid: counts only, nothing called, no side file
    assert json.loads(capsys.readouterr().out)["to_judge"] > 0
    assert not os.path.exists(os.path.join(out2, "judge.jsonl"))
    assert judge.main([out2, "--paid", "--cap", "1"]) == 2
    monkeypatch.delenv("PROJECTS_ANTHROPIC_KEY", raising=False)
    assert judge.main([out2, "--paid", "--cap", "1", "--ledger", str(tmp_path / "l.jsonl")]) == 2


def test_dev2_folders_may_be_judged(tmp_path, monkeypatch):
    ds, out = make_run(tmp_path / "d2", split="dev2")
    qs = {q.id: q for q in ds.questions["dev2"]}
    st = judge.judge_folder(out, qs, Judge(), workers=1)
    assert st["candidates"] > 0 and st["judged"] == st["candidates"]
    assert judge.DEV_SPLITS == ("dev", "dev2")
