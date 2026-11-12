"""The model support gate (verify.support = "llm"): parsing, dropping, grading, cost, selection."""
import json

import pytest

from heuresis import AsOf, Engine
from heuresis import support_llm as S
from heuresis.model import Claim, Passage, Usage
from heuresis.surface.config import load_config

LEI = "urn:lex:br:federal:lei:2020-03-10;1"


class Script:
    def __init__(self, replies, usd=0.0):
        self.replies, self.n, self.usd, self.systems, self.prompts = list(replies), 0, usd, [], []
        self.id = "script"

    def complete(self, system, prompt, *, max_tokens=600):
        self.systems.append(system)
        self.prompts.append(prompt)
        r = self.replies[min(self.n, len(self.replies) - 1)]
        self.n += 1
        return r, Usage(model="script", tokens_in=10, tokens_out=5, usd=self.usd)


@pytest.fixture
def corpus(tmp_path):
    d = tmp_path / "c"
    d.mkdir()
    rows = {"sources.jsonl": [{"id": LEI, "kind": "norm", "authority": 3, "coverage": 4,
                               "meta": {"title": "Lei nº 1, de 10 de março de 2020"}}],
            "units.jsonl": [{"id": LEI + "!art1", "source_id": LEI, "kind": "article",
                             "title": "Lei nº 1, de 10 de março de 2020 — Art. 1"}],
            "events.jsonl": [{"id": "a", "unit_id": LEI + "!art1", "op": "create", "date": "2020-03-10",
                              "recorded_at": "2020-03-10", "text": "Art. 1º O zorblax sintético é obrigatório."}],
            "edges.jsonl": []}
    for n, rs in rows.items():
        (d / n).write_text("\n".join(json.dumps(r) for r in rs), encoding="utf-8")
    return str(d)


def ask(corpus, tmp_path, draft, gate, support_llm=True, mode="llm"):
    cfg = load_config()
    cfg.verify.support = mode
    llm = Script([draft])
    sup = Script([gate], usd=0.002) if support_llm else None
    eng = Engine.open(str(tmp_path / "s.db"), "legal_br", config=cfg, llm=llm, support_llm=sup)
    eng.ingest(corpus)
    ans = eng.ask("O zorblax é obrigatório?", as_of=AsOf(valid="2021-01-01"))
    eng.close()
    return ans, llm, sup


TWO = "O art. 1º da Lei nº 1/2020 diz que o zorblax é obrigatório [t1].\nO art. 1º da Lei nº 1/2020 obriga todos os cidadãos sempre [t1]."


def test_parse_and_apply():
    assert S.parse_gate("1: SUPPORTED\n2. not supported\n3 - PARTIAL\nfoo") == {1: "SUPPORTED", 2: "NOT_SUPPORTED", 3: "PARTIAL"}
    cs = [Claim("a", passage_marks=["t1"]), Claim("b", passage_marks=["t1"]), Claim("c", passage_marks=["t1"]), Claim("d", passage_marks=["t1"])]
    items = [(i + 1, c, []) for i, c in enumerate(cs)]
    counts = S.apply_verdicts(items, {1: "SUPPORTED", 2: "NOT_SUPPORTED", 3: "PARTIAL"})
    assert counts == {"SUPPORTED": 1, "PARTIAL": 1, "NOT_SUPPORTED": 1, "unreadable": 1}
    assert cs[1].checks["exists"] is False and cs[1].checks["llm_support"] is False
    assert cs[2].support == 0.4 and cs[2].label == "partial" and cs[3].checks["llm_support"] is True


def test_not_supported_sentence_is_dropped_and_cost_is_a_stage(corpus, tmp_path):
    ans, llm, sup = ask(corpus, tmp_path, TWO, "1: SUPPORTED\n2: NOT_SUPPORTED")
    assert ans.status == "partial" and "obriga todos" not in ans.text and "zorblax" in ans.text
    st = next(t for t in ans.trace if t.stage == "support_llm")
    assert st.usd == 0.002 and st.n_out == 1 and "N=1" in st.note
    assert sup.n == 1 and llm.n == 1                      # the gate used its own model
    assert sup.systems[0] == S.SUPPORT_GATE_SYSTEM and "Sentence 1:" in sup.prompts[0] and "As-of date: 2021-01-01" in sup.prompts[0]
    assert ans.usd >= 0.002


def test_partial_is_kept_and_lowers_the_grade(corpus, tmp_path):
    (tmp_path / "x").mkdir()
    a, _, _ = ask(corpus, tmp_path / "x", TWO.split("\n")[0], "1: SUPPORTED")
    (tmp_path / "y").mkdir()
    b, _, _ = ask(corpus, tmp_path / "y", TWO.split("\n")[0], "1: PARTIAL")
    assert a.status == b.status == "answered" and b.grade < a.grade


def test_nothing_survives_abstains_unsupported(corpus, tmp_path):
    ans, _, _ = ask(corpus, tmp_path, TWO, "1: NOT_SUPPORTED\n2: NOT_SUPPORTED")
    assert ans.status == "abstained" and ans.abstention.type == "unsupported" and ans.text == ""


def test_unreadable_reply_keeps_the_sentences(corpus, tmp_path):
    ans, _, _ = ask(corpus, tmp_path, TWO, "I cannot say")
    assert ans.status == "answered" and "unreadable=2" in next(t for t in ans.trace if t.stage == "support_llm").note


def test_default_mode_makes_no_extra_call(corpus, tmp_path):
    ans, llm, sup = ask(corpus, tmp_path, TWO.split("\n")[0], "1: NOT_SUPPORTED", mode="window_title")
    assert sup.n == 0 and not any(t.stage == "support_llm" for t in ans.trace)


def test_gate_falls_back_to_the_drafting_model(corpus, tmp_path):
    cfg = load_config()
    cfg.verify.support = "llm"
    llm = Script([TWO.split("\n")[0], "1: SUPPORTED"])
    eng = Engine.open(str(tmp_path / "f.db"), "legal_br", config=cfg, llm=llm)
    eng.ingest(corpus)
    ans = eng.ask("O zorblax é obrigatório?", as_of=AsOf(valid="2021-01-01"))
    eng.close()
    assert llm.n == 2 and ans.status == "answered"


def test_prompt_differs_from_the_benchmark_judge():
    from heuresis.bench.citations import SUPPORT_SYSTEM
    assert S.SUPPORT_GATE_SYSTEM != SUPPORT_SYSTEM and "PARTIAL" in S.SUPPORT_GATE_SYSTEM and "PARTIAL" not in SUPPORT_SYSTEM
