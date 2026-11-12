# Results: hoh, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 5.0% [2.2%, 11.2%] | 83.0% [74.5%, 89.1%] | 12.0% [7.0%, 19.8%] | -0.780 [-0.880, -0.670] |
| bm25 | 100 | 42.0% [32.8%, 51.8%] | 51.0% [41.3%, 60.6%] | 7.0% [3.4%, 13.7%] | -0.090 [-0.280, 0.080] |
| vector | 100 | 34.0% [25.5%, 43.7%] | 44.0% [34.7%, 53.8%] | 22.0% [15.0%, 31.1%] | -0.100 [-0.270, 0.070] |
| hybrid | 100 | 42.0% [32.8%, 51.8%] | 50.0% [40.4%, 59.6%] | 8.0% [4.1%, 15.0%] | -0.080 [-0.260, 0.090] |
| hybrid_rerank | 100 | 37.0% [28.2%, 46.8%] | 51.0% [41.3%, 60.6%] | 12.0% [7.0%, 19.8%] | -0.140 [-0.330, 0.030] |
| agentic | 100 | 44.0% [34.7%, 53.8%] | 51.0% [41.3%, 60.6%] | 5.0% [2.2%, 11.2%] | -0.070 [-0.250, 0.120] |
| engine | 100 | 80.0% [71.1%, 86.7%] | 7.0% [3.4%, 13.7%] | 13.0% [7.8%, 21.0%] | 0.730 [0.610, 0.830] |
| oracle | 100 | 84.0% [75.6%, 89.9%] | 8.0% [4.1%, 15.0%] | 8.0% [4.1%, 15.0%] | 0.760 [0.640, 0.870] |
| bm25+asof (exploratory) | 100 | 84.0% [75.6%, 89.9%] | 7.0% [3.4%, 13.7%] | 9.0% [4.8%, 16.2%] | 0.770 [0.650, 0.880] |
| vector+asof (exploratory) | 100 | 81.0% [72.2%, 87.5%] | 6.0% [2.8%, 12.5%] | 13.0% [7.8%, 21.0%] | 0.750 [0.630, 0.850] |
| hybrid+asof (exploratory) | 100 | 86.0% [77.9%, 91.5%] | 7.0% [3.4%, 13.7%] | 7.0% [3.4%, 13.7%] | 0.790 [0.670, 0.900] |
| hybrid_rerank+asof (exploratory) | 100 | 78.0% [68.9%, 85.0%] | 9.0% [4.8%, 16.2%] | 13.0% [7.8%, 21.0%] | 0.690 [0.570, 0.800] |
| agentic+asof (exploratory) | 100 | 84.0% [75.6%, 89.9%] | 9.0% [4.8%, 16.2%] | 7.0% [3.4%, 13.7%] | 0.750 [0.630, 0.860] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 5.0% | 88.0% | 5.7% | 0.829 | n/a (n=0) | 209.6 |
| bm25 | 100 | 42.0% | 93.0% | 45.2% | 0.583 | n/a (n=0) | 101.6 |
| vector | 100 | 34.0% | 78.0% | 43.6% | 0.559 | n/a (n=0) | 89.8 |
| hybrid | 100 | 42.0% | 92.0% | 45.7% | 0.604 | n/a (n=0) | 99.7 |
| hybrid_rerank | 100 | 37.0% | 88.0% | 42.0% | 0.577 | n/a (n=0) | 91.1 |
| agentic | 100 | 44.0% | 95.0% | 46.3% | 0.531 | n/a (n=0) | 132.3 |
| engine | 100 | 80.0% | 87.0% | 92.0% | 0.066 | n/a (n=0) | 86.8 |
| oracle | 100 | 84.0% | 92.0% | 91.3% | 0.105 | n/a (n=0) | 119.7 |
| bm25+asof (exploratory) | 100 | 84.0% | 91.0% | 92.3% | 0.080 | n/a (n=0) | 96.6 |
| vector+asof (exploratory) | 100 | 81.0% | 87.0% | 93.1% | 0.059 | n/a (n=0) | 95.2 |
| hybrid+asof (exploratory) | 100 | 86.0% | 93.0% | 92.5% | 0.083 | n/a (n=0) | 97.0 |
| hybrid_rerank+asof (exploratory) | 100 | 78.0% | 87.0% | 89.7% | 0.074 | n/a (n=0) | 98.0 |
| agentic+asof (exploratory) | 100 | 84.0% | 93.0% | 90.3% | 0.107 | n/a (n=0) | 139.7 |

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
| closed_book | 100 | $0.0001 | $0.0050 | $0.0010 [$0.0005, $0.0048] | 835.8 | 1184.2 | 1.00 | 0.00 |
| bm25 | 100 | $0.0001 | $0.0101 | $0.0002 [$0.0002, $0.0003] | 1010.7 | 1222.9 | 1.00 | 1.00 |
| vector | 100 | $0.0001 | $0.0107 | $0.0003 [$0.0002, $0.0004] | 3689.2 | 21514.6 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0106 | $0.0003 [$0.0002, $0.0003] | 6048.7 | 25114.9 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0102 | $0.0003 [$0.0002, $0.0004] | 9280.5 | 26044.6 | 1.00 | 1.00 |
| agentic | 100 | $0.0001 | $0.0150 | $0.0003 [$0.0003, $0.0004] | 10528.1 | 27481.2 | 2.15 | 1.15 |
| engine | 100 | $0.0002 | $0.0157 | $0.0002 [$0.0002, $0.0002] | 972.4 | 2392.6 | 1.00 | 1.00 |
| oracle | 100 | $0.0000 | $0.0049 | $0.0001 [$0.0001, $0.0001] | 738.3 | 983.8 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0001 | $0.0104 | $0.0001 [$0.0001, $0.0001] | 949.9 | 1189.3 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0001 | $0.0113 | $0.0001 [$0.0001, $0.0002] | 2818.5 | 13659.0 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0001 | $0.0109 | $0.0001 [$0.0001, $0.0001] | 2774.6 | 17569.0 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0001 | $0.0106 | $0.0001 [$0.0001, $0.0002] | 3881.4 | 19403.4 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0002 | $0.0154 | $0.0002 [$0.0002, $0.0002] | 3411.7 | 23910.9 | 2.14 | 1.14 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 1.000 (100) |
| vector | n/a | n/a | n/a | 0.870 (100) |
| hybrid | n/a | n/a | n/a | 0.980 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.910 (100) |
| agentic | n/a | n/a | n/a | 0.980 (100) |
| engine | 87 | 0.989 | 1.000 | 1.000 (100) |
| oracle | n/a | n/a | n/a | 1.000 (100) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 1.000 (100) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.920 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.980 (100) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.920 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.970 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 1.510 [1.340, 1.650] | 0.0010 | 0.0060 |
| bm25 | 100 | 0.820 [0.620, 1.020] | 0.0010 | 0.0060 |
| vector | 100 | 0.830 [0.640, 1.010] | 0.0010 | 0.0060 |
| hybrid | 100 | 0.810 [0.610, 1.010] | 0.0010 | 0.0060 |
| hybrid_rerank | 100 | 0.870 [0.660, 1.070] | 0.0010 | 0.0060 |
| agentic | 100 | 0.800 [0.600, 1.000] | 0.0010 | 0.0060 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 77 | 2 | 0.0000 | 0.0000 | 0.246 |
| bm25 | 100 | 43 | 5 | 0.0000 | 0.0000 | 0.192 |
| vector | 100 | 50 | 4 | 0.0000 | 0.0000 | 0.203 |
| hybrid | 100 | 45 | 7 | 0.0000 | 0.0000 | 0.200 |
| hybrid_rerank | 100 | 50 | 7 | 0.0000 | 0.0000 | 0.209 |
| agentic | 100 | 43 | 7 | 0.0000 | 0.0000 | 0.196 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $-0.0001 [$-0.0001, $-0.0000] |
| agentic | $-0.0001 [$-0.0002, $-0.0001] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | -0.040 [-0.130, 0.040] | 0.5045 | 1.0000 | 5 | 9 | 0.4240 | 0.104 |
| vector+asof | 100 | -0.020 [-0.120, 0.080] | 0.8511 | 1.0000 | 10 | 11 | 1.0000 | 0.127 |
| hybrid+asof | 100 | -0.060 [-0.150, 0.020] | 0.2717 | 1.0000 | 4 | 10 | 0.1796 | 0.104 |
| hybrid_rerank+asof | 100 | 0.040 [-0.040, 0.120] | 0.4665 | 1.0000 | 8 | 6 | 0.7905 | 0.104 |
| agentic+asof | 100 | -0.020 [-0.120, 0.070] | 0.8402 | 1.0000 | 5 | 9 | 0.4240 | 0.104 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0001 | 5.0% | yes | -0.780 | yes |
| bm25 | $0.0001 | 42.0% | yes | -0.090 | yes |
| vector | $0.0001 | 34.0% | no | -0.100 | no |
| hybrid | $0.0001 | 42.0% | no | -0.080 | yes |
| hybrid_rerank | $0.0001 | 37.0% | no | -0.140 | no |
| agentic | $0.0001 | 44.0% | yes | -0.070 | yes |
| engine | $0.0002 | 80.0% | yes | 0.730 | yes |

