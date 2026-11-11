# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 32.0% [23.7%, 41.7%] | 4.0% [1.6%, 9.8%] | 64.0% [54.2%, 72.7%] | 0.280 [0.170, 0.395] |
| vector | 100 | 27.0% [19.3%, 36.4%] | 2.0% [0.6%, 7.0%] | 71.0% [61.5%, 79.0%] | 0.250 [0.150, 0.352] |
| hybrid | 100 | 34.0% [25.5%, 43.7%] | 1.0% [0.2%, 5.4%] | 65.0% [55.3%, 73.6%] | 0.330 [0.223, 0.433] |
| hybrid_rerank | 100 | 29.0% [21.0%, 38.5%] | 4.0% [1.6%, 9.8%] | 67.0% [57.3%, 75.4%] | 0.250 [0.142, 0.352] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 32.0% | 24.0% | 83.3% | 0.033 | 100.0% (n=12) | 259.7 |
| vector | 100 | 27.0% | 17.0% | 88.2% | 0.094 | 100.0% (n=12) | 258.2 |
| hybrid | 100 | 34.0% | 23.0% | 95.7% | 0.013 | 100.0% (n=12) | 253.5 |
| hybrid_rerank | 100 | 29.0% | 21.0% | 81.0% | 0.092 | 100.0% (n=12) | 230.5 |

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
| bm25 | 100 | $0.0004 | $0.0387 | $0.0012 [$0.0009, $0.0017] | 1856.0 | 3272.6 | 1.00 | 1.00 |
| vector | 100 | $0.0004 | $0.0355 | $0.0013 [$0.0010, $0.0020] | 1695.3 | 3336.4 | 1.00 | 1.00 |
| hybrid | 100 | $0.0004 | $0.0372 | $0.0011 [$0.0009, $0.0016] | 1893.2 | 3235.9 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0004 | $0.0378 | $0.0013 [$0.0010, $0.0019] | 11820.4 | 13666.6 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| bm25 | n/a | n/a | n/a | 0.430 (88) |
| vector | n/a | n/a | n/a | 0.285 (88) |
| hybrid | n/a | n/a | n/a | 0.384 (88) |
| hybrid_rerank | n/a | n/a | n/a | 0.304 (88) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| bm25 | $0.0004 | 32.0% | no | 0.280 | no |
| vector | $0.0004 | 27.0% | yes | 0.250 | yes |
| hybrid | $0.0004 | 34.0% | yes | 0.330 | yes |
| hybrid_rerank | $0.0004 | 29.0% | no | 0.250 | no |

