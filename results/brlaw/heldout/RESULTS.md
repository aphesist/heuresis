# Held-out results: the legal citation-integrity test (`brlaw`)

Registration: `PREREGISTRATION-legal.md` (commit 18aeb40, section order followed). Run once, thinking at the model default, `max_tokens` 4096, model `claude-haiku-5-5`. Sets: BR-TaxQA-R `test` (615 questions) and `temporal_test` (240). 0 error rows, 0 skipped, no ledger stop; complete cases 615 and 240. Support results are **model-reviewed, not human-reviewed**.

## 1. Claim: verdicts

| hypothesis | verdict |
|---|---|
| H1 (primary): engine's tainted rate is lower than each baseline's, `test` | **supported**, 4 of 4 (Holm) |
| H1, `temporal_test` | **not supported** after Holm (0 of 4; direction as expected, discordant pairs 0 vs 1-5, floor effect: baselines 0.4-2.1% of all questions) |
| Co-primary: engine useful-answer rate not worse than `hybrid` by >10 points | **supported**: engine 34.0% useful vs hybrid 33.3% (difference +0.7 pts, one-sided lower bound -2.1 > -10); non-inferior to all four baselines |
| Support share (secondary, two-sided, no claim) | `test`: engine 74.2% vs hybrid 78.2%, agentic 78.8%, agentic+asof 79.2%, closed_book 26.1%; `temporal_test`: engine 98.8%, highest |

## 2. Data and run

Questions: `test` ae73379d...a06fbeda (615), `temporal_test` 1b46b7a3...3ede49 (240); hashes match the registration, and the frozen locked/surface/prompt/engine-config hashes were confirmed unchanged on this branch before the run. Spend: ledger `ledger-heldout.jsonl` (in this folder) US$7.47 of the US$10.00 cap (systems US$6.41; support judge US$0.85 including about US$0.14 of duplicated calls from a rerun; answer judge US$0.21).

## 3. Primary outcome: tainted answers (strict)

### `test`

| system | coverage | tainted, all questions | tainted, answered | covered-only, all |
|---|---|---|---|---|
| closed_book | 68.9% [65.2, 72.5] | 99/615 = 16.1% [13.4, 19.2] | 99/424 = 23.4% [19.6, 27.6] | 78/615 = 12.7% [10.3, 15.6] |
| hybrid | 66.3% [62.5, 70.0] | 37/615 = 6.0% [4.4, 8.2] | 37/408 = 9.1% [6.7, 12.2] | 26/615 = 4.2% [2.9, 6.1] |
| agentic | 77.6% [74.1, 80.7] | 55/615 = 8.9% [6.9, 11.5] | 55/477 = 11.5% [9.0, 14.7] | 41/615 = 6.7% [5.0, 8.9] |
| agentic+asof | 77.2% [73.8, 80.4] | 43/615 = 7.0% [5.2, 9.3] | 43/475 = 9.0% [6.8, 12.0] | 33/615 = 5.4% [3.9, 7.4] |
| engine | 78.2% [74.8, 81.3] | 1/615 = 0.2% [0.0, 0.9] | 1/481 = 0.2% [0.0, 1.2] | 1/615 = 0.2% [0.0, 0.9] |

Engine minus baseline (exact McNemar, two-sided; Holm over all 8; paired bootstrap 95% interval, 5,000 resamples, seed 20261112):

| baseline | engine-only / baseline-only | difference | raw p | Holm p |
|---|---|---|---|---|
| closed_book | 1 / 99 | -15.9 pts [-18.9, -13.2] | 1.59e-28 | 1.27e-27 |
| hybrid | 1 / 37 | -5.9 pts [-7.8, -4.1] | 2.84e-10 | 1.42e-09 |
| agentic | 1 / 55 | -8.8 pts [-11.2, -6.7] | 1.58e-15 | 1.11e-14 |
| agentic+asof | 1 / 43 | -6.8 pts [-8.9, -4.9] | 5.12e-12 | 3.07e-11 |

### `temporal_test`

| system | coverage | tainted, all questions | tainted, answered | covered-only, all |
|---|---|---|---|---|
| closed_book | 17.9% [13.6, 23.3] | 5/240 = 2.1% [0.9, 4.8] | 5/43 = 11.6% [5.1, 24.5] | 4/240 = 1.7% [0.7, 4.2] |
| hybrid | 30.8% [25.3, 36.9] | 1/240 = 0.4% [0.1, 2.3] | 1/74 = 1.4% [0.2, 7.3] | 1/240 = 0.4% [0.1, 2.3] |
| agentic | 37.9% [32.0, 44.2] | 5/240 = 2.1% [0.9, 4.8] | 5/91 = 5.5% [2.4, 12.2] | 5/240 = 2.1% [0.9, 4.8] |
| agentic+asof | 76.7% [70.9, 81.6] | 4/240 = 1.7% [0.7, 4.2] | 4/184 = 2.2% [0.9, 5.5] | 4/240 = 1.7% [0.7, 4.2] |
| engine | 76.7% [70.9, 81.6] | 0/240 = 0.0% [0.0, 1.6] | 0/184 = 0.0% [0.0, 2.1] | 0/240 = 0.0% [0.0, 1.6] |

Engine minus baseline (exact McNemar, two-sided; Holm over all 8; paired bootstrap 95% interval, 5,000 resamples, seed 20261112):

| baseline | engine-only / baseline-only | difference | raw p | Holm p |
|---|---|---|---|---|
| closed_book | 0 / 5 | -2.1 pts [-4.2, -0.4] | 0.0625 | 0.25 |
| hybrid | 0 / 1 | -0.4 pts [-1.2, 0.0] | 1 | 1 |
| agentic | 0 / 5 | -2.1 pts [-4.2, -0.4] | 0.0625 | 0.25 |
| agentic+asof | 0 / 4 | -1.7 pts [-3.3, -0.4] | 0.125 | 0.25 |

The engine's single tainted `test` answer: one article not found. Coverage (answered share) of the engine is the highest or tied on both sets, so the low rate is not from abstaining more.

## 4. Co-primary non-inferiority check

Run as registered after a logged guard change (Deviations). Answer judge `bench.judge` (prompt hash 9542c78c...) over all 2,262 answered `test` rows (10 unreadable, counted as not EQUIVALENT). Useful = answered, not tainted (strict), EQUIVALENT. One-sided paired bootstrap, 5,000 resamples, seed 20261112; non-inferior if the lower 95% bound of engine minus system exceeds -10 points.

| system | judge-EQUIVALENT answers | useful answers (of 615) | US$ per useful answer |
|---|---|---|---|
| closed_book | 185 | 139/615 = 22.6% [19.5, 26.1] | 0.00289 |
| hybrid | 221 | 205/615 = 33.3% [29.7, 37.1] | 0.00308 |
| agentic | 264 | 236/615 = 38.4% [34.6, 42.3] | 0.0047 |
| agentic+asof | 244 | 229/615 = 37.2% [33.5, 41.1] | 0.00505 |
| engine | 210 | 209/615 = 34.0% [30.3, 37.8] | 0.0078 |

| engine minus | difference | two-sided 95% interval | one-sided lower bound | non-inferior (> -10 pts) |
|---|---|---|---|---|
| closed_book | +11.4 pts | [+6.5, +16.3] | +7.3 | yes |
| hybrid | +0.7 pts | [-2.8, +3.9] | -2.1 | yes |
| agentic | -4.4 pts | [-8.3, -0.5] | -7.6 | yes |
| agentic+asof | -3.2 pts | [-7.0, +0.3] | -6.3 | yes |

**Verdict: supported.** The engine is non-inferior to `hybrid` (+0.7 points, lower bound -2.1) and to every other system, including `agentic` (-4.4 points, lower bound -7.6, the closest). It is better than `closed_book`. Against `agentic` the two-sided interval excludes zero (the engine has fewer useful answers by 4.4 points). Cost per useful answer is highest for the engine (US$0.0078 against 0.0029-0.0051). The answer judge is not human-validated (registration section 7); the engine's judge-EQUIVALENT count (210) is the second lowest, with the tainted filter removing almost none of them.

## 5. Secondary outcomes

### `test`

| system | answered | refs/answer | norm not found | article not found | not in force | support share | US$/question | median latency (s) | calls | searches |
|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 424 | 2.82 | 18/935 | 108/935 | 9/809 | 209/800 = 26.1% [23.2, 29.3] | 0.00065 | 6.3 | 1.0 | 0.0 |
| hybrid | 408 | 3.59 | 11/1218 | 32/1218 | 7/1175 | 910/1163 = 78.2% [75.8, 80.5] | 0.00103 | 5.6 | 1.0 | 1.0 |
| agentic | 477 | 3.44 | 12/1294 | 63/1294 | 2/1219 | 957/1214 = 78.8% [76.4, 81.0] | 0.0018 | 7.8 | 2.85 | 1.85 |
| agentic+asof | 475 | 3.38 | 13/1267 | 44/1267 | 0/1210 | 956/1207 = 79.2% [76.8, 81.4] | 0.00188 | 7.5 | 2.9 | 1.9 |
| engine | 481 | 3.66 | 0/1625 | 1/1625 | 0/1624 | 1203/1622 = 74.2% [72.0, 76.2] | 0.00265 | 10.5 | 2.89 | 2.1 |

### `temporal_test`

| system | answered | refs/answer | norm not found | article not found | not in force | support share | US$/question | median latency (s) | calls | searches |
|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 43 | 4.19 | 2/85 | 3/85 | 2/80 | 35/78 = 44.9% [34.3, 55.9] | 0.0005 | 4.6 | 1.0 | 0.0 |
| hybrid | 74 | 2.78 | 0/172 | 1/172 | 0/171 | 160/171 = 93.6% [88.8, 96.4] | 0.0004 | 3.0 | 1.0 | 1.0 |
| agentic | 91 | 3.56 | 0/212 | 2/212 | 8/210 | 153/202 = 75.7% [69.4, 81.1] | 0.00238 | 11.0 | 3.84 | 2.84 |
| agentic+asof | 184 | 2.76 | 0/389 | 2/389 | 2/387 | 356/385 = 92.5% [89.4, 94.7] | 0.00164 | 4.0 | 2.71 | 1.71 |
| engine | 184 | 2.47 | 0/427 | 0/427 | 0/427 | 422/427 = 98.8% [97.3, 99.5] | 0.00123 | 5.2 | 2.39 | 1.6 |

Cost per useful answer: section 4. Abstention rate = 1 - coverage (table above).

### Version in force, `temporal_test` (code-scored, n=240 per system)

| system | gave the gold version | gave another version | abstained | undetermined | cited repealed | no gold / other |
|---|---|---|---|---|---|---|
| agentic | 63 | 22 | 149 | 3 | 2 | 1 |
| agentic+asof | 141 | 9 | 56 | 8 | 1 | 25 |
| closed_book | 18 | 16 | 197 | 5 | 2 | 2 |
| engine | 129 | 5 | 56 | 13 | 0 | 37 |
| hybrid | 69 | 1 | 166 | 4 | 0 | 0 |

`agentic+asof` and the engine answer the same 184 questions; the engine gave the superseded wording 5 times, `agentic+asof` 9, `agentic` 22, `closed_book` 16, `hybrid` 1 (hybrid abstained on 166).

### Engine gate drops by type (claims failing each check; a claim can fail several)

| set | `references_traced` | `numbers_traced` | `exists` | `llm_support` | abstentions: unsupported / no_source / other |
|---|---|---|---|---|---|
| `test` (1,798 claims) | 408 | 315 | 693 | 111 | 97 / 33 / 4 outside coverage |
| `temporal_test` (561 claims) | 42 | 196 | 50 | 6 | 25 / 30 / 1 not valid at date |

(`exists` failures include the `references_traced` reuse of that flag, so the two counts overlap.)

## 6. The judges and the model review

The support judge ran over every resolved, in-force reference of every answered row (6,019 judgements on `test`, 1,263 on `temporal_test`). The registered human check was replaced, by the owner's decision (Deviations log, 2026-11-12), by a blind review from Claude Opus: 200 rows (20 per system per split), each with the question, the sentence, the reference as written and the full provision text in force on the as-of date; no system name, judge verdict or score. All 200 references resolved (the judge only judges resolved references, so no `NOT FOUND` rows appear). Reviewer labels and agreement: `agreement.json`, `reviewer_labels.csv` (quoted provision words stripped).

Judge (rows) by reviewer (columns), all 200 rows; the judge's labels are SUPPORTED / NOT_SUPPORTED only, so the PARTIAL row is empty:

| judge \ reviewer | SUPPORTED | PARTIAL | NOT_SUPPORTED |
|---|---|---|---|
| SUPPORTED | 137 | 6 | 0 |
| PARTIAL | 0 | 0 | 0 |
| NOT_SUPPORTED | 5 | 17 | 35 |

Disagreement on SUPPORTED vs not: 11/200 = 5.5%. Cohen's kappa 0.866 on SUPPORTED/not (0.684 on the 3x3 table). **The registered rule (>20% disagreement) does not fire**; the judge's support figures are not reported as unreliable. The 17 judge-NOT_SUPPORTED rows that the reviewer calls PARTIAL, and the 5 it calls SUPPORTED, are the disagreement mass; the judge never disagrees by calling SUPPORTED what the reviewer calls NOT_SUPPORTED. Both are Claude models, so correlated errors are reduced, not removed.

| system | n | disagree (S vs not) | kappa (S/not) | judge support | reviewer support | reviewer S or P |
|---|---|---|---|---|---|---|
| agentic | 40 | 4/40 | 0.76 | 70.0% | 70.0% | 77.5% |
| agentic+asof | 40 | 2/40 | 0.77 | 87.5% | 87.5% | 95.0% |
| closed_book | 40 | 1/40 | 0.95 | 35.0% | 37.5% | 47.5% |
| engine | 40 | 2/40 | 0.84 | 80.0% | 80.0% | 95.0% |
| hybrid | 40 | 2/40 | 0.83 | 85.0% | 80.0% | 97.5% |

By split: `test` 7/100, `temporal_test` 4/100 disagreements. Per-system 3x3 tables are in `agreement.json`. Samples are 40 rows per system, so the per-system shares carry wide intervals and are stratified, not the full-population support shares of section 5.

## 7. Deviations and limits

- The dev-only guard in `bench/judge.py` blocked the answer judge; with the owner's go-ahead it was changed to accept a held-out split only with `--registered-run` and a matching registered hash (tested, suite 625 passed), logged in the Deviations log, and the judge was run after all answers were complete and before the non-inferiority result was seen. This is the only change under `src/`.
- Human validation replaced by the Opus blind review (logged before the review ran).
- A first support-judge pass was cut by a timeout of mine and rerun (about US$0.14 of duplicate calls).
- The gate, the judge and the generator are the same model family; the strict tainted outcome does not use the judge.
- `temporal_test` is a floor-limited set for the primary outcome (baselines 0.4-2.1% tainted); the engine's gain there is shown by version-in-force and support, not by McNemar.
- Tag `prereg-legal-v1` could not be pushed from this environment.
