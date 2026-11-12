# Results: hoh, split `dev`

Questions planned: 100. Bootstrap: 500 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 44.0% [34.7%, 53.8%] | 51.0% [41.3%, 60.6%] | 5.0% [2.2%, 11.2%] | -0.070 [-0.270, 0.100] |
| vector | 100 | 34.0% [25.5%, 43.7%] | 43.0% [33.7%, 52.8%] | 23.0% [15.8%, 32.2%] | -0.090 [-0.260, 0.060] |
| hybrid | 100 | 39.0% [30.0%, 48.8%] | 49.0% [39.4%, 58.7%] | 12.0% [7.0%, 19.8%] | -0.100 [-0.285, 0.070] |
| hybrid_rerank | 100 | 39.0% [30.0%, 48.8%] | 48.0% [38.5%, 57.7%] | 13.0% [7.8%, 21.0%] | -0.090 [-0.280, 0.090] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 44.0% | 95.0% | 46.3% | 0.597 | n/a (n=0) | 91.1 |
| vector | 100 | 34.0% | 77.0% | 44.2% | 0.594 | n/a (n=0) | 83.3 |
| hybrid | 100 | 39.0% | 88.0% | 44.3% | 0.587 | n/a (n=0) | 87.5 |
| hybrid_rerank | 100 | 39.0% | 87.0% | 44.8% | 0.602 | n/a (n=0) | 91.3 |

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
| bm25 | 100 | $0.0001 | $0.0069 | $0.0002 [$0.0001, $0.0002] | 974.9 | 1352.6 | 1.00 | 1.00 |
| vector | 100 | $0.0001 | $0.0069 | $0.0002 [$0.0002, $0.0003] | 5882.8 | 26260.0 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0069 | $0.0002 [$0.0001, $0.0002] | 11614.8 | 24994.8 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0069 | $0.0002 [$0.0001, $0.0002] | 6866.9 | 25824.1 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| bm25 | n/a | n/a | n/a | 1.000 (100) |
| vector | n/a | n/a | n/a | 0.850 (100) |
| hybrid | n/a | n/a | n/a | 0.940 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.900 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| bm25 | $0.0001 | 44.0% | yes | -0.070 | yes |
| vector | $0.0001 | 34.0% | no | -0.090 | no |
| hybrid | $0.0001 | 39.0% | no | -0.100 | no |
| hybrid_rerank | $0.0001 | 39.0% | no | -0.090 | no |

