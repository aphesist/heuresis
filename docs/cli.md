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
| `hash` | the locked-folder content hash and the surface (default config) hash |
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

## Verification status

All behaviour above is covered by `tests/test_cli.py`. The `--local` path and the `bench` delegation
were not exercised end to end here (no ONNX models, benchmark package not tested through the CLI).
The surface hash is the sha256 of the canonical JSON of the packaged default configuration.
