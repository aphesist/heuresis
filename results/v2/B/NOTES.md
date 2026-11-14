# Stage B: dev comparison of the six systems (calibration data, not results)

Splits: law `dev` (100) and `temporal` (120) of `brlaw-core`; English `dev2` (3 x 100). These splits were seen during v1 design.
Code state: `v2` at c0de81c (judge max_tokens 4096, a reply cut at max_tokens counts as unreadable; LLMError carries HTTP status).
Hashes: protected 5caae6ef44e8634d2e03134bc6f08073627b9fd6112ca65b84b5ffd2bada9657, locked f13783b57968b2b8b9313bb31d89f83aac1ea417520a9de70676aa890d52ad53,
surface 547d7f32387e2e4aff33eaa5ff39a388b52084f3680e54515ccc3d1433d878b3, prompts c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b.
Generator claude-haiku-5-5 (thinking at default, caching on); engine2 judge claude-sonnet-5-5 (ablation: claude-haiku-5-5).
Full per-run tables are in each folder's `results.md` (not committed: they come from rows that carry answer text); the family tables and the legal analysis are committed beside this file.

## Spending (US$)
| ledger | what | total |
|---|---|---|
| `ledger-B-smoke.jsonl` (results/v2/smoke) | three 5-question smoke runs (the first hit the judge failure) | 0.2938 |
| `ledger-B-run.jsonl` | stage B proper (B1 to B5) up to 5.94, plus the Haiku-judge ablation | 6.9756 (B proper about 5.94, ablation about 1.04) |
| both | | 7.27 |
Caps never reached (B 11.80, ablation 13.40). Smoke folders are excluded from every analysis.

## Errors per step (see error-counts.txt)
B1: 3 error rows (same question taxqa-266, HTTP 503 "credential validation failed", transient); one resume cleared them. B2, B3 (x3), citations, support judge, ablation (x4): 0 error rows.
B2 was interrupted once by a container restart (330 of 720 rows written), then resumed; not an API error. Unreadable support verdicts: law dev 3 of 402, musique 0 of 80, multihoprag 10 of 106, hoh 1 of 193.

## Outcomes (primary, containment grade; the law dev split has no answer string to contain, so law correctness is the judge-assisted/useful/tainted numbers below)
| set | system | correct | wrong | abstained | penalised score | coverage |
|---|---|---|---|---|---|---|
| law dev | closed_book / hybrid / agentic / engine / engine2 | 0 / 0 / 0 / 0 / 0 % | 75 / 62 / 75 / 76 / 41 % | 25 / 38 / 25 / 24 / 59 % | -0.750 / -0.620 / -0.750 / -0.760 / -0.410 | 75 / 62 / 75 / 76 / 41 % |
| law temporal | see analysis-law.json (coverage engine2 79%, tainted 0/120) | | | | | |
| musique | engine2 | 37.0 | 3.0 | 60.0 | 0.340 [0.240, 0.444] | 40% |
| multihoprag | engine2 | 51.0 | 12.0 | 37.0 | 0.390 [0.257, 0.514] | 51% (wrong rate when answered 23.5%) |
| hoh | engine2 | 74.0 | 13.0 | 13.0 | 0.610 [0.470, 0.740] | 87% |
Per-system English and temporal rows for the other five systems are in `family-*.md` (differences) and in each `results.md`.

## engine2 vs every other system: paired penalised-score differences (engine2 minus baseline, 95% interval, Holm p)
Law `dev` (n=100): closed_book +0.340 [0.230, 0.450]; hybrid +0.210 [0.110, 0.310]; agentic +0.340 [0.240, 0.440]; engine +0.350 [0.240, 0.460]; all Holm p 0.0008.
Law `temporal` (n=120): closed_book -0.583 [-0.700, -0.458]; hybrid -0.425 [-0.508, -0.342]; agentic -0.283 [-0.392, -0.167]; engine 0.000 [-0.092, 0.092] (p 1.0). engine2 is lower on temporal because it abstains more than the baselines on this score.
musique: closed_book +0.370 [0.202, 0.540]; hybrid +0.190 [0.094, 0.290]; agentic +0.010 [-0.110, 0.130]; engine +0.090 [-0.040, 0.225].
multihoprag: closed_book +0.170 [0.010, 0.344]; hybrid -0.130 [-0.258, 0.000]; agentic -0.110 [-0.234, 0.020]; engine +0.420 [0.205, 0.628] (Holm p 0.0056).
hoh: closed_book +0.880 [0.710, 1.050]; hybrid +0.810 [0.620, 1.010]; agentic +0.810 [0.610, 1.010]; engine +0.030 [-0.090, 0.160].
(agentic+asof is exploratory and not in the family.)

## Law: useful, tainted, judge-assisted (dev)
| system | useful /100 | tainted /100 | judge-assisted correct | cost per question |
|---|---|---|---|---|
| closed_book | 21 | 14 | 28% | 0.0007 |
| hybrid | 33 | 5 | 35% | 0.0010 |
| agentic | 32 | 9 | 36% | 0.0019 |
| agentic+asof | 37 | 6 | 40% | 0.0020 |
| engine | 25 | 0 | 25% | 0.0030 |
| engine2 | 25 | 0 | 25% | 0.0119 (generator 0.0040, judge 0.0080) |
H1 (design check): engine2 is NOT non-inferior to agentic on useful answers (lower bound -0.13 vs margin -0.03) and NOT superior to engine (difference 0.00 [-0.08, 0.08]). Cost per useful answer for engine2 is $0.0478 (generator 0.0158, judge 0.0319), $0.036 more than engine and $0.042 more than agentic. engine2's tainted rate is 0/100 on dev and 0/120 on temporal; closed_book 14, agentic 9 on dev. Support check on engine2 citations (dev): 29/171 supported.
Temporal (H4 design check): engine2 median latency 7.1 s, tainted 0/120, citations 107/140 supported; see analysis-law.json `h4`.

## Costs and latency (mean US$ per question, median ms)
| set | closed_book | hybrid | agentic | engine | engine2 | engine2 median ms |
|---|---|---|---|---|---|---|
| law dev | 0.0007 | 0.0010 | 0.0019 | 0.0030 | 0.0119 | 12487 |
| law temporal | 0.0005 | 0.0004 | 0.0018 | 0.0010 | 0.0041 | 7094 |
| musique | 0.0003 | 0.0003 | 0.0009 | 0.0017 | 0.0052 | 7722 |
| multihoprag | 0.0002 | 0.0006 | 0.0013 | 0.0016 | 0.0076 | 6492 |
| hoh | 0.0002 | 0.0002 | 0.0002 | 0.0003 | 0.0027 | 5338 |
Cost per correct answer (English, engine2): musique $0.0141, multihoprag $0.0149, hoh $0.0036. Latency is with 4 workers and is indicative only.

## Ablation: engine2 with the Sonnet judge vs a Haiku judge (same splits)
| set | judge | correct | wrong | abstained | penalised score | cost/question |
|---|---|---|---|---|---|---|
| law dev | Sonnet | 0 | 41 | 59 | -0.410 | 0.0119 |
| law dev | Haiku | 0 | 20 | 80 | -0.200 | 0.0045 |
| musique | Sonnet / Haiku | 37 / 19 | 3 / 1 | 60 / 80 | 0.340 / 0.180 | 0.0052 / 0.0028 |
| multihoprag | Sonnet / Haiku | 51 / 21 | 12 / 2 | 37 / 77 | 0.390 / 0.190 | 0.0076 / 0.0026 |
| hoh | Sonnet / Haiku | 74 / 60 | 13 / 12 | 13 / 28 | 0.610 / 0.480 | 0.0027 / 0.0005 |
The Haiku judge is 2 to 5 times cheaper but abstains far more (musique 80%, multihoprag 77%, law 80%), losing accuracy at similar error rate. Sonnet judge is the better calibration.

## engine2 abstention types and gate drops (law)
dev: status answered 36, abstained 59, partial 5. Abstention types: unsupported 30, no_source 25, false_premise 2, conflict 2. Claims 675: supported 552, partial 61, unsupported 62. Dropped claims 348: withheld 286, judge unsupported 44, gate references_traced 10, numbers_traced 7, both 1. Claims failing the check: numbers_traced 8, references_traced 11. Rows below tau: 0.
temporal: answered 68, abstained 24, partial 27, divergent 1. Abstention types: no_source 12, conflict 7, unsupported 4, not_valid_at_date 2. Claims 471: supported 400, partial 27, unsupported 44. Dropped 82: withheld 38, gate numbers_traced 23, references_traced 14, judge unsupported 7.

## Measured engine2 cost and re-projection
Measured per question vs the plan's 0.0098 for engine2: law dev 0.0119 (1.2x), law temporal 0.0041 (0.4x), English 0.0052 / 0.0076 / 0.0027 (mean 0.0052, 0.5x). The five earlier systems on law dev cost 0.0066 per question (plan 0.0082), English 0.0010-0.0013. Stage B proper cost about 5.94 against a plan of 7.84 and a cap of 11.80.
Stages C to F were not re-projected here: I did not read their plan sections. Scale their engine2 lines by the ratios above (law dev-like questions about 1.2x, temporal-like and English about 0.4-0.5x the planned engine2 figure); the judge is about two thirds of engine2's cost on law dev, so the Sonnet judge dominates.

## Setup notes
Datasets built with the pinned loaders (manifests verified). leis cloned partial at c9f21b4 (`federal/` and `constituicao.md` only, the full history is over 28 GB). brlaw-core, brlaw-core-t, brlaw, brlaw-t built; stores data/db/brlaw-core.db (embedded), data/db/brlaw.db and brlaw-t.db (ingested, no embeddings). brlaw-core-t.db embedding was interrupted by a container restart and is still to be completed before stage F. brlaw-core-t is built with `build_corpus(..., include_test=True)` (scripts/brlaw/build.py does not build it). No held-out split was run; one early verification print of dataset objects showed a few question texts from the loader and nothing was scored on them.
