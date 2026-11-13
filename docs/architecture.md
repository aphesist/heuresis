# Architecture

How `heuresis` is built, stage by stage. Shared types are in `src/heuresis/model.py`; function
signatures are in `docs/contracts.md`. This page describes what the code does; it makes no claim
about how well it does it (see the README's honesty table).

## Data model

Five kinds of object, all frozen dataclasses (`model.py`):

| Object | What it is |
|---|---|
| `Source` | Where units come from. Has a `coverage` grade (0 to 4) that caps the grade of any answer relying on it, and an `authority` that orders sources when they conflict. |
| `Unit` | A stable identity whose text changes: a provision, a note, a file, a schema card. Has a kind, an optional parent and a title. |
| `Event` | One change to one unit: `create`, `replace`, `repeal`, `restore` or `correct`, with a date, a `recorded_at` stamp, evidence, a certainty (`low`, `medium`, `high`) and optional extra dates in `axes`. |
| `Version` | One text of one unit over one validity interval `[valid_from, valid_to)`, computed by replaying events. Never stored by a domain; always derived. |
| `Edge` | A typed link that exists in the corpus (never extracted by a model), valid over an interval. |

Events are the source of truth. `Store.rebuild()` replays them per unit, in the order
`(date, recorded_at, id)`, into a `versions` table and an FTS5 index. Ingesting twice changes
nothing: ids are deterministic and `add` is idempotent (an event id seen before with different
content is an error).

## Time axes

- **Valid time** (`AsOf.valid`): when the content is in force. A version is in force on date `d`
  when `valid_from <= d < valid_to`; `None` is unbounded. `valid = None` means today (UTC).
- **Transaction time** (`AsOf.recorded`): what the corpus knew by a timestamp. A `correct` event
  rewrites the text of a past interval without changing the interval, and is visible only to
  queries whose `recorded` is at or after its `recorded_at`.
- **Domain axes** (`Domain.axes`, `Event.axes`): extra named dates a plug-in declares, for example
  `published` and `effects` in `legal_br`. They are carried with each version and shown in
  citations. Only valid and recorded time filter retrieval.

## Stages of `Engine.ask`

Cost-ordered: the cheap, local stages run first, the model is called (once for an easy question,
a few times for a hard one, see step 3), and everything after it is local again.

1. **Understand** (`router.py`, zero cost). Rules extract an explicit date from the question into
   `as_of.valid` (ISO, `15/03/2024`, "March 2024", "em março de 2024", a bare year) and set an
   intent (`lookup`, `multi_hop`, `compute`, `table`, `out_of_scope`). A caller-supplied `as_of`
   always wins. Domain rules may add a scope (for example the norm named in a question). An optional
   classifier is consulted only when no rule fired or rules disagree; below `ask_threshold` the
   router sets `clarify` and the engine returns `needs_input` instead of guessing. `Engine` then
   drops a question-extracted date when the corpus has no version history or the date precedes
   the first version, and searches as of today.
2. **Retrieve** (`retrieve.cascade`). Lexical search first (SQLite FTS5 with the as-of and scope
   filters inside the SQL, before ranking). An early-stop test compares the score at rank 1 with the
   score at rank `rerank_out`; if the margin reaches `early_stop_margin` (never for `multi_hop`),
   the dense and expand stages are skipped. Otherwise dense search runs with the same filters and the
   two lists are fused by reciprocal rank fusion. Optional stages, off by default: expansion along
   explicit edges (`expand`) and a cross-encoder rerank (`rerank`). At most `rerank_out` passages
   go on, numbered `t1..tn`, each with its source coverage and version certainty.
3. **Answer** (`draft.py`, `engine.py`), in one of two modes chosen by `answer.mode`. In both, the
   prompt holds the as-of date, the passages with their validity spans (the one shared
   `passage_line` rendering), the question and an optional length limit, and the model writes short
   sentences each ending in citation marks, may request deterministic tool calls
   (`CALL k1 calc {...}`), or may write `ABSTAIN <type>: <reason>`. Passages are dropped, never cut,
   to fit `max_context_chars`.
   - `"search"` (the default since the redesign; a hypothesis until measured, see the README).
     Turn 1 shows the passages of the step-2 cascade, so an easy question costs one call. The model
     may answer, or reply with exactly one line `SEARCH: <query>`. A search runs the **same cascade
     with the question's own as-of date and scope**, so every search is date-filtered in code; it
     shows up to `answer.search_k` passages that were not shown before, with marks continuing the
     numbering (`t9`, `t10`, ...), and the model gets the whole accumulated context again. At most
     `answer.max_searches` searches (default 4); when none remain the prompt says so and the model
     must answer or abstain, and a further `SEARCH` ends in an `unsupported` abstention with a trace
     note. Each model turn is a `draft` stage and each search a `search` stage; budget is checked
     before every call.
   - `"single"` (the earlier design, kept and tested): one draft over the one retrieval of step 2.
4. **Tools** (`tools/`). `calc` (arithmetic by AST whitelist and `Decimal`), `dates` (differences,
   additions, weekday checks) and `sql` (one read-only `SELECT` with a row cap and a time limit). The
   engine binds `sql` to the database the `tables` domain read; a model-written `db` argument is
   overwritten. After a `sql` call there is one follow-up draft with the results in the prompt
   (in `search` mode the follow-up repeats the last turn's prompt).
5. **Verify** (`locked/verify.py`, local). Four checks per sentence: every cited mark exists; every
   cited version is in force at the date (checked against the store, not the passage copy); the cited
   passages entail the sentence (local NLI model, scored as the best entailment over title-prefixed
   windows of up to three consecutive sentences of each cited passage, `verify.support = "window_title"`;
   thresholds `support_threshold` and `partial_threshold`); every number in the sentence appears in a cited passage or is a cited tool
   value. A sentence with no marks is unsupported. A sentence that fails exists, valid or numbers is
   unsupported whatever its entailment score.
6. **Decide** (`locked/decide.py`), in one of two modes chosen by `decide.mode`.
   - `"grade"` (the default since the redesign): verification grades, it does not gate. A sentence is
     removed, or the answer withheld, only for a **deterministic failure**: a cited mark that does not
     exist, a cited version not in force at the as-of date, or a number found in no cited passage or
     tool result; a sentence with no citation mark at all fails too, so that every sentence the engine
     returns cites a source or a tool result). The model's own `ABSTAIN` still abstains, and if every sentence fails a deterministic
     check the answer is an abstention (`not_valid_at_date` when all failed only the date check, else
     `unsupported`). Entailment support no longer removes anything; a kept sentence below the support
     threshold is labelled `partial` and keeps its citations.
   - `"strict"` (the earlier design): all claims supported (fraction `min_supported_fraction`):
     `answered`. At least `partial_fraction` supported: `partial`, with the unsupported sentences
     removed. Otherwise an abstention.
   In both, the grade is the minimum of the lowest claim support, the lowest cited certainty and the
   lowest cited source coverage (of the kept sentences), mapped to 0..1; it is the confidence used for
   risk-coverage.
7. **Assemble.** The answer text with tool values filled in, the claims with their labels and
   citations (`unit_id @ valid_from..valid_to`), the grade and a trace of every stage with time,
   tokens and cost.

## Abstention types

An abstention names why, so the caller can act on it (`model.ABSTENTIONS`):

| Type | When |
|---|---|
| `no_source` | nothing relevant was found |
| `not_valid_at_date` | the topic exists but no version is in force at the date (also when all cited versions failed the date check) |
| `outside_coverage` | every retrieved passage comes from a source with coverage 0 |
| `unsupported` | a draft was written but did not pass verification, the model asked to search with no search left, or the model call failed |
| `needs_input` | the router wants one datum from the user |
| `out_of_scope` | the router judged it not a question for this corpus |
| `budget` | the cost budget ran out before a verified answer |
| `tool_failed` | a required computation could not be done |
| `false_premise` | the question assumes something the sources contradict |
| `conflict` | sources of equal authority disagree. **Not built** as a check: the decision rule has a `divergent` branch, but nothing in the engine produces the conflict flag it reads. |

The drafter can declare any of these types itself with `ABSTAIN <type>: <reason>`; an unknown type
becomes `unsupported`. In practice `tool_failed`, `false_premise` and `conflict` come only from
that route.

## Domains

A domain plug-in (`domains/`) turns a path into sources, units, events and edges, and may add router
rules, tools and abstention wording. Registered: `text` (Markdown folder, one unit per section, dated by the front-matter date or the file's
modification date), `git` (read-only git commands, commits as events), `tables` (a SQLite file, one
schema-card unit per table, with the `sql` tool), `jsonl` (the exchange format used by the benchmark)
and `legal_br` (an example for Brazilian legislation on synthetic data; not a legal product).

## What is locked

`src/heuresis/locked/` (`verify.py`, `decide.py`, `scoring.py`, `guard.py`) is the part an outside
optimiser must not change. `locked_hash()` is the sha256 over the names and bytes of its `*.py`
files. It holds the verifier, the decision rule, the scoring used by the benchmark and the guard
itself.

`src/heuresis/surface/` is the mutable part: `default.json` (one dataclass per stage), `config.py`
and `prompts.py`. `check_diff(paths)` returns every changed path outside `src/heuresis/surface/`;
a diff with any such path is rejected. Everything else (store, router, retrieval code, tools,
benchmark) is outside both folders and is changed by hand, in review.

The split is a contract, not a sandbox: the guard checks paths in a diff, and the hash lets a
benchmark record which locked code it ran. It does not stop code in the surface from doing what
Python allows.

## Cost accounting

Every model call returns a `Usage` priced by `pricing.price` from a dated table. The engine's trace
sums per stage; in `search` mode every model turn (`draft`) and every search (`search`) is a stage
with its tokens, cost and time, so the cost of a question is the sum of all of them and the number
of model calls and retrievals can be read from the trace; the benchmark's ledger (`bench/ledger.py`) appends every charge to a file and stops
at a cap. Local models (embedder, reranker, entailer) are not priced.

## Version 2

Version 2 is a second engine next to v1, not a rewrite of it (`src/heuresis/v2/`; the design and its evidence are in
`docs/design-v2.md`, the signatures in `docs/v2-contracts.md`, the improvement loop in `docs/evolve.md`). It is **built
and tested offline only; nothing about it has been measured** (the paid stages are in `docs/v2-test-plan.md`).
`heuresis ask --engine v2` and the benchmark system `engine2` run it; v1 is unchanged and stays the default.

Stages of one question (`v2/engine.py`; numbered as in its code and stage trace):

1. understand: the question's own as-of date and intent are fixed by code, never by the model.
2. lookup: provisions the question names are resolved by `references.py` and put first in the evidence.
3. retrieve: the same date-filtered store as v1 (`store.py`, `retrieve.py`).
4. propose (`v2/agent.py`): a model writes sentences that cite passages by mark `[t1]`, ...; it may issue `SEARCH:` and `OPEN:` actions for more passages (each date-filtered by the store), `CALL` lines for the locked tools, or `ABSTAIN <type>`.
5. tools and 6. bind: tool results (`k` marks) are run and bound into the sentences (`v2/bind.py`).
7. gates: deterministic checks per sentence: mark exists, version in force at the date, numbers traced, named references traced (`v2/locked/gates.py`).
8. repair: sentences that failed a check are sent back with their reasons (`v2/repair.py`).
9. judge: a locked judge model, fixed by `v2/locked/policy.json`, rates the surviving sentences and the answer as a whole (`v2/locked/judge.py`).
10. decide: a locked rule gives answered / partial / a typed abstention and a confidence against a threshold `tau`, calibrated by `bench.calibrate2` or `default_tau` (`v2/locked/decide.py`, `calibration.py`).
11. escalate: optionally one retry with a stronger model after an unsupported abstention (off by default). 12. assemble: the answer, its claims, passages, meta and cost.

Locked and surface split of v2. **Locked** (`src/heuresis/v2/locked/`, plus `store.py`, `model.py`, `interfaces.py`, `tools/`,
`references.py`, `v2/bind.py`, the benchmark modules and `src/heuresis/evolve/`): changed by hand, in review, and hashed in
`PROTECTED.json` (`heuresis lock`); the loop's evaluator refuses to run if one differs. **Surface** (`src/heuresis/v2/surface/`):
`default.json` (config values within the bounds of `v2/locked/schema.py`), per-domain overrides (`domain.legal_br.json`) and
four prompts (`agent_system`, `agent_more`, `agent_last`, `repair`, with `.legal_br` variants). It is data only; the loop changes
nothing else, and a candidate containing code, a path outside the surface or a forbidden string fails the static stage.
As in v1 this is a contract, not a sandbox (`docs/evolve.md`, stated limits).

