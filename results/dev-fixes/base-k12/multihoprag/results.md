# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 500 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 57.0% [47.2%, 66.3%] | 14.0% [8.5%, 22.1%] | 29.0% [21.0%, 38.5%] | 0.430 [0.257, 0.578] |
| vector | 100 | 41.0% [31.9%, 50.8%] | 13.0% [7.8%, 21.0%] | 46.0% [36.6%, 55.7%] | 0.280 [0.133, 0.398] |
| hybrid | 100 | 53.0% [43.3%, 62.5%] | 13.0% [7.8%, 21.0%] | 34.0% [25.5%, 43.7%] | 0.400 [0.236, 0.532] |
| hybrid_rerank | 100 | 48.0% [38.5%, 57.7%] | 13.0% [7.8%, 21.0%] | 39.0% [30.0%, 48.8%] | 0.350 [0.194, 0.488] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 57.0% | 59.0% | 76.3% | 0.068 | 100.0% (n=12) | 331.7 |
| vector | 100 | 41.0% | 42.0% | 69.0% | 0.167 | 100.0% (n=12) | 316.8 |
| hybrid | 100 | 53.0% | 54.0% | 75.9% | 0.082 | 100.0% (n=12) | 309.1 |
| hybrid_rerank | 100 | 48.0% | 49.0% | 73.5% | 0.122 | 100.0% (n=12) | 316.7 |

## Table 2b. Errors (split `dev`)

An error is an API or model failure after the client's retries. It is counted as a wrong answer in Table 1 and in every score.

| system | n | error rows | of which counted as wrong |
|---|---|---|---|
| bm25 | 100 | 0 | 0 |
| vector | 100 | 0 | 0 |
| hybrid | 100 | 0 | 0 |
| hybrid_rerank | 100 | 0 | 0 |

## Table 3. Cost and latency (split `dev`)

Latency is wall-clock time around `System.answer`, measured the same way for every system, with 4 concurrent workers: it includes waiting for the shared model client and for the other workers, so it is indicative only. The engine's own stage-timing sum is stored separately in each row (`stage_ms`).

| system | n | mean cost | total cost | cost per correct | median ms | p95 ms | calls | searches |
|---|---|---|---|---|---|---|---|---|
| bm25 | 100 | $0.0007 | $0.0664 | $0.0012 [$0.0010, $0.0015] | 1414.8 | 2470.8 | 1.00 | 1.00 |
| vector | 100 | $0.0006 | $0.0646 | $0.0016 [$0.0013, $0.0021] | 1483.7 | 2362.5 | 1.00 | 1.00 |
| hybrid | 100 | $0.0007 | $0.0658 | $0.0012 [$0.0011, $0.0016] | 1697.5 | 2603.1 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0007 | $0.0671 | $0.0014 [$0.0012, $0.0018] | 14866.9 | 17295.6 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| bm25 | n/a | n/a | n/a | 0.670 (88) |
| vector | n/a | n/a | n/a | 0.505 (88) |
| hybrid | n/a | n/a | n/a | 0.650 (88) |
| hybrid_rerank | n/a | n/a | n/a | 0.489 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| bm25 | $0.0007 | 57.0% | yes | 0.430 | yes |
| vector | $0.0006 | 41.0% | yes | 0.280 | yes |
| hybrid | $0.0007 | 53.0% | yes | 0.400 | yes |
| hybrid_rerank | $0.0007 | 48.0% | no | 0.350 | no |

