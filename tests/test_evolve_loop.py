import json

from heuresis.evolve.archive import Archive
from heuresis.evolve.loop import run_cycle
from heuresis.evolve.proposers import PerturbProposer, ReflectiveProposer, Parent, parse_candidate
from heuresis.evolve import candidates as C
from test_evolve_common import (BAD, GOOD, NEUTRAL, NEUTRAL2, Scripted, ScriptedProposer, cycle_kwargs)


def run(wd, runner, proposer, **kw):
    return run_cycle(wd, k=3, cap_usd=kw.pop("cap_usd", 10.0), proposer=proposer, **cycle_kwargs(runner, **kw))


def test_a_better_candidate_is_promoted_and_every_stage_is_recorded(tmp_path):
    r = Scripted()
    base_id = Archive(tmp_path).ensure_champion()["id"]
    out = run(tmp_path, r, ScriptedProposer([GOOD, NEUTRAL, BAD]))
    assert out["status"] == "complete" and out["promoted"]
    arch = Archive(tmp_path)
    ch = arch.champion()
    assert ch["id"] == out["promoted"] != base_id and ch["candidate"] == GOOD
    assert [h["id"] for h in ch["history"]] == [base_id]
    rows = arch.rows()
    good = rows[ch["id"]]
    assert set(good["stages"]) == {"static", "smoke", "screen", "dev", "promote"}
    assert all(good["stages"][s]["passed"] for s in good["stages"])
    assert good["stages"]["dev"]["judge_model"] == "offline-fixture" or good["stages"]["dev"]["judge_model"]
    by = {c["candidate"].get("config", {}).get("retrieve.k_first"): c for c in rows.values() if c["id"] != base_id}
    assert by[3]["status"] == "rejected_screen" and "dev" not in by[3]["stages"]
    neutral = [c for c in rows.values() if c["candidate"] == NEUTRAL][0]
    assert neutral["status"] == "archived" and "screen" in neutral["stages"]
    assert arch.state()["promotions"] == 1 and arch.state()["cycle"] == 1 and arch.state()["open_cycle"] is None
    assert (tmp_path / "cycles" / "0001.json").exists() and (tmp_path / "gold_answers.json").exists()
    assert out["calibration"]["status"] in ("fitted", "uncalibrated")


def test_second_cycle_with_nothing_better_promotes_nothing(tmp_path):
    r = Scripted()
    run(tmp_path, r, ScriptedProposer([GOOD], [NEUTRAL, NEUTRAL2, BAD]))
    champ = Archive(tmp_path).champion()["id"]
    out = run(tmp_path, r, ScriptedProposer([GOOD], [NEUTRAL, NEUTRAL2, BAD]))
    assert out["cycle"] == 2 and out["promoted"] is None and out["rollback"] is None
    assert Archive(tmp_path).champion()["id"] == champ
    assert all(c["status"] in ("archived", "rejected_dev", "rejected_screen") for c in out["candidates"])


def test_a_champion_that_degrades_on_the_next_draw_is_rolled_back(tmp_path):
    r = Scripted(degrade={"rot2"})
    first = run(tmp_path, r, ScriptedProposer([GOOD]))
    assert first["promoted"]
    base_id = Archive(tmp_path).champion()["history"][0]["id"]
    out = run(tmp_path, r, ScriptedProposer([NEUTRAL]))
    assert out["rollback"] and out["rollback"]["to"] == base_id
    arch = Archive(tmp_path)
    assert arch.champion()["id"] == base_id and arch.get(first["promoted"])["status"] == "rolled_back"
    assert "standard errors" in arch.champion()["reason"] or "rollback" in arch.champion()["reason"]


def test_a_healthy_champion_is_not_rolled_back(tmp_path):
    r = Scripted()
    run(tmp_path, r, ScriptedProposer([GOOD]))
    out = run(tmp_path, r, ScriptedProposer([NEUTRAL]))
    assert out["rollback"] is None and out["champion"]["id"] == Archive(tmp_path).champion()["id"]


def test_planted_bad_batch_is_recorded_and_stops_the_cycle(tmp_path):
    bad = [{"prompts": {"agent_more": "x hx-canary-1"}}, {"config": {"retrieve.k_first": 500}},
           {"config": {"retrieve.nope": 1}}]
    r = Scripted()
    out = run(tmp_path, r, ScriptedProposer(bad))
    assert out["status"] == "stopped_tripwire" and r.calls == 0
    rows = Archive(tmp_path).rows()
    statuses = [c["status"] for c in rows.values() if c["id"] != Archive(tmp_path).champion()["id"]]
    assert statuses == ["rejected_static"] * 3
    assert all("static" in c["stages"] for c in rows.values() if c["status"] == "rejected_static")
    assert Archive(tmp_path).champion()["history"] == []


def test_protected_change_stops_the_cycle_before_any_work(tmp_path):
    root = tmp_path / "root"
    f = root / "src" / "heuresis" / "store.py"
    f.parent.mkdir(parents=True)
    f.write_text("a\n")
    from heuresis.v2.locked import manifest
    manifest.write_manifest(root)
    f.write_text("b\n")
    r = Scripted()
    out = run_cycle(tmp_path / "wd", k=3, proposer=ScriptedProposer([GOOD]),
                    **cycle_kwargs(r, allow_unpinned=False, root=root))
    assert out["status"] == "stopped_tripwire" and out["tripwires"][0]["name"] == "protected_file_changed"
    assert r.calls == 0


def test_the_loop_stops_at_the_cap_without_promoting_and_resumes(tmp_path):
    r = Scripted(usd=0.01)
    out = run(tmp_path, r, ScriptedProposer([GOOD, NEUTRAL]), cap_usd=0.3)
    assert out["status"] == "stopped_budget" and out["promoted"] is None
    arch = Archive(tmp_path)
    assert arch.champion()["history"] == [] and arch.state()["open_cycle"] == 1
    assert out["spent_usd"] <= 0.3 + 0.3  # at most one chunk over
    assert not any(c["status"] == "champion" and c["id"] != arch.champion()["id"] for c in arch.rows().values())
    out2 = run(tmp_path, r, ScriptedProposer([NEUTRAL2]), cap_usd=50.0)  # the proposals are reused
    assert out2["cycle"] == 1 and out2["status"] == "complete" and out2["promoted"]
    assert Archive(tmp_path).champion()["candidate"] == GOOD
    # nothing was computed twice for the same (surface, question)
    pairs = [(t, q) for t, q in r.seen if t == "champion"]
    assert pairs and len(pairs) == len(set(pairs))


def test_loop_is_deterministic_given_the_seed(tmp_path):
    a = run_cycle(tmp_path / "a", k=3, proposer=PerturbProposer(1), **cycle_kwargs(Scripted()))
    b = run_cycle(tmp_path / "b", k=3, proposer=PerturbProposer(1), **cycle_kwargs(Scripted()))
    assert [c["id"] for c in a["candidates"]] == [c["id"] for c in b["candidates"]]
    assert a["champion"] == b["champion"]


# ---- proposers ------------------------------------------------------------------------------------------


def _parent():
    s = C.base_surface()
    return Parent(C.candidate_id({}), {}, s)


def test_perturb_proposer_never_produces_an_invalid_candidate():
    p = PerturbProposer(4)
    seen = set()
    for seed in range(40):
        for c in p.propose(_parent(), 6, seed=seed):
            C.surface_of(c.overrides)                      # raises if invalid
            changed = len(c.overrides.get("config", {}))
            assert 1 <= changed <= 3 and not c.overrides.get("prompts")
            seen.add(c.id)
    assert len(seen) > 100
    kids = p.propose(_parent(), 6, seed=1)
    assert len({c.id for c in kids}) == len(kids) == 6 and _parent().id not in {c.id for c in kids}
    assert [c.id for c in kids] == [c.id for c in PerturbProposer(4).propose(_parent(), 6, seed=1)]


class LLM:
    id = "scripted"

    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def complete(self, system, prompt, *, max_tokens=600):
        self.prompts.append(prompt)
        from heuresis.model import Usage
        return self.replies.pop(0), Usage()


def test_reflective_proposer_parses_defensively():
    llm = LLM(['Sure! ```json\n{"config": {"retrieve.k_first": 12}}\n``` done',
               "no json here", '{"config": {"retrieve.k_first": 999}}', '{"foo": 1}',
               '{"prompts": {"agent_more": "Search again if needed, else answer."}}'])
    out = ReflectiveProposer(llm).propose(_parent(), 5, traces=[
        {"question": "Q1?", "answer": "A", "status": "answered", "outcome": "wrong", "reasons": ["r"]}])
    assert [bool(c.overrides.get("config")) for c in out] == [True, False]
    assert out[0].overrides["config"] == {"retrieve.k_first": 12}
    assert "agent_more" in out[1].overrides["prompts"]
    assert len(llm.prompts) == 5 and "Q1?" in llm.prompts[0]
    assert parse_candidate("{}") is None and parse_candidate('{"config": {}}') is None


def test_reflective_proposer_stops_on_a_model_error_and_budget_error_propagates():
    import pytest
    from heuresis.bench.ledger import BudgetExceeded

    class Broken:
        id = "x"

        def complete(self, *a, **k):
            raise RuntimeError("down")

    assert ReflectiveProposer(Broken()).propose(_parent(), 3) == []

    class Cap:
        id = "x"

        def complete(self, *a, **k):
            raise BudgetExceeded("cap")

    with pytest.raises(BudgetExceeded):
        ReflectiveProposer(Cap()).propose(_parent(), 3)


def test_reflective_proposer_in_a_cycle_gets_redacted_traces(tmp_path):
    llm = LLM(['{"config": {"retrieve.k_first": 14}}'] * 3)
    r = Scripted()
    run_cycle(tmp_path, k=2, proposer=ReflectiveProposer(llm), **cycle_kwargs(r))
    run_cycle(tmp_path, k=2, proposer=ReflectiveProposer(LLM(['{"config": {"retrieve.k_first": 15}}'] * 3)),
              **cycle_kwargs(r))
    assert llm.prompts and "GOLD" not in llm.prompts[0]
