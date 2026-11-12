# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 21.0% [14.2%, 30.0%] | 73.0% [63.6%, 80.7%] | 6.0% [2.8%, 12.5%] | -0.520 [-0.673, -0.356] |
| bm25 | 100 | 19.0% [12.5%, 27.8%] | 24.0% [16.7%, 33.2%] | 57.0% [47.2%, 66.3%] | -0.050 [-0.168, 0.067] |
| vector | 100 | 24.0% [16.7%, 33.2%] | 22.0% [15.0%, 31.1%] | 54.0% [44.3%, 63.4%] | 0.020 [-0.118, 0.140] |
| hybrid | 100 | 25.0% [17.5%, 34.3%] | 23.0% [15.8%, 32.2%] | 52.0% [42.3%, 61.5%] | 0.020 [-0.119, 0.153] |
| hybrid_rerank | 100 | 23.0% [15.8%, 32.2%] | 25.0% [17.5%, 34.3%] | 52.0% [42.3%, 61.5%] | -0.020 [-0.155, 0.102] |
| agentic | 100 | 42.0% [32.8%, 51.8%] | 35.0% [26.4%, 44.7%] | 23.0% [15.8%, 32.2%] | 0.070 [-0.108, 0.230] |
| engine | 100 | 16.0% [10.1%, 24.4%] | 11.0% [6.3%, 18.6%] | 73.0% [63.6%, 80.7%] | 0.050 [-0.049, 0.144] |
| oracle | 100 | 64.0% [54.2%, 72.7%] | 10.0% [5.5%, 17.4%] | 26.0% [18.4%, 35.4%] | 0.540 [0.402, 0.674] |
| bm25+asof (exploratory) | 100 | 21.0% [14.2%, 30.0%] | 21.0% [14.2%, 30.0%] | 58.0% [48.2%, 67.2%] | 0.000 [-0.124, 0.119] |
| vector+asof (exploratory) | 100 | 25.0% [17.5%, 34.3%] | 20.0% [13.3%, 28.9%] | 55.0% [45.2%, 64.4%] | 0.050 [-0.080, 0.174] |
| hybrid+asof (exploratory) | 100 | 26.0% [18.4%, 35.4%] | 23.0% [15.8%, 32.2%] | 51.0% [41.3%, 60.6%] | 0.030 [-0.102, 0.155] |
| hybrid_rerank+asof (exploratory) | 100 | 27.0% [19.3%, 36.4%] | 25.0% [17.5%, 34.3%] | 48.0% [38.5%, 57.7%] | 0.020 [-0.132, 0.158] |
| agentic+asof (exploratory) | 100 | 47.0% [37.5%, 56.7%] | 31.0% [22.8%, 40.6%] | 22.0% [15.0%, 31.1%] | 0.160 [-0.010, 0.333] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 73 | 5 | 26.0% [18.4%, 35.4%] | -0.420 [-0.574, -0.242] | -0.520 [-0.673, -0.356] |
| bm25 | 100 | 24 | 2 | 21.0% [14.2%, 30.0%] | -0.010 [-0.131, 0.115] | -0.050 [-0.168, 0.067] |
| vector | 100 | 22 | 1 | 25.0% [17.5%, 34.3%] | 0.040 [-0.096, 0.168] | 0.020 [-0.118, 0.140] |
| hybrid | 100 | 23 | 1 | 26.0% [18.4%, 35.4%] | 0.040 [-0.097, 0.176] | 0.020 [-0.119, 0.153] |
| hybrid_rerank | 100 | 25 | 2 | 25.0% [17.5%, 34.3%] | 0.020 [-0.113, 0.152] | -0.020 [-0.155, 0.102] |
| agentic | 100 | 35 | 1 | 43.0% [33.7%, 52.8%] | 0.090 [-0.080, 0.255] | 0.070 [-0.108, 0.230] |
| engine | 100 | 11 | 1 | 17.0% [10.9%, 25.5%] | 0.070 [-0.020, 0.170] | 0.050 [-0.049, 0.144] |
| oracle | 100 | 10 | 4 | 68.0% [58.3%, 76.3%] | 0.620 [0.490, 0.732] | 0.540 [0.402, 0.674] |
| bm25+asof (exploratory) | 100 | 21 | 0 | 21.0% [14.2%, 30.0%] | 0.000 [-0.124, 0.119] | 0.000 [-0.124, 0.119] |
| vector+asof (exploratory) | 100 | 20 | 1 | 26.0% [18.4%, 35.4%] | 0.070 [-0.061, 0.202] | 0.050 [-0.080, 0.174] |
| hybrid+asof (exploratory) | 100 | 23 | 1 | 27.0% [19.3%, 36.4%] | 0.050 [-0.080, 0.183] | 0.030 [-0.102, 0.155] |
| hybrid_rerank+asof (exploratory) | 100 | 25 | 0 | 27.0% [19.3%, 36.4%] | 0.020 [-0.132, 0.158] | 0.020 [-0.132, 0.158] |
| agentic+asof (exploratory) | 100 | 31 | 3 | 50.0% [40.4%, 59.6%] | 0.220 [0.039, 0.378] | 0.160 [-0.010, 0.333] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 21.0% | 94.0% | 22.3% | 0.549 | n/a (n=0) | 306.4 |
| bm25 | 100 | 19.0% | 43.0% | 44.2% | 0.390 | n/a (n=0) | 207.5 |
| vector | 100 | 24.0% | 46.0% | 52.2% | 0.334 | n/a (n=0) | 194.8 |
| hybrid | 100 | 25.0% | 48.0% | 52.1% | 0.339 | n/a (n=0) | 195.8 |
| hybrid_rerank | 100 | 23.0% | 48.0% | 47.9% | 0.390 | n/a (n=0) | 221.4 |
| agentic | 100 | 42.0% | 77.0% | 54.5% | 0.175 | n/a (n=0) | 277.1 |
| engine | 100 | 16.0% | 27.0% | 59.3% | 0.518 | n/a (n=0) | 139.7 |
| oracle | 100 | 64.0% | 74.0% | 86.5% | 0.127 | n/a (n=0) | 195.2 |
| bm25+asof (exploratory) | 100 | 21.0% | 42.0% | 50.0% | 0.359 | n/a (n=0) | 210.7 |
| vector+asof (exploratory) | 100 | 25.0% | 45.0% | 55.6% | 0.261 | n/a (n=0) | 205.2 |
| hybrid+asof (exploratory) | 100 | 26.0% | 49.0% | 53.1% | 0.278 | n/a (n=0) | 207.9 |
| hybrid_rerank+asof (exploratory) | 100 | 27.0% | 52.0% | 51.9% | 0.343 | n/a (n=0) | 231.7 |
| agentic+asof (exploratory) | 100 | 47.0% | 78.0% | 60.3% | 0.141 | n/a (n=0) | 271.1 |

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
| closed_book | 100 | $0.0001 | $0.0070 | $0.0003 [$0.0002, $0.0005] | 1003.3 | 1524.8 | 1.00 | 0.00 |
| bm25 | 100 | $0.0002 | $0.0215 | $0.0011 [$0.0008, $0.0018] | 820.3 | 1172.4 | 1.00 | 1.00 |
| vector | 100 | $0.0002 | $0.0205 | $0.0009 [$0.0006, $0.0013] | 965.7 | 1294.1 | 1.00 | 1.00 |
| hybrid | 100 | $0.0002 | $0.0209 | $0.0008 [$0.0006, $0.0012] | 1048.9 | 1329.7 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0002 | $0.0222 | $0.0010 [$0.0007, $0.0015] | 4168.5 | 6408.3 | 1.00 | 1.00 |
| agentic | 100 | $0.0005 | $0.0454 | $0.0011 [$0.0009, $0.0014] | 2713.9 | 4177.0 | 2.99 | 1.99 |
| engine | 100 | $0.0003 | $0.0289 | $0.0018 [$0.0013, $0.0032] | 1404.8 | 3132.4 | 1.00 | 1.00 |
| oracle | 100 | $0.0001 | $0.0107 | $0.0002 [$0.0001, $0.0002] | 768.3 | 1142.3 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0002 | $0.0215 | $0.0010 [$0.0007, $0.0016] | 797.8 | 1112.1 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0002 | $0.0206 | $0.0008 [$0.0006, $0.0012] | 1023.8 | 1445.9 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0002 | $0.0211 | $0.0008 [$0.0006, $0.0012] | 1030.0 | 1462.2 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0002 | $0.0224 | $0.0008 [$0.0006, $0.0013] | 3734.1 | 6536.0 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0005 | $0.0471 | $0.0010 [$0.0008, $0.0013] | 2807.2 | 3881.1 | 3.02 | 2.02 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.506 (100) |
| vector | n/a | n/a | n/a | 0.473 (100) |
| hybrid | n/a | n/a | n/a | 0.526 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.576 (100) |
| agentic | n/a | n/a | n/a | 0.672 (100) |
| engine | 27 | 0.864 | 0.515 | 0.522 (100) |
| oracle | n/a | n/a | n/a | 1.000 (100) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 0.506 (100) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.473 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.526 (100) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.576 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.698 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.570 [0.404, 0.735] | 0.0010 | 0.0060 |
| bm25 | 100 | 0.100 [-0.020, 0.226] | 0.1469 | 0.7343 |
| vector | 100 | 0.030 [-0.093, 0.160] | 0.7532 | 1.0000 |
| hybrid | 100 | 0.030 [-0.087, 0.146] | 0.7383 | 1.0000 |
| hybrid_rerank | 100 | 0.070 [-0.071, 0.210] | 0.3816 | 1.0000 |
| agentic | 100 | -0.020 [-0.196, 0.153] | 0.9261 | 1.0000 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 10 | 15 | 0.4244 | 0.8487 | 0.138 |
| bm25 | 100 | 9 | 12 | 0.6636 | 0.8487 | 0.127 |
| vector | 100 | 6 | 14 | 0.1153 | 0.4613 | 0.124 |
| hybrid | 100 | 3 | 12 | 0.0352 | 0.1758 | 0.107 |
| hybrid_rerank | 100 | 9 | 16 | 0.2295 | 0.6886 | 0.138 |
| agentic | 100 | 4 | 30 | 0.0000 | 0.0000 | 0.161 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0010 [$0.0005, $0.0022] |
| agentic | $0.0007 [$0.0001, $0.0021] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | 0.050 [-0.086, 0.182] | 0.5634 | 1.0000 | 9 | 14 | 0.4049 | 0.133 |
| vector+asof | 100 | 0.000 [-0.133, 0.140] | 1.0000 | 1.0000 | 6 | 15 | 0.0784 | 0.127 |
| hybrid+asof | 100 | 0.020 [-0.089, 0.129] | 0.8631 | 1.0000 | 3 | 13 | 0.0213 | 0.111 |
| hybrid_rerank+asof | 100 | 0.030 [-0.119, 0.175] | 0.7962 | 1.0000 | 6 | 17 | 0.0347 | 0.133 |
| agentic+asof | 100 | -0.110 [-0.292, 0.059] | 0.2687 | 1.0000 | 5 | 36 | 0.0000 | 0.177 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0001 | 21.0% | yes | -0.520 | yes |
| bm25 | $0.0002 | 19.0% | no | -0.050 | no |
| vector | $0.0002 | 24.0% | yes | 0.020 | yes |
| hybrid | $0.0002 | 25.0% | yes | 0.020 | no |
| hybrid_rerank | $0.0002 | 23.0% | no | -0.020 | no |
| agentic | $0.0005 | 42.0% | yes | 0.070 | yes |
| engine | $0.0003 | 16.0% | no | 0.050 | yes |

