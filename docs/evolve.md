# The improvement loop (`heuresis evolve`)

The loop changes the v2 engine in one way only: it replaces the **champion surface**
(`src/heuresis/v2/surface/`: config values and four prompts, data only). It never runs inside an
answer. The reasons, the statistics and the benchmark tiers are in `docs/design-v2.md` section
(f); the signatures are in `docs/v2-contracts.md` section 9. This file says how to run it.

Nothing here has been run with a paid model. Every cost figure is **modelled**.

## Quick start, offline and free

```
heuresis lock                                   # once, after reviewing protected files: writes PROTECTED.json
heuresis evolve cycle --workdir evolve_runs --offline
heuresis evolve status --workdir evolve_runs --json
```

`--offline` runs the real `EngineV2` with deterministic fakes (`heuresis.evolve.evaluator.FixtureLLM`,
the hash embedder) on a packaged, invented corpus and question pool
(`src/heuresis/evolve/fixture/`). It proves the machinery, it measures nothing about real
questions. Before `heuresis lock` has been run (a build in progress) add `--allow-unpinned`; the
evaluator otherwise refuses to run because `PROTECTED.json` is missing or differs.

## Commands

All take `--json` and `--workdir DIR` (default `evolve_runs/`, git-ignored).

| command | what it does |
|---|---|
| `heuresis evolve describe` | schema with bounds, champion, protected hash, stages, budget, datasets |
| `heuresis evolve evaluate --candidate FILE \| --candidate-dir DIR --stage S [--nonce N]` | one stage on one candidate; `S` is `static`, `smoke`, `screen`, `dev` or `promote` |
| `heuresis evolve promote ID` | promotion test on an archived candidate; makes it champion if it passes |
| `heuresis evolve rollback [--to ID] [--reason TEXT]` | restore the previous champion (or one from the history) |
| `heuresis evolve status` | champion, counters, promotion blocks in use, spend |
| `heuresis evolve cycle [--k N] [--seed N] (--offline \| --paid ...)` | one whole cycle |
| `heuresis evolve lock-check` | exit 2 listing every protected file that differs from `PROTECTED.json` |
| `heuresis lock [--check]` | write `PROTECTED.json` and print the protected hash; `--check` exits 2 on a difference |
| `heuresis ask DB QUESTION --engine v2 [--model M --budget USD --judge-model J]` | answer with the v2 engine (default `--engine v1`) |

Paid flags (any of `evaluate`, `promote`, `cycle`): `--paid --cap USD --ledger PATH --model NAME
--dataset NAME ... [--judge-model NAME] [--key-env VAR] [--data-root data]`. As in `bench.run`
only the **name** of the key variable is ever read or printed, `--paid` needs `--cap` and
`--ledger`, and the ledger is shared by every run so two runs cannot each believe they have the
whole cap. The per-cycle cap is `spent so far + --cap`; the loop stops cleanly when it is reached.

Programmatic use is the same: `heuresis.evolve.api.evaluate(candidate, stage=..., workdir=...,
context=EvalContext(...))`; passing a context with real clients is the only way a paid run starts.

### Example shell session

```
$ heuresis evolve describe --json | jq .champion
$ heuresis evolve evaluate --candidate-dir my_surface/ --stage static --json
$ heuresis evolve cycle --workdir evolve_runs --offline --json | jq '{cycle, status, promoted}'
$ heuresis evolve status --workdir evolve_runs
$ heuresis evolve rollback --workdir evolve_runs --reason "manual check failed"
```

### Example crontab line (paid, one cycle a night, hard cap US$10)

```
17 3 * * *  cd /srv/heuresis && heuresis evolve cycle --paid --cap 10 --ledger /srv/heuresis/ledger.jsonl --model claude-haiku-5-5 --dataset multihoprag --dataset hoh --workdir /srv/heuresis/evolve_runs >> evolve.log 2>&1
```

(The key variable must be set in the cron environment; its name is `PROJECTS_ANTHROPIC_KEY` unless
`--key-env` says otherwise.) A cycle that hits the cap ends as `stopped_budget`; the next run
resumes the same cycle from the archive.

## Datasets and stores

Names are those `bench.datasets.load` accepts. Rotating and promotion draws: `multihoprag`, `hoh` (they
have pools). Anchors (`config.json`, `anchors`): `musique` splits `dev` and `dev2`; **`brlaw-core`** splits `dev`
and `temporal` (loaded by `bench.brlaw.load` from `data/corpora/brlaw-core`; the name `brlaw` would load the
other, full corpus, which has no such comparison). Each dataset's store is built by the runner at
`<workdir>/stores/<dataset>.sqlite` from the corpus folder, embedding with the local model, unless the file
exists: to avoid re-embedding copy the stores of the benchmark first (`cp data/db/brlaw-core.db
<workdir>/stores/brlaw-core.sqlite`, `cp runs/stores/<dataset>/store.sqlite <workdir>/stores/<dataset>.sqlite`).

## Files in the workdir

| file | content |
|---|---|
| `archive.jsonl` | append-only events (candidate, stage, status, score, admitted); `Archive.rows()` folds them into one row per candidate: id, parent, candidate overrides, surface hash, stage results, status, judge model |
| `champion.json` | current champion (id, surface hash, overrides, why) and `history` used by rollback, plus the rollbacks made |
| `state.json` | cycle number, open cycle, promotion tests and promotions so far, promotion block in use per dataset and its queries, memoised promotion results |
| `ledger.jsonl` | the spend ledger (same format as the benchmark's) |
| `cycles/NNNN.json` | one file per cycle: proposals, tripwires, rollback, calibration note, status |
| `cache/<surface hash>.<tier>.json` | rows per (surface, tier, question). Tiers `rotating`, `canary`, `smoke` keep answers; `anchor`, `promotion` and `calibration` rows are stored **without text** |
| `calibration/` | calibration file fitted for a new champion (when the budget allowed) |
| `gold_answers.json` | the **decoy**: only the canaries' fake answers, mode 0444 |
| `stores/` | the ingested corpora of paid runs |

All JSON is written atomically. Candidate ids are the sha256 of the canonical JSON of the
normalised overrides, always relative to the packaged default surface; a directory that mirrors
`v2/surface/` and equals the champion's surface gives the champion's id.

## What the proposer sees, and never sees

Sees: `describe()` (schema, bounds, current values), the parent's four prompts, and
`reflective_dataset(candidate_id, workdir=...)`: for failures on the **rotating dev** draws, the
question, the engine's answer, the typed outcome, the abstention type, and gate and judge
reasons. Parent selection is fixed code in `archive.py` (weight `sigmoid(10 (score - 0.5)) / (1 +
children)` over admitted candidates, seeded RNG); a proposer cannot change it.

Never sees: gold answers or gold units; anything from the promotion blocks, the anchors or the
calibration block (stored without text; the reflective dataset reads only the rotating tier);
canaries; the decoy's contents are not shown either. The promotion stage returns pass or fail and
the decision statistics, never a row. This is enforced by what the functions return, and tested
by scanning reports for the fixture's gold strings.

Proposers: `PerturbProposer(seed)` changes one to three schema values inside their bounds and
never produces an invalid candidate; `ReflectiveProposer(llm)` asks a model for a JSON candidate
(parsed defensively, invalid output gives no candidate) and is never called unless an LLM is
injected.

## One cycle

1. Protected-tree check (a difference stops the cycle). Re-check the champion on the new rotating
   draw against the previous champion (for `recheck_window_cycles` = 3 cycles after a promotion);
   a score more than 2 standard errors lower, or a tripwire, restores the previous champion.
2. Select a parent, propose K candidates (default 4).
3. **static** (free): schema, bounds, path guard (`manifest.check_candidate_paths`), protected hash,
   prompt lint (forbidden strings, canary marker, 8-word overlap with any evaluation question).
4. **smoke** (free): the fixture through the engine with fakes; must run and trip nothing.
5. **screen**: `screen_n` questions per dataset of the draw, plus canaries, paired with the
   champion. Out only if clearly worse (below zero by more than 2 standard errors).
6. **dev**: the top candidate(s) (`dev_top`, default 1) on the whole draw: positive paired
   difference, one-sided 90% bootstrap lower bound above zero, guard rails of the dev rows.
7. **promote**: at most one candidate per cycle, on the sealed promotion block plus the anchors,
   paired with the champion; one-sided paired sign-flip test at the level
   `alpha_t = alpha * gamma_t * (promotions so far + 1)`, `gamma_t = 6 / (pi^2 t^2)` (sums to 1, so
   with no promotion the levels sum to at most alpha = 0.05; `t` counts every promotion test ever
   made). The promotion block is retired after 10 promotion queries and the next reserved block is used (2 per dataset, so 20 queries at most; see Stated limits).
8. A promoted candidate becomes champion; the loop then runs it on the calibration block **only if
   budget remains** and fits the locked risk-controlled threshold, otherwise the cycle record says
   the champion is uncalibrated. Everything else stays in the archive as a possible parent.

Guard rails (against the champion): no tainted citation on any anchor answer;
error rate among answered not more than 2 points higher; coverage not more than 5 points lower; cost per question
not more than 25% higher; no **graded** anchor group lower by more than 2 standard errors.
**Legal anchors are not graded by containment** (BR-TaxQA-R answers are paragraphs, so the containment grade
means nothing there): their rows carry `graded: false` and the penalised score is never applied to them (the
`anchor_score` rail ignores them). A separate rail, `anchor_ungraded`, uses only what code can score on
those groups: coverage (not more than 5 points lower), cost (not more than 25% higher) and, on the dated
`temporal` questions, the share of answers that gave the version in force (`bench.citations.temporal_outcome`
= `gold_version`; not more than `version_points` = 5 points lower; needs at least `min_pairs` dated pairs).
Tainted citations are rail 1 for every anchor. The version score needs the corpus store of the run to hold the
versions of the cited units (the packaged law store does); if it cannot be computed the row has no `temporal`
value and that part of the rail is skipped.
Winner's curse:
only the promotion-set difference is recorded as a candidate's gain.

## Tripwires (`evolve/tripwires.py`)

| name | trips when | default severity |
|---|---|---|
| `protected_file_changed` | a protected file differs from the manifest | stop cycle |
| `invalid_surface` | not a valid surface (schema, bounds, path guard, lint) | stop cycle |
| `canary_marker` | the canary marker is in a prompt or any answer | stop cycle |
| `canary_answered` | more than 10% of canary questions are answered | stop cycle |
| `tainted_anchor` | a fabricated or out-of-force citation on an anchor answer | stop candidate |
| `implausible_jump` | dev gain above 4 standard errors | flag |
| `dev_promotion_gap` | dev gain exceeds promotion gain by more than 3 standard errors | flag |
| `cost_doubled` | cost per question above twice the champion's | stop candidate |

Severities are overridable in `config.json`. A planted bad batch is recorded in the archive (each
candidate `rejected_static`) and ends the cycle before any paid stage. Canaries and decoys catch
crude leaks only; no detection rate is claimed.

## Budget per cycle (modelled)

Prices (`src/heuresis/pricing.py`): the generator (Haiku 5.5) US$0.10 / 0.50 per million input /
output tokens; the locked judge, now fixed to `v2/locked/policy.json` `judge_model`
(`claude-sonnet-5-5`, thinking disabled) US$2 / 10. A judge call modelled at about 3,000 input
and 150 output tokens is about US$0.0075, so the engine costs about **US$0.010 per question** in
the loop (modelled; `design-v2.md` (f) quoted US$0.003 before the judge was fixed to Sonnet). At
the default US$10 cap a cycle affords about 1,000 questions. Defaults are sized to fit
(`config.json`): rotating draw 2 x 50, screen 4 candidates x 2 x 20 plus 6 canaries each, dev 1
candidate on the whole draw, anchors 15 per group and promotion only for the one candidate that
reaches it.

| line | questions | US$ (modelled) |
|---|---|---|
| champion on the draw (cached after) | 100 | 1.0 |
| screen, 4 candidates | 4 x (40 + 6) | 1.8 |
| dev, 1 candidate (screen rows reused) | about 60 new | 0.6 |
| anchors, candidate and champion | 2 x 60 | 1.2 |
| promotion, candidate and champion, `n` per dataset | 2 x 2 x n | 0.04 n |
| **total with n = 127** (what remains under the cap less the US$0.25 margin) | | about 9.7 |
| re-check of the previous champion (3 cycles after a promotion) | 100 | 1.0 (not in the total) |
| calibration block after a promotion | 100 | 1.0 (usually no budget left: recorded as uncalibrated) |

The promotion test size is **reduced to what the remaining budget allows and never below 200
questions in total** (`promotion_min_n`); below that the test is not run and the candidate is
archived with the reason. At 2 x 127 = 254 pairs the smallest paired difference in a proportion
that `bench.stats.min_detectable_diff` (alpha 0.05, power 0.8, normal approximation to McNemar)
can detect is about 0.055 / 0.078 / 0.096 at a discordance rate of 10% / 20% / 30%; at 200 pairs
0.062 / 0.088 / 0.108. The level of the first promotion test is 0.030 and falls with t, so the
real detectable effect is somewhat larger. Run-to-run noise (4-22% of outcomes in earlier runs) is
larger than these figures: a promotion here is evidence, not proof.

## Driving it from autopoiesis or a cron job

| autopoiesis concept | heuresis |
|---|---|
| agent directory a diff is applied to | a copy of `src/heuresis/v2/surface/`; `evaluate --candidate-dir DIR` reads only `default.json` and `prompts/<name>.txt`; a `.py` file, a path outside the surface or a symlink leaving the directory is a static failure |
| selection evaluator | `evaluate --stage screen` / `--stage dev` |
| clean evaluator, never fed back | `evaluate --stage promote`: pass or fail and statistics only |
| host-side tripwires | `evolve/tripwires.py`, protected by the manifest; the decoy `gold_answers.json` |
| mutator prompt | `describe --json` and `reflective_dataset` |
| budget ledger | the same append-only ledger, one file per workdir |
| nonce-tagged report line | `--nonce N`: stdout is exactly one line `HEURESIS-EVAL N <compact json>`; stderr carries any notice; on an error the line still appears with `passed: false` and an `error` field and the exit code is 2 |

`evaluate` is stateless apart from the row caches, the ledger and (for `promote`) the promotion
counters. `heuresis evolve cycle` with the built-in proposers is the minimal loop, so a cron line
is enough.

## Stated limits

* **This is not a sandbox.** The guarantee is that a candidate that reaches evaluation is a valid
  surface and nothing else. A process with write access to the repository can edit protected
  files (the evolve package is itself protected); the manifest turns that into a refused run, not
  an impossible one. The decoy file lives in the workdir, which a proposer process could read.
  Isolation (container, no network) belongs to the outer harness.
* Not closed: a prompt that makes the generator write answers the judge likes without being right
  (the gates bound it: no invented source; the judge prompt is locked; the lint removes the
  obvious routes; only a human-labelled sample really tests it); slow overfitting to the kind of
  question in the pools (rotating draws reduce it); judge and labels wrong in the same direction
  as the generator; same-family judge errors.
* The loop evolves only on datasets with pools (MultiHop-RAG, HoH); the legal corpora have none and
  appear only as anchors. Anchors are sampled (`anchor_n` per group) at this budget.
* Promotion queries are limited. `bench.splits.PROMO_RESERVED` = 2 blocks of `PROMO_N` = 300 ids
  are reserved per dataset and `config.json` assumes the same (`promotion_blocks` 2,
  `promotion_query_budget` 10 queries per block, `promotion_n` 150 of a block's 300 ids). A dataset
  therefore supports **2 x 10 = 20 promotion queries**, each `heuresis evolve promote` (or the
  promotion stage of a cycle) using one on every dataset of the run; the 21st reports "no
  promotion block left" and nothing is promoted. A cycle makes at most one promotion test, so
  the loop can promote at most 20 times per pool. Rotating draws are limited by the pool as well:
  `bench.splits` takes the 600 promotion ids and the 400 calibration ids (`CAL_N`, `CAL_RESERVED` = 1)
  out first and cuts draws of 100 from the rest (the loop uses the first 50 of a draw). With the
  pool sizes quoted in `docs/design-v2.md` (MultiHop-RAG about 1,550, HoH about 110,000;
  **modelled from those counts, not read from the data**) MultiHop-RAG leaves about 550 ids, that
  is 5 cycles (`rot0` to `rot4`), after which `cycle` stops with `SplitExhausted`; HoH is not a limit.
  `BenchSplits.capacity(name, budget)` reports the figures for a real pool without printing a question.
  Stage C3 of `docs/v2-test-plan.md` also reads `rot0`, which the loop's first cycle draws too.
* The cap is checked before each chunk of 25 questions, so a stop can overshoot by about one chunk.
* Per-cycle cost is modelled from a US$0.010 per question estimate; the ledger records what was
  actually charged.
* Rollback re-checks only for 3 cycles after a promotion (design: every draw), to bound its cost.
