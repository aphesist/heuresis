"""Citation integrity: does a cited provision exist, was it in force, does it support the claim?

Applied IDENTICALLY to the answer text of every system. The domain's resolver
(``Domain.resolve_references``) finds the citations a lawyer would write; for systems that cite
by mark (the engine) the cited units are added, so every system is held to the same standard.

Per answer (``analyse``): the references found, each resolved against the store, and for the
resolved ones whether a version of the unit was in force at the question's date. Per run
(``summarise``): references per answer; existence (``container_not_found`` and ``unit_not_found``
reported separately, plus ``norm_only``); the in-force share; *tainted* answers (at least one
fabricated or not-in-force reference, the headline); answers with no reference at all. The support
of a claim by the cited text is judged by a model (``judge_support``, paid) and sampled to a CSV for
human checking (``export_support_sample``).

``container_not_found`` can mean fabricated OR real but outside the corpus; ``summarise`` reports
the headline both ways, and restricted to the containers a caller-supplied ``coverage`` predicate
says the corpus covers completely.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from typing import Any, Callable, Iterable, Sequence

from ..interfaces import domain_references
from ..model import AsOf

FABRICATED = ("container_not_found", "unit_not_found")
_MARK = re.compile(r"\[[tk]\d+\]")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ\"“])|\n+")
_ABBREV = re.compile(r"\b(?:arts?|inc|par|cf|c/c|n|nº|no)\.$", re.I)


def _sentences(text: str) -> list[str]:
    """Sentences, not splitting after an abbreviation such as "art." or "nº"."""
    out: list[str] = []
    for piece in _SENT.split(text):
        if out and _ABBREV.search(out[-1]):
            out[-1] += " " + piece
        else:
            out.append(piece)
    return out


def _in_force(store: Any, unit_id: str, as_of: str | None) -> bool:
    return store.text_at(unit_id, AsOf(valid=as_of)) is not None


def analyse(text: str, as_of: str | None, store: Any, domain: Any, cited_units: Sequence[str] = ()) -> dict:
    """References of one answer, resolved and checked against the date. Read-only."""
    refs = []
    for r in domain_references(domain, _MARK.sub("", text or ""), store):
        row = {"text": r.text, "status": r.status, "container": r.container, "unit": r.unit,
               "unit_ids": list(r.unit_ids), "meta": dict(r.meta), "source": "text", "in_force": None}
        if r.status == "resolved":
            row["in_force"] = all(_in_force(store, u, as_of) for u in r.unit_ids)
        refs.append(row)
    for u in dict.fromkeys(cited_units):
        refs.append({"text": u, "status": "resolved" if store.has_unit(u) else "unit_not_found",
                     "container": "", "unit": "", "unit_ids": [u], "meta": {}, "source": "mark",
                     "in_force": _in_force(store, u, as_of) if store.has_unit(u) else None})
    return {"refs": refs, "n_refs": len(refs)}


def is_tainted(a: dict, coverage: Callable[[dict], bool] | None = None) -> bool:
    """At least one fabricated or not-in-force reference. With ``coverage``, a
    ``container_not_found`` counts only when the predicate says the corpus covers that
    container completely (so a real norm outside the corpus is not called fabricated)."""
    for r in a["refs"]:
        if r["status"] == "unit_not_found":
            return True
        if r["status"] == "container_not_found" and (coverage is None or coverage(r["meta"])):
            return True
        if r["status"] == "resolved" and r["in_force"] is False:
            return True
    return False


def _share(n: int, d: int) -> float | None:
    return None if d == 0 else n / d


def summarise(rows: Iterable[dict], coverage: Callable[[dict], bool] | None = None) -> dict:
    """Aggregate ``analyse`` results. Each row: ``{"status": "answered"|"abstained", "analysis": {...}}``."""
    rows = list(rows)
    answered = [r for r in rows if r.get("status") == "answered"]
    refs = [x for r in answered for x in r["analysis"]["refs"]]
    text_refs = [x for x in refs if x["source"] == "text"]
    c = {s: sum(x["status"] == s for x in refs) for s in ("resolved", "norm_only", "unit_not_found", "container_not_found")}
    checkable = c["resolved"] + c["unit_not_found"] + c["container_not_found"]
    resolved = [x for x in refs if x["status"] == "resolved"]
    cnf_cov = [x for x in refs if x["status"] == "container_not_found" and (coverage is None or coverage(x["meta"]))]
    return {
        "rows": len(rows), "answered": len(answered), "abstained": len(rows) - len(answered),
        "references": len(refs), "references_free_text": len(text_refs),
        "references_per_answer": _share(len(refs), len(answered)),
        "counts": c,
        "exist_share": _share(c["resolved"], checkable),
        "container_not_found_share": _share(c["container_not_found"], checkable),
        "container_not_found_in_covered_share": _share(len(cnf_cov), checkable),
        "unit_not_found_share": _share(c["unit_not_found"], checkable),
        "in_force_share": _share(sum(x["in_force"] is True for x in resolved), len(resolved)),
        "tainted": sum(is_tainted(r["analysis"]) for r in answered),
        "tainted_share": _share(sum(is_tainted(r["analysis"]) for r in answered), len(answered)),
        "tainted_covered_only": sum(is_tainted(r["analysis"], coverage or (lambda m: False)) for r in answered),
        "tainted_covered_only_share": _share(
            sum(is_tainted(r["analysis"], coverage or (lambda m: False)) for r in answered), len(answered)),
        "no_reference": sum(r["analysis"]["n_refs"] == 0 for r in answered),
        "no_reference_share": _share(sum(r["analysis"]["n_refs"] == 0 for r in answered), len(answered)),
    }


# ----------------------------------------------------------------------------
# Support (model judge) and the human-check sample
# ----------------------------------------------------------------------------

SUPPORT_SYSTEM = (
    "You check a legal citation. You get the text of a provision, as in force on a date, and a "
    "sentence from an answer that cites it. Reply with exactly one word: SUPPORTED if the "
    "provision, as worded, states or clearly entails what the sentence claims about it; "
    "NOT_SUPPORTED if it does not (it says something different, is silent on the point, or the "
    "sentence adds content the provision does not contain)."
)


def sentence_of(text: str, span_text: str) -> str:
    """The sentence of ``text`` that holds ``span_text`` (the whole text when none does)."""
    clean = _MARK.sub("", text or "")
    for s in _sentences(clean):
        if span_text and span_text in s:
            return s.strip()
    return clean.strip()


def support_items(analysed: Iterable[dict], store: Any, *, max_chars: int = 3000) -> list[dict]:
    """One item per resolved, in-force reference: the sentence and the provision text in force."""
    items = []
    for r in analysed:
        if r.get("status") != "answered":
            continue
        for x in r["analysis"]["refs"]:
            if x["status"] != "resolved" or not x["in_force"]:
                continue
            v = store.text_at(x["unit_ids"][0], AsOf(valid=r.get("as_of")))
            if v is None:
                continue
            items.append({"system": r["system"], "qid": r["qid"], "unit": x["unit_ids"][0],
                          "reference": x["text"], "source": x["source"],
                          "sentence": sentence_of(r.get("text", ""), x["text"] if x["source"] == "text" else ""),
                          "provision": v.text[:max_chars], "as_of": r.get("as_of")})
    return items


def support_prompt(item: dict) -> str:
    return (f"Date: {item['as_of'] or 'today'}\nProvision ({item['unit']}):\n{item['provision']}\n\n"
            f"Sentence citing it:\n{item['sentence']}\n\nSUPPORTED or NOT_SUPPORTED?")


def parse_support(raw: str) -> str | None:
    w = (raw or "").strip().upper().replace(" ", "_").split("\n")[0]
    if w.startswith("NOT"):
        return "NOT_SUPPORTED"
    return "SUPPORTED" if w.startswith("SUPPORTED") else None


def judge_support(items: Sequence[dict], llm: Any, *, max_tokens: int = 20) -> list[dict]:
    """Ask the model judge about each item; unreadable verdicts are kept as ``None``."""
    out = []
    for it in items:
        raw, _u = llm.complete(SUPPORT_SYSTEM, support_prompt(it), max_tokens=max_tokens)
        out.append({**{k: it[k] for k in ("system", "qid", "unit", "reference")},
                    "verdict": parse_support(raw), "raw": (raw or "")[:40]})
    return out


def stratified_sample(items: Sequence[dict], per_system: int, seed: int = 0) -> list[dict]:
    """Deterministic sample, ``per_system`` items of each system (hash order)."""
    by: dict[str, list[dict]] = {}
    for it in items:
        by.setdefault(it["system"], []).append(it)
    out = []
    for s in sorted(by):
        key = lambda it: hashlib.sha256(f"{seed}:{it['system']}:{it['qid']}:{it['unit']}".encode()).hexdigest()
        out += sorted(by[s], key=key)[:per_system]
    return out


def export_support_sample(items: Sequence[dict], verdicts: dict[tuple, str | None], path: str, *,
                          per_system: int = 20, seed: int = 0) -> int:
    """CSV for human checking: the model's verdict and an empty ``human_verdict`` column."""
    sample = stratified_sample(items, per_system, seed)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["system", "qid", "unit", "reference", "as_of", "sentence", "provision",
                    "model_verdict", "human_verdict"])
        for it in sample:
            w.writerow([it["system"], it["qid"], it["unit"], it["reference"], it["as_of"], it["sentence"],
                        it["provision"], verdicts.get((it["system"], it["qid"], it["unit"], it["reference"])) or "", ""])
    return len(sample)


# ----------------------------------------------------------------------------
# Run folders
# ----------------------------------------------------------------------------

CITATIONS_FILE = "citations.jsonl"
SUMMARY_FILE = "citations_summary.json"
SUPPORT_FILE = "citation_support.jsonl"


def analyse_run(run_dir: str, db_path: str, domain: str = "legal_br") -> list[dict]:
    """Analyse every row of a run folder and write ``citations.jsonl`` (one row per system and
    question, without the answer text). Returns the analysed rows (with text, for the judge)."""
    from ..domains import get_domain
    from ..store import Store
    from . import report
    _manifest, rows, _ = report.load(run_dir)
    st, dom = Store(db_path), get_domain(domain)
    out = []
    try:
        for r in rows:
            if r.get("status") not in ("answered", "abstained"):
                continue
            a = analyse(r.get("text", "") if r["status"] == "answered" else "", r.get("as_of"), st, dom,
                        r.get("cited_units") or ())
            out.append({"system": r["system"], "qid": r["qid"], "status": r["status"], "as_of": r.get("as_of"),
                        "kind": r.get("kind"), "text": r.get("text", ""), "analysis": a})
    finally:
        st.close()
    with open(os.path.join(run_dir, CITATIONS_FILE), "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps({k: v for k, v in r.items() if k != "text"}, ensure_ascii=False, sort_keys=True) + "\n")
    return out


def summary_by_system(analysed: Sequence[dict], coverage: Callable[[dict], bool] | None = None) -> dict:
    systems: dict[str, list[dict]] = {}
    for r in analysed:
        systems.setdefault(r["system"], []).append(r)
    return {s: summarise(rs, coverage) for s, rs in sorted(systems.items())}


def table(summary: dict) -> str:
    """Markdown table of ``summary_by_system``."""
    def f(x):
        return "-" if x is None else f"{x:.1%}"
    head = ("| system | answered | refs/answer | exist | container not found | unit not found | in force | "
            "tainted | tainted (covered only) | no reference |\n|---|---|---|---|---|---|---|---|---|---|")
    rows = []
    for s, v in summary.items():
        rpa = "-" if v["references_per_answer"] is None else f"{v['references_per_answer']:.2f}"
        rows.append(f"| {s} | {v['answered']} | {rpa} | {f(v['exist_share'])} | {f(v['container_not_found_share'])} | "
                    f"{f(v['unit_not_found_share'])} | {f(v['in_force_share'])} | {f(v['tainted_share'])} | "
                    f"{f(v['tainted_covered_only_share'])} | {f(v['no_reference_share'])} |")
    return head + "\n" + "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m heuresis.bench.citations",
                                 description="Citation-integrity metric over a run folder (free); "
                                             "--paid adds the model support judge.")
    ap.add_argument("run_dir")
    ap.add_argument("--db", required=True, help="the SQLite store of the corpus the run used")
    ap.add_argument("--domain", default="legal_br")
    ap.add_argument("--paid", action="store_true", help="run the support judge (needs --cap and --ledger)")
    ap.add_argument("--cap", "--cap-usd", dest="cap_usd", type=float)
    ap.add_argument("--margin-usd", type=float, default=1.0)
    ap.add_argument("--estimate-usd", type=float, default=0.02)
    ap.add_argument("--ledger")
    ap.add_argument("--key-env", default="PROJECTS_ANTHROPIC_KEY", metavar="NAME")
    ap.add_argument("--model", default=None)
    ap.add_argument("--sample", type=int, default=20, help="items per system in the human-check CSV")
    a = ap.parse_args(argv)
    if a.paid and (a.cap_usd is None or not a.ledger):
        print("error: --paid needs --cap USD and --ledger PATH", file=sys.stderr)
        return 2
    if a.paid and not os.environ.get(a.key_env):
        print(f"error: environment variable {a.key_env} is not set; nothing was run", file=sys.stderr)
        return 2
    analysed = analyse_run(a.run_dir, a.db, a.domain)
    summary = summary_by_system(analysed)
    items: list[dict] = []
    if a.paid:
        from ..domains import get_domain
        from ..llm import AnthropicLLM
        from ..store import Store
        from ..surface.config import load_config
        from .ledger import Ledger, LedgerLLM
        from .systems import BENCH_THINKING
        st = Store(a.db)
        try:
            items = support_items(analysed, st)
        finally:
            st.close()
        inner = AnthropicLLM(a.model or load_config().draft.model, key_env=a.key_env, thinking=BENCH_THINKING)
        llm = LedgerLLM(inner, Ledger(a.ledger, a.cap_usd, a.margin_usd), "citation_support", a.estimate_usd)
        done = _load_support(a.run_dir)
        todo = [it for it in items if (it["system"], it["qid"], it["unit"], it["reference"]) not in done]
        with open(os.path.join(a.run_dir, SUPPORT_FILE), "a", encoding="utf-8") as fh:
            for it, v in zip(todo, judge_support(todo, llm)):
                fh.write(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n")
        verdicts = _load_support(a.run_dir)
        for s, v in summary.items():
            vs = [x for k, x in verdicts.items() if k[0] == s and x]
            v["support_judged"] = len(vs)
            v["support_share"] = _share(sum(x == "SUPPORTED" for x in vs), len(vs))
        export_support_sample(items, verdicts, os.path.join(a.run_dir, "citation_support_sample.csv"),
                              per_system=a.sample)
    with open(os.path.join(a.run_dir, SUMMARY_FILE), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(table(summary))
    return 0


def _load_support(run_dir: str) -> dict[tuple, str | None]:
    path = os.path.join(run_dir, SUPPORT_FILE)
    out: dict[tuple, str | None] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    out[(r["system"], r["qid"], r["unit"], r["reference"])] = r["verdict"]
                except (ValueError, KeyError):
                    continue
    return out


if __name__ == "__main__":
    sys.exit(main())
