# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 500 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 23.0% [15.8%, 32.2%] | 25.0% [17.5%, 34.3%] | 52.0% [42.3%, 61.5%] | -0.020 [-0.154, 0.104] |
| vector | 100 | 28.0% [20.1%, 37.5%] | 20.0% [13.3%, 28.9%] | 52.0% [42.3%, 61.5%] | 0.080 [-0.065, 0.212] |
| hybrid | 100 | 30.0% [21.9%, 39.6%] | 17.0% [10.9%, 25.5%] | 53.0% [43.3%, 62.5%] | 0.130 [0.000, 0.255] |
| hybrid_rerank | 100 | 31.0% [22.8%, 40.6%] | 28.0% [20.1%, 37.5%] | 41.0% [31.9%, 50.8%] | 0.030 [-0.121, 0.163] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 23.0% | 48.0% | 47.9% | 0.450 | n/a (n=0) | 210.2 |
| vector | 100 | 28.0% | 48.0% | 58.3% | 0.244 | n/a (n=0) | 214.6 |
| hybrid | 100 | 30.0% | 47.0% | 63.8% | 0.228 | n/a (n=0) | 206.0 |
| hybrid_rerank | 100 | 31.0% | 59.0% | 52.5% | 0.388 | n/a (n=0) | 236.1 |

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
| bm25 | 100 | $0.0003 | $0.0306 | $0.0013 [$0.0010, $0.0019] | 1257.3 | 2095.8 | 1.00 | 1.00 |
| vector | 100 | $0.0003 | $0.0294 | $0.0011 [$0.0008, $0.0015] | 1476.2 | 2322.6 | 1.00 | 1.00 |
| hybrid | 100 | $0.0003 | $0.0295 | $0.0010 [$0.0008, $0.0014] | 1322.7 | 2202.1 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0003 | $0.0319 | $0.0010 [$0.0008, $0.0014] | 5193.9 | 7728.1 | 1.00 | 1.00 |

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
| bm25 | $0.0003 | 23.0% | no | -0.020 | no |
| vector | $0.0003 | 28.0% | yes | 0.080 | yes |
| hybrid | $0.0003 | 30.0% | yes | 0.130 | yes |
| hybrid_rerank | $0.0003 | 31.0% | yes | 0.030 | no |

