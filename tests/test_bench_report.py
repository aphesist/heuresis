import json
import os

import pytest

from heuresis.bench import report, stats
from heuresis.bench.run import run
from heuresis.bench.systems import build_context, build_systems
from test_bench_common import make_dataset


def row(system, qid, status, outcome, conf, usd, ms, **kw):
    score = {"correct": 1.0, "wrong": -1.0, "abstained": 0.0}[outcome]
    r = {"system": system, "qid": qid, "split": "dev", "status": status, "text": "", "confidence": conf,
         "cited_units": [], "retrieved_units": [], "tokens_in": 100, "tokens_out": 10, "usd": usd,
         "ms": ms, "calls": 2, "searches": 1, "answerable": True, "as_of": None, "kind": "",
         "cluster": "", "gold_units": [], "time_aware": system == "engine", "outcome": outcome,
         "correct": outcome == "correct", "score": score, "f1": None}
    r.update(kw)
    return r


def write(out, rows, dry=False, systems=("engine", "bm25")):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "results.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    with open(os.path.join(out, "manifest.json"), "w") as fh:
        json.dump({"dataset": "hand", "split": "dev", "n_questions": 4, "dry_run": dry,
                   "systems": [{"name": s, "available": True} for s in systems],
                   "price_table": "anthropic-2026-11"}, fh)


def hand_rows():
    eng = [("correct", .9), ("correct", .8), ("correct", .7), ("wrong", .6)]
    bm = [("correct", .9), ("wrong", .8), ("wrong", .3), ("abstained", .5)]
    rs = []
    for i, (o, c) in enumerate(eng, 1):
        rs.append(row("engine", f"q{i}", "answered", o, c, 0.1, 10 * i,
                      gold_units=["u1"], cited_units=["u1", "u2"], retrieved_units=["u1"]))
    for i, (o, c) in enumerate(bm, 1):
        rs.append(row("bm25", f"q{i}", "abstained" if o == "abstained" else "answered", o, c, 0.01, 5 * i,
                      gold_units=["u1"], retrieved_units=["u2"]))
    return rs


def test_hand_computed_numbers(tmp_path):
    out = str(tmp_path)
    write(out, hand_rows())
    res = report.write(out, iters=500)
    e, b = res["systems"]["engine"], res["systems"]["bm25"]
    assert e["n"] == 4 and e["counts"] == {"correct": 3, "wrong": 1, "abstained": 0}
    assert e["wilson"]["correct"]["lo"] == pytest.approx(stats.wilson_interval(3, 4)[0])
    assert e["penalised_score"]["est"] == pytest.approx(0.5) and b["penalised_score"]["est"] == pytest.approx(-0.25)
    assert e["accuracy"] == 0.75 and e["coverage"] == 1.0 and e["selective_accuracy"] == 0.75
    assert b["coverage"] == 0.75 and b["selective_accuracy"] == pytest.approx(1 / 3)
    assert e["aurc"] == pytest.approx(0.0625)  # risks 0,0,0,0.25
    assert e["risk_coverage"][-1] == [1.0, 0.25]
    assert e["cost"]["total_usd"] == pytest.approx(0.4)
    assert e["cost_per_correct"]["est"] == pytest.approx(0.4 / 3)
    assert b["cost_per_correct"]["est"] == pytest.approx(0.04)
    assert e["latency_ms"]["median"] == 25.0 and e["mean_calls"] == 2.0
    assert e["citation"]["precision"] == pytest.approx(0.5) and e["citation"]["recall"] == 1.0
    assert b["citation"] is None and b["retrieval_recall"]["value"] == 0.0
    p = res["paired"]["bm25"]
    assert p["n"] == 4 and p["reference_only_correct"] == 2 and p["other_only_correct"] == 0
    assert p["score_diff"]["est"] == pytest.approx(0.75)
    assert p["mcnemar_p"] == pytest.approx(0.5) and p["mcnemar_p_holm"] == pytest.approx(0.5)
    md = open(os.path.join(out, "results.md")).read()
    assert "split `dev`" in md and "| engine | 4 |" in md and "DRY RUN" not in md
    assert json.load(open(os.path.join(out, "results.json")))["systems"]["engine"]["n"] == 4


def test_oracle_excluded_and_holm_family(tmp_path):
    out = str(tmp_path)
    rs = hand_rows() + [dict(r, system="oracle") for r in hand_rows() if r["system"] == "engine"]
    rs += [dict(r, system="vector") for r in hand_rows() if r["system"] == "bm25"]
    write(out, rs, systems=("engine", "bm25", "oracle", "vector"))
    res = report.build(out, iters=100)
    assert set(res["paired"]) == {"bm25", "vector"}
    assert res["paired"]["bm25"]["mcnemar_p_holm"] == pytest.approx(1.0)  # 2 * 0.5


def test_dry_run_banner(tmp_path):
    out = str(tmp_path)
    write(out, hand_rows(), dry=True)
    report.write(out, iters=100)
    for f in ("results.md", "results.json"):
        text = open(os.path.join(out, f), encoding="utf-8").read()
        assert "DRY RUN — offline fakes, not a measurement" in text[:200]
    assert open(os.path.join(out, "results.md"), encoding="utf-8").read().startswith("DRY RUN — offline fakes, not a measurement\n")
    assert json.load(open(os.path.join(out, "results.json"), encoding="utf-8"))["banner"] == "DRY RUN — offline fakes, not a measurement"


def test_banner_first_line_of_json_file(tmp_path):
    out = str(tmp_path)
    write(out, hand_rows(), dry=True)
    report.write(out, iters=100)
    head = open(os.path.join(out, "results.json"), encoding="utf-8").read().splitlines()[:2]
    assert "DRY RUN" in head[1]


def test_end_to_end_dry_run(tmp_path):
    ds = make_dataset(tmp_path)
    out = str(tmp_path / "out")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    run(ds, "dev", build_systems(ctx), out, None, workers=2, dry_run=True)
    res = report.write(out, iters=200)
    assert res["dry_run"] and set(res["systems"]) == {
        "closed_book", "bm25", "vector", "hybrid_rerank", "agentic", "long_context", "engine", "oracle"}
    assert all(m["n"] == 12 for m in res["systems"].values())
    assert "engine" in open(os.path.join(out, "results.md")).read()
