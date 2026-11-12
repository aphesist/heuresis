# Results: multihoprag, split `dev2`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 44.0% [34.7%, 53.8%] | 9.0% [4.8%, 16.2%] | 47.0% [37.5%, 56.7%] | 0.350 [0.212, 0.469] |
| bm25 | 100 | 59.0% [49.2%, 68.1%] | 15.0% [9.3%, 23.3%] | 26.0% [18.4%, 35.4%] | 0.440 [0.283, 0.575] |
| hybrid | 100 | 56.0% [46.2%, 65.3%] | 10.0% [5.5%, 17.4%] | 34.0% [25.5%, 43.7%] | 0.460 [0.317, 0.594] |
| hybrid_rerank | 100 | 49.0% [39.4%, 58.7%] | 10.0% [5.5%, 17.4%] | 41.0% [31.9%, 50.8%] | 0.390 [0.250, 0.514] |
| agentic | 100 | 66.0% [56.3%, 74.5%] | 20.0% [13.3%, 28.9%] | 14.0% [8.5%, 22.1%] | 0.460 [0.300, 0.615] |
| engine | 100 | 42.0% [32.8%, 51.8%] | 52.0% [42.3%, 61.5%] | 6.0% [2.8%, 12.5%] | -0.100 [-0.291, 0.099] |
| engine_single (exploratory) | 100 | 27.0% [19.3%, 36.4%] | 10.0% [5.5%, 17.4%] | 63.0% [53.2%, 71.8%] | 0.170 [0.050, 0.278] |
| hybrid+asof (exploratory) | 100 | 55.0% [45.2%, 64.4%] | 10.0% [5.5%, 17.4%] | 35.0% [26.4%, 44.7%] | 0.450 [0.300, 0.586] |
| agentic+asof (exploratory) | 100 | 70.0% [60.4%, 78.1%] | 20.0% [13.3%, 28.9%] | 10.0% [5.5%, 17.4%] | 0.500 [0.304, 0.657] |

## Table 1b. Secondary, exploratory: judge-assisted grade (split `dev2`)

The containment grade of Table 1 is the primary measure and is unchanged. For every answered row of every system that it marked wrong, `claude-haiku-5-5` (the generator's model family, thinking off) was asked whether the answer states the same answer as a gold answer; EQUIVALENT counts as correct here. The same rule applies to all systems.

| system | n | judged | flipped to correct | correct (judge-assisted) | penalised score (judge-assisted) | penalised score (primary) |
|---|---|---|---|---|---|---|
| closed_book | 100 | 4 | 1 | 45.0% [35.6%, 54.8%] | 0.370 [0.231, 0.491] | 0.350 [0.212, 0.469] |
| bm25 | 100 | 15 | 0 | 59.0% [49.2%, 68.1%] | 0.440 [0.283, 0.575] | 0.440 [0.283, 0.575] |
| hybrid | 100 | 10 | 1 | 57.0% [47.2%, 66.3%] | 0.480 [0.336, 0.606] | 0.460 [0.317, 0.594] |
| hybrid_rerank | 100 | 10 | 1 | 50.0% [40.4%, 59.6%] | 0.410 [0.274, 0.537] | 0.390 [0.250, 0.514] |
| agentic | 100 | 20 | 5 | 71.0% [61.5%, 79.0%] | 0.560 [0.407, 0.699] | 0.460 [0.300, 0.615] |
| engine | 100 | 52 | 12 | 54.0% [44.3%, 63.4%] | 0.140 [-0.067, 0.347] | -0.100 [-0.291, 0.099] |
| engine_single (exploratory) | 100 | 10 | 5 | 32.0% [23.7%, 41.7%] | 0.270 [0.160, 0.375] | 0.170 [0.050, 0.278] |
| hybrid+asof (exploratory) | 100 | 10 | 1 | 56.0% [46.2%, 65.3%] | 0.470 [0.326, 0.602] | 0.450 [0.300, 0.586] |
| agentic+asof (exploratory) | 100 | 20 | 5 | 75.0% [65.7%, 82.5%] | 0.600 [0.439, 0.733] | 0.500 [0.304, 0.657] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 44.0% | 46.0% | 80.4% | 0.086 | 58.3% (n=12) | 250.1 |
| bm25 | 100 | 59.0% | 62.0% | 75.8% | 0.134 | 100.0% (n=12) | 287.8 |
| hybrid | 100 | 56.0% | 54.0% | 81.5% | 0.087 | 100.0% (n=12) | 284.4 |
| hybrid_rerank | 100 | 49.0% | 47.0% | 78.7% | 0.124 | 100.0% (n=12) | 277.8 |
| agentic | 100 | 66.0% | 74.0% | 73.0% | 0.119 | 100.0% (n=12) | 321.4 |
| engine | 100 | 42.0% | 82.0% | 36.6% | 0.664 | 100.0% (n=12) | 270.8 |
| engine_single (exploratory) | 100 | 27.0% | 25.0% | 60.0% | 0.330 | 100.0% (n=12) | 159.3 |
| hybrid+asof (exploratory) | 100 | 55.0% | 53.0% | 81.1% | 0.091 | 100.0% (n=12) | 294.5 |
| agentic+asof (exploratory) | 100 | 70.0% | 78.0% | 74.4% | 0.100 | 100.0% (n=12) | 321.8 |

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
| closed_book | 100 | $0.0002 | $0.0198 | $0.0005 [$0.0004, $0.0006] | 1965.8 | 3995.9 | 1.00 | 0.00 |
| bm25 | 100 | $0.0006 | $0.0598 | $0.0010 [$0.0009, $0.0013] | 1875.7 | 3315.1 | 1.00 | 1.00 |
| hybrid | 100 | $0.0006 | $0.0594 | $0.0011 [$0.0009, $0.0013] | 1880.7 | 3683.5 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0006 | $0.0612 | $0.0012 [$0.0010, $0.0016] | 6892.7 | 10265.2 | 1.00 | 1.00 |
| agentic | 100 | $0.0012 | $0.1222 | $0.0019 [$0.0016, $0.0023] | 4962.4 | 8221.0 | 3.03 | 2.03 |
| engine | 100 | $0.0016 | $0.1587 | $0.0038 [$0.0030, $0.0050] | 5794.8 | 11375.9 | 1.88 | 1.88 |
| engine_single (exploratory) | 100 | $0.0007 | $0.0686 | $0.0025 [$0.0019, $0.0038] | 4373.1 | 6556.1 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0006 | $0.0591 | $0.0011 [$0.0009, $0.0013] | 2160.6 | 3684.1 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0012 | $0.1196 | $0.0017 [$0.0015, $0.0021] | 4769.2 | 8250.1 | 2.98 | 1.98 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.528 (88) |
| hybrid | n/a | n/a | n/a | 0.467 (88) |
| hybrid_rerank | n/a | n/a | n/a | 0.383 (88) |
| agentic | n/a | n/a | n/a | 0.598 (88) |
| engine | 82 | 0.534 | 0.550 | 0.618 (88) |
| engine_single (exploratory) | 25 | 0.660 | 0.520 | 0.521 (88) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.467 (88) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.602 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev2`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | -0.450 [-0.655, -0.222] | 0.0010 | 0.0050 |
| bm25 | 100 | -0.540 [-0.744, -0.344] | 0.0010 | 0.0050 |
| hybrid | 100 | -0.560 [-0.748, -0.358] | 0.0010 | 0.0050 |
| hybrid_rerank | 100 | -0.490 [-0.688, -0.281] | 0.0010 | 0.0050 |
| agentic | 100 | -0.560 [-0.756, -0.362] | 0.0010 | 0.0050 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 18 | 20 | 0.8714 | 0.8714 | 0.171 |
| bm25 | 100 | 10 | 27 | 0.0076 | 0.0305 | 0.168 |
| hybrid | 100 | 10 | 24 | 0.0243 | 0.0729 | 0.161 |
| hybrid_rerank | 100 | 12 | 19 | 0.2810 | 0.5621 | 0.154 |
| agentic | 100 | 6 | 30 | 0.0001 | 0.0003 | 0.166 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev2`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0027 [$0.0019, $0.0039] |
| agentic | $0.0019 [$0.0012, $0.0030] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `dev2`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| engine_single | 100 | -0.270 [-0.463, -0.064] | 0.0150 | 0.0150 | 23 | 8 | 0.0107 | 0.154 |
| hybrid+asof | 100 | -0.550 [-0.762, -0.333] | 0.0010 | 0.0030 | 12 | 25 | 0.0470 | 0.168 |
| agentic+asof | 100 | -0.600 [-0.818, -0.376] | 0.0010 | 0.0030 | 4 | 32 | 0.0000 | 0.166 |

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 44.0% | yes | 0.350 | yes |
| bm25 | $0.0006 | 59.0% | yes | 0.440 | no |
| hybrid | $0.0006 | 56.0% | yes | 0.460 | yes |
| hybrid_rerank | $0.0006 | 49.0% | no | 0.390 | no |
| agentic | $0.0012 | 66.0% | yes | 0.460 | no |
| engine | $0.0016 | 42.0% | no | -0.100 | no |

