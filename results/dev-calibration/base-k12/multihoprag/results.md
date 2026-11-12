# Results: multihoprag, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 43.0% [33.7%, 52.8%] | 7.0% [3.4%, 13.7%] | 50.0% [40.4%, 59.6%] | 0.360 [0.241, 0.476] |
| vector | 100 | 31.0% [22.8%, 40.6%] | 5.0% [2.2%, 11.2%] | 64.0% [54.2%, 72.7%] | 0.260 [0.154, 0.368] |
| hybrid | 100 | 40.0% [30.9%, 49.8%] | 9.0% [4.8%, 16.2%] | 51.0% [41.3%, 60.6%] | 0.310 [0.192, 0.419] |
| hybrid_rerank | 100 | 36.0% [27.3%, 45.8%] | 3.0% [1.0%, 8.5%] | 61.0% [51.2%, 70.0%] | 0.330 [0.230, 0.427] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 43.0% | 38.0% | 81.6% | 0.074 | 100.0% (n=12) | 242.3 |
| vector | 100 | 31.0% | 24.0% | 79.2% | 0.065 | 100.0% (n=12) | 241.8 |
| hybrid | 100 | 40.0% | 37.0% | 75.7% | 0.096 | 100.0% (n=12) | 228.1 |
| hybrid_rerank | 100 | 36.0% | 27.0% | 88.9% | 0.074 | 100.0% (n=12) | 247.0 |

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
| bm25 | 100 | $0.0008 | $0.0817 | $0.0019 [$0.0015, $0.0024] | 2382.1 | 3309.4 | 1.00 | 1.00 |
| vector | 100 | $0.0008 | $0.0777 | $0.0025 [$0.0019, $0.0036] | 2122.2 | 3436.6 | 1.00 | 1.00 |
| hybrid | 100 | $0.0008 | $0.0804 | $0.0020 [$0.0017, $0.0026] | 2447.0 | 3522.8 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0008 | $0.0817 | $0.0023 [$0.0018, $0.0030] | 10145.6 | 12508.2 | 1.00 | 1.00 |

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
| bm25 | $0.0008 | 43.0% | yes | 0.360 | yes |
| vector | $0.0008 | 31.0% | yes | 0.260 | yes |
| hybrid | $0.0008 | 40.0% | yes | 0.310 | yes |
| hybrid_rerank | $0.0008 | 36.0% | no | 0.330 | no |

