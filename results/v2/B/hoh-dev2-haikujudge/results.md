# Results: hoh, split `dev2`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `engine2`. Completed per system: engine2 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| engine2 | 100 | 60.0% [50.2%, 69.1%] | 12.0% [7.0%, 19.8%] | 28.0% [20.1%, 37.5%] | 0.480 [0.340, 0.610] |

## Table 2. Selective answering (split `dev2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| engine2 | 100 | 60.0% | 72.0% | 83.3% | 16.7% [9.8%, 26.9%] (12/72) | 0.210 | n/a (n=0) | 149.1 |

## Table 2b. Errors (split `dev2`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| engine2 | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev2`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| engine2 | 100 | $0.0005 | $0.0466 | $0.0008 [$0.0006, $0.0010] | 6667.6 | 25040.2 | 2.39 | 1.34 |

## Table 4. Evidence (split `dev2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| engine2 | 72 | 0.896 | 1.000 | 1.000 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `dev2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| engine2 | $0.0005 | 60.0% | yes | 0.480 | yes |

