# Results: musique, split `dev2`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 21.0% [14.2%, 30.0%] | 77.0% [67.8%, 84.2%] | 2.0% [0.6%, 7.0%] | -0.560 [-0.730, -0.386] |
| bm25 | 100 | 18.0% [11.7%, 26.7%] | 27.0% [19.3%, 36.4%] | 55.0% [45.2%, 64.4%] | -0.090 [-0.230, 0.041] |
| hybrid | 100 | 23.0% [15.8%, 32.2%] | 23.0% [15.8%, 32.2%] | 54.0% [44.3%, 63.4%] | 0.000 [-0.140, 0.137] |
| hybrid_rerank | 100 | 22.0% [15.0%, 31.1%] | 30.0% [21.9%, 39.6%] | 48.0% [38.5%, 57.7%] | -0.080 [-0.223, 0.053] |
| agentic | 100 | 41.0% [31.9%, 50.8%] | 35.0% [26.4%, 44.7%] | 24.0% [16.7%, 33.2%] | 0.060 [-0.101, 0.240] |
| engine | 100 | 29.0% [21.0%, 38.5%] | 11.0% [6.3%, 18.6%] | 60.0% [50.2%, 69.1%] | 0.180 [0.061, 0.301] |
| engine_single (exploratory) | 100 | 12.0% [7.0%, 19.8%] | 12.0% [7.0%, 19.8%] | 76.0% [66.8%, 83.3%] | 0.000 [-0.101, 0.091] |
| hybrid+asof (exploratory) | 100 | 20.0% [13.3%, 28.9%] | 27.0% [19.3%, 36.4%] | 53.0% [43.3%, 62.5%] | -0.070 [-0.216, 0.063] |
| agentic+asof (exploratory) | 100 | 36.0% [27.3%, 45.8%] | 37.0% [28.2%, 46.8%] | 27.0% [19.3%, 36.4%] | -0.010 [-0.170, 0.162] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 77 | 0 | 21.0% [14.2%, 30.0%] | -0.560 [-0.730, -0.386] | -0.560 [-0.730, -0.386] |
| bm25 | 100 | 27 | 1 | 19.0% [12.5%, 27.8%] | -0.070 [-0.204, 0.060] | -0.090 [-0.230, 0.041] |
| hybrid | 100 | 23 | 0 | 23.0% [15.8%, 32.2%] | 0.000 [-0.140, 0.137] | 0.000 [-0.140, 0.137] |
| hybrid_rerank | 100 | 30 | 0 | 22.0% [15.0%, 31.1%] | -0.080 [-0.223, 0.053] | -0.080 [-0.223, 0.053] |
| agentic | 100 | 35 | 3 | 44.0% [34.7%, 53.8%] | 0.120 [-0.049, 0.294] | 0.060 [-0.101, 0.240] |
| engine | 100 | 11 | 2 | 31.0% [22.8%, 40.6%] | 0.220 [0.102, 0.343] | 0.180 [0.061, 0.301] |
| engine_single (exploratory) | 100 | 12 | 1 | 13.0% [7.8%, 21.0%] | 0.020 [-0.082, 0.112] | 0.000 [-0.101, 0.091] |
| hybrid+asof (exploratory) | 100 | 27 | 2 | 22.0% [15.0%, 31.1%] | -0.030 [-0.172, 0.109] | -0.070 [-0.216, 0.063] |
| agentic+asof (exploratory) | 100 | 37 | 2 | 38.0% [29.1%, 47.8%] | 0.030 [-0.128, 0.194] | -0.010 [-0.170, 0.162] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 21.0% | 98.0% | 21.4% | 0.648 | n/a (n=0) | 306.1 |
| bm25 | 100 | 18.0% | 45.0% | 40.0% | 0.417 | n/a (n=0) | 219.9 |
| hybrid | 100 | 23.0% | 46.0% | 50.0% | 0.363 | n/a (n=0) | 219.9 |
| hybrid_rerank | 100 | 22.0% | 52.0% | 42.3% | 0.357 | n/a (n=0) | 227.5 |
| agentic | 100 | 41.0% | 76.0% | 53.9% | 0.191 | n/a (n=0) | 283.3 |
| engine | 100 | 29.0% | 40.0% | 72.5% | 0.155 | n/a (n=0) | 183.9 |
| engine_single (exploratory) | 100 | 12.0% | 24.0% | 50.0% | 0.619 | n/a (n=0) | 156.2 |
| hybrid+asof (exploratory) | 100 | 20.0% | 47.0% | 42.6% | 0.392 | n/a (n=0) | 192.4 |
| agentic+asof (exploratory) | 100 | 36.0% | 73.0% | 49.3% | 0.254 | n/a (n=0) | 258.1 |

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
| closed_book | 100 | $0.0001 | $0.0071 | $0.0003 [$0.0002, $0.0006] | 1074.7 | 1844.4 | 1.00 | 0.00 |
| bm25 | 100 | $0.0002 | $0.0216 | $0.0012 [$0.0008, $0.0021] | 877.7 | 2084.0 | 1.00 | 1.00 |
| hybrid | 100 | $0.0002 | $0.0214 | $0.0009 [$0.0007, $0.0015] | 975.2 | 1687.8 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0002 | $0.0226 | $0.0010 [$0.0007, $0.0016] | 3473.3 | 5224.0 | 1.00 | 1.00 |
| agentic | 100 | $0.0005 | $0.0456 | $0.0011 [$0.0009, $0.0015] | 3133.3 | 4334.7 | 3.00 | 2.00 |
| engine | 100 | $0.0010 | $0.0950 | $0.0033 [$0.0023, $0.0048] | 3006.2 | 4375.8 | 2.54 | 2.54 |
| engine_single (exploratory) | 100 | $0.0003 | $0.0295 | $0.0025 [$0.0016, $0.0050] | 1456.8 | 2823.2 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0002 | $0.0212 | $0.0011 [$0.0008, $0.0018] | 1026.0 | 1543.9 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0004 | $0.0437 | $0.0012 [$0.0010, $0.0016] | 2874.9 | 4634.6 | 2.96 | 1.96 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.495 (100) |
| hybrid | n/a | n/a | n/a | 0.534 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.552 (100) |
| agentic | n/a | n/a | n/a | 0.692 (100) |
| engine | 40 | 0.819 | 0.738 | 0.777 (100) |
| engine_single (exploratory) | 24 | 0.771 | 0.597 | 0.532 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.534 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.686 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.740 [0.535, 0.951] | 0.0010 | 0.0050 |
| bm25 | 100 | 0.270 [0.101, 0.442] | 0.0050 | 0.0200 |
| hybrid | 100 | 0.180 [0.021, 0.354] | 0.0470 | 0.0939 |
| hybrid_rerank | 100 | 0.260 [0.089, 0.426] | 0.0080 | 0.0240 |
| agentic | 100 | 0.120 [-0.083, 0.307] | 0.2338 | 0.2338 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 24 | 16 | 0.2682 | 0.6301 | 0.175 |
| bm25 | 100 | 18 | 7 | 0.0433 | 0.2139 | 0.138 |
| hybrid | 100 | 14 | 8 | 0.2863 | 0.6301 | 0.130 |
| hybrid_rerank | 100 | 15 | 8 | 0.2100 | 0.6301 | 0.133 |
| agentic | 100 | 9 | 21 | 0.0428 | 0.2139 | 0.152 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0023 [$0.0015, $0.0038] |
| agentic | $0.0022 [$0.0013, $0.0037] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| engine_single | 100 | 0.180 [0.058, 0.313] | 0.0070 | 0.0150 | 18 | 1 | 0.0001 | 0.121 |
| hybrid+asof | 100 | 0.250 [0.098, 0.420] | 0.0050 | 0.0150 | 16 | 7 | 0.0931 | 0.133 |
| agentic+asof | 100 | 0.190 [0.000, 0.357] | 0.0629 | 0.0629 | 10 | 17 | 0.2478 | 0.144 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0001 | 21.0% | yes | -0.560 | yes |
| bm25 | $0.0002 | 18.0% | no | -0.090 | no |
| hybrid | $0.0002 | 23.0% | yes | 0.000 | yes |
| hybrid_rerank | $0.0002 | 22.0% | no | -0.080 | no |
| agentic | $0.0005 | 41.0% | yes | 0.060 | yes |
| engine | $0.0010 | 29.0% | no | 0.180 | yes |

