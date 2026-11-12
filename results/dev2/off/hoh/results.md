# Results: hoh, split `dev2`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 6.0% [2.8%, 12.5%] | 85.0% [76.7%, 90.7%] | 9.0% [4.8%, 16.2%] | -0.790 [-0.880, -0.680] |
| bm25 | 100 | 33.0% [24.6%, 42.7%] | 58.0% [48.2%, 67.2%] | 9.0% [4.8%, 16.2%] | -0.250 [-0.420, -0.060] |
| hybrid | 100 | 34.0% [25.5%, 43.7%] | 53.0% [43.3%, 62.5%] | 13.0% [7.8%, 21.0%] | -0.190 [-0.350, -0.010] |
| hybrid_rerank | 100 | 34.0% [25.5%, 43.7%] | 46.0% [36.6%, 55.7%] | 20.0% [13.3%, 28.9%] | -0.120 [-0.300, 0.050] |
| agentic | 100 | 36.0% [27.3%, 45.8%] | 59.0% [49.2%, 68.1%] | 5.0% [2.2%, 11.2%] | -0.230 [-0.410, -0.040] |
| engine | 100 | 78.0% [68.9%, 85.0%] | 16.0% [10.1%, 24.4%] | 6.0% [2.8%, 12.5%] | 0.620 [0.470, 0.760] |
| engine_single (exploratory) | 100 | 67.0% [57.3%, 75.4%] | 16.0% [10.1%, 24.4%] | 17.0% [10.9%, 25.5%] | 0.510 [0.350, 0.650] |
| hybrid+asof (exploratory) | 100 | 73.0% [63.6%, 80.7%] | 14.0% [8.5%, 22.1%] | 13.0% [7.8%, 21.0%] | 0.590 [0.450, 0.730] |
| agentic+asof (exploratory) | 100 | 77.0% [67.8%, 84.2%] | 15.0% [9.3%, 23.3%] | 8.0% [4.1%, 15.0%] | 0.620 [0.480, 0.760] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 85 | 1 | 7.0% [3.4%, 13.7%] | -0.770 [-0.870, -0.660] | -0.790 [-0.880, -0.680] |
| bm25 | 100 | 58 | 12 | 45.0% [35.6%, 54.8%] | -0.010 [-0.180, 0.180] | -0.250 [-0.420, -0.060] |
| hybrid | 100 | 53 | 11 | 45.0% [35.6%, 54.8%] | 0.030 [-0.140, 0.210] | -0.190 [-0.350, -0.010] |
| hybrid_rerank | 100 | 46 | 10 | 44.0% [34.7%, 53.8%] | 0.080 [-0.080, 0.260] | -0.120 [-0.300, 0.050] |
| agentic | 100 | 59 | 10 | 46.0% [36.6%, 55.7%] | -0.030 [-0.210, 0.160] | -0.230 [-0.410, -0.040] |
| engine | 100 | 16 | 14 | 92.0% [85.0%, 95.9%] | 0.900 [0.820, 0.960] | 0.620 [0.470, 0.760] |
| engine_single (exploratory) | 100 | 16 | 12 | 79.0% [70.0%, 85.8%] | 0.750 [0.640, 0.850] | 0.510 [0.350, 0.650] |
| hybrid+asof (exploratory) | 100 | 14 | 11 | 84.0% [75.6%, 89.9%] | 0.810 [0.710, 0.890] | 0.590 [0.450, 0.730] |
| agentic+asof (exploratory) | 100 | 15 | 11 | 88.0% [80.2%, 93.0%] | 0.840 [0.740, 0.920] | 0.620 [0.480, 0.760] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 6.0% | 91.0% | 6.6% | 0.847 | n/a (n=0) | 200.1 |
| bm25 | 100 | 33.0% | 91.0% | 36.3% | 0.717 | n/a (n=0) | 97.5 |
| hybrid | 100 | 34.0% | 87.0% | 39.1% | 0.620 | n/a (n=0) | 100.8 |
| hybrid_rerank | 100 | 34.0% | 80.0% | 42.5% | 0.603 | n/a (n=0) | 100.8 |
| agentic | 100 | 36.0% | 95.0% | 37.9% | 0.598 | n/a (n=0) | 136.9 |
| engine | 100 | 78.0% | 94.0% | 83.0% | 0.171 | n/a (n=0) | 94.3 |
| engine_single (exploratory) | 100 | 67.0% | 83.0% | 80.7% | 0.180 | n/a (n=0) | 90.5 |
| hybrid+asof (exploratory) | 100 | 73.0% | 87.0% | 83.9% | 0.100 | n/a (n=0) | 96.1 |
| agentic+asof (exploratory) | 100 | 77.0% | 92.0% | 83.7% | 0.074 | n/a (n=0) | 138.8 |

## Table 2b. Errors (split `dev2`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 100 | 0 | 0 |
| bm25 | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| hybrid_rerank | 100 | 0 | 0 |
| agentic | 100 | 0 | 0 |
| engine | 100 | 0 | 0 |
| engine_single (exploratory) | 100 | 0 | 0 |
| hybrid+asof (exploratory) | 100 | 0 | 0 |
| agentic+asof (exploratory) | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev2`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | $0.0000 | $0.0049 | $0.0008 [$0.0005, $0.0024] | 854.9 | 1330.2 | 1.00 | 0.00 |
| bm25 | 100 | $0.0001 | $0.0099 | $0.0003 [$0.0002, $0.0004] | 858.8 | 1253.3 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0105 | $0.0003 [$0.0002, $0.0004] | 4222.5 | 24049.2 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0102 | $0.0003 [$0.0002, $0.0004] | 10581.1 | 25683.8 | 1.00 | 1.00 |
| agentic | 100 | $0.0002 | $0.0152 | $0.0004 [$0.0003, $0.0006] | 10647.0 | 27453.8 | 2.18 | 1.18 |
| engine | 100 | $0.0002 | $0.0174 | $0.0002 [$0.0002, $0.0003] | 952.6 | 20844.2 | 1.07 | 1.07 |
| engine_single (exploratory) | 100 | $0.0002 | $0.0157 | $0.0002 [$0.0002, $0.0003] | 1015.7 | 3343.9 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0001 | $0.0107 | $0.0001 [$0.0001, $0.0002] | 2967.2 | 15243.4 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0002 | $0.0150 | $0.0002 [$0.0002, $0.0002] | 3001.2 | 23140.0 | 2.12 | 1.12 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.980 (100) |
| hybrid | n/a | n/a | n/a | 0.930 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.860 (100) |
| agentic | n/a | n/a | n/a | 0.940 (100) |
| engine | 94 | 0.920 | 1.000 | 1.000 (100) |
| engine_single (exploratory) | 83 | 0.942 | 1.000 | 0.990 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.940 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.930 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 1.410 [1.230, 1.570] | 0.0010 | 0.0050 |
| bm25 | 100 | 0.870 [0.650, 1.070] | 0.0010 | 0.0050 |
| hybrid | 100 | 0.810 [0.610, 1.000] | 0.0010 | 0.0050 |
| hybrid_rerank | 100 | 0.740 [0.540, 0.940] | 0.0010 | 0.0050 |
| agentic | 100 | 0.850 [0.630, 1.050] | 0.0010 | 0.0050 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 72 | 0 | 0.0000 | 0.0000 | 0.235 |
| bm25 | 100 | 48 | 3 | 0.0000 | 0.0000 | 0.198 |
| hybrid | 100 | 46 | 2 | 0.0000 | 0.0000 | 0.192 |
| hybrid_rerank | 100 | 48 | 4 | 0.0000 | 0.0000 | 0.200 |
| agentic | 100 | 45 | 3 | 0.0000 | 0.0000 | 0.192 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $-0.0001 [$-0.0002, $-0.0000] |
| agentic | $-0.0002 [$-0.0003, $-0.0001] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| engine_single | 100 | 0.110 [0.010, 0.210] | 0.0549 | 0.1648 | 12 | 1 | 0.0034 | 0.100 |
| hybrid+asof | 100 | 0.030 [-0.100, 0.150] | 0.7602 | 1.0000 | 11 | 6 | 0.3323 | 0.114 |
| agentic+asof | 100 | 0.000 [-0.120, 0.110] | 1.0000 | 1.0000 | 7 | 6 | 1.0000 | 0.100 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0000 | 6.0% | yes | -0.790 | yes |
| bm25 | $0.0001 | 33.0% | yes | -0.250 | yes |
| hybrid | $0.0001 | 34.0% | no | -0.190 | no |
| hybrid_rerank | $0.0001 | 34.0% | yes | -0.120 | yes |
| agentic | $0.0002 | 36.0% | yes | -0.230 | no |
| engine | $0.0002 | 78.0% | yes | 0.620 | yes |

