import dataclasses

import pytest

from heuresis.bench import systems as S
from heuresis.bench.ledger import Ledger
from heuresis.bench.systems import SYSTEM_NAMES, build_context, build_systems, parse_reply
from heuresis.fakes import EchoLLM
from test_bench_common import Recorder, make_dataset, questions


def test_parse_reply():
    assert parse_reply("It is 5.\nCONFIDENCE: 80") == ("It is 5.", False, 0.8)
    assert parse_reply("ABSTAIN\nCONFIDENCE: 20")[1:] == (True, 0.2)
    assert parse_reply("It is 5.") == ("It is 5.", False, 0.5)
    assert parse_reply("abstain.")[1] is True
    assert parse_reply("x\nCONFIDENCE: 250%")[2] == 1.0
    assert parse_reply("")[1] is True


def test_every_system_returns_wellformed_result(tmp_path):
    ds = make_dataset(tmp_path)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    systems = build_systems(ctx)
    assert [s.name for s in systems] == list(SYSTEM_NAMES)
    for s in systems:
        assert s.available, s.name
        for q in questions()[:3] + questions()[6:7] + questions()[8:9]:
            r = s.answer(q)
            assert r.status in ("answered", "abstained")
            assert 0.0 <= r.confidence <= 1.0
            assert isinstance(r.text, str) and r.ms >= 0
            assert r.usage.tokens_in >= 0 and r.usage.usd == 0.0
            assert r.calls >= 0 and r.searches >= 0
            assert isinstance(r.cited_units, tuple)
    # the extractive fake answers from the passage, so retrieval systems answer q01
    for name in ("bm25", "vector", "hybrid_rerank", "long_context", "oracle"):
        s = next(x for x in systems if x.name == name)
        r = s.answer(questions()[0])
        assert r.status == "answered" and r.calls == 1, name
    assert next(x for x in systems if x.name == "closed_book").answer(questions()[0]).status == "abstained"


def test_prompts_share_format_and_cap(tmp_path):
    ds = make_dataset(tmp_path)
    rec = Recorder(lambda s, p: "ok\nCONFIDENCE: 70")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec)
    seen = {}
    for s in build_systems(ctx, ["closed_book", "bm25", "vector", "hybrid_rerank", "long_context", "oracle"]):
        s.answer(questions()[0])
        seen[s.name] = rec.systems[-1]
    for name, system in seen.items():
        assert S.ANSWER_FORMAT in system, name
    assert "Question: How long is the Beta river?" in rec.prompts[0]
    assert "Passages:" not in rec.prompts[0]
    assert "Documents:" in rec.prompts[-2]  # long_context
    assert S.prompts_hash() == S.prompts_hash()


def test_baselines_naive_vs_time_aware(tmp_path):
    ds = make_dataset(tmp_path)
    q = questions()[6]  # as_of 2019: the 500 euro version
    rec = Recorder(lambda s, p: "x\nCONFIDENCE: 50")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec)
    naive, aware = build_systems(ctx, ["bm25"]) + build_systems(ctx, ["bm25"], time_aware=True)
    assert not naive.time_aware and aware.time_aware
    naive.answer(q)
    aware.answer(q)
    assert "800 euros" in rec.prompts[0] and "500 euros" not in rec.prompts[0]
    assert "500 euros" in rec.prompts[1] and "800 euros" not in rec.prompts[1]
    assert "As-of date: 2019-06-01" in rec.prompts[1] and "As-of date" not in rec.prompts[0]


def test_engine_is_time_aware_and_maps_status(tmp_path):
    ds = make_dataset(tmp_path)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    eng = build_systems(ctx, ["engine"])[0]
    assert eng.time_aware and eng.cites
    r = eng.answer(questions()[6])
    assert r.status in ("answered", "abstained")
    if r.status == "answered":
        assert "u1" in r.cited_units and "500" in r.text
    assert r.searches >= 1


def test_agentic_cap_enforced(tmp_path):
    ds = make_dataset(tmp_path)
    llm = EchoLLM(["SEARCH: beta river"] * 10)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=llm)
    ag = build_systems(ctx, ["agentic"], max_actions=2)[0]
    r = ag.answer(questions()[0])
    assert r.searches == 2 and r.calls == 3 and r.status == "abstained"
    assert "cap" in r.note


def test_agentic_search_then_answer_resends_context(tmp_path):
    ds = make_dataset(tmp_path)
    replies = iter(["SEARCH: Beta river length", "The Beta river is 120 kilometres long.\nCONFIDENCE: 90"])
    rec = Recorder(lambda s, p: next(replies))
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec)
    ag = build_systems(ctx, ["agentic"])[0]
    r = ag.answer(questions()[0])
    assert (r.status, r.confidence, r.searches, r.calls) == ("answered", 0.9, 1, 2)
    assert "Searches used: 0 of 4" in rec.prompts[0] and "Searches used: 1 of 4" in rec.prompts[1]
    assert "120 kilometres" in rec.prompts[1] and "Question: How long" in rec.prompts[1]
    assert r.usage.tokens_in == sum(len(p.split()) for p in rec.prompts)  # all turns counted
    assert "u2" in r.retrieved_units


def test_long_context_availability(tmp_path):
    ds = make_dataset(tmp_path, corpus_tokens=50_000)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    assert build_systems(ctx, ["long_context"])[0].available
    big = dataclasses.replace(ds, corpus_tokens=500_000)
    ctx2 = build_context(big, str(tmp_path / "s2.sqlite"))
    lc = build_systems(ctx2, ["long_context"])[0]
    assert not lc.available and "500000" in lc.reason
    with pytest.raises(RuntimeError):
        lc.answer(questions()[0])
    assert build_systems(ctx2, ["long_context"], long_context_limit=1_000_000)[0].available


def test_oracle_sees_gold_passage_at_date(tmp_path):
    ds = make_dataset(tmp_path)
    rec = Recorder(lambda s, p: "x\nCONFIDENCE: 50")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec)
    o = build_systems(ctx, ["oracle"])[0]
    o.answer(questions()[6])
    assert "500 euros" in rec.prompts[-1] and "800 euros" not in rec.prompts[-1]


def test_ledger_meters_each_system(tmp_path):
    ds = make_dataset(tmp_path)
    lg = Ledger(str(tmp_path / "l.jsonl"), 100.0)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=Recorder(usd=0.01), ledger=lg)
    for s in build_systems(ctx, ["closed_book", "bm25"]):
        s.answer(questions()[0])
    assert lg.by_tag() == pytest.approx({"closed_book": 0.01, "bm25": 0.01})


def test_engine_config_copy_sets_max_sentences(tmp_path):
    ds = make_dataset(tmp_path)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    assert ctx.config.draft.max_sentences == 0
    eff = ctx.engine_config()
    assert eff.draft.max_sentences == 2 and eff is not ctx.config
    assert ctx.config.draft.max_sentences == 0
    assert ctx.engine().config.draft.max_sentences == 2
