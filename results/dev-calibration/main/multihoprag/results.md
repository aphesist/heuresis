# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic`, `engine`. Completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 100 | 39.0% [30.0%, 48.8%] | 6.0% [2.8%, 12.5%] | 55.0% [45.2%, 64.4%] | 0.330 [0.198, 0.448] |
| bm25 | 100 | 39.0% [30.0%, 48.8%] | 4.0% [1.6%, 9.8%] | 57.0% [47.2%, 66.3%] | 0.350 [0.240, 0.468] |
| vector | 100 | 33.0% [24.6%, 42.7%] | 3.0% [1.0%, 8.5%] | 64.0% [54.2%, 72.7%] | 0.300 [0.198, 0.400] |
| hybrid | 100 | 35.0% [26.4%, 44.7%] | 5.0% [2.2%, 11.2%] | 60.0% [50.2%, 69.1%] | 0.300 [0.194, 0.402] |
| hybrid_rerank | 100 | 34.0% [25.5%, 43.7%] | 5.0% [2.2%, 11.2%] | 61.0% [51.2%, 70.0%] | 0.290 [0.176, 0.408] |
| agentic | 100 | 58.0% [48.2%, 67.2%] | 17.0% [10.9%, 25.5%] | 25.0% [17.5%, 34.3%] | 0.410 [0.259, 0.543] |
| engine | 100 | 12.0% [7.0%, 19.8%] | 2.0% [0.6%, 7.0%] | 86.0% [77.9%, 91.5%] | 0.100 [0.027, 0.182] |
| oracle | 100 | 48.0% [38.5%, 57.7%] | 8.0% [4.1%, 15.0%] | 44.0% [34.7%, 53.8%] | 0.400 [0.264, 0.524] |
| bm25+asof (exploratory) | 100 | 42.0% [32.8%, 51.8%] | 4.0% [1.6%, 9.8%] | 54.0% [44.3%, 63.4%] | 0.380 [0.263, 0.495] |
| vector+asof (exploratory) | 100 | 34.0% [25.5%, 43.7%] | 4.0% [1.6%, 9.8%] | 62.0% [52.2%, 70.9%] | 0.300 [0.186, 0.423] |
| hybrid+asof (exploratory) | 100 | 38.0% [29.1%, 47.8%] | 3.0% [1.0%, 8.5%] | 59.0% [49.2%, 68.1%] | 0.350 [0.236, 0.461] |
| hybrid_rerank+asof (exploratory) | 100 | 33.0% [24.6%, 42.7%] | 4.0% [1.6%, 9.8%] | 63.0% [53.2%, 71.8%] | 0.290 [0.181, 0.398] |
| agentic+asof (exploratory) | 100 | 56.0% [46.2%, 65.3%] | 17.0% [10.9%, 25.5%] | 27.0% [19.3%, 36.4%] | 0.390 [0.242, 0.535] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 100 | 39.0% | 37.0% | 83.8% | 0.060 | 66.7% (n=12) | 226.5 |
| bm25 | 100 | 39.0% | 31.0% | 87.1% | 0.076 | 100.0% (n=12) | 261.4 |
| vector | 100 | 33.0% | 24.0% | 87.5% | 0.101 | 100.0% (n=12) | 260.3 |
| hybrid | 100 | 35.0% | 28.0% | 82.1% | 0.106 | 100.0% (n=12) | 264.7 |
| hybrid_rerank | 100 | 34.0% | 27.0% | 81.5% | 0.068 | 100.0% (n=12) | 251.4 |
| agentic | 100 | 58.0% | 63.0% | 73.0% | 0.101 | 100.0% (n=12) | 306.4 |
| engine | 100 | 12.0% | 2.0% | 0.0% | 1.000 | 100.0% (n=12) | 123.5 |
| oracle | 100 | 48.0% | 44.0% | 81.8% | 0.032 | 100.0% (n=12) | 266.1 |
| bm25+asof (exploratory) | 100 | 42.0% | 34.0% | 88.2% | 0.032 | 100.0% (n=12) | 264.8 |
| vector+asof (exploratory) | 100 | 34.0% | 26.0% | 84.6% | 0.054 | 100.0% (n=12) | 255.7 |
| hybrid+asof (exploratory) | 100 | 38.0% | 29.0% | 89.7% | 0.062 | 100.0% (n=12) | 238.2 |
| hybrid_rerank+asof (exploratory) | 100 | 33.0% | 25.0% | 84.0% | 0.068 | 100.0% (n=12) | 258.8 |
| agentic+asof (exploratory) | 100 | 56.0% | 61.0% | 72.1% | 0.111 | 100.0% (n=12) | 279.0 |

## Table 2b. Errors (split `dev`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 100 | 0 | 0 |
| bm25 | 100 | 0 | 0 |
| vector | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| hybrid_rerank | 100 | 0 | 0 |
| agentic | 100 | 0 | 0 |
| engine | 100 | 0 | 0 |
| oracle | 100 | 0 | 0 |
| bm25+asof (exploratory) | 100 | 0 | 0 |
| vector+asof (exploratory) | 100 | 0 | 0 |
| hybrid+asof (exploratory) | 100 | 0 | 0 |
| hybrid_rerank+asof (exploratory) | 100 | 0 | 0 |
| agentic+asof (exploratory) | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | $0.0002 | $0.0183 | $0.0005 [$0.0004, $0.0007] | 1773.4 | 3176.6 | 1.00 | 0.00 |
| bm25 | 100 | $0.0006 | $0.0605 | $0.0016 [$0.0012, $0.0021] | 2234.1 | 3340.6 | 1.00 | 1.00 |
| vector | 100 | $0.0006 | $0.0573 | $0.0017 [$0.0014, $0.0024] | 1920.1 | 3322.8 | 1.00 | 1.00 |
| hybrid | 100 | $0.0006 | $0.0601 | $0.0017 [$0.0014, $0.0023] | 2309.8 | 3348.3 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0006 | $0.0607 | $0.0018 [$0.0014, $0.0025] | 6941.2 | 8234.7 | 1.00 | 1.00 |
| agentic | 100 | $0.0013 | $0.1252 | $0.0022 [$0.0018, $0.0027] | 4751.0 | 7914.9 | 3.06 | 2.06 |
| engine | 100 | $0.0007 | $0.0678 | $0.0057 [$0.0033, $0.0123] | 2852.5 | 3620.7 | 1.00 | 1.00 |
| oracle | 100 | $0.0003 | $0.0295 | $0.0006 [$0.0005, $0.0008] | 1956.1 | 3164.9 | 1.00 | 0.00 |
| bm25+asof (exploratory) | 100 | $0.0006 | $0.0608 | $0.0014 [$0.0012, $0.0019] | 2110.7 | 3282.4 | 1.00 | 1.00 |
| vector+asof (exploratory) | 100 | $0.0006 | $0.0575 | $0.0017 [$0.0013, $0.0024] | 1908.2 | 3316.3 | 1.00 | 1.00 |
| hybrid+asof (exploratory) | 100 | $0.0006 | $0.0600 | $0.0016 [$0.0012, $0.0022] | 2214.5 | 3404.8 | 1.00 | 1.00 |
| hybrid_rerank+asof (exploratory) | 100 | $0.0006 | $0.0609 | $0.0018 [$0.0014, $0.0026] | 6833.2 | 8959.1 | 1.00 | 1.00 |
| agentic+asof (exploratory) | 100 | $0.0012 | $0.1194 | $0.0021 [$0.0018, $0.0026] | 4453.5 | 8545.5 | 2.98 | 1.98 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| bm25 | n/a | n/a | n/a | 0.589 (88) |
| vector | n/a | n/a | n/a | 0.406 (88) |
| hybrid | n/a | n/a | n/a | 0.576 (88) |
| hybrid_rerank | n/a | n/a | n/a | 0.422 (88) |
| agentic | n/a | n/a | n/a | 0.591 (88) |
| engine | 2 | 1.000 | 0.500 | 0.594 (88) |
| oracle | n/a | n/a | n/a | 1.000 (88) |
| bm25+asof (exploratory) | n/a | n/a | n/a | 0.589 (88) |
| vector+asof (exploratory) | n/a | n/a | n/a | 0.406 (88) |
| hybrid+asof (exploratory) | n/a | n/a | n/a | 0.576 (88) |
| hybrid_rerank+asof (exploratory) | n/a | n/a | n/a | 0.422 (88) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.559 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `dev`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 100 | -0.230 [-0.373, -0.069] | 0.0190 | 0.0210 |
| bm25 | 100 | -0.250 [-0.371, -0.134] | 0.0030 | 0.0120 |
| vector | 100 | -0.200 [-0.300, -0.092] | 0.0020 | 0.0100 |
| hybrid | 100 | -0.200 [-0.303, -0.086] | 0.0070 | 0.0210 |
| hybrid_rerank | 100 | -0.190 [-0.302, -0.070] | 0.0080 | 0.0210 |
| agentic | 100 | -0.310 [-0.463, -0.149] | 0.0010 | 0.0060 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 100 | 4 | 31 | 0.0000 | 0.0000 | 0.164 |
| bm25 | 100 | 0 | 27 | 0.0000 | 0.0000 | 0.144 |
| vector | 100 | 0 | 21 | 0.0000 | 0.0000 | 0.127 |
| hybrid | 100 | 0 | 23 | 0.0000 | 0.0000 | 0.133 |
| hybrid_rerank | 100 | 0 | 22 | 0.0000 | 0.0000 | 0.130 |
| agentic | 100 | 0 | 46 | 0.0000 | 0.0000 | 0.188 |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `dev`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0039 [$0.0018, $0.0102] |
| agentic | $0.0035 [$0.0010, $0.0102] |

## Table 6. Exploratory: `engine` against the time-aware variants (split `dev`; paired on shared questions)

The `+asof` systems search as of the question date. They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| bm25+asof | 100 | -0.280 [-0.394, -0.163] | 0.0010 | 0.0050 | 0 | 30 | 0.0000 | 0.152 |
| vector+asof | 100 | -0.200 [-0.313, -0.082] | 0.0060 | 0.0120 | 0 | 22 | 0.0000 | 0.130 |
| hybrid+asof | 100 | -0.250 [-0.356, -0.147] | 0.0010 | 0.0050 | 0 | 26 | 0.0000 | 0.141 |
| hybrid_rerank+asof | 100 | -0.190 [-0.299, -0.082] | 0.0040 | 0.0120 | 0 | 21 | 0.0000 | 0.127 |
| agentic+asof | 100 | -0.290 [-0.436, -0.136] | 0.0060 | 0.0120 | 0 | 44 | 0.0000 | 0.184 |

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0002 | 39.0% | yes | 0.330 | yes |
| bm25 | $0.0006 | 39.0% | no | 0.350 | yes |
| vector | $0.0006 | 33.0% | no | 0.300 | no |
| hybrid | $0.0006 | 35.0% | no | 0.300 | no |
| hybrid_rerank | $0.0006 | 34.0% | no | 0.290 | no |
| agentic | $0.0013 | 58.0% | yes | 0.410 | yes |
| engine | $0.0007 | 12.0% | no | 0.100 | no |

