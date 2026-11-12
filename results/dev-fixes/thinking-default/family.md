# Confirmatory family: 12 comparisons, Holm across all

Penalised score, engine minus baseline; two-sided paired sign-flip permutation test. Complete-case: each dataset uses only the questions completed by all systems of its confirmatory family (column n).

- `musique`: n = 100 common questions; completed per system: closed_book 100, bm25 100, hybrid 100, agentic 100, engine 100.
- `multihoprag`: n = 100 common questions; completed per system: closed_book 100, bm25 100, hybrid 100, agentic 100, engine 100.
- `hoh`: n = 100 common questions; completed per system: closed_book 100, bm25 100, hybrid 100, agentic 100, engine 100.

| dataset | baseline | n | score diff | permutation p | Holm p (family) |
|---|---|---|---|---|---|
| musique | closed_book | 100 | 0.080 [-0.071, 0.223] | 0.3536 | 0.9530 |
| musique | bm25 | 100 | -0.070 [-0.186, 0.031] | 0.3177 | 0.9530 |
| musique | hybrid | 100 | -0.040 [-0.134, 0.057] | 0.5235 | 0.9530 |
| musique | agentic | 100 | -0.240 [-0.366, -0.118] | 0.0010 | 0.0120 |
| multihoprag | closed_book | 100 | -0.160 [-0.324, 0.009] | 0.0749 | 0.2997 |
| multihoprag | bm25 | 100 | -0.230 [-0.429, -0.041] | 0.0300 | 0.1499 |
| multihoprag | hybrid | 100 | -0.250 [-0.434, -0.069] | 0.0180 | 0.1079 |
| multihoprag | agentic | 100 | -0.270 [-0.442, -0.109] | 0.0030 | 0.0210 |
| hoh | closed_book | 100 | 1.080 [0.900, 1.260] | 0.0010 | 0.0120 |
| hoh | bm25 | 100 | 0.850 [0.670, 1.040] | 0.0010 | 0.0120 |
| hoh | hybrid | 100 | 0.790 [0.610, 0.980] | 0.0010 | 0.0120 |
| hoh | agentic | 100 | 0.780 [0.600, 0.970] | 0.0010 | 0.0120 |
