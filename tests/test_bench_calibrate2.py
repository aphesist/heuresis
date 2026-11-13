import json
import os
import pathlib

import pytest

from heuresis.bench import calibrate2 as C
from heuresis.bench.run import run
from heuresis.bench.systems import build_context, build_systems
from heuresis.v2.locked import calibration as cal_mod
from heuresis.v2.locked.decide import load_policy
from test_bench_common import Recorder, make_dataset, questions

SH = "ab" * 32


def write_run(path, rows, *, split="dev", dataset="tiny", surface=SH, dry=False):
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "results.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    man = {"dataset": dataset, "split": split, "v2_surface_hash": surface, "dry_run": dry, "systems": []}
    (path / "manifest.json").write_text(json.dumps(man))
    return str(path)


def row(i, conf, outcome, *, status="answered", tau=0.5, below=False, text="", qid=None):
    rp = {"engine": "v2", "status": "abstained" if status != "answered" else "answered", "confidence": conf,
          "tau": tau, "below_tau": below}
    if text:
        rp["candidate_text"] = text
    return {"system": "engine2", "qid": qid or f"q{i:03d}", "status": status, "outcome": outcome,
            "confidence": 0.0 if status != "answered" else conf, "replay": rp, "answerable": True}


def basic_rows():
    rows = [row(i, 0.9, "correct") for i in range(60)]
    rows += [row(100 + i, 0.6, "wrong" if i < 5 else "correct") for i in range(20)]
    rows += [row(200, 0.0, "abstained", status="abstained")]
    rows.append({"system": "closed_book", "qid": "q000", "status": "answered", "outcome": "wrong", "confidence": 0.5})
    return rows


def test_containment_fit_walks_from_the_strictest_threshold(tmp_path):
    d = write_run(tmp_path / "r", basic_rows())
    got = C.collect(d, "containment")
    assert got["n_questions"] == 81 and len(got["conf"]) == 80 and sum(got["wrong"]) == 5
    res = C.calibrate([got], "containment", load_policy())
    f = res["fit"]
    assert f["tau"] == 0.7 and f["n_answered"] == 60 and f["errors"] == 0 and f["upper"] <= 0.05
    by = {r["tau"]: r for r in res["table"]}
    assert by[0.6]["n_answered"] == 80 and by[0.6]["errors"] == 5 and by[0.6]["accepted"] is False
    assert by[0.5].get("walk_stopped") and by[0.9]["coverage"] == pytest.approx(60 / 81)


def test_the_judge_label_flips_rows_the_judge_called_equivalent(tmp_path):
    d = write_run(tmp_path / "r", basic_rows())
    with open(os.path.join(d, "judge.jsonl"), "w") as fh:
        for i in range(5):
            fh.write(json.dumps({"system": "engine2", "qid": f"q{100 + i:03d}", "verdict": "EQUIVALENT"}) + "\n")
        fh.write(json.dumps({"system": "engine2", "qid": "q106", "verdict": "NOT_EQUIVALENT"}) + "\n")
    got = C.collect(d, "judge")
    assert sum(got["wrong"]) == 0
    res = C.calibrate([got], "judge", load_policy())
    assert res["fit"]["tau"] == 0.5 and res["fit"]["n_answered"] == 80


def test_thresholds_below_the_runs_tau_need_graded_held_back_rows(tmp_path):
    qs = {q.id: q for q in questions()}
    rows = [row(i, 0.9, "correct", tau=0.7, qid=f"x{i:03d}") for i in range(60)]
    held = [row(0, 0.5, "abstained", status="abstained", tau=0.7, below=True, qid="q01", text="It is 120 kilometres."),
            row(1, 0.4, "abstained", status="abstained", tau=0.7, below=True, qid="q02", text="Founded in 1851.")]
    d = write_run(tmp_path / "r", rows + held)
    # judge: nobody judged the held-back rows, so taus below the run's are not evaluable
    r = C.calibrate([C.collect(d, "judge")], "judge", load_policy())
    assert r["run_tau"] == 0.7 and not r["below_ok"] and r["ungraded"] == 2
    assert [x["tau"] for x in r["table"] if not x["evaluable"]] == [0.6, 0.5, 0.4, 0.3]
    # containment: graded here against the gold answers (only questions the loader returns)
    got = C.collect(d, "containment", questions=lambda m: qs)
    assert got["held_back"] == 2 and got["ungraded"] == 0 and len(got["conf"]) == 62
    assert got["wrong"][-2:] == [False, True]  # q01 contains "120 kilometres"; q02 says 1851, gold is 1850
    r = C.calibrate([got], "containment", load_policy())
    assert r["below_ok"] and all(x["evaluable"] for x in r["table"])
    # no loader for the questions: the rows stay ungraded and the low thresholds not evaluable
    r2 = C.calibrate([C.collect(d, "containment", questions=lambda m: {})], "containment", load_policy())
    assert not r2["below_ok"]
    text = C.render_table(r, label="containment", dataset="tiny", split="dev", surface_hash=SH, policy=load_policy())
    assert "evaluable" in text and "graded by containment" in text


def test_held_out_runs_are_refused(tmp_path, capsys):
    for sp in ("test", "sealed", "temporal_test"):
        d = write_run(tmp_path / sp, basic_rows(), split=sp)
        with pytest.raises(ValueError, match="held out"):
            C.collect(d, "containment")
        out = tmp_path / f"{sp}.json"
        assert C.main([d, "--label", "containment", "--out", str(out)]) == 2
        assert "held out" in capsys.readouterr().err and not out.exists()


def test_main_writes_a_calibration_file_and_the_table(tmp_path, capsys):
    d = write_run(tmp_path / "r", basic_rows())
    out = tmp_path / "cal" / "tiny.json"
    assert C.main([d, "--label", "containment", "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "| 0.9 | yes | 60 | 0 |" in text and "selected tau: 0.7" in text and "the runs applied tau = 0.5" in text
    c = cal_mod.load(out)
    assert (c.tau, c.dataset, c.split, c.label, c.surface_hash) == (0.7, "tiny", "dev", "containment", SH)
    assert (c.n_questions, c.n_answered, c.errors) == (81, 60, 0) and c.coverage == pytest.approx(60 / 81)
    assert cal_mod.find(out.parent, SH, "tiny") is not None  # the engine finds it; the table file is no calibration
    assert text.startswith(out.with_suffix(".table.md").read_text())
    j = tmp_path / "cal" / "tiny-judge.json"
    assert C.main([d, "--label", "judge", "--out", str(j)]) == 0
    assert cal_mod.load(j).label == "judge_equivalent"


def test_runs_must_agree_and_default_path(tmp_path, capsys):
    a = write_run(tmp_path / "a", basic_rows())
    b = write_run(tmp_path / "b", basic_rows(), surface="cd" * 32)
    assert C.main([a, b, "--label", "containment", "--out", str(tmp_path / "x.json")]) == 2
    assert "share one dataset" in capsys.readouterr().err
    c = write_run(tmp_path / "c", basic_rows(), split="temporal")
    assert C.main([a, c, "--label", "containment", "--out", str(tmp_path / "y.json")]) == 0
    assert cal_mod.load(tmp_path / "y.json").split == "dev+temporal"
    no_v2 = write_run(tmp_path / "n", basic_rows(), surface="")
    assert C.main([no_v2, "--label", "containment", "--out", str(tmp_path / "z.json")]) == 2
    p = C.default_out("law", SH)
    assert p.name == f"law-{SH[:12]}.json"
    assert p.parent.name == "calibration" and p.parent.parent.name == "v2"


def test_end_to_end_on_a_real_engine2_run(tmp_path, capsys):
    ds = make_dataset(tmp_path)
    gen = Recorder(lambda s, p: "The Beta river is 120 kilometres long. [t1]")
    judge = Recorder(lambda s, p: "S1: SUPPORTED\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: NONE")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), v2_llm=gen, judge_llm=judge)
    out = str(tmp_path / "out")
    run(ds, "dev", build_systems(ctx, ["engine2"]), out, None, workers=2, dry_run=True)
    got = C.collect(out, "containment")
    assert got["n_questions"] == 12 and 0 < len(got["conf"]) < 12  # the scripted answer fits some questions only
    assert all(c == pytest.approx(0.9) for c in got["conf"])
    assert C.main([out, "--label", "containment", "--out", str(tmp_path / "c.json")]) == 0
    assert cal_mod.load(tmp_path / "c.json").tau is None  # a handful of answered rows certify nothing
    assert "none (nothing certified" in capsys.readouterr().out


def test_calibration_and_rotating_splits_are_accepted(tmp_path):
    for sp in ("cal0", "rot3", "dev", "dev2", "temporal"):
        d = write_run(tmp_path / sp, basic_rows(), split=sp)
        assert C.collect(d, "containment")["n_questions"] == 81
