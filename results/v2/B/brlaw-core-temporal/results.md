# Results: brlaw-core, split `temporal`

Questions planned: 120. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 120 questions completed by all of `closed_book`, `hybrid`, `agentic`, `engine`, `engine2`. Completed per system: closed_book 120, hybrid 120, agentic 120, engine 120, engine2 120. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `temporal`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 120 | 10.0% [5.8%, 16.7%] | 20.0% [13.8%, 28.0%] | 70.0% [61.3%, 77.5%] | -0.100 [-0.217, 0.008] |
| hybrid | 120 | 10.8% [6.4%, 17.7%] | 36.7% [28.6%, 45.6%] | 52.5% [43.6%, 61.2%] | -0.258 [-0.367, -0.150] |
| agentic | 120 | 7.5% [4.0%, 13.6%] | 47.5% [38.8%, 56.4%] | 45.0% [36.4%, 53.9%] | -0.400 [-0.517, -0.283] |
| engine | 120 | 10.0% [5.8%, 16.7%] | 78.3% [70.1%, 84.8%] | 11.7% [7.1%, 18.6%] | -0.683 [-0.800, -0.558] |
| engine2 | 120 | 10.8% [6.4%, 17.7%] | 79.2% [71.1%, 85.5%] | 10.0% [5.8%, 16.7%] | -0.683 [-0.800, -0.567] |
| agentic+asof (exploratory) | 120 | 9.2% [5.2%, 15.7%] | 83.3% [75.7%, 88.9%] | 7.5% [4.0%, 13.6%] | -0.742 [-0.858, -0.608] |

## Table 2. Selective answering (split `temporal`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| closed_book | 120 | 10.0% | 20.0% | 0.0% | 100.0% [86.2%, 100.0%] (24/24) | 1.000 | 92.3% (n=13) | 479.3 |
| hybrid | 120 | 10.8% | 36.7% | 0.0% | 100.0% [92.0%, 100.0%] (44/44) | 1.000 | 100.0% (n=13) | 524.0 |
| agentic | 120 | 7.5% | 47.5% | 0.0% | 100.0% [93.7%, 100.0%] (57/57) | 1.000 | 69.2% (n=13) | 496.0 |
| engine | 120 | 10.0% | 78.3% | 0.0% | 100.0% [96.1%, 100.0%] (94/94) | 1.000 | 92.3% (n=13) | 326.3 |
| engine2 | 120 | 10.8% | 79.2% | 0.0% | 100.0% [96.1%, 100.0%] (95/95) | 1.000 | 100.0% (n=13) | 578.9 |
| agentic+asof (exploratory) | 120 | 9.2% | 83.3% | 0.0% | 100.0% [96.3%, 100.0%] (100/100) | 1.000 | 84.6% (n=13) | 500.6 |

## Table 2b. Errors (split `temporal`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 120 | 0 | 0 |
| hybrid | 120 | 0 | 0 |
| agentic | 120 | 0 | 0 |
| engine | 120 | 0 | 0 |
| engine2 | 120 | 0 | 0 |
| agentic+asof (exploratory) | 120 | 0 | 0 |

## Table 3. Cost and latency (split `temporal`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 120 | $0.0005 | $0.0558 | $0.0047 [$0.0030, $0.0092] | 4509.7 | 8121.4 | 1.00 | 0.00 |
| hybrid | 120 | $0.0004 | $0.0500 | $0.0038 [$0.0025, $0.0075] | 3337.5 | 6848.1 | 1.00 | 1.00 |
| agentic | 120 | $0.0018 | $0.2107 | $0.0234 [$0.0147, $0.0514] | 9458.9 | 18661.6 | 3.54 | 2.54 |
| engine | 120 | $0.0010 | $0.1254 | $0.0104 [$0.0074, $0.0186] | 5665.9 | 12127.5 | 2.19 | 1.40 |
| engine2 | 120 | $0.0041 | $0.4912 | $0.0378 [$0.0250, $0.0714] | 7094.2 | 13961.3 | 2.72 | 2.58 |
| agentic+asof (exploratory) | 120 | $0.0013 | $0.1518 | $0.0138 [$0.0090, $0.0275] | 4013.8 | 10941.6 | 2.50 | 1.50 |

## Table 4. Evidence (split `temporal`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| hybrid | n/a | n/a | n/a | 0.000 (107) |
| agentic | n/a | n/a | n/a | 0.000 (107) |
| engine | 93 | 0.000 | 0.000 | 0.000 (107) |
| engine2 | 95 | 0.000 | 0.000 | 0.000 (107) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.000 (107) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine2` against each baseline (split `temporal`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 120 | -0.583 [-0.700, -0.458] | 0.0001 | 0.0004 |
| hybrid | 120 | -0.425 [-0.508, -0.342] | 0.0001 | 0.0004 |
| agentic | 120 | -0.283 [-0.392, -0.167] | 0.0001 | 0.0004 |
| engine | 120 | 0.000 [-0.092, 0.092] | 1.0000 | 1.0000 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 120 | 1 | 0 | 1.0000 | 1.0000 | n/a |
| hybrid | 120 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| agentic | 120 | 4 | 0 | 0.1250 | 0.5000 | n/a |
| engine | 120 | 1 | 0 | 1.0000 | 1.0000 | n/a |

## Table 5b. Cost per correct answer, `engine2` minus baseline (split `temporal`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0339 [$0.0224, $0.0641] |
| agentic | $0.0144 [$0.0004, $0.0326] |

## Table 6. Exploratory: `engine2` against the time-aware variants and the earlier engine design (split `temporal`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| agentic+asof | 120 | 0.058 [-0.033, 0.158] | 0.3184 | 0.3184 | 2 | 0 | 0.5000 | n/a |

## Table 7. Accuracy against cost (split `temporal`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0005 | 10.0% | no | -0.100 | yes |
| hybrid | $0.0004 | 10.8% | yes | -0.258 | yes |
| agentic | $0.0018 | 7.5% | no | -0.400 | no |
| engine | $0.0010 | 10.0% | no | -0.683 | no |
| engine2 | $0.0041 | 10.8% | no | -0.683 | no |

