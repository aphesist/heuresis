# Results: hoh, split `dev2`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `hybrid`, `agentic`, `engine`, `engine2`. Completed per system: closed_book 100, hybrid 100, agentic 100, engine 100, engine2 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 9.0% [4.8%, 16.2%] | 36.0% [27.3%, 45.8%] | 55.0% [45.2%, 64.4%] | -0.270 [-0.390, -0.150] |
| hybrid | 100 | 35.0% [26.4%, 44.7%] | 55.0% [45.2%, 64.4%] | 10.0% [5.5%, 17.4%] | -0.200 [-0.380, -0.020] |
| agentic | 100 | 37.0% [28.2%, 46.8%] | 57.0% [47.2%, 66.3%] | 6.0% [2.8%, 12.5%] | -0.200 [-0.380, -0.010] |
| engine | 100 | 76.0% [66.8%, 83.3%] | 18.0% [11.7%, 26.7%] | 6.0% [2.8%, 12.5%] | 0.580 [0.420, 0.730] |
| engine2 | 100 | 74.0% [64.6%, 81.6%] | 13.0% [7.8%, 21.0%] | 13.0% [7.8%, 21.0%] | 0.610 [0.470, 0.740] |
| agentic+asof (exploratory) | 100 | 81.0% [72.2%, 87.5%] | 14.0% [8.5%, 22.1%] | 5.0% [2.2%, 11.2%] | 0.670 [0.530, 0.800] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 36 | 6 | 15.0% [9.3%, 23.3%] | -0.150 [-0.280, -0.020] | -0.270 [-0.390, -0.150] |
| hybrid | 100 | 55 | 11 | 46.0% [36.6%, 55.7%] | 0.020 [-0.170, 0.200] | -0.200 [-0.380, -0.020] |
| agentic | 100 | 57 | 12 | 49.0% [39.4%, 58.7%] | 0.040 [-0.150, 0.230] | -0.200 [-0.380, -0.010] |
| engine | 100 | 18 | 11 | 87.0% [79.0%, 92.2%] | 0.800 [0.680, 0.900] | 0.580 [0.420, 0.730] |
| engine2 | 100 | 13 | 12 | 86.0% [77.9%, 91.5%] | 0.850 [0.770, 0.920] | 0.610 [0.470, 0.740] |
| agentic+asof (exploratory) | 100 | 14 | 12 | 93.0% [86.3%, 96.6%] | 0.910 [0.830, 0.970] | 0.670 [0.530, 0.800] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 9.0% | 45.0% | 20.0% | 80.0% [66.2%, 89.1%] (36/45) | 0.774 | n/a (n=0) | 191.4 |
| hybrid | 100 | 35.0% | 90.0% | 38.9% | 61.1% [50.8%, 70.5%] (55/90) | 0.610 | n/a (n=0) | 113.6 |
| agentic | 100 | 37.0% | 94.0% | 39.4% | 60.6% [50.5%, 69.9%] (57/94) | 0.557 | n/a (n=0) | 123.6 |
| engine | 100 | 76.0% | 94.0% | 80.9% | 19.1% [12.5%, 28.3%] (18/94) | 0.131 | n/a (n=0) | 96.4 |
| engine2 | 100 | 74.0% | 87.0% | 85.1% | 14.9% [8.9%, 23.9%] (13/87) | 0.180 | n/a (n=0) | 165.0 |
| agentic+asof (exploratory) | 100 | 81.0% | 95.0% | 85.3% | 14.7% [9.0%, 23.2%] (14/95) | 0.100 | n/a (n=0) | 136.8 |

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
| closed_book | 100 | $0.0002 | $0.0206 | $0.0023 [$0.0014, $0.0052] | 2125.6 | 4060.5 | 1.00 | 0.00 |
| hybrid | 100 | $0.0002 | $0.0155 | $0.0004 [$0.0003, $0.0006] | 2654.9 | 18061.0 | 1.00 | 1.00 |
| agentic | 100 | $0.0002 | $0.0235 | $0.0006 [$0.0005, $0.0009] | 5079.8 | 21409.2 | 2.31 | 1.31 |
| engine | 100 | $0.0003 | $0.0257 | $0.0003 [$0.0003, $0.0004] | 1190.3 | 9185.8 | 1.15 | 1.15 |
| engine2 | 100 | $0.0027 | $0.2676 | $0.0036 [$0.0031, $0.0043] | 5338.0 | 20906.8 | 2.39 | 1.37 |
| agentic+asof (exploratory) | 100 | $0.0002 | $0.0244 | $0.0003 [$0.0003, $0.0004] | 3866.6 | 18383.4 | 2.30 | 1.30 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| hybrid | n/a | n/a | n/a | 0.930 (100) |
| agentic | n/a | n/a | n/a | 0.970 (100) |
| engine | 94 | 0.922 | 0.989 | 1.000 (100) |
| engine2 | 87 | 0.893 | 0.989 | 1.000 (100) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.960 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine2` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.880 [0.710, 1.050] | 0.0001 | 0.0004 |
| hybrid | 100 | 0.810 [0.620, 1.010] | 0.0001 | 0.0004 |
| agentic | 100 | 0.810 [0.610, 1.010] | 0.0001 | 0.0004 |
| engine | 100 | 0.030 [-0.090, 0.160] | 0.7591 | 0.7591 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 67 | 2 | 0.0000 | 0.0000 | 0.230 |
| hybrid | 100 | 42 | 3 | 0.0000 | 0.0000 | 0.186 |
| agentic | 100 | 41 | 4 | 0.0000 | 0.0000 | 0.186 |
| engine | 100 | 6 | 8 | 0.7905 | 0.7905 | 0.104 |

## Table 5b. Cost per correct answer, `engine2` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0032 [$0.0027, $0.0038] |
| agentic | $0.0030 [$0.0025, $0.0036] |

## Table 6. Exploratory: `engine2` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| agentic+asof | 100 | -0.060 [-0.180, 0.050] | 0.3938 | 0.3938 | 4 | 11 | 0.1185 | 0.107 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 9.0% | no | -0.270 | no |
| hybrid | $0.0002 | 35.0% | yes | -0.200 | yes |
| agentic | $0.0002 | 37.0% | yes | -0.200 | no |
| engine | $0.0003 | 76.0% | yes | 0.580 | yes |
| engine2 | $0.0027 | 74.0% | no | 0.610 | yes |

