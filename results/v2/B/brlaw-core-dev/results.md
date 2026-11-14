# Results: brlaw-core, split `dev`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `hybrid`, `agentic`, `engine`, `engine2`. Completed per system: closed_book 100, hybrid 100, agentic 100, engine 100, engine2 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 0.0% [0.0%, 3.7%] | 75.0% [65.7%, 82.5%] | 25.0% [17.5%, 34.3%] | -0.750 [-0.830, -0.660] |
| hybrid | 100 | 0.0% [0.0%, 3.7%] | 62.0% [52.2%, 70.9%] | 38.0% [29.1%, 47.8%] | -0.620 [-0.710, -0.520] |
| agentic | 100 | 0.0% [0.0%, 3.7%] | 75.0% [65.7%, 82.5%] | 25.0% [17.5%, 34.3%] | -0.750 [-0.830, -0.660] |
| engine | 100 | 0.0% [0.0%, 3.7%] | 76.0% [66.8%, 83.3%] | 24.0% [16.7%, 33.2%] | -0.760 [-0.840, -0.670] |
| engine2 | 100 | 0.0% [0.0%, 3.7%] | 41.0% [31.9%, 50.8%] | 59.0% [49.2%, 68.1%] | -0.410 [-0.510, -0.310] |
| agentic+asof (exploratory) | 100 | 0.0% [0.0%, 3.7%] | 73.0% [63.6%, 80.7%] | 27.0% [19.3%, 36.4%] | -0.730 [-0.810, -0.640] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 75 | 28 | 28.0% [20.1%, 37.5%] | -0.190 [-0.360, -0.020] | -0.750 [-0.830, -0.660] |
| hybrid | 100 | 62 | 35 | 35.0% [26.4%, 44.7%] | 0.080 [-0.070, 0.240] | -0.620 [-0.710, -0.520] |
| agentic | 100 | 75 | 36 | 36.0% [27.3%, 45.8%] | -0.030 [-0.200, 0.140] | -0.750 [-0.830, -0.660] |
| engine | 100 | 76 | 25 | 25.0% [17.5%, 34.3%] | -0.260 [-0.420, -0.090] | -0.760 [-0.840, -0.670] |
| engine2 | 100 | 41 | 25 | 25.0% [17.5%, 34.3%] | 0.090 [-0.030, 0.210] | -0.410 [-0.510, -0.310] |
| agentic+asof (exploratory) | 100 | 73 | 40 | 40.0% [30.9%, 49.8%] | 0.070 [-0.100, 0.240] | -0.730 [-0.810, -0.640] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 0.0% | 75.0% | 0.0% | 100.0% [95.1%, 100.0%] (75/75) | 1.000 | n/a (n=0) | 486.8 |
| hybrid | 100 | 0.0% | 62.0% | 0.0% | 100.0% [94.2%, 100.0%] (62/62) | 1.000 | n/a (n=0) | 620.3 |
| agentic | 100 | 0.0% | 75.0% | 0.0% | 100.0% [95.1%, 100.0%] (75/75) | 1.000 | n/a (n=0) | 579.1 |
| engine | 100 | 0.0% | 76.0% | 0.0% | 100.0% [95.2%, 100.0%] (76/76) | 1.000 | n/a (n=0) | 439.0 |
| engine2 | 100 | 0.0% | 41.0% | 0.0% | 100.0% [91.4%, 100.0%] (41/41) | 1.000 | n/a (n=0) | 1120.2 |
| agentic+asof (exploratory) | 100 | 0.0% | 73.0% | 0.0% | 100.0% [95.0%, 100.0%] (73/73) | 1.000 | n/a (n=0) | 586.9 |

## Table 2b. Errors (split `dev`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| agentic | 100 | 0 | 0 |
| engine | 100 | 0 | 0 |
| engine2 | 100 | 0 | 0 |
| agentic+asof (exploratory) | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | $0.0007 | $0.0672 | n/a | 6742.1 | 9525.2 | 1.00 | 0.00 |
| hybrid | 100 | $0.0010 | $0.0988 | n/a | 5976.7 | 9038.3 | 1.00 | 1.00 |
| agentic | 100 | $0.0019 | $0.1879 | n/a | 9309.2 | 23944.7 | 3.01 | 2.01 |
| engine | 100 | $0.0030 | $0.2964 | n/a | 17311.1 | 31050.8 | 3.15 | 2.39 |
| engine2 | 100 | $0.0119 | $1.1943 | n/a | 12486.7 | 34273.6 | 3.09 | 4.19 |
| agentic+asof (exploratory) | 100 | $0.0020 | $0.1989 | n/a | 8059.3 | 19357.4 | 3.04 | 2.04 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| hybrid | n/a | n/a | n/a | 0.337 (77) |
| agentic | n/a | n/a | n/a | 0.335 (77) |
| engine | 63 | 0.354 | 0.315 | 0.374 (77) |
| engine2 | 37 | 0.404 | 0.548 | 0.460 (77) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.376 (77) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine2` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.340 [0.230, 0.450] | 0.0001 | 0.0004 |
| hybrid | 100 | 0.210 [0.110, 0.310] | 0.0002 | 0.0004 |
| agentic | 100 | 0.340 [0.240, 0.440] | 0.0001 | 0.0004 |
| engine | 100 | 0.350 [0.240, 0.460] | 0.0001 | 0.0004 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| hybrid | 100 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| agentic | 100 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| engine | 100 | 0 | 0 | 1.0000 | 1.0000 | n/a |

## Table 5b. Cost per correct answer, `engine2` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | n/a [n/a, n/a] |
| agentic | n/a [n/a, n/a] |

## Table 6. Exploratory: `engine2` against the time-aware variants and the earlier engine design (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| agentic+asof | 100 | 0.320 [0.230, 0.410] | 0.0001 | 0.0001 | 0 | 0 | 1.0000 | n/a |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0007 | 0.0% | yes | -0.750 | yes |
| hybrid | $0.0010 | 0.0% | no | -0.620 | yes |
| agentic | $0.0019 | 0.0% | no | -0.750 | no |
| engine | $0.0030 | 0.0% | no | -0.760 | no |
| engine2 | $0.0119 | 0.0% | no | -0.410 | yes |

