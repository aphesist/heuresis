# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 21.0% [14.2%, 30.0%] | 4.0% [1.6%, 9.8%] | 75.0% [65.7%, 82.5%] | 0.170 [0.072, 0.265] |
| vector | 100 | 24.0% [16.7%, 33.2%] | 6.0% [2.8%, 12.5%] | 70.0% [60.4%, 78.1%] | 0.180 [0.079, 0.278] |
| hybrid | 100 | 27.0% [19.3%, 36.4%] | 5.0% [2.2%, 11.2%] | 68.0% [58.3%, 76.3%] | 0.220 [0.108, 0.320] |
| hybrid_rerank | 100 | 30.0% [21.9%, 39.6%] | 9.0% [4.8%, 16.2%] | 61.0% [51.2%, 70.0%] | 0.210 [0.096, 0.320] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 21.0% | 25.0% | 84.0% | 0.063 | n/a (n=0) | 158.5 |
| vector | 100 | 24.0% | 30.0% | 80.0% | 0.071 | n/a (n=0) | 167.4 |
| hybrid | 100 | 27.0% | 32.0% | 84.4% | 0.051 | n/a (n=0) | 159.7 |
| hybrid_rerank | 100 | 30.0% | 39.0% | 76.9% | 0.083 | n/a (n=0) | 181.9 |

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
| bm25 | 100 | $0.0004 | $0.0400 | $0.0019 [$0.0014, $0.0030] | 1350.3 | 2931.0 | 1.00 | 1.00 |
| vector | 100 | $0.0004 | $0.0383 | $0.0016 [$0.0012, $0.0025] | 1490.6 | 3079.6 | 1.00 | 1.00 |
| hybrid | 100 | $0.0004 | $0.0387 | $0.0014 [$0.0011, $0.0021] | 1550.2 | 3080.5 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0004 | $0.0412 | $0.0014 [$0.0011, $0.0019] | 3769.2 | 5877.8 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| bm25 | n/a | n/a | n/a | 0.551 (100) |
| vector | n/a | n/a | n/a | 0.517 (100) |
| hybrid | n/a | n/a | n/a | 0.597 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.618 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| bm25 | $0.0004 | 21.0% | no | 0.170 | no |
| vector | $0.0004 | 24.0% | yes | 0.180 | yes |
| hybrid | $0.0004 | 27.0% | yes | 0.220 | yes |
| hybrid_rerank | $0.0004 | 30.0% | yes | 0.210 | no |

