"""Offline replay of verification and the threshold grid (bench.calibrate)."""
import json
import os

import pytest

from heuresis.bench import calibrate, report
from heuresis.bench.ledger import Ledger
from heuresis.bench.run import run
from heuresis.bench.systems import build_context, build_systems
from heuresis.surface.config import load_config


def strict_cfg():
    """The earlier design, where thresholds decide: the threshold tests below are about it."""
    cfg = load_config()
    cfg.answer.mode, cfg.decide.mode = "single", "strict"
    return cfg
from test_bench_common import Recorder, make_dataset, questions

EXTRA = ["", " and extremely mysterious", " and extremely mysterious faraway uncharted",
         " and extremely mysterious faraway uncharted legendary hidden"]


def varied_reply(system, prompt):
    """An extractive draft padded with words the passage lacks, so that the entailment
    score differs from question to question and the thresholds matter."""
    line = next((ln for ln in prompt.splitlines() if ln.startswith("[t1]")), None)
    if line is None:
        return "ABSTAIN no_source: nothing."
    body = line.split(") ", 1)[1].rstrip(".")
    return f"{body}{EXTRA[len(prompt) % 4]}. [t1]"


def engine_run(tmp_path, name, split="dev", config=None, reply=varied_reply):
    config = config or strict_cfg()
    ds = make_dataset(tmp_path / name)
    out = str(tmp_path / name / "out")
    ctx = build_context(ds, str(tmp_path / name / "s.sqlite"), llm=Recorder(reply), config=config)
    run(ds, split, build_systems(ctx, ["engine"]), out, None, workers=1, dry_run=True)
    return out


def engine_rows(out):
    _, rows, _ = report.load(out)
    return sorted((r for r in rows if r["system"] == "engine"), key=lambda r: r["qid"])


def test_engine_rows_store_what_replay_needs(tmp_path):
    out = engine_run(tmp_path, "a")
    rows = engine_rows(out)
    assert len(rows) == 12
    r = next(x for x in rows if x["replay"]["verified"])
    rp = r["replay"]
    assert rp["draft_raw"].strip().endswith("[t1]")
    p = rp["passages"][0]
    assert {"unit_id", "seq", "mark", "text", "coverage", "certainty", "valid_from", "valid_to"} <= set(p)
    assert p["mark"] == "t1"
    c = rp["claims"][0]
    assert 0.0 <= c["support"] <= 1.0 and set(c["checks"]) == {"exists", "valid_at_date", "numbers_traced"}
    assert rp["thresholds"] == {"support": 0.5, "partial": 0.3}
    assert "tool_results" in rp and rp["answers"] is not None
    # the wall-clock ms and the engine's stage sum are separate fields
    assert r["ms"] > 0 and r["stage_ms"] is not None


def test_replay_at_the_run_thresholds_reproduces_every_stored_outcome(tmp_path):
    out = engine_run(tmp_path, "a")
    cfg = strict_cfg()
    seen = set()
    for r in engine_rows(out):
        s, p = r["replay"]["thresholds"]["support"], r["replay"]["thresholds"]["partial"]
        status, text, grade = calibrate.replay(r, s, p, cfg)
        assert calibrate.run_status(status) == r["status"]
        assert text == r["text"]
        assert grade == pytest.approx(r["confidence"])
        g = calibrate.outcome_of(r, status, text)
        assert g["outcome"] == r["outcome"] and g["score"] == r["score"]
        seen.add(status)
    assert "answered" in seen  # not only abstentions


@pytest.mark.parametrize("s,p", [(0.9, 0.1), (0.7, 0.7), (0.3, 0.3), (0.2, 0.1), (0.8, 0.5)])
def test_replay_at_other_thresholds_equals_a_fresh_run_at_them(tmp_path, s, p):
    base = engine_rows(engine_run(tmp_path, "base"))
    cfg = strict_cfg()
    cfg.verify.support_threshold, cfg.verify.partial_threshold = s, p
    fresh = {r["qid"]: r for r in engine_rows(engine_run(tmp_path, f"f{s}{p}", config=cfg))}
    for r in base:
        status, text, grade = calibrate.replay(r, s, p, strict_cfg())
        f = fresh[r["qid"]]
        assert calibrate.run_status(status) == f["status"], r["qid"]
        assert text == f["text"] and grade == pytest.approx(f["confidence"])


def test_thresholds_matter_somewhere(tmp_path):
    rows = engine_rows(engine_run(tmp_path, "a"))
    cfg = strict_cfg()
    outs = {calibrate.replay(r, s, p, cfg)[0] for r in rows for s, p in ((0.95, 0.9), (0.1, 0.1))}
    assert len(outs) >= 2


def test_replay_without_payload_is_refused():
    with pytest.raises(ValueError, match="replay payload"):
        calibrate.replay({"system": "engine", "qid": "x"}, 0.5, 0.3, strict_cfg())


def test_grid_has_45_pairs_and_the_stated_tie_break(tmp_path):
    out = engine_run(tmp_path, "a")
    table, best = calibrate.grid(out)
    assert len(table) == 45 and all(r["partial"] <= r["support"] for r in table)
    assert {r["support"] for r in table} == set(calibrate.THRESHOLDS)
    top = max(r["sum"] for r in table)
    tied = [r for r in table if r["sum"] == top]
    want = max(tied, key=lambda r: (r["support"], r["partial"]))
    assert (best["support"], best["partial"]) == (want["support"], want["partial"])
    assert best["score"] == pytest.approx(top / best["n"]) and best["n"] == 12
    assert "proposed" in best["tie_break"] and best["packaged"]["support"] == 0.5
    # the row at the run's own thresholds equals the stored mean score
    stored = sum(r["score"] for r in engine_rows(out)) / 12
    at = next(r for r in table if (r["support"], r["partial"]) == (0.5, 0.3))
    assert at["score"] == pytest.approx(stored)


def test_grid_tie_goes_to_higher_support_then_higher_partial(tmp_path):
    # every draft abstains, so every pair ties at 0 on answerable questions
    out = engine_run(tmp_path, "abst", reply=lambda s, p: "ABSTAIN no_source: x")
    table, best = calibrate.grid(out)
    assert len({r["sum"] for r in table}) == 1
    assert (best["support"], best["partial"]) == (0.9, 0.9)


def test_grid_pools_run_folders(tmp_path):
    a = engine_run(tmp_path, "a")
    b = engine_run(tmp_path, "b")
    table, best = calibrate.grid([a, b])
    one, _ = calibrate.grid(a)
    assert best["n"] == 24 and table[0]["sum"] == pytest.approx(2 * one[0]["sum"])


def test_dev_only(tmp_path, capsys):
    test_out = engine_run(tmp_path, "t", split="test")
    with pytest.raises(calibrate.CalibrationRefused, match="not 'dev'"):
        calibrate.grid(test_out)
    with pytest.raises(calibrate.CalibrationRefused):
        calibrate.grid(test_out, split="test")
    dev = engine_run(tmp_path, "d")
    with pytest.raises(calibrate.CalibrationRefused):
        calibrate.grid([dev, test_out])
    assert calibrate.main([test_out]) == 2
    assert "not 'dev'" in capsys.readouterr().err


def test_cli_prints_table_and_argmax(tmp_path, capsys):
    out = engine_run(tmp_path, "a")
    assert calibrate.main([out]) == 0
    text = capsys.readouterr().out
    assert "DRY RUN" in text and "Argmax" in text and "Tie-break" in text
    assert text.count("\n| 0.") == 45


def test_error_rows_count_as_wrong_at_every_pair(tmp_path):
    out = engine_run(tmp_path, "a")
    path = os.path.join(out, "results.jsonl")
    rows = [json.loads(x) for x in open(path)]
    victim = next(r for r in rows if r["system"] == "engine" and r["qid"] == "q01")
    victim.pop("replay", None)
    victim.update({"status": "error", "outcome": "error", "error": "boom"})
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    table, _ = calibrate.grid(out)
    assert all(r["errors"] == 1 and r["wrong"] >= 1 for r in table)


def test_dev2_is_a_dev_split_for_calibration(tmp_path, capsys):
    out2 = engine_run(tmp_path, "d2", split="dev2")
    table, best = calibrate.grid(out2, split="dev2")
    assert len(table) == 45 and best["n"] == 7
    with pytest.raises(calibrate.CalibrationRefused, match="not 'dev'"):
        calibrate.grid(out2)  # a dev2 folder is not a dev folder
    dev = engine_run(tmp_path, "d")
    with pytest.raises(calibrate.CalibrationRefused):
        calibrate.grid([dev, out2], split="dev2")  # nor may the two be mixed
    assert calibrate.main([out2, "--split", "dev2"]) == 0
    assert "Argmax" in capsys.readouterr().out
    for bad in ("test", "sealed"):
        with pytest.raises(calibrate.CalibrationRefused, match="dev splits"):
            calibrate.grid(out2, split=bad)
        with pytest.raises(SystemExit):
            calibrate.main([out2, "--split", bad])


def test_grade_mode_replay_does_not_depend_on_the_thresholds(tmp_path):
    out = engine_run(tmp_path, "g", config=load_config())  # the default: search + grade
    rows = engine_rows(out)
    cfg = load_config()
    assert cfg.decide.mode == "grade"
    seen = set()
    for r in rows:
        base = calibrate.replay(r, 0.5, 0.3, cfg)
        for s, p in ((0.95, 0.9), (0.1, 0.1), (0.7, 0.2)):
            assert calibrate.replay(r, s, p, cfg) == base
        status, text, grade = base
        assert calibrate.run_status(status) == r["status"] and text == r["text"]
        assert grade == pytest.approx(r["confidence"])
        seen.add(status)
    assert "answered" in seen


def test_grade_mode_replay_drops_only_deterministic_failures(tmp_path):
    row = {"system": "engine", "qid": "x", "text": "", "answerable": True, "replay": {
        "version": 1, "verified": True, "engine_status": "partial", "grade": 0.2, "answers": ["blue"],
        "passages": [{"unit_id": "u", "seq": 0, "mark": "t1", "text": "The sky is blue.", "title": "",
                      "coverage": 4, "certainty": "high", "valid_from": None, "valid_to": None}],
        "tool_results": [],
        "draft_raw": "The sky is blue [t1]. Grass is green [t1]. It is 42 [t1]. Ghost [t9].",
        "claims": [
            {"text": "The sky is blue.", "passage_marks": ["t1"], "tool_marks": [], "support": 0.9,
             "checks": {"exists": True, "valid_at_date": True, "numbers_traced": True}},
            {"text": "Grass is green.", "passage_marks": ["t1"], "tool_marks": [], "support": 0.1,
             "checks": {"exists": True, "valid_at_date": True, "numbers_traced": True}},
            {"text": "It is 42.", "passage_marks": ["t1"], "tool_marks": [], "support": 0.9,
             "checks": {"exists": True, "valid_at_date": True, "numbers_traced": False}},
            {"text": "Ghost.", "passage_marks": ["t9"], "tool_marks": [], "support": 0.0,
             "checks": {"exists": False, "valid_at_date": True, "numbers_traced": True}}]}}
    status, text, grade = calibrate.replay(row, 0.5, 0.3, load_config())
    assert status == "partial" and grade == 0.1
    assert "blue" in text and "green" in text and "42" not in text and "Ghost" not in text
    status, text, grade = calibrate.replay(row, 0.5, 0.3, strict_cfg())
    assert "green" not in text  # the earlier rule removes the low-support sentence too


def test_engine_single_rows_are_replayed_with_their_own_strict_config(tmp_path):
    ds = make_dataset(tmp_path / "es")
    out = str(tmp_path / "es" / "out")
    ctx = build_context(ds, str(tmp_path / "es" / "s.sqlite"), llm=Recorder(varied_reply))
    run(ds, "dev", build_systems(ctx, ["engine", "engine_single"]), out, None, workers=1, dry_run=True)
    table, best = calibrate.grid(out, system="engine_single")
    assert best["n"] == 12 and len({r["sum"] for r in table}) > 1  # strict: thresholds matter
    flat, _ = calibrate.grid(out, system="engine")
    assert len({r["sum"] for r in flat}) == 1  # grade: they do not
    assert calibrate.main([out, "--system", "engine_single"]) == 0
