# Confirmatory family: 18 comparisons, Holm across all

Penalised score, engine minus baseline; two-sided paired sign-flip permutation test. Complete-case: each dataset uses only the questions completed by all systems of its confirmatory family (column n).

- `musique`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.
- `multihoprag`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.
- `hoh`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.

| dataset | baseline | n | score diff | permutation p | Holm p (family) |
|---|---|---|---|---|---|
| musique | closed_book | 100 | 0.550 [0.343, 0.750] | 0.0010 | 0.0180 |
| musique | bm25 | 100 | 0.040 [-0.099, 0.176] | 0.6623 | 1.0000 |
| musique | vector | 100 | 0.020 [-0.121, 0.157] | 0.8851 | 1.0000 |
| musique | hybrid | 100 | -0.010 [-0.133, 0.103] | 1.0000 | 1.0000 |
| musique | hybrid_rerank | 100 | 0.020 [-0.129, 0.170] | 0.8851 | 1.0000 |
| musique | agentic | 100 | -0.110 [-0.272, 0.059] | 0.2677 | 1.0000 |
| multihoprag | closed_book | 100 | 0.060 [-0.100, 0.235] | 0.5624 | 1.0000 |
| multihoprag | bm25 | 100 | -0.340 [-0.470, -0.198] | 0.0010 | 0.0180 |
| multihoprag | vector | 100 | -0.280 [-0.414, -0.130] | 0.0010 | 0.0180 |
| multihoprag | hybrid | 100 | -0.220 [-0.370, -0.057] | 0.0170 | 0.1359 |
| multihoprag | hybrid_rerank | 100 | -0.200 [-0.333, -0.067] | 0.0110 | 0.0989 |
| multihoprag | agentic | 100 | 0.150 [-0.027, 0.354] | 0.1419 | 0.9930 |
| hoh | closed_book | 100 | 1.510 [1.340, 1.650] | 0.0010 | 0.0180 |
| hoh | bm25 | 100 | 0.820 [0.620, 1.020] | 0.0010 | 0.0180 |
| hoh | vector | 100 | 0.830 [0.640, 1.010] | 0.0010 | 0.0180 |
| hoh | hybrid | 100 | 0.810 [0.610, 1.010] | 0.0010 | 0.0180 |
| hoh | hybrid_rerank | 100 | 0.870 [0.660, 1.070] | 0.0010 | 0.0180 |
| hoh | agentic | 100 | 0.800 [0.600, 1.000] | 0.0010 | 0.0180 |
