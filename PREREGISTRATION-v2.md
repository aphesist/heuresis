# Pre-registration (DRAFT): the v2 engine on the English `test` splits

Status: **DRAFT. Not registered. To be frozen by the owner before any held-out run.** It becomes registered when the owner fills the `<...>` placeholders (from command output, never by guess), commits this file and tags the commit.
Values marked **[proposed]** are choices made here, not measurements. Definitions and statistics are those of `PREREGISTRATION.md` (the English benchmark) and `PREREGISTRATION-legal.md`; nothing in them is changed.
The legal held-out sets of the second comparison are registered in `PREREGISTRATION-legal-v2.md`. Companion documents: `docs/design-v2.md` section (g), `docs/v2-contracts.md`, `docs/v2-test-plan.md` (stage E: commands, cost).

## 0. Disclosure

The English `test` splits (500 questions each of `musique`, `multihoprag`, `hoh`) have **never been answered by any model**; two retrieval-only checks touched them (`PREREGISTRATION.md` section 2a). So this is a first test on these splits for `engine2`.
The v2 design, however, **used the aggregate results of the first legal held-out run** (`results/brlaw/heldout/RESULTS.md`; never its questions or rows) and the `dev`, `dev2` and `temporal` splits, on which `engine2` was developed and calibrated. The design's reading of those
aggregates is a hypothesis; this registration does not test it for law (see `PREREGISTRATION-legal-v2.md`). Nothing is tuned after registration.

## 1. Claim

On the three English datasets, `engine2` answers only with a statement whose every sentence was checked against the sources it cites, as of the question's date, or refuses; as a result **its error rate among answered questions is lower than that of `agentic` and `agentic+asof`**, its confidence orders its answers, and it
is not meaningfully worse than date-aware agentic search on the penalised score. It is not claimed to be cheaper (section 5).

## 2. Data

| Set | Questions | Id-list sha256 | Notes |
|---|---|---|---|
| `musique` `test` | 500 | `<sha256 of ordered question ids: fill from the dataset manifest>` | all answerable; no dates; no pool |
| `multihoprag` `test` | 500 | `<sha256 of ordered question ids: fill from the dataset manifest>` | 59 unanswerable (`PREREGISTRATION.md`) |
| `hoh` `test` | 500 | `<sha256 of ordered question ids: fill from the dataset manifest>` | dated; current / outdated strata |

Splits are cut by `sha256("20261111:<id>")` as in `PREREGISTRATION.md` section 2; manifest hashes: `<fill from each MANIFEST.json>`. Splits other than `test` that `engine2` has seen: `dev`, `dev2`, rotating and calibration draws (`rot<c>`, `cal<k>`), and the improvement loop's draws; none overlaps `test` (`bench/splits.py`, tested).
`bench.run` refuses `test` without `--registered-run PREREGISTRATION-v2.md` and a matching hash.

## 3. Systems (frozen)

Six systems, run together in one session, paired on the same questions: `closed_book`, `hybrid` (k = 8), `agentic` (k = 5, at most 4 searches), `agentic+asof`, `engine` (v1 at its registered configuration, `PREREGISTRATION.md` section 7 with `decide.mode = "grade"`, `answer.mode = "search"`), `engine2` (the reference of every paired comparison).
Generator `claude-haiku-5-5`, thinking at the default, `draft.max_tokens` 4096, no temperature. Command per dataset: `--systems closed_book,hybrid,agentic,engine,engine2 --time-aware-variants --variants-of agentic --thinking default --set draft.max_tokens=4096 --v2-cache --registered-run PREREGISTRATION-v2.md`
(`docs/v2-test-plan.md` stage E). `agentic+asof` is built as an exploratory copy by the harness, so the report's confirmatory family omits it; it is compared in the exploratory table and in sections 4.1 and 4.2 below.

`engine2` settings: surface `<v2 surface hash: heuresis hash output>` (packaged default, no override); locked judge on `claude-sonnet-5-5`, thinking disabled (`v2/locked/policy.json`; the manifest records it and `judge_is_policy_model`); policy alpha 0.05, delta 0.10, `default_tau` 0.5; calibration files per dataset
`<path and sha256 per dataset, or "none: nothing certified">`, fitted by `bench.calibrate2` on the calibration blocks (`cal0` for `multihoprag` and `hoh`, `dev2` for `musique`) with the containment label, never on `test`; protected files hash `<protected hash: heuresis hash output>`.
The benchmark's own judges (the judge-assisted grade, `bench.judge`) stay on `claude-haiku-5-5` and are secondary.

## 4. Hypotheses, outcomes and tests

Grading is the deterministic containment grade of `PREREGISTRATION.md` section 5 (outcome correct / wrong / abstained; unanswerable abstained is correct; statuses answered and partial count as answering). Penalised score: +1 / 0 / -1. Bootstrap: 10,000 resamples, seed 0, clusters as in `PREREGISTRATION.md` section 2.
Holm at alpha 0.05 is applied within each hypothesis family below, over datasets and comparators. Complete-case analysis over the questions completed by all six systems.

**H2: refusal instead of error.** (a) Per dataset, `engine2`'s error rate among answered questions (wrong / answered) is lower than that of `agentic` and of `agentic+asof`: exact McNemar (two-sided) on the paired per-question indicator "answered and wrong" over all complete-case questions, plus the Wilson intervals of wrong / answered per system (reported, `error_rate_answered`).
A lower indicator rate can come from answering less, so the coverage is reported beside it and (b) is the guard: **(b)** `engine2`'s answered share is not below the comparator's by more than 15 points **[proposed]** (one-sided paired bootstrap). H2 is supported for a dataset when (a) holds after Holm over the 6 McNemar tests and (b) holds.
(c) The confidence orders answers: `engine2`'s AURC is lower than the v1 `engine`'s (paired bootstrap 95% interval of the difference, questions resampled), and risk falls as the threshold rises: error rate among answered at confidence >= 0.8 is below that at >= 0.5 (reported with intervals; descriptive). Confidences of different systems are different kinds of signal (`PREREGISTRATION.md` section 5): AURC across systems is not a calibration comparison.

**H4: dates (`hoh`).** `engine2`'s correct share on `hoh` is **at least that of `agentic+asof`**: exact McNemar on the paired correctness indicators; H4 is not supported if `engine2` has fewer correct answers and the one-sided exact p-value for "fewer" is below 0.05 **[proposed]**. Counts, difference and bootstrap interval are reported;
how often each system gives the outdated value is reported (`kind` strata).

**H5: multi-hop (`musique`, `multihoprag`).** (a) `engine2`'s penalised score is **not below `agentic+asof`'s by more than 0.05** (one-sided paired bootstrap; non-inferior if the lower 95% bound of the difference exceeds -0.05) **[proposed]**; (b) it is above the v1 `engine`'s (two-sided paired sign-flip permutation test, Holm over the two datasets, difference with a bootstrap interval).

**H6: cost.** Cost per correct answer (`cost_per_correct`, with bootstrap intervals) of `engine2` is below the v1 `engine`'s; secondary: not above `agentic`'s. Paired bootstrap of the difference as in `PREREGISTRATION.md` section 4.3. **`engine2`'s cost includes the locked judge on `claude-sonnet-5-5`, which dominates it** (modelled about US$0.0098 per question, US$0.0075 of it the judge, against US$0.00121 for the v1 engine on `dev2`:
`docs/v2-test-plan.md`); H6 is **expected to fail** and is reported with that note. The cost is the ledger's, not the rows' (ledger tags `engine2`, `engine2-judge`).

**H7: calibration.** For each dataset with a certified threshold (a calibration file with `tau` not null), on `test` (a split not used for fitting) the error rate among `engine2`'s answered questions, by the containment label, is **at most alpha + 3 points = 8%**: supported when the observed rate is at most 0.08; the Clopper-Pearson upper bound at confidence 90% is reported. For a dataset without a certified threshold the engine ran on `default_tau`
and H7 is **not assessable** there; that is reported, not counted as failure. The statement is about the average, under exchangeability with the calibration split; it is not a statement about any one answer, and "wrong" means a failed containment grade, not a human judgement.

H1 and H3 (legal) are in `PREREGISTRATION-legal-v2.md`; H8 (the improvement loop) is not tested here.

## 5. Secondary outcomes (exploratory, two-sided, no correction)

Accuracy, coverage, selective accuracy, risk-coverage curves, abstention rate on unanswerable questions, cost per question, tokens, calls and searches, latency (wall-clock, concurrent workers), citation precision and recall against gold units, retrieval recall, the judge-assisted grade (`bench.judge`, Haiku, `--registered-run`), the engine's gate drops by type and judge verdicts from the `replay` payloads, and the share of `partial` answers.
Pareto table of cost against accuracy (`bench.report` Tables 3, 5b and 7).

## 6. Rules of the run

One run per dataset, all six systems in one session; nothing tuned after registration; a stopped run is not restarted with other settings; if the ledger stops a run only the complete cases are analysed and the number is printed; error rows count against the system. Run-to-run noise is 4-22% of outcomes and differences under about 0.1 at n = 300 are noise (measured, `docs/design-v2.md` (g)); at n = 500 paired, the detectable difference in
accuracy is about 0.05-0.07 (`PREREGISTRATION.md` section 4.4), so smaller differences are not claimed. Negative and null results are published. The deviations log below starts empty.

## 7. Frozen items and budget

| Item | Value | How obtained |
|---|---|---|
| Code commit | `<commit hash>` | `git rev-parse HEAD` at the tag |
| v1 locked hash | `<heuresis hash output: locked hash>` | `heuresis hash` |
| v1 surface hash / prompts hash | `<heuresis hash output>` / `<heuresis hash output>` | `heuresis hash` |
| v1 baseline prompts (hash of the constants) | `<prompts_hash at freeze>` | `heuresis hash` |
| v2 surface hash | `<v2 surface hash: heuresis hash output>` | `heuresis hash` / run manifest `v2_surface_hash` |
| Protected files hash | `<protected hash: heuresis hash output>` | `heuresis hash` / run manifest `protected_hash` |
| Locked judge model; policy | `claude-sonnet-5-5`; alpha 0.05, delta 0.10, `default_tau` 0.5 | `v2/locked/policy.json` |
| Calibration files | `<path, sha256 per dataset>` | `v2/calibration/` |
| Dataset manifests, `test` id hashes | section 2 | `MANIFEST.json` |
| Models and price table | `claude-haiku-5-5`; local models as `model_provenance`; `anthropic-2026-11` | run manifest |

**Budget (owner to approve):** modelled US$20.02 for stage E (1,500 questions x about US$0.01318 for six systems, plus about US$0.25 for the judge-assisted grade); suggested cumulative ledger cap **US$30.10**, margin 0.25, one new ledger (`docs/v2-test-plan.md` stage E). All figures are modelled; `engine2` has not been measured.

## Deviations log

| Date | Change | Reason | Data seen at the time |
|---|---|---|---|
| | (empty at registration) | | |
| 2026-11-13 | Judge `max_tokens` raised from 400 to 4096 (`JUDGE_MAX_TOKENS`; surface default and schema range follow); a judge reply that stops at `max_tokens` now counts as unreadable | The judge model thinks by default and its thinking tokens count against `max_tokens`, so a smoke call was truncated at 400 | None: made before any registered run |
