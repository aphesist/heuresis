"""Offline (free) replay of the engine rows of the dev2 runs: what the penalised score would have been
if a sentence with no citation mark were KEPT in grade mode (the other deterministic checks as built).
Usage: uncited_replay.py runs/dev2   (calibration data; no model call)."""
import dataclasses, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from heuresis import draft as dm
from heuresis.bench.run import grade
from heuresis.bench.types import Question
from heuresis.model import ToolResult

def fails(c, keep_uncited):
    ch = c["checks"]; cited = bool(c["passage_marks"] or c["tool_marks"])
    ex = (not ch["exists"]) and (cited or not keep_uncited)
    return ex or not ch["valid_at_date"] or not ch["numbers_traced"]

root = sys.argv[1]
for cond in ("off", "default"):
    for d in ("musique", "multihoprag", "hoh", "pooled"):
        tot = {"as built": [0, 0, 0], "uncited kept": [0, 0, 0]}
        for dd in (("musique", "multihoprag", "hoh") if d == "pooled" else (d,)):
            for l in open(os.path.join(root, cond, dd, "results.jsonl")):
                r = json.loads(l)
                if r["system"] != "engine" or r.get("status") == "error": continue
                rp = r["replay"]; q = Question(id=r["qid"], text="", answers=tuple(rp["answers"]), answerable=r["answerable"])
                for name, keep in (("as built", False), ("uncited kept", True)):
                    if not rp["verified"] or rp["engine_status"] == "abstained" and rp["abstention"] not in (None, "unsupported"):
                        status, text = ("answered" if r["status"] == "answered" else "abstained"), r["text"]
                    else:
                        dr = dm.parse_draft(rp["draft_raw"])
                        if dr.declined: status, text = "abstained", ""
                        else:
                            bad = {c["text"] for c in rp["claims"] if fails(c, keep)}
                            kept = [s for s in dr.sentences if s.text not in bad]
                            if not kept: status, text = "abstained", ""
                            else:
                                status = "answered"
                                res = [ToolResult(mark=t["mark"], tool=t["tool"], args=t.get("args") or {}, ok=t["ok"], value=t["value_text"]) for t in rp["tool_results"]]
                                text = dm.render(dataclasses.replace(dr, sentences=kept), res)
                    g = grade(q, status, text)["outcome"]
                    tot[name][{"correct": 0, "wrong": 1, "abstained": 2}[g]] += 1
        for name, (c, w, a) in tot.items():
            n = c + w + a
            print(f"| {cond} | {d} | {name} | {c}/{w}/{a} | {(c - w) / n:+.3f} |")
