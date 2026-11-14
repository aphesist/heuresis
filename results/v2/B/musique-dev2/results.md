# Results: musique, split `dev2`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `hybrid`, `agentic`, `engine`, `engine2`. Completed per system: closed_book 100, hybrid 100, agentic 100, engine 100, engine2 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 25.0% [17.5%, 34.3%] | 28.0% [20.1%, 37.5%] | 47.0% [37.5%, 56.7%] | -0.030 [-0.175, 0.117] |
| hybrid | 100 | 21.0% [14.2%, 30.0%] | 6.0% [2.8%, 12.5%] | 73.0% [63.6%, 80.7%] | 0.150 [0.051, 0.250] |
| agentic | 100 | 48.0% [38.5%, 57.7%] | 15.0% [9.3%, 23.3%] | 37.0% [28.2%, 46.8%] | 0.330 [0.190, 0.466] |
| engine | 100 | 46.0% [36.6%, 55.7%] | 21.0% [14.2%, 30.0%] | 33.0% [24.6%, 42.7%] | 0.250 [0.098, 0.400] |
| engine2 | 100 | 37.0% [28.2%, 46.8%] | 3.0% [1.0%, 8.5%] | 60.0% [50.2%, 69.1%] | 0.340 [0.240, 0.444] |
| agentic+asof (exploratory) | 100 | 51.0% [41.3%, 60.6%] | 7.0% [3.4%, 13.7%] | 42.0% [32.8%, 51.8%] | 0.440 [0.320, 0.559] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 28 | 3 | 28.0% [20.1%, 37.5%] | 0.030 [-0.118, 0.173] | -0.030 [-0.175, 0.117] |
| hybrid | 100 | 6 | 2 | 23.0% [15.8%, 32.2%] | 0.190 [0.098, 0.286] | 0.150 [0.051, 0.250] |
| agentic | 100 | 15 | 5 | 53.0% [43.3%, 62.5%] | 0.430 [0.300, 0.558] | 0.330 [0.190, 0.466] |
| engine | 100 | 21 | 5 | 51.0% [41.3%, 60.6%] | 0.350 [0.204, 0.495] | 0.250 [0.098, 0.400] |
| engine2 | 100 | 3 | 1 | 38.0% [29.1%, 47.8%] | 0.360 [0.260, 0.464] | 0.340 [0.240, 0.444] |
| agentic+asof (exploratory) | 100 | 7 | 3 | 54.0% [44.3%, 63.4%] | 0.500 [0.388, 0.608] | 0.440 [0.320, 0.559] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 25.0% | 53.0% | 47.2% | 52.8% [39.7%, 65.6%] (28/53) | 0.355 | n/a (n=0) | 222.2 |
| hybrid | 100 | 21.0% | 27.0% | 77.8% | 22.2% [10.6%, 40.8%] (6/27) | 0.088 | n/a (n=0) | 180.9 |
| agentic | 100 | 48.0% | 63.0% | 76.2% | 23.8% [15.0%, 35.6%] (15/63) | 0.093 | n/a (n=0) | 219.3 |
| engine | 100 | 46.0% | 67.0% | 68.7% | 31.3% [21.5%, 43.2%] (21/67) | 0.227 | n/a (n=0) | 172.8 |
| engine2 | 100 | 37.0% | 40.0% | 92.5% | 7.5% [2.6%, 19.9%] (3/40) | 0.036 | n/a (n=0) | 379.8 |
| agentic+asof (exploratory) | 100 | 51.0% | 58.0% | 87.9% | 12.1% [6.0%, 22.9%] (7/58) | 0.069 | n/a (n=0) | 215.2 |

## Table 2b. Errors (split `dev2`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| agentic | 100 | 0 | 0 |
| engine | 100 | 0 | 0 |
| engine2 | 100 | 0 | 0 |
| agentic+asof (exploratory) | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev2`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | $0.0003 | $0.0285 | $0.0011 [$0.0008, $0.0018] | 2665.5 | 5181.2 | 1.00 | 0.00 |
| hybrid | 100 | $0.0003 | $0.0312 | $0.0015 [$0.0011, $0.0023] | 1518.3 | 2916.5 | 1.00 | 1.00 |
| agentic | 100 | $0.0009 | $0.0906 | $0.0019 [$0.0015, $0.0025] | 5007.7 | 9293.1 | 3.46 | 2.46 |
| engine | 100 | $0.0017 | $0.1731 | $0.0038 [$0.0028, $0.0052] | 4817.2 | 13296.8 | 2.99 | 2.99 |
| engine2 | 100 | $0.0052 | $0.5206 | $0.0141 [$0.0110, $0.0189] | 7722.1 | 15342.5 | 3.90 | 4.46 |
| agentic+asof (exploratory) | 100 | $0.0009 | $0.0908 | $0.0018 [$0.0014, $0.0023] | 5284.4 | 9211.4 | 3.48 | 2.48 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| hybrid | n/a | n/a | n/a | 0.534 (100) |
| agentic | n/a | n/a | n/a | 0.763 (100) |
| engine | 67 | 0.873 | 0.801 | 0.853 (100) |
| engine2 | 40 | 0.923 | 0.938 | 0.902 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.765 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine2` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.370 [0.202, 0.540] | 0.0002 | 0.0008 |
| hybrid | 100 | 0.190 [0.094, 0.290] | 0.0006 | 0.0018 |
| agentic | 100 | 0.010 [-0.110, 0.130] | 1.0000 | 1.0000 |
| engine | 100 | 0.090 [-0.040, 0.225] | 0.2609 | 0.5217 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 27 | 15 | 0.0884 | 0.1299 | 0.179 |
| hybrid | 100 | 21 | 5 | 0.0025 | 0.0100 | 0.141 |
| agentic | 100 | 7 | 18 | 0.0433 | 0.1299 | 0.138 |
| engine | 100 | 5 | 14 | 0.0636 | 0.1299 | 0.121 |

## Table 5b. Cost per correct answer, `engine2` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0126 [$0.0096, $0.0171] |
| agentic | $0.0122 [$0.0093, $0.0167] |

## Table 6. Exploratory: `engine2` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| agentic+asof | 100 | -0.100 [-0.202, 0.010] | 0.0955 | 0.0955 | 4 | 18 | 0.0043 | 0.130 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0003 | 25.0% | yes | -0.030 | yes |
| hybrid | $0.0003 | 21.0% | no | 0.150 | yes |
| agentic | $0.0009 | 48.0% | yes | 0.330 | yes |
| engine | $0.0017 | 46.0% | no | 0.250 | no |
| engine2 | $0.0052 | 37.0% | no | 0.340 | yes |

