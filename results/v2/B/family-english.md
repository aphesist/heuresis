# Confirmatory family: 12 comparisons, Holm across all

Penalised score, engine minus baseline; two-sided paired sign-flip permutation test. Complete-case: each dataset uses only the questions completed by all systems of its confirmatory family (column n).

- `musique`: n = 100 common questions; completed per system: closed_book 100, hybrid 100, agentic 100, engine 100, engine2 100.
- `multihoprag`: n = 100 common questions; completed per system: closed_book 100, hybrid 100, agentic 100, engine 100, engine2 100.
- `hoh`: n = 100 common questions; completed per system: closed_book 100, hybrid 100, agentic 100, engine 100, engine2 100.

| dataset | baseline | n | score diff | permutation p | Holm p (family) |
|---|---|---|---|---|---|
| musique | closed_book | 100 | 0.370 [0.202, 0.540] | 0.0002 | 0.0018 |
| musique | hybrid | 100 | 0.190 [0.094, 0.290] | 0.0006 | 0.0048 |
| musique | agentic | 100 | 0.010 [-0.110, 0.130] | 1.0000 | 1.0000 |
| musique | engine | 100 | 0.090 [-0.040, 0.225] | 0.2609 | 0.7826 |
| multihoprag | closed_book | 100 | 0.170 [0.010, 0.344] | 0.0677 | 0.4062 |
| multihoprag | hybrid | 100 | -0.130 [-0.258, 0.000] | 0.0680 | 0.4062 |
| multihoprag | agentic | 100 | -0.110 [-0.234, 0.020] | 0.1309 | 0.5235 |
| multihoprag | engine | 100 | 0.420 [0.205, 0.628] | 0.0008 | 0.0056 |
| hoh | closed_book | 100 | 0.880 [0.710, 1.050] | 0.0001 | 0.0012 |
| hoh | hybrid | 100 | 0.810 [0.620, 1.010] | 0.0001 | 0.0012 |
| hoh | agentic | 100 | 0.810 [0.610, 1.010] | 0.0001 | 0.0012 |
| hoh | engine | 100 | 0.030 [-0.090, 0.160] | 0.7591 | 1.0000 |
