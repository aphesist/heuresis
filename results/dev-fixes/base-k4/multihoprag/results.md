# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 500 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 39.0% [30.0%, 48.8%] | 9.0% [4.8%, 16.2%] | 52.0% [42.3%, 61.5%] | 0.300 [0.177, 0.423] |
| vector | 100 | 33.0% [24.6%, 42.7%] | 7.0% [3.4%, 13.7%] | 60.0% [50.2%, 69.1%] | 0.260 [0.131, 0.372] |
| hybrid | 100 | 39.0% [30.0%, 48.8%] | 6.0% [2.8%, 12.5%] | 55.0% [45.2%, 64.4%] | 0.330 [0.205, 0.450] |
| hybrid_rerank | 100 | 33.0% [24.6%, 42.7%] | 10.0% [5.5%, 17.4%] | 57.0% [47.2%, 66.3%] | 0.230 [0.091, 0.352] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 39.0% | 36.0% | 75.0% | 0.099 | 100.0% (n=12) | 320.9 |
| vector | 100 | 33.0% | 28.0% | 75.0% | 0.184 | 100.0% (n=12) | 312.0 |
| hybrid | 100 | 39.0% | 33.0% | 81.8% | 0.063 | 100.0% (n=12) | 304.2 |
| hybrid_rerank | 100 | 33.0% | 31.0% | 67.7% | 0.196 | 100.0% (n=12) | 313.0 |

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
| bm25 | 100 | $0.0003 | $0.0252 | $0.0006 [$0.0005, $0.0008] | 818.0 | 1245.1 | 1.00 | 1.00 |
| vector | 100 | $0.0002 | $0.0241 | $0.0007 [$0.0006, $0.0010] | 981.3 | 1424.3 | 1.00 | 1.00 |
| hybrid | 100 | $0.0003 | $0.0250 | $0.0006 [$0.0005, $0.0009] | 1063.4 | 1500.2 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0003 | $0.0252 | $0.0008 [$0.0006, $0.0011] | 15242.6 | 17285.2 | 1.00 | 1.00 |

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
| bm25 | $0.0003 | 39.0% | no | 0.300 | no |
| vector | $0.0002 | 33.0% | yes | 0.260 | yes |
| hybrid | $0.0003 | 39.0% | yes | 0.330 | yes |
| hybrid_rerank | $0.0003 | 33.0% | no | 0.230 | no |

