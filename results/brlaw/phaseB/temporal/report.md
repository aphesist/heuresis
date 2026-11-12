# Results: brlaw-core, split `temporal`

Questions planned: 120. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 120 questions completed by all of `closed_book`, `hybrid`, `agentic`, `engine`. Completed per system: closed_book 120, hybrid 120, agentic 120, engine 120. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `temporal`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| closed_book | 120 | 10.0% [5.8%, 16.7%] | 21.7% [15.2%, 29.9%] | 68.3% [59.6%, 76.0%] | -0.117 [-0.242, 0.000] |
| hybrid | 120 | 10.8% [6.4%, 17.7%] | 35.8% [27.8%, 44.7%] | 53.3% [44.4%, 62.0%] | -0.250 [-0.358, -0.142] |
| agentic | 120 | 10.0% [5.8%, 16.7%] | 40.0% [31.7%, 48.9%] | 50.0% [41.2%, 58.8%] | -0.300 [-0.408, -0.183] |
| engine | 120 | 6.7% [3.4%, 12.6%] | 79.2% [71.1%, 85.5%] | 14.2% [9.0%, 21.5%] | -0.725 [-0.825, -0.625] |
| agentic+asof (exploratory) | 120 | 7.5% [4.0%, 13.6%] | 85.8% [78.5%, 91.0%] | 6.7% [3.4%, 12.6%] | -0.783 [-0.900, -0.658] |

## Table 2. Selective answering (split `temporal`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| closed_book | 120 | 10.0% | 21.7% | 0.0% | 1.000 | 92.3% (n=13) | 457.4 |
| hybrid | 120 | 10.8% | 35.8% | 0.0% | 1.000 | 100.0% (n=13) | 552.0 |
| agentic | 120 | 10.0% | 40.0% | 0.0% | 1.000 | 92.3% (n=13) | 511.8 |
| engine | 120 | 6.7% | 79.2% | 0.0% | 1.000 | 61.5% (n=13) | 290.6 |
| agentic+asof (exploratory) | 120 | 7.5% | 85.8% | 0.0% | 1.000 | 69.2% (n=13) | 496.0 |

## Table 2b. Errors (split `temporal`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| closed_book | 120 | 0 | 0 |
| hybrid | 120 | 0 | 0 |
| agentic | 120 | 0 | 0 |
| engine | 120 | 0 | 0 |
| agentic+asof (exploratory) | 120 | 0 | 0 |

## Table 3. Cost and latency (split `temporal`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 3 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| closed_book | 120 | $0.0005 | $0.0562 | $0.0047 [$0.0030, $0.0094] | 4309.6 | 7205.6 | 1.00 | 0.00 |
| hybrid | 120 | $0.0004 | $0.0502 | $0.0039 [$0.0025, $0.0075] | 3242.6 | 6077.3 | 1.00 | 1.00 |
| agentic | 120 | $0.0018 | $0.2170 | $0.0181 [$0.0119, $0.0343] | 9054.6 | 15113.6 | 3.52 | 2.52 |
| engine | 120 | $0.0010 | $0.1188 | $0.0148 [$0.0098, $0.0327] | 3884.4 | 11024.0 | 1.44 | 1.44 |
| agentic+asof (exploratory) | 120 | $0.0012 | $0.1488 | $0.0165 [$0.0105, $0.0357] | 3853.9 | 10760.0 | 2.50 | 1.50 |

## Table 4. Evidence (split `temporal`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| closed_book | n/a | n/a | n/a | n/a (n/a) |
| hybrid | n/a | n/a | n/a | 0.000 (107) |
| agentic | n/a | n/a | n/a | 0.000 (107) |
| engine | 90 | 0.000 | 0.000 | 0.000 (107) |
| agentic+asof (exploratory) | n/a | n/a | n/a | 0.000 (107) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 5. `engine` against each baseline (split `temporal`; paired on shared questions)

Primary test. Score difference = engine minus baseline on the penalised score (+1 correct, 0 abstained, -1 wrong), with a paired bootstrap 95% interval. The permutation p is a two-sided paired sign-flip test; Holm adjusts across the rows below (and across datasets in the family table). The oracle is excluded. Time-aware variants are in Table 6.

| baseline | n | score diff | permutation p | Holm p |
|---|---|---|---|---|
| closed_book | 120 | -0.608 [-0.733, -0.475] | 0.0001 | 0.0003 |
| hybrid | 120 | -0.475 [-0.575, -0.375] | 0.0001 | 0.0003 |
| agentic | 120 | -0.425 [-0.508, -0.333] | 0.0001 | 0.0003 |

Secondary: McNemar is exact, two-sided, on correct outcomes; Holm adjusts across the rows.

| baseline | n | engine only | baseline only | McNemar p | Holm p | min detectable diff |
|---|---|---|---|---|---|---|
| closed_book | 120 | 0 | 4 | 0.1250 | 0.2500 | n/a |
| hybrid | 120 | 0 | 5 | 0.0625 | 0.1875 | n/a |
| agentic | 120 | 0 | 4 | 0.1250 | 0.2500 | n/a |

## Table 5b. Cost per correct answer, `engine` minus baseline (split `temporal`)

Bootstrap 95% interval, questions resampled with each pair kept together. Negative means the engine costs less per correct answer.

| baseline | difference in cost per correct |
|---|---|
| hybrid | $0.0110 [$0.0066, $0.0263] |
| agentic | $-0.0032 [$-0.0126, $0.0075] |

## Table 6. Exploratory: `engine` against the time-aware variants and the earlier engine design (split `temporal`; paired on shared questions)

The `+asof` systems search as of the question date; `engine_single` is the earlier engine (one draft, entailment as a gate). They are exploratory: not part of the confirmatory family of Table 5, and Holm here adjusts only across the rows below.

| variant | n | score diff | permutation p | Holm p | engine only | variant only | McNemar p | min detectable diff |
|---|---|---|---|---|---|---|---|---|
| agentic+asof | 120 | 0.058 [-0.042, 0.158] | 0.3500 | 0.3500 | 0 | 1 | 1.0000 | n/a |

## Table 7. Accuracy against cost (split `temporal`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| closed_book | $0.0005 | 10.0% | no | -0.117 | yes |
| hybrid | $0.0004 | 10.8% | yes | -0.250 | yes |
| agentic | $0.0018 | 10.0% | no | -0.300 | no |
| engine | $0.0010 | 6.7% | no | -0.725 | no |

