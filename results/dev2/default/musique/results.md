# Results: musique, split `dev2`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 26.0% [18.4%, 35.4%] | 31.0% [22.8%, 40.6%] | 43.0% [33.7%, 52.8%] | -0.050 [-0.192, 0.108] |
| bm25 | 100 | 15.0% [9.3%, 23.3%] | 6.0% [2.8%, 12.5%] | 79.0% [70.0%, 85.8%] | 0.090 [0.010, 0.181] |
| hybrid | 100 | 21.0% [14.2%, 30.0%] | 5.0% [2.2%, 11.2%] | 74.0% [64.6%, 81.6%] | 0.160 [0.071, 0.258] |
| hybrid_rerank | 100 | 24.0% [16.7%, 33.2%] | 5.0% [2.2%, 11.2%] | 71.0% [61.5%, 79.0%] | 0.190 [0.091, 0.284] |
| agentic | 100 | 55.0% [45.2%, 64.4%] | 8.0% [4.1%, 15.0%] | 37.0% [28.2%, 46.8%] | 0.470 [0.350, 0.594] |
| engine | 100 | 47.0% [37.5%, 56.7%] | 21.0% [14.2%, 30.0%] | 32.0% [23.7%, 41.7%] | 0.260 [0.110, 0.406] |
| engine_single (exploratory) | 100 | 13.0% [7.8%, 21.0%] | 8.0% [4.1%, 15.0%] | 79.0% [70.0%, 85.8%] | 0.050 [-0.031, 0.133] |
| hybrid+asof (exploratory) | 100 | 20.0% [13.3%, 28.9%] | 7.0% [3.4%, 13.7%] | 73.0% [63.6%, 80.7%] | 0.130 [0.031, 0.226] |
| agentic+asof (exploratory) | 100 | 48.0% [38.5%, 57.7%] | 9.0% [4.8%, 16.2%] | 43.0% [33.7%, 52.8%] | 0.390 [0.268, 0.510] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 31 | 2 | 28.0% [20.1%, 37.5%] | -0.010 [-0.165, 0.137] | -0.050 [-0.192, 0.108] |
| bm25 | 100 | 6 | 2 | 17.0% [10.9%, 25.5%] | 0.130 [0.049, 0.218] | 0.090 [0.010, 0.181] |
| hybrid | 100 | 5 | 2 | 23.0% [15.8%, 32.2%] | 0.200 [0.118, 0.299] | 0.160 [0.071, 0.258] |
| hybrid_rerank | 100 | 5 | 1 | 25.0% [17.5%, 34.3%] | 0.210 [0.113, 0.306] | 0.190 [0.091, 0.284] |
| agentic | 100 | 8 | 5 | 60.0% [50.2%, 69.1%] | 0.570 [0.458, 0.684] | 0.470 [0.350, 0.594] |
| engine | 100 | 21 | 8 | 55.0% [45.2%, 64.4%] | 0.420 [0.277, 0.551] | 0.260 [0.110, 0.406] |
| engine_single (exploratory) | 100 | 8 | 0 | 13.0% [7.8%, 21.0%] | 0.050 [-0.031, 0.133] | 0.050 [-0.031, 0.133] |
| hybrid+asof (exploratory) | 100 | 7 | 2 | 22.0% [15.0%, 31.1%] | 0.170 [0.078, 0.268] | 0.130 [0.031, 0.226] |
| agentic+asof (exploratory) | 100 | 9 | 4 | 52.0% [42.3%, 61.5%] | 0.470 [0.356, 0.583] | 0.390 [0.268, 0.510] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 26.0% | 57.0% | 45.6% | 0.396 | n/a (n=0) | 202.8 |
| bm25 | 100 | 15.0% | 21.0% | 71.4% | 0.088 | n/a (n=0) | 170.1 |
| hybrid | 100 | 21.0% | 26.0% | 80.8% | 0.093 | n/a (n=0) | 190.0 |
| hybrid_rerank | 100 | 24.0% | 29.0% | 82.8% | 0.135 | n/a (n=0) | 192.9 |
| agentic | 100 | 55.0% | 63.0% | 87.3% | 0.042 | n/a (n=0) | 218.5 |
| engine | 100 | 47.0% | 68.0% | 69.1% | 0.210 | n/a (n=0) | 170.6 |
| engine_single (exploratory) | 100 | 13.0% | 21.0% | 61.9% | 0.270 | n/a (n=0) | 113.7 |
| hybrid+asof (exploratory) | 100 | 20.0% | 27.0% | 74.1% | 0.084 | n/a (n=0) | 179.4 |
| agentic+asof (exploratory) | 100 | 48.0% | 57.0% | 84.2% | 0.077 | n/a (n=0) | 210.4 |

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
| closed_book | 100 | $0.0003 | $0.0294 | $0.0011 [$0.0008, $0.0017] | 2771.2 | 5459.0 | 1.00 | 0.00 |
| bm25 | 100 | $0.0003 | $0.0311 | $0.0021 [$0.0014, $0.0037] | 1371.9 | 2907.0 | 1.00 | 1.00 |
| hybrid | 100 | $0.0003 | $0.0314 | $0.0015 [$0.0011, $0.0024] | 1528.6 | 3233.3 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0003 | $0.0331 | $0.0014 [$0.0010, $0.0020] | 3602.9 | 5321.5 | 1.00 | 1.00 |
| agentic | 100 | $0.0009 | $0.0921 | $0.0017 [$0.0013, $0.0021] | 5278.1 | 9341.3 | 3.53 | 2.53 |
| engine | 100 | $0.0018 | $0.1772 | $0.0038 [$0.0028, $0.0053] | 6232.4 | 13136.9 | 3.06 | 3.06 |
| engine_single (exploratory) | 100 | $0.0004 | $0.0412 | $0.0032 [$0.0020, $0.0058] | 1934.9 | 3742.1 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0003 | $0.0309 | $0.0015 [$0.0011, $0.0025] | 1519.1 | 3102.1 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0009 | $0.0938 | $0.0020 [$0.0015, $0.0026] | 5436.0 | 9249.4 | 3.55 | 2.55 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.495 (100) |
| hybrid | n/a | n/a | n/a | 0.534 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.552 (100) |
| agentic | n/a | n/a | n/a | 0.771 (100) |
| engine | 68 | 0.828 | 0.751 | 0.837 (100) |
| engine_single (exploratory) | 21 | 0.738 | 0.643 | 0.532 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.534 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.775 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.310 [0.139, 0.495] | 0.0040 | 0.0200 |
| bm25 | 100 | 0.170 [0.031, 0.305] | 0.0460 | 0.1379 |
| hybrid | 100 | 0.100 [-0.041, 0.242] | 0.2228 | 0.4456 |
| hybrid_rerank | 100 | 0.070 [-0.083, 0.214] | 0.4446 | 0.4456 |
| agentic | 100 | -0.210 [-0.351, -0.061] | 0.0180 | 0.0719 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 30 | 9 | 0.0011 | 0.0021 | 0.173 |
| bm25 | 100 | 33 | 1 | 0.0000 | 0.0000 | 0.161 |
| hybrid | 100 | 30 | 4 | 0.0000 | 0.0000 | 0.161 |
| hybrid_rerank | 100 | 30 | 7 | 0.0002 | 0.0006 | 0.168 |
| agentic | 100 | 11 | 19 | 0.2005 | 0.2005 | 0.152 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0023 [$0.0013, $0.0035] |
| agentic | $0.0021 [$0.0012, $0.0034] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| engine_single | 100 | 0.210 [0.062, 0.354] | 0.0130 | 0.0390 | 36 | 2 | 0.0000 | 0.171 |
| hybrid+asof | 100 | 0.130 [0.000, 0.263] | 0.0759 | 0.1518 | 29 | 2 | 0.0000 | 0.154 |
| agentic+asof | 100 | -0.130 [-0.280, 0.020] | 0.1109 | 0.1518 | 13 | 14 | 1.0000 | 0.144 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0003 | 26.0% | yes | -0.050 | yes |
| bm25 | $0.0003 | 15.0% | no | 0.090 | yes |
| hybrid | $0.0003 | 21.0% | no | 0.160 | yes |
| hybrid_rerank | $0.0003 | 24.0% | no | 0.190 | yes |
| agentic | $0.0009 | 55.0% | yes | 0.470 | yes |
| engine | $0.0018 | 47.0% | no | 0.260 | no |

