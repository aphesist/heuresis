# heuresis

*Retrieve what was in force, cite it, and abstain when you cannot.*

**heuresis** is an open-source, domain-agnostic retrieval engine for searching and reasoning over
large corpora that change over time. It orders its work by cost (cheap local stages first, one model
call, then local verification), filters by validity date before it ranks, and returns either an
answer in which every sentence is checked against the passages it cites, or a typed abstention that
says why it did not answer. Law and accounting were its first intended domain and are one example
plug-in among several; the core knows nothing about any of them.

> **Status: built and tested offline; nothing has been measured on a test split; no paid model call
> has been made.** The one measurement that exists is a retrieval-only pilot on the dev split
> ([below](#what-the-dev-pilot-showed)). The benchmark is pre-registered as a draft in
> [PREREGISTRATION.md](PREREGISTRATION.md) and has not been run.

## How it works

```
question ──► understand ──► retrieve ──────────────► draft ──► tools ──► verify ──► decide ──► answer
             (rules,        lexical (as-of filter     one       calc,     4 checks   answered   with cited
              dates,        inside the query)         model     dates,    per        partial    versions
              ask-back)       │ early stop?           call      sql       sentence   abstained  or a typed
                              ▼ no                                        (local)    divergent  abstention
                           dense + RRF                                                needs_input
                           (+ edges, + rerank: off by default)
```

1. **Understand.** Zero-cost rules read an explicit date and an intent from the question. If a
   classifier is attached and unsure, the engine asks one short question instead of guessing.
2. **Retrieve.** Lexical search first, with the as-of and scope filters applied inside the SQL, before
   ranking, so a version that was not in force at the date cannot reach the ranking. When the top
   lexical hits stand clear of the rest, the later stages are skipped; otherwise dense search is
   fused in by reciprocal rank fusion.
3. **Draft.** One model call writes short sentences, each ending in citation marks, and may request
   deterministic tools (arithmetic, date arithmetic, one read-only SQL query) instead of computing.
4. **Verify.** Per sentence: the cited marks exist, the cited versions are in force at the date, a
   local entailment model says the cited text supports the sentence, and every number comes from a
   cited passage or a tool result.
5. **Decide.** Answered, partial (unsupported sentences removed), or abstained with a reason. The
   grade is the minimum of claim support, version certainty and source coverage.

Time has two axes: *valid time* (when the content was in force) and *recorded time* (when the corpus
learned of it), so a later correction can be hidden from a question about what was known earlier.
Details are in [docs/architecture.md](docs/architecture.md).

## Quick start

Python 3.11+. The core depends on NumPy only. `local` adds ONNX Runtime for local models; `bench` adds
the dataset loaders.

```bash
pip install -e ".[dev]"
python3 -m pytest -q

# offline, on the synthetic fixture: no model, no key, no cost
F=tests/fixtures/domains/legal_br
heuresis init demo.db --domain legal_br
heuresis ingest demo.db $F
heuresis ask demo.db "Qual o texto do art. 2º?" --as-of 2021-01-01     # the original wording
heuresis ask demo.db "Qual o texto do art. 2º?" --as-of 2023-01-01     # the corrected rewording
heuresis ask demo.db "Qual o texto do art. 2º?" --as-of 2023-01-01 --recorded 2022-12-31   # before the correction was recorded
heuresis hash                                                           # locked-folder and surface hashes
```

Offline, `ask` uses built-in fakes: an extractive "model" and a rule-based verifier. It shows the
mechanics (dates, citations, abstentions), not answer quality. A real model needs `--model` and a
required `--budget`; the key is read from `PROJECTS_ANTHROPIC_KEY`. See [docs/cli.md](docs/cli.md).

```python
from heuresis import Engine, AsOf

with Engine.open("demo.db", "legal_br") as eng:
    ans = eng.ask("Qual o texto do art. 2º?", as_of=AsOf(valid="2021-01-01"))
    print(ans.status, round(ans.grade, 2), ans.citations)
    # answered 0.95 [('urn:lex:br:federal:lei:2020-03-10;1!art2', 0)]
    print(ans.text)
    print(eng.unit("urn:lex:br:federal:lei:2020-03-10;1!art2", AsOf(valid="2023-01-01")).text)
```

An MCP server over the same engine is described in [docs/mcp.md](docs/mcp.md).

## Plug-ins

A domain plug-in turns a path into sources, units, events and edges, and may add router rules, tools
and wording. Everything domain-specific lives there.

| Plug-in | Reads | Time comes from | Notes |
|---|---|---|---|
| `text` | a folder of Markdown or plain text | front-matter date, else file modification date | one unit per section |
| `git` | a local repository | commit dates | read-only git commands |
| `tables` | a SQLite file | file date | one schema-card unit per table; enables the bound `sql` tool |
| `jsonl` | the exchange format (`sources`, `units`, `events`, `edges`) | the events themselves | used by the benchmark |
| `legal_br` | the `jsonl` format with LexML-style ids | the events, plus `published` and `effects` axes | **a synthetic example**: Portuguese date and reference rules and wording; not legal advice, not a legal product |

## The locked surface

The code is split into a part an outside optimiser may change and a part it may not.

- `src/heuresis/surface/` is the **mutable surface**: the configuration (`default.json`, one block per
  stage) and the prompts.
- `src/heuresis/locked/` is the **locked judge**: the verifier, the decision rule, the scoring and the
  guard. `locked_hash()` is the sha256 of its files, and every benchmark run records it.
- `check_diff(paths)` returns every changed path outside the surface. A candidate change that touches
  anything else is rejected.

The intent is that an external optimiser, such as [`aphesist/autopoiesis`](https://github.com/aphesist/autopoiesis),
proposes changes to the surface, scores them on the dev split with the locked scoring, and is refused
if it edits the judge. That is a contract between the two projects, not something this repository has
exercised: no optimiser has been run against it. The guard checks paths in a diff; it is not a
sandbox.

## The benchmark, in brief

A pre-registered comparison of the engine with standard RAG and agentic search, on three public
datasets: `hoh` (facts that changed between monthly Wikipedia snapshots), `multihoprag` (multi-hop
news questions, 11.8% unanswerable in the pool) and `musique` (multi-hop, all answerable). One
generator, `claude-haiku-5-5`, for every system. Dev (100 questions per dataset) is for tuning; test
(500) is run once; a sealed set (300) is never used here.

- **Systems:** `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic` (4-search cap),
  `engine`; an `oracle` as a ceiling. `long_context` is not run: the corpora are 1.4 to 7.3 million
  tokens.
- **Primary test:** the engine against each of the six baselines on each dataset (18 comparisons), on
  the penalised score (+1 correct, 0 abstained, -1 wrong), paired permutation test, Holm-corrected at
  0.05.
- **Cost:** cost per correct answer against `agentic` and `hybrid`, with bootstrap intervals.
- **Expectations stated in advance:** a win on `hoh` (the date filter), a win on `multihoprag`
  through abstention, and **no win over `hybrid` expected on `musique`**.
- **Budget:** a hard cap of US$30, enforced by a ledger.

The full design, the refutation rules and the threats to validity are in
[PREREGISTRATION.md](PREREGISTRATION.md), which is a draft: thresholds are not calibrated and no hash
is frozen.

## What the dev pilot showed

*Dev split, n=100, retrieval only.* No language model was called. Source: [docs/pilot-dev.md](docs/pilot-dev.md),
item 2 (top 8 passages, unit level; Wilson 95% intervals in brackets). The cascade run there
included the cross-encoder rerank, which is now off by default.

**The date filter.** On `hoh`, does the retrieved gold unit hold the version in force at the question
date? (Answerable dev questions, n=100.)

| system | as-of = question date | as-of = today (not time-aware) |
|---|---|---|
| BM25 | 100/100 = 100% [96, 100] | 49/100 = 49% [39, 59] |
| dense | 92/100 = 92% [85, 96] | 42/100 = 42% [33, 52] |
| BM25 + dense (RRF) | 98/100 = 98% [93, 99] | 48/100 = 48% [38, 58] |
| RRF + rerank | 92/100 = 92% [85, 96] | 43/100 = 43% [34, 53] |
| default cascade (with rerank) | 93/100 = 93% [86, 97] | 44/100 = 44% [35, 54] |

Searching as of today returned the version in force at the question date for fewer than half of the
questions, and for none (0/51) of the "outdated" ones. The filter's side of this is partly by
construction, since it removes out-of-force versions before ranking; the table measures how often
retrieval without it returns the wrong version. It is retrieval, not answer accuracy.

**The reranker.** Any-gold-unit recall @8, same split:

| dataset | BM25 + dense (RRF) | + cross-encoder rerank |
|---|---|---|
| `musique` | 89/100 = 89% [81, 94] | 95/100 = 95% [89, 98] |
| `multihoprag` | 80/88 = 91% [83, 95] | 67/88 = 76% [66, 84] |
| `hoh` (as-of question date) | 98/100 = 98% [93, 99] | 92/100 = 92% [85, 96] |

The rerank raised recall on `musique`, lowered it on `multihoprag` and `hoh`, and cost 1.3 to 4.2
seconds per query. It is now an optional stage that is off by default. This change was made from the
same dev questions, so it is a tuned choice, not a tested one.

**The verifier, as a crude proxy.** A local entailment model separated gold-passage statements from
random-passage statements on dev: AUROC 0.855 [0.806, 0.902] on `musique`, 0.659 [0.578, 0.734] on
`multihoprag`, 0.918 [0.878, 0.955] on `hoh` (item 5, statements built from the question and gold
answer). This is not a measure of verification quality on drafted answers, which were not available.
At the packaged support threshold of 0.5, 0 of 100 matched pairs on `musique`, 3 of 88 on
`multihoprag` and 39 of 100 on `hoh` scored at or above it, so the threshold is probably too strict
for this kind of statement; the pre-registration calibrates it on dev.

## Honesty table

What each claim rests on today. "Measured" means a number in a committed file; "tested" means a test
in `tests/` passes; "modelled" means arithmetic on stated assumptions.

| Claim | Status | Evidence or what it needs |
|---|---|---|
| The as-of filter never returns a version outside its validity interval | **Tested** (property test) | `tests/test_store.py`, `test_invariant_nothing_outside_validity` (Hypothesis, 150 examples) |
| Consolidated text is replayed from events, including corrections and transaction time | **Tested**, on synthetic fixtures only | `tests/test_store.py`, `tests/test_domains.py`; no real amended corpus has been used |
| Numbers in an answer come only from cited sources or tool results | **Tested** | `tests/test_locked_verify.py` |
| The SQL tool is bound to the engine's own database; a model-written `db` is overwritten | **Tested** | `tests/test_engine.py`, `test_sql_binding` |
| The guard rejects diffs outside the surface | **Tested** | `tests/test_locked_guard.py` |
| The date filter fixes in-force retrieval on `hoh` | **Measured** (dev, n=100, retrieval only) | 92 to 100 of 100 with the filter against 42 to 49 of 100 without; partly by construction; no answer accuracy ([pilot](docs/pilot-dev.md)) |
| A local verifier separates matched from mismatched passages | **Measured as a crude proxy** (dev) | AUROC 0.855, 0.659, 0.918 on `musique`, `multihoprag`, `hoh`; not verification quality on drafted answers |
| The benchmark costs a few dollars | **Modelled** | $2.16 to $4.01 for one test run of seven systems on 3 x 500 questions at 1 to 4 agentic searches; excludes `hybrid`, the `+asof` variants and calibration; assumes 120 output tokens per call and 3.5 characters per token |
| The engine beats the baselines on the penalised score | Hypothesis | the pre-registered 18-comparison family; not run |
| It is cheaper per correct answer than agentic search | Hypothesis | bootstrap interval of the difference; not run |
| Verification improves reliability | Hypothesis | no end-to-end run exists; no drafted answers have been verified |
| The ask-back gate helps | Hypothesis, not benchmarked | the benchmark attaches no classifier, so the gate cannot fire there |
| Coverage grades improve calibration | Hypothesis, not benchmarked | the benchmark datasets declare full coverage |
| Explicit-edge expansion helps | Hypothesis, off by default | not evaluated; the benchmark corpora have no edges |
| Divergence (conflict) detection | **Not built** | the decision rule has a branch for it; nothing produces the flag |
| The offline mode's rule-based verifier | A test fixture, lenient | token containment; not a demonstration of verification quality |
| Portuguese | Untested beyond tokenisation, dates and wording | no Portuguese retrieval or verification evaluation; the verifier model is reported not to have been trained on Portuguese data |
| The legal plug-in | A synthetic example | not legal advice and not a legal product |

Rows move from *hypothesis* to *measured* only when a result with its confidence interval is
committed.

## Related work

Versioned retrieval over legislation already exists; one example is SAT-Graph RAG. The contribution
claimed here is narrower: an integration of validity-filtered retrieval, a cost-ordered cascade and
claim-level verification with typed abstention; a general versioned-retrieval core with legal text as
one plug-in; and a pre-registered, cost-accounted comparison with standard RAG and agentic search on
public datasets. It does not claim a new retrieval method, a better verifier or a result on legal
text.

## Budget

A hard cap of US$30 for every paid call this project makes, enforced by an append-only ledger that
stops a run at the cap minus a $1 margin. The modelled cost of a test run is in the honesty table;
the figures are in [docs/pilot-dev.md](docs/pilot-dev.md) (item 6) and
[PREREGISTRATION.md](PREREGISTRATION.md) (section 9). Everything else (the pilot, the tests, the
offline mode) costs nothing.

## Where it sits

heuresis is the retrieval layer that [`aphesist/contraprova`](https://github.com/aphesist/contraprova)
calls, and its surface is what [`aphesist/autopoiesis`](https://github.com/aphesist/autopoiesis) is
meant to improve from outside, under the locked judge. Neither integration is exercised in this
repository.

## Licence

Apache-2.0. The benchmark datasets are not redistributed; their licences and open questions are in
[docs/datasets.md](docs/datasets.md).
