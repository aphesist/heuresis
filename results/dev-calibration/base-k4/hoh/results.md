# Results: hoh, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 41.0% [31.9%, 50.8%] | 53.0% [43.3%, 62.5%] | 6.0% [2.8%, 12.5%] | -0.120 [-0.300, 0.050] |
| vector | 100 | 36.0% [27.3%, 45.8%] | 45.0% [35.6%, 54.8%] | 19.0% [12.5%, 27.8%] | -0.090 [-0.260, 0.090] |
| hybrid | 100 | 39.0% [30.0%, 48.8%] | 51.0% [41.3%, 60.6%] | 10.0% [5.5%, 17.4%] | -0.120 [-0.310, 0.060] |
| hybrid_rerank | 100 | 37.0% [28.2%, 46.8%] | 49.0% [39.4%, 58.7%] | 14.0% [8.5%, 22.1%] | -0.120 [-0.290, 0.060] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 41.0% | 94.0% | 43.6% | 0.597 | n/a (n=0) | 97.9 |
| vector | 100 | 36.0% | 81.0% | 44.4% | 0.623 | n/a (n=0) | 96.8 |
| hybrid | 100 | 39.0% | 90.0% | 43.3% | 0.564 | n/a (n=0) | 96.0 |
| hybrid_rerank | 100 | 37.0% | 86.0% | 43.0% | 0.586 | n/a (n=0) | 96.1 |

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
| bm25 | 100 | $0.0001 | $0.0104 | $0.0003 [$0.0002, $0.0003] | 1122.6 | 2114.1 | 1.00 | 1.00 |
| vector | 100 | $0.0001 | $0.0102 | $0.0003 [$0.0002, $0.0004] | 3967.5 | 23767.3 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0103 | $0.0003 [$0.0002, $0.0004] | 8894.7 | 24559.4 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0099 | $0.0003 [$0.0002, $0.0004] | 5779.3 | 24007.1 | 1.00 | 1.00 |

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
| bm25 | $0.0001 | 41.0% | yes | -0.120 | no |
| vector | $0.0001 | 36.0% | no | -0.090 | yes |
| hybrid | $0.0001 | 39.0% | yes | -0.120 | no |
| hybrid_rerank | $0.0001 | 37.0% | yes | -0.120 | yes |

