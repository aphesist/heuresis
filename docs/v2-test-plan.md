# v2 test plan: the paid commands, stage by stage

Companion to `docs/design-v2.md` section (g). It lists every command that touches a paid model, what it reads
and writes, and what it should cost. **Nothing here has been run.** Every cost below is **modelled**: measured
per-question costs of the earlier runs (file named for each figure) multiplied by question counts, with `engine2`
assumed at **about US$0.0098 per question**: generator about US$0.0023 (`docs/design-v2.md` section (c): 2.2 propose calls and 0.3 repair
calls on Haiku, no caching; that section's US$0.0027 minus its Haiku judge call) plus the locked judge on `claude-sonnet-5-5` (`v2/locked/policy.json`
`judge_model`; `pricing.py`: US$2 / US$10 per million input / output tokens) at about 3,000 input and 150 output tokens per judged question
(modelled) = US$0.0075. No `engine2` cost has been measured.

**With this judge the engine's cost per answer is dominated by the judge** (77% of the modelled US$0.0098): `engine2` costs about 4 to 8 times what the v1 `engine` cost
per question (US$0.00121 on the English `dev2` sets, US$0.00265 on the legal `test`). At the v1 useful rate on law (34%) that is about US$0.029 per useful answer against
US$0.0078 for v1 and US$0.0047 for `agentic` (`results/brlaw/heldout/RESULTS.md` section 4), so **H6 (cost per useful answer below v1's) is expected to fail on law unless the useful rate
rises a lot**; it is reported either way. Stage B has an optional dev-only ablation with the judge on `claude-haiku-5-5` (`--judge-model claude-haiku-5-5`, about US$0.0027 per question)
so the two costs can be compared. The registered runs use the policy's judge.

Rules that hold for every command:

- A paid command needs `--paid --cap USD --ledger PATH` and the key in `PROJECTS_ANTHROPIC_KEY` (or `--key-env NAME`);
  without `--paid` it is an offline dry run. Conventions of the earlier runs: `--thinking default --set draft.max_tokens=4096
  --margin-usd 0.25 --workers 4`.
- **The cap is cumulative per ledger file**: the ledger sums everything ever charged to the file and the run stops at
  `cap - margin`. This plan uses one ledger per stage (`ledger-B.jsonl`, ...) and gives, for each command, the
  cumulative cap (about 1.5 times the cumulative estimate) to pass at that point. The ledger tags `engine2` (generator), `engine2-judge` and `engine2-strong`.
- The engine2 judge defaults to the policy's model with thinking disabled; `--judge-model` overrides it and the manifest records the judge used and `judge_is_policy_model`.
  The v1 benchmark judges (`bench.citations`, `bench.judge`) stay on `claude-haiku-5-5`, unchanged, so the two registered legal runs are comparable.
- `--v2-cache` gives `engine2`'s generator a separate client with prompt caching (`AnthropicLLM(cache=True)`, same thinking setting).
  The estimates ignore its saving (design (c): at most 20-25% of propose cost), so they are conservative.
- The six systems of every comparison are `closed_book`, `hybrid`, `agentic`, `agentic+asof`, `engine`, `engine2`:
  `--systems closed_book,hybrid,agentic,engine,engine2 --time-aware-variants --variants-of agentic`. All six run in one
  session so the comparisons are paired. `agentic+asof` is built as an exploratory copy, so `bench.report` lists it in
  Table 6 (exploratory) and not in the confirmatory family; per-system tables show all six.
- **Held-out splits** (`test`, `sealed`, `temporal_test`; every `promo*`) are refused by `bench.run` unless
  `--registered-run FILE` is given and the file contains the sha256 of the split's ordered question ids
  (dry runs too); `promo*` is never readable from the CLI. The legal sets use **`PREREGISTRATION-legal-v2.md`**, the English `test` splits **`PREREGISTRATION-v2.md`**.
  Both are drafts: the owner freezes them, fills the hashes and tags the commit before stage E or F. `cal<k>` and `rot<c>` are not held out.
- Pool precedence for the unused questions of an English dataset (MultiHop-RAG about 1,550, HoH about 110,000; MuSiQue has none): promotion blocks (`promo0`, `promo1`, 300 each) first,
  then calibration blocks (`cal0`, 400), then rotating draws (`rot<c>`, 100 each). They are disjoint by construction and tested.
- Each paid `bench.run` writes `runs/v2/<stage>/<name>/{results.jsonl,manifest.json}`. The manifest records the
  surface hash, the protected hash, the judge and strong model ids and whether caching was on. Stores: copy the embedded
  store of the corpus to `<out>/store.sqlite` first (`cp data/db/<corpus>.db <out>/store.sqlite`, or
  `cp runs/stores/<dataset>/store.sqlite <out>/store.sqlite` for the English datasets, as in `scripts/dev2/run_all.sh`) so nothing is
  re-embedded.

Common prefix, used below (run from the repository root):

```
export PYTHONPATH=src
SYS="--systems closed_book,hybrid,agentic,engine,engine2 --time-aware-variants --variants-of agentic"
OPTS="--paid --margin-usd 0.25 --workers 4 --thinking default --set draft.max_tokens=4096 --v2-cache"
```

The stages: A offline; B dev comparison of the six systems; C calibration (`cal0` and a fresh `rot0`); D improvement loop; E registered English test; F registered legal re-run.

## Stage A: offline (free)

| Command | Reads | Produces |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` | fixtures only | the whole offline suite, including the as-of property tests, the protected-file manifest check and the held-out guard |
| `python -m heuresis.bench.run --dataset brlaw-core --split dev --limit 8 --systems closed_book,hybrid,agentic,engine,engine2 --time-aware-variants --variants-of agentic --out bench_out/a-law` | `dev` (dry run, fakes) | 8 questions x 6 systems of fake rows, `manifest.json` with the v2 fields; the fake judge reads nothing, so `engine2` abstains: it checks the plumbing, not the engine |
| `python -m heuresis.bench.run --dataset multihoprag --split cal0 --limit 8 --systems closed_book,engine,engine2 --out bench_out/a-rot` | `cal0` (dry run) | the calibration block resolves from the pool |
| `python -m heuresis.bench.run --dataset musique --split test --limit 8 --systems engine2 --registered-run PREREGISTRATION-v2.md --out bench_out/a-guard` | `test` | **must exit 2** while the draft holds placeholders instead of hashes (the guard) |
| `python -m heuresis.bench.report bench_out/a-law --reference engine2` | the dry run | `results.md` with the DRY RUN banner |

Cost: US$0. The held-out guard loads the split only to hash its question ids; nothing else of it is used or printed.

## Stage B: dev comparison of the six systems (paid)

Splits read: law `dev` (100) and `temporal` (120) of `brlaw-core`; English `dev2` (3 x 100). These were seen during v1 design, so every number here is
design-check data, not a result: a first look at H1-H6 and the runs the legal calibration attempt reuses. Ledger `runs/v2/ledger-B.jsonl`.

```
L=runs/v2/ledger-B.jsonl
# B1, B2: law (corpus brlaw-core; one store copy per run)
for S in dev temporal; do
  O=runs/v2/B/brlaw-core-$S; mkdir -p $O; cp data/db/brlaw-core.db $O/store.sqlite
  python -m heuresis.bench.run --dataset brlaw-core --split $S $SYS $OPTS --ledger $L --cap CAP --out $O   # CAP: see table
done
# B3: English dev2
for D in musique multihoprag hoh; do
  O=runs/v2/B/$D-dev2; mkdir -p $O; cp runs/stores/$D/store.sqlite $O/store.sqlite
  python -m heuresis.bench.run --dataset $D --split dev2 $SYS $OPTS --ledger $L --cap 11.30 --out $O
done
# B4: citation integrity and the support judge on the law runs (the full store checks existence and in-force)
for S in dev temporal; do
  python -m heuresis.bench.citations runs/v2/B/brlaw-core-$S --db data/db/brlaw.db --paid --cap 11.60 --margin-usd 0.25 --ledger $L
done
# B5: the secondary, judge-assisted grade (dev and dev2 only: bench.judge refuses every other split)
python -m heuresis.bench.judge runs/v2/B/brlaw-core-dev runs/v2/B/{musique,multihoprag,hoh}-dev2 --paid --cap 11.80 --margin-usd 0.25 --ledger $L --workers 4 --max-tokens 20
# B6: reports, `engine2` as the reference (free)
python -m heuresis.bench.report runs/v2/B/{musique,multihoprag,hoh}-dev2 --reference engine2 --family-out runs/v2/B/family-english.md
python -m heuresis.bench.report runs/v2/B/brlaw-core-dev runs/v2/B/brlaw-core-temporal --reference engine2 --family-out runs/v2/B/family-law.md
# the legal analysis of the preregistration (tainted, useful, H1, H3, H4, cost split, engine2 drops), as a design check on dev + temporal; English folders of the root are skipped (no citations.jsonl)
python scripts/brlaw/analyse_v2.py runs/v2/B runs/v2/B/analysis-law.json --db data/db/brlaw.db
# B7 (optional ablation, dev only): engine2 alone with the judge on Haiku, to compare cost and answers with the Sonnet judge
for D in musique multihoprag hoh; do
  O=runs/v2/B/$D-dev2-haikujudge; mkdir -p $O; cp runs/stores/$D/store.sqlite $O/store.sqlite
  python -m heuresis.bench.run --dataset $D --split dev2 --systems engine2 $OPTS --judge-model claude-haiku-5-5 --ledger $L --cap 13.40 --out $O
done
O=runs/v2/B/brlaw-core-dev-haikujudge; mkdir -p $O; cp data/db/brlaw-core.db $O/store.sqlite
python -m heuresis.bench.run --dataset brlaw-core --split dev --systems engine2 $OPTS --judge-model claude-haiku-5-5 --ledger $L --cap 13.40 --out $O
```

Produces: rows with `replay` payloads (confidence per answer, gates, verdicts, no passage text), `citations.jsonl` and the support judgements, `judge.jsonl`,
`results.md`/`results.json` per run. Reads H1 and H3 (first look, law), H2, H5, H6 (English), H4 (`temporal`).

| # | Command | Reads | Estimate (modelled) | `--cap`, cumulative on ledger B |
|---|---|---|---|---|
| B1 | `bench.run` law `dev`, six systems | `dev` (100) | US$1.80 | 2.70 |
| B2 | `bench.run` law `temporal` | `temporal` (120) | US$1.78 | 5.40 |
| B3 | `bench.run` English `dev2`, three datasets | `dev2` (3 x 100) | US$3.95 | 11.30 |
| B4 | `bench.citations --paid`, two runs | the B1/B2 rows | US$0.20 | 11.60 |
| B5 | `bench.judge --paid`, four folders | the B1/B3 rows | US$0.11 | 11.80 |
| B6 | `bench.report`, `scripts/brlaw/analyse_v2.py` | the folders | US$0 | |
| | **Stage B total** | | **US$7.84** | **11.80** |
| B7 | optional ablation, `engine2` with a Haiku judge, `dev` + `dev2` | 400 questions | US$1.08 | 13.40 |

Basis: law per-question costs of the five earlier systems on `dev` `0.00066 + 0.00099 + 0.00179 + 0.00201 + 0.00271 = 0.00816` (`results/brlaw/NOTES.md`, phase B and C tables) and on
`temporal` `0.00047 + 0.00042 + 0.00181 + 0.00124 + 0.00108 = 0.00502` (`PREREGISTRATION-legal.md` section 9, from `results/brlaw/phaseB/*/analysis.json` and `phaseC/analysis_c.json`), plus 0.0098
for `engine2`: US$0.01796 and 0.01482 per question. English per-question costs at default thinking, pooled over the three `dev2` sets (`results/dev2/NOTES.md`, phase B, condition `default`): `closed_book`
0.00023, `hybrid` 0.00035, `agentic` 0.00080, `agentic+asof` 0.00079, `engine` 0.00121 (sum 0.00338), plus 0.0098: US$0.01318 per question. B4: the support judge cost US$0.85 for 7,282 judgements on the
held-out run, US$0.000117 each (`results/brlaw/heldout/RESULTS.md` sections 2 and 6), about 1,300 judgements for the five earlier systems on `dev` and `temporal` (`results/brlaw/NOTES.md`), 20% more
with `engine2`. B5: US$0.000093 per answer judgement (US$0.21 for 2,262 rows, `RESULTS.md` section 4) and about US$0.056 per 1,000 for the English judge-assisted grade (about US$0.05 for 900 calls,
`results/dev2/NOTES.md`), about 1,200 rows. B7: 400 x US$0.0027 (the design's Haiku-judge figure).

## Stage C: calibration (paid, engine2 only, plus a free fit)

The confidence threshold `tau` is fitted by `bench.calibrate2` on labelled answers of a split that is not held out. It reads only `engine2` rows of non-held-out folders (`dev`, `dev2`, `temporal`, `cal<k>`, `rot<c>`),
walks the grid of `v2/locked/policy.json` from the strictest threshold to the loosest and writes `src/heuresis/v2/calibration/<dataset>-<surface hash[:12]>.json` and a `.table.md` beside it. The run
already applied `default_tau`; rows the engine held back for confidence carry their confidence and the sentences they would have given, so the containment label can go below the run's tau and the judge
label cannot (the table says which thresholds were evaluable). **A calibration file is valid only for the surface it was fitted on: after any surface change, fit again.** The files are committed at the freeze.

**Sizing (arithmetic; Clopper-Pearson upper bound at confidence 90%, target 5%).** The walk certifies a threshold when the bound on the error rate among answered questions is at most 5%. That needs
45 answered with 0 errors, 77 with 1, 132 with 3, about 306 with 10. A calibration block of 400 questions at about 70% coverage gives about 280 answered, which certifies if the error rate among answered is at most
about 3%. The legal sets are too small and, if the engine's useful rate stays near v1's, too error-prone: the 220 legal questions (`dev` 100 + `temporal` 120; labels from the model answer judge) will
**likely certify nothing**, and `temporal` has no equivalence label at all (its questions have no gold answer text and `bench.judge` refuses the split), so the legal attempt fits on `dev` alone (100 questions, at most about 85
answered). If nothing is certified, `tau` is null and the engine keeps `default_tau`; the plan says so rather than lowering the bar.

```
L=runs/v2/ledger-C.jsonl
# C1: calibration block cal0 (400 each), engine2 only, English datasets with a pool
for D in multihoprag hoh; do
  O=runs/v2/C/$D-cal0; mkdir -p $O; cp runs/stores/$D/store.sqlite $O/store.sqlite
  python -m heuresis.bench.run --dataset $D --split cal0 --systems engine2 $OPTS --ledger $L --cap 11.80 --out $O
done
# C2: fit (free). English: label = containment (deterministic; held-back rows graded against the gold answers).
for D in multihoprag hoh; do python -m heuresis.bench.calibrate2 runs/v2/C/$D-cal0 --label containment; done
# MuSiQue has no pool: its calibration file is fitted on dev2 from stage B (100 questions; expect nothing certified).
python -m heuresis.bench.calibrate2 runs/v2/B/musique-dev2 --label containment
# Legal attempt: the stage-B `dev` run, label = judge-equivalent (B5 wrote judge.jsonl); expect `tau` null.
python -m heuresis.bench.calibrate2 runs/v2/B/brlaw-core-dev --label judge
# C3: unseen check of the fitted tau (H7), a fresh rotating draw rot0, engine2 only, with the file from C2
for D in multihoprag hoh; do
  O=runs/v2/C/$D-rot0; mkdir -p $O; cp runs/stores/$D/store.sqlite $O/store.sqlite
  C=$(ls src/heuresis/v2/calibration/$D-*.json 2>/dev/null | head -1); CAL=${C:+--v2-calibration $C}   # no file: the engine keeps default_tau
  python -m heuresis.bench.run --dataset $D --split rot0 --systems engine2 $OPTS --ledger $L --cap 14.70 $CAL --out $O
done
python -m heuresis.bench.report runs/v2/C/{multihoprag,hoh}-rot0 --reference engine2 --family-out runs/v2/C/family.md
```

Produces: the calibration files and tables; the first look at H7 on questions neither used for fitting nor seen by anyone (`rot0`: the next draw is `rot1`; do not rerun `rot0` as if it were fresh after a surface change).
There is no judge-assisted grade on `cal<k>` / `rot<c>` (`bench.judge` reads `dev` and `dev2` only).

| # | Command | Reads | Estimate (modelled) | `--cap`, cumulative on ledger C |
|---|---|---|---|---|
| C1 | `bench.run` `cal0`, two datasets, `engine2` only | `cal0` (2 x 400) | US$7.84 | 11.80 |
| C2 | `bench.calibrate2` x 4 | the folders | US$0 | |
| C3 | `bench.run` `rot0`, two datasets, `engine2` only | `rot0` (2 x 100) | US$1.96 | 14.70 |
| | **Stage C total** | | **US$9.80** | **14.70** |

Basis: 1,000 questions x US$0.0098. The legal attempt reuses the stage-B runs and costs nothing more.

## Stage D: improvement loop (paid, one or two cycles)

The loop (`docs/evolve.md`) evolves only the champion surface and reads only non-held-out data: rotating draws (`rot0`, `rot1`, ...) and the sealed promotion blocks of `multihoprag` and `hoh`, plus the anchors `musique` (`dev`, `dev2`)
and `brlaw-core` (`dev`, `temporal`). Each cycle is hard-capped by the loop's ledger at **US$10** (`--cap 10` is per cycle: the cap of a cycle is what the ledger had already spent plus 10; the loop stops cleanly at it and the next call
resumes the same cycle). `docs/evolve.md` models a cycle at about US$9.7 (Sonnet judge included), so one or two cycles are **US$10 to US$20 at most**. Ledger `runs/v2/ledger-D.jsonl`, workdir `evolve_runs/` (git-ignored). The flags are the ones
`heuresis evolve cycle --help` lists: `--paid --cap USD --ledger PATH --model NAME --dataset NAME (repeatable) [--judge-model NAME] [--key-env NAME] [--data-root DIR] [--k N] [--seed N] [--workdir DIR] [--allow-unpinned] [--json]`;
`--paid` needs `--cap`, `--ledger`, `--model` and at least one `--dataset`, and the key is read from `PROJECTS_ANTHROPIC_KEY` unless `--key-env` names another variable.

```
export PYTHONPATH=src
python -m heuresis.cli lock --check                       # exit 2 if a protected file differs from PROTECTED.json (the freeze writes it with `heuresis lock`)
python -m heuresis.cli evolve describe --workdir evolve_runs --json | head -c 600   # schema, champion, protected hash (no model call)
# stores: copy the embedded ones so nothing is re-embedded (the runner builds <workdir>/stores/<dataset>.sqlite when missing)
mkdir -p evolve_runs/stores
for D in multihoprag hoh musique; do cp runs/stores/$D/store.sqlite evolve_runs/stores/$D.sqlite; done
cp data/db/brlaw-core.db evolve_runs/stores/brlaw-core.sqlite
L=runs/v2/ledger-D.jsonl
# D1: cycle 1 (draws rot0), cap US$10
python -m heuresis.cli evolve cycle --paid --cap 10 --ledger $L --model claude-haiku-5-5 --dataset multihoprag --dataset hoh --data-root data --workdir evolve_runs --json
# D2 (optional): cycle 2 (draws rot1), another US$10 on the same ledger
python -m heuresis.cli evolve cycle --paid --cap 10 --ledger $L --model claude-haiku-5-5 --dataset multihoprag --dataset hoh --data-root data --workdir evolve_runs --json
python -m heuresis.cli evolve status --workdir evolve_runs --json
# if a promoted champion looks wrong on inspection:
# python -m heuresis.cli evolve rollback --workdir evolve_runs --reason "manual check failed"
```

| # | Command | Reads | Estimate (modelled) | `--cap` per call |
|---|---|---|---|---|
| D1 | `heuresis evolve cycle --paid`, `multihoprag` + `hoh` | `rot0`, `promo0` (the sealed block, never printed), the anchors | about US$9.7 (`docs/evolve.md`) | 10 |
| D2 | the same, second cycle (optional) | `rot1`, the same promotion block (2nd of 10 queries) | about US$9.7 | 10 |
| | **Stage D total** | | **US$9.7 to US$19.4** | **at most US$10 per call, US$20 on the ledger** |

Notes. (1) The loop's first cycle draws `rot0`, which stage C3 also reads: run C3 first and treat `rot0` as seen afterwards. (2) A promoted champion has to be re-calibrated (stage C) before it is registered; the loop does this only if budget
is left. (3) The paid flags above are the only ones the CLI accepts: `heuresis evolve cycle` has no `--limit`, `--split` or `--systems` (the cycle's draws, promotion blocks and anchors come from `evolve/config.json`).

## Stage E: registered English test (paid)

Splits read: `test` of `musique`, `multihoprag`, `hoh` (3 x 500). **Held out: every command needs `--registered-run PREREGISTRATION-v2.md`, the registration frozen and committed first** (hashes of the three `test` splits filled in,
surface hash and protected hash of the commit to be run, calibration files committed). These splits have never been answered by any model. Ledger `runs/v2/ledger-E.jsonl`. Nothing is tuned after registration; one run.

```
L=runs/v2/ledger-E.jsonl; R=PREREGISTRATION-v2.md
for D in musique multihoprag hoh; do
  O=runs/v2/E/$D-test; mkdir -p $O; cp runs/stores/$D/store.sqlite $O/store.sqlite
  C=$(ls src/heuresis/v2/calibration/$D-*.json 2>/dev/null | head -1); CAL=${C:+--v2-calibration $C}   # no file: the engine keeps default_tau
  python -m heuresis.bench.run --dataset $D --split test $SYS $OPTS --ledger $L --cap 29.70 --registered-run $R $CAL --out $O
done
# secondary, judge-assisted grade, as in the first registration (held-out split: the registered-run flag again)
python -m heuresis.bench.judge runs/v2/E/{musique,multihoprag,hoh}-test --paid --cap 30.10 --margin-usd 0.25 --ledger $L --workers 4 --max-tokens 20 --registered-run $R
python -m heuresis.bench.report runs/v2/E/{hoh,multihoprag,musique}-test --reference engine2 --family-out runs/v2/E/family.md
```

Produces: H2 (error rate among answered, risk-coverage and AURC), H4 (HoH), H5 (penalised score), H6 (cost per correct answer; note the judge dominates it), H7 (calibration on a split not used for fitting), with the complete-case rule and Holm across the family of the report.

| # | Command | Reads | Estimate (modelled) | `--cap`, cumulative on ledger E |
|---|---|---|---|---|
| E1 | `bench.run` `test`, three datasets, six systems | `test` (3 x 500) | US$19.77 | 29.70 |
| E2 | `bench.judge --registered-run` (secondary) | the E1 rows | US$0.25 | 30.10 |
| E3 | `bench.report` | the folders | US$0 | |
| | **Stage E total** | | **US$20.02** | **30.10** |

Basis: 1,500 questions x US$0.01318; judge about 4,500 judged rows x US$0.000056 (`results/dev2/NOTES.md`). For reference, `PREREGISTRATION.md` section 9 capped the English run at US$30 for eight systems.

## Stage F: registered legal re-run (paid)

Splits read: BR-TaxQA-R `test` (615) and `temporal_test` (240) of `brlaw-core-t`: a **second registered comparison on the same questions**, all six systems re-run together (design section (g)), registered in
**`PREREGISTRATION-legal-v2.md`**. Both commands need `--registered-run PREREGISTRATION-legal-v2.md`. Ledger `runs/v2/ledger-F.jsonl`. Prerequisites that exist from the first run: the corpus `data/corpora/brlaw-core-t`, its embedded
store `data/db/brlaw-core-t.db`, and the full corpus `brlaw-t` ingested without embeddings as `data/db/brlaw-t.db` for the existence and in-force checks (store paths inferred from `scripts/brlaw/check_recall.py` and
`results/brlaw/NOTES.md`; adjust to where the first run kept them). The full store is built, if missing, with the ingest half of `scripts/brlaw/embed.py`:

```
python -c "from heuresis.store import Store; from heuresis.ingest import ingest; from heuresis.domains import get_domain; s=Store('data/db/brlaw-t.db'); print(ingest(s,'data/corpora/brlaw-t',get_domain('legal_br')))"
```

```
L=runs/v2/ledger-F.jsonl; R=PREREGISTRATION-legal-v2.md
for S in test temporal_test; do
  O=runs/v2/F/brlaw-core-t-$S; mkdir -p $O; cp data/db/brlaw-core-t.db $O/store.sqlite
  python -m heuresis.bench.run --dataset brlaw-core-t --split $S $SYS $OPTS --ledger $L --cap CAP --registered-run $R --out $O   # CAP: see table
done
# citation integrity (tainted answers, version in force) and the support judge (v1 judge, Haiku, unchanged)
for S in test temporal_test; do
  python -m heuresis.bench.citations runs/v2/F/brlaw-core-t-$S --db data/db/brlaw-t.db --paid --cap 23.70 --margin-usd 0.25 --ledger $L --sample 20
done
# the answer judge (useful answers), test only, as in the first registration
python -m heuresis.bench.judge runs/v2/F/brlaw-core-t-test --paid --cap 24.10 --margin-usd 0.25 --ledger $L --workers 4 --max-tokens 20 --registered-run $R
# analysis (free): six systems, reference engine2; --db is the full store of the citation check and scores H4 per question
python scripts/brlaw/analyse_v2.py runs/v2/F runs/v2/F/analysis.json --db data/db/brlaw-t.db
# then the model review of the support judge, as logged in PREREGISTRATION-legal.md
```

`scripts/brlaw/analyse_v2.py` is the analysis of this registration: the six systems `closed_book, hybrid, agentic, agentic+asof, engine, engine2`, reference `engine2`, on any folder layout `bench.run` + `bench.citations` + `bench.judge` leave (it finds the run folders under
`runs/v2/F` by their manifests' `split`). It computes tainted answers (strict and covered-only; exact McNemar and Holm over the 8 + 2 tests of `PREREGISTRATION-legal-v2.md` section 4), useful answers with paired bootstrap differences,
the H1 check (non-inferiority to `agentic` at -3 points, superiority over `engine`), the H3 non-inferiority check against v1 (margin 1 point), H4 on `temporal_test` (paired with `--db`), cost per question and per useful answer split into generator and judge, coverage, and `engine2`'s gate and judge drops by
reason from the rows' `replay` payloads. `scripts/brlaw/analyse_heldout.py` (the first registration's analysis, five systems, reference `engine`) is not changed and not used here. `scripts/brlaw/agreement.py` joins the blind reviewer's labels with the support judge's verdicts.
Reads H1 (useful answers), H3 (tainted answers, non-inferiority within 1 point of v1), H4 (`temporal_test`: version in force), H6, with Holm over the family. On `temporal_test` the primary outcome sat at the floor in
the first run (baselines 0.4-2.1% tainted), so it can show H3 non-inferiority and H4 only.

| # | Command | Reads | Estimate (modelled) | `--cap`, cumulative on ledger F |
|---|---|---|---|---|
| F1 | `bench.run` `test`, six systems | `test` (615) | US$10.95 | 16.45 |
| F2 | `bench.run` `temporal_test`, six systems | `temporal_test` (240) | US$3.83 | 22.20 |
| F3 | `bench.citations --paid`, support judge | the F1/F2 rows | US$1.02 | 23.70 |
| F4 | `bench.judge --registered-run`, answer judge | the F1 rows | US$0.25 | 24.10 |
| F5 | `scripts/brlaw/analyse_v2.py` | the folders | US$0 | |
| | **Stage F total** | | **US$16.05** | **24.10** |

Basis: held-out per-question costs at default thinking, US$/question (`results/brlaw/heldout/RESULTS.md` section 5): on `test` `closed_book` 0.00065, `hybrid` 0.00103, `agentic` 0.0018, `agentic+asof` 0.00188,
`engine` 0.00265, sum 0.00801, plus 0.0098 = US$0.01781 x 615; on `temporal_test` 0.0005 + 0.0004 + 0.00238 + 0.00164 + 0.00123 = 0.00615, plus 0.0098 = US$0.01595 x 240. F3: the first run's support judge cost US$0.85
(6,019 + 1,263 judgements), 20% more for the sixth system. F4: the first run's answer judge cost US$0.21 (2,262 rows), 20% more. For comparison, the whole first held-out run cost US$7.47 of a US$10 cap (`RESULTS.md`
section 2), against a modelled US$7.1.

## Totals

| Stage | Ledger | Estimate (modelled) | Highest cumulative `--cap` |
|---|---|---|---|
| A offline | none | US$0 | |
| B dev comparison, six systems (+ optional ablation US$1.08) | `ledger-B.jsonl` | US$7.84 | 11.80 (13.40) |
| C calibration (`cal0`, fit, `rot0`) | `ledger-C.jsonl` | US$9.80 | 14.70 |
| D improvement loop, 1-2 cycles | the loop's own | US$10-20 (cap US$10 per cycle) | 20 |
| E registered English test | `ledger-E.jsonl` | US$20.02 | 30.10 |
| F registered legal re-run | `ledger-F.jsonl` | US$16.05 | 24.10 |
| **Total (A-C, E, F)** | | **US$53.71** | **80.70** |
| **Total with two loop cycles** | | **US$73.71** | **100.70** |

Order and gates: A must pass before anything else. B before C (the legal calibration attempt reuses B; the unseen check uses C's files). The go / no-go is the owner's, made before the registrations are frozen; **after the freeze
nothing is changed and E and F are run once**, each in one session with every system in the same session. A ledger stop ends a run cleanly and a restart resumes it (complete cases are analysed); a failed run is not restarted
with other settings. Every figure in the cost tables is a model, to be replaced by the first measured `engine2` cost per question from stage B; the Sonnet judge is the term to watch.
