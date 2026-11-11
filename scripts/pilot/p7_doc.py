"""Assemble docs/pilot-dev.md from the raw outputs in runs/pilot-dev/. Numbers are read from the
JSON files, never typed by hand."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.bench.stats import wilson_interval
from heuresis.locked.guard import locked_hash
from heuresis.bench.systems import prompts_hash

J = lambda *p: json.load(open(os.path.join(OUT, *p)))
W = lambda k, n: wilson_interval(k, n) if n else (float("nan"),) * 2
def prop(k, n):
    lo, hi = W(k, n)
    return f"{k}/{n} = {100*k/n:.0f}% [{100*lo:.0f}, {100*hi:.0f}]" if n else "n/a (n=0)"
CPT = 3.5
tok = lambda c: c / CPT
L = []
def add(s=""): L.append(s)
def table(head, rows):
    add("| " + " | ".join(head) + " |"); add("|" + "|".join("---" for _ in head) + "|")
    for r in rows: add("| " + " | ".join(str(x) for x in r) + " |")
    add()

man = J("musique", "dryrun", "manifest.json")
cost = J("p6_cost.json")
meta = {d: J(d, "dryrun", "p3_meta.json") for d in DATASETS}
total_wall = float(open(os.path.join(OUT, "wall_total_s.txt")).read()) if os.path.exists(os.path.join(OUT, "wall_total_s.txt")) else None

add("# Pilot on the dev split (zero cost)"); add()
add("Date: 2026-11-11. Every number is labelled **measured on dev (n=...)** or **assumed**. "
    "No language-model call was made: the generator in item 3 is the offline `EchoLLM`; the "
    "embedder, reranker and entailer are the local ONNX models. Only the `dev` split of each dataset "
    "was used (100 questions each). Wilson 95% intervals are given in brackets for every proportion.")
add()
add("## Versions at the time of the pilot"); add()
table(["Item", "Value"], [
    ["`locked_hash()`", f"`{locked_hash()}`"],
    ["surface config hash (`bench.run.surface_hash`, config + `DRAFT_SYSTEM`)", f"`{man['surface_hash']}`"],
    ["`prompts_hash()`", f"`{prompts_hash()}`"],
    ["embedder", f"`{man['models']['embedder']}`"], ["reranker", f"`{man['models']['reranker']}`"],
    ["entailer", f"`{man['models']['entailer']}`"],
    ["generator in the dry run", f"`{man['models']['generator']}` (offline fake). Configured paid model, never called: `{man['config']['draft']['model']}`"],
    ["retrieve config", f"`{json.dumps(man['config']['retrieve'])}`"],
])

# ---- item 1
add("## 1. Ingest and embedding"); add()
rows = []
for d in DATASETS:
    r = J(d, "p1_ingest.json")
    rows.append([d, r["counts"]["units"], r["versions_embedded"], f"{r['ingest_s']:.1f}", f"{r['embed_s']:.0f} ({r['embed_s']/60:.1f} min)",
                 f"{r['passages_per_s']:.1f}", f"{r['db_mb']:.0f}"])
add("Measured on the full built corpus (not a sample), 4 CPU cores, ONNX fp32, batch 64 (inner batch 16, length-sorted within the 64).")
add()
table(["dataset", "units", "versions embedded", "ingest s", "embedding time", "versions/s", "db size MB (incl. vectors)"], rows)
add("The `hoh` projection was 22 minutes from a 256-passage probe (under the 45-minute line), so all versions were embedded; no sampling was done.")
add()

# ---- item 2
add("## 2. Retrieval only (k = 8), answerable dev questions with gold units"); add()
add("Recall of any gold unit and of all gold units among the 8 returned passages (unit level). "
    "Time is wall-clock per query over all 100 dev questions, one thread, including embedding the query "
    "and the cross-encoder where used. BM25 = SQLite FTS5 `bm25()`; the packaged config is used for all legs "
    "(k_lexical 50, k_dense 50, rrf_k 60, rerank 50 -> 8). The cascade is run with a default `Query` (`intent=lookup`), i.e. without the router.")
add()
LAB = {"a_bm25": "a. BM25", "b_dense": "b. dense", "c_rrf": "c. BM25+dense RRF", "d_rerank": "d. c + rerank", "e_cascade": "e. default cascade"}
for d in DATASETS:
    p2 = J(d, "p2_retrieval.json")
    modes = [m for m in ("none", "dated", "today") if f"{m}/a_bm25" in p2["results"]]
    for mode in modes:
        title = d if mode == "none" else f"{d}, as-of = {'question date' if mode == 'dated' else 'today (not time-aware)'}"
        add(f"### {title}"); add()
        rows = []
        for s, lab in LAB.items():
            recs = p2["results"][f"{mode}/{s}"]
            sc = [r for r in recs if "any" in r]; n = len(sc)
            row = [lab, prop(sum(r["any"] for r in sc), n), prop(sum(r["all"] for r in sc), n),
                   f"{np.mean([r['ms'] for r in recs]):.0f}"]
            if d == "hoh":
                row.append(prop(sum(r["version_ok"] for r in sc), n))
            rows.append(row)
        head = ["system", "any gold unit @8", "all gold units @8", "ms / query"] + (["in-force version retrieved"] if d == "hoh" else [])
        table(head, rows)
        recs = p2["results"][f"{mode}/e_cascade"]
        sc = [r for r in recs if "any" in r]
        fired = [r for r in sc if r["extra"]["fired"]]; nf = [r for r in sc if not r["extra"]["fired"]]
        allq = [r for r in recs]
        add(f"Cascade early stop (measured on dev): fired on {sum(r['extra']['fired'] for r in allq)}/{len(allq)} questions "
            f"({sum(r['extra']['fired'] for r in sc)}/{len(sc)} of the scored ones). Recall of any / all gold unit:")
        add()
        table(["subset", "n", "any @8", "all @8"] + (["in-force version"] if d == "hoh" else []),
              [[nm, len(sub), prop(sum(r["any"] for r in sub), len(sub)), prop(sum(r["all"] for r in sub), len(sub))]
               + ([prop(sum(r["version_ok"] for r in sub), len(sub))] if d == "hoh" else [])
               for nm, sub in (("early stop fired", fired), ("did not fire", nf))])
        if d == "hoh":
            add("In-force version by question kind (measured on dev):"); add()
            rows = []
            for s, lab in LAB.items():
                sc2 = [r for r in p2["results"][f"{mode}/{s}"] if "any" in r]
                cell = []
                for kind in ("current", "outdated"):
                    sub = [r for r in sc2 if r["kind"] == kind]
                    cell.append(prop(sum(r["version_ok"] for r in sub), len(sub)))
                rows.append([lab] + cell)
            table(["system", "kind = current", "kind = outdated"], rows)

# ---- item 3
add("## 3. Harness end to end in dry-run mode: prompt sizes and calls"); add()
add("Command path: `heuresis.bench.run.run(dataset, 'dev', systems, out, ledger, dry_run=True)` with all eight systems, `EchoLLM` "
    "as generator, local retrieval models, one worker, baselines not time-aware (the default). Characters = system prompt + user prompt "
    "of every model call, summed over the calls of a question (measured on dev, n=100). Tokens = characters / 3.5 (**assumed** conversion, not measured; "
    "the dataset manifests use /4).")
add()
for d in DATASETS:
    cc = J(d, "dryrun", "call_chars.json")
    rows_raw = [json.loads(l) for l in open(os.path.join(OUT, d, "dryrun", "results.jsonl"))]
    by = {}
    for r in rows_raw: by.setdefault(r["system"], []).append(r)
    chars = {}
    for k, v in cc.items():
        s, q = k.split("|", 1); chars.setdefault(s, {})[q] = sum(v)
    add(f"### {d}"); add()
    rows = []
    for s in ("closed_book", "bm25", "vector", "hybrid_rerank", "agentic", "long_context", "engine", "oracle"):
        if s not in by:
            rows.append([s, "unavailable", "", "", "", meta[d]["unavailable"].get(s, "")]); continue
        a = np.array(list(chars[s].values()))
        calls = np.mean([r["calls"] for r in by[s]])
        err = sum(1 for r in by[s] if r["status"] == "error")
        nonn = sum(1 for r in by[s] if r["status"] != "error")
        rows.append([s, f"{a.mean():,.0f}", f"{np.percentile(a,95):,.0f}", f"{tok(a.mean()):,.0f} / {tok(np.percentile(a,95)):,.0f}",
                     f"{calls:.2f}", f"rows {len(by[s])}, errors {err}"])
    table(["system", "mean chars", "p95 chars", "mean / p95 tokens (assumed /3.5)", "mean calls (EchoLLM)", "note"], rows)
    ag = J(d, "p3b_agentic.json")
    add(f"`agentic` analytic (the offline fake never searches, so its row above is a single call with no passages). Built with the real prompt code, "
        f"search i returns the next 5 passages of the hybrid+rerank ranking, query text = the question; calls = searches + 1 (analytic, n={ag['n']} dev questions):")
    add()
    table(["searches", "calls", "mean chars", "p95 chars", "mean / p95 tokens (assumed /3.5)"],
          [[s, f"{v['mean_calls']:.0f}", f"{v['mean_chars']:,.0f}", f"{v['p95_chars']:,.0f}", f"{tok(v['mean_chars']):,.0f} / {tok(v['p95_chars']):,.0f}"]
           for s, v in ag["searches"].items()])
add("Unavailable systems: `long_context` on all three datasets, because the corpus is far above its ~90,000-token limit "
    "(manifest `corpus_tokens`: " + ", ".join(f"{d} {J(d,'dryrun','manifest.json')['corpus_tokens']:,}" for d in DATASETS) + "). "
    "`agentic` with the offline fake is available but does not exercise its loop (see the analytic rows).")
add()
add("Harness reports written by the pipeline (`report.write`, 200 bootstrap iterations) are in `runs/pilot-dev/<dataset>/dryrun/results.md`; "
    "their accuracy columns are meaningless here (EchoLLM) and are not used.")
add()

# ---- item 4
p4 = J("multihoprag", "p4_longctx.json")
add("## 4. Long-context feasibility for `multihoprag` (reduced-corpus tier)"); add()
add("Articles (unit id without `#n`, e.g. `multihoprag:aab13a0697b`) sorted by `sha256(article id)` and added in that order while the rendered prompt "
    "stays under 80,000 tokens; the first article that would not fit stops the selection. Prompt size is the document block as `long_context` "
    "renders it (one line per passage with title and validity span). Dev: " f"{p4['dev_n']} questions, {p4['dev_answerable']} answerable, {p4['dev_unanswerable']} unanswerable (measured on dev).")
add()
rows = []
for lab, key in (("tokens = chars/3.5 (assumed)", "chars_over_3.5"), ("tokens = chars/4 (manifest convention)", "chars_over_4")):
    v = p4[key]
    rows.append([lab, f"{v['articles']} of {p4['n_articles']} ({100*v['share_of_articles']:.1f}%)", v["passages"], f"{v['prompt_tokens_est']:,.0f}",
                 f"{v['dev_all_gold_inside']}/{p4['dev_answerable']}", f"{v['dev_any_gold_inside']}/{p4['dev_answerable']}",
                 f"{v['dev_unanswerable_valid']}/{p4['dev_unanswerable']}", v["dev_usable_total"]])
table(["token rule", "articles chosen", "passages", "est. tokens", "dev answerable with ALL gold inside", "with ANY gold inside", "dev unanswerable still valid", "usable dev questions"], rows)
g = p4["gold_articles_union"]
add(f"For scale (measured on dev): the {g['articles']} distinct articles that hold the gold evidence of the {p4['dev_answerable']} answerable dev questions "
    f"alone would need about {g['tokens_est_chars_3.5']:,.0f} tokens (chars/3.5); a tier chosen by gold would also leak the answers' location, so it is not an option. "
    f"Gold articles per question (dev): {p4['gold_articles_per_q']}.")
add()

# ---- item 5
add("## 5. Entailer sanity check without a language model"); add()
add("**Crude proxy, not a measurement of verification quality on drafted answers.** Matched pairs: (gold passage, statement). Mismatched: the same statement against a random "
    "non-gold passage (seeded draw from all versions of the store). Premise = gold passage (for multi-gold questions, the gold passage that contains the answer, else the first). "
    "Statement S2 = `<question> <gold answer>` (all pairs); S1 = a minimal declarative rewrite `The X was <answer>.` for questions of the form \"What/Who is/was X?\" (only where the rule fires). "
    "Containment = the normalised gold answer occurs in the passage, no model involved. Threshold = packaged `verify.support_threshold`.")
add()
for d in DATASETS:
    p5 = J(d, "p5_verifier.json")
    add(f"### {d} (n pairs = {p5['n_pairs']}, entailer throughput {p5['throughput_pairs_per_s']:.1f} pairs/s)"); add()
    rows = []
    for lab in ("S2_question_plus_answer", "S1_declarative"):
        v = p5[lab]
        if "auroc" not in v:
            rows.append([lab, v.get("n", 0), "too few", "", "", "", "", "", ""]); continue
        for nm in ("matched", "mismatched"):
            x = v[nm]
            rows.append([lab if nm == "matched" else "", nm, x["n"], f"{x['mean']:.3f}", f"{x['q1']:.3f} / {x['median']:.3f} / {x['q3']:.3f}",
                         prop(*v[nm + "_ge_thr"][:2]), f"{v['auroc']:.3f} [{v['auroc_ci95_bootstrap'][0]:.3f}, {v['auroc_ci95_bootstrap'][1]:.3f}]" if nm == "matched" else "", ""])
    table(["statement", "pairs", "n", "mean score", "Q1 / median / Q3", f"score >= threshold", "AUROC [95% bootstrap]", ""], rows)
    c = p5["containment"]
    add(f"Containment of the gold answer: gold passage {prop(*c['gold_passage'][:2])}, random passage {prop(*c['random_passage'][:2])}.")
    add()

# ---- item 6
C = cost["constants"]
add("## 6. Cost model (arithmetic on measured prompt sizes)"); add()
add(f"**Assumed:** tokens = chars/{C['chars_per_token']}; {C['output_tokens_per_call']} output tokens per call; ${C['usd_per_m_in']}/M input and ${C['usd_per_m_out']}/M output tokens; "
    f"{C['questions']} test questions per dataset, one run; any single request above {C['big_request_tokens']:,} prompt tokens is priced at {C['big_mult']:.0f}x (input and output); "
    "the prompt-size distribution of the dev split is taken to represent the test split (an extrapolation). `long_context` is excluded (unavailable). "
    "`engine` calls are those of the offline fake (a real draft that requests tools adds a follow-up call). `agentic` is shown for 1, 2 and 4 searches (analytic).")
add()
sysorder = ["closed_book", "bm25", "vector", "hybrid_rerank", "agentic_1search", "agentic_2search", "agentic_4search", "engine", "oracle"]
rows = []
for s in sysorder:
    r = [s]
    for d in DATASETS:
        v = cost["datasets"][d][s]
        r.append(f"{v['tokens_in_per_q']:,.0f} in, {v['calls_per_q']:.0f} call(s): ${v['usd_500']:.2f}")
    r.append(f"${cost['total_three_datasets_usd'][s]:.2f}")
    rows.append(r)
table(["system", "musique (500 q)", "multihoprag (500 q)", "hoh (500 q)", "total, 3 datasets"], rows)
sel = lambda ag: sum(cost["total_three_datasets_usd"][s] for s in ("closed_book", "bm25", "vector", "hybrid_rerank", ag, "engine", "oracle"))
add(f"Total for all seven available systems plus `oracle`, one run on 3 x 500 questions: **${sel('agentic_1search'):.2f}** (agentic at 1 search), "
    f"**${sel('agentic_2search'):.2f}** (2 searches), **${sel('agentic_4search'):.2f}** (4 searches). No request exceeds {C['big_request_tokens']:,} tokens, so the 5x rule never applies "
    "(`long_context` would trigger it on every request).")
add()
add("Batch API (50% off) on single-call systems (`closed_book`, `bm25`, `vector`, `hybrid_rerank`, `oracle`), assumed to apply to input and output:")
add()
table(["system", "saving, 3 datasets"], [[s, f"${v:.2f}"] for s, v in cost["batch_saving_usd"].items()] + [["**total**", f"**${cost['batch_saving_total_usd']:.2f}**"]])
add("`agentic` is sequential (each search depends on the previous reply) and `engine` may need a follow-up call after tool results, so neither is counted as batchable.")
add()

add("The low absolute scores of `S2` mostly reflect its form (a question followed by an answer is not a declarative); only the separation between matched and mismatched pairs and the throughput are of interest here.")
add()
add("## Side findings (measured on dev)"); add()
add("- **Cross-encoder rerank lowers recall on `multihoprag`.** Any-gold recall @8 falls from 80/88 (BM25+dense RRF) to 67/88 after the rerank, and all-gold from 23/88 to 12/88 (item 2). It raises recall on `musique` (89 -> 95 any) and lowers it slightly on `hoh` (98 -> 92). The default cascade inherits this because rerank is always on.")
add("- **The early stop saves little time as configured.** The rerank stage still runs over the lexical list after an early stop, so the cascade costs about as much as retrieval with rerank on `musique` and `multihoprag`; it is faster only on `hoh`, where the dense scan dominates. It fired on 51, 38 and 95-97 of 100 dev questions (musique, multihoprag, hoh).")
add("- **Router date rule on an undated corpus (possible bug, not fixed).** In `heuresis.router.understand` (built-in date rule) a date in the question text becomes `as_of.valid`. `musique` units carry a placeholder `create` event dated 1970-01-01, so a question that mentions an earlier date has no version in force and the engine abstains with `not_valid_at_date`. In the dry run this hit `musique:2hop__47071_162399` (\"... on 4th february 1928 ...\"); the router also turned the \"4th february 1928\" into 1928-02-29. Minimal reproduction: an in-memory `Engine` over one unit whose only event is dated 1970-01-01, then `ask(\"When did the person who launched the Bardoli Satyagraha on 4th february 1928 die?\")` returns `abstained` / `not_valid_at_date`, while the same question without the date is answered. The router found a date in 4 / 4 / 1 of the 100 dev questions of `musique` / `multihoprag` / `hoh`. In the benchmark the engine is called with the question's own `as_of` (None for the two undated sets), and a caller-supplied `as_of` wins only when it is set, so undated corpora are exposed.")
add()
add("## Reproduce"); add()
add("```")
add("export HF_HUB_OFFLINE=1   # the loaders then use only the cached models; nothing is downloaded")
add("for d in musique multihoprag hoh; do python3 scripts/pilot/p1_ingest.py $d; done      # item 1 (about 35 min on 4 cores)")
add("for d in musique multihoprag hoh; do python3 scripts/pilot/p2_retrieval.py $d; done   # item 2")
add("for d in musique multihoprag hoh; do python3 scripts/pilot/p3_dryrun.py $d; python3 scripts/pilot/p3b_agentic.py $d; done   # item 3")
add("python3 scripts/pilot/p4_longctx.py                                                     # item 4")
add("for d in musique multihoprag hoh; do python3 scripts/pilot/p5_verifier.py $d; done      # item 5")
add("python3 scripts/pilot/p6_cost.py                                                        # item 6")
add("python3 scripts/pilot/p7_doc.py                                                         # this document")
add("```")
add()
add("Raw outputs: `runs/pilot-dev/` (git-ignored): `<dataset>/p1_ingest.json`, `p2_retrieval.json` (per-question), `p3b_agentic.json`, `p4_longctx.json`, `p5_verifier.json`, "
    "`<dataset>/dryrun/{results.jsonl,results.json,results.md,manifest.json,call_chars.json}`, `p6_cost.json`, and the stores `<dataset>/store.sqlite` (hoh: 0.7 GB).")
add()
if total_wall:
    add(f"Total pilot compute time (ingest through dry runs, excluding script writing): about {total_wall/60:.0f} minutes wall-clock on 4 cores.")
    add()
add("## What this does not show"); add()
for s in ("**No answer accuracy.** The generator was an offline echo; nothing here says how often any system answers correctly.",
          "**No verification quality on real drafts.** Item 5 scores statements built from gold answers against gold or random passages; model-written drafts are longer, paraphrased, multi-claim and sometimes wrong in subtler ways.",
          "**No abstention behaviour.** Unanswerable questions were only used for timing (item 2) and counted in item 4; no abstain decision was measured.",
          "**Dev split only** (100 questions per dataset, 88 answerable for `multihoprag`). Test and sealed splits were neither loaded into any output nor scored. Intervals are wide at n=100.",
          "Retrieval recall is unit-level and uses the question text as the query; the router, query rewriting, expansion and second-round switches are off in the packaged config and were not exercised.",
          "Prompt sizes come from one deterministic retrieval per question; real model replies (search queries, tool calls) will change multi-call systems. Token counts use an assumed 3.5 characters per token.",
          "Timings are for a 4-core CPU, single thread of queries, warm file cache; the `hoh` dense scan reads every in-force vector from SQLite on every query.",
          "The cost model is an extrapolation from dev prompt sizes to 500 test questions at assumed prices; it is not a quote."):
    add("- " + s)
add()
open(os.path.join(ROOT, "docs", "pilot-dev.md"), "w").write("\n".join(L) + "\n")
print("written", len(L), "lines")
