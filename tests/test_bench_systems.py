import dataclasses

import pytest

from heuresis.bench import systems as S
from heuresis.bench.ledger import Ledger
from heuresis.bench.systems import SYSTEM_NAMES, build_context, build_systems, parse_reply
from heuresis.fakes import EchoLLM
from heuresis.surface.config import config_to_dict, load_config
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
    for name in ("bm25", "vector", "hybrid", "hybrid_rerank", "long_context", "oracle"):
        s = next(x for x in systems if x.name == name)
        r = s.answer(questions()[0])
        assert r.status == "answered" and r.calls == 1, name
    assert next(x for x in systems if x.name == "closed_book").answer(questions()[0]).status == "abstained"


def test_prompts_share_format_and_cap(tmp_path):
    ds = make_dataset(tmp_path)
    rec = Recorder(lambda s, p: "ok\nCONFIDENCE: 70")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec)
    seen = {}
    for s in build_systems(ctx, ["closed_book", "bm25", "vector", "hybrid", "hybrid_rerank", "long_context", "oracle"]):
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


class CountingReranker:
    id = "counting"

    def __init__(self):
        self.calls = 0

    def score(self, query, texts):
        self.calls += 1
        return [float(len(t)) for t in texts]


def test_system_order_and_hybrid_has_no_reranker(tmp_path):
    assert SYSTEM_NAMES == ("closed_book", "bm25", "vector", "hybrid", "hybrid_rerank",
                            "agentic", "long_context", "engine", "oracle", "engine_single")
    ds = make_dataset(tmp_path)
    rr = CountingReranker()
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), reranker=rr)
    h, hr = build_systems(ctx, ["hybrid", "hybrid_rerank"])
    a = h.retrieve("Beta river length", questions()[0])
    assert rr.calls == 0 and a and {p.stage for p in a} == {"fused"}
    b = hr.retrieve("Beta river length", questions()[0])
    assert rr.calls == 1 and {p.stage for p in b} == {"rerank"}


def test_agentic_retriever_follows_agent_rerank(tmp_path):
    ds = make_dataset(tmp_path)
    rr = CountingReranker()
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), reranker=rr)
    plain, with_rr = (build_systems(ctx, ["agentic"])[0],
                      build_systems(ctx, ["agentic"], agent_rerank=True)[0])
    plain.retrieve("Beta river", questions()[0])
    assert rr.calls == 0 and plain.describe()["retriever"] == "hybrid"
    with_rr.retrieve("Beta river", questions()[0])
    assert rr.calls == 1 and with_rr.describe()["retriever"] == "hybrid_rerank"


def test_time_aware_variants_are_extra_copies_with_suffix(tmp_path):
    ds = make_dataset(tmp_path)
    rec = Recorder(lambda s, p: "x\nCONFIDENCE: 50")
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec)
    names = ["closed_book", "bm25", "vector", "hybrid", "hybrid_rerank", "agentic", "engine"]
    systems = build_systems(ctx, names, time_aware_variants=True)
    assert [s.name for s in systems] == names + [
        "bm25+asof", "vector+asof", "hybrid+asof", "hybrid_rerank+asof", "agentic+asof"]
    by = {s.name: s for s in systems}
    assert not by["bm25"].time_aware and by["bm25+asof"].time_aware
    assert by["bm25+asof"].describe()["exploratory"] and not by["bm25"].describe()["exploratory"]
    assert not by["engine"].exploratory
    q = questions()[6]  # as_of 2019: 500 euros
    by["hybrid"].answer(q)
    by["hybrid+asof"].answer(q)
    assert "800 euros" in rec.prompts[0] and "As-of date" not in rec.prompts[0]
    assert "500 euros" in rec.prompts[1] and "800 euros" not in rec.prompts[1]
    assert build_systems(ctx, names)[0].name == "closed_book" and len(build_systems(ctx, names)) == 7


# ----------------------------------------------------------------------------
# Hashes, provenance
# ----------------------------------------------------------------------------


def test_surface_hash_covers_config_draft_system_and_prompts_source(tmp_path, monkeypatch):
    from heuresis.surface import prompts as P
    from heuresis.surface.config import load_config
    base = S.surface_hash()
    assert base == S.surface_hash(load_config()) and len(base) == 64
    # the effective engine config: the benchmark's max_sentences is part of it
    assert S.effective_engine_config(load_config()).draft.max_sentences == S.ENGINE_MAX_SENTENCES
    cfg = load_config()
    cfg.verify.support_threshold = 0.6
    assert S.surface_hash(cfg) != base
    # DRAFT_SYSTEM
    monkeypatch.setattr(P, "DRAFT_SYSTEM", P.DRAFT_SYSTEM + " Be brief.")
    assert S.surface_hash() != base
    monkeypatch.undo()
    # the source of prompts.py, so draft_prompt is covered
    edited = tmp_path / "prompts.py"
    edited.write_text(open(P.__file__).read().replace('"Passages:"', '"Documents:"'))
    assert 'Documents:' in edited.read_text()
    monkeypatch.setattr(P, "__file__", str(edited))
    assert S.surface_hash() != base


def test_prompts_hash_covers_constants_and_the_builder_functions(monkeypatch):
    base = S.prompts_hash()
    monkeypatch.setattr(S, "AGENT_MORE", S.AGENT_MORE + " Hurry.")
    assert S.prompts_hash() != base
    monkeypatch.undo()
    assert S.prompts_hash() == base

    def passages_prompt(question, passages, as_of=None, header="Passages:"):  # a different builder
        return question

    monkeypatch.setattr(S, "passages_prompt", passages_prompt)
    assert S.prompts_hash() != base


def test_fingerprint_hashes_the_files_on_disk(tmp_path):
    import hashlib
    from heuresis.models_local import LocalEntailer
    onnx, tok = tmp_path / "model.onnx", tmp_path / "tokenizer.json"
    onnx.write_bytes(b"onnx bytes")
    tok.write_bytes(b"{}")
    m = object.__new__(LocalEntailer)  # no model is loaded: only the fingerprint is under test
    m.id, m.name, m._onnx_path, m._tok_path, m._fingerprint = "onnx:x/y", "x/y", str(onnx), str(tok), None
    assert m.fingerprint() == {"id": "onnx:x/y",
                               "onnx_sha256": hashlib.sha256(b"onnx bytes").hexdigest(),
                               "tokenizer_sha256": hashlib.sha256(b"{}").hexdigest()}
    onnx.write_bytes(b"other")  # cached after the first call
    assert m.fingerprint()["onnx_sha256"] == hashlib.sha256(b"onnx bytes").hexdigest()
    assert S.fingerprint_of(m)["id"] == "onnx:x/y"
    assert S.fingerprint_of(None)["note"] == "not used"


def test_draft_raws_drop_the_answers_question_reply_only_when_that_call_ran():
    from heuresis.bench.systems import _draft_raws
    from heuresis.model import StageTrace
    ran = [StageTrace("draft", 1.0, 10, 5), StageTrace("answers_question", 1.0, 50, 1, 0.0, 0, "x")]
    assert _draft_raws(["draft text", "NO"], ran) == ["draft text"]
    failed = [StageTrace("draft", 1.0, 10, 5), StageTrace("answers_question", 1.0, 0, 0, 0.0, 0, "model error: X")]
    assert _draft_raws(["draft text"], failed) == ["draft text"]
    assert _draft_raws(["draft text"], [StageTrace("draft", 1.0, 10, 5)]) == ["draft text"]


def test_variants_of_limits_the_time_aware_copies():
    from heuresis.bench.systems import build_context, build_systems
    from test_bench_common import make_dataset
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        ctx = build_context(make_dataset(pathlib.Path(d)), str(pathlib.Path(d) / "s.sqlite"))
        names = lambda **kw: [s.name for s in build_systems(ctx, ["bm25", "hybrid", "engine"], **kw)]
        assert names(time_aware_variants=True) == ["bm25", "hybrid", "engine", "bm25+asof", "hybrid+asof"]
        assert names(time_aware_variants=True, variants_of=["hybrid"]) == ["bm25", "hybrid", "engine", "hybrid+asof"]


# ---------------------------------------------------------------- engine variants (search / single)


def test_effective_engine_config_variants():
    base = load_config()
    eng = S.effective_engine_config(base)
    single = S.effective_engine_config(base, "engine_single")
    assert (eng.answer.mode, eng.decide.mode) == ("search", "grade")  # the engine's own default
    assert (single.answer.mode, single.decide.mode) == ("single", "strict")
    assert eng.draft.max_sentences == single.draft.max_sentences == S.ENGINE_MAX_SENTENCES
    assert (base.answer.mode, base.decide.mode) == ("search", "grade") and base.draft.max_sentences == 0
    # everything else is the same
    d1, d2 = config_to_dict(eng), config_to_dict(single)
    assert {k for k in d1 if d1[k] != d2[k]} == {"answer", "decide"}
    with pytest.raises(ValueError):
        S.effective_engine_config(base, "nope")


def test_engine_single_is_an_exploratory_system_with_its_own_engine(tmp_path):
    ds = make_dataset(tmp_path)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    eng, single = build_systems(ctx, ["engine", "engine_single"])
    assert (eng.name, eng.exploratory, single.name, single.exploratory) == \
        ("engine", False, "engine_single", True)
    assert ctx.engine("engine").config.answer.mode == "search"
    assert ctx.engine("engine_single").config.answer.mode == "single"
    assert ctx.engine("engine_single").config.decide.mode == "strict"
    assert ctx.engine("engine") is ctx.engine("engine")
    assert eng.describe()["answer_mode"] == "search" and single.describe()["decide_mode"] == "strict"
    assert ctx.engine_tap("engine") is not ctx.engine_tap("engine_single")


def test_engine_counts_calls_and_searches_like_agentic(tmp_path):
    ds = make_dataset(tmp_path)
    replies = iter(["SEARCH: Beta river length",
                    "The Beta river is 120 kilometres long [t1]."])
    rec = Recorder(lambda s, p: next(replies), usd=0.01)
    lg = Ledger(str(tmp_path / "l.jsonl"), 10.0)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec, ledger=lg)
    ctx.config.retrieve.rerank_out = 1  # a first retrieval too narrow to hold the answer
    eng = build_systems(ctx, ["engine"])[0]
    q = questions()[0]
    r = eng.answer(q)
    assert r.calls == 2 and r.searches == 2  # one model call per turn; first retrieval + 1 search
    assert r.usage.usd == pytest.approx(0.02) and lg.by_tag() == pytest.approx({"engine": 0.02})
    assert r.usage.tokens_in == sum(len(p.split()) for p in rec.prompts)
    assert len(r.usage.stop_reason) == 0  # the recorder reports none; the totals still add up
    assert "Searches used: 1 of 4." in rec.prompts[1]
    assert "searches" not in r.note and r.replay["draft_raws"] == [
        "SEARCH: Beta river length", "The Beta river is 120 kilometres long [t1]."]
    assert r.replay["draft_raw"].startswith("The Beta river")


def test_engine_single_makes_one_call_and_one_retrieval_and_is_metered_apart(tmp_path):
    ds = make_dataset(tmp_path)
    rec = Recorder(lambda s, p: "The Beta river is 120 kilometres long [t1].", usd=0.01)
    lg = Ledger(str(tmp_path / "l.jsonl"), 10.0)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), llm=rec, ledger=lg)
    single = build_systems(ctx, ["engine_single"])[0]
    r = single.answer(questions()[0])
    assert (r.calls, r.searches, r.status) == (1, 1, "answered")
    assert lg.by_tag() == pytest.approx({"engine_single": 0.01})
    assert "Searches used" not in rec.prompts[0]
