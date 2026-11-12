"""Phase 1, item C: replay candidate claim-support scores on the STORED dev engine rows.

Reads the run folders of the dev calibration run (engine rows with a `replay` payload),
recomputes a support score per claim with each candidate (the local NLI model is used for
some; no language-model API call is made), and re-applies the locked labelling and decision
rule of `heuresis.bench.calibrate.replay` over the 45 threshold pairs. Dev only.

Usage: HF_HUB_OFFLINE=1 python3 scripts/dev_fixes/verifier_replay.py RUN_ROOT OUT_JSON
       (RUN_ROOT holds main/<dataset>/ ; OUT_JSON is where the table is written)
"""
from __future__ import annotations

import copy
import json
import os
import random
import re
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from heuresis import draft as draft_mod  # noqa: E402
from heuresis.bench import calibrate as cal  # noqa: E402
from heuresis.bench.run import grade  # noqa: E402
from heuresis.bench.types import Question  # noqa: E402
from heuresis.surface.config import config_from_dict  # noqa: E402

DATASETS = ("musique", "multihoprag", "hoh")
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
STOP = set("""a an the of in on at to for from by with and or but is are was were be been being has have had do does did
that this these those it its as into than then so such not no yes also which who whom whose what when where why how there
their they them he she his her him we our you your i about over under between during after before while if
""".split())


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def lexical(claim: str, premises: list[str]) -> float:
    """Share of the claim's content tokens found in the cited passages (accent- and
    case-folded); 0 if any number of the claim is missing from them."""
    ptxt = fold(" ".join(premises))
    ptok = set(_WORD.findall(ptxt))
    nums = {n.replace(",", "") for n in _NUM.findall(ptxt)}
    body = re.sub(r"\[[tk]\d+\]", " ", claim)
    ctok = [t for t in _WORD.findall(fold(body)) if t not in STOP and not t.isdigit()]
    cnum = [n.replace(",", "") for n in _NUM.findall(fold(body))]
    if any(n not in nums and n not in ptok for n in cnum):
        return 0.0
    if not ctok:
        return 1.0 if cnum else 0.0
    return sum(t in ptok for t in ctok) / len(ctok)


def windows(text: str, max_len: int = 3) -> list[str]:
    sents = [s.strip() for s in _SENT.split(text) if s and s.strip()]
    out = []
    for i in range(len(sents)):
        for k in range(1, max_len + 1):
            if i + k <= len(sents):
                out.append(" ".join(sents[i:i + k]))
    return out or [text]


def load_rows(root):
    items = []
    for d in DATASETS:
        man = json.load(open(f"{root}/main/{d}/manifest.json"))
        assert man["split"] == "dev"
        cfg = config_from_dict(man["engine_config"])
        for line in open(f"{root}/main/{d}/results.jsonl"):
            r = json.loads(line)
            if r["system"] == "engine":
                items.append((d, r, cfg))
    return items


def premises_of(rp, c):
    P = {p["mark"]: p for p in rp["passages"]}
    T = {t["mark"]: t for t in rp["tool_results"]}
    out = []
    for m in c["passage_marks"]:
        if m in P:
            out.append(("p", P[m]["title"], P[m]["text"]))
    for m in c["tool_marks"]:
        if m in T and T[m]["ok"]:
            out.append(("t", "", T[m]["value_text"]))
    return out


def draft_correct(r):
    rp = r["replay"]
    d = draft_mod.parse_draft(rp.get("draft_raw", ""))
    res = [draft_mod.ToolResult(mark=t["mark"], tool=t["tool"], args=t.get("args") or {}, ok=t["ok"],
                                value=t["value_text"], error=t.get("error", "")) for t in rp["tool_results"]]
    text = draft_mod.render(d, res)
    q = Question(id=r["qid"], text="", answers=tuple(rp.get("answers") or ()), answerable=bool(r.get("answerable", True)))
    return grade(q, "answered", text)["outcome"] == "correct"


def score_all(items, ent, cache_path):
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    need = {}
    def want(prem, hyp):
        k = prem + "\x00" + hyp
        if k not in cache:
            need[k] = (prem, hyp)
    for d, r, cfg in items:
        rp = r["replay"]
        for c in rp.get("claims", []):
            prs = premises_of(rp, c)
            if not prs:
                continue
            h = c["text"]
            want("\n".join(t for _, _, t in prs), h)                                    # C1 current
            want("\n".join((ti + ". " if ti else "") + t for _, ti, t in prs), h)       # C1t
            for _, ti, t in prs:
                want(t, h)                                                              # C2
                want((ti + ". " if ti else "") + t, h)                                  # C2t
                for w in windows(t):
                    want(w, h)                                                          # C3
                    want((ti + ". " if ti else "") + w, h)                              # C3t
    keys = list(need)
    print("entailer pairs to score:", len(keys), "cached:", len(cache), flush=True)
    for i in range(0, len(keys), 256):
        chunk = keys[i:i + 256]
        sc = ent.entail([need[k] for k in chunk])
        for k, v in zip(chunk, sc):
            cache[k] = v
        print(f"  {min(i + 256, len(keys))}/{len(keys)}", flush=True)
    json.dump(cache, open(cache_path, "w"))
    return cache


CANDS = ["C1_current", "C1t_current_with_title", "C2_max_passage", "C2t_max_passage_title",
         "C3_max_sentence_window", "C3t_max_window_title", "C4_lexical", "C5_max(C3,C4)", "C5t_max(C3t,C4)"]


def claim_scores(rp, c, cache):
    prs = premises_of(rp, c)
    h = c["text"]
    if not prs:
        return {k: 0.0 for k in CANDS}
    g = lambda p: cache[p + "\x00" + h]
    t = lambda ti: (ti + ". " if ti else "")
    s = {}
    s["C1_current"] = g("\n".join(x for _, _, x in prs))
    s["C1t_current_with_title"] = g("\n".join(t(ti) + x for _, ti, x in prs))
    s["C2_max_passage"] = max(g(x) for _, _, x in prs)
    s["C2t_max_passage_title"] = max(g(t(ti) + x) for _, ti, x in prs)
    s["C3_max_sentence_window"] = max(g(w) for _, _, x in prs for w in windows(x))
    s["C3t_max_window_title"] = max(g(t(ti) + w) for _, ti, x in prs for w in windows(x))
    s["C4_lexical"] = lexical(h, [t(ti) + x for _, ti, x in prs])
    s["C5_max(C3,C4)"] = max(s["C3_max_sentence_window"], s["C4_lexical"])
    s["C5t_max(C3t,C4)"] = max(s["C3t_max_window_title"], s["C4_lexical"])
    return s


def auroc(pos, neg):
    if not pos or not neg:
        return float("nan")
    w = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return w / (len(pos) * len(neg))


def boot_auroc(pos, neg, iters=1000, seed=0):
    rng = random.Random(seed)
    xs = []
    for _ in range(iters):
        a = [rng.choice(pos) for _ in pos]
        b = [rng.choice(neg) for _ in neg]
        xs.append(auroc(a, b))
    xs.sort()
    return xs[int(.025 * iters)], xs[int(.975 * iters) - 1]


def penalised(items, scores, cand, sup, par):
    """Per-question score (+1/0/-1) at a threshold pair, using candidate supports."""
    out = []
    for (d, r, cfg), sc in zip(items, scores):
        if r.get("status") == "error":
            out.append(-1.0); continue
        row = copy.deepcopy(r)
        rp = row["replay"]
        if rp.get("verified"):
            for c, s in zip(rp["claims"], sc):
                c["support"] = s[cand]
        status, text, _ = cal.replay(row, sup, par, cfg)
        out.append(cal.outcome_of(row, status, text)["score"])
    return out


def boot_mean(xs, iters=2000, seed=0):
    rng = random.Random(seed)
    n = len(xs)
    m = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return m[int(.025 * iters)], m[int(.975 * iters) - 1]


def main(root, out_json):
    from heuresis.models_local import load_entailer
    items = load_rows(root)
    ent = load_entailer()
    cache = score_all(items, ent, os.path.join(os.path.dirname(out_json) or ".", "verifier_replay_cache.json"))
    scores = []
    for d, r, cfg in items:
        rp = r["replay"]
        scores.append([claim_scores(rp, c, cache) for c in rp.get("claims", [])])
    # claim-level AUROC: claims (exists, valid, numbers traced) of correct drafts vs wrong drafts
    lab = [draft_correct(r) if r["replay"].get("claims") else None for d, r, cfg in items]
    res = {"auroc": {}, "grid": {}, "n_claims": {}}
    for scope in ("pooled",) + DATASETS:
        for cand in CANDS:
            pos, neg = [], []
            for (d, r, cfg), sc, y in zip(items, scores, lab):
                if y is None or (scope != "pooled" and d != scope):
                    continue
                for c, s in zip(r["replay"]["claims"], sc):
                    ck = c["checks"]
                    if not (ck["exists"] and ck["valid_at_date"] and ck["numbers_traced"]):
                        continue
                    (pos if y else neg).append(s[cand])
            a = auroc(pos, neg)
            lo, hi = boot_auroc(pos, neg) if pos and neg else (float("nan"),) * 2
            res["auroc"][f"{scope}|{cand}"] = {"auroc": a, "lo": lo, "hi": hi, "pos": len(pos), "neg": len(neg)}
    grid_pairs = [(s / 10, p / 10) for s in range(1, 10) for p in range(1, s + 1)]
    for cand in CANDS:
        per_pair = {}
        for sup, par in grid_pairs:
            per_pair[(sup, par)] = penalised(items, scores, cand, sup, par)
        pooled_best = max(grid_pairs, key=lambda k: (sum(per_pair[k]), k[0], k[1]))
        entry = {"best_pair": pooled_best, "per_dataset": {}}
        for scope in ("pooled",) + DATASETS:
            idx = [i for i, (d, _, _) in enumerate(items) if scope == "pooled" or d == scope]
            for tag, pair in (("default(0.5,0.3)", (0.5, 0.3)), ("best_pooled", pooled_best)):
                xs = [per_pair[pair][i] for i in idx]
                lo, hi = boot_mean(xs)
                entry["per_dataset"][f"{scope}|{tag}"] = {"pair": pair, "score": sum(xs) / len(xs), "lo": lo, "hi": hi,
                                                           "correct": sum(x == 1 for x in xs), "wrong": sum(x == -1 for x in xs), "n": len(xs)}
            if scope != "pooled":
                best_d = max(grid_pairs, key=lambda k: (sum(per_pair[k][i] for i in idx), k[0], k[1]))
                xs = [per_pair[best_d][i] for i in idx]
                entry["per_dataset"][f"{scope}|best_own"] = {"pair": best_d, "score": sum(xs) / len(xs), "n": len(xs)}
        res["grid"][cand] = entry
        print(cand, "best pooled pair", pooled_best, "pooled score", round(entry["per_dataset"]["pooled|best_pooled"]["score"], 4),
              "at default", round(entry["per_dataset"]["pooled|default(0.5,0.3)"]["score"], 4), flush=True)
    json.dump(res, open(out_json, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
