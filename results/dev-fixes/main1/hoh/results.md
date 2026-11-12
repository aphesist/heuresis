# Results: hoh, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 8.0% [4.1%, 15.0%] | 81.0% [72.2%, 87.5%] | 11.0% [6.3%, 18.6%] | -0.730 [-0.850, -0.610] |
| bm25 | 100 | 42.0% [32.8%, 51.8%] | 51.0% [41.3%, 60.6%] | 7.0% [3.4%, 13.7%] | -0.090 [-0.280, 0.080] |
| vector | 100 | 38.0% [29.1%, 47.8%] | 41.0% [31.9%, 50.8%] | 21.0% [14.2%, 30.0%] | -0.030 [-0.210, 0.140] |
| hybrid | 100 | 43.0% [33.7%, 52.8%] | 49.0% [39.4%, 58.7%] | 8.0% [4.1%, 15.0%] | -0.060 [-0.240, 0.110] |
| hybrid_rerank | 100 | 36.0% [27.3%, 45.8%] | 48.0% [38.5%, 57.7%] | 16.0% [10.1%, 24.4%] | -0.120 [-0.300, 0.050] |
| agentic | 100 | 42.0% [32.8%, 51.8%] | 53.0% [43.3%, 62.5%] | 5.0% [2.2%, 11.2%] | -0.110 [-0.300, 0.070] |
| engine | 100 | 82.0% [73.3%, 88.3%] | 7.0% [3.4%, 13.7%] | 11.0% [6.3%, 18.6%] | 0.750 [0.640, 0.850] |
| oracle | 100 | 82.0% [73.3%, 88.3%] | 8.0% [4.1%, 15.0%] | 10.0% [5.5%, 17.4%] | 0.740 [0.620, 0.850] |
| bm25+asof (exploratory) | 100 | 85.0% [76.7%, 90.7%] | 7.0% [3.4%, 13.7%] | 8.0% [4.1%, 15.0%] | 0.780 [0.670, 0.880] |
| vector+asof (exploratory) | 100 | 81.0% [72.2%, 87.5%] | 6.0% [2.8%, 12.5%] | 13.0% [7.8%, 21.0%] | 0.750 [0.630, 0.860] |
| hybrid+asof (exploratory) | 100 | 85.0% [76.7%, 90.7%] | 8.0% [4.1%, 15.0%] | 7.0% [3.4%, 13.7%] | 0.770 [0.650, 0.880] |
| hybrid_rerank+asof (exploratory) | 100 | 76.0% [66.8%, 83.3%] | 10.0% [5.5%, 17.4%] | 14.0% [8.5%, 22.1%] | 0.660 [0.530, 0.780] |
| agentic+asof (exploratory) | 100 | 85.0% [76.7%, 90.7%] | 10.0% [5.5%, 17.4%] | 5.0% [2.2%, 11.2%] | 0.750 [0.620, 0.870] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 81 | 3 | 11.0% [6.3%, 18.6%] | -0.670 [-0.790, -0.530] | -0.730 [-0.850, -0.610] |
| bm25 | 100 | 51 | 3 | 45.0% [35.6%, 54.8%] | -0.030 [-0.220, 0.150] | -0.090 [-0.280, 0.080] |
| vector | 100 | 41 | 3 | 41.0% [31.9%, 50.8%] | 0.030 [-0.150, 0.210] | -0.030 [-0.210, 0.140] |
| hybrid | 100 | 49 | 3 | 46.0% [36.6%, 55.7%] | 0.000 [-0.180, 0.170] | -0.060 [-0.240, 0.110] |
| hybrid_rerank | 100 | 48 | 3 | 39.0% [30.0%, 48.8%] | -0.060 [-0.240, 0.110] | -0.120 [-0.300, 0.050] |
| agentic | 100 | 53 | 4 | 46.0% [36.6%, 55.7%] | -0.030 [-0.230, 0.150] | -0.110 [-0.300, 0.070] |
| engine | 100 | 7 | 7 | 89.0% [81.4%, 93.7%] | 0.890 [0.830, 0.940] | 0.750 [0.640, 0.850] |
| oracle | 100 | 8 | 7 | 89.0% [81.4%, 93.7%] | 0.880 [0.810, 0.940] | 0.740 [0.620, 0.850] |
| bm25+asof (exploratory) | 100 | 7 | 6 | 91.0% [83.8%, 95.2%] | 0.900 [0.830, 0.960] | 0.780 [0.670, 0.880] |
| vector+asof (exploratory) | 100 | 6 | 6 | 87.0% [79.0%, 92.2%] | 0.870 [0.800, 0.930] | 0.750 [0.630, 0.860] |
| hybrid+asof (exploratory) | 100 | 8 | 7 | 92.0% [85.0%, 95.9%] | 0.910 [0.840, 0.970] | 0.770 [0.650, 0.880] |
| hybrid_rerank+asof (exploratory) | 100 | 10 | 9 | 85.0% [76.7%, 90.7%] | 0.840 [0.760, 0.910] | 0.660 [0.530, 0.780] |
| agentic+asof (exploratory) | 100 | 10 | 7 | 92.0% [85.0%, 95.9%] | 0.890 [0.800, 0.960] | 0.750 [0.620, 0.870] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 8.0% | 89.0% | 9.0% | 0.795 | n/a (n=0) | 206.5 |
| bm25 | 100 | 42.0% | 93.0% | 45.2% | 0.523 | n/a (n=0) | 95.3 |
| vector | 100 | 38.0% | 79.0% | 48.1% | 0.533 | n/a (n=0) | 90.9 |
| hybrid | 100 | 43.0% | 92.0% | 46.7% | 0.599 | n/a (n=0) | 101.1 |
| hybrid_rerank | 100 | 36.0% | 84.0% | 42.9% | 0.578 | n/a (n=0) | 92.0 |
| agentic | 100 | 42.0% | 95.0% | 44.2% | 0.562 | n/a (n=0) | 135.3 |
| engine | 100 | 82.0% | 89.0% | 92.1% | 0.053 | n/a (n=0) | 89.6 |
| oracle | 100 | 82.0% | 90.0% | 91.1% | 0.090 | n/a (n=0) | 112.2 |
| bm25+asof (exploratory) | 100 | 85.0% | 92.0% | 92.4% | 0.120 | n/a (n=0) | 100.4 |
| vector+asof (exploratory) | 100 | 81.0% | 87.0% | 93.1% | 0.090 | n/a (n=0) | 96.0 |
| hybrid+asof (exploratory) | 100 | 85.0% | 93.0% | 91.4% | 0.103 | n/a (n=0) | 93.9 |
| hybrid_rerank+asof (exploratory) | 100 | 76.0% | 86.0% | 88.4% | 0.116 | n/a (n=0) | 92.7 |
| agentic+asof (exploratory) | 100 | 85.0% | 95.0% | 89.5% | 0.067 | n/a (n=0) | 137.2 |

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
| closed_book | 100 | $0.0001 | $0.0050 | $0.0006 [$0.0004, $0.0017] | 826.6 | 1233.3 | 1.00 | 0.00 |
| bm25 | 100 | $0.0001 | $0.0100 | $0.0002 [$0.0002, $0.0003] | 994.4 | 1350.8 | 1.00 | 1.00 |
| vector | 100 | $0.0001 | $0.0108 | $0.0003 [$0.0002, $0.0004] | 3247.6 | 19624.5 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0106 | $0.0002 [$0.0002, $0.0003] | 6706.0 | 21493.9 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0101 | $0.0003 [$0.0002, $0.0004] | 9417.9 | 22263.5 | 1.00 | 1.00 |
| agentic | 100 | $0.0001 | $0.0146 | $0.0003 [$0.0003, $0.0005] | 9439.0 | 20786.1 | 2.11 | 1.11 |
| engine | 100 | $0.0002 | $0.0157 | $0.0002 [$0.0002, $0.0002] | 997.9 | 2569.6 | 1.00 | 1.00 |
| oracle | 100 | $0.0000 | $0.0047 | $0.0001 [$0.0001, $0.0001] | 735.1 | 1030.9 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0001 | $0.0105 | $0.0001 [$0.0001, $0.0001] | 950.4 | 1275.6 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0001 | $0.0113 | $0.0001 [$0.0001, $0.0002] | 3706.1 | 16001.8 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0001 | $0.0108 | $0.0001 [$0.0001, $0.0001] | 2920.4 | 17938.7 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0001 | $0.0105 | $0.0001 [$0.0001, $0.0002] | 3815.6 | 19764.0 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0002 | $0.0152 | $0.0002 [$0.0002, $0.0002] | 3419.2 | 21063.8 | 2.11 | 1.11 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 1.000 (100) |
| vector | n/a | n/a | n/a | 0.870 (100) |
| hybrid | n/a | n/a | n/a | 0.980 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.910 (100) |
| agentic | n/a | n/a | n/a | 0.970 (100) |
| engine | 89 | 0.966 | 0.989 | 1.000 (100) |
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
| closed_book | 100 | 1.480 [1.310, 1.630] | 0.0010 | 0.0060 |
| bm25 | 100 | 0.840 [0.640, 1.060] | 0.0010 | 0.0060 |
| vector | 100 | 0.780 [0.580, 0.970] | 0.0010 | 0.0060 |
| hybrid | 100 | 0.810 [0.590, 1.010] | 0.0010 | 0.0060 |
| hybrid_rerank | 100 | 0.870 [0.680, 1.060] | 0.0010 | 0.0060 |
| agentic | 100 | 0.860 [0.660, 1.070] | 0.0010 | 0.0060 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 76 | 2 | 0.0000 | 0.0000 | 0.245 |
| bm25 | 100 | 46 | 6 | 0.0000 | 0.0000 | 0.200 |
| vector | 100 | 50 | 6 | 0.0000 | 0.0000 | 0.207 |
| hybrid | 100 | 46 | 7 | 0.0000 | 0.0000 | 0.202 |
| hybrid_rerank | 100 | 50 | 4 | 0.0000 | 0.0000 | 0.203 |
| agentic | 100 | 47 | 7 | 0.0000 | 0.0000 | 0.203 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $-0.0001 [$-0.0001, $-0.0000] |
| agentic | $-0.0002 [$-0.0003, $-0.0001] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | -0.030 [-0.130, 0.070] | 0.6943 | 1.0000 | 5 | 8 | 0.5811 | 0.100 |
| vector+asof | 100 | 0.000 [-0.100, 0.100] | 1.0000 | 1.0000 | 10 | 9 | 1.0000 | 0.121 |
| hybrid+asof | 100 | -0.020 [-0.110, 0.080] | 0.8372 | 1.0000 | 5 | 8 | 0.5811 | 0.100 |
| hybrid_rerank+asof | 100 | 0.090 [0.010, 0.180] | 0.0849 | 0.4246 | 10 | 4 | 0.1796 | 0.104 |
| agentic+asof | 100 | 0.000 [-0.100, 0.100] | 1.0000 | 1.0000 | 5 | 8 | 0.5811 | 0.100 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0001 | 8.0% | yes | -0.730 | yes |
| bm25 | $0.0001 | 42.0% | yes | -0.090 | yes |
| vector | $0.0001 | 38.0% | no | -0.030 | yes |
| hybrid | $0.0001 | 43.0% | yes | -0.060 | yes |
| hybrid_rerank | $0.0001 | 36.0% | no | -0.120 | no |
| agentic | $0.0001 | 42.0% | no | -0.110 | no |
| engine | $0.0002 | 82.0% | yes | 0.750 | yes |

