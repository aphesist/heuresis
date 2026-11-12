# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 24.0% [16.7%, 33.2%] | 18.0% [11.7%, 26.7%] | 58.0% [48.2%, 67.2%] | 0.060 [-0.069, 0.186] |
| bm25 | 100 | 18.0% [11.7%, 26.7%] | 4.0% [1.6%, 9.8%] | 78.0% [68.9%, 85.0%] | 0.140 [0.051, 0.232] |
| vector | 100 | 20.0% [13.3%, 28.9%] | 6.0% [2.8%, 12.5%] | 74.0% [64.6%, 81.6%] | 0.140 [0.042, 0.235] |
| hybrid | 100 | 24.0% [16.7%, 33.2%] | 6.0% [2.8%, 12.5%] | 70.0% [60.4%, 78.1%] | 0.180 [0.079, 0.273] |
| hybrid_rerank | 100 | 27.0% [19.3%, 36.4%] | 6.0% [2.8%, 12.5%] | 67.0% [57.3%, 75.4%] | 0.210 [0.110, 0.313] |
| agentic | 100 | 50.0% [40.4%, 59.6%] | 14.0% [8.5%, 22.1%] | 36.0% [27.3%, 45.8%] | 0.360 [0.214, 0.505] |
| engine | 100 | 8.0% [4.1%, 15.0%] | 6.0% [2.8%, 12.5%] | 86.0% [77.9%, 91.5%] | 0.020 [-0.059, 0.094] |
| oracle | 100 | 61.0% [51.2%, 70.0%] | 5.0% [2.2%, 11.2%] | 34.0% [25.5%, 43.7%] | 0.560 [0.437, 0.676] |
| bm25+asof (exploratory) | 100 | 18.0% [11.7%, 26.7%] | 3.0% [1.0%, 8.5%] | 79.0% [70.0%, 85.8%] | 0.150 [0.059, 0.235] |
| vector+asof (exploratory) | 100 | 20.0% [13.3%, 28.9%] | 7.0% [3.4%, 13.7%] | 73.0% [63.6%, 80.7%] | 0.130 [0.038, 0.229] |
| hybrid+asof (exploratory) | 100 | 21.0% [14.2%, 30.0%] | 7.0% [3.4%, 13.7%] | 72.0% [62.5%, 79.9%] | 0.140 [0.039, 0.240] |
| hybrid_rerank+asof (exploratory) | 100 | 25.0% [17.5%, 34.3%] | 6.0% [2.8%, 12.5%] | 69.0% [59.4%, 77.2%] | 0.190 [0.088, 0.290] |
| agentic+asof (exploratory) | 100 | 47.0% [37.5%, 56.7%] | 12.0% [7.0%, 19.8%] | 41.0% [31.9%, 50.8%] | 0.350 [0.210, 0.490] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 24.0% | 42.0% | 57.1% | 0.311 | n/a (n=0) | 184.8 |
| bm25 | 100 | 18.0% | 22.0% | 81.8% | 0.024 | n/a (n=0) | 157.8 |
| vector | 100 | 20.0% | 26.0% | 76.9% | 0.045 | n/a (n=0) | 163.2 |
| hybrid | 100 | 24.0% | 30.0% | 80.0% | 0.051 | n/a (n=0) | 154.7 |
| hybrid_rerank | 100 | 27.0% | 33.0% | 81.8% | 0.066 | n/a (n=0) | 157.6 |
| agentic | 100 | 50.0% | 64.0% | 78.1% | 0.074 | n/a (n=0) | 197.7 |
| engine | 100 | 8.0% | 14.0% | 57.1% | 0.455 | n/a (n=0) | 92.1 |
| oracle | 100 | 61.0% | 66.0% | 92.4% | 0.026 | n/a (n=0) | 165.4 |
| bm25+asof (exploratory) | 100 | 18.0% | 21.0% | 85.7% | 0.059 | n/a (n=0) | 149.1 |
| vector+asof (exploratory) | 100 | 20.0% | 27.0% | 74.1% | 0.063 | n/a (n=0) | 158.1 |
| hybrid+asof (exploratory) | 100 | 21.0% | 28.0% | 75.0% | 0.066 | n/a (n=0) | 144.3 |
| hybrid_rerank+asof (exploratory) | 100 | 25.0% | 31.0% | 80.6% | 0.065 | n/a (n=0) | 178.0 |
| agentic+asof (exploratory) | 100 | 47.0% | 59.0% | 79.7% | 0.052 | n/a (n=0) | 194.3 |

## Table 2b. Errors (split `dev`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 100 | 0 | 0 |
| bm25 | 100 | 0 | 0 |
| vector | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| hybrid_rerank | 100 | 0 | 0 |
| agentic | 100 | 0 | 0 |
| engine | 100 | 0 | 0 |
| oracle | 100 | 0 | 0 |
| bm25+asof (exploratory) | 100 | 0 | 0 |
| vector+asof (exploratory) | 100 | 0 | 0 |
| hybrid+asof (exploratory) | 100 | 0 | 0 |
| hybrid_rerank+asof (exploratory) | 100 | 0 | 0 |
| agentic+asof (exploratory) | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | $0.0002 | $0.0248 | $0.0010 [$0.0007, $0.0016] | 2752.5 | 3459.7 | 1.00 | 0.00 |
| bm25 | 100 | $0.0003 | $0.0306 | $0.0017 [$0.0012, $0.0030] | 1348.2 | 3042.7 | 1.00 | 1.00 |
| vector | 100 | $0.0003 | $0.0290 | $0.0015 [$0.0010, $0.0023] | 1469.1 | 2847.9 | 1.00 | 1.00 |
| hybrid | 100 | $0.0003 | $0.0298 | $0.0012 [$0.0009, $0.0019] | 1447.9 | 3010.2 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0003 | $0.0324 | $0.0012 [$0.0009, $0.0017] | 3418.4 | 5247.1 | 1.00 | 1.00 |
| agentic | 100 | $0.0009 | $0.0877 | $0.0018 [$0.0014, $0.0023] | 5143.6 | 9400.1 | 3.46 | 2.46 |
| engine | 100 | $0.0004 | $0.0370 | $0.0046 [$0.0026, $0.0125] | 1816.2 | 3079.5 | 1.00 | 1.00 |
| oracle | 100 | $0.0002 | $0.0201 | $0.0003 [$0.0003, $0.0004] | 1437.4 | 2609.2 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0003 | $0.0304 | $0.0017 [$0.0012, $0.0029] | 1399.6 | 2734.2 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0003 | $0.0289 | $0.0014 [$0.0010, $0.0023] | 1391.9 | 2752.9 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0003 | $0.0296 | $0.0014 [$0.0010, $0.0022] | 1518.2 | 2978.1 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0003 | $0.0318 | $0.0013 [$0.0009, $0.0019] | 3361.8 | 5099.2 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0009 | $0.0892 | $0.0019 [$0.0015, $0.0025] | 5392.1 | 8967.5 | 3.52 | 2.52 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.506 (100) |
| vector | n/a | n/a | n/a | 0.473 (100) |
| hybrid | n/a | n/a | n/a | 0.526 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.576 (100) |
| agentic | n/a | n/a | n/a | 0.753 (100) |
| engine | 14 | 0.857 | 0.488 | 0.522 (100) |
| oracle | n/a | n/a | n/a | 1.000 (100) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 0.506 (100) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.473 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.526 (100) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.576 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.755 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | -0.040 [-0.180, 0.089] | 0.6494 | 0.6494 |
| bm25 | 100 | -0.120 [-0.228, -0.019] | 0.0420 | 0.1139 |
| vector | 100 | -0.120 [-0.223, -0.029] | 0.0380 | 0.1139 |
| hybrid | 100 | -0.160 [-0.255, -0.060] | 0.0030 | 0.0150 |
| hybrid_rerank | 100 | -0.190 [-0.296, -0.089] | 0.0040 | 0.0160 |
| agentic | 100 | -0.340 [-0.485, -0.189] | 0.0010 | 0.0060 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 4 | 20 | 0.0015 | 0.0046 | 0.136 |
| bm25 | 100 | 2 | 12 | 0.0129 | 0.0129 | 0.104 |
| vector | 100 | 2 | 14 | 0.0042 | 0.0084 | 0.111 |
| hybrid | 100 | 1 | 17 | 0.0001 | 0.0006 | 0.117 |
| hybrid_rerank | 100 | 2 | 21 | 0.0001 | 0.0003 | 0.133 |
| agentic | 100 | 0 | 42 | 0.0000 | 0.0000 | 0.179 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0034 [$0.0015, $0.0110] |
| agentic | $0.0029 [$0.0010, $0.0105] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | -0.130 [-0.224, -0.040] | 0.0090 | 0.0270 | 2 | 12 | 0.0129 | 0.104 |
| vector+asof | 100 | -0.110 [-0.214, -0.020] | 0.0559 | 0.0559 | 2 | 14 | 0.0042 | 0.111 |
| hybrid+asof | 100 | -0.120 [-0.214, -0.021] | 0.0190 | 0.0380 | 1 | 14 | 0.0010 | 0.107 |
| hybrid_rerank+asof | 100 | -0.170 [-0.276, -0.069] | 0.0060 | 0.0240 | 2 | 19 | 0.0002 | 0.127 |
| agentic+asof | 100 | -0.330 [-0.465, -0.196] | 0.0010 | 0.0050 | 1 | 40 | 0.0000 | 0.177 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 24.0% | yes | 0.060 | yes |
| bm25 | $0.0003 | 18.0% | no | 0.140 | no |
| vector | $0.0003 | 20.0% | no | 0.140 | yes |
| hybrid | $0.0003 | 24.0% | no | 0.180 | yes |
| hybrid_rerank | $0.0003 | 27.0% | yes | 0.210 | yes |
| agentic | $0.0009 | 50.0% | yes | 0.360 | yes |
| engine | $0.0004 | 8.0% | no | 0.020 | no |

