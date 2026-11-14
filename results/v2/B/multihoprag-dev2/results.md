# Results: multihoprag, split `dev2`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `hybrid`, `agentic`, `engine`, `engine2`. Completed per system: closed_book 100, hybrid 100, agentic 100, engine 100, engine2 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 37.0% [28.2%, 46.8%] | 15.0% [9.3%, 23.3%] | 48.0% [38.5%, 57.7%] | 0.220 [0.075, 0.349] |
| hybrid | 100 | 59.0% [49.2%, 68.1%] | 7.0% [3.4%, 13.7%] | 34.0% [25.5%, 43.7%] | 0.520 [0.388, 0.642] |
| agentic | 100 | 68.0% [58.3%, 76.3%] | 18.0% [11.7%, 26.7%] | 14.0% [8.5%, 22.1%] | 0.500 [0.337, 0.652] |
| engine | 100 | 45.0% [35.6%, 54.8%] | 48.0% [38.5%, 57.7%] | 7.0% [3.4%, 13.7%] | -0.030 [-0.231, 0.175] |
| engine2 | 100 | 51.0% [41.3%, 60.6%] | 12.0% [7.0%, 19.8%] | 37.0% [28.2%, 46.8%] | 0.390 [0.257, 0.514] |
| agentic+asof (exploratory) | 100 | 75.0% [65.7%, 82.5%] | 14.0% [8.5%, 22.1%] | 11.0% [6.3%, 18.6%] | 0.610 [0.464, 0.744] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 7 | 3 | 40.0% [30.9%, 49.8%] | 0.280 [0.131, 0.412] | 0.220 [0.075, 0.349] |
| hybrid | 100 | 7 | 1 | 60.0% [50.2%, 69.1%] | 0.540 [0.411, 0.657] | 0.520 [0.388, 0.642] |
| agentic | 100 | 18 | 4 | 72.0% [62.5%, 79.9%] | 0.580 [0.429, 0.723] | 0.500 [0.337, 0.652] |
| engine | 100 | 48 | 6 | 51.0% [41.3%, 60.6%] | 0.090 [-0.120, 0.300] | -0.030 [-0.231, 0.175] |
| engine2 | 100 | 12 | 6 | 57.0% [47.2%, 66.3%] | 0.510 [0.387, 0.629] | 0.390 [0.257, 0.514] |
| agentic+asof (exploratory) | 100 | 14 | 2 | 77.0% [67.8%, 84.2%] | 0.650 [0.505, 0.779] | 0.610 [0.464, 0.744] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 37.0% | 48.0% | 68.8% | 31.2% [19.9%, 45.3%] (15/48) | 0.134 | 33.3% (n=12) | 248.2 |
| hybrid | 100 | 59.0% | 54.0% | 87.0% | 13.0% [6.4%, 24.4%] (7/54) | 0.077 | 100.0% (n=12) | 295.0 |
| agentic | 100 | 68.0% | 74.0% | 75.7% | 24.3% [16.0%, 35.2%] (18/74) | 0.105 | 100.0% (n=12) | 325.8 |
| engine | 100 | 45.0% | 81.0% | 40.7% | 59.3% [48.4%, 69.3%] (48/81) | 0.627 | 100.0% (n=12) | 264.8 |
| engine2 | 100 | 51.0% | 51.0% | 76.5% | 23.5% [14.0%, 36.8%] (12/51) | 0.337 | 100.0% (n=12) | 772.7 |
| agentic+asof (exploratory) | 100 | 75.0% | 77.0% | 81.8% | 18.2% [11.2%, 28.2%] (14/77) | 0.094 | 100.0% (n=12) | 322.3 |

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
| closed_book | 100 | $0.0002 | $0.0198 | $0.0005 [$0.0004, $0.0008] | 2120.6 | 3974.4 | 1.00 | 0.00 |
| hybrid | 100 | $0.0006 | $0.0593 | $0.0010 [$0.0009, $0.0012] | 1843.6 | 3852.0 | 1.00 | 1.00 |
| agentic | 100 | $0.0013 | $0.1274 | $0.0019 [$0.0016, $0.0023] | 4647.6 | 9136.6 | 3.08 | 2.08 |
| engine | 100 | $0.0016 | $0.1581 | $0.0035 [$0.0027, $0.0047] | 4809.3 | 9265.5 | 1.88 | 1.88 |
| engine2 | 100 | $0.0076 | $0.7614 | $0.0149 [$0.0124, $0.0185] | 6492.0 | 11020.9 | 2.72 | 2.51 |
| agentic+asof (exploratory) | 100 | $0.0012 | $0.1234 | $0.0016 [$0.0014, $0.0019] | 4725.2 | 8469.2 | 3.03 | 2.03 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| hybrid | n/a | n/a | n/a | 0.467 (88) |
| agentic | n/a | n/a | n/a | 0.595 (88) |
| engine | 81 | 0.506 | 0.533 | 0.608 (88) |
| engine2 | 51 | 0.506 | 0.696 | 0.747 (88) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.589 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine2` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | 0.170 [0.010, 0.344] | 0.0677 | 0.2031 |
| hybrid | 100 | -0.130 [-0.258, 0.000] | 0.0680 | 0.2031 |
| agentic | 100 | -0.110 [-0.234, 0.020] | 0.1309 | 0.2031 |
| engine | 100 | 0.420 [0.205, 0.628] | 0.0008 | 0.0032 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 24 | 10 | 0.0243 | 0.0729 | 0.161 |
| hybrid | 100 | 9 | 17 | 0.1686 | 0.3373 | 0.141 |
| agentic | 100 | 4 | 21 | 0.0009 | 0.0036 | 0.138 |
| engine | 100 | 21 | 15 | 0.4050 | 0.4050 | 0.166 |

## Table 5b. Cost per correct answer, `engine2` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0139 [$0.0115, $0.0174] |
| agentic | $0.0131 [$0.0107, $0.0164] |

## Table 6. Exploratory: `engine2` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| agentic+asof | 100 | -0.220 [-0.367, -0.079] | 0.0050 | 0.0050 | 3 | 27 | 0.0000 | 0.152 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 37.0% | yes | 0.220 | yes |
| hybrid | $0.0006 | 59.0% | yes | 0.520 | yes |
| agentic | $0.0013 | 68.0% | yes | 0.500 | no |
| engine | $0.0016 | 45.0% | no | -0.030 | no |
| engine2 | $0.0076 | 51.0% | no | 0.390 | no |

