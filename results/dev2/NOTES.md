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
