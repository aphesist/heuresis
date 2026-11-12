# Confirmatory family: 18 comparisons, Holm across all

Penalised score, engine minus baseline; two-sided paired sign-flip permutation test. Complete-case: each dataset uses only the questions completed by all systems of its confirmatory family (column n).

- `musique`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.
- `multihoprag`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.
- `hoh`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.

| dataset | baseline | n | score diff | permutation p | Holm p (family) |
|---|---|---|---|---|---|
| musique | closed_book | 100 | 0.570 [0.404, 0.735] | 0.0010 | 0.0180 |
| musique | bm25 | 100 | 0.100 [-0.020, 0.226] | 0.1469 | 1.0000 |
| musique | vector | 100 | 0.030 [-0.093, 0.160] | 0.7532 | 1.0000 |
| musique | hybrid | 100 | 0.030 [-0.087, 0.146] | 0.7383 | 1.0000 |
| musique | hybrid_rerank | 100 | 0.070 [-0.071, 0.210] | 0.3816 | 1.0000 |
| musique | agentic | 100 | -0.020 [-0.196, 0.153] | 0.9261 | 1.0000 |
| multihoprag | closed_book | 100 | 0.100 [-0.069, 0.280] | 0.3007 | 1.0000 |
| multihoprag | bm25 | 100 | -0.260 [-0.396, -0.103] | 0.0090 | 0.0899 |
| multihoprag | vector | 100 | -0.200 [-0.357, -0.051] | 0.0320 | 0.2557 |
| multihoprag | hybrid | 100 | -0.250 [-0.390, -0.113] | 0.0040 | 0.0440 |
| multihoprag | hybrid_rerank | 100 | -0.170 [-0.300, -0.042] | 0.0260 | 0.2338 |
| multihoprag | agentic | 100 | 0.100 [-0.048, 0.258] | 0.2258 | 1.0000 |
| hoh | closed_book | 100 | 1.480 [1.310, 1.630] | 0.0010 | 0.0180 |
| hoh | bm25 | 100 | 0.840 [0.640, 1.060] | 0.0010 | 0.0180 |
| hoh | vector | 100 | 0.780 [0.580, 0.970] | 0.0010 | 0.0180 |
| hoh | hybrid | 100 | 0.810 [0.590, 1.010] | 0.0010 | 0.0180 |
| hoh | hybrid_rerank | 100 | 0.870 [0.680, 1.060] | 0.0010 | 0.0180 |
| hoh | agentic | 100 | 0.860 [0.660, 1.070] | 0.0010 | 0.0180 |
