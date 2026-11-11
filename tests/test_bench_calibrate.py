"""Offline replay of verification and the threshold grid (bench.calibrate)."""
import json
import os

import pytest

from heuresis.bench import calibrate, report
from heuresis.bench.ledger import Ledger
from heuresis.bench.run import run
from heuresis.bench.systems import build_context, build_systems
from heuresis.surface.config import load_config
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
    cfg = load_config()
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
    cfg = load_config()
    cfg.verify.support_threshold, cfg.verify.partial_threshold = s, p
    fresh = {r["qid"]: r for r in engine_rows(engine_run(tmp_path, f"f{s}{p}", config=cfg))}
    for r in base:
        status, text, grade = calibrate.replay(r, s, p, load_config())
        f = fresh[r["qid"]]
        assert calibrate.run_status(status) == f["status"], r["qid"]
        assert text == f["text"] and grade == pytest.approx(f["confidence"])


def test_thresholds_matter_somewhere(tmp_path):
    rows = engine_rows(engine_run(tmp_path, "a"))
    cfg = load_config()
    outs = {calibrate.replay(r, s, p, cfg)[0] for r in rows for s, p in ((0.95, 0.9), (0.1, 0.1))}
    assert len(outs) >= 2


def test_replay_without_payload_is_refused():
    with pytest.raises(ValueError, match="replay payload"):
        calibrate.replay({"system": "engine", "qid": "x"}, 0.5, 0.3, load_config())


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
