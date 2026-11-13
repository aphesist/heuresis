# Command line

`heuresis` (entry point `heuresis.cli:main`; also `python -m heuresis.cli`). Every command takes
`--json` to print JSON instead of text. Exit codes: 0 success, 2 refused or invalid input (message
on stderr), 1 unexpected failure (one line, no traceback).

| Command | Purpose |
|---|---|
| `init DB [--domain NAME]` | create an empty database; the domain is remembered |
| `ingest DB PATH [--domain NAME]` | read a path with a domain plug-in into the store (default domain: the database's, else `text`) |
| `index DB [--local]` | embed versions that have no vector yet; `--local` loads the ONNX models from `heuresis.models_local` |
| `ask DB QUESTION [--as-of DATE] [--recorded TS] [--source ID ...] [--budget USD] [--local] [--model MODEL] [--trace] [--engine v1\|v2] [--judge-model MODEL]` | verified answer or typed abstention; `--engine v2` runs `EngineV2` |
| `search DB QUESTION [--as-of DATE] [-k N]` | passages in force at the date, no drafting |
| `unit DB UNIT_ID [--as-of DATE]` | one unit as it read at the date, with its validity interval |
| `verify DB --text TEXT --unit UNIT_ID ... [--as-of DATE]` | verify a text against the named units in force at the date |
| `hash` | the locked-folder hash, the surface hash and the baseline prompts hash, exactly as a benchmark run manifest records them |
| `lock [--check]` | write `src/heuresis/v2/locked/PROTECTED.json` (sha256 of every protected file) and print the protected hash; `--check` exits 2 listing the differences instead of writing |
| `evolve describe\|evaluate\|promote\|rollback\|status\|cycle\|lock-check ...` | the improvement loop over the v2 engine; see below and `docs/evolve.md` |
| `bench run\|report [--dry-run] [--paid --cap USD] ...` | delegate to `heuresis.bench`, imported lazily |

Dates are `YYYY-MM-DD`; `--recorded` is an ISO date or timestamp (only what the corpus knew by then).

## ask

By default `ask` runs fully offline with the built-in fakes (a notice goes to stderr) and costs
nothing. `--model MODEL` uses `heuresis.llm.AnthropicLLM`, which reads its key from the environment
variable `PROJECTS_ANTHROPIC_KEY` (the CLI never reads or prints it) and **requires `--budget USD`**:
the run is refused without it. `--budget` without `--model` is refused too. The cap is enforced by a
budget wrapper around the model and also passed to the engine.

The text output shows: status; the answer text; each claim with its label and citations as
`unit_id @ valid_from..valid_to` (open ends are empty); the grade; for abstentions the type, the
message and what was searched; the total cost and time. `--trace` adds the stage table
(stage, ms, tokens in/out, usd, note). With `--json` the full structure is printed, trace included.

```
$ heuresis ask corpus.db "Qual o texto do art. 2º?" --as-of 2021-01-01
status: answered
...
  [supported] Art.  (support 0.95)
      urn:lex:br:federal:lei:2020-03-10;1!art2 @ 2020-03-10..2022-06-01
grade: 0.95
cost: $0.0000   time: 1.6 ms
```

## ask --engine v2

`--engine v2` answers with `EngineV2` (`src/heuresis/v2/`; default `--engine v1`). Offline it uses the same fakes
and so mostly abstains: it shows the mechanics. `--model MODEL --budget USD` is a real, paid run as for v1; the
locked judge model is fixed by `v2/locked/policy.json` (`claude-sonnet-5-5`) and `--judge-model MODEL` overrides it
for a run (v2 with `--model` only). Nothing about v2 has been measured (`docs/v2-test-plan.md`).

## lock

`heuresis lock` hashes the files that the improvement loop and the benchmark must not change (the patterns of
`heuresis.v2.locked.manifest.PROTECTED`) into `PROTECTED.json` and prints the protected hash; `--check` verifies
instead and exits 2 listing every changed, missing or new protected path. The loop's evaluator refuses to run on a
tree that differs from it (`--allow-unpinned` for builds before the first `lock`).

## evolve

`heuresis evolve COMMAND [--json] [--workdir DIR] ...` (default workdir `evolve_runs/`). Details, files and limits in `docs/evolve.md`.

| Command | Purpose |
|---|---|
| `evolve describe` | surface schema with bounds, champion, protected hash, stages, budget |
| `evolve evaluate --stage {static,smoke,screen,dev,promote} (--candidate FILE \| --candidate-dir DIR) [--nonce N]` | one stage on one candidate; with `--nonce` stdout is exactly one `HEURESIS-EVAL N <json>` line |
| `evolve promote CANDIDATE_ID` | promotion test on an archived candidate; makes it champion if it passes |
| `evolve rollback [--to ID] [--reason TEXT]` | restore the previous champion, or one from the history |
| `evolve status` | champion, counters, promotion blocks in use, spend |
| `evolve cycle [--k N] [--seed N] (--offline \| --paid ...)` | one whole cycle |
| `evolve lock-check` | exit 2 if a protected file differs from `PROTECTED.json` |

`evaluate`, `promote` and `cycle` also take `--allow-unpinned`, and for a paid run `--paid --cap USD --ledger PATH
--model NAME --dataset NAME (repeatable) [--judge-model NAME] [--key-env NAME] [--data-root DIR]`: `--paid` needs the
first four, the key is read from the variable named by `--key-env` (default `PROJECTS_ANTHROPIC_KEY`; only the name is
printed) and the cap of a cycle is what the ledger had already spent plus `--cap`. Without `--paid`, `evolve cycle` needs
`--offline` (a packaged invented corpus with deterministic fakes; free). `--cap` without `--paid` is refused.

## verify

`verify` looks up each named unit as it read at `--as-of` (default: today) and checks every sentence
of `--text` against them. Sentences without `[tN]` marks are cited to all named units (marks are
numbered in the order of `--unit`). Units not in force at the date are listed as such; if none is,
the command fails.

## bench

`--dry-run` is the default: no paid call is made. A paid run needs both `--paid` and `--cap USD`.
If `heuresis.bench` is not installed, a one-line message is printed and the exit code is 2. Extra
arguments are passed through to `heuresis.bench.run.main` / `report.main`.

### Benchmark runner (`python -m heuresis.bench.run`)

- **Paid runs.** `--paid` needs `--cap USD` and **`--ledger PATH`**. Without `--ledger` the runner
  refuses (exit 2) and does nothing, so that every paid run, dev or test, shares one append-only ledger
  and two runs can never each believe they have the whole cap. A dry run (the default) may omit it
  (the ledger then defaults to `<out>/ledger.jsonl` and never stops the run).
- **Key.** A paid run reads the API key from the environment variable `PROJECTS_ANTHROPIC_KEY`, or
  from the variable named by `--key-env NAME`. Before any work it prints the variable NAME and the
  base URL (`https://api.anthropic.com`), never the value, and exits 2 if the variable is unset.
- **Sampling.** No `temperature` is sent: the model rejects the parameter (HTTP 400), so sampling is the
  API default. `--thinking disabled` (the default) sends `thinking: {"type": "disabled"}` on every call of
  every system, so `max_tokens` bounds the visible answer; `--thinking default` sends nothing (adaptive
  thinking stays on and its tokens count against `max_tokens`). The manifest records `"temperature": null`
  with a note, the `thinking` setting, the model id and the output cap. Every call's stop reason and
  content-block counts go to the ledger, and each result row records `stop_reasons`, `blocks` and `text_chars`.
- **Splits and systems.** `--split` takes `dev`, `dev2`, `test`, `sealed` (and, for the legal corpora, `temporal`, `temporal_test`; for datasets with a pool, `rot<c>` and `cal<k>`, see below); `dev2` is a tuning split like
  `dev` (`docs/datasets.md`). The default systems include `engine` (answer mode `search`, decision mode
  `grade`) and the exploratory `engine_single` (the earlier design); `--set answer.mode=single` or
  `--set decide.mode=strict` changes the engine itself. The manifest records each engine system's effective
  configuration under `engine_configs`.
- **Config overrides.** `--set SECTION.KEY=VALUE` (repeatable) overrides one packaged config value for the run, e.g.
  `--set draft.prompt=v1`; the manifest records the resulting `engine_config`.
- **Errors.** An API or model failure after the client's retries is written as a row with
  `status: "error"` for every system (the engine included), retried when the runner restarts, and
  counted by the report as a wrong answer for that system. A budget stop is never an error: the run
  stops and no row is written for the call that was refused.
- **Latency.** `ms` is wall-clock time around `System.answer`, measured by the runner the same way for
  every system, with `--workers N` concurrent workers (recorded in the manifest). The engine's stage
  timings are summed into the separate field `stage_ms`.
- **Replay data.** Each engine row stores the raw draft, the passages shown, the tool results and the
  per-claim entailment scores before thresholding (`replay`), for `bench.calibrate`.

- **Version 2 (`engine2`).** `--systems` takes `engine2`, which is never in the default list. `--time-aware-variants`
  adds `+asof` copies (exploratory in the report), `--variants-of NAMES` limits them to the named systems. Flags that
  only `engine2` reads: `--judge-model NAME` (default: the policy's locked judge, thinking disabled), `--strong-model NAME`
  (only if the surface's `route.escalate` is on), `--v2-cache` (a separate generator client with prompt caching),
  `--v2-set SECTION.KEY=VALUE` (repeatable) and `--v2-candidate FILE` (a JSON `{"config": ..., "prompts": ...}`), both
  checked by the v2 schema, and `--v2-calibration PATH` (a file written by `bench.calibrate2`). The manifest records the
  surface hash, the protected hash, the judge and strong models and whether the judge is the policy's.
- **Held-out and drawn splits.** `--registered-run FILE` is required for `test`, `sealed`, `temporal_test` (dry runs
  included): the file must contain the sha256 of the split's ordered question ids. `promo*` is never readable here.
  `rot<c>` (rotating draws) and `cal<k>` (calibration blocks) come from the pool of unused questions of a dataset
  (`bench.splits`; `--data-root DIR` says where the corpora are, default `data`) and are not held out.
- **Other flags.** `--legal-prompt {v1,v2}` (legal datasets), `--agent-rerank`, `--long-context-limit`, `--embedder`, `--reranker`,
  `--entailer`, `--k`, `--agent-k`, `--max-actions`, `--estimate-usd`, `--margin-usd`, `--seed`, `--limit`, `--out`.

### Report (`python -m heuresis.bench.report OUT_DIR [OUT_DIR ...] [--reference NAME] [--family-out FILE] [--iters N] [--seed N]`)

`--reference NAME` is the system every paired comparison puts first (default `engine`; `engine2` for a run of the v2
engine). With several folders a family table with Holm across all of them is also written to `--family-out`.

### Calibration of `engine2` (`python -m heuresis.bench.calibrate2 RUN_DIR [RUN_DIR ...] --label {containment,judge} [--out FILE] [--data-root DIR]`)

Fits the confidence threshold `tau` of `engine2` from the `engine2` rows of non-held-out folders (`dev`, `dev2`,
`temporal`, `cal<k>`, `rot<c>`): it reads each row's `replay` payload, labels answers by containment of a gold answer
or by the `judge.jsonl` verdict, walks the grid of `v2/locked/policy.json` from the strictest threshold and writes
`src/heuresis/v2/calibration/<dataset>-<surface hash[:12]>.json` (and a `.table.md`), or the path given by `--out`. If nothing
is certified `tau` is null and the engine keeps `default_tau`. A file is valid only for the surface it was fitted on.

### Judge-assisted secondary grade (`python -m heuresis.bench.judge RUN_DIR [RUN_DIR ...]`)

Secondary and exploratory; the containment grade stays the primary measure and is never changed.
For every answered row of every system that the containment grader marked wrong on an answerable
question, the generator's model (thinking off, tag `judge` in the shared ledger) is asked whether the
answer states the same answer as a gold answer (EQUIVALENT / NOT_EQUIVALENT). Verdicts are written to
`RUN_DIR/judge.jsonl` (resumable), never into `results.jsonl`; `bench.report` then adds Table 1b
(correct and penalised score under the judge-assisted grade, rows flipped per system). Without
`--paid` it only prints how many rows it would judge; `--paid` needs `--cap`, `--ledger` and the key
variable, as for `bench.run`. Dev run folders only: `dev` and `dev2` (it refuses any other split).

### Threshold calibration (`python -m heuresis.bench.calibrate RUN_DIR [RUN_DIR ...]`)

Prints the penalised score of the engine at each of the 45 pairs (`support_threshold`,
`partial_threshold`) in 0.1 .. 0.9 with partial not above support, pooled over the run folders, and the
argmax. It replays labelling and the decision from the stored scores: no model, no entailer, no cost.
Ties go to the higher support threshold, then the higher partial threshold (the proposed tie-break of
PREREGISTRATION.md section 8.1). It refuses any run folder whose manifest split is not the `--split`
given (`dev`, the default, or `dev2`), and every other split. With `decide.mode = "grade"` (the default)
the thresholds no longer decide what is removed, so the grid is flat; it is informative only for the
`strict` mode (`engine_single`).

## Verification status

All behaviour above is covered by `tests/test_cli.py`. The `--local` path and the `bench` delegation
were not exercised end to end here (no ONNX models, benchmark package not tested through the CLI).
The surface hash is the sha256 of the canonical JSON of the packaged default configuration.
