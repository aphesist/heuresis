# dev2: the redesigned engine, phase A (free): what was built and how it was checked offline

**No paid call has been made for this work. No test or sealed split was loaded, scored, printed or run.**
Branch `agentic-engine` (from `main` at cbc3333). Everything below is code, tests, documents and an offline
dry run with the fakes. The dev2 check itself (phase B) has not been run.

## What was built

**A1. `answer.mode`** (`src/heuresis/surface/config.py`, `engine.py`, `draft.py`, `surface/prompts.py`).
`"single"` is the earlier behaviour, unchanged and still tested. `"search"` (new default): turn 1 shows the
passages of the engine's own cascade; the model answers (sentences with marks, `CALL` lines, or
`ABSTAIN <type>: reason`) or replies with exactly one line `SEARCH: <query>`. A search runs the same cascade
with the question's own as-of date and scope (`dataclasses.replace(query, text=<search query>)`, so the
router's as-of and scope are kept; every search is date-filtered in code), shows up to `answer.search_k`
(default 5) passages not shown before, with marks continuing the numbering, and the model gets the
accumulated context again. At most `answer.max_searches` (default 4); when none remain the prompt says so,
and a further `SEARCH` is an `unsupported` abstention with the trace note "search requested: ...; none left".
Passages go through the shared `passage_line`. Every model turn is a `draft` stage and every search a
`search` stage (tokens, cost, time); the budget is checked before each call. Passages that do not fit
`draft.max_context_chars` are dropped (never cut): the tail of the first retrieval as in single mode, and
the tail of a search's new passages. The passages in `Answer.passages` are exactly those the model saw.

**A2. `decide.mode`** (`src/heuresis/locked/decide.py`, so `locked_hash()` changed). `"strict"` is today's
rule. `"grade"` (new default): a sentence is dropped, or the answer withheld, only for a deterministic
failure (`deterministic_failure`: a cited mark that does not exist or a sentence with no mark, a cited version not in force at the
as-of date, a number found in no cited passage or tool result) or when the model abstains; if every
sentence fails one the answer is an abstention (`not_valid_at_date` if all failed only the date check, else
`unsupported`). Entailment support (`verify.support = window_title`, unchanged) sets only the grade (min of
support, version certainty, source coverage). A kept sentence below the support threshold is relabelled
`partial` (so its citations still count in `Answer.citations`); `status` is `answered`, or `partial` when
some sentence was dropped. `bench.calibrate` replays both modes.

**A3. Benchmark wiring** (`bench/systems.py`, `run.py`, `report.py`). `engine` runs the engine's default
configuration plus `draft.max_sentences = 2` (search + grade). New `engine_single` (exploratory, Table 6)
runs `answer.mode = "single"`, `decide.mode = "strict"`. `calls` counts model calls and `searches` counts
retrievals (first retrieval plus the model's searches; single-shot systems 1, `agentic` its `SEARCH`
actions). The manifest records `engine_config` and `engine_configs` (the effective configuration of each
engine system in the run). `bench.calibrate --split dev2 --system engine_single` and `bench.judge` accept
`dev2`.

**A4. `dev2`** (`bench/datasets.py`). Cut after dev, test and sealed from the questions in none of them, in
the same sha256(seed || id) order with the same per-stratum allocation. Its record is the manifest key
`dev2`; the `splits` record is unchanged.

### The exact new system prompt (`SEARCH_SYSTEM`)

```
Answer ONLY from the numbered passages. Never use outside knowledge. They are what was in force at the as-of date, and so is everything a search returns.
If the passages lack the answer, or only a step of it (for a multi-step question, first find the entity, then the fact about it), reply with exactly one line `SEARCH: <query>` and nothing else; a good query is short and names what you still need. Otherwise answer, combining passages when needed.
Format, one item per line:
- State the answer in the first sentence, then add only what is needed. Write short sentences. End EVERY sentence with the marks of ALL the passages that support it, like [t1] or [t1][t2].
- Never do arithmetic or date math yourself. Request it before the answer with a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write {k1} where the result goes and add the mark [k1] to that sentence.
- Abstain only when no search remains and the answer is still not in the passages: write only `ABSTAIN <type>: <reason>` with type one of: no_source, not_valid_at_date, conflict, false_premise, outside_coverage, unsupported, needs_input, tool_failed, out_of_scope, budget.
```

User prompt: `As-of date: <date or today>`, a `Tools:` line, `Passages:` (first retrieval), per search
`Search <i>: <query>` and the new passages (`(no new passages)` when none), `Question: <text>`,
`Searches used: <m> of <n>.`, `Answer in at most 2 short sentences.` (the engine system sets
`draft.max_sentences = 2`), and `Answer now, or reply with exactly one line `SEARCH: <query>`.` or, when none
remain, `No searches remain. Answer from the passages, or ABSTAIN.`

## dev2 sizes, and proof that dev, test and sealed are unchanged

| dataset | dev2 size | unanswerable in dev2 | questions in none of dev/test/sealed | `dev2` ids sha256 |
|---|---|---|---|---|
| `hoh` | 100 | 0 | 109,821 | `41868551aa1ec86a2c10c6b341541af5fb580dafb10a001b767289b3a738b93e` |
| `multihoprag` | 100 | 12 | 1,656 | `4ed5abcef4f97c0e63fbfc8001614ae4f4263cad8a923dfb678d520158ee88eb` |
| `musique` | 100 | 0 | 100 (all of them) | `5df630c5b6604b8b6ebcb984a5c98a2e4b77dcdf255f75d7b94ef49e32b3c49f` |

`musique` has 1,000 questions, so after 100 + 500 + 300 exactly 100 are left and dev2 is those 100.

Proof that the three existing splits are unchanged: (1) `tests/test_bench_datasets.py` asserts that
`split_questions` with and without dev2 gives identical dev/test/sealed id lists; (2) with
`HEURESIS_TEST_DATA=1`, `test_real_original_split_hashes_are_the_preregistered_ones` compares the id-list
hashes of the built manifests, and of `load()`, with the nine values in `PREREGISTRATION.md` section 2
(typed into the test from that table): 27 passed on the built corpora; (3) the built manifests'
`splits.question_ids_sha256` equal those values, e.g. dev `877ed197...` / `1e0ecec0...` / `8e995fe3...`, test
`67ba51b7...` / `ffc6230a...` / `73ae2d3b...`, sealed `b49defb6...` / `990c9256...` / `2cc5aa3f...`
(`hoh` / `multihoprag` / `musique`); `questions.jsonl` hashes are unchanged (`22746e97...`, `cf7f031d...`,
`ecab41c2...`). Only the `MANIFEST.json` file hash differs, because of the added `dev2` key: `hoh`
`f8fe31dc...`, `multihoprag` `cb0d9fab...`, `musique` `515a3eb3...` (full values in `PREREGISTRATION.md`
section 2). No question of dev2, test or sealed was printed; only ids were hashed.

## Tests

`PYTHONPATH=src python3 -m pytest -q tests`: **560 passed, 19 skipped** (before: 509 passed, 16 skipped; the
3 new skips are the real-data tests, which run with `HEURESIS_TEST_DATA=1`; with it set, the dataset tests
pass: 27 passed). Each commit's suite was run on that commit's tree (515 passed after the dev2 commit, 560
after the engine commit).

## Hashes (`PYTHONPATH=src python3 -m heuresis.cli hash`)

```
locked:  f13783b57968b2b8b9313bb31d89f83aac1ea417520a9de70676aa890d52ad53
surface: 547d7f32387e2e4aff33eaa5ff39a388b52084f3680e54515ccc3d1433d878b3
prompts: c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b
```

Before this work: locked `d98f86a5...`, surface `a7fe2849...`, prompts `c025db9e...` (unchanged: the shared
passage line and the baselines' prompts were not touched).

## Setup and dry run (A6)

`pip install -e ".[dev,local,bench]"` and `pyarrow`; datasets built with `heuresis.bench.datasets.build`;
stores built and embedded with the default local embedder (`onnx:intfloat/multilingual-e5-small`) by
`scripts/dev2/build_stores.py` into `runs/stores/<dataset>/store.sqlite` (not committed): `musique` 11,656
versions in 389 s, `multihoprag` 5,048, `hoh` 230,746 in 1,525 s on 4 cores. For each phase B run, copy the
store into the run folder (`cp runs/stores/D/store.sqlite runs/dev2/T/D/store.sqlite`); `bench.run` then
embeds nothing.

Offline dry run on `dev2` with the fakes, all systems plus the `+asof` copies
(`python -m heuresis.bench.run --dataset D --split dev2 --workers 2 --time-aware-variants`): `musique` 1,400
rows (100 questions x 14 systems), `multihoprag` 1,400, `hoh` 140 (`--limit 10`); 0 errors, 0 spent;
`bench.report` runs on all three; the manifests record `engine_configs` for `engine` and `engine_single`.
The fake model never asks for a search, so the dry run does not exercise `search`; the unit tests do
(`tests/test_engine_search.py`, 22 tests), and a smoke run with the real embedder and entailer and a
scripted model on the old `dev` split (6 questions each of `musique` and `multihoprag`, debugging only) showed
the search turn, marks continuing at t9..t13 and the verifier running on them.

## Estimated cost of phase B

From the measured per-question cost and tokens of the dev runs (`results/dev-fixes/main1`, thinking disabled;
`results/dev-fixes/thinking-default`, default thinking with `draft.max_tokens = 4096`), 100 questions x 3
datasets, haiku 5.5 at US$0.10 / 0.50 per million tokens (input / output), tokens as measured:

| | thinking disabled | thinking default (4096 cap) |
|---|---|---|
| closed_book, bm25, hybrid, hybrid_rerank, agentic, hybrid+asof, agentic+asof (measured per-question costs of the dev runs; hybrid_rerank and agentic+asof under default thinking scaled from `hybrid` and `agentic` by their ratio with thinking disabled) | 0.57 | 0.98 |
| `engine_single` (the old engine; the measured engine rows) | 0.10 | 0.13 |
| `engine`, search mode (model: first turn = the measured engine prompt of 2,400 / 4,762 / 1,324 input tokens on `musique` / `multihoprag` / `hoh`, each search adds 5 passages and the model gets the whole context again, one-line search replies of 25 output tokens, 200 under default thinking), at 1 / 2 / 4 searches per question on average | 0.23 / 0.37 / 0.72 | 0.29 / 0.46 / 0.85 |
| judge-assisted grade (about 900 calls per condition, as on dev, with the cap raised to 20 tokens) | about 0.04 | about 0.05 |
| **Total** | **0.9 / 1.1 / 1.4** | **1.4 / 1.6 / 1.9** |

Both conditions together: about **US$2.3 (1 search per question on average), US$2.7 (2), US$3.4 (4, the
worst case in which every question uses every search)**, under the cap of US$4.00 with margin 0.25 (the run
stops at US$3.75). The number of searches the model really asks for is unknown: `agentic` made 1.99, 1.37
and 1.11 searches per question on `musique`, `multihoprag` and `hoh` on dev (`mean_calls` - 1; thinking
disabled), and the engine's first retrieval already holds the answer for many questions, so 1 to 2 is the
expectation. The
estimate assumes the cap of 4 searches and the 24,000-character context limit are not exceeded; it
excludes retries after API errors, and any repeat run.

## Things that differ from, or that the documents did not settle

- **`locked/decide.py` changed.** The decision rule is in the locked folder, so `locked_hash()` changed; this
  is what the redesign asked for, and it is logged in `PREREGISTRATION.md` (deviations log, section 7).
- **An uncited sentence fails `exists` in grade mode** (changed after the phase A review: it is dropped, and an answer with no cited sentence is an `unsupported` abstention). `locked_hash()` is now `f13783b5...`.
- **Not in the brief:** `answer.search_k` (5 new passages per search, as `agentic`'s `--agent-k`).
- **README status was stale** ("no paid model call has been made"): corrected to say that paid calls were
  made on the dev split only (US$5.78 of the cap).
- **`PREREGISTRATION.md` sections 4.2 and 4.3** (expectations) were written for the single-draft engine; they
  are kept and marked as describing `engine_single`. Section 8.1 (threshold calibration) is marked as
  applying to `engine_single`; for `engine` the grid is flat by construction.
- `SYSTEM_NAMES` now ends with `engine_single`, so the default `--systems` of `bench.run` includes it; phase B
  names its systems explicitly.


---

# Phase B: the paid dev2 check (calibration data, NOT benchmark results)

**Everything below is tuning data on the dev2 split (n = 100 per dataset, 300 pooled), one run per condition, no seed. It is not a test result and is not evidence for the claim of PREREGISTRATION.md.**
Model `claude-haiku-5-5`; code `44268d0` (the commit after the phase A review: an uncited sentence fails `exists`); `locked` `f13783b57968b2b8b9313bb31d89f83aac1ea417520a9de70676aa890d52ad53`, surface `547d7f32387e2e4aff33eaa5ff39a388b52084f3680e54515ccc3d1433d878b3`, prompts `c025db9e...`. One ledger `runs/dev2/ledger.jsonl` (copy `ledger.jsonl`), cap US$4.00, margin 0.25. **Total spent US$2.3924 over 9,439 calls (smoke 0.0074, condition `off` about 0.94, `default` about 1.40, judge about 0.05); remaining under the cap US$1.61 (US$1.36 above the margin). The ledger never stopped a run; 0 error rows anywhere.**

Commands: `scripts/dev2/run_all.sh` (systems `closed_book,bm25,hybrid,hybrid_rerank,agentic,engine,engine_single` with `--time-aware-variants --variants-of hybrid,agentic`; `off` = `--thinking disabled`, `default` = `--thinking default --set draft.max_tokens=4096`; a copy of the embedded store per run; `--workers 4`), then `python -m heuresis.bench.judge <six folders> --paid --cap 4.00 --margin-usd 0.25 --ledger runs/dev2/ledger.jsonl --workers 4 --max-tokens 20` and `bench.report --iters 1000` per folder. Analysis: `scripts/dev2/analysis.py runs/dev2 > analysis.md` (all per-dataset tables, paired differences, engine details, examples) and `scripts/dev2/uncited_replay.py` (free offline replay). Raw rows (`results.jsonl`, with replay payloads) stay in `runs/` in the container; `results/dev2/{off,default}/<dataset>/` holds `results.json`, `results.md`, `manifest.json`, `judge.jsonl`. The smoke (5 `musique` questions, hybrid, agentic, engine) showed searches issued, marks continuing (t9 to t13), cost and calls recorded; the projection stayed under US$3.50 so no system was dropped. On `hoh`, all 835 (`off`) and 890 (`default`) passages the engine was shown, searches included, were in force at the question's date (checked from the rows).

## Pooled over the three datasets (n = 300): c/w/a, penalised score [95% bootstrap CI], and the judge-assisted score

### `off` (thinking disabled)
| scope | system | n | c/w/a | penalised [95% CI] | c/w/a (judge) | penalised (judge) | $/q | $/correct | calls | searches | median ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pooled | closed_book | 300 | 63/187/50 | -0.413 [-0.507, -0.323] | 64/186/50 | -0.407 | 0.00006 | 0.00028 | 1.00 | 0.00 | 982 |
| pooled | bm25 | 300 | 99/93/108 | +0.020 [-0.070, +0.113] | 114/78/108 | +0.120 | 0.00026 | 0.00078 | 1.00 | 1.00 | 898 |
| pooled | hybrid | 300 | 108/84/108 | +0.080 [-0.017, +0.170] | 121/71/108 | +0.167 | 0.00026 | 0.00072 | 1.00 | 1.00 | 1384 |
| pooled | hybrid_rerank | 300 | 103/81/116 | +0.073 [-0.013, +0.160] | 113/71/116 | +0.140 | 0.00027 | 0.00078 | 1.00 | 1.00 | 7913 |
| pooled | agentic | 300 | 122/128/50 | -0.020 [-0.127, +0.083] | 140/110/50 | +0.100 | 0.00041 | 0.00101 | 2.53 | 1.53 | 3302 |
| pooled | engine | 300 | 143/73/84 | +0.233 [+0.143, +0.327] | 171/45/84 | +0.420 | 0.00066 | 0.00138 | 1.67 | 1.67 | 2782 |
| pooled | engine_single | 300 | 102/41/157 | +0.203 [+0.127, +0.277] | 120/23/157 | +0.323 | 0.00033 | 0.00097 | 1.00 | 1.00 | 1344 |
| pooled | hybrid+asof | 300 | 144/49/107 | +0.317 [+0.240, +0.403] | 159/34/107 | +0.417 | 0.00026 | 0.00054 | 1.00 | 1.00 | 1399 |
| pooled | agentic+asof | 300 | 154/81/65 | +0.243 [+0.143, +0.340] | 171/64/65 | +0.357 | 0.00040 | 0.00078 | 2.51 | 1.51 | 2841 |
| pooled | engine - hybrid | +0.153 [+0.040, +0.277] | +0.253 [+0.137, +0.367] |
| pooled | engine - agentic | +0.253 [+0.127, +0.377] | +0.320 [+0.193, +0.447] |
| pooled | engine - hybrid+asof | -0.083 [-0.183, +0.010] | +0.003 [-0.090, +0.093] |
| pooled | engine - agentic+asof | -0.010 [-0.113, +0.090] | +0.063 [-0.040, +0.170] |
| pooled | engine - engine_single | +0.030 [-0.053, +0.110] | +0.097 [+0.013, +0.177] |

### `default` (default thinking, 4096 cap)
| scope | system | n | c/w/a | penalised [95% CI] | c/w/a (judge) | penalised (judge) | $/q | $/correct | calls | searches | median ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pooled | closed_book | 300 | 75/80/145 | -0.017 [-0.100, +0.067] | 81/74/145 | +0.023 | 0.00023 | 0.00093 | 1.00 | 0.00 | 2290 |
| pooled | bm25 | 300 | 110/77/113 | +0.110 [+0.023, +0.203] | 124/63/113 | +0.203 | 0.00035 | 0.00096 | 1.00 | 1.00 | 1425 |
| pooled | hybrid | 300 | 111/70/119 | +0.137 [+0.053, +0.223] | 125/56/119 | +0.230 | 0.00035 | 0.00096 | 1.00 | 1.00 | 2087 |
| pooled | hybrid_rerank | 300 | 105/65/130 | +0.133 [+0.047, +0.213] | 118/52/130 | +0.220 | 0.00036 | 0.00104 | 1.00 | 1.00 | 4963 |
| pooled | agentic | 300 | 158/86/56 | +0.240 [+0.143, +0.330] | 181/63/56 | +0.393 | 0.00080 | 0.00151 | 2.98 | 1.98 | 4958 |
| pooled | engine | 300 | 166/92/42 | +0.247 [+0.150, +0.347] | 199/59/42 | +0.467 | 0.00121 | 0.00218 | 2.04 | 2.04 | 4569 |
| pooled | engine_single | 300 | 110/33/157 | +0.257 [+0.183, +0.330] | 126/17/157 | +0.363 | 0.00043 | 0.00116 | 1.00 | 1.00 | 1929 |
| pooled | hybrid+asof | 300 | 149/32/119 | +0.390 [+0.310, +0.460] | 164/17/119 | +0.490 | 0.00035 | 0.00071 | 1.00 | 1.00 | 2018 |
| pooled | agentic+asof | 300 | 201/41/58 | +0.533 [+0.450, +0.613] | 219/23/58 | +0.653 | 0.00079 | 0.00118 | 2.93 | 1.93 | 4293 |
| pooled | engine - hybrid | +0.110 [-0.013, +0.230] | +0.237 [+0.130, +0.357] |
| pooled | engine - agentic | +0.007 [-0.123, +0.137] | +0.073 [-0.047, +0.190] |
| pooled | engine - hybrid+asof | -0.143 [-0.240, -0.047] | -0.023 [-0.113, +0.073] |
| pooled | engine - agentic+asof | -0.287 [-0.387, -0.190] | -0.187 [-0.283, -0.090] |
| pooled | engine - engine_single | -0.010 [-0.100, +0.077] | +0.103 [+0.013, +0.193] |

Reading, pooled (all dev2, calibration): with thinking disabled the new `engine` scores +0.233 [+0.143, +0.327] against `hybrid` +0.080, `agentic` -0.020, and the earlier design `engine_single` +0.203; with default thinking `engine` +0.247, `agentic` +0.240, `agentic+asof` +0.533, `hybrid+asof` +0.390. **The date-aware baselines are at or above the engine in both conditions** (`engine - hybrid+asof` -0.083 [-0.183, +0.010] off, -0.143 [-0.240, -0.047] default; `engine - agentic+asof` -0.010 [-0.113, +0.090] off, -0.287 [-0.387, -0.190] default). The engine beats the non-date-aware baselines on `hoh` by the date filter (+0.62 against -0.19 `hybrid`); `engine - hybrid+asof` on `hoh` is +0.03 [-0.09, +0.15] off. On `musique` the engine is ahead of `hybrid` (+0.22 [+0.08, +0.37] off) and of `engine_single` (+0.20 [+0.07, +0.32] off; +0.37 [+0.23, +0.52] default); with default thinking `agentic` is ahead of it on `musique` (-0.15 [-0.28, -0.02]). **On `multihoprag` the engine is the worst of the retrieval systems in both conditions** (-0.100, 46 and 52 wrong of 100; `hybrid` +0.43 / +0.46). Full per-dataset tables, paired differences with intervals (primary and judge-assisted) for `engine` minus `hybrid`, `agentic`, `hybrid+asof`, `agentic+asof`, `engine_single`, cost per question and per correct answer, mean calls and searches and median latency for every system are in `analysis.md` and each folder's `results.md`.

## The engine's behaviour (all in `analysis.md`, "Engine details")

| | `off` pooled | `default` pooled |
|---|---|---|
| answered in one call (no search) | 57% (musique 13%, multihoprag 65%, hoh 94%) | 59% (22%, 61%, 94%) |
| mean model searches per question | 0.67 | 1.04 |
| mean model calls / cost per question / median latency | 1.67 / US$0.00066 / 2.8 s | 2.04 / US$0.00121 / 4.6 s |
| abstentions (all / answerable) | 96 / 84 (no_source 29, unsupported 57, not_valid_at_date 6, outside_coverage 4) | 54 / 42 (no_source 41, unsupported 11, outside_coverage 1, needs_input 1) |
| sentences dropped by `exists` (**all 118 / 104 are sentences with no mark; 0 are marks that do not exist**) / `valid_at_date` / `numbers_traced`, of 454 / 511 claims | 118 / 0 / 32 | 104 / 0 / 26 |
| risk-coverage on the answered ones, ranked by the grade: AURC; accuracy at 50% / 80% of the answered | 0.223; 0.84 / 0.69 (all answered: 0.64) | 0.242; 0.80 / 0.64 (all answered: 0.63) |
| replies cut at `max_tokens` (zero-truncation check, all systems, generator calls) | 0 | 0 |

(The grade ranks answers usefully on `musique` and `hoh` (accuracy at 50% of answered 0.80 / 0.87 off, 0.82 / 0.90 default, against 0.72 / 0.83 and 0.69 / 0.80 overall) and weakly on `multihoprag`: 0.40 off and 0.22 default at 50%, against 0.34 and 0.37 overall.) The judge: 50 verdicts were unreadable (prose reply cut at 20 tokens) and counted as not flipped, as before.

## Finding that follows from the phase A review rule (free replay, `uncited_replay.md`)

**The "an uncited sentence is dropped" rule is what makes the engine lose on `multihoprag`.** 38 of the 46 wrong engine answers there (`off`; 46 of 52 `default`) are `partial`: a sentence was dropped, and 100% of the sentences dropped by `exists` are sentences with no marks (typically the one-line conclusion, "Yes, they agree", that follows the cited summaries). Replaying the stored drafts offline (no model call; the "as built" row reproduces the stored results exactly) with uncited sentences kept and the other checks unchanged gives:

| condition | scope | as built (c/w/a: penalised) | uncited kept |
|---|---|---|---|
| off | multihoprag | 36/46/18: -0.100 | 64/23/13: +0.410 |
| off | pooled | 143/73/84: +0.233 | 171/52/77: +0.397 |
| default | multihoprag | 42/52/6: -0.100 | 76/22/2: +0.540 |
| default | pooled | 166/92/42: +0.247 | 205/57/38: +0.493 |

(`musique` and `hoh` change by at most 0.08.) This is an offline replay of the same drafts, calibration data, not a run; the uncited sentence would reach the user without a source. It is reported for the owner's decision and nothing was changed.
Other observation from the examples: the `numbers_traced` check also drops correct sentences whose years or counts are in no cited passage (for example `musique:2hop__223655_463572`: the sentence that names MGM Records is dropped because "1953" and "1993" are not in the cited passage, and a hedging sentence is what remains).

## Examples (dev2 only, engine, `off`): `analysis.md` lists five wrong answers and five abstentions on answerable questions with gold, draft replies and the engine's note.
