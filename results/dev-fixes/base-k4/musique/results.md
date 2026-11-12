# Results: musique, split `dev`

Questions planned: 100. Bootstrap: 500 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 18.0% [11.7%, 26.7%] | 17.0% [10.9%, 25.5%] | 65.0% [55.3%, 73.6%] | 0.010 [-0.094, 0.102] |
| vector | 100 | 18.0% [11.7%, 26.7%] | 20.0% [13.3%, 28.9%] | 62.0% [52.2%, 70.9%] | -0.020 [-0.147, 0.091] |
| hybrid | 100 | 18.0% [11.7%, 26.7%] | 19.0% [12.5%, 27.8%] | 63.0% [53.2%, 71.8%] | -0.010 [-0.120, 0.099] |
| hybrid_rerank | 100 | 17.0% [10.9%, 25.5%] | 32.0% [23.7%, 41.7%] | 51.0% [41.3%, 60.6%] | -0.150 [-0.278, -0.040] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 18.0% | 35.0% | 51.4% | 0.306 | n/a (n=0) | 190.0 |
| vector | 100 | 18.0% | 38.0% | 47.4% | 0.414 | n/a (n=0) | 182.2 |
| hybrid | 100 | 18.0% | 37.0% | 48.6% | 0.445 | n/a (n=0) | 181.5 |
| hybrid_rerank | 100 | 17.0% | 49.0% | 34.7% | 0.544 | n/a (n=0) | 185.4 |

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
| bm25 | 100 | $0.0001 | $0.0120 | $0.0007 [$0.0005, $0.0011] | 785.9 | 1134.7 | 1.00 | 1.00 |
| vector | 100 | $0.0001 | $0.0120 | $0.0007 [$0.0005, $0.0011] | 978.0 | 1290.4 | 1.00 | 1.00 |
| hybrid | 100 | $0.0001 | $0.0119 | $0.0007 [$0.0005, $0.0011] | 1053.8 | 1324.5 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0001 | $0.0133 | $0.0008 [$0.0005, $0.0013] | 5686.8 | 7867.2 | 1.00 | 1.00 |

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
| bm25 | $0.0001 | 18.0% | no | 0.010 | yes |
| vector | $0.0001 | 18.0% | no | -0.020 | no |
| hybrid | $0.0001 | 18.0% | yes | -0.010 | yes |
| hybrid_rerank | $0.0001 | 17.0% | no | -0.150 | no |

