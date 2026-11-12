# Results: hoh, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 6.0% [2.8%, 12.5%] | 45.0% [35.6%, 54.8%] | 49.0% [39.4%, 58.7%] | -0.390 [-0.500, -0.270] |
| bm25 | 100 | 39.0% [30.0%, 48.8%] | 55.0% [45.2%, 64.4%] | 6.0% [2.8%, 12.5%] | -0.160 [-0.340, 0.020] |
| hybrid | 100 | 42.0% [32.8%, 51.8%] | 52.0% [42.3%, 61.5%] | 6.0% [2.8%, 12.5%] | -0.100 [-0.280, 0.080] |
| agentic | 100 | 44.0% [34.7%, 53.8%] | 53.0% [43.3%, 62.5%] | 3.0% [1.0%, 8.5%] | -0.090 [-0.280, 0.090] |
| engine | 100 | 80.0% [71.1%, 86.7%] | 11.0% [6.3%, 18.6%] | 9.0% [4.8%, 16.2%] | 0.690 [0.560, 0.810] |
| hybrid+asof (exploratory) | 100 | 80.0% [71.1%, 86.7%] | 12.0% [7.0%, 19.8%] | 8.0% [4.1%, 15.0%] | 0.680 [0.540, 0.810] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 45 | 7 | 13.0% [7.8%, 21.0%] | -0.250 [-0.380, -0.120] | -0.390 [-0.500, -0.270] |
| bm25 | 100 | 55 | 4 | 43.0% [33.7%, 52.8%] | -0.080 [-0.270, 0.090] | -0.160 [-0.340, 0.020] |
| hybrid | 100 | 52 | 4 | 46.0% [36.6%, 55.7%] | -0.020 [-0.200, 0.150] | -0.100 [-0.280, 0.080] |
| agentic | 100 | 53 | 5 | 49.0% [39.4%, 58.7%] | 0.010 [-0.180, 0.190] | -0.090 [-0.280, 0.090] |
| engine | 100 | 11 | 6 | 86.0% [77.9%, 91.5%] | 0.810 [0.700, 0.900] | 0.690 [0.560, 0.810] |
| hybrid+asof (exploratory) | 100 | 12 | 11 | 91.0% [83.8%, 95.2%] | 0.900 [0.830, 0.960] | 0.680 [0.540, 0.810] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 6.0% | 51.0% | 11.8% | 0.744 | n/a (n=0) | 183.1 |
| bm25 | 100 | 39.0% | 94.0% | 41.5% | 0.568 | n/a (n=0) | 104.3 |
| hybrid | 100 | 42.0% | 94.0% | 44.7% | 0.550 | n/a (n=0) | 103.7 |
| agentic | 100 | 44.0% | 97.0% | 45.4% | 0.568 | n/a (n=0) | 128.6 |
| engine | 100 | 80.0% | 91.0% | 87.9% | 0.109 | n/a (n=0) | 82.5 |
| hybrid+asof (exploratory) | 100 | 80.0% | 92.0% | 87.0% | 0.106 | n/a (n=0) | 97.9 |

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
| closed_book | 100 | $0.0002 | $0.0204 | $0.0034 [$0.0018, $0.0103] | 2068.9 | 4106.4 | 1.00 | 0.00 |
| bm25 | 100 | $0.0001 | $0.0142 | $0.0004 [$0.0003, $0.0005] | 1437.9 | 2791.7 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0145 | $0.0003 [$0.0003, $0.0004] | 2997.0 | 11985.2 | 1.00 | 1.00 |
| agentic | 100 | $0.0002 | $0.0223 | $0.0005 [$0.0004, $0.0007] | 4857.1 | 26953.3 | 2.24 | 1.24 |
| engine | 100 | $0.0002 | $0.0179 | $0.0002 [$0.0002, $0.0003] | 1353.9 | 3047.8 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0001 | $0.0149 | $0.0002 [$0.0002, $0.0002] | 3357.0 | 10327.7 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 1.000 (100) |
| hybrid | n/a | n/a | n/a | 0.980 (100) |
| agentic | n/a | n/a | n/a | 0.990 (100) |
| engine | 91 | 0.989 | 1.000 | 1.000 (100) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.980 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 1.080 [0.900, 1.260] | 0.0010 | 0.0040 |
| bm25 | 100 | 0.850 [0.670, 1.040] | 0.0010 | 0.0040 |
| hybrid | 100 | 0.790 [0.610, 0.980] | 0.0010 | 0.0040 |
| agentic | 100 | 0.780 [0.600, 0.970] | 0.0010 | 0.0040 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 75 | 1 | 0.0000 | 0.0000 | 0.241 |
| bm25 | 100 | 43 | 2 | 0.0000 | 0.0000 | 0.186 |
| hybrid | 100 | 40 | 2 | 0.0000 | 0.0000 | 0.179 |
| agentic | 100 | 39 | 3 | 0.0000 | 0.0000 | 0.179 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $-0.0001 [$-0.0002, $-0.0001] |
| agentic | $-0.0003 [$-0.0005, $-0.0002] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| hybrid+asof | 100 | 0.010 [-0.100, 0.130] | 1.0000 | 1.0000 | 8 | 8 | 1.0000 | 0.111 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 6.0% | no | -0.390 | no |
| bm25 | $0.0001 | 39.0% | yes | -0.160 | yes |
| hybrid | $0.0001 | 42.0% | yes | -0.100 | yes |
| agentic | $0.0002 | 44.0% | no | -0.090 | no |
| engine | $0.0002 | 80.0% | yes | 0.690 | yes |

