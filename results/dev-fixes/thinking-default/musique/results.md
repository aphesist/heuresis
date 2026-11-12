# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 28.0% [20.1%, 37.5%] | 28.0% [20.1%, 37.5%] | 44.0% [34.7%, 53.8%] | 0.000 [-0.144, 0.150] |
| bm25 | 100 | 20.0% [13.3%, 28.9%] | 5.0% [2.2%, 11.2%] | 75.0% [65.7%, 82.5%] | 0.150 [0.058, 0.247] |
| hybrid | 100 | 21.0% [14.2%, 30.0%] | 9.0% [4.8%, 16.2%] | 70.0% [60.4%, 78.1%] | 0.120 [0.020, 0.216] |
| agentic | 100 | 47.0% [37.5%, 56.7%] | 15.0% [9.3%, 23.3%] | 38.0% [29.1%, 47.8%] | 0.320 [0.184, 0.454] |
| engine | 100 | 16.0% [10.1%, 24.4%] | 8.0% [4.1%, 15.0%] | 76.0% [66.8%, 83.3%] | 0.080 [-0.010, 0.170] |
| hybrid+asof (exploratory) | 100 | 23.0% [15.8%, 32.2%] | 8.0% [4.1%, 15.0%] | 69.0% [59.4%, 77.2%] | 0.150 [0.049, 0.245] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 28 | 6 | 34.0% [25.5%, 43.7%] | 0.120 [-0.029, 0.275] | 0.000 [-0.144, 0.150] |
| bm25 | 100 | 5 | 1 | 21.0% [14.2%, 30.0%] | 0.170 [0.078, 0.260] | 0.150 [0.058, 0.247] |
| hybrid | 100 | 9 | 3 | 24.0% [16.7%, 33.2%] | 0.180 [0.088, 0.273] | 0.120 [0.020, 0.216] |
| agentic | 100 | 15 | 8 | 55.0% [45.2%, 64.4%] | 0.480 [0.347, 0.600] | 0.320 [0.184, 0.454] |
| engine | 100 | 8 | 3 | 19.0% [12.5%, 27.8%] | 0.140 [0.049, 0.230] | 0.080 [-0.010, 0.170] |
| hybrid+asof (exploratory) | 100 | 8 | 4 | 27.0% [19.3%, 36.4%] | 0.230 [0.135, 0.320] | 0.150 [0.049, 0.245] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 28.0% | 56.0% | 50.0% | 0.350 | n/a (n=0) | 206.7 |
| bm25 | 100 | 20.0% | 25.0% | 80.0% | 0.039 | n/a (n=0) | 172.1 |
| hybrid | 100 | 21.0% | 30.0% | 70.0% | 0.098 | n/a (n=0) | 169.0 |
| agentic | 100 | 47.0% | 62.0% | 75.8% | 0.135 | n/a (n=0) | 202.3 |
| engine | 100 | 16.0% | 24.0% | 66.7% | 0.509 | n/a (n=0) | 103.4 |
| hybrid+asof (exploratory) | 100 | 23.0% | 31.0% | 74.2% | 0.096 | n/a (n=0) | 169.8 |

## Table 2b. Errors (split `dev`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 100 | 0 | 0 |
| bm25 | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| agentic | 100 | 0 | 0 |
| engine | 100 | 0 | 0 |
| hybrid+asof (exploratory) | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | $0.0003 | $0.0287 | $0.0010 [$0.0007, $0.0015] | 2739.8 | 5152.0 | 1.00 | 0.00 |
| bm25 | 100 | $0.0003 | $0.0315 | $0.0016 [$0.0011, $0.0027] | 1505.2 | 2844.9 | 1.00 | 1.00 |
| hybrid | 100 | $0.0003 | $0.0311 | $0.0015 [$0.0011, $0.0023] | 1611.1 | 3232.9 | 1.00 | 1.00 |
| agentic | 100 | $0.0009 | $0.0904 | $0.0019 [$0.0015, $0.0026] | 5154.7 | 10067.6 | 3.49 | 2.49 |
| engine | 100 | $0.0004 | $0.0404 | $0.0025 [$0.0018, $0.0045] | 1998.0 | 3799.7 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0003 | $0.0306 | $0.0013 [$0.0010, $0.0020] | 1652.7 | 2953.8 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.506 (100) |
| hybrid | n/a | n/a | n/a | 0.526 (100) |
| agentic | n/a | n/a | n/a | 0.739 (100) |
| engine | 24 | 0.809 | 0.632 | 0.522 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.526 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.080 [-0.071, 0.223] | 0.3536 | 0.9530 |
| bm25 | 100 | -0.070 [-0.186, 0.031] | 0.3177 | 0.9530 |
| hybrid | 100 | -0.040 [-0.134, 0.057] | 0.5235 | 0.9530 |
| agentic | 100 | -0.240 [-0.366, -0.118] | 0.0010 | 0.0040 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 6 | 18 | 0.0227 | 0.0680 | 0.136 |
| bm25 | 100 | 4 | 8 | 0.3877 | 0.4531 | 0.096 |
| hybrid | 100 | 3 | 8 | 0.2266 | 0.4531 | 0.092 |
| agentic | 100 | 1 | 32 | 0.0000 | 0.0000 | 0.159 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0010 [$0.0004, $0.0025] |
| agentic | $0.0006 [$-0.0001, $0.0023] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| hybrid+asof | 100 | -0.070 [-0.157, 0.020] | 0.2328 | 0.2328 | 2 | 9 | 0.0654 | 0.092 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0003 | 28.0% | yes | 0.000 | yes |
| bm25 | $0.0003 | 20.0% | no | 0.150 | yes |
| hybrid | $0.0003 | 21.0% | no | 0.120 | yes |
| agentic | $0.0009 | 47.0% | yes | 0.320 | yes |
| engine | $0.0004 | 16.0% | no | 0.080 | no |

