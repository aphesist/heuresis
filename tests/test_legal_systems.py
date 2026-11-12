"""The legal prompt set, the dataset attribute that selects it, and the whole legal test end to end
in dry-run mode with the fakes (no model, no network, synthetic text only)."""
import json
import os

from heuresis.bench import citations, report
from heuresis.bench import systems as S
from heuresis.bench.ledger import Ledger
from heuresis.bench.run import run
from heuresis.bench.systems import build_context, build_systems, legal_system
from heuresis.bench.types import Dataset, Question
from heuresis.model import Usage
from test_bench_common import make_dataset

LEI = "urn:lex:br:federal:lei:2020-03-10;1"


def legal_dataset(tmp_path):
    d = tmp_path / "corpus"
    d.mkdir()
    rows = {
        "sources.jsonl": [{"id": LEI, "kind": "norm", "authority": 3, "coverage": 4,
                           "meta": {"title": "Lei nº 1, de 10 de março de 2020"}}],
        "units.jsonl": [{"id": f"{LEI}!art{n}", "source_id": LEI, "kind": "article",
                         "title": f"Lei nº 1, de 10 de março de 2020 — Art. {n}"} for n in (1, 2)],
        "events.jsonl": [
            {"id": "a", "unit_id": LEI + "!art1", "op": "create", "date": "2020-03-10", "recorded_at": "2020-03-10",
             "text": "Art. 1º O zorblax sintético é obrigatório."},
            {"id": "b", "unit_id": LEI + "!art2", "op": "create", "date": "2020-03-10", "recorded_at": "2020-03-10",
             "text": "Art. 2º O quibblet sintético antigo é facultativo."},
            {"id": "c", "unit_id": LEI + "!art2", "op": "replace", "date": "2022-01-01", "recorded_at": "2022-01-01",
             "text": "Art. 2º O quibblet sintético novo é obrigatório."}],
        "edges.jsonl": []}
    for n, rs in rows.items():
        (d / n).write_text("\n".join(json.dumps(r) for r in rs), encoding="utf-8")
    qs = (Question("l1", "O zorblax é obrigatório?", ("sim",), as_of="2021-01-01", gold_units=(LEI + "!art1",), kind="gold"),
          Question("l2", "O quibblet é obrigatório?", (), as_of="2021-01-01", gold_units=(LEI + "!art2#v0",),
                   kind="temporal_replace_before"))
    return Dataset(name="legal", corpus_dir=str(d), questions={"dev": qs, "temporal": qs}, licence="test",
                   corpus_tokens=100, meta={"domain": "legal_br", "prompt_set": "legal_br"})


def test_the_old_prompts_are_pinned():
    # computed on main before this work: the Wikipedia-QA prompts must not change
    assert S.prompts_hash() == "c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b"
    assert S.surface_hash() == "547d7f32387e2e4aff33eaa5ff39a388b52084f3680e54515ccc3d1433d878b3"


def test_legal_system_prompts():
    assert legal_system(S.CLOSED_SYSTEM) == S.LEGAL_CLOSED
    assert legal_system(S.PASSAGES_SYSTEM) == S.LEGAL_PASSAGES
    assert legal_system(S.AGENT_SYSTEM.format(n=3)) == S.LEGAL_AGENT.format(n=3)
    other = "some engine instruction"
    assert legal_system(other).startswith(other) and "[tN]" in legal_system(other)
    for p in (S.LEGAL_CLOSED, S.LEGAL_PASSAGES, S.LEGAL_AGENT, S.LEGAL_FORMAT):
        assert "português" in p.lower() and "ABSTAIN" in p and "artigo" in p


class Rec:
    id = "rec"

    def __init__(self):
        self.systems = []

    def complete(self, system, prompt, *, max_tokens=600):
        self.systems.append(system)
        return "ABSTAIN", Usage(model="rec")


def test_prompt_set_is_selected_by_the_dataset_attribute(tmp_path):
    rec = Rec()
    ctx = build_context(legal_dataset(tmp_path), str(tmp_path / "s.db"), llm=rec)
    assert ctx.legal and ctx.engine_config().draft.max_sentences == 3
    ctx.llm_for("closed_book").complete(S.CLOSED_SYSTEM, "p")
    assert rec.systems == [S.LEGAL_CLOSED]
    old = Rec()
    ctx2 = build_context(make_dataset(tmp_path / "o"), str(tmp_path / "o.db"), llm=old)
    assert not ctx2.legal and ctx2.engine_config().draft.max_sentences == 2
    ctx2.llm_for("closed_book").complete(S.CLOSED_SYSTEM, "p")
    assert old.systems == [S.CLOSED_SYSTEM]


def test_end_to_end_dry_run_and_citation_metric(tmp_path):
    ds = legal_dataset(tmp_path)
    out = str(tmp_path / "out")
    lg = Ledger(str(tmp_path / "l.jsonl"), 10.0, dry_run=True)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"), ledger=lg)
    systems = build_systems(ctx, ["closed_book", "hybrid", "agentic", "engine"], time_aware_variants=True,
                            variants_of=["agentic"])
    assert [s.name for s in systems] == ["closed_book", "hybrid", "agentic", "engine", "agentic+asof"]
    st = run(ds, "dev", systems, out, lg, workers=2, dry_run=True)
    assert st["written"] == 10 and st["stopped"] is None
    # the engine runs its domain (the resolver gate is on) and rows carry what the metric needs
    eng = [r for r in (json.loads(l) for l in open(os.path.join(out, "results.jsonl"))) if r["system"] == "engine"]
    assert eng and all("cited_units" in r and r["as_of"] == "2021-01-01" for r in eng)
    analysed = citations.analyse_run(out, str(tmp_path / "s.sqlite"))
    assert {r["system"] for r in analysed} == {s.name for s in systems}
    summary = citations.summary_by_system(analysed)
    assert set(summary) == {s.name for s in systems} and "tainted_share" in summary["engine"]
    assert os.path.exists(os.path.join(out, "citations.jsonl"))


def test_legal_prompt_versions_and_the_engine_support_gate(tmp_path):
    rec = Rec()
    ds = legal_dataset(tmp_path)
    v2 = build_context(ds, str(tmp_path / "a.db"), llm=rec)                       # default: v2
    assert v2.engine_config().verify.support == "llm" and v2.engine_config("engine_single").verify.support != "llm"
    v2.llm_for("engine").complete("engine instruction", "p")
    assert rec.systems[-1] == "engine instruction" + S.LEGAL_ENGINE_SUFFIX_V2
    assert "SOMENTE o que o dispositivo citado diz" in S.LEGAL_ENGINE_SUFFIX_V2
    v1 = build_context(ds, str(tmp_path / "b.db"), llm=rec, legal_prompt="v1")
    assert v1.engine_config().verify.support == "window_title"
    v1.llm_for("engine").complete("engine instruction", "p")
    assert rec.systems[-1] == "engine instruction" + S.LEGAL_ENGINE_SUFFIX
    # the baselines are the same under both versions, and the old datasets never get the gate
    for ctx in (v1, v2):
        ctx.llm_for("closed_book").complete(S.CLOSED_SYSTEM, "p")
        assert rec.systems[-1] == S.LEGAL_CLOSED
    old = build_context(make_dataset(tmp_path / "o"), str(tmp_path / "o.db"), llm=rec)
    assert old.engine_config().verify.support == "window_title"


def test_engine_system_runs_with_the_gate_in_dry_run(tmp_path):
    ds = legal_dataset(tmp_path)
    ctx = build_context(ds, str(tmp_path / "s.sqlite"))
    out = str(tmp_path / "out")
    lg = Ledger(str(tmp_path / "l.jsonl"), 10.0, dry_run=True)
    run(ds, "dev", build_systems(ctx, ["engine"]), out, lg, workers=1, dry_run=True)
    rows = [json.loads(l) for l in open(os.path.join(out, "results.jsonl"))]
    assert len(rows) == 2 and all(r["status"] in ("answered", "abstained") and not r.get("error") for r in rows)
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["engine_config"]["verify"]["support"] == "llm"
