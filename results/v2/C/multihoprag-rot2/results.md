# Results: multihoprag, split `rot2`

Questions planned: 100. Bootstrap: 10000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `engine2`. Completed per system: engine2 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `rot2`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| engine2 | 100 | 58.0% [48.2%, 67.2%] | 9.0% [4.8%, 16.2%] | 33.0% [24.6%, 42.7%] | 0.490 [0.357, 0.613] |

## Table 2. Selective answering (split `rot2`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | error rate (answered) | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|---|
| engine2 | 100 | 58.0% | 54.0% | 83.3% | 16.7% [9.0%, 28.7%] (9/54) | 0.161 | 100.0% (n=13) | 755.6 |

## Table 2b. Errors (split `rot2`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| engine2 | 100 | 0 | 0 |

## Table 3. Cost and latency (split `rot2`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| engine2 | 100 | $0.0077 | $0.7686 | $0.0133 [$0.0112, $0.0159] | 6340.3 | 12240.6 | 2.74 | 2.63 |

## Table 4. Evidence (split `rot2`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| engine2 | 54 | 0.507 | 0.701 | 0.759 (87) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `rot2`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| engine2 | $0.0077 | 58.0% | yes | 0.490 | yes |

