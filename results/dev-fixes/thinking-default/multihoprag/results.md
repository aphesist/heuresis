# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 37.0% [28.2%, 46.8%] | 6.0% [2.8%, 12.5%] | 57.0% [47.2%, 66.3%] | 0.310 [0.179, 0.444] |
| bm25 | 100 | 57.0% [47.2%, 66.3%] | 19.0% [12.5%, 27.8%] | 24.0% [16.7%, 33.2%] | 0.380 [0.216, 0.530] |
| hybrid | 100 | 58.0% [48.2%, 67.2%] | 18.0% [11.7%, 26.7%] | 24.0% [16.7%, 33.2%] | 0.400 [0.240, 0.542] |
| agentic | 100 | 64.0% [54.2%, 72.7%] | 22.0% [15.0%, 31.1%] | 14.0% [8.5%, 22.1%] | 0.420 [0.257, 0.560] |
| engine | 100 | 27.0% [19.3%, 36.4%] | 12.0% [7.0%, 19.8%] | 61.0% [51.2%, 70.0%] | 0.150 [-0.010, 0.303] |
| hybrid+asof (exploratory) | 100 | 60.0% [50.2%, 69.1%] | 17.0% [10.9%, 25.5%] | 23.0% [15.8%, 32.2%] | 0.430 [0.271, 0.586] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 2 | 0 | 37.0% [28.2%, 46.8%] | 0.310 [0.179, 0.444] | 0.310 [0.179, 0.444] |
| bm25 | 100 | 19 | 3 | 60.0% [50.2%, 69.1%] | 0.440 [0.274, 0.587] | 0.380 [0.216, 0.530] |
| hybrid | 100 | 18 | 1 | 59.0% [49.2%, 68.1%] | 0.420 [0.271, 0.557] | 0.400 [0.240, 0.542] |
| agentic | 100 | 22 | 1 | 65.0% [55.3%, 73.6%] | 0.440 [0.274, 0.583] | 0.420 [0.257, 0.560] |
| engine | 100 | 12 | 0 | 27.0% [19.3%, 36.4%] | 0.150 [-0.010, 0.303] | 0.150 [-0.010, 0.303] |
| hybrid+asof (exploratory) | 100 | 17 | 3 | 63.0% [53.2%, 71.8%] | 0.490 [0.337, 0.630] | 0.430 [0.271, 0.586] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 37.0% | 35.0% | 82.9% | 0.046 | 66.7% (n=12) | 238.7 |
| bm25 | 100 | 57.0% | 64.0% | 70.3% | 0.149 | 100.0% (n=12) | 291.0 |
| hybrid | 100 | 58.0% | 64.0% | 71.9% | 0.154 | 100.0% (n=12) | 281.1 |
| agentic | 100 | 64.0% | 74.0% | 70.3% | 0.109 | 100.0% (n=12) | 297.3 |
| engine | 100 | 27.0% | 27.0% | 55.6% | 0.454 | 100.0% (n=12) | 141.0 |
| hybrid+asof (exploratory) | 100 | 60.0% | 65.0% | 73.8% | 0.133 | 100.0% (n=12) | 284.1 |

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
| closed_book | 100 | $0.0002 | $0.0185 | $0.0005 [$0.0004, $0.0007] | 2005.2 | 3791.3 | 1.00 | 0.00 |
| bm25 | 100 | $0.0006 | $0.0622 | $0.0011 [$0.0009, $0.0013] | 2450.9 | 4221.3 | 1.00 | 1.00 |
| hybrid | 100 | $0.0006 | $0.0623 | $0.0011 [$0.0009, $0.0013] | 2813.8 | 4335.2 | 1.00 | 1.00 |
| agentic | 100 | $0.0012 | $0.1210 | $0.0019 [$0.0016, $0.0023] | 5328.0 | 9255.9 | 3.03 | 2.03 |
| engine | 100 | $0.0007 | $0.0730 | $0.0027 [$0.0019, $0.0046] | 4285.8 | 7322.5 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0006 | $0.0623 | $0.0010 [$0.0009, $0.0013] | 2740.8 | 4098.5 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.589 (88) |
| hybrid | n/a | n/a | n/a | 0.576 (88) |
| agentic | n/a | n/a | n/a | 0.577 (88) |
| engine | 27 | 0.537 | 0.392 | 0.594 (88) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.576 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | -0.160 [-0.324, 0.009] | 0.0749 | 0.0749 |
| bm25 | 100 | -0.230 [-0.429, -0.041] | 0.0300 | 0.0599 |
| hybrid | 100 | -0.250 [-0.434, -0.069] | 0.0180 | 0.0539 |
| agentic | 100 | -0.270 [-0.442, -0.109] | 0.0030 | 0.0120 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 5 | 15 | 0.0414 | 0.0414 | 0.124 |
| bm25 | 100 | 5 | 35 | 0.0000 | 0.0000 | 0.175 |
| hybrid | 100 | 4 | 35 | 0.0000 | 0.0000 | 0.173 |
| agentic | 100 | 0 | 37 | 0.0000 | 0.0000 | 0.168 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0016 [$0.0008, $0.0035] |
| agentic | $0.0008 [$-0.0000, $0.0027] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| hybrid+asof | 100 | -0.280 [-0.458, -0.111] | 0.0060 | 0.0060 | 2 | 35 | 0.0000 | 0.168 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 37.0% | yes | 0.310 | yes |
| bm25 | $0.0006 | 57.0% | yes | 0.380 | yes |
| hybrid | $0.0006 | 58.0% | yes | 0.400 | yes |
| agentic | $0.0012 | 64.0% | yes | 0.420 | yes |
| engine | $0.0007 | 27.0% | no | 0.150 | no |

