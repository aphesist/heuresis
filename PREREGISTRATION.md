# Pre-registration (DRAFT)

> **Draft. Not yet registered: thresholds are not calibrated and no hash is frozen. No system has been run and no answer has been graded on the test split, but two retrieval-only sanity checks did read part of it (section 2a, "Prior contact with the test split"): a contamination risk the reader should weigh.**

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
- **Test, n = 500 per dataset.** Each system answers each question once (section 6). No system has been run on it and no answer graded; two retrieval-only checks read part of it (section 2a).
- **Sealed, n = 300 per dataset.** Never used by this project. It is kept for outside replication. Only its id hash appears here.

### 2a. Prior contact with the test split

The earlier statement of this draft, that nothing on the test split had been run, was inaccurate. Two retrieval sanity checks read the test split before this draft was written. This is exactly what they did:

1. **First 20 answerable test questions, BM25 at k = 50.** For each of `musique`, `multihoprag` and `hoh`, the first 20 answerable test questions were run through BM25 at k = 50 and the share of questions whose gold units were retrieved was noted: 20 of 20 on each dataset.
2. **`hoh`, 100 test questions, gold-answer check.** For 100 `hoh` test questions it was checked whether the retrieved version of the gold unit contains the gold answer, with the date filter (86 of 100) and without it (41 of 100). This is the "Sanity" row of `docs/datasets.md`.

What did not happen: no system produced an answer on a test question, no language model was called, and nothing was graded with `bench.run`. No design decision used these numbers; every tuning decision cites the dev pilot (`docs/pilot-dev.md`). The sealed split has not been read by any script that computes or prints anything about it; only its id hash appears in section 2.

This is a contamination risk and is disclosed as one. The checks looked at gold answers and gold units of test questions, so the reader cannot take on trust that the test questions were never seen; they should weigh it. The risk is bounded by the facts that the checks were retrieval-only and that no setting was chosen from them, but that is the author's statement, not something the repository can prove. The same entry is in the deviations log (section 10).

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

All systems share one generator (`claude-haiku-5-5`) called with thinking turned off (`thinking: {"type": "disabled"}`, `bench.run --thinking disabled`, the default; see the deviations log of 2026-11-12), so that one output cap (`draft.max_tokens` = 600) bounds the visible answer, one SQLite corpus per dataset (built with the `jsonl` domain) and one local embedder. The generator's sampling is the API default for every system: the Messages API rejects the `temperature` parameter for `claude-haiku-5-5` (HTTP 400, "`temperature` is deprecated for this model."), so it cannot be set and `bench.run` does not send it (`AnthropicLLM(temperature=None)` in `src/heuresis/llm.py`). The manifest records `"temperature": null` with a note, the `thinking` setting, the model id and the output cap. No seed parameter exists in the request, so repeat runs may differ.

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

These are the exact strings in `src/heuresis/bench/systems.py`. Their combined hash, `prompts_hash()`, covers these constants and the source of the functions that build the baselines' prompts (`_span`, `_passage_line`, `passages_prompt` and the `_answer` methods of `closed_book`, the single-shot systems, `agentic`, `long_context` and `oracle`). It is `1498745bcecca370bd94caef482d685ab41c84890ab5a208320f2dcbacc2a462` at the time of drafting, as printed by `python -m heuresis.cli hash` (the value `c82a56eb...` in `docs/pilot-dev.md` was computed over the constants only and is not comparable); the frozen value is `[prompts_hash at freeze]`.

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

(`long_context` has its own prompt, also in the hash, and is not run.) User prompts: `Question: <text>` for `closed_book`; for the single-shot systems a `Passages:` header, one line per passage `[t<i>] (<title>; source: <source label>; valid <from>..<to>) <text>` (the `source:` part is left out when a passage has no source id; deviations log, 2026-11-12), then `Question: <text>`. The `agentic` user prompt holds the question, `Searches used: <m> of 4.`, each earlier search with its new passages, and one of:

```
Reply with exactly one line `SEARCH: <query>` to search again, or answer now.
No searches remain. Answer now.
```

The engine's system prompt is `DRAFT_SYSTEM` (= `DRAFT_SYSTEM_V2`) in `src/heuresis/surface/prompts.py`; the first version, `DRAFT_SYSTEM_V1`, is kept verbatim and selectable with `draft.prompt = "v1"` for an A/B. The prompt is part of the surface hash (which also covers the source of `surface/prompts.py`, so `draft_prompt` and V1 too), not of `prompts_hash()`. It was rewritten on dev evidence (deviations log, 2026-11-12):

```
Answer ONLY from the numbered passages. Never use outside knowledge.
Answer whenever the passages contain the answer, also when you must combine facts from two or more passages (for example, one passage names the person and another gives the fact about that person). A passage that is only partly relevant, or that does not repeat the question's wording, is no reason to abstain.
Format, one item per line:
- State the answer in the first sentence, then add only what is needed. Write short sentences. End EVERY sentence with the marks of ALL the passages that support it, like [t1] or [t1][t2].
- Never do arithmetic or date math yourself. Request it before the answer with a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write {k1} where the result goes and add the mark [k1] to that sentence.
- Use the as-of date you are given; passages show their validity as (title; valid from..to).
- Only if the answer is not in the passages, write only `ABSTAIN <type>: <reason>` with type one of: no_source, not_valid_at_date, conflict, false_premise, outside_coverage, unsupported, needs_input, tool_failed, out_of_scope, budget.
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

**Grading** is deterministic and has no language-model judge. (A secondary, exploratory, judge-assisted grade exists for the dev calibration only, see the deviations log of 2026-11-12; the confirmatory tests use the containment grade below.) An answerable question is answered correctly when any gold answer, normalised, occurs in the normalised answer on token boundaries. Normalisation is SQuAD-style (lower case, punctuation and articles removed, whitespace collapsed) plus accent folding; citation marks such as `[t1]` are removed first (`run.is_correct`, `locked/scoring.py`). Token F1 is stored but is not a confirmatory measure. Outcomes are `scoring.outcome`: on an answerable question, answered and correct is `correct`, abstained is `abstained`, answered and incorrect is `wrong`; on an unanswerable one, abstained is `correct` and answered is `wrong`. Statuses `answered` and `partial` both count as answering. A baseline abstains when its reply starts with `ABSTAIN` or is empty.

## 6. Analysis plan

- **One run.** Each system runs on each test question once. There are no repeats in the confirmatory analysis. An optional repeat on a 100-question subset, to estimate run-to-run variance, is exploratory.
- **No peeking.** No result on the test split is read before the runs are complete. The runner writes rows as they finish; nobody computes a report on a partial test run except to check that it is running.
- **Stopping.** The shared ledger is a hard stop at the cap minus its margin (section 9). If the budget stops a run, only question ids completed by **all** systems in the family are analysed (an error row counts as completed), and the report prints that n and the per-system completed counts. The confirmatory comparisons and the family table use that common set; the per-system descriptive tables use every question a system completed. The runner orders work question by question, so a stop cuts every system at about the same question.
- **Errors and refusals.** An API or model failure after the client's retries (up to 5 attempts) is handled the same for every system, the engine included (`Engine.ask` still turns it into an "unsupported" abstention as a library; the engine system detects that from the trace): the row is written with `status: "error"`, it is retried when the runner restarts, and the report counts a remaining error row as outcome "wrong" for that system and prints the error count per system. A budget stop is never an error: the run stops and no row is written for the refused call. A model refusal or an empty reply is graded like any other reply: empty counts as an abstention.
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
| `locked_hash()` | `heuresis hash`, or `heuresis.locked.guard.locked_hash()` | `d98f86a5969279db434645acb8585f512999c60789068afdfa3cfdff4aa2eb88` (changed on 2026-11-12 by the verifier change in `locked/verify.py`, deviations log; it was `3c23fecd42520db9a36c3208d285d6d96465f42e1c2ef8e31d2d2b2d79de1b71` before) | `[ ... ]` |
| Surface hash | `heuresis.bench.systems.surface_hash` (effective engine config JSON, `DRAFT_SYSTEM`, source of `surface/prompts.py`); `heuresis hash` prints it and each run's `manifest.json` records it | `a7fe2849f9a81805785afbcc818dff39953e0d8f6ff459a5648c61d40332d8d7` (changed on 2026-11-12 by the drafting prompt, the source label in the passage line and the config fields; before the source label it was `ca69c121b7a9d2a47da5f6ad04f31caf6dad9587a5afcf3c7dafe858350ea173`, and before this day's changes `b7e767ecd37764e19220985ea959a16c650a2aec104f7f3a867013de736ed58f`; the pilot recorded `3e310d25...` and the earlier draft `9de82a74...` under narrower definitions) | `[ ... ]` |
| Full effective engine config | `manifest.json` key `engine_config` | see below | `[ ... ]` |
| `prompts_hash()` | `heuresis.bench.systems.prompts_hash()`; also printed by `heuresis hash` | `c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b` (changed on 2026-11-12 by the shared passage line with the source label; it was `1498745bcecca370bd94caef482d685ab41c84890ab5a208320f2dcbacc2a462`) | `[ ... ]` |
| Dataset manifest hashes | sha256 of each `MANIFEST.json` | section 2 | `[ ... ]` |
| Model ids and files | generator, embedder, reranker, entailer; `manifest.json` key `model_provenance` | `claude-haiku-5-5`, no temperature sent (`null`), `thinking` `{"type": "disabled"}` and `max_tokens` 600; the three `onnx:` ids of section 3.1; for each local model the sha256 of its ONNX file and tokenizer file on disk (`fingerprint()`) | `[ ... ]` (the file hashes exist only once a paid or local run has loaded the models) |
| Baseline settings | passage count k per baseline (section 8.2) | 8 (agentic: 5 per search, 4 searches) | `[ ... ]` |
| Price table | `PRICE_TABLE` in `bench/run.py` | `anthropic-2026-11` | `[ ... ]` |
| Commit hash | repository `HEAD` at the tag | `[ ... ]` | `[ ... ]` |

Effective engine config at drafting (packaged `surface/default.json` with `draft.max_sentences` set to 2 by `BenchContext.engine_config()`):

```json
{"decide": {"conflict_margin": 0.1, "min_supported_fraction": 1.0, "partial_fraction": 0.5},
 "draft": {"max_context_chars": 24000, "max_sentences": 2, "max_tokens": 600, "model": "claude-haiku-5-5", "prompt": "v2"},
 "retrieve": {"dense": true, "early_stop": true, "early_stop_margin": 0.35, "expand": false, "expand_hops": 1,
              "k_dense": 50, "k_lexical": 50, "rerank": false, "rerank_in": 50, "rerank_out": 8, "rewrite": false,
              "rrf_k": 60, "second_round": false},
 "router": {"ask_threshold": 0.6, "default_intent": "lookup"},
 "verify": {"answers_question": false, "atomic_claims": false, "partial_threshold": 0.3, "support": "window_title", "support_threshold": 0.5}}
```

The two `verify` thresholds are the values to be replaced by calibration (section 8.1). The engine runs with no router classifier, so the ask-back gate cannot fire in the benchmark.

## 8. Calibration on dev

Placeholder: to be filled after the run. Nothing in this section has been run.

**Procedure.** One paid run of all systems of section 3.1 on the 100 dev questions of each dataset (300 questions), under the shared ledger. Nothing is read from the test or sealed splits.

### 8.1 Engine

`verify.support_threshold` and `verify.partial_threshold` are set to maximise the dev penalised score over a fixed grid: each from 0.1 to 0.9 in steps of 0.1, with partial not above support (45 pairs), pooled over the three datasets, one setting for all. Ties are broken toward the higher support threshold, then the higher partial threshold (the more conservative setting; **proposed**). The drafts do not depend on the thresholds, so each draft is stored once (the engine's row keeps the raw draft, the passages shown, the tool results and the per-claim entailment scores before thresholding) and `python -m heuresis.bench.calibrate RUN_DIR...` replays labelling and the decision locally for each pair, with no model call; it refuses a run folder whose manifest split is not `dev`. The tie-break above is the one the code implements, and it is still **proposed**.

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

*(Entries before the tag are disclosures; the first one corrects the draft's own banner.)*

| Date | Change | Reason | Data seen at the time |
|---|---|---|---|
| 2026-11-11 | Banner and section 2 corrected, section 2a added: "nothing on the test split has been run" was inaccurate. | Two retrieval-only sanity checks read the test split: BM25 at k = 50 on the first 20 answerable test questions of each dataset (gold units found 20/20 each), and, on `hoh`, 100 test questions checked for the gold answer in the retrieved gold unit (86/100 with the date filter, 41/100 without). No system answered, no model was called, no design decision used the numbers; the sealed split was not read. A contamination risk for the reader to weigh. | Test split, as described in section 2a. |
| 2026-11-11 | Temperature 0 was planned; the model rejects the parameter (HTTP 400 on the first paid smoke call, $0 spent); the parameter is no longer sent. | The Messages API answers HTTP 400 "`temperature` is deprecated for this model." for `claude-haiku-5-5`; the manifest records `"temperature": null`. | No paid answer seen; $0 spent. |
| 2026-11-12 | The generator is called with `thinking: {"type": "disabled"}` for every system (`bench.run --thinking disabled`, the default; `--thinking default` restores the old behaviour). Each paid call now records its stop reason, content-block counts and visible characters in the ledger, and each result row records `stop_reasons`, `blocks` and `text_chars`. | **Made on dev evidence** (`results/dev-calibration/NOTES.md`, `results/dev-calibration/phase1/NOTES.md`): in the dev calibration run Haiku 5.5 spent most output tokens on adaptive thinking that `AnthropicLLM` does not read (thinking is on by default at medium effort for this model, `platform.claude.com/docs/en/build-with-claude/adaptive-thinking` and `.../effort`; `max_tokens` bounds thinking plus text, thinking tokens are billed as output tokens). Evidence: engine rows with a raw draft of 0 characters and 600 output tokens; `ABSTAIN` replies (7 characters) billed at 100 to 380 output tokens; 41 of 100 `closed_book` replies on `musique` and 34 of 100 engine replies on `multihoprag` at the cap. The documentation says the model accepts `thinking: disabled` at effort high or below; the call is untested until the next paid run. | Dev calibration run (3 x 100 dev questions, all systems). |
| 2026-11-12 | Drafting instruction rewritten (`DRAFT_SYSTEM_V2`, section 3.4); the first one stays selectable (`draft.prompt = "v1"`). | **Made on dev evidence** (`results/dev-calibration/phase1/NOTES.md`, item B): 78 of 100 (`musique`) and 68 of 100 (`multihoprag`) engine abstentions were the model writing ABSTAIN. In 3 of the 78 and 19 of the 68 all gold passages were among those shown; the rest are retrieval gaps. The new text asks for the answer first, for combining facts across passages, and for ABSTAIN only when the answer is not in the passages. Not verified: the effect can only be measured with paid calls. | Dev calibration run, engine drafts. |
| 2026-11-12 | The verifier scores a claim by the best entailment over title-prefixed windows of up to three consecutive sentences of each cited passage (`verify.support = "window_title"`, `locked/verify.py`); the first scoring (one joined premise of the passage texts) stays selectable (`verify.support = "current"`). Thresholds unchanged (0.5 / 0.3). | **Made on dev evidence** (`results/dev-calibration/phase1/`: `verifier_replay.json`, `verifier_paired.txt`, `NOTES.md` item C): the NLI model scored claims that restate a passage at 0.002 to 0.07 because the claim names an entity that only the passage title carries (neutral 0.99; with the title prepended entailment 0.97 to 0.99), and a joined premise is cut at 512 tokens for 16 of 194 claims. Replay on the stored dev rows at the default thresholds, pooled n = 300: penalised score 0.200 (current), 0.303 (title in the joined premise), 0.333 (this scoring), 0.347 (lexical share of content tokens); paired difference of this scoring against the current one +0.133 [+0.087, +0.180], no dataset worse; against the lexical score -0.013 [-0.037, +0.007]. The lexical score was not adopted (not distinguishable on n = 100 per dataset; it checks no meaning). The claim-level AUROC against correct versus wrong drafts is about 0.5 for every candidate (the wrong answers' claims are true of their passages). | Dev calibration run, engine replay payloads; the choice used the same 300 dev questions it is scored on (in-sample). |
| 2026-11-12 | Every passage line of every system (the engine's draft prompt, the baselines, the agentic search results, the oracle) now carries a readable source label, e.g. `[t1] (Title; source: Sporting News; valid 2023-10-24..) ...`, from one shared function (`passage_line` in `surface/prompts.py`; `bench.systems._passage_line` calls it). | **Made on dev evidence** (`results/dev-calibration/phase1/NOTES.md`, item B): many `multihoprag` abstentions say that the passages do not name the outlet the question names, while the outlet (`source_id`) was known and never shown, to the engine and the baselines alike. The label is derived from the source id (after the first colon, hyphens and underscores to spaces, capitalised); on `musique` it is the uninformative `Hipporag` and on `hoh` whatever its source id gives. Both the surface hash and `prompts_hash()` change. | Dev calibration run, engine drafts. |
| 2026-11-12 | A secondary, exploratory, judge-assisted grade is added (`python -m heuresis.bench.judge`, `judge.jsonl`, Table 1b of the report). **The deterministic containment grade stays the primary measure and is unchanged.** | **Made on dev evidence** (`results/dev-calibration/phase1/NOTES.md`, item D): 7 of the engine's 15 dev answers graded wrong read as correct but are rejected by string containment ("140 miles" vs "140 mi", word order, a possessive, a two-part answer). The judge is `claude-haiku-5-5`, the same model family as the generator, so it may favour that family's answers; it sees the question, the gold answers and the answer, for every answered row of every system that the containment grader marked wrong on an answerable question, identically for all systems, with thinking off. Its verdicts are stored beside the results and never overwrite the primary grade. It will not be used for the confirmatory tests. | Dev calibration run (15 engine answers read by hand). |
| 2026-11-12 | An optional engine stage `verify.answers_question` (default **off**): after verification, on answered questions only, one model call asks whether the answer states what the question asks for (YES / NO); NO turns the answer into an abstention of type `unsupported` with a trace note; its cost is recorded as a stage and in the ledger. It exists as an A/B arm for the dev re-run only. | **Made on dev evidence** (`results/dev-calibration/phase1/NOTES.md`, item D): 8 of the engine's 15 wrong dev answers are supported statements that do not answer the question. The threshold replay (`bench.calibrate`) does not model this stage, so rows of this arm are not used for calibration. | Dev calibration run, engine wrong answers. |

## 11. Threats to validity

- **LLM-generated questions in HoH.** Question texts were generated from diffs by a model; some may be odd, ambiguous or answerable without the date.
- **Monthly snapshot granularity.** `valid_from` is late by up to a month, and only six months of change are present.
- **The engine is given the date; the baselines are not** (section 3.2). A `hoh` win says the date filter works end to end; it does not say the rest of the algorithm is better. The `+asof` copies are the control, and they are exploratory.
- **Cover-exact-match favours longer answers.** An answer that contains the gold string is correct however much else it says. This is mitigated by the shared two-sentence instruction, and mean answer length is reported per system. It is not eliminated: the engine's draft format and the baselines' differ.
- **Different kinds of confidence** (section 5): AURC compares the engine's verification grade with a model's stated number.
- **One generator model, one run.** No claim extends to other models. Sampling is the API default and cannot be set for this model (it rejects `temperature`); repeats may differ. This is one more reason a single run carries run-to-run variance that the confirmatory analysis does not estimate.
- **Local compute is not priced.** The engine runs an entailer on CPU for every answer; the baselines run none. Latency is wall-clock time around `System.answer`, measured the same way for every system with the manifest's number of worker threads in parallel (the engine's stage-timing sum is kept in a separate field), so it includes waiting on the shared client and the other workers and is indicative only.
- **Verifier training data.** The verification model is a multilingual NLI model reported to have been trained without Portuguese data (not verified in this repository). The three English datasets here do not exercise Portuguese, so nothing in this study says how the verifier behaves on Portuguese.
- **The verifier may reject correct answers.** The dev proxy in `docs/pilot-dev.md` item 5 reports, at the packaged threshold, 0 of 100 matched pairs on `musique` and 3 of 88 on `multihoprag` scoring at or above 0.5, and 39 of 100 on `hoh`. It is built from gold answers rather than drafted ones, but it suggests the packaged threshold is strict; calibration (section 8) addresses it on dev.
- **Divergence and conflict detection is not implemented.** The engine never returns `divergent` (a comment in `src/heuresis/engine.py` says so). Nothing here tests it, and none of the three datasets contains conflicting sources by design.
- **The reranker choice was made on dev.** The cross-encoder is off in the engine because dev retrieval fell with it on two of three datasets (`docs/pilot-dev.md` side findings), and it is on in `hybrid_rerank`. Both choices were informed by the same 100 dev questions per dataset.
- **The engine's default cascade was changed after the dev pilot.** See `docs/pilot-dev.md`, section "Cascade after the pilot's changes": the packaged default `retrieve.rerank` went from true to false. The pilot's dry-run prompt sizes (item 3) and cost model (item 6) were produced with the earlier default.
- **Other changes after the pilot.** `Engine._settle_date` (a date named in a question is used as an as-of date only if the corpus holds history and the date is not earlier than its first version) and `draft.max_sentences = 2` for the benchmark postdate the pilot's text. `docs/pilot-dev.md` keeps the pilot's text on the router date problem ("possible bug, not fixed") with one dated line saying it was fixed afterwards in `Engine._settle_date`. The behaviour was checked on 2026-11-11 on a one-unit in-memory corpus and the engine answered.
- **Unverified licences.** See section 2 and `docs/datasets.md`, "Not verified".
- **Retrieval recall is unit-level** and uses the question text as the query. It says whether a gold unit was shown to the generator, not whether the answer was in it.

## 12. Open items before registration

Gaps between the earlier draft and the code. Closed items say how; open ones remain to be closed or logged as deviations before the tag. The draft banner stays: thresholds are uncalibrated and no hash is frozen.

1. **Error rows. Closed.** An API or model failure after retries is an `error` row for every system (`bench/run.py` writes it, `bench/systems.py` detects the engine's from its trace via `engine.trace_failure`; `Engine.ask` keeps its library behaviour), is retried on restart, and `bench/report.py` counts a remaining one as outcome "wrong" and prints the count per system. Budget stops are not errors: the engine system now raises the budget stop like a baseline, so no row is written (before this, the engine wrote an "abstained / budget" row that a restart would not retry).
2. **Common question ids. Closed.** `report.build` restricts the confirmatory comparisons, the exploratory ones and the family table to the ids completed by all confirmatory-family systems and prints that n and the per-system completed counts.
3. **Grid replay. Closed.** Engine rows store the replay data; `bench/calibrate.py` (`replay`, `grid`, command line) replays labelling and `decide` offline; a test shows replay at the run's thresholds reproduces every stored outcome and at other thresholds equals a fresh run. It has not been run on real drafts: the calibration itself (section 8) is still to be done.
4. **Model revisions. Closed in code.** The manifest records, per local model, its id and the sha256 of the ONNX and tokenizer files on disk (`fingerprint()` in `models_local.py`), and for the generator its id, temperature (`null`: not sent, see the deviations log of 2026-11-11) and `max_tokens`. The values exist only after a run that loads the real models; the frozen values in section 7 are still `[ ... ]`. No Hugging Face revision is recorded; the file hashes identify the files.
5. **Two "surface hashes". Closed.** One implementation, `bench.systems.surface_hash` (effective engine config, `DRAFT_SYSTEM`, source of `surface/prompts.py`), used by `run.py` and by `heuresis hash`, which also prints `prompts_hash()` and `locked_hash()`. `prompts_hash()` now also covers the source of the functions that build baseline prompts. Both hashes changed by this; section 7 holds the new values.
6. **`docs/datasets.md`, `hoh` "Sanity" row. Closed.** It was a test-split check. The banner, section 2, the new section 2a, the deviations log (section 10), `README.md` and `docs/datasets.md` now say so; the numbers are unchanged and unused.
7. **Decision rules** in section 1 and the tie-breaks in sections 8.1 and 8.2 are proposals. **Open.** The owner confirms them before the tag.
8. **Further changes made while closing the items above.** `AnthropicLLM` sends `temperature` only when given, and the benchmark sends none (section 3; deviations log, 2026-11-11); `bench.run --paid` requires `--ledger` and reads the key from `PROJECTS_ANTHROPIC_KEY` or `--key-env NAME`, printing only the name and the base URL and failing before any work if the variable is unset (`docs/cli.md`); latency is wall-clock around `System.answer` for every system. **Open caveat:** an error row of a baseline that failed mid-way (for example `agentic` on its third call) carries no usage, so the report's cost for that system omits the money the ledger did charge for the failed answer; the ledger total is the reference for spend.
