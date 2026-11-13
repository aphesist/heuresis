"""`heuresis evolve ...`, `heuresis lock` and `heuresis ask --engine v2`. Offline; no network, no key."""
import json
from pathlib import Path

import pytest

from heuresis.cli import main
from heuresis.evolve.archive import Archive
from heuresis.evolve.splits import FIXTURE_DIR

NOKEY = "HEURESIS_TEST_UNSET_VAR"


def run(capsys, *argv):
    capsys.readouterr()
    code = main(list(argv))
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def test_describe_json_has_the_schema(capsys):
    code, out, _ = run(capsys, "evolve", "describe", "--json")
    d = json.loads(out)
    assert code == 0
    assert d["surface_schema"]["config"]["retrieve"]["k_first"] == {
        "kind": "int", "default": 8, "lo": 3, "hi": 20, "choices": []}
    assert set(d["surface_schema"]["prompts"]) == {"agent_system", "agent_more", "agent_last", "repair"}
    assert [s["name"] for s in d["stages"]] == ["static", "smoke", "screen", "dev", "promote"]
    assert d["protected_hash"] and d["budget"]["cap_usd_per_cycle"] == 10.0


def test_evaluate_with_a_nonce_prints_exactly_one_tagged_line(tmp_path, capsys):
    cand = tmp_path / "c.json"
    cand.write_text(json.dumps({"config": {"retrieve.k_first": 10}}))
    code, out, _ = run(capsys, "evolve", "evaluate", "--candidate", str(cand), "--stage", "static",
                       "--nonce", "abc123", "--workdir", str(tmp_path / "wd"), "--allow-unpinned")
    lines = out.splitlines()
    assert code == 0 and len(lines) == 1 and lines[0].startswith("HEURESIS-EVAL abc123 ")
    rep = json.loads(lines[0].split(" ", 2)[2])
    assert rep["stage"] == "static" and rep["passed"] is True


def test_evaluate_candidate_dir_and_a_bad_one(tmp_path, capsys):
    d = tmp_path / "cand"
    d.mkdir()
    (d / "default.json").write_text("{}")
    (d / "x.py").write_text("1")
    code, out, _ = run(capsys, "evolve", "evaluate", "--candidate-dir", str(d), "--stage", "static",
                       "--nonce", "n1", "--workdir", str(tmp_path / "wd"), "--allow-unpinned")
    rep = json.loads(out.strip().split(" ", 2)[2])
    assert code == 0 and rep["passed"] is False and rep["tripwires"][0]["name"] == "invalid_surface"
    code, out, err = run(capsys, "evolve", "evaluate", "--stage", "static", "--workdir", str(tmp_path / "wd"))
    assert code == 2 and "exactly one" in err


def test_evaluate_without_allow_unpinned_fails_when_there_is_no_manifest(tmp_path, capsys, monkeypatch):
    from heuresis.v2.locked import manifest
    root = tmp_path / "bare"
    root.mkdir()
    monkeypatch.setattr(manifest, "default_root", lambda: root)
    code, out, _ = run(capsys, "evolve", "evaluate", "--candidate", str(tmp_path / "none.json"),
                       "--stage", "static", "--nonce", "z", "--workdir", str(tmp_path / "wd"))
    assert json.loads(out.split(" ", 2)[2])["passed"] is False


def test_offline_cycle_runs_end_to_end_with_the_engine_and_fakes(tmp_path, capsys):
    wd = str(tmp_path / "wd")
    code, out, err = run(capsys, "evolve", "cycle", "--workdir", wd, "--offline", "--allow-unpinned", "--json")
    assert code == 0, err
    rep = json.loads(out)
    assert rep["status"] == "complete" and rep["cycle"] == 1 and rep["cost_usd"] == 0.0
    assert len(rep["candidates"]) == 4 and rep["judge_model"] == "offline-fixture"
    assert all(c["stages"]["static"] and c["stages"]["smoke"] for c in rep["candidates"])
    arch = Archive(wd)
    assert arch.champion() and len(arch.rows()) == 5
    assert (Path(wd) / "cycles" / "0001.json").exists() and (Path(wd) / "gold_answers.json").exists()
    # the engine really answered fixture questions correctly: a rotating-dev cache holds correct rows
    caches = list((Path(wd) / "cache").glob("*.rotating.json"))
    rows = [r for f in caches for r in json.loads(f.read_text())["rows"].values()]
    assert any(r["outcome"] == "correct" and r["status"] == "answered" for r in rows)
    assert any(r["status"] == "abstained" and not r["answerable"] for r in rows)
    code, out, _ = run(capsys, "evolve", "status", "--workdir", wd, "--json")
    st = json.loads(out)
    assert code == 0 and st["cycle"] == 1 and st["candidates"] == 5
    code, out, _ = run(capsys, "evolve", "cycle", "--workdir", wd, "--offline", "--allow-unpinned")
    assert code == 0 and "cycle 2: complete" in out


def test_cycle_needs_offline_or_paid(tmp_path, capsys):
    code, _, err = run(capsys, "evolve", "cycle", "--workdir", str(tmp_path), "--allow-unpinned")
    assert code == 2 and "--offline" in err


def test_paid_refusals_never_touch_a_key(tmp_path, capsys):
    base = ["evolve", "cycle", "--workdir", str(tmp_path), "--paid"]
    assert run(capsys, *base)[0] == 2
    assert "--cap" in run(capsys, *base)[2]
    assert "--ledger" in run(capsys, *base, "--cap", "1")[2]
    assert "--model" in run(capsys, *base, "--cap", "1", "--ledger", str(tmp_path / "l"))[2]
    assert "--dataset" in run(capsys, *base, "--cap", "1", "--ledger", str(tmp_path / "l"), "--model", "m")[2]
    code, _, err = run(capsys, *base, "--cap", "1", "--ledger", str(tmp_path / "l"), "--model", "m",
                       "--dataset", "multihoprag", "--key-env", NOKEY)
    assert code == 2 and NOKEY in err and "not set" in err


def test_rollback_command(tmp_path, capsys):
    arch = Archive(tmp_path)
    root = arch.ensure_champion()["id"]
    c = arch.add_candidate({"config": {"retrieve.k_first": 10}}, root, cycle=1)
    arch.set_champion(c, reason="t", cycle=1)
    code, out, _ = run(capsys, "evolve", "rollback", "--workdir", str(tmp_path), "--json")
    assert code == 0 and json.loads(out)["to"] == root
    code, _, err = run(capsys, "evolve", "rollback", "--workdir", str(tmp_path))
    assert code == 2 and "no previous champion" in err


def test_lock_and_lock_check(tmp_path, capsys, monkeypatch):
    from heuresis.v2.locked import manifest
    root = tmp_path / "root"
    f = root / "src" / "heuresis" / "store.py"
    f.parent.mkdir(parents=True)
    f.write_text("a\n")
    monkeypatch.setattr(manifest, "default_root", lambda: root)
    assert run(capsys, "lock", "--check")[0] == 2                       # no manifest yet
    code, out, _ = run(capsys, "lock", "--json")
    assert code == 0 and json.loads(out)["protected_hash"] == manifest.protected_hash(root)
    assert run(capsys, "lock", "--check")[0] == 0
    code, out, _ = run(capsys, "evolve", "lock-check", "--workdir", str(tmp_path))
    assert code == 0
    f.write_text("b\n")
    code, out, err = run(capsys, "lock", "--check")
    assert code == 2 and "changed: src/heuresis/store.py" in out
    assert run(capsys, "evolve", "lock-check")[0] == 2


def test_ask_engine_v2_offline(tmp_path, capsys):
    db = str(tmp_path / "c.db")
    assert main(["init", db, "--domain", "jsonl"]) == 0
    assert main(["ingest", db, str(FIXTURE_DIR), "--domain", "jsonl"]) == 0
    q = json.loads(Path(FIXTURE_DIR, "questions.jsonl").read_text().splitlines()[0])["text"]
    code, out, _ = run(capsys, "ask", db, q, "--engine", "v2", "--json")
    d = json.loads(out)
    assert code == 0 and d["status"] in ("answered", "partial", "abstained", "divergent") and d["offline"] is True
    assert run(capsys, "ask", db, q, "--judge-model", "x")[0] == 2        # v1 has no judge model
    code, out, _ = run(capsys, "ask", db, q, "--json")                       # default engine is v1
    assert code == 0 and "engine" not in json.loads(out).get("meta", {})


def test_ask_engine_v2_judge_model_needs_a_model(tmp_path, capsys):
    db = str(tmp_path / "c.db")
    main(["init", db, "--domain", "jsonl"])
    assert run(capsys, "ask", db, "q?", "--engine", "v2", "--judge-model", "x")[0] == 2
