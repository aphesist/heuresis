# Results: hoh, split `dev`

Questions planned: 100. Bootstrap: 1000 resamples, seed 0, 95% intervals. Price table: anthropic-2026-11.
Complete-case analysis: the confirmatory comparisons (Tables 5, 5b, 6 and the family table) use the 100 questions completed by all of `bm25`, `vector`, `hybrid`, `hybrid_rerank`. Completed per system: bm25 100, vector 100, hybrid 100, hybrid_rerank 100. Tables 1 to 4 and 7 use every question a system completed (column n).

## Table 1. Outcomes (split `dev`; n per system in column n)

| system | n | correct | wrong | abstained | penalised score |
|---|---|---|---|---|---|
| bm25 | 100 | 43.0% [33.7%, 52.8%] | 52.0% [42.3%, 61.5%] | 5.0% [2.2%, 11.2%] | -0.090 [-0.270, 0.090] |
| vector | 100 | 36.0% [27.3%, 45.8%] | 47.0% [37.5%, 56.7%] | 17.0% [10.9%, 25.5%] | -0.110 [-0.280, 0.070] |
| hybrid | 100 | 42.0% [32.8%, 51.8%] | 51.0% [41.3%, 60.6%] | 7.0% [3.4%, 13.7%] | -0.090 [-0.270, 0.090] |
| hybrid_rerank | 100 | 38.0% [29.1%, 47.8%] | 48.0% [38.5%, 57.7%] | 14.0% [8.5%, 22.1%] | -0.100 [-0.280, 0.080] |

## Table 2. Selective answering (split `dev`; AURC over answered questions, lower is better)

| system | n | accuracy | coverage | selective accuracy | AURC | abstains on unanswerable | mean answer chars |
|---|---|---|---|---|---|---|---|
| bm25 | 100 | 43.0% | 95.0% | 45.3% | 0.597 | n/a (n=0) | 104.0 |
| vector | 100 | 36.0% | 83.0% | 43.4% | 0.580 | n/a (n=0) | 95.9 |
| hybrid | 100 | 42.0% | 93.0% | 45.2% | 0.539 | n/a (n=0) | 98.1 |
| hybrid_rerank | 100 | 38.0% | 86.0% | 44.2% | 0.588 | n/a (n=0) | 96.2 |

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
| bm25 | 100 | $0.0002 | $0.0161 | $0.0004 [$0.0003, $0.0005] | 1079.7 | 2184.4 | 1.00 | 1.00 |
| vector | 100 | $0.0002 | $0.0164 | $0.0005 [$0.0004, $0.0006] | 4435.9 | 23643.1 | 1.00 | 1.00 |
| hybrid | 100 | $0.0002 | $0.0168 | $0.0004 [$0.0003, $0.0005] | 10050.3 | 24038.2 | 1.00 | 1.00 |
| hybrid_rerank | 100 | $0.0002 | $0.0161 | $0.0004 [$0.0003, $0.0006] | 9849.9 | 25413.2 | 1.00 | 1.00 |

## Table 4. Evidence (split `dev`; only questions with known gold units)

| system | citation n | citation precision | citation recall | retrieval recall (n) |
|---|---|---|---|---|
| bm25 | n/a | n/a | n/a | 1.000 (100) |
| vector | n/a | n/a | n/a | 0.880 (100) |
| hybrid | n/a | n/a | n/a | 0.990 (100) |
| hybrid_rerank | n/a | n/a | n/a | 0.920 (100) |

Only the engine cites units itself; baselines show retrieval recall only.

## Table 7. Accuracy against cost (split `dev`)

A system is on the frontier for a measure when no other system (oracle and exploratory variants excluded) costs no more and scores no less on it, with one strict. Costs are per question at the dated price table.

| system | mean cost | accuracy | on frontier (accuracy) | penalised score | on frontier (penalised) |
|---|---|---|---|---|---|
| bm25 | $0.0002 | 43.0% | yes | -0.090 | yes |
| vector | $0.0002 | 36.0% | no | -0.110 | no |
| hybrid | $0.0002 | 42.0% | no | -0.090 | no |
| hybrid_rerank | $0.0002 | 38.0% | no | -0.100 | no |

