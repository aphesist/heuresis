# Results: multihoprag, split `dev2`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 36.0% [27.3%, 45.8%] | 25.0% [17.5%, 34.3%] | 39.0% [30.0%, 48.8%] | 0.110 [-0.063, 0.263] |
| bm25 | 100 | 48.0% [38.5%, 57.7%] | 8.0% [4.1%, 15.0%] | 44.0% [34.7%, 53.8%] | 0.400 [0.274, 0.521] |
| hybrid | 100 | 51.0% [41.3%, 60.6%] | 8.0% [4.1%, 15.0%] | 41.0% [31.9%, 50.8%] | 0.430 [0.293, 0.553] |
| hybrid_rerank | 100 | 47.0% [37.5%, 56.7%] | 5.0% [2.2%, 11.2%] | 48.0% [38.5%, 57.7%] | 0.420 [0.292, 0.528] |
| agentic | 100 | 45.0% [35.6%, 54.8%] | 34.0% [25.5%, 43.7%] | 21.0% [14.2%, 30.0%] | 0.110 [-0.076, 0.269] |
| engine | 100 | 36.0% [27.3%, 45.8%] | 46.0% [36.6%, 55.7%] | 18.0% [11.7%, 26.7%] | -0.100 [-0.275, 0.086] |
| engine_single (exploratory) | 100 | 23.0% [15.8%, 32.2%] | 13.0% [7.8%, 21.0%] | 64.0% [54.2%, 72.7%] | 0.100 [-0.031, 0.226] |
| hybrid+asof (exploratory) | 100 | 51.0% [41.3%, 60.6%] | 8.0% [4.1%, 15.0%] | 41.0% [31.9%, 50.8%] | 0.430 [0.283, 0.550] |
| agentic+asof (exploratory) | 100 | 41.0% [31.9%, 50.8%] | 29.0% [21.0%, 38.5%] | 30.0% [21.9%, 39.6%] | 0.120 [-0.045, 0.257] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 23 | 0 | 36.0% [27.3%, 45.8%] | 0.110 [-0.063, 0.263] | 0.110 [-0.063, 0.263] |
| bm25 | 100 | 8 | 2 | 50.0% [40.4%, 59.6%] | 0.440 [0.323, 0.554] | 0.400 [0.274, 0.521] |
| hybrid | 100 | 8 | 2 | 53.0% [43.3%, 62.5%] | 0.470 [0.341, 0.585] | 0.430 [0.293, 0.553] |
| hybrid_rerank | 100 | 5 | 0 | 47.0% [37.5%, 56.7%] | 0.420 [0.292, 0.528] | 0.420 [0.292, 0.528] |
| agentic | 100 | 33 | 5 | 50.0% [40.4%, 59.6%] | 0.210 [0.032, 0.369] | 0.110 [-0.076, 0.269] |
| engine | 100 | 46 | 12 | 48.0% [38.5%, 57.7%] | 0.140 [-0.029, 0.329] | -0.100 [-0.275, 0.086] |
| engine_single (exploratory) | 100 | 13 | 5 | 28.0% [20.1%, 37.5%] | 0.200 [0.080, 0.313] | 0.100 [-0.031, 0.226] |
| hybrid+asof (exploratory) | 100 | 8 | 2 | 53.0% [43.3%, 62.5%] | 0.470 [0.340, 0.587] | 0.430 [0.283, 0.550] |
| agentic+asof (exploratory) | 100 | 28 | 4 | 45.0% [35.6%, 54.8%] | 0.200 [0.034, 0.340] | 0.120 [-0.045, 0.257] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 36.0% | 51.0% | 51.0% | 0.179 | 83.3% (n=12) | 297.4 |
| bm25 | 100 | 48.0% | 44.0% | 81.8% | 0.053 | 100.0% (n=12) | 314.2 |
| hybrid | 100 | 51.0% | 47.0% | 83.0% | 0.085 | 100.0% (n=12) | 336.2 |
| hybrid_rerank | 100 | 47.0% | 40.0% | 87.5% | 0.022 | 100.0% (n=12) | 320.9 |
| agentic | 100 | 45.0% | 68.0% | 50.0% | 0.266 | 91.7% (n=12) | 382.7 |
| engine | 100 | 36.0% | 70.0% | 34.3% | 0.583 | 100.0% (n=12) | 300.6 |
| engine_single (exploratory) | 100 | 23.0% | 24.0% | 45.8% | 0.558 | 100.0% (n=12) | 209.4 |
| hybrid+asof (exploratory) | 100 | 51.0% | 47.0% | 83.0% | 0.054 | 100.0% (n=12) | 325.5 |
| agentic+asof (exploratory) | 100 | 41.0% | 59.0% | 50.8% | 0.233 | 91.7% (n=12) | 382.2 |

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
| closed_book | 100 | $0.0001 | $0.0053 | $0.0001 [$0.0001, $0.0002] | 1014.1 | 1874.6 | 1.00 | 0.00 |
| bm25 | 100 | $0.0005 | $0.0459 | $0.0010 [$0.0008, $0.0012] | 997.0 | 1475.3 | 1.00 | 1.00 |
| hybrid | 100 | $0.0005 | $0.0462 | $0.0009 [$0.0008, $0.0011] | 1267.7 | 1907.3 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0005 | $0.0473 | $0.0010 [$0.0008, $0.0013] | 11785.7 | 14556.9 | 1.00 | 1.00 |
| agentic | 100 | $0.0006 | $0.0619 | $0.0014 [$0.0011, $0.0018] | 2364.6 | 3949.1 | 2.42 | 1.42 |
| engine | 100 | $0.0009 | $0.0854 | $0.0024 [$0.0018, $0.0032] | 5249.7 | 9265.4 | 1.40 | 1.40 |
| engine_single (exploratory) | 100 | $0.0005 | $0.0533 | $0.0023 [$0.0017, $0.0036] | 4290.5 | 7847.1 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0005 | $0.0462 | $0.0009 [$0.0008, $0.0011] | 1288.8 | 2116.6 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0006 | $0.0621 | $0.0015 [$0.0012, $0.0020] | 2380.0 | 4425.0 | 2.45 | 1.45 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.528 (88) |
| hybrid | n/a | n/a | n/a | 0.467 (88) |
| hybrid_rerank | n/a | n/a | n/a | 0.383 (88) |
| agentic | n/a | n/a | n/a | 0.497 (88) |
| engine | 70 | 0.452 | 0.512 | 0.583 (88) |
| engine_single (exploratory) | 24 | 0.376 | 0.358 | 0.521 (88) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.467 (88) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.489 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | -0.210 [-0.471, 0.061] | 0.1748 | 0.2398 |
| bm25 | 100 | -0.500 [-0.703, -0.290] | 0.0010 | 0.0050 |
| hybrid | 100 | -0.530 [-0.727, -0.316] | 0.0010 | 0.0050 |
| hybrid_rerank | 100 | -0.520 [-0.744, -0.294] | 0.0010 | 0.0050 |
| agentic | 100 | -0.210 [-0.439, 0.030] | 0.1199 | 0.2398 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 17 | 17 | 1.0000 | 1.0000 | 0.161 |
| bm25 | 100 | 11 | 23 | 0.0576 | 0.2305 | 0.161 |
| hybrid | 100 | 7 | 22 | 0.0081 | 0.0407 | 0.149 |
| hybrid_rerank | 100 | 12 | 23 | 0.0895 | 0.2686 | 0.164 |
| agentic | 100 | 9 | 18 | 0.1221 | 0.2686 | 0.144 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0015 [$0.0009, $0.0023] |
| agentic | $0.0010 [$0.0004, $0.0018] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| engine_single | 100 | -0.200 [-0.411, 0.010] | 0.1079 | 0.2098 | 19 | 6 | 0.0146 | 0.138 |
| hybrid+asof | 100 | -0.530 [-0.732, -0.316] | 0.0010 | 0.0030 | 8 | 23 | 0.0107 | 0.154 |
| agentic+asof | 100 | -0.220 [-0.454, 0.031] | 0.1049 | 0.2098 | 14 | 19 | 0.4869 | 0.159 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0001 | 36.0% | yes | 0.110 | yes |
| bm25 | $0.0005 | 48.0% | yes | 0.400 | yes |
| hybrid | $0.0005 | 51.0% | yes | 0.430 | yes |
| hybrid_rerank | $0.0005 | 47.0% | no | 0.420 | no |
| agentic | $0.0006 | 45.0% | no | 0.110 | no |
| engine | $0.0009 | 36.0% | no | -0.100 | no |

