import json
import os

import pytest

from heuresis.bench.ledger import BudgetExceeded, Ledger
from heuresis.bench.run import run
from heuresis.bench.systems import (
    DEFAULT_SYSTEMS, SYSTEM_NAMES, LegalPrompts, build_context, build_systems,
)
from heuresis.bench.systems_v2 import EngineV2System
from heuresis.model import Usage
from heuresis.v2.locked import calibration as cal_mod
from heuresis.v2.locked.schema import apply_overrides, load_surface, surface_hash
from test_bench_common import Recorder, make_dataset, questions

GEN = "The Beta river is 120 kilometres long. [t1]"
JUDGE = "S1: SUPPORTED\nANSWER: DIRECT\nSUFFICIENT: YES\nPREMISE: OK\nCONFLICT: NONE"


def ctx_for(tmp_path, *, gen=None, judge=None, **kw):
    ds = kw.pop("ds", None) or make_dataset(tmp_path)
    gen = gen or Recorder(lambda s, p: GEN)
    judge = judge or Recorder(lambda s, p: JUDGE)
    return build_context(ds, str(tmp_path / "s.sqlite"), v2_llm=gen, judge_llm=judge, **kw), gen, judge


def test_registered_but_not_a_default_system():
    assert "engine2" in SYSTEM_NAMES and "engine2" not in DEFAULT_SYSTEMS


def test_engine2_answers_with_checked_citations_and_a_replay_without_passage_text(tmp_path):
    ctx, gen, judge = ctx_for(tmp_path)
    s = build_systems(ctx, ["engine2"])[0]
    assert isinstance(s, EngineV2System) and s.cites and s.time_aware and s.name == "engine2"
    r = s.answer(questions()[0])
    assert r.status == "answered" and r.error == "" and r.cited_units == ("u2",)
    assert r.confidence == pytest.approx(0.9) and r.calls == 2 and r.searches >= 1
    assert r.usage.tokens_in > 0 and r.stage_ms is not None
    rp = r.replay
    assert rp["engine"] == "v2" and rp["status"] == "answered" and rp["abstention"] is None
    assert rp["confidence"] == pytest.approx(0.9) and rp["meta"]["engine"] == "v2"
    c = rp["claims"][0]
    assert set(c) == {"text", "kind", "label", "support", "checks", "note", "passage_marks", "tool_marks"}
    assert c["label"] == "supported" and c["passage_marks"] == ["t1"] and c["checks"]["exists"] is True
    assert {"mark", "unit_id", "seq", "valid_from", "valid_to", "coverage", "certainty", "stage"} == set(rp["passages"][0])
    assert rp["raw_usage_by_stage"]["draft"]["n"] == 1 and rp["raw_usage_by_stage"]["judge"]["n"] == 1
    blob = json.dumps(rp)
    assert "Theta museum" not in blob and "closes on Mondays" not in blob  # no passage text
    assert gen.prompts and judge.prompts  # separate generator and judge clients


def test_engine2_abstains_and_reports_the_type(tmp_path):
    ctx, _, _ = ctx_for(tmp_path, gen=Recorder(lambda s, p: "ABSTAIN no_source: nothing"))
    r = build_systems(ctx, ["engine2"])[0].answer(questions()[8])
    assert r.status == "abstained" and r.text == "" and r.error == ""
    assert r.replay["status"] == "abstained" and r.replay["abstention"] == "no_source"


def test_dates_reach_the_engine(tmp_path):
    seen = []
    ctx, gen, _ = ctx_for(tmp_path, gen=Recorder(lambda s, p: seen.append(p) or GEN))
    build_systems(ctx, ["engine2"])[0].answer(questions()[6])  # q07, as_of 2019-06-01
    assert "2019-06-01" in seen[0]


def test_a_model_failure_is_an_error_result_and_a_budget_stop_raises(tmp_path):
    def boom(system, prompt):
        raise RuntimeError("API outage after retries")

    ctx, _, _ = ctx_for(tmp_path, gen=Recorder(boom))
    r = build_systems(ctx, ["engine2"])[0].answer(questions()[0])
    assert r.error.startswith("model failure") and r.status == "abstained"
    rec = Recorder(lambda s, p: GEN, usd=0.4)
    lg = Ledger(str(tmp_path / "l.jsonl"), cap_usd=0.5, margin_usd=0.0)
    ds = make_dataset(tmp_path / "b")
    ctx2 = build_context(ds, str(tmp_path / "s2.sqlite"), llm=rec, ledger=lg, estimate_usd=0.4)
    with pytest.raises(BudgetExceeded):
        build_systems(ctx2, ["engine2"])[0].answer(questions()[0])


def test_models_are_metered_under_their_own_tags_and_never_wear_the_legal_prompts(tmp_path):
    ds = make_dataset(tmp_path)
    lg = Ledger(str(tmp_path / "l.jsonl"), 10.0)
    gen = Recorder(lambda s, p: GEN, usd=0.001)
    judge = Recorder(lambda s, p: JUDGE, usd=0.0005)
    strong = Recorder(lambda s, p: GEN, usd=0.01)
    base = Recorder(lambda s, p: GEN, usd=0.002)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=base, ledger=lg, v2_llm=gen, judge_llm=judge,
                        strong_llm=strong)
    r = build_systems(ctx, ["engine2"])[0].answer(questions()[0])
    tags = lg.by_tag()
    assert tags["engine2"] == pytest.approx(0.001 * gen_calls(gen)) and tags["engine2-judge"] == pytest.approx(0.0005)
    assert "engine2-strong" not in tags and not base.prompts
    assert ctx.v2_llm_for("engine2") is ctx.v2_llm_for("engine2")
    assert ctx.strong_llm_for().tag == "engine2-strong" and ctx.judge_llm_for().tag == "engine2-judge"
    assert r.usage.usd == pytest.approx(sum(tags.values()))
    # a legal dataset: the v1 generator wears the Portuguese suffix, the v2 one does not
    legal = make_dataset(tmp_path / "legal")
    legal = type(legal)(name=legal.name, corpus_dir=legal.corpus_dir, questions=legal.questions,
                        licence="t", corpus_tokens=1, meta={"prompt_set": "legal_br", "domain": "jsonl"})
    lctx = build_context(legal, str(tmp_path / "s3.sqlite"), llm=Recorder(lambda s, p: GEN))
    assert isinstance(lctx.llm_for("engine"), LegalPrompts)
    assert not isinstance(lctx.v2_llm_for("engine2"), LegalPrompts)
    assert not isinstance(lctx.judge_llm_for(), LegalPrompts) and lctx.strong_llm_for() is None
    s = build_systems(lctx, ["engine2"])[0]
    assert s.surface().prompts["agent_system"] == load_surface(domain="jsonl", prompt_set="legal_br").prompts["agent_system"]


def gen_calls(rec):
    return len(rec.prompts)


def test_the_cache_marker_support_survives_the_meter(tmp_path):
    class Cached(Recorder):
        supports_cache_break = True

    ctx, _, _ = ctx_for(tmp_path, gen=Cached(lambda s, p: GEN), ledger=Ledger(str(tmp_path / "l.jsonl"), 10.0))
    assert ctx.v2_llm_for().supports_cache_break is True
    assert ctx.judge_llm_for().supports_cache_break is False
    s = build_systems(ctx, ["engine2"])[0]
    assert s.manifest_info()["v2_cache"] is True
    s.answer(questions()[0])
    assert s._tls.taps["gen"].supports_cache_break is True


def test_surface_comes_from_the_context_and_changes_the_hash(tmp_path):
    ds = make_dataset(tmp_path)
    default = build_systems(build_context(ds, str(tmp_path / "a.sqlite")), ["engine2"])[0]
    assert default.params()["surface_hash"] == surface_hash(load_surface(domain="jsonl"))
    surf = apply_overrides(load_surface(domain="jsonl"), {"config": {"agent.max_turns": 2}})
    custom = build_systems(build_context(ds, str(tmp_path / "b.sqlite"), v2_surface=surf), ["engine2"])[0]
    assert custom.params()["surface_hash"] == surface_hash(surf) != default.params()["surface_hash"]
    assert custom.surface().get("agent", "max_turns") == 2


def test_params_say_whether_a_calibration_file_was_used(tmp_path):
    ds = make_dataset(tmp_path)
    sh = surface_hash(load_surface(domain="jsonl"))

    def cal(h, tau):
        return cal_mod.Calibration(tau=tau, alpha=0.05, delta=0.1, n_questions=100, n_answered=60, errors=1,
                                   upper=0.04, coverage=0.6, surface_hash=h, dataset="tiny", split="dev",
                                   label="containment", created="2026-11-13T00:00:00Z")

    path = tmp_path / "c.json"
    cal_mod.save(cal(sh, 0.7), path)
    for given, used, tau in ((str(path), True, 0.7), (cal(sh, 0.6), True, 0.6), (cal("other", 0.6), False, None)):
        s = build_systems(build_context(ds, str(tmp_path / "x.sqlite"), v2_calibration=given), ["engine2"])[0]
        p = s.params()
        assert (p["calibration_file"], p["calibration_tau"]) == (used, tau)
    assert s.describe()["name"] == "engine2"


def test_a_calibration_directory_is_searched_per_dataset(tmp_path, monkeypatch):
    import heuresis.v2.engine as eng_mod
    ds = make_dataset(tmp_path)  # named "tiny"
    sh = surface_hash(load_surface(domain="jsonl"))
    for name, tau in (("other", 0.9), ("tiny", 0.6)):
        cal_mod.save(cal_mod.Calibration(
            tau=tau, alpha=0.05, delta=0.1, n_questions=100, n_answered=60, errors=1, upper=0.04, coverage=0.6,
            surface_hash=sh, dataset=name, split="dev", label="containment",
            created="2026-11-13T00:00:00Z" if name == "tiny" else "2026-11-14T00:00:00Z"), tmp_path / "cals" / f"{name}.json")
    monkeypatch.setattr(eng_mod, "CALIBRATION_DIR", tmp_path / "cals")
    p = build_systems(build_context(ds, str(tmp_path / "x.sqlite")), ["engine2"])[0].params()
    assert p["calibration_file"] is True and p["calibration_tau"] == 0.6  # not the newer file of another dataset


def test_a_run_records_the_v2_facts_in_the_manifest_and_replay_in_rows(tmp_path):
    ds = make_dataset(tmp_path)
    ctx, _, _ = ctx_for(tmp_path, ds=ds)
    out = str(tmp_path / "out")
    systems = build_systems(ctx, ["engine2", "closed_book"])
    st = run(ds, "dev", systems, out, None, workers=3, dry_run=True, limit=6)
    assert st["written"] == 12 and st["stopped"] is None
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["v2_surface_hash"] == systems[0].surface_hash() and len(man["protected_hash"]) == 64
    assert man["judge_model"] == "recorder" and man["strong_model"] is None and man["v2_cache"] is False
    assert len(man["split_ids_sha256"]) == 64
    rows = [json.loads(x) for x in open(os.path.join(out, "results.jsonl"))]
    e2 = [r for r in rows if r["system"] == "engine2"]
    assert len(e2) == 6 and all(r["replay"]["engine"] == "v2" for r in e2)
    assert all("replay" not in r for r in rows if r["system"] == "closed_book")


def test_another_datasets_calibration_is_never_applied(tmp_path, monkeypatch):
    import heuresis.v2.engine as eng_mod
    sh = surface_hash(load_surface(domain="jsonl"))
    cal_mod.save(cal_mod.Calibration(
        tau=0.95, alpha=0.05, delta=0.1, n_questions=100, n_answered=60, errors=1, upper=0.04, coverage=0.6,
        surface_hash=sh, dataset="other", split="dev", label="containment", created="2026-11-14T00:00:00Z"),
        tmp_path / "cals" / "other.json")
    monkeypatch.setattr(eng_mod, "CALIBRATION_DIR", tmp_path / "cals")
    ctx, _, _ = ctx_for(tmp_path)  # dataset "tiny": no file of its own
    r = build_systems(ctx, ["engine2"])[0].answer(questions()[0])
    assert r.status == "answered" and r.replay["meta"]["calibrated"] is False and r.replay["tau"] != 0.95
