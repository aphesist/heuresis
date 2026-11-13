"""scripts/brlaw/analyse_v2.py on synthetic run folders (invented content, nothing read from data/)."""
import importlib.util
import json
import math
import os
import sys
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "analyse_v2", os.path.join(os.path.dirname(__file__), "..", "scripts", "brlaw", "analyse_v2.py"))
A = importlib.util.module_from_spec(SPEC)
sys.modules["analyse_v2"] = A
SPEC.loader.exec_module(A)

N = 40
SYS = A.SYSTEMS
GEN = {"closed_book": 0.001, "hybrid": 0.002, "agentic": 0.003, "agentic+asof": 0.003, "engine": 0.004, "engine2": 0.002}
JUDGE_USD = 0.0075
EXISTS_REASON = "a cited mark does not exist or the sentence cites nothing"


def _tainted(s, i):
    return {"closed_book": i % 4 == 0, "hybrid": i % 6 == 0, "agentic": i % 8 == 0, "agentic+asof": i % 10 == 0,
            "engine": i == 3, "engine2": False}[s]


def _answered(s, i):
    return (i + SYS.index(s)) % 5 != 0


def _equivalent(s, i):
    return {"closed_book": i % 3 == 0, "hybrid": i % 2 == 0, "agentic": i % 2 == 0, "agentic+asof": i % 2 == 0,
            "engine": i % 3 != 0, "engine2": i % 4 != 0}[s]


def _replay(i, answered):
    if not answered:
        return {"engine": "v2", "status": "abstained", "confidence": 0.1, "abstention": "unsupported", "below_tau": False,
                "claims": [{"text": "Frase", "kind": "fact", "label": "unsupported", "support": 0.0,
                            "checks": {"exists": True, "valid_at_date": True, "numbers_traced": True, "references_traced": True},
                            "note": "", "passage_marks": [], "tool_marks": []}],
                "meta": {"dropped": [{"text": "Frase", "reason": "withheld: no supported sentence"}], "repairs": 0,
                         "verdict": {"answer": "no", "sufficient": "no"}},
                "raw_usage_by_stage": {"judge": {"usd": JUDGE_USD}}}
    claims = [{"text": "Frase ok", "kind": "fact", "label": "supported", "support": 1.0,
               "checks": {"exists": True, "valid_at_date": True, "numbers_traced": True, "references_traced": True},
               "note": "", "passage_marks": ["p1"], "tool_marks": []}]
    dropped = []
    if i % 3 == 0:    # a sentence the gates removed
        claims.append({"text": "Frase gate", "kind": "fact", "label": "unsupported", "support": 0.0,
                       "checks": {"exists": False, "valid_at_date": True, "numbers_traced": True, "references_traced": True},
                       "note": EXISTS_REASON, "passage_marks": [], "tool_marks": []})
        dropped.append({"text": "Frase gate", "reason": EXISTS_REASON})
    if i % 4 == 0:    # a sentence the judge removed
        claims.append({"text": "Frase juiz", "kind": "fact", "label": "unsupported", "support": 0.0,
                       "checks": {"exists": True, "valid_at_date": True, "numbers_traced": True, "references_traced": True},
                       "note": "", "passage_marks": ["p1"], "tool_marks": []})
        dropped.append({"text": "Frase juiz", "reason": "dropped by the judge"})
    return {"engine": "v2", "status": "answered", "confidence": 0.9, "abstention": None, "below_tau": False,
            "claims": claims, "meta": {"dropped": dropped, "repairs": 1, "verdict": {"answer": "yes", "sufficient": "yes"}},
            "raw_usage_by_stage": {"judge": {"usd": JUDGE_USD}}}


def write_run(folder, split, *, judge=True, citations=True, temporal=False, drop_system=None, n=N):
    folder.mkdir(parents=True)
    rows, an, jr, sup = [], [], [], []
    for s in SYS:
        if s == drop_system:
            continue
        for i in range(n):
            qid = f"q{i:03d}"
            ans = _answered(s, i)
            usd = GEN[s] + (JUDGE_USD if s == "engine2" else 0.0)
            row = {"system": s, "qid": qid, "split": split, "status": "answered" if ans else "abstained",
                   "text": "delta echo" if (ans and i % 2 == 0) else "bravo charlie" if ans else "",
                   "usd": usd, "calls": 2, "searches": 1, "ms": 100 + i, "kind": "temporal" if temporal else "",
                   "answerable": True, "cluster": "U1" if temporal else "", "gold_units": ["U1#v1"] if temporal else []}
            if s == "engine2":
                row["replay"] = _replay(i, ans)
            rows.append(row)
            if ans and _tainted(s, i):
                refs = [{"status": "unit_not_found", "in_force": None, "unit_ids": [], "meta": {}}]
            elif ans:
                refs = [{"status": "resolved", "in_force": True, "unit_ids": ["U1"], "meta": {}}]
            else:
                refs = []
            an.append({"system": s, "qid": qid, "status": row["status"], "kind": row["kind"], "as_of": None,
                       "analysis": {"refs": refs, "n_refs": len(refs)}, "gold_units": row["gold_units"],
                       "answerable": True, "cluster": row["cluster"]})
            if ans:
                jr.append({"system": s, "qid": qid, "verdict": "EQUIVALENT" if _equivalent(s, i) else "NOT_EQUIVALENT"})
                if refs:
                    sup.append({"system": s, "qid": qid, "unit": "U1", "reference": "r", "verdict": "SUPPORTED" if i % 2 else "UNSUPPORTED"})
    (folder / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (folder / "manifest.json").write_text(json.dumps({"split": split, "dataset": "synthetic"}))
    if citations:
        (folder / "citations.jsonl").write_text("\n".join(json.dumps(r) for r in an) + "\n")
        (folder / "citation_support.jsonl").write_text("\n".join(json.dumps(r) for r in sup) + "\n")
    if judge:
        (folder / "judge.jsonl").write_text("\n".join(json.dumps(r) for r in jr) + "\n")


class FakeStore:
    def versions(self, uid):
        return [SimpleNamespace(text="alfa bravo charlie"), SimpleNamespace(text="alfa delta echo")]


def covers_all(meta):
    return True


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "F"
    write_run(r / "brlaw-core-t-test", "test")
    write_run(r / "brlaw-core-t-temporal_test", "temporal_test", judge=False, temporal=True)
    return r


def test_holm_family_and_mcnemar_match_the_registered_definition(root):
    res = A.analyse(str(root), store=FakeStore(), covers=covers_all)
    assert set(res["sets"]) == {"test", "temporal_test"} and res["reference"] == "engine2"
    assert res["holm_family_size"] == 10        # 4 baselines x 2 sets + 2 non-inferiority tests
    t = res["sets"]["test"]
    assert t["questions"] == N and t["complete_cases"] == N
    tn = t["tainted"]["strict"]["closed_book"]
    answered = [i for i in range(N) if _answered("closed_book", i)]
    only = sum(1 for i in answered if _tainted("closed_book", i))       # engine2 is never tainted
    assert (tn["reference_only_tainted"], tn["other_only_tainted"]) == (0, only)
    assert tn["p_raw"] == pytest.approx(min(1.0, 2 * 0.5 ** only))
    assert tn["p_holm"] >= tn["p_raw"] and tn["reference_tainted_lower"] is True
    assert "p_holm" not in t["tainted"]["covered_only"]["closed_book"]    # exploratory, outside the family
    ni = t["tainted"]["strict"]["engine"]["non_inferiority"]
    assert ni["non_inferior"] is True and ni["margin"] == 0.01 and "p_holm" in ni
    assert t["tainted"]["strict"]["engine"]["in_holm_family"] is False      # engine enters through its NI test only


def test_systems_coverage_useful_and_cost_split(root):
    t = A.analyse(str(root), store=FakeStore(), covers=covers_all)["sets"]["test"]
    e2, ag = t["systems"]["engine2"], t["systems"]["agentic"]
    n_ans = sum(_answered("engine2", i) for i in range(N))
    assert e2["answered"] == n_ans and e2["abstained"] == N - n_ans
    assert e2["coverage"][0] == pytest.approx(n_ans / N, abs=1e-4) and e2["coverage"][1] < e2["coverage"][0] < e2["coverage"][2]
    assert e2["tainted_all"][0] == 0 and e2["tainted_covered_only_all"][0] == 0
    want = sum(_answered("engine2", i) and _equivalent("engine2", i) for i in range(N))
    assert e2["useful"][0] == want
    want_ag = sum(_answered("agentic", i) and not _tainted("agentic", i) and _equivalent("agentic", i) for i in range(N))
    assert ag["useful"][0] == want_ag                              # tainted answers are not useful
    assert e2["usd_per_question"] == pytest.approx(0.0095)
    assert e2["usd_per_question_judge"] == pytest.approx(JUDGE_USD) and e2["usd_per_question_generator"] == pytest.approx(0.002)
    assert e2["usd_per_useful"] == pytest.approx(0.0095 * N / want, abs=1e-5)
    assert e2["usd_per_useful_judge"] == pytest.approx(JUDGE_USD * N / want, abs=1e-5)
    assert ag["usd_judge"] == 0.0 or ag["usd_per_question_judge"] == 0.0
    assert t["h6"]["engine2_minus_engine"]["usd_per_useful_diff"][0] > 0   # the judge dominates the cost


def test_h1_and_h3_checks(root):
    t = A.analyse(str(root), store=FakeStore(), covers=covers_all)["sets"]["test"]
    h1 = t["h1"]
    d = t["useful_diffs"]["agentic"]["diff_reference_minus_system"]
    assert h1["non_inferior_to_agentic"]["margin"] == -0.03
    assert h1["non_inferior_to_agentic"]["holds"] == (h1["non_inferior_to_agentic"]["lower_one_sided_95"] > -0.03)
    assert d[1] <= d[0] <= d[2]
    assert h1["superior_to_engine"]["holds"] == (h1["superior_to_engine"]["diff_ci95"][1] > 0)
    assert {"p_holm"} <= set(h1["superior_to_engine"]) and {"p_holm"} <= set(h1["non_inferior_to_agentic"])
    assert set(t["useful_diffs"]) == {"closed_book", "hybrid", "agentic", "agentic+asof", "engine"}


def test_h4_paired_with_a_store_and_unpaired_without(root):
    h = A.analyse(str(root), store=FakeStore(), covers=covers_all)["sets"]["temporal_test"]["h4"]
    assert h["paired"] is True
    v = h["vs_agentic+asof"]
    assert v["gold_version"]["n"] == N and v["reference_only"] + v["comparator_only"] <= N
    assert v["h4_not_supported"] in (True, False) and 0 <= v["p_one_sided_reference_fewer"] <= 1
    assert sum(h["outcomes"]["engine2"].values()) == N
    h2 = A.analyse(str(root), covers=covers_all)["sets"]["temporal_test"]["h4"]
    assert h2["paired"] is False and "vs_agentic+asof" not in h2
    assert "useful" not in A.analyse(str(root), covers=covers_all)["sets"]["temporal_test"]["systems"]["engine2"]  # no judge file


def test_reference_drops_by_reason_from_the_replay_payload(root):
    rp = A.analyse(str(root), covers=covers_all)["sets"]["test"]["reference_replay"]
    complete = range(N)
    gate = sum(1 for i in complete if _answered("engine2", i) and i % 3 == 0)
    judge = sum(1 for i in complete if _answered("engine2", i) and i % 4 == 0)
    withheld = sum(1 for i in complete if not _answered("engine2", i))
    assert rp["rows_with_replay"] == N
    assert rp["dropped_by_reason"] == {k: v for k, v in {"gate: exists": gate, "judge: unsupported": judge,
                                                         "withheld (answer not given)": withheld}.items() if v}
    assert rp["claims_failing_check"] == {"exists": gate}
    assert rp["abstention_types"] == {"unsupported": withheld} and rp["dropped_claims"] == gate + judge + withheld
    assert rp["judge_verdicts"]["answer"]["yes"] == N - withheld


def test_any_layout_missing_systems_and_missing_files(tmp_path):
    one = tmp_path / "just_one_run"
    write_run(one, "test", drop_system="agentic+asof")
    res = A.analyse(str(one), covers=covers_all)          # a single run folder, a system missing
    R = res["sets"]["test"]
    assert R["systems_missing"] == ["agentic+asof"] and "agentic+asof" not in R["systems"]
    assert res["holm_family_size"] == 3 + 1               # three baselines and the non-inferiority test
    no_ref = tmp_path / "noref"
    write_run(no_ref, "test", drop_system="engine2")
    with pytest.raises(SystemExit, match="reference system"):
        A.analyse(str(no_ref), covers=covers_all)
    nocit = tmp_path / "nocit"
    write_run(nocit, "test", citations=False)
    with pytest.raises(SystemExit, match="bench.citations"):
        A.analyse(str(nocit), covers=covers_all)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SystemExit, match="no run folder"):
        A.analyse(str(empty), covers=covers_all)


def test_a_root_with_other_runs_skips_those_without_citations(tmp_path):
    r = tmp_path / "B"
    write_run(r / "brlaw-core-dev", "dev")
    write_run(r / "musique-dev2", "dev2", citations=False)
    res = A.analyse(str(r), covers=covers_all)
    assert list(res["sets"]) == ["dev"] and [os.path.basename(f) for f in res["skipped_folders"]] == ["musique-dev2"]


def test_incomplete_questions_are_dropped_from_the_complete_cases(tmp_path):
    r = tmp_path / "r"
    write_run(r, "test")
    lines = (r / "results.jsonl").read_text().splitlines()
    keep = [l for l in lines if not (json.loads(l)["system"] == "engine" and json.loads(l)["qid"] in {"q000", "q001"})]
    (r / "results.jsonl").write_text("\n".join(keep) + "\n")
    R = A.analyse(str(r), covers=covers_all)["sets"]["test"]
    assert R["questions"] == N and R["complete_cases"] == N - 2


def test_cli_writes_json_and_prints_no_text(root, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(A.sys, "argv", ["analyse_v2.py"])
    out = tmp_path / "analysis.json"
    assert A.main([str(root), str(out)]) == 0
    printed = capsys.readouterr().out
    doc = json.loads(out.read_text())
    assert doc["holm_family_size"] == 10 and "written" in printed
    assert "bravo" not in printed and "bravo" not in out.read_text()     # answer texts never leave the rows
    assert math.isclose(doc["sets"]["test"]["systems"]["engine2"]["usd_per_question"], 0.0095)
