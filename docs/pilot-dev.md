# Pilot on the dev split (zero cost)

Date: 2026-11-11. Every number is labelled **measured on dev (n=...)** or **assumed**. No language-model call was made: the generator in item 3 is the offline `EchoLLM`; the embedder, reranker and entailer are the local ONNX models. Only the `dev` split of each dataset was used (100 questions each). Wilson 95% intervals are given in brackets for every proportion.

## Versions at the time of the pilot

| Item | Value |
|---|---|
| `locked_hash()` | `3c23fecd42520db9a36c3208d285d6d96465f42e1c2ef8e31d2d2b2d79de1b71` |
| surface config hash (`bench.run.surface_hash`, config + `DRAFT_SYSTEM`) | `3e310d251f55e0f45b60381d04272bddbeb1bd7cd69da434e567e6f45b53886d` |
| `prompts_hash()` | `c82a56eba64a36982a8106c6a40f4b5c02c459de4cd981cd724cf72435dca6de` |
| embedder | `onnx:intfloat/multilingual-e5-small` |
| reranker | `onnx:cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` |
| entailer | `onnx:MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli` |
| generator in the dry run | `echo` (offline fake). Configured paid model, never called: `claude-haiku-5-5` |
| retrieve config | `{"dense": true, "early_stop": true, "early_stop_margin": 0.35, "expand": false, "expand_hops": 1, "k_dense": 50, "k_lexical": 50, "rerank": true, "rerank_in": 50, "rerank_out": 8, "rewrite": false, "rrf_k": 60, "second_round": false}` |

## 1. Ingest and embedding

Measured on the full built corpus (not a sample), 4 CPU cores, ONNX fp32, batch 64 (inner batch 16, length-sorted within the 64).

| dataset | units | versions embedded | ingest s | embedding time | versions/s | db size MB (incl. vectors) |
|---|---|---|---|---|---|---|
| musique | 11656 | 11656 | 0.9 | 359 (6.0 min) | 32.4 | 49 |
| multihoprag | 5048 | 5048 | 0.6 | 345 (5.8 min) | 14.6 | 37 |
| hoh | 111972 | 230746 | 11.3 | 1586 (26.4 min) | 145.5 | 702 |

The `hoh` projection was 22 minutes from a 256-passage probe (under the 45-minute line), so all versions were embedded; no sampling was done.

## 2. Retrieval only (k = 8), answerable dev questions with gold units

Recall of any gold unit and of all gold units among the 8 returned passages (unit level). Time is wall-clock per query over all 100 dev questions, one thread, including embedding the query and the cross-encoder where used. BM25 = SQLite FTS5 `bm25()`; the packaged config is used for all legs (k_lexical 50, k_dense 50, rrf_k 60, rerank 50 -> 8). The cascade is run with a default `Query` (`intent=lookup`), i.e. without the router.

### musique

| system | any gold unit @8 | all gold units @8 | ms / query |
|---|---|---|---|
| a. BM25 | 87/100 = 87% [79, 92] | 15/100 = 15% [9, 23] | 16 |
| b. dense | 80/100 = 80% [71, 87] | 16/100 = 16% [10, 24] | 130 |
| c. BM25+dense RRF | 89/100 = 89% [81, 94] | 18/100 = 18% [12, 27] | 143 |
| d. c + rerank | 95/100 = 95% [89, 98] | 21/100 = 21% [14, 30] | 1728 |
| e. default cascade | 94/100 = 94% [88, 97] | 20/100 = 20% [13, 29] | 1746 |

Cascade early stop (measured on dev): fired on 51/100 questions (51/100 of the scored ones). Recall of any / all gold unit:

| subset | n | any @8 | all @8 |
|---|---|---|---|
| early stop fired | 51 | 50/51 = 98% [90, 100] | 11/51 = 22% [12, 35] |
| did not fire | 49 | 44/49 = 90% [78, 96] | 9/49 = 18% [10, 31] |

### multihoprag

| system | any gold unit @8 | all gold units @8 | ms / query |
|---|---|---|---|
| a. BM25 | 81/88 = 92% [84, 96] | 25/88 = 28% [20, 39] | 25 |
| b. dense | 64/88 = 73% [63, 81] | 12/88 = 14% [8, 22] | 104 |
| c. BM25+dense RRF | 80/88 = 91% [83, 95] | 23/88 = 26% [18, 36] | 112 |
| d. c + rerank | 67/88 = 76% [66, 84] | 12/88 = 14% [8, 22] | 4198 |
| e. default cascade | 68/88 = 77% [67, 85] | 12/88 = 14% [8, 22] | 4161 |

Cascade early stop (measured on dev): fired on 38/100 questions (35/88 of the scored ones). Recall of any / all gold unit:

| subset | n | any @8 | all @8 |
|---|---|---|---|
| early stop fired | 35 | 29/35 = 83% [67, 92] | 7/35 = 20% [10, 36] |
| did not fire | 53 | 39/53 = 74% [60, 84] | 5/53 = 9% [4, 20] |

### hoh, as-of = question date

| system | any gold unit @8 | all gold units @8 | ms / query | in-force version retrieved |
|---|---|---|---|---|
| a. BM25 | 100/100 = 100% [96, 100] | 100/100 = 100% [96, 100] | 96 | 100/100 = 100% [96, 100] |
| b. dense | 92/100 = 92% [85, 96] | 92/100 = 92% [85, 96] | 735 | 92/100 = 92% [85, 96] |
| c. BM25+dense RRF | 98/100 = 98% [93, 99] | 98/100 = 98% [93, 99] | 763 | 98/100 = 98% [93, 99] |
| d. c + rerank | 92/100 = 92% [85, 96] | 92/100 = 92% [85, 96] | 1300 | 92/100 = 92% [85, 96] |
| e. default cascade | 93/100 = 93% [86, 97] | 93/100 = 93% [86, 97] | 585 | 93/100 = 93% [86, 97] |

Cascade early stop (measured on dev): fired on 97/100 questions (97/100 of the scored ones). Recall of any / all gold unit:

| subset | n | any @8 | all @8 | in-force version |
|---|---|---|---|---|
| early stop fired | 97 | 91/97 = 94% [87, 97] | 91/97 = 94% [87, 97] | 91/97 = 94% [87, 97] |
| did not fire | 3 | 2/3 = 67% [21, 94] | 2/3 = 67% [21, 94] | 2/3 = 67% [21, 94] |

In-force version by question kind (measured on dev):

| system | kind = current | kind = outdated |
|---|---|---|
| a. BM25 | 49/49 = 100% [93, 100] | 51/51 = 100% [93, 100] |
| b. dense | 42/49 = 86% [73, 93] | 50/51 = 98% [90, 100] |
| c. BM25+dense RRF | 48/49 = 98% [89, 100] | 50/51 = 98% [90, 100] |
| d. c + rerank | 43/49 = 88% [76, 94] | 49/51 = 96% [87, 99] |
| e. default cascade | 44/49 = 90% [78, 96] | 49/51 = 96% [87, 99] |

### hoh, as-of = today (not time-aware)

| system | any gold unit @8 | all gold units @8 | ms / query | in-force version retrieved |
|---|---|---|---|---|
| a. BM25 | 100/100 = 100% [96, 100] | 100/100 = 100% [96, 100] | 111 | 49/100 = 49% [39, 59] |
| b. dense | 87/100 = 87% [79, 92] | 87/100 = 87% [79, 92] | 909 | 42/100 = 42% [33, 52] |
| c. BM25+dense RRF | 98/100 = 98% [93, 99] | 98/100 = 98% [93, 99] | 1025 | 48/100 = 48% [38, 58] |
| d. c + rerank | 91/100 = 91% [84, 95] | 91/100 = 91% [84, 95] | 1610 | 43/100 = 43% [34, 53] |
| e. default cascade | 92/100 = 92% [85, 96] | 92/100 = 92% [85, 96] | 625 | 44/100 = 44% [35, 54] |

Cascade early stop (measured on dev): fired on 95/100 questions (95/100 of the scored ones). Recall of any / all gold unit:

| subset | n | any @8 | all @8 | in-force version |
|---|---|---|---|---|
| early stop fired | 95 | 89/95 = 94% [87, 97] | 89/95 = 94% [87, 97] | 43/95 = 45% [36, 55] |
| did not fire | 5 | 3/5 = 60% [23, 88] | 3/5 = 60% [23, 88] | 1/5 = 20% [4, 62] |

In-force version by question kind (measured on dev):

| system | kind = current | kind = outdated |
|---|---|---|
| a. BM25 | 49/49 = 100% [93, 100] | 0/51 = 0% [0, 7] |
| b. dense | 42/49 = 86% [73, 93] | 0/51 = 0% [0, 7] |
| c. BM25+dense RRF | 48/49 = 98% [89, 100] | 0/51 = 0% [0, 7] |
| d. c + rerank | 43/49 = 88% [76, 94] | 0/51 = 0% [0, 7] |
| e. default cascade | 44/49 = 90% [78, 96] | 0/51 = 0% [0, 7] |

## 3. Harness end to end in dry-run mode: prompt sizes and calls

Command path: `heuresis.bench.run.run(dataset, 'dev', systems, out, ledger, dry_run=True)` with all eight systems, `EchoLLM` as generator, local retrieval models, one worker, baselines not time-aware (the default). Characters = system prompt + user prompt of every model call, summed over the calls of a question (measured on dev, n=100). Tokens = characters / 3.5 (**assumed** conversion, not measured; the dataset manifests use /4).

### musique

| system | mean chars | p95 chars | mean / p95 tokens (assumed /3.5) | mean calls (EchoLLM) | note |
|---|---|---|---|---|---|
| closed_book | 293 | 359 | 84 / 103 | 1.00 | rows 100, errors 0 |
| bm25 | 4,932 | 6,841 | 1,409 / 1,955 | 1.00 | rows 100, errors 0 |
| vector | 4,607 | 7,163 | 1,316 / 2,047 | 1.00 | rows 100, errors 0 |
| hybrid_rerank | 5,048 | 7,781 | 1,442 / 2,223 | 1.00 | rows 100, errors 0 |
| agentic | 629 | 695 | 180 / 199 | 1.00 | rows 100, errors 0 |
| long_context | unavailable |  |  |  | corpus is about 1409951 tokens, limit is 90000 |
| engine | 6,104 | 8,817 | 1,744 / 2,519 | 0.99 | rows 100, errors 0 |
| oracle | 1,899 | 3,487 | 543 / 996 | 1.00 | rows 100, errors 0 |

`agentic` analytic (the offline fake never searches, so its row above is a single call with no passages). Built with the real prompt code, search i returns the next 5 passages of the hybrid+rerank ranking, query text = the question; calls = searches + 1 (analytic, n=100 dev questions):

| searches | calls | mean chars | p95 chars | mean / p95 tokens (assumed /3.5) |
|---|---|---|---|---|
| 1 | 2 | 4,514 | 6,456 | 1,290 / 1,845 |
| 2 | 3 | 11,305 | 16,296 | 3,230 / 4,656 |
| 4 | 5 | 33,788 | 49,069 | 9,654 / 14,020 |

### multihoprag

| system | mean chars | p95 chars | mean / p95 tokens (assumed /3.5) | mean calls (EchoLLM) | note |
|---|---|---|---|---|---|
| closed_book | 492 | 628 | 141 / 179 | 1.00 | rows 100, errors 0 |
| bm25 | 11,987 | 12,980 | 3,425 / 3,709 | 1.00 | rows 100, errors 0 |
| vector | 11,879 | 12,771 | 3,394 / 3,649 | 1.00 | rows 100, errors 0 |
| hybrid_rerank | 12,175 | 13,061 | 3,479 / 3,732 | 1.00 | rows 100, errors 0 |
| agentic | 828 | 964 | 237 / 275 | 1.00 | rows 100, errors 0 |
| long_context | unavailable |  |  |  | corpus is about 1574432 tokens, limit is 90000 |
| engine | 13,248 | 14,220 | 3,785 / 4,063 | 1.00 | rows 100, errors 0 |
| oracle | 3,682 | 6,050 | 1,052 / 1,729 | 1.00 | rows 100, errors 0 |

`agentic` analytic (the offline fake never searches, so its row above is a single call with no passages). Built with the real prompt code, search i returns the next 5 passages of the hybrid+rerank ranking, query text = the question; calls = searches + 1 (analytic, n=100 dev questions):

| searches | calls | mean chars | p95 chars | mean / p95 tokens (assumed /3.5) |
|---|---|---|---|---|
| 1 | 2 | 9,307 | 9,988 | 2,659 / 2,854 |
| 2 | 3 | 25,288 | 27,078 | 7,225 / 7,737 |
| 4 | 5 | 79,932 | 85,786 | 22,838 / 24,510 |

### hoh

| system | mean chars | p95 chars | mean / p95 tokens (assumed /3.5) | mean calls (EchoLLM) | note |
|---|---|---|---|---|---|
| closed_book | 269 | 314 | 77 / 90 | 1.00 | rows 100, errors 0 |
| bm25 | 1,634 | 2,058 | 467 / 588 | 1.00 | rows 100, errors 0 |
| vector | 1,869 | 2,361 | 534 / 675 | 1.00 | rows 100, errors 0 |
| hybrid_rerank | 1,693 | 2,089 | 484 / 597 | 1.00 | rows 100, errors 0 |
| agentic | 605 | 650 | 173 / 186 | 1.00 | rows 100, errors 0 |
| long_context | unavailable |  |  |  | corpus is about 7296081 tokens, limit is 90000 |
| engine | 2,691 | 3,033 | 769 / 866 | 1.00 | rows 100, errors 0 |
| oracle | 497 | 630 | 142 / 180 | 1.00 | rows 100, errors 0 |

`agentic` analytic (the offline fake never searches, so its row above is a single call with no passages). Built with the real prompt code, search i returns the next 5 passages of the hybrid+rerank ranking, query text = the question; calls = searches + 1 (analytic, n=100 dev questions):

| searches | calls | mean chars | p95 chars | mean / p95 tokens (assumed /3.5) |
|---|---|---|---|---|
| 1 | 2 | 2,187 | 2,551 | 625 / 729 |
| 2 | 3 | 4,740 | 5,603 | 1,354 / 1,601 |
| 4 | 5 | 12,750 | 15,736 | 3,643 / 4,496 |

Unavailable systems: `long_context` on all three datasets, because the corpus is far above its ~90,000-token limit (manifest `corpus_tokens`: musique 1,409,951, multihoprag 1,574,432, hoh 7,296,081). `agentic` with the offline fake is available but does not exercise its loop (see the analytic rows).

Harness reports written by the pipeline (`report.write`, 200 bootstrap iterations) are in `runs/pilot-dev/<dataset>/dryrun/results.md`; their accuracy columns are meaningless here (EchoLLM) and are not used.

## 4. Long-context feasibility for `multihoprag` (reduced-corpus tier)

Articles (unit id without `#n`, e.g. `multihoprag:aab13a0697b`) sorted by `sha256(article id)` and added in that order while the rendered prompt stays under 80,000 tokens; the first article that would not fit stops the selection. Prompt size is the document block as `long_context` renders it (one line per passage with title and validity span). Dev: 100 questions, 88 answerable, 12 unanswerable (measured on dev).

| token rule | articles chosen | passages | est. tokens | dev answerable with ALL gold inside | with ANY gold inside | dev unanswerable still valid | usable dev questions |
|---|---|---|---|---|---|---|---|
| tokens = chars/3.5 (assumed) | 31 of 609 (5.1%) | 218 | 79,855 | 0/88 | 5/88 | 12/12 | 12 |
| tokens = chars/4 (manifest convention) | 36 of 609 (5.9%) | 246 | 79,137 | 0/88 | 5/88 | 12/12 | 12 |

For scale (measured on dev): the 122 distinct articles that hold the gold evidence of the 88 answerable dev questions alone would need about 411,670 tokens (chars/3.5); a tier chosen by gold would also leak the answers' location, so it is not an option. Gold articles per question (dev): {'2': 51, '3': 28, '4': 9}.

## 5. Entailer sanity check without a language model

**Crude proxy, not a measurement of verification quality on drafted answers.** Matched pairs: (gold passage, statement). Mismatched: the same statement against a random non-gold passage (seeded draw from all versions of the store). Premise = gold passage (for multi-gold questions, the gold passage that contains the answer, else the first). Statement S2 = `<question> <gold answer>` (all pairs); S1 = a minimal declarative rewrite `The X was <answer>.` for questions of the form "What/Who is/was X?" (only where the rule fires). Containment = the normalised gold answer occurs in the passage, no model involved. Threshold = packaged `verify.support_threshold`.

### musique (n pairs = 100, entailer throughput 62.8 pairs/s)

| statement | pairs | n | mean score | Q1 / median / Q3 | score >= threshold | AUROC [95% bootstrap] |  |
|---|---|---|---|---|---|---|---|
| S2_question_plus_answer | matched | 100 | 0.070 | 0.016 / 0.042 / 0.082 | 0/100 = 0% [0, 4] | 0.855 [0.806, 0.902] |  |
|  | mismatched | 100 | 0.013 | 0.003 / 0.006 / 0.014 | 0/100 = 0% [0, 4] |  |  |
| S1_declarative | matched | 20 | 0.119 | 0.034 / 0.061 / 0.194 | 0/20 = 0% [0, 16] | 0.938 [0.853, 1.000] |  |
|  | mismatched | 20 | 0.016 | 0.002 / 0.003 / 0.007 | 0/20 = 0% [0, 16] |  |  |

Containment of the gold answer: gold passage 100/100 = 100% [96, 100], random passage 1/100 = 1% [0, 5].

### multihoprag (n pairs = 88, entailer throughput 23.7 pairs/s)

| statement | pairs | n | mean score | Q1 / median / Q3 | score >= threshold | AUROC [95% bootstrap] |  |
|---|---|---|---|---|---|---|---|
| S2_question_plus_answer | matched | 88 | 0.181 | 0.092 / 0.157 / 0.250 | 3/88 = 3% [1, 10] | 0.659 [0.578, 0.734] |  |
|  | mismatched | 88 | 0.126 | 0.046 / 0.092 / 0.179 | 0/88 = 0% [0, 4] |  |  |
| S1_declarative | 0 | too few |  |  |  |  |  |  |

Containment of the gold answer: gold passage 39/88 = 44% [34, 55], random passage 18/88 = 20% [13, 30].

### hoh (n pairs = 100, entailer throughput 194.9 pairs/s)

| statement | pairs | n | mean score | Q1 / median / Q3 | score >= threshold | AUROC [95% bootstrap] |  |
|---|---|---|---|---|---|---|---|
| S2_question_plus_answer | matched | 100 | 0.346 | 0.029 / 0.317 / 0.591 | 39/100 = 39% [30, 49] | 0.918 [0.878, 0.955] |  |
|  | mismatched | 100 | 0.012 | 0.002 / 0.003 / 0.005 | 1/100 = 1% [0, 5] |  |  |
| S1_declarative | matched | 29 | 0.469 | 0.007 / 0.328 / 0.976 | 13/29 = 45% [28, 62] | 0.869 [0.773, 0.942] |  |
|  | mismatched | 29 | 0.006 | 0.001 / 0.002 / 0.005 | 0/29 = 0% [0, 12] |  |  |

Containment of the gold answer: gold passage 91/100 = 91% [84, 95], random passage 1/100 = 1% [0, 5].

## 6. Cost model (arithmetic on measured prompt sizes)

**Assumed:** tokens = chars/3.5; 120 output tokens per call; $0.1/M input and $0.5/M output tokens; 500 test questions per dataset, one run; any single request above 100,000 prompt tokens is priced at 5x (input and output); the prompt-size distribution of the dev split is taken to represent the test split (an extrapolation). `long_context` is excluded (unavailable). `engine` calls are those of the offline fake (a real draft that requests tools adds a follow-up call). `agentic` is shown for 1, 2 and 4 searches (analytic).

| system | musique (500 q) | multihoprag (500 q) | hoh (500 q) | total, 3 datasets |
|---|---|---|---|---|
| closed_book | 84 in, 1 call(s): $0.03 | 141 in, 1 call(s): $0.04 | 77 in, 1 call(s): $0.03 | $0.11 |
| bm25 | 1,409 in, 1 call(s): $0.10 | 3,425 in, 1 call(s): $0.20 | 467 in, 1 call(s): $0.05 | $0.36 |
| vector | 1,316 in, 1 call(s): $0.10 | 3,394 in, 1 call(s): $0.20 | 534 in, 1 call(s): $0.06 | $0.35 |
| hybrid_rerank | 1,442 in, 1 call(s): $0.10 | 3,479 in, 1 call(s): $0.20 | 484 in, 1 call(s): $0.05 | $0.36 |
| agentic_1search | 1,290 in, 2 call(s): $0.12 | 2,659 in, 2 call(s): $0.19 | 625 in, 2 call(s): $0.09 | $0.41 |
| agentic_2search | 3,230 in, 3 call(s): $0.25 | 7,225 in, 3 call(s): $0.45 | 1,354 in, 3 call(s): $0.16 | $0.86 |
| agentic_4search | 9,654 in, 5 call(s): $0.63 | 22,838 in, 5 call(s): $1.29 | 3,643 in, 5 call(s): $0.33 | $2.26 |
| engine | 1,744 in, 1 call(s): $0.12 | 3,785 in, 1 call(s): $0.22 | 769 in, 1 call(s): $0.07 | $0.40 |
| oracle | 543 in, 1 call(s): $0.06 | 1,052 in, 1 call(s): $0.08 | 142 in, 1 call(s): $0.04 | $0.18 |

Total for all seven available systems plus `oracle`, one run on 3 x 500 questions: **$2.16** (agentic at 1 search), **$2.61** (2 searches), **$4.01** (4 searches). No request exceeds 100,000 tokens, so the 5x rule never applies (`long_context` would trigger it on every request).

Batch API (50% off) on single-call systems (`closed_book`, `bm25`, `vector`, `hybrid_rerank`, `oracle`), assumed to apply to input and output:

| system | saving, 3 datasets |
|---|---|
| closed_book | $0.05 |
| bm25 | $0.18 |
| vector | $0.18 |
| hybrid_rerank | $0.18 |
| oracle | $0.09 |
| **total** | **$0.67** |

`agentic` is sequential (each search depends on the previous reply) and `engine` may need a follow-up call after tool results, so neither is counted as batchable.

The low absolute scores of `S2` mostly reflect its form (a question followed by an answer is not a declarative); only the separation between matched and mismatched pairs and the throughput are of interest here.

## Side findings (measured on dev)

- **Cross-encoder rerank lowers recall on `multihoprag`.** Any-gold recall @8 falls from 80/88 (BM25+dense RRF) to 67/88 after the rerank, and all-gold from 23/88 to 12/88 (item 2). It raises recall on `musique` (89 -> 95 any) and lowers it slightly on `hoh` (98 -> 92). The default cascade inherits this because rerank is always on.
- **The early stop saves little time as configured.** The rerank stage still runs over the lexical list after an early stop, so the cascade costs about as much as retrieval with rerank on `musique` and `multihoprag`; it is faster only on `hoh`, where the dense scan dominates. It fired on 51, 38 and 95-97 of 100 dev questions (musique, multihoprag, hoh).
- **Router date rule on an undated corpus (possible bug, not fixed).** In `heuresis.router.understand` (built-in date rule) a date in the question text becomes `as_of.valid`. `musique` units carry a placeholder `create` event dated 1970-01-01, so a question that mentions an earlier date has no version in force and the engine abstains with `not_valid_at_date`. In the dry run this hit `musique:2hop__47071_162399` ("... on 4th february 1928 ..."); the router also turned the "4th february 1928" into 1928-02-29. Minimal reproduction: an in-memory `Engine` over one unit whose only event is dated 1970-01-01, then `ask("When did the person who launched the Bardoli Satyagraha on 4th february 1928 die?")` returns `abstained` / `not_valid_at_date`, while the same question without the date is answered. The router found a date in 4 / 4 / 1 of the 100 dev questions of `musique` / `multihoprag` / `hoh`. In the benchmark the engine is called with the question's own `as_of` (None for the two undated sets), and a caller-supplied `as_of` wins only when it is set, so undated corpora are exposed.

## Reproduce

```
export HF_HUB_OFFLINE=1   # the loaders then use only the cached models; nothing is downloaded
for d in musique multihoprag hoh; do python3 scripts/pilot/p1_ingest.py $d; done      # item 1 (about 35 min on 4 cores)
for d in musique multihoprag hoh; do python3 scripts/pilot/p2_retrieval.py $d; done   # item 2
for d in musique multihoprag hoh; do python3 scripts/pilot/p3_dryrun.py $d; python3 scripts/pilot/p3b_agentic.py $d; done   # item 3
python3 scripts/pilot/p4_longctx.py                                                     # item 4
for d in musique multihoprag hoh; do python3 scripts/pilot/p5_verifier.py $d; done      # item 5
python3 scripts/pilot/p6_cost.py                                                        # item 6
python3 scripts/pilot/p7_doc.py                                                         # this document
```

Raw outputs: `runs/pilot-dev/` (git-ignored): `<dataset>/p1_ingest.json`, `p2_retrieval.json` (per-question), `p3b_agentic.json`, `p4_longctx.json`, `p5_verifier.json`, `<dataset>/dryrun/{results.jsonl,results.json,results.md,manifest.json,call_chars.json}`, `p6_cost.json`, and the stores `<dataset>/store.sqlite` (hoh: 0.7 GB).

Total pilot compute time (ingest through dry runs, excluding script writing): about 114 minutes wall-clock on 4 cores.

## What this does not show

- **No answer accuracy.** The generator was an offline echo; nothing here says how often any system answers correctly.
- **No verification quality on real drafts.** Item 5 scores statements built from gold answers against gold or random passages; model-written drafts are longer, paraphrased, multi-claim and sometimes wrong in subtler ways.
- **No abstention behaviour.** Unanswerable questions were only used for timing (item 2) and counted in item 4; no abstain decision was measured.
- **Dev split only** (100 questions per dataset, 88 answerable for `multihoprag`). Test and sealed splits were neither loaded into any output nor scored. Intervals are wide at n=100.
- Retrieval recall is unit-level and uses the question text as the query; the router, query rewriting, expansion and second-round switches are off in the packaged config and were not exercised.
- Prompt sizes come from one deterministic retrieval per question; real model replies (search queries, tool calls) will change multi-call systems. Token counts use an assumed 3.5 characters per token.
- Timings are for a 4-core CPU, single thread of queries, warm file cache; the `hoh` dense scan reads every in-force vector from SQLite on every query.
- The cost model is an extrapolation from dev prompt sizes to 500 test questions at assumed prices; it is not a quote.


## Cascade after the pilot's changes

Date: 2026-11-11. Measured on dev (n=100 per dataset; 88 answerable for `multihoprag`), retrieval only, k = 8, zero cost, same stores and local ONNX embedder as item 2 (`scripts/pilot/p8_cascade_norerank.py`, raw output `runs/pilot-dev/<dataset>/p8_cascade_norerank.json`). The cascade is the packaged default with `rerank` now `false` (lexical, early-stop test, dense + RRF when the stop did not fire; no cross-encoder), run with a default `Query` and without the router, as in item 2. Time is wall-clock per query over all 100 dev questions, one thread, including embedding the query.

| dataset | any gold @8 | all gold @8 | early stop fired | any @8 fired / not fired | all @8 fired / not fired | ms / query |
|---|---|---|---|---|---|---|
| musique | 89/100 = 89% [81, 94] | 16/100 = 16% [10, 24] | 51/100 | 49/51 = 96% [87, 99] / 40/49 = 82% [69, 90] | 8/51 = 16% / 8/49 = 16% | 63 |
| multihoprag | 81/88 = 92% [84, 96] | 25/88 = 28% [20, 39] | 38/100 (35 of the 88 scored) | 35/35 = 100% [90, 100] / 46/53 = 87% [75, 93] | 16/35 = 46% / 9/53 = 17% | 80 |
| hoh, as-of question date | 100/100 = 100% [96, 100] | 100/100 = 100% [96, 100] | 97/100 | 97/97 = 100% [96, 100] / 3/3 = 100% [44, 100] | 97/97 / 3/3 | 110 |
| hoh, as-of today | 100/100 = 100% [96, 100] | 100/100 = 100% [96, 100] | 95/100 | 95/95 = 100% [96, 100] / 5/5 = 100% [57, 100] | 95/95 / 5/5 | 144 |

The default changed because of the dev measurements above (item 2 and the side findings): the cross-encoder raised any-gold recall on `musique` but lowered it on `multihoprag` and `hoh`, at 1.3 to 4.2 s per query, so it is now an optional stage that stays off unless a configuration turns it on.
