# Pre-registration (DRAFT)

> **Draft. Not yet registered: thresholds are not calibrated and no hash is frozen. Nothing on the test split has been run.**

Date of this draft: 2026-11-11. Every number below is copied from a file in this repository (named next to it), computed by running the repository's own function (stated), or marked **modelled**, **proposed** or **placeholder**. Where a value will only exist after calibration or freezing, it is written `[ ... ]`.

This document will be frozen by a git tag (`prereg-v1`) after the calibration on dev (section 8) and before any run on the test split. After the tag, every change goes into the deviations log (section 10) with its reason and the date.

## 1. The claim

> On corpora too large for one context window, a cost-ordered, time-aware, verified-and-abstaining retrieval algorithm is cheaper per correct answer and more reliable than standard RAG and agentic search.

The algorithm is the one implemented in `heuresis` (`docs/architecture.md`). "Standard RAG" means the single-shot baselines `bm25`, `vector`, `hybrid`, `hybrid_rerank`; "agentic search" means the `agentic` baseline. "More reliable" means a higher penalised score (+1 correct, 0 abstained, -1 wrong), which rewards abstaining over answering wrongly. "Cheaper per correct answer" means lower total API cost divided by the number of correct outcomes, at the dated price table in `src/heuresis/pricing.py`.

The claim is limited to corpora that do not fit in a context window (section 3.3), to the three datasets below, to one generator model, and to the comparison as built: the engine is given the question's as-of date, the baselines are not (section 3.2).

### What would refute it

These decision rules are **proposed**; the owner confirms them before the tag.

- **Supported** only if, on at least two of the three datasets, the engine's penalised score is higher than that of both `hybrid` and `agentic` with a Holm-adjusted p below 0.05 (section 4), and its cost per correct answer is lower than `agentic`'s with a bootstrap 95% interval that excludes zero.
- **Refuted** if any of these holds:
  - on `hoh`, the engine does not beat `hybrid` on the penalised score at Holm-adjusted p below 0.05 (the one dataset where the engine has a structural advantage, the date filter);
  - the engine's cost per correct answer is not lower than `agentic`'s on any dataset (interval includes zero or lies above it);
  - the engine's penalised score is lower than `hybrid`'s, with Holm-adjusted p below 0.05, on two or more datasets.
- **Mixed** in every other case. Results are then reported dataset by dataset, and the claim is not stated in its general form.

A result on `musique` of "no difference" or "worse" than `hybrid` does not by itself refute the claim, but it counts against its generality and is reported as such (section 4.2).

## 2. Datasets

Built by `heuresis.bench.datasets` from pinned revisions; see `docs/datasets.md` and `data/corpora/<name>/MANIFEST.json`. All three are public. The repository does not redistribute them.

| | `hoh` (temporal) | `multihoprag` (multi-hop, with unanswerable questions) | `musique` (multi-hop) |
|---|---|---|---|
| Source repo | `russwest404/HoH-QAs` | `yixuantt/MultiHopRAG` | `osunlp/HippoRAG_2` |
| Pinned revision | `8f12fd356240fa9386d20346fe1e1f9b928d1b64` | `71ac0d0bd1f951d2d6b70311f7d2ae404e1ffa82` | `5ec05b38deecc3318bb432c69865959c56058990` |
| Units / versions | 111,972 units, 230,746 versions | 5,048 passages, 49 sources | 11,656 passages |
| Corpus size (`corpus_tokens`, chars/4) | 7,296,081 | 1,574,432 | 1,409,951 |
| Question pool | 110,721, all answerable | 2,556, of which 301 unanswerable | 1,000, all answerable |
| Dev / test / sealed | 100 / 500 / 300 | 100 / 500 / 300 | 100 / 500 / 300 |
| Unanswerable in dev / test / sealed | 0 / 0 / 0 | 12 / 59 / 35 | 0 / 0 / 0 |
| Split stratum | `kind` (current / outdated) | answerable | answerable |
| Split seed | 20261111 | 20261111 | 20261111 |
| `question_ids_sha256` dev | `877ed197a98ad4551a3f2effac63ad191883dc3af811876a63187ff04b2f8d37` | `1e0ecec058beaeb9c4e2073b5157ee3851035e3ca496255e31c7d7895d0d0fda` | `8e995fe3dcf8f98cf04a9b59b13217eca2fbd66ec13d7162cc5d662f9ee622dc` |
| `question_ids_sha256` test | `67ba51b77a7e344943d4a2c7612eda61e41dd5b0d5d6243e465e1d9b7191790e` | `ffc6230a6b7158e5f09ce29448edf86122537c78d64de9fb9bb2b0518f9ea028` | `73ae2d3b9a5ce7f1f4ad5367701782a6eecc7a7e3518d43a3dd665fd45a202c3` |
| `question_ids_sha256` sealed | `b49defb6cc9dc2291d7c667e6d7f7c2ae8f6284884fab4d8210c0e6b1b69d34b` | `990c92563d7b19d74376a2241e976f1c6a74f89179ed37d35d5f134cde7bfc07` | `2cc5aa3fe534ed1de7d0a7fb95cc9731dec0722f4e18833c5f181b0842e9567e` |
| `questions.jsonl` sha256 | `22746e97a4002a83334935854de73f1a29cf27b603f7383bbe9df095d0266a44` | `cf7f031da1623ca807170526a22e0a6ba61d25edd98c58f3a714ee9239dc8e8b` | `ecab41c2f8ccf34e36d5946c689559cac221967bb602a6bf3d44cae3e54a6e57` |
| `MANIFEST.json` sha256 (at drafting) | `1f1e84d9f6eae4dfb870f8b3e31c48bee8c5d1628b5e217392ae5d6f0a02617a` | `2576f85c65490020ae57db5991395d6a1f660b97fba57462212892e26915b251` | `2480671872d12dccc638ca5d5856b0f8f4b0061d42ce67e5579bf5a21e3827ee` |
| Cluster used for resampling and sign flips | Wikipedia page | first evidence article | first gold unit |

(`corpus_tokens` and the counts are from the manifests; the cluster definitions are in `src/heuresis/bench/datasets.py`; the `MANIFEST.json` hashes were computed on 2026-11-11 and are re-computed at freezing.)

**Splits.** Question ids are ordered by `sha256("<seed>:<id>")` and cut into dev, test and sealed per stratum (`docs/datasets.md`). `load` refuses to continue if the split hashes differ from the manifest.

- **Dev, n = 100 per dataset.** Used for all tuning, and only for that (section 8).
- **Test, n = 500 per dataset.** Each system answers each question once (section 6). Nothing on the test split has been run.
- **Sealed, n = 300 per dataset.** Never used by this project. It is kept for outside replication. Only its id hash appears here.

### Known weaknesses of each dataset

Copied from `docs/datasets.md`.

- **`hoh`.**
  - Evidence is a short snippet (about 21 words), not a full page.
  - Granularity is monthly, and facts changed over six months only (snapshots 2024-06-01 to 2024-12-01).
  - Question texts were LLM-generated from diffs.
  - A snapshot date is when the text was first observed; the true change happened up to one month earlier, so `valid_from` is late by up to a month. The "current" answer is current for the data's horizon (2024-12-01), not today.
  - It has no repeal or retroactive correction, so it exercises `create` and `replace` and the as-of filter, not `repeal`, `restore`, `correct` or the transaction-time axis.
  - Data quality beyond the checks listed there is not verified.
  - Wikipedia-derived text is CC BY-SA 4.0; attribution applies and ShareAlike applies if passages are shared publicly. They are not redistributed.
- **`multihoprag`.**
  - Questions carry no date (`as_of = None`), so the date filter is not exercised even though articles have publication dates.
  - 110 of 6,084 gold matches were made by a token-overlap fallback rather than an exact substring match (5,974 exact).
  - Copyright in the article texts stays with the outlets; the dataset card says nothing about it, and it was not verified.
  - The 301 null queries become `answerable = False`; the original label is "Insufficient information.".
- **`musique`.**
  - The file actually downloaded (the HippoRAG 2 redistribution) states no licence; only the upstream MuSiQue README states CC BY 4.0. The subset was judged a verbatim derivative on matching ids and texts. This is not verified further.
  - The corpus has no dates: each passage gets a placeholder `create` event on 1970-01-01 and questions have `as_of = None`.
  - MuSiQue's README cautions about its single-hop seed questions; this project only evaluates.
  - The 1,000 questions are the retrieval subset used by HippoRAG and IRCoT, not the full official dev set.

## 3. Systems

All systems share one generator (`claude-haiku-5-5`), one output cap (`draft.max_tokens` = 600), one SQLite corpus per dataset (built with the `jsonl` domain) and one local embedder. The generator is called with no temperature or seed parameter (`src/heuresis/llm.py` sends only model, max tokens, system and messages), so the API's default sampling applies and a repeat run would differ.

### 3.1 The list

| System | What it does | Passages shown |
|---|---|---|
| `closed_book` | No retrieval. | 0 |
| `bm25` | SQLite FTS5 `bm25()` over all versions in force today. | k |
| `vector` | Dense cosine search with the local embedder. | k |
| `hybrid` | BM25 and dense, 50 candidates each, fused by reciprocal rank fusion (`rrf_k` = 60). No reranker. | k |
| `hybrid_rerank` | `hybrid`, then the local cross-encoder over 50 candidates. | k |
| `agentic` | A search-tool loop. The model replies `SEARCH: <query>`; each search runs the `hybrid` retriever and returns 5 new passages. Hard cap of 4 searches (so at most 5 model calls). | up to 20 |
| `engine` | The `heuresis` algorithm (`docs/architecture.md`) with the packaged configuration plus `draft.max_sentences = 2`. | up to 8 |
| `oracle` | The gold passages, as of the question date. **A ceiling, not a competitor.** Excluded from every comparison. | gold |

`k` is 8 until calibration (section 8.2). All single-shot systems cut the passage list to `draft.max_context_chars` (24,000) by dropping the tail.

Local models (the same for every system that uses them), as configured in `src/heuresis/models_local.py`:

| Role | Model id | Used by |
|---|---|---|
| Embedder | `onnx:intfloat/multilingual-e5-small` | `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine` |
| Reranker | `onnx:cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | `hybrid_rerank` (the engine's rerank stage is off by default) |
| Entailer | `onnx:MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli` | `engine` (verification) |

### 3.2 Time handling: the comparison as built

The engine is called with the question's own as-of date (`as_of = None` on `musique` and `multihoprag`). **The baselines search as of today and are not told the question's date.** This is deliberate: it is the comparison between a system that handles validity and systems that do not. Each baseline passage is shown with its validity span, but the baseline does not receive the as-of date, and its retrieval does not filter on it.

For `hoh`, the date is carried by the question's `as_of` field, not by its text: the router found a date in the text of 1 of the 100 dev questions (`docs/pilot-dev.md`, side findings). The `hoh` comparison therefore measures the value of date handling, not retrieval quality in general.

To show how much of any gap is the date filter alone, a time-aware copy of each of `bm25`, `vector`, `hybrid`, `hybrid_rerank` and `agentic` (name suffix `+asof`) is run too. These filter by the question date and see an `As-of date:` line. They are **exploratory** and are not part of the confirmatory family (`--time-aware-variants`, `src/heuresis/bench/systems.py`).

### 3.3 `long_context` is not run

`long_context` puts the whole corpus in the prompt. It is not run because the corpora are far above its 90,000-token limit (manifest `corpus_tokens`: `musique` 1,409,951, `multihoprag` 1,574,432, `hoh` 7,296,081; `docs/pilot-dev.md` item 3). A reduced-corpus tier was examined on `multihoprag` dev and does not work: a corpus of at most about 80,000 tokens held all gold evidence for 0 of 88 answerable dev questions (`docs/pilot-dev.md` item 4). The claim is therefore stated only for corpora that do not fit in a context window, and nothing here says how the engine compares with a model that can read the whole corpus.

### 3.4 Prompts

These are the exact strings in `src/heuresis/bench/systems.py`. Their combined hash, `prompts_hash()`, is `c82a56eba64a36982a8106c6a40f4b5c02c459de4cd981cd724cf72435dca6de` at the time of drafting (also the value recorded in `docs/pilot-dev.md`); the frozen value is `[prompts_hash at freeze]`.

Shared answer-format instruction (`ANSWER_FORMAT`):

```
Answer in at most two short sentences; if the information is not sufficient, reply exactly ABSTAIN; end with a line `CONFIDENCE: <0-100>`.
```

System prompts of the baselines:

```
closed_book:   Answer the question from your own knowledge. <ANSWER_FORMAT>
bm25, vector, hybrid, hybrid_rerank, oracle:
               Answer ONLY from the passages provided; do not use outside knowledge. <ANSWER_FORMAT>
agentic:       You answer questions about a document collection with a search tool. To search, reply with exactly one line `SEARCH: <query>` and nothing else. You may search at most 4 times; after that you must answer. When you answer, use ONLY the passages found; do not use outside knowledge. <ANSWER_FORMAT>
```

(`long_context` has its own prompt, also in the hash, and is not run.) User prompts: `Question: <text>` for `closed_book`; for the single-shot systems a `Passages:` header, one line per passage `[t<i>] (<title>; valid <from>..<to>) <text>`, then `Question: <text>`. The `agentic` user prompt holds the question, `Searches used: <m> of 4.`, each earlier search with its new passages, and one of:

```
Reply with exactly one line `SEARCH: <query>` to search again, or answer now.
No searches remain. Answer now.
```

The engine's system prompt is `DRAFT_SYSTEM` in `src/heuresis/surface/prompts.py`. It is part of the surface hash, not of `prompts_hash()`:

```
Answer ONLY from the numbered passages. Never use outside knowledge.
Format, one item per line:
- Write short sentences. End EVERY sentence with the marks of the passages that support it, like [t1] or [t1][t2].
- Never do arithmetic or date math yourself. Request it before the answer with a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write {k1} where the result goes and add the mark [k1] to that sentence.
- Use the as-of date you are given; passages show their validity as (title; valid from..to).
- If the passages do not answer the question, write only `ABSTAIN <type>: <reason>` with type one of: no_source, not_valid_at_date, conflict, false_premise, outside_coverage, unsupported, needs_input, tool_failed, out_of_scope, budget.
```

Its user prompt starts `As-of date: <date or "today">`, lists the passages as above and the question, and ends with `Answer in at most 2 short sentences.` The same two-sentence length instruction therefore reaches every system, in different words.

## 4. Hypotheses

### 4.1 Confirmatory family: 18 comparisons

The engine against each of six baselines (`closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`) on each of three datasets.

- **Measure.** Penalised score per question: +1 correct, 0 abstained, -1 wrong. On unanswerable questions, abstaining is correct and answering is wrong (`scoring.outcome`).
- **Test.** Two-sided paired sign-flip permutation test on the mean per-question difference (`paired_permutation_test` in `src/heuresis/bench/stats.py`). Signs are flipped per cluster (section 2). With more than 13 non-zero clusters the test uses 10,000 random sign assignments (seed 0), so the smallest possible p-value is 1/10,001; with 13 or fewer it is exact.
- **Correction.** Holm across all 18 comparisons at alpha = 0.05 (`report.family`). The pre-registered result of each comparison is its Holm-adjusted p and the difference with a paired bootstrap 95% interval (10,000 resamples, seed 0, clusters resampled).
- **Secondary.** Exact McNemar on correctness, with its own Holm adjustment within a dataset. It is reported and is not used to decide.

The `+asof` variants and the oracle are outside the family.

### 4.2 Directional expectations, stated in advance

- **`hoh`: the engine is expected to beat every baseline.** The reason is the date filter. On dev, a plain retrieval that searches as of today returned the version in force at the question date for 42 to 49 of 100 questions, against 92 to 100 with the filter (`docs/pilot-dev.md` item 2; retrieval only, partly by construction, since the filter removes out-of-force versions before ranking).
- **`multihoprag`: the engine is expected to beat the baselines on the penalised score through abstention on unanswerable questions** (59 of the 500 test questions; manifest). The baselines are also told to reply `ABSTAIN`, so the expectation is that verification makes the engine abstain more reliably, not that baselines cannot abstain. The most unanswerable questions can add is 59 / 500 = 0.118 to a system's mean score.
- **`musique` (all answerable, no dates): no superiority over `hybrid` is expected, and the engine may score lower.** Verification can reject correct answers. The one crude measurement available points that way: with the packaged support threshold of 0.5, none of the 100 matched (gold passage, statement) pairs on `musique` dev scored at or above it (`docs/pilot-dev.md` item 5; a proxy, not a measure of verification quality on drafted answers). A result of "no difference or worse" on `musique` counts against the generality of the claim and will be reported as such.

### 4.3 Cost hypothesis

- The engine's cost per correct answer is lower than `agentic`'s on each dataset: the bootstrap 95% interval of the difference (engine minus `agentic`) excludes zero and lies below it.
- Against `hybrid`, the engine is expected to cost slightly more per question, because its prompts are longer. In the pilot's dry run the engine's mean prompt was 1,744 / 3,785 / 769 tokens (`musique` / `multihoprag` / `hoh`, characters / 3.5, assumed) and `hybrid_rerank`'s was 1,442 / 3,479 / 484 (`docs/pilot-dev.md` item 3, dev, offline generator). The question for `hybrid` is therefore whether more correct answers per dollar offset a higher price per question; no direction is predicted, and the result is reported with its interval.
- Reported for both comparisons: cost per correct answer for each system with a bootstrap interval, the difference (engine minus baseline) with a paired bootstrap interval that resamples questions and keeps each pair together, and an accuracy-against-cost table marking which systems no other system dominates (Tables 3, 5b and 7 of `report.py`). The Pareto table is descriptive and has no test.
- Cost counts API spend only. Local compute (embedder, reranker, entailer) is not priced.

### 4.4 Minimum effect of interest

`min_detectable_diff` in `src/heuresis/bench/stats.py` gives the smallest difference in two paired proportions detectable with n pairs, a share of discordant pairs, alpha and power (normal approximation to McNemar). Run with n = 500, alpha = 0.05, power = 0.8:

| Discordance | Smallest detectable difference in accuracy |
|---|---|
| 0.15 | 0.0484 |
| 0.30 | 0.0685 |

The same function at the Holm-conservative alpha = 0.05 / 18 gives 0.0662 and 0.0936 (a bound for the most significant of the 18 comparisons only; Holm's later steps use larger alphas). These figures are for differences in *correctness*, the McNemar scale. No power calculation has been done for the permutation test on the penalised score. A wrong answer replaced by an abstention changes that score by 1 and a wrong answer replaced by a correct one by 2, so the same change in accuracy moves it by more than it moves accuracy. A difference smaller than about 0.05 in accuracy will not be resolved and will not be claimed.

## 5. Measures and grading

Primary: penalised score (section 4.1). Secondary, all in `src/heuresis/bench/report.py`:

- accuracy (correct / n), coverage (answered / n), selective accuracy (correct among answered);
- risk-coverage curve and AURC over answered questions. **The two kinds of confidence differ:** the engine's confidence is its verification grade, `min(lowest claim support, lowest cited certainty, lowest cited coverage)`; a baseline's is the model's own stated `CONFIDENCE: <0-100>`. AURC across systems compares different kinds of signal and is not a like-for-like calibration comparison;
- cost per question and per correct answer at the dated price table `anthropic-2026-11` (`claude-haiku-5-5`: $0.10 per million input and $0.50 per million output tokens up to 100,000 prompt tokens, $0.50 and $2.50 above; `src/heuresis/pricing.py`, read 2026-11-11);
- tokens in and out, model calls, searches, median and p95 latency, mean answer length in characters;
- citation precision and recall against gold units: **engine only**; baselines do not cite;
- retrieval recall of gold units among the passages shown to the generator: all systems that retrieve.

**Grading** is deterministic and has no language-model judge. An answerable question is answered correctly when any gold answer, normalised, occurs in the normalised answer on token boundaries. Normalisation is SQuAD-style (lower case, punctuation and articles removed, whitespace collapsed) plus accent folding; citation marks such as `[t1]` are removed first (`run.is_correct`, `locked/scoring.py`). Token F1 is stored but is not a confirmatory measure. Outcomes are `scoring.outcome`: on an answerable question, answered and correct is `correct`, abstained is `abstained`, answered and incorrect is `wrong`; on an unanswerable one, abstained is `correct` and answered is `wrong`. Statuses `answered` and `partial` both count as answering. A baseline abstains when its reply starts with `ABSTAIN` or is empty.

## 6. Analysis plan

- **One run.** Each system runs on each test question once. There are no repeats in the confirmatory analysis. An optional repeat on a 100-question subset, to estimate run-to-run variance, is exploratory.
- **No peeking.** No result on the test split is read before the runs are complete. The runner writes rows as they finish; nobody computes a report on a partial test run except to check that it is running.
- **Stopping.** The shared ledger is a hard stop at the cap minus its margin (section 9). If the budget stops a run, only question ids completed by **all** systems in the family are analysed, and this is reported with the number of questions lost. The runner orders work question by question, so a stop cuts every system at about the same question.
- **Errors and refusals.** An API error after the client's retries (up to 5 attempts) is recorded and counted as wrong for that system, and the count of such rows per system is reported. A model refusal or an empty reply is graded like any other reply: empty counts as an abstention.
- **Bootstrap and permutation.** 10,000 resamples or sign assignments, seed 0, clusters as in section 2.
- **Commands.** One run folder per dataset, one shared ledger:

```
python -m heuresis.bench.run --dataset <name> --split test --paid --cap 30 \
    --systems closed_book,bm25,vector,hybrid,hybrid_rerank,agentic,engine,oracle \
    --time-aware-variants --ledger runs/ledger.jsonl --out runs/test/<name>
python -m heuresis.bench.report runs/test/hoh runs/test/multihoprag runs/test/musique --family-out runs/test/family.md
```

- **Reporting.** All 18 comparisons are reported in the order of the family table, whatever their direction. Negative and null results are published. Exploratory results are labelled as such and are not used to support the claim.

## 7. What is frozen at registration

| Item | How it is obtained | Value at drafting | Frozen value |
|---|---|---|---|
| `locked_hash()` | `heuresis hash`, or `heuresis.locked.guard.locked_hash()` | `3c23fecd42520db9a36c3208d285d6d96465f42e1c2ef8e31d2d2b2d79de1b71` | `[ ... ]` |
| Surface config hash | `bench.run.surface_hash` (config JSON + `DRAFT_SYSTEM`), recorded in each run's `manifest.json` | `9de82a74a90b3cbbc01b0e4ea56e77affc39cda4eae06146a62bf537a9fb505a` (the pilot recorded `3e310d25...`; the default configuration has changed since) | `[ ... ]` |
| Full effective engine config | `manifest.json` key `engine_config` | see below | `[ ... ]` |
| `prompts_hash()` | `heuresis.bench.systems.prompts_hash()` | `c82a56eba64a36982a8106c6a40f4b5c02c459de4cd981cd724cf72435dca6de` | `[ ... ]` |
| Dataset manifest hashes | sha256 of each `MANIFEST.json` | section 2 | `[ ... ]` |
| Model ids | generator, embedder, reranker, entailer | `claude-haiku-5-5`; the three `onnx:` ids of section 3.1 | `[ ... ]`, plus `[ file hash or Hugging Face revision of each local model ]` |
| Baseline settings | passage count k per baseline (section 8.2) | 8 (agentic: 5 per search, 4 searches) | `[ ... ]` |
| Price table | `PRICE_TABLE` in `bench/run.py` | `anthropic-2026-11` | `[ ... ]` |
| Commit hash | repository `HEAD` at the tag | `[ ... ]` | `[ ... ]` |

Effective engine config at drafting (packaged `surface/default.json` with `draft.max_sentences` set to 2 by `BenchContext.engine_config()`):

```json
{"decide": {"conflict_margin": 0.1, "min_supported_fraction": 1.0, "partial_fraction": 0.5},
 "draft": {"max_context_chars": 24000, "max_sentences": 2, "max_tokens": 600, "model": "claude-haiku-5-5"},
 "retrieve": {"dense": true, "early_stop": true, "early_stop_margin": 0.35, "expand": false, "expand_hops": 1,
              "k_dense": 50, "k_lexical": 50, "rerank": false, "rerank_in": 50, "rerank_out": 8, "rewrite": false,
              "rrf_k": 60, "second_round": false},
 "router": {"ask_threshold": 0.6, "default_intent": "lookup"},
 "verify": {"atomic_claims": false, "partial_threshold": 0.3, "support_threshold": 0.5}}
```

The two `verify` thresholds are the values to be replaced by calibration (section 8.1). The engine runs with no router classifier, so the ask-back gate cannot fire in the benchmark.

## 8. Calibration on dev

Placeholder: to be filled after the run. Nothing in this section has been run.

**Procedure.** One paid run of all systems of section 3.1 on the 100 dev questions of each dataset (300 questions), under the shared ledger. Nothing is read from the test or sealed splits.

### 8.1 Engine

`verify.support_threshold` and `verify.partial_threshold` are set to maximise the dev penalised score over a fixed grid: each from 0.1 to 0.9 in steps of 0.1, with partial not above support (45 pairs), pooled over the three datasets, one setting for all. Ties are broken toward the higher support threshold, then the higher partial threshold (the more conservative setting; **proposed**). The drafts do not depend on the thresholds, so the intended way is to store each draft once and replay verification and the decision locally for each pair; whether the code supports that replay at the time of freezing is an open item (section 12).

| Quantity | Result |
|---|---|
| Chosen `support_threshold` | `[ ... ]` |
| Chosen `partial_threshold` | `[ ... ]` |
| Dev penalised score at the chosen pair, pooled (n = 300) | `[ ... ]` |
| Dev penalised score at the packaged pair (0.5, 0.3) | `[ ... ]` |

### 8.2 Baselines

Each baseline may use the same budget to choose its passage count k from {4, 8, 12}: the single-shot systems their k, `agentic` its per-search count. The choice maximises the dev penalised score pooled over the three datasets; ties go to the smaller k (**proposed**). `closed_book` has no k. The engine's own passage count (`retrieve.rerank_out` = 8) is not tuned, so the baselines have one free setting that the engine does not.

| Baseline | Chosen k | Dev penalised score at k = 4 / 8 / 12 |
|---|---|---|
| `bm25` | `[ ... ]` | `[ ... ]` |
| `vector` | `[ ... ]` | `[ ... ]` |
| `hybrid` | `[ ... ]` | `[ ... ]` |
| `hybrid_rerank` | `[ ... ]` | `[ ... ]` |
| `agentic` | `[ ... ]` | `[ ... ]` |

**Nothing else is tuned.** Prompts, the router, the early-stop margin, the candidate counts, the reranker choice, the 4-search cap and the generator are fixed by sections 3 and 7.

## 9. Budget

The owner-approved cap is **US$30**, enforced by the ledger (`src/heuresis/bench/ledger.py`), one file shared by every run of this project, dev and test. The runner's default safety margin is $1.00 (`--margin-usd`), so spending stops at $29.00. A paid run needs `--paid` and `--cap`; it is never the default.

**Modelled cost** (not measured; `docs/pilot-dev.md` item 6). Assumptions stated there: tokens = characters / 3.5; 120 output tokens per call; $0.1 and $0.5 per million input and output tokens; 500 test questions per dataset, one run; the dev prompt-size distribution standing in for the test split. Totals for one run on 3 x 500 questions:

| System | Modelled, 3 datasets |
|---|---|
| `closed_book` | $0.11 |
| `bm25` | $0.36 |
| `vector` | $0.35 |
| `hybrid_rerank` | $0.36 |
| `agentic`, 1 / 2 / 4 searches | $0.41 / $0.86 / $2.26 |
| `engine` | $0.40 |
| `oracle` | $0.18 |
| **Total, all of the above** | **$2.16 / $2.61 / $4.01** (agentic at 1 / 2 / 4 searches) |

The pilot model has no row for `hybrid`, which was added later; it is not in these totals. The `+asof` variants, the calibration runs and the optional repeat are not modelled either. The test run is therefore expected to cost a few dollars, and the calibration (100 instead of 500 questions per dataset, plus passes for k in {4, 8, 12}) a fraction of that, but these are modelled figures on assumptions that the pilot could not check (no real model reply was ever seen, so output lengths and the number of searches `agentic` actually makes are unknown). The cap leaves room for that. If measured cost on dev per task is several times the model, the run is paused and this section is revised before the tag.

## 10. Deviations log

*(Empty. Nothing to log before the tag.)*

| Date | Change | Reason | Data seen at the time |
|---|---|---|---|

## 11. Threats to validity

- **LLM-generated questions in HoH.** Question texts were generated from diffs by a model; some may be odd, ambiguous or answerable without the date.
- **Monthly snapshot granularity.** `valid_from` is late by up to a month, and only six months of change are present.
- **The engine is given the date; the baselines are not** (section 3.2). A `hoh` win says the date filter works end to end; it does not say the rest of the algorithm is better. The `+asof` copies are the control, and they are exploratory.
- **Cover-exact-match favours longer answers.** An answer that contains the gold string is correct however much else it says. This is mitigated by the shared two-sentence instruction, and mean answer length is reported per system. It is not eliminated: the engine's draft format and the baselines' differ.
- **Different kinds of confidence** (section 5): AURC compares the engine's verification grade with a model's stated number.
- **One generator model, one run.** No claim extends to other models. Sampling is at the API default and a repeat would differ.
- **Local compute is not priced.** The engine runs an entailer on CPU for every answer; the baselines run none. Latency is measured with four worker threads in parallel, the engine's from its stage timings and the baselines' by wall clock, so latency figures are indicative only.
- **Verifier training data.** The verification model is a multilingual NLI model reported to have been trained without Portuguese data (not verified in this repository). The three English datasets here do not exercise Portuguese, so nothing in this study says how the verifier behaves on Portuguese.
- **The verifier may reject correct answers.** The dev proxy in `docs/pilot-dev.md` item 5 reports, at the packaged threshold, 0 of 100 matched pairs on `musique` and 3 of 88 on `multihoprag` scoring at or above 0.5, and 39 of 100 on `hoh`. It is built from gold answers rather than drafted ones, but it suggests the packaged threshold is strict; calibration (section 8) addresses it on dev.
- **Divergence and conflict detection is not implemented.** The engine never returns `divergent` (a comment in `src/heuresis/engine.py` says so). Nothing here tests it, and none of the three datasets contains conflicting sources by design.
- **The reranker choice was made on dev.** The cross-encoder is off in the engine because dev retrieval fell with it on two of three datasets (`docs/pilot-dev.md` side findings), and it is on in `hybrid_rerank`. Both choices were informed by the same 100 dev questions per dataset.
- **The engine's default cascade was changed after the dev pilot.** See `docs/pilot-dev.md`, section "Cascade after the pilot's changes": the packaged default `retrieve.rerank` went from true to false. The pilot's dry-run prompt sizes (item 3) and cost model (item 6) were produced with the earlier default.
- **Other changes after the pilot.** `Engine._settle_date` (a date named in a question is used as an as-of date only if the corpus holds history and the date is not earlier than its first version) and `draft.max_sentences = 2` for the benchmark postdate the pilot's text. `docs/pilot-dev.md` still lists the router date problem as "possible bug, not fixed". The behaviour was checked on 2026-11-11 on a one-unit in-memory corpus and the engine answered.
- **Unverified licences.** See section 2 and `docs/datasets.md`, "Not verified".
- **Retrieval recall is unit-level** and uses the question text as the query. It says whether a gold unit was shown to the generator, not whether the answer was in it.

## 12. Open items before registration

Gaps between this draft and the code, to be closed or logged as deviations before the tag.

1. **Error rows.** `src/heuresis/bench/report.py` (`load`) excludes rows with `status == "error"` from the analysis, and the runner retries them on restart. Section 6 says an error after retries counts as wrong. The report must be changed, or the section revised, before freezing. Also, the engine turns a failed model call into an abstention (`Engine._draft`), whereas a baseline's failure is an error row, so the two are not treated alike today.
2. **Common question ids.** Section 6 restricts the analysis to ids completed by all systems. `report.paired` pairs on the ids shared by the engine and each baseline, so after a budget stop the 18 comparisons could have different n. A restriction to the common ids must be added.
3. **Grid replay.** Section 8.1 needs stored drafts and local replay of verification. No such replay exists yet; without it the 45 pairs would need 45 engine runs.
4. **Model revisions.** The harness records model ids (`BenchContext.models()`), not file hashes or Hugging Face revisions.
5. **Two "surface hashes".** `heuresis hash` prints the hash of the default configuration alone; `bench.run.surface_hash` hashes the configuration and `DRAFT_SYSTEM`. The frozen one is the second (section 7).
6. **`docs/datasets.md`, `hoh` "Sanity" row** mentions "100 test questions". If that was a test-split check, the banner of this draft is wrong; if it is loose wording for dev questions, the row should be corrected. Its numbers are not used here.
7. **Decision rules** in section 1 and the tie-breaks in section 8 are proposals.
