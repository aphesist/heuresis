import json
import os

import pytest

from heuresis.evolve import api
from heuresis.evolve.archive import Archive
from heuresis.evolve.evaluator import Evaluator, ProtectedTreeError
from heuresis.v2.locked import manifest
from test_evolve_common import BAD, CFG, GOLD, GOOD, NEUTRAL, NEUTRAL2, Scripted, make_splits


def ev_kwargs(runner, **kw):
    d = dict(runner=runner, smoke_runner=runner, splits=make_splits(), config=dict(CFG), allow_unpinned=True)
    d.update(kw)
    return d


def evaluate(cand, stage, wd, runner, **kw):
    return api.evaluate(cand, stage=stage, workdir=wd, **ev_kwargs(runner, **kw))


def boom(*a, **k):
    raise AssertionError("the runner must not be called")


# ---- H8: planted bad candidates are rejected at the static stage ------------------------------


def _dir(tmp_path, name, files):
    d = tmp_path / name
    for rel, text in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return d


def test_planted_bad_candidates_fail_static_and_never_reach_the_runner(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    sym = _dir(tmp_path, "sym", {"default.json": "{}"})
    os.symlink(outside, sym / "escape.json")
    bad = {
        "canary marker in a prompt": {"prompts": {"agent_more": "Remember hx-canary-0123abcd always."}},
        "out of bounds": {"config": {"retrieve.k_first": 500}},
        "unknown key": {"config": {"retrieve.not_a_key": 1}},
        "unknown section field": {"code": "import os"},
        "python file": _dir(tmp_path, "py", {"default.json": "{}", "gates.py": "x = 1"}),
        "path outside the surface": _dir(tmp_path, "out", {"default.json": "{}", "locked/judge.json": "{}"}),
        "symlink out": sym,
        "prompt without protocol word": {"prompts": {"agent_system": "Just answer."}},
    }
    wd = tmp_path / "wd"
    for name, cand in bad.items():
        rep = evaluate(cand, "static", wd, boom)
        assert rep["stage"] == "static" and rep["passed"] is False, name
        assert any(t["name"] == "invalid_surface" for t in rep["tripwires"]), name
        for later in ("smoke", "screen", "dev", "promote"):
            r2 = evaluate(cand, later, wd, boom)
            assert r2["passed"] is False and r2["stage"] == later, (name, later)
    rep = evaluate(bad["canary marker in a prompt"], "static", wd, boom)
    assert {t["name"] for t in rep["tripwires"]} >= {"canary_marker", "invalid_surface"}


def test_prompt_lint_rejects_an_evaluation_question_in_a_prompt(tmp_path):
    splits = make_splits()
    q = splits.rotating("syn", 1, 20)[0].text
    cand = {"prompts": {"agent_more": f"Search more. {q} {q}"}}
    rep = evaluate(cand, "static", tmp_path, boom, splits=splits)
    assert not rep["passed"] and "8-word" in " ".join(rep["metrics"]["problems"])


def test_a_changed_protected_file_is_recorded_at_static_and_refuses_later_stages(tmp_path):
    root = tmp_path / "root"
    f = root / "src" / "heuresis" / "store.py"
    f.parent.mkdir(parents=True)
    f.write_text("x = 1\n")
    manifest.write_manifest(root)
    kw = dict(allow_unpinned=False, root=root)
    ok = evaluate({}, "static", tmp_path / "wd", boom, **kw)
    assert ok["passed"] and ok["metrics"]["protected_ok"]
    f.write_text("x = 2\n")
    rep = evaluate({}, "static", tmp_path / "wd", boom, **kw)
    assert not rep["passed"] and rep["tripwires"][0]["name"] == "protected_file_changed"
    assert rep["tripwires"][0]["severity"] == "stop_cycle"
    for later in ("smoke", "screen", "dev", "promote"):
        assert not evaluate({}, later, tmp_path / "wd", boom, **kw)["passed"]
    ev = Evaluator(tmp_path / "wd", **ev_kwargs(boom, allow_unpinned=False, root=root))
    with pytest.raises(ProtectedTreeError):
        ev.require_pinned()
    assert Evaluator(tmp_path / "wd", **ev_kwargs(boom, allow_unpinned=True)).protected_differences() == []


def test_a_missing_manifest_refuses_unless_unpinned(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    rep = evaluate({}, "static", tmp_path / "wd", boom, allow_unpinned=False, root=root)
    assert not rep["passed"]


# ---- splits -------------------------------------------------------------------------------------


def test_rotating_draws_never_overlap_each_other_or_promotion_or_calibration():
    s = make_splits()
    draws = [{q.id for q in s.rotating("syn", c, 20)} for c in range(1, 5)]
    promo = [{q.id for q in s.promotion("syn", b, 40)} for b in range(2)]
    cal = {q.id for q in s.calibration("syn", 0, 5)}
    groups = draws + promo + [cal]
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            assert not (a & b)
    assert all(len(x) == 20 for x in draws) and all(len(x) == 40 for x in promo)
    anchors = {q.id for q in s.anchors()}
    assert not (anchors & set().union(*groups))


def test_exhaustion_is_reported():
    from heuresis.evolve.splits import SplitExhausted
    s = make_splits()
    with pytest.raises(SplitExhausted):
        s.rotating("syn", 6, 20)
    with pytest.raises(SplitExhausted):
        s.promotion("syn", 2, 40)


# ---- the stages -----------------------------------------------------------------------------------


def test_screen_and_dev_report_aggregates_only(tmp_path):
    r = Scripted()
    scr = evaluate(GOOD, "screen", tmp_path, r)
    dev = evaluate(GOOD, "dev", tmp_path, r)
    assert scr["passed"] and dev["passed"]
    assert dev["metrics"]["diff"] > 0 and dev["metrics"]["lower_bound"] > 0
    assert set(dev) >= {"stage", "passed", "metrics", "tripwires", "cost_usd"}
    text = json.dumps(dev)
    assert GOLD not in text and "p0" not in text.replace('"p_one_sided"', "")
    bad = evaluate(BAD, "screen", tmp_path, r)
    assert not bad["passed"] and "worse" in bad["reasons"][0]
    neutral = evaluate(NEUTRAL, "dev", tmp_path, r)
    assert not neutral["passed"]          # no positive difference


def test_champion_rows_are_cached(tmp_path):
    r = Scripted()
    evaluate(GOOD, "dev", tmp_path, r)
    champion_calls = [t for t, _ in r.seen if t == "champion"]
    n_first = len(champion_calls)
    evaluate(NEUTRAL, "dev", tmp_path, r)
    assert len([t for t, _ in r.seen if t == "champion"]) == n_first
    assert list((tmp_path / "cache").glob("*.rotating.json"))


def test_cost_comes_from_row_usd_and_goes_to_the_ledger(tmp_path):
    r = Scripted(usd=0.001)
    rep = evaluate(GOOD, "screen", tmp_path, r)
    assert rep["cost_usd"] > 0
    spent = sum(json.loads(line)["usd"] for line in (tmp_path / "ledger.jsonl").read_text().splitlines())
    assert abs(spent - rep["cost_usd"]) < 1e-9


def test_tripwires_in_dev(tmp_path):
    leak = evaluate(GOOD, "dev", tmp_path / "a", Scripted(leak=True))
    names = {t["name"] for t in leak["tripwires"]}
    assert {"canary_answered", "canary_marker"} <= names and not leak["passed"]

    class Dear(Scripted):
        def __call__(self, surface, questions, *, tag):
            rows = super().__call__(surface, questions, tag=tag)
            if surface.get("retrieve", "k_first") >= 12:
                for x in rows:
                    x["usd"] = 0.05
            else:
                for x in rows:
                    x["usd"] = 0.01
            return rows
    dear = evaluate(GOOD, "dev", tmp_path / "b", Dear())
    assert "cost_doubled" in {t["name"] for t in dear["tripwires"]} and not dear["passed"]
    honest = evaluate(GOOD, "dev", tmp_path / "c", Scripted(usd=0.001))
    assert [t for t in honest["tripwires"] if t["severity"] != "flag"] == []


# ---- the promotion stage ------------------------------------------------------------------------


def test_promotion_returns_statistics_and_no_rows_or_gold(tmp_path):
    r = Scripted()
    rep = evaluate(GOOD, "promote", tmp_path, r)
    assert rep["passed"] is True
    m = rep["metrics"]
    assert set(m) >= {"statistic", "p_value", "level", "n", "guard_rails"} and m["p_value"] <= m["level"]
    text = json.dumps(rep)
    promo_ids = {q.id for q in make_splits().promotion("syn", 0, 40)}
    assert GOLD not in text and not any(i in text for i in promo_ids)
    assert "answer" not in text.lower().replace("answered", "")
    for f in (tmp_path / "cache").glob("*.promotion.json"):  # stored rows carry no answer text
        for row in json.loads(f.read_text())["rows"].values():
            assert row["text"] == "" and "question" not in row


def test_promotion_block_is_retired_after_its_budget_and_a_fresh_one_drawn(tmp_path):
    r = Scripted()
    cfg = {**CFG, "promotion_query_budget": 2}
    seen = []
    for cand in (GOOD, NEUTRAL, NEUTRAL2):
        before = len(r.seen)
        evaluate(cand, "promote", tmp_path, r, config=cfg)
        seen.append({q for t, q in r.seen[before:] if t == "promote" and q.startswith("p")})
    assert seen[0] == seen[1] != seen[2]
    assert seen[2] and not (seen[2] & seen[0])
    st = Archive(tmp_path).state()
    assert st["promotion"]["syn"]["block"] == 1 and st["promotion"]["syn"]["retired"] == [0]
    assert st["promotion_tests"] == 3


def test_promotion_is_memoised_and_does_not_spend_a_query_twice(tmp_path):
    r = Scripted()
    a = evaluate(GOOD, "promote", tmp_path, r)
    calls = r.calls
    b = evaluate(GOOD, "promote", tmp_path, r)
    assert r.calls == calls and b["passed"] == a["passed"]
    assert Archive(tmp_path).state()["promotion_tests"] == 1


def test_promotion_fails_on_a_tainted_anchor_and_when_pool_is_exhausted(tmp_path):
    rep = evaluate(GOOD, "promote", tmp_path / "t", Scripted(taint_good=True))
    assert not rep["passed"] and "tainted_anchor" in {t["name"] for t in rep["tripwires"]}
    cfg = {**CFG, "promotion_query_budget": 1}
    r = Scripted()
    docs = [{"config": {"retrieve.k_lexical": 60 + i}} for i in range(3)]
    reps = [evaluate(d, "promote", tmp_path / "e", r, config=cfg) for d in docs]
    assert "no promotion block left" in reps[2]["reasons"][0] and not reps[2]["passed"]


def test_promotion_respects_a_small_remaining_budget(tmp_path):
    from heuresis.bench.ledger import Ledger
    led = Ledger(str(tmp_path / "ledger.jsonl"), 0.30, 0.0)   # at US$0.010 per question: too little
    rep = evaluate(GOOD, "promote", tmp_path, Scripted(), ledger=led)
    assert not rep["passed"] and rep["metrics"].get("budget_limited")


# ---- reflective dataset ----------------------------------------------------------------------------


def test_reflective_dataset_is_redacted(tmp_path):
    r = Scripted()
    arch = Archive(tmp_path)
    arch.ensure_champion()
    cid = arch.add_candidate(GOOD, None, cycle=1)
    evaluate(GOOD, "dev", tmp_path, r)
    evaluate(GOOD, "promote", tmp_path, r)
    out = api.reflective_dataset(cid, workdir=tmp_path, limit=50)
    assert out and all(e["outcome"] != "correct" for e in out)
    text = json.dumps(out)
    assert GOLD not in text and "hx-canary" not in text and "canary-" not in text
    promo_ids = {q.id for b in range(2) for q in make_splits().promotion("syn", b, 40)}
    anchor_ids = {q.id for q in make_splits().anchors()}
    assert not ({e["qid"] for e in out} & (promo_ids | anchor_ids))
    assert set(out[0]) == {"qid", "dataset", "question", "answer", "status", "outcome", "abstention",
                           "reasons", "confidence"}
    assert len(api.reflective_dataset(cid, workdir=tmp_path, limit=3)) == 3
    assert api.reflective_dataset("0" * 64, workdir=tmp_path) == []


def test_describe_status_and_rollback(tmp_path):
    d = api.describe()
    json.dumps(d)
    assert set(d) >= {"surface_schema", "champion", "protected_hash", "stages", "budget", "datasets"}
    assert d["surface_schema"]["config"]["retrieve"]["k_first"]["hi"] == 20
    s = api.status(workdir=tmp_path)
    assert s["champion"] is None or s["candidates"] >= 0
    Archive(tmp_path).ensure_champion()
    assert api.status(workdir=tmp_path)["champion"]["id"]
