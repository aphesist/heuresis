import json

import pytest

from heuresis.model import ABSTENTIONS, Passage
from heuresis.surface import (
    DRAFT_SYSTEM, Config, config_from_dict, config_to_dict, draft_prompt, load_config,
)


def test_default_json_round_trips_to_defaults():
    cfg = load_config()
    assert cfg == Config()
    assert config_from_dict(config_to_dict(cfg)) == cfg
    assert cfg.retrieve.rerank_out == 8 and cfg.draft.model == "claude-haiku-5-5"


def test_load_from_path_and_partial(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"retrieve": {"k_lexical": 7}}))
    cfg = load_config(str(p))
    assert cfg.retrieve.k_lexical == 7 and cfg.retrieve.k_dense == 50


def test_unknown_keys_raise():
    with pytest.raises(ValueError):
        config_from_dict({"bogus": 1})
    with pytest.raises(ValueError):
        config_from_dict({"retrieve": {"nope": 1}})


def test_prompt_contents():
    ps = [Passage("u1", 0, "The limit is 5.", title="Art 1", valid_from="2020-01-01", mark="t1")]
    out = draft_prompt("What is the limit?", "2024-03-15", ps, [])
    assert "[t1] (Art 1; valid 2020-01-01..) The limit is 5." in out
    assert "2024-03-15" in out and "What is the limit?" in out
    for kw in ("ONLY", "CALL k1 calc", "{k1}", "ABSTAIN <type>"):
        assert kw in DRAFT_SYSTEM
    assert all(a in DRAFT_SYSTEM for a in ABSTENTIONS)
