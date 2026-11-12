"""The citation-integrity metric, on a synthetic store (no model, no network)."""
import csv
import json

import pytest

from heuresis.bench import citations as C
from heuresis.domains import get_domain
from heuresis.model import Event, Source, Unit
from heuresis.store import Store

LEI = "urn:lex:br:federal:lei:2020-03-10;1"


@pytest.fixture
def store():
    st = Store(":memory:")
    uid1, uid2, uid3 = (f"{LEI}!art{n}" for n in (1, 2, 3))
    st.add([Source(LEI, "norm", 3, 3, None, {"title": "Lei nº 1, de 10 de março de 2020"})],
           [Unit(u, LEI, "article", None, u) for u in (uid1, uid2, uid3)],
           [Event("a", uid1, "create", "2020-03-10", "Art. 1º Texto um.", "2020-03-10"),
            Event("b", uid2, "create", "2020-03-10", "Art. 2º Texto dois antigo.", "2020-03-10"),
            Event("c", uid2, "replace", "2022-01-01", "Art. 2º Texto dois novo.", "2022-01-01"),
            Event("d", uid3, "create", "2020-03-10", "Art. 3º Texto três.", "2020-03-10"),
            Event("e", uid3, "repeal", "2021-01-01", None, "2021-01-01")])
    st.rebuild()
    return st


DOM = get_domain("legal_br")


def test_analyse_statuses_and_in_force(store):
    a = C.analyse("Veja o art. 1º da Lei nº 1/2020 e o art. 3º da Lei nº 1/2020.", "2021-06-01", store, DOM)
    assert [(r["status"], r["in_force"]) for r in a["refs"]] == [("resolved", True), ("resolved", False)]
    a = C.analyse("Veja o art. 1º da Lei nº 1/2020.", "2019-01-01", store, DOM)   # before the norm existed
    assert a["refs"][0]["in_force"] is False
    a = C.analyse("art. 9 da Lei nº 1/2020; Lei nº 9/2020, art. 1; a Lei nº 1/2020", "2021-06-01", store, DOM)
    assert [r["status"] for r in a["refs"]] == ["unit_not_found", "container_not_found", "norm_only"]
    assert a["refs"][2]["in_force"] is None


def test_marks_are_added_and_held_to_the_same_standard(store):
    a = C.analyse("Texto sem citação livre [t1].", "2021-06-01", store, DOM, [f"{LEI}!art3", f"{LEI}!art1", "x!art1"])
    assert [(r["source"], r["status"], r["in_force"]) for r in a["refs"]] == [
        ("mark", "resolved", False), ("mark", "resolved", True), ("mark", "unit_not_found", None)]
    assert C.is_tainted(a)


def row(status, refs):
    return {"status": status, "system": "s", "qid": "q", "analysis": {"refs": refs, "n_refs": len(refs)}}


def ref(status, in_force=None, source="text", meta=None):
    return {"status": status, "in_force": in_force, "source": source, "meta": meta or {}, "unit_ids": [], "text": "t"}


def test_summarise_counts_and_headline():
    rows = [row("answered", [ref("resolved", True), ref("resolved", True)]),                 # clean
            row("answered", [ref("resolved", True), ref("container_not_found", meta={"kind": "lei", "year": "2020"})]),
            row("answered", [ref("resolved", False)]),                                         # not in force
            row("answered", []),                                                               # no reference
            row("abstained", [])]
    cov = lambda m: m.get("kind") == "lei" and m.get("year") == "2020"
    s = C.summarise(rows, cov)
    assert (s["rows"], s["answered"], s["abstained"]) == (5, 4, 1)
    assert s["counts"] == {"resolved": 4, "norm_only": 0, "unit_not_found": 0, "container_not_found": 1}
    assert s["exist_share"] == pytest.approx(4 / 5) and s["container_not_found_share"] == pytest.approx(1 / 5)
    assert s["in_force_share"] == pytest.approx(3 / 4)
    assert s["tainted"] == 2 and s["tainted_share"] == pytest.approx(2 / 4)
    assert s["no_reference"] == 1 and s["no_reference_share"] == pytest.approx(1 / 4)
    # a real norm outside the corpus is not called fabricated when the corpus does not cover it
    s2 = C.summarise(rows, lambda m: False)
    assert s2["tainted_covered_only"] == 1 and s2["tainted"] == 2


def test_summarise_with_no_answers():
    s = C.summarise([row("abstained", [])])
    assert s["answered"] == 0 and s["tainted_share"] is None and s["exist_share"] is None


def test_support_items_prompt_and_verdict_parsing(store):
    a = C.analyse("Sim. O art. 2º da Lei nº 1/2020 dispõe sobre o texto dois novo.", "2023-01-01", store, DOM)
    r = {"status": "answered", "system": "hybrid", "qid": "q1", "as_of": "2023-01-01", "analysis": a,
         "text": "Sim. O art. 2º da Lei nº 1/2020 dispõe sobre o texto dois novo."}
    items = C.support_items([r, {**r, "analysis": C.analyse("art. 3º da Lei nº 1/2020", "2023-01-01", store, DOM)}], store)
    assert len(items) == 1 and "Texto dois novo" in items[0]["provision"]      # the version in force at the date
    assert items[0]["sentence"].startswith("O art. 2º")
    assert "SUPPORTED or NOT_SUPPORTED" in C.support_prompt(items[0])
    assert C.parse_support("SUPPORTED") == "SUPPORTED" and C.parse_support("not supported") == "NOT_SUPPORTED"
    assert C.parse_support("maybe") is None

    class Fake:
        def complete(self, system, prompt, *, max_tokens=20):
            return "SUPPORTED", None
    v = C.judge_support(items, Fake())
    assert v[0]["verdict"] == "SUPPORTED"


def test_sample_csv_is_stratified_and_deterministic(tmp_path):
    items = [{"system": s, "qid": f"q{i}", "unit": f"u{i}", "reference": "r", "sentence": "s", "provision": "p",
              "as_of": "2024-01-01", "source": "text"} for s in ("a", "b") for i in range(30)]
    s1 = C.stratified_sample(items, 5, seed=1)
    assert [x["qid"] for x in s1] == [x["qid"] for x in C.stratified_sample(list(reversed(items)), 5, seed=1)]
    assert sum(x["system"] == "a" for x in s1) == 5 and sum(x["system"] == "b" for x in s1) == 5
    p = tmp_path / "s.csv"
    assert C.export_support_sample(items, {("a", "q1", "u1", "r"): "SUPPORTED"}, str(p), per_system=5) == 10
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    assert len(rows) == 10 and set(rows[0]) >= {"model_verdict", "human_verdict"} and all(r["human_verdict"] == "" for r in rows)


def test_analyse_run_writes_files(store, tmp_path, monkeypatch):
    """analyse_run reads a run folder's rows and writes citations.jsonl (no text)."""
    from heuresis.bench import report
    rows = [{"system": "hybrid", "qid": "q1", "status": "answered", "as_of": "2021-06-01", "kind": "k",
             "text": "Veja o art. 1º da Lei nº 1/2020."},
            {"system": "hybrid", "qid": "q2", "status": "abstained", "as_of": "2021-06-01", "text": ""}]
    monkeypatch.setattr(report, "load", lambda d: ({}, rows, None))
    db = tmp_path / "s.db"
    st = Store(str(db))
    st.add([Source(LEI, "norm", 3, 3, None, {"title": "Lei nº 1, de 10 de março de 2020"})],
           [Unit(f"{LEI}!art1", LEI, "article", None, "t")],
           [Event("a", f"{LEI}!art1", "create", "2020-03-10", "Art. 1º Texto.", "2020-03-10")])
    st.rebuild()
    st.close()
    out = C.analyse_run(str(tmp_path), str(db))
    assert len(out) == 2 and out[0]["analysis"]["refs"][0]["status"] == "resolved"
    written = [json.loads(l) for l in open(tmp_path / "citations.jsonl")]
    assert "text" not in written[0] and written[0]["analysis"]["n_refs"] == 1
    assert "hybrid" in C.table(C.summary_by_system(out))


def test_unit_not_found_in_a_stub_container_is_not_called_fabricated():
    stub = row("answered", [ref("unit_not_found", meta={"container_incomplete": True})])
    real = row("answered", [ref("unit_not_found")])
    s = C.summarise([stub, real], lambda m: True)
    assert s["unit_not_found_in_incomplete_container"] == 1
    assert s["tainted"] == 2 and s["tainted_covered_only"] == 1   # strict: both; restricted: only the real gap


def _trow(status, text, unit_ids, answerable=True, golds=("%s!art2#v0" % LEI,)):
    return {"status": status, "text": text, "system": "s", "qid": "q", "cluster": f"{LEI}!art2", "kind": "temporal_replace_before",
            "answerable": answerable, "gold_units": list(golds) if answerable else [],
            "analysis": {"refs": [{"unit_ids": unit_ids, "status": "resolved"}], "n_refs": 1}}


def test_temporal_outcomes(store):
    u = f"{LEI}!art2"
    # v0 = "texto dois antigo", v1 = "texto dois novo": the distinctive words are antigo / novo
    assert C.temporal_outcome(_trow("answered", "O art. 2º diz texto dois antigo.", [u]), store)["outcome"] == "gold_version"
    assert C.temporal_outcome(_trow("answered", "O art. 2º diz texto dois novo.", [u]), store)["outcome"] == "other_version"
    assert C.temporal_outcome(_trow("answered", "O art. 2º diz algo.", [u]), store)["outcome"] == "undetermined"
    assert C.temporal_outcome(_trow("answered", "texto dois antigo", [f"{LEI}!art1"]), store)["outcome"] == "unit_not_cited"
    assert C.temporal_outcome(_trow("abstained", "", []), store)["outcome"] == "abstained"
    # after a repeal nothing is in force: giving the provision as if it were is the error
    assert C.temporal_outcome(_trow("answered", "x", [u], answerable=False), store)["outcome"] == "cited_repealed"
    assert C.temporal_outcome(_trow("abstained", "", [], answerable=False), store)["outcome"] == "abstained"
    s = C.summarise_temporal([_trow("answered", "texto dois antigo", [u]), _trow("abstained", "", [])], store)
    assert s == {"s": {"gold_version": 1, "abstained": 1, "n": 2}}
