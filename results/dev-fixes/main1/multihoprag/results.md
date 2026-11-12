# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 32.0% [23.7%, 41.7%] | 27.0% [19.3%, 36.4%] | 41.0% [31.9%, 50.8%] | 0.050 [-0.118, 0.208] |
| bm25 | 100 | 52.0% [42.3%, 61.5%] | 11.0% [6.3%, 18.6%] | 37.0% [28.2%, 46.8%] | 0.410 [0.253, 0.548] |
| vector | 100 | 41.0% [31.9%, 50.8%] | 6.0% [2.8%, 12.5%] | 53.0% [43.3%, 62.5%] | 0.350 [0.216, 0.472] |
| hybrid | 100 | 52.0% [42.3%, 61.5%] | 12.0% [7.0%, 19.8%] | 36.0% [27.3%, 45.8%] | 0.400 [0.263, 0.521] |
| hybrid_rerank | 100 | 44.0% [34.7%, 53.8%] | 12.0% [7.0%, 19.8%] | 44.0% [34.7%, 53.8%] | 0.320 [0.187, 0.447] |
| agentic | 100 | 39.0% [30.0%, 48.8%] | 34.0% [25.5%, 43.7%] | 27.0% [19.3%, 36.4%] | 0.050 [-0.121, 0.211] |
| engine | 100 | 25.0% [17.5%, 34.3%] | 10.0% [5.5%, 17.4%] | 65.0% [55.3%, 73.6%] | 0.150 [0.032, 0.266] |
| oracle | 100 | 54.0% [44.3%, 63.4%] | 8.0% [4.1%, 15.0%] | 38.0% [29.1%, 47.8%] | 0.460 [0.316, 0.600] |
| bm25+asof (exploratory) | 100 | 49.0% [39.4%, 58.7%] | 13.0% [7.8%, 21.0%] | 38.0% [29.1%, 47.8%] | 0.360 [0.200, 0.500] |
| vector+asof (exploratory) | 100 | 42.0% [32.8%, 51.8%] | 6.0% [2.8%, 12.5%] | 52.0% [42.3%, 61.5%] | 0.360 [0.233, 0.473] |
| hybrid+asof (exploratory) | 100 | 49.0% [39.4%, 58.7%] | 12.0% [7.0%, 19.8%] | 39.0% [30.0%, 48.8%] | 0.370 [0.227, 0.500] |
| hybrid_rerank+asof (exploratory) | 100 | 46.0% [36.6%, 55.7%] | 8.0% [4.1%, 15.0%] | 46.0% [36.6%, 55.7%] | 0.380 [0.261, 0.495] |
| agentic+asof (exploratory) | 100 | 40.0% [30.9%, 49.8%] | 31.0% [22.8%, 40.6%] | 29.0% [21.0%, 38.5%] | 0.090 [-0.093, 0.259] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 23 | 0 | 32.0% [23.7%, 41.7%] | 0.050 [-0.118, 0.208] | 0.050 [-0.118, 0.208] |
| bm25 | 100 | 11 | 2 | 54.0% [44.3%, 63.4%] | 0.450 [0.311, 0.586] | 0.410 [0.253, 0.548] |
| vector | 100 | 6 | 0 | 41.0% [31.9%, 50.8%] | 0.350 [0.216, 0.472] | 0.350 [0.216, 0.472] |
| hybrid | 100 | 12 | 2 | 54.0% [44.3%, 63.4%] | 0.440 [0.308, 0.557] | 0.400 [0.263, 0.521] |
| hybrid_rerank | 100 | 12 | 2 | 46.0% [36.6%, 55.7%] | 0.360 [0.223, 0.485] | 0.320 [0.187, 0.447] |
| agentic | 100 | 34 | 6 | 45.0% [35.6%, 54.8%] | 0.170 [0.000, 0.327] | 0.050 [-0.121, 0.211] |
| engine | 100 | 10 | 3 | 28.0% [20.1%, 37.5%] | 0.210 [0.100, 0.326] | 0.150 [0.032, 0.266] |
| oracle | 100 | 8 | 2 | 56.0% [46.2%, 65.3%] | 0.500 [0.368, 0.630] | 0.460 [0.316, 0.600] |
| bm25+asof (exploratory) | 100 | 13 | 5 | 54.0% [44.3%, 63.4%] | 0.460 [0.318, 0.598] | 0.360 [0.200, 0.500] |
| vector+asof (exploratory) | 100 | 6 | 0 | 42.0% [32.8%, 51.8%] | 0.360 [0.233, 0.473] | 0.360 [0.233, 0.473] |
| hybrid+asof (exploratory) | 100 | 12 | 2 | 51.0% [41.3%, 60.6%] | 0.410 [0.275, 0.533] | 0.370 [0.227, 0.500] |
| hybrid_rerank+asof (exploratory) | 100 | 8 | 2 | 48.0% [38.5%, 57.7%] | 0.420 [0.306, 0.531] | 0.380 [0.261, 0.495] |
| agentic+asof (exploratory) | 100 | 31 | 9 | 49.0% [39.4%, 58.7%] | 0.270 [0.126, 0.419] | 0.090 [-0.093, 0.259] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 32.0% | 51.0% | 47.1% | 0.197 | 66.7% (n=12) | 301.8 |
| bm25 | 100 | 52.0% | 51.0% | 78.4% | 0.080 | 100.0% (n=12) | 320.0 |
| vector | 100 | 41.0% | 35.0% | 82.9% | 0.055 | 100.0% (n=12) | 297.8 |
| hybrid | 100 | 52.0% | 52.0% | 76.9% | 0.078 | 100.0% (n=12) | 306.4 |
| hybrid_rerank | 100 | 44.0% | 44.0% | 72.7% | 0.158 | 100.0% (n=12) | 318.2 |
| agentic | 100 | 39.0% | 61.0% | 44.3% | 0.370 | 100.0% (n=12) | 385.3 |
| engine | 100 | 25.0% | 23.0% | 56.5% | 0.378 | 100.0% (n=12) | 215.0 |
| oracle | 100 | 54.0% | 50.0% | 84.0% | 0.036 | 100.0% (n=12) | 265.5 |
| bm25+asof (exploratory) | 100 | 49.0% | 50.0% | 74.0% | 0.121 | 100.0% (n=12) | 330.6 |
| vector+asof (exploratory) | 100 | 42.0% | 36.0% | 83.3% | 0.120 | 100.0% (n=12) | 292.2 |
| hybrid+asof (exploratory) | 100 | 49.0% | 49.0% | 75.5% | 0.091 | 100.0% (n=12) | 306.2 |
| hybrid_rerank+asof (exploratory) | 100 | 46.0% | 42.0% | 81.0% | 0.106 | 100.0% (n=12) | 318.6 |
| agentic+asof (exploratory) | 100 | 40.0% | 59.0% | 47.5% | 0.316 | 100.0% (n=12) | 406.3 |

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
| closed_book | 100 | $0.0001 | $0.0054 | $0.0002 [$0.0001, $0.0003] | 951.5 | 1662.7 | 1.00 | 0.00 |
| bm25 | 100 | $0.0005 | $0.0461 | $0.0009 [$0.0007, $0.0011] | 1005.5 | 1959.9 | 1.00 | 1.00 |
| vector | 100 | $0.0004 | $0.0443 | $0.0011 [$0.0009, $0.0015] | 1113.0 | 1795.1 | 1.00 | 1.00 |
| hybrid | 100 | $0.0005 | $0.0459 | $0.0009 [$0.0008, $0.0011] | 1171.1 | 1998.1 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0005 | $0.0464 | $0.0011 [$0.0009, $0.0013] | 13518.7 | 16422.7 | 1.00 | 1.00 |
| agentic | 100 | $0.0006 | $0.0570 | $0.0015 [$0.0011, $0.0021] | 2231.6 | 3871.6 | 2.37 | 1.37 |
| engine | 100 | $0.0005 | $0.0536 | $0.0021 [$0.0016, $0.0033] | 4994.9 | 9111.7 | 1.00 | 1.00 |
| oracle | 100 | $0.0002 | $0.0161 | $0.0003 [$0.0002, $0.0004] | 865.2 | 1716.8 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0005 | $0.0461 | $0.0009 [$0.0008, $0.0012] | 1082.8 | 1850.4 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0004 | $0.0443 | $0.0011 [$0.0009, $0.0014] | 1184.7 | 1898.7 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0005 | $0.0458 | $0.0009 [$0.0008, $0.0012] | 1311.2 | 2139.4 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0005 | $0.0463 | $0.0010 [$0.0008, $0.0012] | 13828.4 | 15984.1 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0006 | $0.0612 | $0.0015 [$0.0011, $0.0022] | 2513.1 | 4602.3 | 2.45 | 1.45 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.589 (88) |
| vector | n/a | n/a | n/a | 0.406 (88) |
| hybrid | n/a | n/a | n/a | 0.576 (88) |
| hybrid_rerank | n/a | n/a | n/a | 0.422 (88) |
| agentic | n/a | n/a | n/a | 0.476 (88) |
| engine | 23 | 0.546 | 0.467 | 0.594 (88) |
| oracle | n/a | n/a | n/a | 1.000 (88) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 0.589 (88) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.406 (88) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.576 (88) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.422 (88) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.495 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.100 [-0.069, 0.280] | 0.3007 | 0.4515 |
| bm25 | 100 | -0.260 [-0.396, -0.103] | 0.0090 | 0.0450 |
| vector | 100 | -0.200 [-0.357, -0.051] | 0.0320 | 0.1039 |
| hybrid | 100 | -0.250 [-0.390, -0.113] | 0.0040 | 0.0240 |
| hybrid_rerank | 100 | -0.170 [-0.300, -0.042] | 0.0260 | 0.1039 |
| agentic | 100 | 0.100 [-0.048, 0.258] | 0.2258 | 0.4515 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 8 | 15 | 0.2100 | 0.2100 | 0.133 |
| bm25 | 100 | 1 | 28 | 0.0000 | 0.0000 | 0.149 |
| vector | 100 | 6 | 22 | 0.0037 | 0.0112 | 0.147 |
| hybrid | 100 | 3 | 30 | 0.0000 | 0.0000 | 0.159 |
| hybrid_rerank | 100 | 3 | 22 | 0.0002 | 0.0006 | 0.138 |
| agentic | 100 | 4 | 18 | 0.0043 | 0.0112 | 0.130 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0013 [$0.0007, $0.0023] |
| agentic | $0.0007 [$0.0001, $0.0016] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | -0.210 [-0.339, -0.066] | 0.0150 | 0.0360 | 2 | 26 | 0.0000 | 0.147 |
| vector+asof | 100 | -0.210 [-0.354, -0.067] | 0.0090 | 0.0360 | 6 | 23 | 0.0023 | 0.149 |
| hybrid+asof | 100 | -0.220 [-0.373, -0.073] | 0.0100 | 0.0360 | 3 | 27 | 0.0000 | 0.152 |
| hybrid_rerank+asof | 100 | -0.230 [-0.366, -0.100] | 0.0060 | 0.0300 | 3 | 24 | 0.0000 | 0.144 |
| agentic+asof | 100 | 0.060 [-0.098, 0.215] | 0.5974 | 0.5974 | 3 | 18 | 0.0015 | 0.127 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0001 | 32.0% | yes | 0.050 | yes |
| bm25 | $0.0005 | 52.0% | no | 0.410 | yes |
| vector | $0.0004 | 41.0% | yes | 0.350 | yes |
| hybrid | $0.0005 | 52.0% | yes | 0.400 | yes |
| hybrid_rerank | $0.0005 | 44.0% | no | 0.320 | no |
| agentic | $0.0006 | 39.0% | no | 0.050 | no |
| engine | $0.0005 | 25.0% | no | 0.150 | no |

