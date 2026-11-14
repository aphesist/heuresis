# Results: hoh, split `rot2`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `engine2`. Completed per system: engine2 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `rot2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| engine2 | 100 | 76.0% [66.8%, 83.3%] | 5.0% [2.2%, 11.2%] | 19.0% [12.5%, 27.8%] | 0.710 [0.600, 0.816] |

## Table 2. Selective answering (split `rot2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| engine2 | 100 | 76.0% | 81.0% | 93.8% | 6.2% [2.7%, 13.6%] (5/81) | 0.101 | n/a (n=0) | 152.6 |

## Table 2b. Errors (split `rot2`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| engine2 | 100 | 0 | 0 |

## Table 3. Cost and latency (split `rot2`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| engine2 | 100 | $0.0024 | $0.2384 | $0.0031 [$0.0028, $0.0035] | 6177.8 | 27783.3 | 2.38 | 1.49 |

## Table 4. Evidence (split `rot2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| engine2 | 81 | 0.926 | 1.000 | 0.990 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `rot2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| engine2 | $0.0024 | 76.0% | yes | 0.710 | yes |

