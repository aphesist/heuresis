# Results: brlaw-core, split `dev`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `hybrid`, `agentic`, `engine`. Completed per system: closed_book 100, hybrid 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 0.0% [0.0%, 3.7%] | 72.0% [62.5%, 79.9%] | 28.0% [20.1%, 37.5%] | -0.720 [-0.810, -0.630] |
| hybrid | 100 | 0.0% [0.0%, 3.7%] | 64.0% [54.2%, 72.7%] | 36.0% [27.3%, 45.8%] | -0.640 [-0.730, -0.550] |
| agentic | 100 | 0.0% [0.0%, 3.7%] | 73.0% [63.6%, 80.7%] | 27.0% [19.3%, 36.4%] | -0.730 [-0.820, -0.640] |
| engine | 100 | 0.0% [0.0%, 3.7%] | 87.0% [79.0%, 92.2%] | 13.0% [7.8%, 21.0%] | -0.870 [-0.930, -0.800] |
| agentic+asof (exploratory) | 100 | 0.0% [0.0%, 3.7%] | 76.0% [66.8%, 83.3%] | 24.0% [16.7%, 33.2%] | -0.760 [-0.840, -0.670] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 72 | 24 | 24.0% [16.7%, 33.2%] | -0.240 [-0.400, -0.080] | -0.720 [-0.810, -0.630] |
| hybrid | 100 | 64 | 32 | 32.0% [23.7%, 41.7%] | 0.000 [-0.160, 0.160] | -0.640 [-0.730, -0.550] |
| agentic | 100 | 73 | 35 | 35.0% [26.4%, 44.7%] | -0.030 [-0.200, 0.140] | -0.730 [-0.820, -0.640] |
| engine | 100 | 87 | 32 | 32.0% [23.7%, 41.7%] | -0.230 [-0.410, -0.050] | -0.870 [-0.930, -0.800] |
| agentic+asof (exploratory) | 100 | 76 | 41 | 41.0% [31.9%, 50.8%] | 0.060 [-0.110, 0.230] | -0.760 [-0.840, -0.670] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 0.0% | 72.0% | 0.0% | 1.000 | n/a (n=0) | 499.7 |
| hybrid | 100 | 0.0% | 64.0% | 0.0% | 1.000 | n/a (n=0) | 603.8 |
| agentic | 100 | 0.0% | 73.0% | 0.0% | 1.000 | n/a (n=0) | 551.9 |
| engine | 100 | 0.0% | 87.0% | 0.0% | 1.000 | n/a (n=0) | 448.9 |
| agentic+asof (exploratory) | 100 | 0.0% | 76.0% | 0.0% | 1.000 | n/a (n=0) | 580.4 |

## Table 2b. Errors (split `dev`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| agentic | 100 | 0 | 0 |
| engine | 100 | 0 | 0 |
| agentic+asof (exploratory) | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 3 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | $0.0007 | $0.0656 | n/a | 6606.6 | 8965.9 | 1.00 | 0.00 |
| hybrid | 100 | $0.0010 | $0.0992 | n/a | 5293.3 | 7972.7 | 1.00 | 1.00 |
| agentic | 100 | $0.0018 | $0.1789 | n/a | 7623.5 | 18273.9 | 2.92 | 1.92 |
| engine | 100 | $0.0025 | $0.2451 | n/a | 9546.9 | 22393.6 | 2.16 | 2.16 |
| agentic+asof (exploratory) | 100 | $0.0020 | $0.2015 | n/a | 7607.8 | 19227.2 | 3.02 | 2.02 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| hybrid | n/a | n/a | n/a | 0.337 (77) |
| agentic | n/a | n/a | n/a | 0.312 (77) |
| engine | 69 | 0.370 | 0.344 | 0.398 (77) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.349 (77) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | -0.150 [-0.250, -0.050] | 0.0059 | 0.0059 |
| hybrid | 100 | -0.230 [-0.320, -0.150] | 0.0001 | 0.0003 |
| agentic | 100 | -0.140 [-0.220, -0.070] | 0.0016 | 0.0032 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| hybrid | 100 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| agentic | 100 | 0 | 0 | 1.0000 | 1.0000 | n/a |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | n/a [n/a, n/a] |
| agentic | n/a [n/a, n/a] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| agentic+asof | 100 | -0.110 [-0.190, -0.030] | 0.0138 | 0.0138 | 0 | 0 | 1.0000 | n/a |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0007 | 0.0% | yes | -0.720 | yes |
| hybrid | $0.0010 | 0.0% | no | -0.640 | yes |
| agentic | $0.0018 | 0.0% | no | -0.730 | no |
| engine | $0.0025 | 0.0% | no | -0.870 | no |

