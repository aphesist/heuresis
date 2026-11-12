# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 30.0% [21.9%, 39.6%] | 23.0% [15.8%, 32.2%] | 47.0% [37.5%, 56.7%] | 0.070 [-0.086, 0.220] |
| bm25 | 100 | 54.0% [44.3%, 63.4%] | 7.0% [3.4%, 13.7%] | 39.0% [30.0%, 48.8%] | 0.470 [0.337, 0.598] |
| vector | 100 | 46.0% [36.6%, 55.7%] | 5.0% [2.2%, 11.2%] | 49.0% [39.4%, 58.7%] | 0.410 [0.293, 0.516] |
| hybrid | 100 | 48.0% [38.5%, 57.7%] | 13.0% [7.8%, 21.0%] | 39.0% [30.0%, 48.8%] | 0.350 [0.196, 0.488] |
| hybrid_rerank | 100 | 43.0% [33.7%, 52.8%] | 10.0% [5.5%, 17.4%] | 47.0% [37.5%, 56.7%] | 0.330 [0.207, 0.450] |
| agentic | 100 | 34.0% [25.5%, 43.7%] | 36.0% [27.3%, 45.8%] | 30.0% [21.9%, 39.6%] | -0.020 [-0.221, 0.155] |
| engine | 100 | 25.0% [17.5%, 34.3%] | 12.0% [7.0%, 19.8%] | 63.0% [53.2%, 71.8%] | 0.130 [0.011, 0.247] |
| oracle | 100 | 55.0% [45.2%, 64.4%] | 9.0% [4.8%, 16.2%] | 36.0% [27.3%, 45.8%] | 0.460 [0.306, 0.610] |
| bm25+asof (exploratory) | 100 | 49.0% [39.4%, 58.7%] | 13.0% [7.8%, 21.0%] | 38.0% [29.1%, 47.8%] | 0.360 [0.212, 0.500] |
| vector+asof (exploratory) | 100 | 41.0% [31.9%, 50.8%] | 9.0% [4.8%, 16.2%] | 50.0% [40.4%, 59.6%] | 0.320 [0.176, 0.448] |
| hybrid+asof (exploratory) | 100 | 50.0% [40.4%, 59.6%] | 11.0% [6.3%, 18.6%] | 39.0% [30.0%, 48.8%] | 0.390 [0.261, 0.513] |
| hybrid_rerank+asof (exploratory) | 100 | 43.0% [33.7%, 52.8%] | 11.0% [6.3%, 18.6%] | 46.0% [36.6%, 55.7%] | 0.320 [0.181, 0.442] |
| agentic+asof (exploratory) | 100 | 37.0% [28.2%, 46.8%] | 36.0% [27.3%, 45.8%] | 27.0% [19.3%, 36.4%] | 0.010 [-0.191, 0.202] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 30.0% | 46.0% | 50.0% | 0.170 | 58.3% (n=12) | 281.9 |
| bm25 | 100 | 54.0% | 49.0% | 85.7% | 0.060 | 100.0% (n=12) | 335.0 |
| vector | 100 | 46.0% | 39.0% | 87.2% | 0.041 | 100.0% (n=12) | 294.5 |
| hybrid | 100 | 48.0% | 49.0% | 73.5% | 0.111 | 100.0% (n=12) | 315.4 |
| hybrid_rerank | 100 | 43.0% | 41.0% | 75.6% | 0.126 | 100.0% (n=12) | 325.8 |
| agentic | 100 | 34.0% | 60.0% | 40.0% | 0.411 | 83.3% (n=12) | 403.2 |
| engine | 100 | 25.0% | 25.0% | 52.0% | 0.560 | 100.0% (n=12) | 223.2 |
| oracle | 100 | 55.0% | 52.0% | 82.7% | 0.039 | 100.0% (n=12) | 274.7 |
| bm25+asof (exploratory) | 100 | 49.0% | 50.0% | 74.0% | 0.098 | 100.0% (n=12) | 336.5 |
| vector+asof (exploratory) | 100 | 41.0% | 38.0% | 76.3% | 0.126 | 100.0% (n=12) | 301.3 |
| hybrid+asof (exploratory) | 100 | 50.0% | 49.0% | 77.6% | 0.091 | 100.0% (n=12) | 313.5 |
| hybrid_rerank+asof (exploratory) | 100 | 43.0% | 42.0% | 73.8% | 0.131 | 100.0% (n=12) | 313.1 |
| agentic+asof (exploratory) | 100 | 37.0% | 63.0% | 42.9% | 0.339 | 83.3% (n=12) | 395.4 |

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
| closed_book | 100 | $0.0000 | $0.0050 | $0.0002 [$0.0001, $0.0003] | 790.3 | 1146.6 | 1.00 | 0.00 |
| bm25 | 100 | $0.0005 | $0.0461 | $0.0009 [$0.0007, $0.0010] | 935.0 | 1285.6 | 1.00 | 1.00 |
| vector | 100 | $0.0004 | $0.0445 | $0.0010 [$0.0008, $0.0012] | 991.3 | 1493.2 | 1.00 | 1.00 |
| hybrid | 100 | $0.0005 | $0.0459 | $0.0010 [$0.0008, $0.0012] | 1111.1 | 1546.5 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0005 | $0.0463 | $0.0011 [$0.0009, $0.0014] | 13986.9 | 16979.8 | 1.00 | 1.00 |
| agentic | 100 | $0.0006 | $0.0561 | $0.0017 [$0.0012, $0.0026] | 1959.7 | 3312.2 | 2.35 | 1.35 |
| engine | 100 | $0.0005 | $0.0535 | $0.0021 [$0.0016, $0.0032] | 5092.4 | 10432.5 | 1.00 | 1.00 |
| oracle | 100 | $0.0002 | $0.0162 | $0.0003 [$0.0002, $0.0004] | 823.2 | 1231.7 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0005 | $0.0462 | $0.0009 [$0.0008, $0.0012] | 924.2 | 1401.2 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0004 | $0.0445 | $0.0011 [$0.0009, $0.0015] | 1054.3 | 1473.1 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0005 | $0.0459 | $0.0009 [$0.0008, $0.0011] | 1174.6 | 1653.1 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0005 | $0.0463 | $0.0011 [$0.0009, $0.0014] | 13846.7 | 17746.6 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0006 | $0.0579 | $0.0016 [$0.0012, $0.0023] | 2174.7 | 3301.9 | 2.39 | 1.39 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.589 (88) |
| vector | n/a | n/a | n/a | 0.406 (88) |
| hybrid | n/a | n/a | n/a | 0.576 (88) |
| hybrid_rerank | n/a | n/a | n/a | 0.422 (88) |
| agentic | n/a | n/a | n/a | 0.470 (88) |
| engine | 25 | 0.613 | 0.483 | 0.594 (88) |
| oracle | n/a | n/a | n/a | 1.000 (88) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 0.589 (88) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.406 (88) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.576 (88) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.422 (88) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.483 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.060 [-0.100, 0.235] | 0.5624 | 0.5624 |
| bm25 | 100 | -0.340 [-0.470, -0.198] | 0.0010 | 0.0060 |
| vector | 100 | -0.280 [-0.414, -0.130] | 0.0010 | 0.0060 |
| hybrid | 100 | -0.220 [-0.370, -0.057] | 0.0170 | 0.0509 |
| hybrid_rerank | 100 | -0.200 [-0.333, -0.067] | 0.0110 | 0.0440 |
| agentic | 100 | 0.150 [-0.027, 0.354] | 0.1419 | 0.2837 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 8 | 13 | 0.3833 | 0.3833 | 0.127 |
| bm25 | 100 | 2 | 31 | 0.0000 | 0.0000 | 0.159 |
| vector | 100 | 5 | 26 | 0.0002 | 0.0008 | 0.154 |
| hybrid | 100 | 2 | 25 | 0.0000 | 0.0000 | 0.144 |
| hybrid_rerank | 100 | 3 | 21 | 0.0003 | 0.0008 | 0.136 |
| agentic | 100 | 5 | 14 | 0.0636 | 0.1271 | 0.121 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0012 [$0.0007, $0.0022] |
| agentic | $0.0005 [$-0.0003, $0.0012] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | -0.230 [-0.364, -0.081] | 0.0110 | 0.0440 | 2 | 26 | 0.0000 | 0.147 |
| vector+asof | 100 | -0.190 [-0.330, -0.022] | 0.0330 | 0.0659 | 6 | 22 | 0.0037 | 0.147 |
| hybrid+asof | 100 | -0.260 [-0.398, -0.121] | 0.0030 | 0.0150 | 3 | 28 | 0.0000 | 0.154 |
| hybrid_rerank+asof | 100 | -0.190 [-0.323, -0.045] | 0.0170 | 0.0509 | 4 | 22 | 0.0005 | 0.141 |
| agentic+asof | 100 | 0.120 [-0.065, 0.304] | 0.2767 | 0.2767 | 4 | 16 | 0.0118 | 0.124 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0000 | 30.0% | yes | 0.070 | yes |
| bm25 | $0.0005 | 54.0% | yes | 0.470 | yes |
| vector | $0.0004 | 46.0% | yes | 0.410 | yes |
| hybrid | $0.0005 | 48.0% | yes | 0.350 | no |
| hybrid_rerank | $0.0005 | 43.0% | no | 0.330 | no |
| agentic | $0.0006 | 34.0% | no | -0.020 | no |
| engine | $0.0005 | 25.0% | no | 0.130 | no |

