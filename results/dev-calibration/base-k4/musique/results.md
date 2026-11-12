# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 9.0% [4.8%, 16.2%] | 4.0% [1.6%, 9.8%] | 87.0% [79.0%, 92.2%] | 0.050 [-0.020, 0.121] |
| vector | 100 | 17.0% [10.9%, 25.5%] | 3.0% [1.0%, 8.5%] | 80.0% [71.1%, 86.7%] | 0.140 [0.060, 0.226] |
| hybrid | 100 | 17.0% [10.9%, 25.5%] | 4.0% [1.6%, 9.8%] | 79.0% [70.0%, 85.8%] | 0.130 [0.049, 0.216] |
| hybrid_rerank | 100 | 17.0% [10.9%, 25.5%] | 8.0% [4.1%, 15.0%] | 75.0% [65.7%, 82.5%] | 0.090 [0.000, 0.180] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 9.0% | 13.0% | 69.2% | 0.094 | n/a (n=0) | 133.6 |
| vector | 100 | 17.0% | 20.0% | 85.0% | 0.027 | n/a (n=0) | 142.0 |
| hybrid | 100 | 17.0% | 21.0% | 81.0% | 0.044 | n/a (n=0) | 155.3 |
| hybrid_rerank | 100 | 17.0% | 25.0% | 68.0% | 0.103 | n/a (n=0) | 162.4 |

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
| bm25 | 100 | $0.0002 | $0.0199 | $0.0022 [$0.0013, $0.0053] | 1225.2 | 2509.7 | 1.00 | 1.00 |
| vector | 100 | $0.0002 | $0.0201 | $0.0012 [$0.0008, $0.0020] | 1385.5 | 2908.4 | 1.00 | 1.00 |
| hybrid | 100 | $0.0002 | $0.0206 | $0.0012 [$0.0008, $0.0021] | 1460.8 | 3137.5 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0002 | $0.0232 | $0.0014 [$0.0009, $0.0023] | 3977.7 | 5797.6 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| bm25 | n/a | n/a | n/a | 0.432 (100) |
| vector | n/a | n/a | n/a | 0.411 (100) |
| hybrid | n/a | n/a | n/a | 0.442 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.487 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| bm25 | $0.0002 | 9.0% | yes | 0.050 | yes |
| vector | $0.0002 | 17.0% | yes | 0.140 | yes |
| hybrid | $0.0002 | 17.0% | no | 0.130 | no |
| hybrid_rerank | $0.0002 | 17.0% | no | 0.090 | no |

