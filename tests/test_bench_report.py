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
        "closed_book", "bm25", "vector", "hybrid", "hybrid_rerank", "agentic", "long_context",
        "engine", "oracle"}
    assert set(res["paired"]) == {"closed_book", "bm25", "vector", "hybrid", "hybrid_rerank",
                                  "agentic", "long_context"}
    assert all(m["n"] == 12 for m in res["systems"].values())
    assert "engine" in open(os.path.join(out, "results.md")).read()


def test_mean_answer_chars(tmp_path):
    out = str(tmp_path)
    rs = [row("engine", "q1", "answered", "correct", .9, 0.1, 10, text="abcd"),
          row("engine", "q2", "answered", "wrong", .8, 0.1, 10, text="abcdef"),
          row("engine", "q3", "abstained", "abstained", .1, 0.1, 10, text="long abstention text")]
    write(out, rs, systems=("engine",))
    res = report.write(out, iters=50)
    assert res["systems"]["engine"]["mean_answer_chars"] == pytest.approx(5.0)
    assert "mean answer chars" in report.render(res)


def test_asof_variants_are_exploratory_not_in_the_family(tmp_path):
    out = str(tmp_path)
    rs = hand_rows() + [dict(r, system="bm25+asof", time_aware=True)
                        for r in hand_rows() if r["system"] == "bm25"]
    write(out, rs, systems=("engine", "bm25", "bm25+asof"))
    res = report.write(out, iters=100)
    assert set(res["paired"]) == {"bm25"} and set(res["exploratory_paired"]) == {"bm25+asof"}
    assert res["exploratory_systems"] == ["bm25+asof"]
    assert res["paired"]["bm25"]["mcnemar_p_holm"] == pytest.approx(0.5)  # family of one
    md = open(os.path.join(out, "results.md")).read()
    assert "| bm25+asof (exploratory) |" in md and "Table 6. Exploratory" in md


def test_primary_permutation_test_and_holm_by_hand(tmp_path):
    out = str(tmp_path)
    rs = hand_rows() + [dict(r, system="vector", usd=0.02) for r in hand_rows() if r["system"] == "bm25"]
    write(out, rs, systems=("engine", "bm25", "vector"))
    res = report.write(out, iters=500)
    # engine scores 1, 1, 1, -1; bm25 scores 1, -1, -1, 0: differences 0, 2, 2, -1.
    # Of the 8 sign assignments of (2, 2, 1), four reach |sum| >= 3, so p = 0.5.
    p = res["paired"]["bm25"]
    assert p["perm_p"] == pytest.approx(0.5)
    assert p["perm_p_holm"] == pytest.approx(1.0)  # family of two
    assert p["score_diff"]["est"] == pytest.approx(0.75)
    assert "cost_per_correct_diff" not in p  # only agentic and hybrid are compared on cost
    md = open(os.path.join(out, "results.md")).read()
    assert "permutation p" in md and "McNemar p" in md


def test_cost_per_correct_difference_for_agentic_and_hybrid(tmp_path):
    out = str(tmp_path)
    rs = hand_rows()
    for name, usd in (("agentic", 0.04), ("hybrid", 0.01)):
        rs += [dict(r, system=name, usd=usd) for r in hand_rows() if r["system"] == "bm25"]
    write(out, rs, systems=("engine", "bm25", "agentic", "hybrid"))
    res = report.write(out, iters=300)
    # engine: 0.4 usd over 3 correct = 0.1333; agentic: 0.16 over 1 correct = 0.16;
    # hybrid: 0.04 over 1 correct = 0.04
    assert res["paired"]["agentic"]["cost_per_correct_diff"]["est"] == pytest.approx(0.4 / 3 - 0.16)
    assert res["paired"]["hybrid"]["cost_per_correct_diff"]["est"] == pytest.approx(0.4 / 3 - 0.04)
    assert "bm25" in res["paired"] and "cost_per_correct_diff" not in res["paired"]["bm25"]
    md = open(os.path.join(out, "results.md")).read()
    assert "Table 5b" in md and "Table 7" in md


def test_pareto_flags(tmp_path):
    out = str(tmp_path)
    write(out, hand_rows())
    res = report.build(out, iters=50)
    # engine costs 0.1 per question and scores 0.5; bm25 costs 0.01 and scores -0.25: neither dominates
    assert res["pareto"]["engine"]["pareto_penalised_score"] is True
    assert res["pareto"]["bm25"]["pareto_penalised_score"] is True
    assert res["pareto"]["engine"]["mean_usd"] == pytest.approx(0.1)


def test_family_holm_across_datasets(tmp_path):
    results = []
    for i in (1, 2):
        out = str(tmp_path / f"d{i}")
        write(out, hand_rows())
        r = report.build(out, iters=100)
        r["dataset"] = f"d{i}"
        results.append(r)
    rows = report.family(results)
    assert [x["dataset"] for x in rows] == ["d1", "d2"]
    assert all(x["perm_p"] == pytest.approx(0.5) and x["perm_p_holm_family"] == pytest.approx(1.0)
               for x in rows)
    assert "Holm p (family)" in report.render_family(rows)
