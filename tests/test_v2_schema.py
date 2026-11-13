import json
import shutil
from pathlib import Path

import pytest

from heuresis.v2 import load_surface
from heuresis.v2.locked import schema as S

PKG = Path(S.__file__).resolve().parent.parent / "surface"


@pytest.fixture
def base():
    return load_surface()


def test_default_matches_schema_defaults(base):
    assert S.validate(base) == []
    for sec, fields in S.SCHEMA.items():
        for k, f in fields.items():
            assert base.get(sec, k) == f.default
    assert base.get("retrieve", "k_first") == 8 and base.get("repair", "rounds") == 1
    assert set(base.prompts) == set(S.PROMPTS)


def test_domain_and_prompt_set_load():
    s = load_surface(domain="legal_br", prompt_set="legal_br")
    assert s.get("retrieve", "fusion") == "none"
    assert s.get("retrieve", "k_lexical") == 50
    assert "ABSTAIN <tipo>" in s.prompt("agent_system")
    assert S.validate(s) == []
    plain = load_surface(domain="legal_br")
    assert plain.prompt("agent_system") == load_surface().prompt("agent_system")
    assert S.surface_hash(s) != S.surface_hash(load_surface())


def test_unknown_domain_or_prompt_set_falls_back_to_default():
    assert load_surface(domain="nope", prompt_set="nope") == load_surface()


def test_shipped_prompts_have_protocol_words():
    for ps in (None, "legal_br"):
        s = load_surface(prompt_set=ps)
        sysm = s.prompt("agent_system")
        for w in ("SEARCH:", "OPEN:", "ABSTAIN", "CALL", "no_source", "false_premise",
                  "conflict", "not_valid_at_date", "unsupported", "[t1]", "{k1}"):
            assert w in sysm
        for name, spec in S.PROMPTS.items():
            low = s.prompt(name).lower()
            assert len(s.prompt(name)) <= spec.max_chars
            assert not any(f.lower() in low for f in S.FORBIDDEN)


def test_hash_is_canonical_and_stable(base):
    h = S.surface_hash(base)
    assert len(h) == 64 and h == S.surface_hash(load_surface())
    assert h != S.surface_hash(S.apply_overrides(base, {"config": {"agent.max_turns": 5}}))


def test_forbidden_includes_judge_words_and_canary():
    for w in ("NOT_SUPPORTED", "NOT_FOLLOWS", "SUFFICIENT:", "PREMISE:", "CONFLICT:"):
        assert w in S.FORBIDDEN
    assert S.CANARY_MARKER == "hx-canary-" and S.CANARY_MARKER in S.FORBIDDEN


def test_describe_is_json():
    d = S.describe()
    json.dumps(d)
    assert d["config"]["retrieve"]["fusion"]["choices"] == ["none", "rrf", "convex"]
    assert d["prompts"]["agent_system"]["required"] == ["SEARCH:", "OPEN:", "ABSTAIN"]


def test_apply_valid_override(base):
    new = S.apply_overrides(base, {"config": {"agent.max_turns": 3, "retrieve.fusion": "rrf",
                                              "retrieve.alpha": 1, "route.escalate": True},
                                   "prompts": {"agent_more": "Search or answer."}})
    assert new.get("agent", "max_turns") == 3 and new.get("retrieve", "alpha") == 1
    assert new.prompt("agent_more") == "Search or answer."
    assert base.get("agent", "max_turns") == 6  # the original is untouched


@pytest.mark.parametrize("cand,frag", [
    ({"config": {"agent.nope": 1}}, "unknown config key"),
    ({"config": {"nosection.k": 1}}, "unknown config key"),
    ({"config": {"agent.max_turns": 11}}, "outside"),
    ({"config": {"agent.max_turns": 0}}, "outside"),
    ({"config": {"agent.max_turns": 2.5}}, "expected an int"),
    ({"config": {"agent.max_turns": True}}, "expected an int"),
    ({"config": {"retrieve.alpha": 1.5}}, "outside"),
    ({"config": {"retrieve.alpha": "x"}}, "expected a number"),
    ({"config": {"retrieve.fusion": "magic"}}, "not one of"),
    ({"config": {"route.escalate": 1}}, "expected a bool"),
    ({"prompts": {"nope": "x"}}, "unknown prompt"),
    ({"prompts": {"agent_more": "x" * 1501}}, "exceeds"),
    ({"prompts": {"agent_system": "no protocol words"}}, "missing required"),
    ({"prompts": {"agent_more": "say NOT_SUPPORTED"}}, "forbidden"),
    ({"prompts": {"agent_more": "say not_follows"}}, "forbidden"),
    ({"prompts": {"repair": "see hx-canary-3"}}, "forbidden"),
    ({"prompts": {"repair": "Conflict: both"}}, "forbidden"),
    ({"prompts": {"repair": 5}}, "expected text"),
    ({"thresholds": {}}, "unknown candidate field"),
])
def test_violations_raise(base, cand, frag):
    with pytest.raises(ValueError, match=frag):
        S.apply_overrides(base, cand)


def test_validate_reports_extra_and_missing(base):
    bad = S.Surface({"agent": {"max_turns": 99, "extra": 1}, "zzz": {}}, {"agent_more": "x"})
    v = S.validate(bad)
    assert any("unknown section" in x for x in v) and any("unknown key agent.extra" in x for x in v)
    assert any("missing retrieve.k_first" in x for x in v)
    assert any("missing prompt agent_system" in x for x in v)
    assert any("agent.max_turns" in x and "outside" in x for x in v)


def test_load_from_directory_and_errors(tmp_path):
    d = tmp_path / "surf"
    shutil.copytree(PKG, d)
    assert load_surface(d) == load_surface()
    (d / "default.json").write_text(json.dumps({"agent": {"max_turns": 99}}))
    with pytest.raises(ValueError, match="invalid surface"):
        load_surface(d)
    (d / "default.json").write_text("{not json")
    with pytest.raises(ValueError, match="cannot read"):
        load_surface(d)
    (d / "default.json").unlink()
    with pytest.raises(ValueError, match="missing"):
        load_surface(d)


def test_prompt_missing_in_directory(tmp_path):
    d = tmp_path / "surf"
    shutil.copytree(PKG, d)
    (d / "prompts" / "repair.txt").unlink()
    with pytest.raises(ValueError, match="missing prompt repair"):
        load_surface(d)


def test_surface_dir_is_data_only():
    assert not list(PKG.rglob("*.py"))


def test_package_import_is_light():
    import heuresis.v2 as v2
    assert v2.load_surface is load_surface
    with pytest.raises(AttributeError):
        v2.nothing
