# Command line

`heuresis` (entry point `heuresis.cli:main`; also `python -m heuresis.cli`). Every command takes
`--json` to print JSON instead of text. Exit codes: 0 success, 2 refused or invalid input (message
on stderr), 1 unexpected failure (one line, no traceback).

| Command | Purpose |
|---|---|
| `init DB [--domain NAME]` | create an empty database; the domain is remembered |
| `ingest DB PATH [--domain NAME]` | read a path with a domain plug-in into the store (default domain: the database's, else `text`) |
| `index DB [--local]` | embed versions that have no vector yet; `--local` loads the ONNX models from `heuresis.models_local` |
| `ask DB QUESTION [--as-of DATE] [--recorded TS] [--source ID ...] [--budget USD] [--local] [--model MODEL] [--trace]` | verified answer or typed abstention |
| `search DB QUESTION [--as-of DATE] [-k N]` | passages in force at the date, no drafting |
| `unit DB UNIT_ID [--as-of DATE]` | one unit as it read at the date, with its validity interval |
| `verify DB --text TEXT --unit UNIT_ID ... [--as-of DATE]` | verify a text against the named units in force at the date |
| `hash` | the locked-folder hash, the surface hash and the baseline prompts hash, exactly as a benchmark run manifest records them |
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
- **Errors.** An API or model failure after the client's retries is written as a row with
  `status: "error"` for every system (the engine included), retried when the runner restarts, and
  counted by the report as a wrong answer for that system. A budget stop is never an error: the run
  stops and no row is written for the call that was refused.
- **Latency.** `ms` is wall-clock time around `System.answer`, measured by the runner the same way for
  every system, with `--workers N` concurrent workers (recorded in the manifest). The engine's stage
  timings are summed into the separate field `stage_ms`.
- **Replay data.** Each engine row stores the raw draft, the passages shown, the tool results and the
  per-claim entailment scores before thresholding (`replay`), for `bench.calibrate`.

### Judge-assisted secondary grade (`python -m heuresis.bench.judge RUN_DIR [RUN_DIR ...]`)

Secondary and exploratory; the containment grade stays the primary measure and is never changed.
For every answered row of every system that the containment grader marked wrong on an answerable
question, the generator's model (thinking off, tag `judge` in the shared ledger) is asked whether the
answer states the same answer as a gold answer (EQUIVALENT / NOT_EQUIVALENT). Verdicts are written to
`RUN_DIR/judge.jsonl` (resumable), never into `results.jsonl`; `bench.report` then adds Table 1b
(correct and penalised score under the judge-assisted grade, rows flipped per system). Without
`--paid` it only prints how many rows it would judge; `--paid` needs `--cap`, `--ledger` and the key
variable, as for `bench.run`. Dev run folders only (it refuses any other split).

### Threshold calibration (`python -m heuresis.bench.calibrate RUN_DIR [RUN_DIR ...]`)

Prints the penalised score of the engine at each of the 45 pairs (`support_threshold`,
`partial_threshold`) in 0.1 .. 0.9 with partial not above support, pooled over the run folders, and the
argmax. It replays labelling and the decision from the stored scores: no model, no entailer, no cost.
Ties go to the higher support threshold, then the higher partial threshold (the proposed tie-break of
PREREGISTRATION.md section 8.1). It refuses any run folder whose manifest split is not `dev`.

## Verification status

All behaviour above is covered by `tests/test_cli.py`. The `--local` path and the `bench` delegation
were not exercised end to end here (no ONNX models, benchmark package not tested through the CLI).
The surface hash is the sha256 of the canonical JSON of the packaged default configuration.
