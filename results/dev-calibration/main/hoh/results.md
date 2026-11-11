# Results: hoh, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 7.0% [3.4%, 13.7%] | 43.0% [33.7%, 52.8%] | 50.0% [40.4%, 59.6%] | -0.360 [-0.470, -0.250] |
| bm25 | 100 | 41.0% [31.9%, 50.8%] | 51.0% [41.3%, 60.6%] | 8.0% [4.1%, 15.0%] | -0.100 [-0.280, 0.080] |
| vector | 100 | 37.0% [28.2%, 46.8%] | 45.0% [35.6%, 54.8%] | 18.0% [11.7%, 26.7%] | -0.080 [-0.260, 0.090] |
| hybrid | 100 | 40.0% [30.9%, 49.8%] | 52.0% [42.3%, 61.5%] | 8.0% [4.1%, 15.0%] | -0.120 [-0.300, 0.060] |
| hybrid_rerank | 100 | 36.0% [27.3%, 45.8%] | 51.0% [41.3%, 60.6%] | 13.0% [7.8%, 21.0%] | -0.150 [-0.330, 0.030] |
| agentic | 100 | 42.0% [32.8%, 51.8%] | 53.0% [43.3%, 62.5%] | 5.0% [2.2%, 11.2%] | -0.110 [-0.300, 0.070] |
| engine | 100 | 55.0% [45.2%, 64.4%] | 7.0% [3.4%, 13.7%] | 38.0% [29.1%, 47.8%] | 0.480 [0.350, 0.590] |
| oracle | 100 | 61.0% [51.2%, 70.0%] | 9.0% [4.8%, 16.2%] | 30.0% [21.9%, 39.6%] | 0.520 [0.380, 0.650] |
| bm25+asof (exploratory) | 100 | 86.0% [77.9%, 91.5%] | 9.0% [4.8%, 16.2%] | 5.0% [2.2%, 11.2%] | 0.770 [0.650, 0.880] |
| vector+asof (exploratory) | 100 | 79.0% [70.0%, 85.8%] | 9.0% [4.8%, 16.2%] | 12.0% [7.0%, 19.8%] | 0.700 [0.580, 0.830] |
| hybrid+asof (exploratory) | 100 | 84.0% [75.6%, 89.9%] | 7.0% [3.4%, 13.7%] | 9.0% [4.8%, 16.2%] | 0.770 [0.650, 0.870] |
| hybrid_rerank+asof (exploratory) | 100 | 80.0% [71.1%, 86.7%] | 9.0% [4.8%, 16.2%] | 11.0% [6.3%, 18.6%] | 0.710 [0.590, 0.830] |
| agentic+asof (exploratory) | 100 | 87.0% [79.0%, 92.2%] | 10.0% [5.5%, 17.4%] | 3.0% [1.0%, 8.5%] | 0.770 [0.650, 0.880] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 7.0% | 50.0% | 14.0% | 0.705 | n/a (n=0) | 182.9 |
| bm25 | 100 | 41.0% | 92.0% | 44.6% | 0.534 | n/a (n=0) | 94.4 |
| vector | 100 | 37.0% | 82.0% | 45.1% | 0.573 | n/a (n=0) | 95.8 |
| hybrid | 100 | 40.0% | 92.0% | 43.5% | 0.607 | n/a (n=0) | 102.8 |
| hybrid_rerank | 100 | 36.0% | 87.0% | 41.4% | 0.632 | n/a (n=0) | 95.9 |
| agentic | 100 | 42.0% | 95.0% | 44.2% | 0.569 | n/a (n=0) | 116.1 |
| engine | 100 | 55.0% | 62.0% | 88.7% | 0.108 | n/a (n=0) | 89.9 |
| oracle | 100 | 61.0% | 70.0% | 87.1% | 0.087 | n/a (n=0) | 96.9 |
| bm25+asof (exploratory) | 100 | 86.0% | 95.0% | 90.5% | 0.063 | n/a (n=0) | 100.8 |
| vector+asof (exploratory) | 100 | 79.0% | 88.0% | 89.8% | 0.107 | n/a (n=0) | 100.3 |
| hybrid+asof (exploratory) | 100 | 84.0% | 91.0% | 92.3% | 0.092 | n/a (n=0) | 98.3 |
| hybrid_rerank+asof (exploratory) | 100 | 80.0% | 89.0% | 89.9% | 0.112 | n/a (n=0) | 101.6 |
| agentic+asof (exploratory) | 100 | 87.0% | 97.0% | 89.7% | 0.086 | n/a (n=0) | 123.4 |

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
| closed_book | 100 | $0.0002 | $0.0190 | $0.0027 [$0.0015, $0.0066] | 2084.9 | 2993.3 | 1.00 | 0.00 |
| bm25 | 100 | $0.0001 | $0.0131 | $0.0003 [$0.0003, $0.0004] | 1095.7 | 2047.0 | 1.00 | 1.00 |
| vector | 100 | $0.0001 | $0.0133 | $0.0004 [$0.0003, $0.0005] | 2434.0 | 20577.9 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0137 | $0.0003 [$0.0003, $0.0004] | 5184.6 | 28049.2 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0130 | $0.0004 [$0.0003, $0.0005] | 7022.1 | 29347.9 | 1.00 | 1.00 |
| agentic | 100 | $0.0002 | $0.0208 | $0.0005 [$0.0004, $0.0007] | 6594.6 | 32391.2 | 2.22 | 1.22 |
| engine | 100 | $0.0002 | $0.0173 | $0.0003 [$0.0003, $0.0004] | 1039.4 | 2678.9 | 1.00 | 1.00 |
| oracle | 100 | $0.0001 | $0.0092 | $0.0002 [$0.0001, $0.0002] | 939.7 | 1980.7 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0001 | $0.0139 | $0.0002 [$0.0001, $0.0002] | 1101.6 | 2139.2 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0001 | $0.0144 | $0.0002 [$0.0002, $0.0002] | 2279.2 | 14007.4 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0001 | $0.0140 | $0.0002 [$0.0002, $0.0002] | 2295.1 | 20789.0 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0001 | $0.0135 | $0.0002 [$0.0002, $0.0002] | 3316.8 | 21643.6 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0002 | $0.0208 | $0.0002 [$0.0002, $0.0003] | 3028.9 | 18125.4 | 2.12 | 1.12 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 1.000 (100) |
| vector | n/a | n/a | n/a | 0.870 (100) |
| hybrid | n/a | n/a | n/a | 0.980 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.910 (100) |
| agentic | n/a | n/a | n/a | 0.990 (100) |
| engine | 62 | 0.976 | 0.984 | 1.000 (100) |
| oracle | n/a | n/a | n/a | 1.000 (100) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 1.000 (100) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.920 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.980 (100) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.920 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.990 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.840 [0.680, 1.000] | 0.0010 | 0.0060 |
| bm25 | 100 | 0.580 [0.380, 0.780] | 0.0010 | 0.0060 |
| vector | 100 | 0.560 [0.370, 0.750] | 0.0010 | 0.0060 |
| hybrid | 100 | 0.600 [0.410, 0.790] | 0.0010 | 0.0060 |
| hybrid_rerank | 100 | 0.630 [0.440, 0.810] | 0.0010 | 0.0060 |
| agentic | 100 | 0.590 [0.400, 0.790] | 0.0010 | 0.0060 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 49 | 1 | 0.0000 | 0.0000 | 0.196 |
| bm25 | 100 | 28 | 14 | 0.0436 | 0.0871 | 0.179 |
| vector | 100 | 28 | 10 | 0.0051 | 0.0204 | 0.171 |
| hybrid | 100 | 28 | 13 | 0.0275 | 0.0826 | 0.177 |
| hybrid_rerank | 100 | 29 | 10 | 0.0034 | 0.0169 | 0.173 |
| agentic | 100 | 29 | 16 | 0.0725 | 0.0871 | 0.186 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $-0.0000 [$-0.0001, $0.0001] |
| agentic | $-0.0002 [$-0.0003, $-0.0001] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | -0.290 [-0.420, -0.160] | 0.0010 | 0.0050 | 2 | 33 | 0.0000 | 0.164 |
| vector+asof | 100 | -0.220 [-0.330, -0.110] | 0.0010 | 0.0050 | 2 | 26 | 0.0000 | 0.147 |
| hybrid+asof | 100 | -0.290 [-0.410, -0.190] | 0.0010 | 0.0050 | 1 | 30 | 0.0000 | 0.154 |
| hybrid_rerank+asof | 100 | -0.230 [-0.350, -0.110] | 0.0030 | 0.0050 | 2 | 27 | 0.0000 | 0.149 |
| agentic+asof | 100 | -0.290 [-0.420, -0.170] | 0.0010 | 0.0050 | 2 | 34 | 0.0000 | 0.166 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 7.0% | no | -0.360 | no |
| bm25 | $0.0001 | 41.0% | yes | -0.100 | yes |
| vector | $0.0001 | 37.0% | no | -0.080 | yes |
| hybrid | $0.0001 | 40.0% | no | -0.120 | no |
| hybrid_rerank | $0.0001 | 36.0% | yes | -0.150 | yes |
| agentic | $0.0002 | 42.0% | no | -0.110 | no |
| engine | $0.0002 | 55.0% | yes | 0.480 | yes |

