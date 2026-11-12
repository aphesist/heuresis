# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 23.0% [15.8%, 32.2%] | 73.0% [63.6%, 80.7%] | 4.0% [1.6%, 9.8%] | -0.500 [-0.649, -0.330] |
| bm25 | 100 | 22.0% [15.0%, 31.1%] | 21.0% [14.2%, 30.0%] | 57.0% [47.2%, 66.3%] | 0.010 [-0.112, 0.127] |
| vector | 100 | 25.0% [17.5%, 34.3%] | 22.0% [15.0%, 31.1%] | 53.0% [43.3%, 62.5%] | 0.030 [-0.106, 0.160] |
| hybrid | 100 | 27.0% [19.3%, 36.4%] | 21.0% [14.2%, 30.0%] | 52.0% [42.3%, 61.5%] | 0.060 [-0.072, 0.184] |
| hybrid_rerank | 100 | 26.0% [18.4%, 35.4%] | 23.0% [15.8%, 32.2%] | 51.0% [41.3%, 60.6%] | 0.030 [-0.107, 0.162] |
| agentic | 100 | 48.0% [38.5%, 57.7%] | 32.0% [23.7%, 41.7%] | 20.0% [13.3%, 28.9%] | 0.160 [-0.010, 0.319] |
| engine | 100 | 18.0% [11.7%, 26.7%] | 13.0% [7.8%, 21.0%] | 69.0% [59.4%, 77.2%] | 0.050 [-0.069, 0.152] |
| oracle | 100 | 61.0% [51.2%, 70.0%] | 10.0% [5.5%, 17.4%] | 29.0% [21.0%, 38.5%] | 0.510 [0.380, 0.630] |
| bm25+asof (exploratory) | 100 | 22.0% [15.0%, 31.1%] | 20.0% [13.3%, 28.9%] | 58.0% [48.2%, 67.2%] | 0.020 [-0.100, 0.131] |
| vector+asof (exploratory) | 100 | 23.0% [15.8%, 32.2%] | 22.0% [15.0%, 31.1%] | 55.0% [45.2%, 64.4%] | 0.010 [-0.126, 0.134] |
| hybrid+asof (exploratory) | 100 | 26.0% [18.4%, 35.4%] | 22.0% [15.0%, 31.1%] | 52.0% [42.3%, 61.5%] | 0.040 [-0.098, 0.163] |
| hybrid_rerank+asof (exploratory) | 100 | 25.0% [17.5%, 34.3%] | 28.0% [20.1%, 37.5%] | 47.0% [37.5%, 56.7%] | -0.030 [-0.179, 0.093] |
| agentic+asof (exploratory) | 100 | 38.0% [29.1%, 47.8%] | 29.0% [21.0%, 38.5%] | 33.0% [24.6%, 42.7%] | 0.090 [-0.059, 0.245] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 23.0% | 96.0% | 24.0% | 0.523 | n/a (n=0) | 321.2 |
| bm25 | 100 | 22.0% | 43.0% | 51.2% | 0.336 | n/a (n=0) | 212.1 |
| vector | 100 | 25.0% | 47.0% | 53.2% | 0.212 | n/a (n=0) | 193.1 |
| hybrid | 100 | 27.0% | 48.0% | 56.2% | 0.286 | n/a (n=0) | 203.7 |
| hybrid_rerank | 100 | 26.0% | 49.0% | 53.1% | 0.393 | n/a (n=0) | 210.3 |
| agentic | 100 | 48.0% | 80.0% | 60.0% | 0.130 | n/a (n=0) | 289.2 |
| engine | 100 | 18.0% | 31.0% | 58.1% | 0.451 | n/a (n=0) | 137.7 |
| oracle | 100 | 61.0% | 71.0% | 85.9% | 0.064 | n/a (n=0) | 193.1 |
| bm25+asof (exploratory) | 100 | 22.0% | 42.0% | 52.4% | 0.334 | n/a (n=0) | 199.1 |
| vector+asof (exploratory) | 100 | 23.0% | 45.0% | 51.1% | 0.327 | n/a (n=0) | 186.3 |
| hybrid+asof (exploratory) | 100 | 26.0% | 48.0% | 54.2% | 0.290 | n/a (n=0) | 215.9 |
| hybrid_rerank+asof (exploratory) | 100 | 25.0% | 53.0% | 47.2% | 0.416 | n/a (n=0) | 226.0 |
| agentic+asof (exploratory) | 100 | 38.0% | 67.0% | 56.7% | 0.161 | n/a (n=0) | 273.1 |

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
| closed_book | 100 | $0.0001 | $0.0074 | $0.0003 [$0.0002, $0.0005] | 1037.7 | 1616.0 | 1.00 | 0.00 |
| bm25 | 100 | $0.0002 | $0.0216 | $0.0010 [$0.0007, $0.0015] | 824.4 | 1228.0 | 1.00 | 1.00 |
| vector | 100 | $0.0002 | $0.0205 | $0.0008 [$0.0006, $0.0012] | 1053.9 | 1441.4 | 1.00 | 1.00 |
| hybrid | 100 | $0.0002 | $0.0210 | $0.0008 [$0.0006, $0.0011] | 1102.6 | 1518.1 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0002 | $0.0221 | $0.0009 [$0.0006, $0.0012] | 4521.0 | 6758.4 | 1.00 | 1.00 |
| agentic | 100 | $0.0005 | $0.0477 | $0.0010 [$0.0008, $0.0013] | 2891.9 | 4160.7 | 3.04 | 2.04 |
| engine | 100 | $0.0003 | $0.0289 | $0.0016 [$0.0011, $0.0027] | 1358.0 | 3406.5 | 1.00 | 1.00 |
| oracle | 100 | $0.0001 | $0.0106 | $0.0002 [$0.0001, $0.0002] | 811.6 | 1157.8 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0002 | $0.0214 | $0.0010 [$0.0007, $0.0015] | 799.6 | 1217.5 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0002 | $0.0204 | $0.0009 [$0.0007, $0.0014] | 1059.6 | 1400.0 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0002 | $0.0210 | $0.0008 [$0.0006, $0.0012] | 1080.0 | 1497.2 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0002 | $0.0224 | $0.0009 [$0.0007, $0.0013] | 4065.1 | 6787.0 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0005 | $0.0467 | $0.0012 [$0.0010, $0.0017] | 2839.0 | 4192.0 | 3.01 | 2.01 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.506 (100) |
| vector | n/a | n/a | n/a | 0.473 (100) |
| hybrid | n/a | n/a | n/a | 0.526 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.576 (100) |
| agentic | n/a | n/a | n/a | 0.711 (100) |
| engine | 31 | 0.898 | 0.546 | 0.522 (100) |
| oracle | n/a | n/a | n/a | 1.000 (100) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 0.506 (100) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.473 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.526 (100) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.576 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.671 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.550 [0.343, 0.750] | 0.0010 | 0.0060 |
| bm25 | 100 | 0.040 [-0.099, 0.176] | 0.6623 | 1.0000 |
| vector | 100 | 0.020 [-0.121, 0.157] | 0.8851 | 1.0000 |
| hybrid | 100 | -0.010 [-0.133, 0.103] | 1.0000 | 1.0000 |
| hybrid_rerank | 100 | 0.020 [-0.129, 0.170] | 0.8851 | 1.0000 |
| agentic | 100 | -0.110 [-0.272, 0.059] | 0.2677 | 1.0000 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 15 | 20 | 0.4996 | 0.9614 | 0.164 |
| bm25 | 100 | 7 | 11 | 0.4807 | 0.9614 | 0.117 |
| vector | 100 | 5 | 12 | 0.1435 | 0.4613 | 0.114 |
| hybrid | 100 | 1 | 10 | 0.0117 | 0.0586 | 0.092 |
| hybrid_rerank | 100 | 6 | 14 | 0.1153 | 0.4613 | 0.124 |
| agentic | 100 | 2 | 32 | 0.0000 | 0.0000 | 0.161 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0008 [$0.0005, $0.0017] |
| agentic | $0.0006 [$0.0002, $0.0016] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | 0.030 [-0.121, 0.170] | 0.7892 | 1.0000 | 8 | 12 | 0.5034 | 0.124 |
| vector+asof | 100 | 0.040 [-0.089, 0.174] | 0.6553 | 1.0000 | 5 | 10 | 0.3018 | 0.107 |
| hybrid+asof | 100 | 0.010 [-0.112, 0.127] | 1.0000 | 1.0000 | 2 | 10 | 0.0386 | 0.096 |
| hybrid_rerank+asof | 100 | 0.080 [-0.084, 0.238] | 0.4136 | 1.0000 | 7 | 14 | 0.1892 | 0.127 |
| agentic+asof | 100 | -0.040 [-0.196, 0.121] | 0.7522 | 1.0000 | 4 | 24 | 0.0002 | 0.147 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0001 | 23.0% | yes | -0.500 | yes |
| bm25 | $0.0002 | 22.0% | no | 0.010 | no |
| vector | $0.0002 | 25.0% | yes | 0.030 | yes |
| hybrid | $0.0002 | 27.0% | yes | 0.060 | yes |
| hybrid_rerank | $0.0002 | 26.0% | no | 0.030 | no |
| agentic | $0.0005 | 48.0% | yes | 0.160 | yes |
| engine | $0.0003 | 18.0% | no | 0.050 | no |

