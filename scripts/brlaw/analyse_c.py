"""Phase C: engine-old (phase B) vs engine-new on dev and temporal. Usage: analyse_c.py OUT_JSON  (free)."""
import collections
import json
import re
import sys

from heuresis.bench import citations as C

OUT = sys.argv[1]
res = {}


def engine_only(d):
    out = {}
    for l in open(f"runs/brlaw/{d}/results.jsonl"):
        r = json.loads(l)
        if r["system"] == "engine":
            out[r["qid"]] = r
    return out


def jd(d):
    return {(r["system"], r["qid"]): r["verdict"] for r in map(json.loads, open(f"runs/brlaw/{d}/judge.jsonl"))} \
        if __import__("os").path.exists(f"runs/brlaw/{d}/judge.jsonl") else {}


def sup(d):
    out = {}
    for l in open(f"runs/brlaw/{d}/citation_support.jsonl"):
        r = json.loads(l)
        if r["system"] == "engine":
            out[(r["qid"], r["unit"], r["reference"])] = r["verdict"]
    return out


def norm(t):
    return re.sub(r"\W+", " ", re.sub(r"\[[tk]\d+\]", " ", t or "")).strip().lower()


for sp, old, new in (("dev", "dev", "c-dev"), ("temporal", "temporal", "c-temporal")):
    d = {}
    for tag, folder in (("engine_old", old), ("engine_new", new)):
        R = engine_only(folder)
        an = {a["qid"]: a for a in map(json.loads, open(f"runs/brlaw/{folder}/citations.jsonl")) if a["system"] == "engine"}
        ans = [a for a in an.values() if a["status"] == "answered"]
        sv = sup(folder)
        vs = [v for v in sv.values() if v]
        j = jd(folder)
        eq = sum(1 for (s, q), v in j.items() if s == "engine" and v == "EQUIVALENT")
        usd = sum(r["usd"] for r in R.values())
        t = json.load(open(f"runs/brlaw/{folder}/citations_summary.json"))
        # gate drops by type, from the stored claims' checks
        g = collections.Counter(); sent = 0
        for r in R.values():
            for c in (r.get("replay") or {}).get("claims", []):
                sent += 1
                ch = c["checks"]
                if not ch.get("valid_at_date", True): g["valid_at_date"] += 1
                if not ch.get("numbers_traced", True): g["numbers_traced"] += 1
                if ch.get("references_traced") is False: g["references_traced"] += 1
                if ch.get("llm_support") is False: g["llm_support"] += 1
                if not ch["exists"] and ch.get("references_traced", True) and ch.get("llm_support", True): g["exists_other"] += 1
        d[tag] = {
            "n": len(R), "answered": len(ans), "abstained": len(R) - len(ans),
            "tainted_strict": sum(C.is_tainted(a["analysis"]) for a in ans),
            "tainted_covered_only": sum(C.is_tainted(a["analysis"], lambda m: m.get("kind") in ("lei", "lei.complementar", "decreto.lei", "emenda.constitucional") and str(m.get("year", "")).isdigit() and 1946 <= int(m["year"]) <= 2025) for a in ans),
            "refs_per_answer": round(sum(a["analysis"]["n_refs"] for a in ans) / max(1, len(ans)), 2),
            "support_supported": [sum(v == "SUPPORTED" for v in vs), len(vs)],
            "equivalent": eq, "usd": round(usd, 4), "usd_per_question": round(usd / len(R), 5),
            "usd_per_equivalent": round(usd / eq, 4) if eq else None,
            "calls_mean": round(sum(r["calls"] for r in R.values()) / len(R), 2),
            "searches_mean": round(sum(r["searches"] for r in R.values()) / len(R), 2),
            "median_latency_ms": sorted(r["ms"] for r in R.values())[len(R) // 2],
            "sentences_drafted": sent, "gate_flags": dict(g), "temporal": t.get("temporal", {}).get("engine"),
        }
    res[sp] = d
# agreement between the engine's own support gate and the benchmark judge (new runs, kept sentences)
two = {"SUPPORTED": {"SUPPORTED": 0, "NOT_SUPPORTED": 0}, "PARTIAL": {"SUPPORTED": 0, "NOT_SUPPORTED": 0}}
for folder in ("c-dev", "c-temporal"):
    R = engine_only(folder)
    sv = sup(folder)
    anq = {a["qid"]: a for a in map(json.loads, open(f"runs/brlaw/{folder}/citations.jsonl")) if a["system"] == "engine"}
    for (qid, unit, ref), verdict in sv.items():
        if not verdict or qid not in R:
            continue
        # the sentence the judge saw = the answer sentence that holds the reference
        sentence = C.sentence_of(R[qid]["text"], ref)
        gate = None
        for c in (R[qid].get("replay") or {}).get("claims", []):
            if norm(c["text"]) == norm(sentence):
                gate = "SUPPORTED" if c["support"] >= 0.9 - 1e-6 else "PARTIAL" if abs(c["support"] - 0.4) < 1e-6 else None
        if gate:
            two[gate][verdict] += 1
res["agreement_gate_vs_judge"] = two
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
