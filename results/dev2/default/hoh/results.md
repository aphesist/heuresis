# Results: hoh, split `dev2`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 5.0% [2.2%, 11.2%] | 40.0% [30.9%, 49.8%] | 55.0% [45.2%, 64.4%] | -0.350 [-0.460, -0.240] |
| bm25 | 100 | 36.0% [27.3%, 45.8%] | 56.0% [46.2%, 65.3%] | 8.0% [4.1%, 15.0%] | -0.200 [-0.370, -0.010] |
| hybrid | 100 | 34.0% [25.5%, 43.7%] | 55.0% [45.2%, 64.4%] | 11.0% [6.3%, 18.6%] | -0.210 [-0.380, -0.020] |
| hybrid_rerank | 100 | 32.0% [23.7%, 41.7%] | 50.0% [40.4%, 59.6%] | 18.0% [11.7%, 26.7%] | -0.180 [-0.350, -0.010] |
| agentic | 100 | 37.0% [28.2%, 46.8%] | 58.0% [48.2%, 67.2%] | 5.0% [2.2%, 11.2%] | -0.210 [-0.380, -0.030] |
| engine | 100 | 77.0% [67.8%, 84.2%] | 19.0% [12.5%, 27.8%] | 4.0% [1.6%, 9.8%] | 0.580 [0.430, 0.730] |
| engine_single (exploratory) | 100 | 70.0% [60.4%, 78.1%] | 15.0% [9.3%, 23.3%] | 15.0% [9.3%, 23.3%] | 0.550 [0.390, 0.680] |
| hybrid+asof (exploratory) | 100 | 74.0% [64.6%, 81.6%] | 15.0% [9.3%, 23.3%] | 11.0% [6.3%, 18.6%] | 0.590 [0.440, 0.730] |
| agentic+asof (exploratory) | 100 | 83.0% [74.5%, 89.1%] | 12.0% [7.0%, 19.8%] | 5.0% [2.2%, 11.2%] | 0.710 [0.580, 0.840] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 40 | 3 | 8.0% [4.1%, 15.0%] | -0.290 [-0.400, -0.170] | -0.350 [-0.460, -0.240] |
| bm25 | 100 | 56 | 12 | 48.0% [38.5%, 57.7%] | 0.040 [-0.130, 0.230] | -0.200 [-0.370, -0.010] |
| hybrid | 100 | 55 | 11 | 45.0% [35.6%, 54.8%] | 0.010 [-0.160, 0.190] | -0.210 [-0.380, -0.020] |
| hybrid_rerank | 100 | 50 | 11 | 43.0% [33.7%, 52.8%] | 0.040 [-0.130, 0.220] | -0.180 [-0.350, -0.010] |
| agentic | 100 | 58 | 13 | 50.0% [40.4%, 59.6%] | 0.050 [-0.130, 0.250] | -0.210 [-0.380, -0.030] |
| engine | 100 | 19 | 13 | 90.0% [82.6%, 94.5%] | 0.840 [0.730, 0.930] | 0.580 [0.430, 0.730] |
| engine_single (exploratory) | 100 | 15 | 11 | 81.0% [72.2%, 87.5%] | 0.770 [0.660, 0.870] | 0.550 [0.390, 0.680] |
| hybrid+asof (exploratory) | 100 | 15 | 12 | 86.0% [77.9%, 91.5%] | 0.830 [0.730, 0.920] | 0.590 [0.440, 0.730] |
| agentic+asof (exploratory) | 100 | 12 | 9 | 92.0% [85.0%, 95.9%] | 0.890 [0.800, 0.960] | 0.710 [0.580, 0.840] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 5.0% | 45.0% | 11.1% | 0.844 | n/a (n=0) | 189.8 |
| bm25 | 100 | 36.0% | 92.0% | 39.1% | 0.713 | n/a (n=0) | 107.4 |
| hybrid | 100 | 34.0% | 89.0% | 38.2% | 0.608 | n/a (n=0) | 113.3 |
| hybrid_rerank | 100 | 32.0% | 82.0% | 39.0% | 0.640 | n/a (n=0) | 108.3 |
| agentic | 100 | 37.0% | 95.0% | 38.9% | 0.611 | n/a (n=0) | 123.4 |
| engine | 100 | 77.0% | 96.0% | 80.2% | 0.145 | n/a (n=0) | 95.4 |
| engine_single (exploratory) | 100 | 70.0% | 85.0% | 82.4% | 0.141 | n/a (n=0) | 84.4 |
| hybrid+asof (exploratory) | 100 | 74.0% | 89.0% | 83.1% | 0.184 | n/a (n=0) | 106.1 |
| agentic+asof (exploratory) | 100 | 83.0% | 95.0% | 87.4% | 0.090 | n/a (n=0) | 132.1 |

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
| closed_book | 100 | $0.0002 | $0.0206 | $0.0041 [$0.0022, $0.0198] | 2048.3 | 4164.0 | 1.00 | 0.00 |
| bm25 | 100 | $0.0001 | $0.0143 | $0.0004 [$0.0003, $0.0005] | 1130.0 | 2050.9 | 1.00 | 1.00 |
| hybrid | 100 | $0.0002 | $0.0157 | $0.0005 [$0.0004, $0.0006] | 2729.0 | 18818.9 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0146 | $0.0005 [$0.0004, $0.0006] | 4035.2 | 20711.7 | 1.00 | 1.00 |
| agentic | 100 | $0.0002 | $0.0243 | $0.0007 [$0.0005, $0.0009] | 4787.3 | 23534.9 | 2.37 | 1.37 |
| engine | 100 | $0.0003 | $0.0265 | $0.0003 [$0.0003, $0.0005] | 1188.9 | 10577.9 | 1.18 | 1.18 |
| engine_single (exploratory) | 100 | $0.0002 | $0.0181 | $0.0003 [$0.0002, $0.0003] | 1083.9 | 3260.7 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0002 | $0.0157 | $0.0002 [$0.0002, $0.0002] | 2572.7 | 7173.0 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0002 | $0.0238 | $0.0003 [$0.0002, $0.0003] | 3103.0 | 11756.2 | 2.27 | 1.27 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.980 (100) |
| hybrid | n/a | n/a | n/a | 0.930 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.860 (100) |
| agentic | n/a | n/a | n/a | 0.980 (100) |
| engine | 96 | 0.927 | 1.000 | 1.000 (100) |
| engine_single (exploratory) | 85 | 0.941 | 1.000 | 0.990 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.940 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.960 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.930 [0.760, 1.100] | 0.0010 | 0.0050 |
| bm25 | 100 | 0.780 [0.570, 0.970] | 0.0010 | 0.0050 |
| hybrid | 100 | 0.790 [0.600, 0.970] | 0.0010 | 0.0050 |
| hybrid_rerank | 100 | 0.760 [0.580, 0.950] | 0.0010 | 0.0050 |
| agentic | 100 | 0.790 [0.590, 0.990] | 0.0010 | 0.0050 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 72 | 0 | 0.0000 | 0.0000 | 0.235 |
| bm25 | 100 | 43 | 2 | 0.0000 | 0.0000 | 0.186 |
| hybrid | 100 | 43 | 0 | 0.0000 | 0.0000 | 0.182 |
| hybrid_rerank | 100 | 46 | 1 | 0.0000 | 0.0000 | 0.190 |
| agentic | 100 | 41 | 1 | 0.0000 | 0.0000 | 0.179 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $-0.0001 [$-0.0003, $-0.0000] |
| agentic | $-0.0003 [$-0.0006, $-0.0002] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| engine_single | 100 | 0.030 [-0.070, 0.140] | 0.7183 | 1.0000 | 10 | 3 | 0.0923 | 0.100 |
| hybrid+asof | 100 | -0.010 [-0.130, 0.110] | 1.0000 | 1.0000 | 9 | 6 | 0.6072 | 0.107 |
| agentic+asof | 100 | -0.130 [-0.250, -0.010] | 0.0450 | 0.1349 | 3 | 9 | 0.1460 | 0.096 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 5.0% | no | -0.350 | no |
| bm25 | $0.0001 | 36.0% | yes | -0.200 | yes |
| hybrid | $0.0002 | 34.0% | no | -0.210 | no |
| hybrid_rerank | $0.0001 | 32.0% | no | -0.180 | yes |
| agentic | $0.0002 | 37.0% | yes | -0.210 | no |
| engine | $0.0003 | 77.0% | yes | 0.580 | yes |

