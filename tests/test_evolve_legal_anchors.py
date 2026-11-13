"""Legal anchors are scored with what code can score, never with the penalised containment score."""
import json
from pathlib import Path

from heuresis.bench.types import Question
from heuresis.evolve import promotion as P
from heuresis.evolve.evaluator import Evaluator
from heuresis.evolve.splits import to_pool

CFG = {"error_rate_points": 0.02, "coverage_points": 0.05, "cost_ratio": 1.25, "anchor_score_se": 2.0,
       "version_points": 0.05}


def arows(n, *, status="answered", usd=0.01, temporal=None, graded=False, outcome="wrong", split="temporal"):
    return [{"qid": f"l{i:02d}", "status": status, "outcome": outcome, "usd": usd, "tainted": False,
             "dataset": "brlaw-core", "split": split, "graded": graded, "temporal": temporal, "cluster": f"c{i}"}
            for i in range(n)]


def dev(n=12):
    return [{"qid": f"d{i}", "status": "answered", "outcome": "correct", "usd": 0.01, "tainted": False,
             "cluster": f"d{i}"} for i in range(n)]


def test_config_names_a_dataset_the_loader_accepts():
    cfg = json.loads((Path(P.__file__).parent / "config.json").read_text())
    assert "brlaw-core" in cfg["anchors"] and "brlaw" not in cfg["anchors"]
    assert cfg["guard_rails"]["version_points"] == 0.05


def test_the_penalised_score_is_not_applied_to_ungraded_anchor_rows():
    # every legal row is "wrong" by containment in both runs, and the candidate differs only by noise in outcome
    cand = arows(20, outcome="wrong")
    champ = arows(20, outcome="correct")          # would be a huge score drop if it were graded
    r = P.guard_rails(dev(), dev(), cand, champ, CFG)
    assert r["anchor_score"]["ok"] and "no anchor rows" in r["anchor_score"]["detail"]
    assert r["anchor_ungraded"]["ok"] and P.rails_ok(r)
    graded = P.guard_rails(dev(), dev(), arows(20, graded=True, outcome="wrong"),
                           arows(20, graded=True, outcome="correct"), CFG)
    assert not graded["anchor_score"]["ok"]       # the same rows, graded, do fail the score rail


def test_ungraded_rails_use_coverage_cost_and_version_in_force():
    base = arows(20, temporal="gold_version")
    assert P.guard_rails(dev(), dev(), base, base, CFG)["anchor_ungraded"]["ok"]
    abst = arows(10) + arows(10, status="abstained")
    abst = [{**a, "qid": f"l{i:02d}"} for i, a in enumerate(abst)]
    assert not P.guard_rails(dev(), dev(), abst, arows(20), CFG)["anchor_ungraded"]["ok"]            # coverage
    assert not P.guard_rails(dev(), dev(), arows(20, usd=0.02), arows(20), CFG)["anchor_ungraded"]["ok"]  # cost
    worse = arows(20, temporal="other_version")
    r = P.guard_rails(dev(), dev(), worse, base, CFG)["anchor_ungraded"]
    assert not r["ok"] and "version in force" in r["detail"]
    r2 = P.guard_rails(dev(), dev(), base, worse, CFG)["anchor_ungraded"]
    assert r2["ok"]


def test_tainted_legal_anchor_answer_still_fails_rail_one():
    bad = [{**a, "tainted": True} for a in arows(20)]
    assert not P.guard_rails(dev(), dev(), bad, arows(20), CFG)["no_tainted_anchor"]["ok"]


def test_evaluator_keeps_the_graded_flag_and_temporal_outcome(tmp_path):
    ev = Evaluator(tmp_path, offline=True, allow_unpinned=True)
    q = to_pool(Question(id="l1", text="t?", answers=("x",)), "brlaw-core", "temporal")
    row = ev._norm_row({"status": "answered", "text": "x", "graded": False, "temporal": "gold_version"}, q, "anchor")
    assert row["graded"] is False and row["temporal"] == "gold_version" and row["text"] == ""
    assert ev._norm_row({"status": "answered", "text": "x"}, q, "anchor")["graded"] is True
