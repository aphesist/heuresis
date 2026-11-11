# Confirmatory family: 18 comparisons, Holm across all

Penalised score, engine minus baseline; two-sided paired sign-flip permutation test. Complete-case: each dataset uses only the questions completed by all systems of its confirmatory family (column n).

- `musique`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.
- `multihoprag`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.
- `hoh`: n = 100 common questions; completed per system: closed_book 100, bm25 100, vector 100, hybrid 100, hybrid_rerank 100, agentic 100, engine 100.

| dataset | baseline | n | score diff | permutation p | Holm p (family) |
|---|---|---|---|---|---|
| musique | closed_book | 100 | -0.040 [-0.180, 0.089] | 0.6494 | 0.6494 |
| musique | bm25 | 100 | -0.120 [-0.228, -0.019] | 0.0420 | 0.1139 |
| musique | vector | 100 | -0.120 [-0.223, -0.029] | 0.0380 | 0.1139 |
| musique | hybrid | 100 | -0.160 [-0.255, -0.060] | 0.0030 | 0.0270 |
| musique | hybrid_rerank | 100 | -0.190 [-0.296, -0.089] | 0.0040 | 0.0280 |
| musique | agentic | 100 | -0.340 [-0.485, -0.189] | 0.0010 | 0.0180 |
| multihoprag | closed_book | 100 | -0.230 [-0.373, -0.069] | 0.0190 | 0.0759 |
| multihoprag | bm25 | 100 | -0.250 [-0.371, -0.134] | 0.0030 | 0.0270 |
| multihoprag | vector | 100 | -0.200 [-0.300, -0.092] | 0.0020 | 0.0200 |
| multihoprag | hybrid | 100 | -0.200 [-0.303, -0.086] | 0.0070 | 0.0420 |
| multihoprag | hybrid_rerank | 100 | -0.190 [-0.302, -0.070] | 0.0080 | 0.0420 |
| multihoprag | agentic | 100 | -0.310 [-0.463, -0.149] | 0.0010 | 0.0180 |
| hoh | closed_book | 100 | 0.840 [0.680, 1.000] | 0.0010 | 0.0180 |
| hoh | bm25 | 100 | 0.580 [0.380, 0.780] | 0.0010 | 0.0180 |
| hoh | vector | 100 | 0.560 [0.370, 0.750] | 0.0010 | 0.0180 |
| hoh | hybrid | 100 | 0.600 [0.410, 0.790] | 0.0010 | 0.0180 |
| hoh | hybrid_rerank | 100 | 0.630 [0.440, 0.810] | 0.0010 | 0.0180 |
| hoh | agentic | 100 | 0.590 [0.400, 0.790] | 0.0010 | 0.0180 |
