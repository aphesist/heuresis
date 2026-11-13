import json
import os

from heuresis.evolve import candidates as C
from heuresis.v2.locked import schema


def test_id_is_stable_and_normalised():
    a = {"config": {"retrieve.k_first": 12, "agent.max_turns": 4}}
    b = {"config": {"agent.max_turns": 4, "retrieve.k_first": 12}, "prompts": {}}
    assert C.candidate_id(a) == C.candidate_id(b) and len(C.candidate_id(a)) == 64
    base = C.base_surface()
    # a value equal to the default is dropped, so it is the same candidate as the empty one
    assert C.candidate_id({"config": {"retrieve.k_first": 8}}, base) == C.candidate_id({})
    assert C.candidate_id(a) != C.candidate_id({"config": {"retrieve.k_first": 13}})


def test_surface_of_validates():
    s = C.surface_of({"config": {"retrieve.k_first": 12}})
    assert s.get("retrieve", "k_first") == 12
    for bad in ({"config": {"retrieve.k_first": 99}}, {"config": {"retrieve.nope": 1}}, {"x": 1}):
        try:
            C.surface_of(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def _mirror(tmp_path):
    d = tmp_path / "cand"
    (d / "prompts").mkdir(parents=True)
    base = C.base_surface()
    (d / "default.json").write_text(json.dumps(base.config))
    for n, t in base.prompts.items():
        (d / "prompts" / f"{n}.txt").write_text(t)
    return d


def test_directory_mirroring_the_surface_is_the_empty_candidate(tmp_path):
    d = _mirror(tmp_path)
    loaded = C.load_candidate(d)
    assert loaded.problems == [] and loaded.overrides == {}
    cfg = json.loads((d / "default.json").read_text())
    cfg["retrieve"]["k_first"] = 15
    (d / "default.json").write_text(json.dumps(cfg))
    (d / "prompts" / "repair.txt").write_text("Fix the sentences listed and answer again.")
    loaded = C.load_candidate(d)
    assert loaded.problems == []
    assert loaded.overrides["config"] == {"retrieve.k_first": 15}
    assert "repair" in loaded.overrides["prompts"]
    assert C.diff_surface(C.surface_of(loaded.overrides), C.base_surface()) == loaded.overrides


def test_directory_problems(tmp_path):
    d = _mirror(tmp_path)
    (d / "evil.py").write_text("print(1)")
    (d / "locked").mkdir()
    (d / "locked" / "gates.json").write_text("{}")
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    os.symlink(outside, d / "link.json")
    probs = " | ".join(C.load_candidate(d).problems)
    assert "evil.py" in probs and "locked/gates.json" in probs and "link.json" in probs


def test_load_file_and_missing(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"config": {"agent.max_turns": 3}}))
    assert C.load_candidate(str(f)).overrides == {"config": {"agent.max_turns": 3}}
    f.write_text("not json")
    assert C.load_candidate(f).problems
    assert C.load_candidate(tmp_path / "nope").problems


def test_changed_path_guard():
    assert C.check_changed_paths(["src/heuresis/v2/surface/default.json"]) == []
    assert C.check_changed_paths(["src/heuresis/v2/locked/gates.py", "../x.json"])


def test_schema_describe_is_json():
    json.dumps(schema.describe())
