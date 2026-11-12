<div align="center">

<a href="https://github.com/aphesist/heuresis"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/header-2-dark.svg"><img src="assets/readme/header-2-light.svg" alt="heuresis: a retrieval engine that cites what was in force, or abstains." width="100%"></picture></a>

</div>

heuresis is an open-source, domain-agnostic retrieval engine for searching and reasoning over
large corpora that change over time. it orders its work by cost (cheap local stages first, one model
call, then local checks), filters by validity date before it ranks, and returns either an
answer in which every sentence is checked against the passages it cites, or a typed abstention that
says why it did not answer. law and accounting were its first intended domain and are one example
plug-in among several; the core knows nothing about any of them.

> **status:** built and tested offline. paid model calls have been made on the dev split only
> (calibration data, n = 100 per dataset; us$5.78 of the us$30 cap, ledger in
> [`results/dev-fixes/ledger.jsonl`](results/dev-fixes/ledger.jsonl)); no system has been run and no
> answer graded on a test or sealed split. two retrieval-only sanity checks did read part of the test
> split (no model, no system answer); they are disclosed in
> [PREREGISTRATION.md, section 2a](PREREGISTRATION.md#2a-prior-contact-with-the-test-split). the
> engine was redesigned on dev evidence (an answer mode where the model may search, and
> verification that grades instead of gating, see [below](#what-the-paid-dev-runs-showed)); the
> redesigned engine is a hypothesis until it has been measured on `dev2`, a fresh tuning split,
> and then on test. the benchmark is pre-registered as a draft in
> [PREREGISTRATION.md](PREREGISTRATION.md) and its confirmatory part has not been run.

## what it found

no system has been run and no answer graded on a test or sealed split; the confirmatory part of the
benchmark has not been run. what follows is dev-split calibration data.

### what the dev pilot showed

*dev split, n=100, retrieval only.* no language model was called. source: [docs/pilot-dev.md](docs/pilot-dev.md),
item 2 (top 8 passages, unit level; wilson 95% intervals in brackets). the cascade run there
included the cross-encoder rerank, which is now off by default.

**the date filter.** on `hoh`, does the retrieved gold unit hold the version in force at the question
date? (answerable dev questions, n=100.)

| system | as-of = question date | as-of = today (not time-aware) |
|---|---|---|
| bm25 | 100/100 = 100% [96, 100] | 49/100 = 49% [39, 59] |
| dense | 92/100 = 92% [85, 96] | 42/100 = 42% [33, 52] |
| bm25 + dense (rrf) | 98/100 = 98% [93, 99] | 48/100 = 48% [38, 58] |
| rrf + rerank | 92/100 = 92% [85, 96] | 43/100 = 43% [34, 53] |
| default cascade (with rerank) | 93/100 = 93% [86, 97] | 44/100 = 44% [35, 54] |

searching as of today returned the version in force at the question date for fewer than half of the
questions, and for none (0/51) of the "outdated" ones. the filter's side of this is partly by
construction, since it removes out-of-force versions before ranking; the table measures how often
retrieval without it returns the wrong version. it is retrieval, not answer accuracy.

**the reranker.** any-gold-unit recall @8, same split:

| dataset | bm25 + dense (rrf) | + cross-encoder rerank |
|---|---|---|
| `musique` | 89/100 = 89% [81, 94] | 95/100 = 95% [89, 98] |
| `multihoprag` | 80/88 = 91% [83, 95] | 67/88 = 76% [66, 84] |
| `hoh` (as-of question date) | 98/100 = 98% [93, 99] | 92/100 = 92% [85, 96] |

the rerank raised recall on `musique`, lowered it on `multihoprag` and `hoh`, and cost 1.3 to 4.2
seconds per query. it is now an optional stage that is off by default. this change was made from the
same dev questions, so it is a tuned choice, not a tested one.

**the verifier, as a crude proxy.** a local entailment model separated gold-passage statements from
random-passage statements on dev: auroc 0.855 [0.806, 0.902] on `musique`, 0.659 [0.578, 0.734] on
`multihoprag`, 0.918 [0.878, 0.955] on `hoh` (item 5, statements built from the question and gold
answer). this is not a measure of verification quality on drafted answers, which were not available.
at the packaged support threshold of 0.5, 0 of 100 matched pairs on `musique`, 3 of 88 on
`multihoprag` and 39 of 100 on `hoh` scored at or above it, so the threshold is probably too strict
for this kind of statement; the pre-registration calibrates it on dev.

### what the paid dev runs showed

*dev split, n = 100 per dataset, `claude-haiku-5-5`: calibration data, not benchmark results; the same
100 questions per dataset were used three times for tuning.* sources: [`results/dev-fixes/NOTES.md`](results/dev-fixes/NOTES.md),
[`results/dev-fixes/thinking-default/comparison.md`](results/dev-fixes/thinking-default/comparison.md) and
[`results/dev-calibration/phase1/NOTES.md`](results/dev-calibration/phase1/NOTES.md). penalised score:
+1 correct, 0 abstained, -1 wrong.

- **the versioned store with its as-of filter is a large, robust gain.** on `hoh`, `hybrid` (searches as
  of today) scored -0.060 and `hybrid` given the date (`hybrid+asof`) +0.770 with the model's thinking
  disabled; with default thinking -0.100 and +0.680. pooled over the three datasets: 0.120 and 0.390
  (thinking disabled, n = 300).
- **a plain hybrid baseline that is given the date matches the engine on the temporal set.** `hoh`,
  `hybrid+asof` against the (earlier, single-draft) engine: +0.770 against +0.750 (thinking disabled),
  +0.680 against +0.690 (default thinking). so the date filter, not the rest of the engine, carries that
  result.
- **the single-draft engine abstained on 61 to 76 percent of the multi-hop questions** (`musique` 73 and
  76 of 100, `multihoprag` 65 and 61, with thinking disabled and default) and, with the model's default
  thinking on, lost to the `agentic` baseline on both (engine minus `agentic`: `musique` -0.240
  [-0.370, -0.110], `multihoprag` -0.270 [-0.440, -0.110]).
- **the entailment verifier cannot separate right answers from wrong ones.** the claim-level auroc for
  claims of correct versus wrong drafts is 0.50 [0.36, 0.62] for the scoring the engine uses (163 claims
  of correct and 24 of wrong drafts, pooled) and 0.44 to 0.57 for every candidate tried, because the
  wrong answers' claims are usually true of their passage. this is why verification became a grader of
  confidence, not a gate, in the redesign.

the redesign these results led to (the `search` answer mode and the `grade` decision mode) is **not
measured**. the check is a paid run on `dev2` with both thinking conditions and `engine_single` beside
the new `engine`; its result will be reported in the same way, as tuning data.

## how it works

```
question ──► understand ──► retrieve ─────────────► answer ──► tools ──► verify ──► decide ──► answer
             (rules,        lexical (as-of filter    model sees  calc,     4 checks   answered   with cited
              dates,        inside the query)        passages;   dates,    per        partial    versions
              ask-back)       │ early stop?          may reply   sql       sentence   abstained  or a typed
                              ▼ no                   SEARCH: q    │        (local)    divergent  abstention
                           dense + RRF                  │  ▲      │                   needs_input
                           (+ edges, + rerank:          ▼  │ same as-of date and scope
                            off by default)           retrieve again (at most 4 searches)
```

1. **understand.** zero-cost rules read an explicit date and an intent from the question. if a
   classifier is attached and unsure, the engine asks one short question instead of guessing.
2. **retrieve.** lexical search first, with the as-of and scope filters applied inside the sql, before
   ranking, so a version that was not in force at the date cannot reach the ranking. when the top
   lexical hits stand clear of the rest, the later stages are skipped; otherwise dense search is
   fused in by reciprocal rank fusion.
3. **answer.** in the default `search` mode the model sees the retrieved passages (so an easy question
   costs one call) and either writes short sentences, each ending in citation marks, or replies
   `SEARCH: <query>`; a search runs the same retrieval with the question's own as-of date and scope,
   shows passages not shown before, and the model answers or searches again (at most four searches).
   it may request deterministic tools (arithmetic, date arithmetic, one read-only sql query) instead
   of computing. `answer.mode = "single"` is the earlier one-draft design.
4. **verify.** per sentence: the cited marks exist, the cited versions are in force at the date, a
   local entailment model scores whether the cited text supports the sentence, and every number comes
   from a cited passage or a tool result.
5. **decide.** in the default `grade` mode a sentence is dropped, or the answer withheld, only for a
   deterministic failure (a mark that does not exist, a version not in force at the date, a number
   found nowhere in the cited passages or tool results) or when the model itself abstains; entailment
   support only sets the grade (the minimum of claim support, version certainty and source coverage),
   which is the answer's confidence. `decide.mode = "strict"` is the earlier design, where low
   support also removes sentences.

time has two axes: *valid time* (when the content was in force) and *recorded time* (when the corpus
learned of it), so a later correction can be hidden from a question about what was known earlier.
details are in [docs/architecture.md](docs/architecture.md).

## pre-registration

a pre-registered comparison of the engine with standard rag and agentic search, on three public
datasets: `hoh` (facts that changed between monthly wikipedia snapshots), `multihoprag` (multi-hop
news questions, 11.8% unanswerable in the pool) and `musique` (multi-hop, all answerable). one
generator, `claude-haiku-5-5`, for every system. dev (100 questions per dataset) and `dev2` (up to 100
more, from the questions in none of dev, test and sealed) are for tuning; test (500) is run once; a
sealed set (300) is never used here.

- **systems:** `closed_book`, `bm25`, `vector`, `hybrid`, `hybrid_rerank`, `agentic` (4-search cap),
  `engine`; an `oracle` as a ceiling; and, exploratory, `engine_single` (the earlier engine design) and
  time-aware `+asof` copies of the baselines. `long_context` is not run: the corpora are 1.4 to 7.3 million
  tokens.
- **primary test:** the engine against each of the six baselines on each dataset (18 comparisons), on
  the penalised score (+1 correct, 0 abstained, -1 wrong), paired permutation test, holm-corrected at
  0.05.
- **cost:** cost per correct answer against `agentic` and `hybrid`, with bootstrap intervals.
- **expectations stated in advance:** a win on `hoh` (the date filter), a win on `multihoprag`
  through abstention, and no win over `hybrid` expected on `musique`.
- **budget:** a hard cap of us$30, enforced by a ledger.

the full design, the refutation rules and the threats to validity are in
[PREREGISTRATION.md](PREREGISTRATION.md), which is a draft: thresholds are not calibrated and no hash
is frozen. the legal citation test is a separate study with its own proposed pre-registration, not yet frozen, in
[PREREGISTRATION-legal.md](PREREGISTRATION-legal.md).

## honesty table

what each claim rests on today. "measured" means a number in a committed file; "tested" means a test
in `tests/` passes; "modelled" means arithmetic on stated assumptions.

| claim | status | basis |
|---|---|---|
| the as-of filter never returns a version outside its validity interval | **tested** (property test) | `tests/test_store.py`, `test_invariant_nothing_outside_validity` (hypothesis, 150 examples) |
| consolidated text is replayed from events, including corrections and transaction time | **tested**, on synthetic fixtures only | `tests/test_store.py`, `tests/test_domains.py`; no real amended corpus has been used |
| numbers in an answer come only from cited sources or tool results | **tested** | `tests/test_locked_verify.py` |
| the sql tool is bound to the engine's own database; a model-written `db` is overwritten | **tested** | `tests/test_engine.py`, `test_sql_binding` |
| the guard rejects diffs outside the surface | **tested** | `tests/test_locked_guard.py` |
| the date filter fixes in-force retrieval on `hoh` | **measured** (dev, n=100, retrieval only) | 92 to 100 of 100 with the filter against 42 to 49 of 100 without; partly by construction; no answer accuracy ([pilot](docs/pilot-dev.md)) |
| time-aware retrieval lifts answer accuracy on dated questions | **measured** on dev (n = 100 per dataset, calibration data) | `hoh`: `hybrid` -0.060 and `hybrid+asof` +0.770 penalised score (thinking disabled); pooled 0.120 and 0.390 (n = 300). a plain `hybrid+asof` matches the single-draft engine on `hoh` (+0.770 against +0.750). [`results/dev-fixes/thinking-default/comparison.md`](results/dev-fixes/thinking-default/comparison.md) |
| a local verifier separates matched from mismatched passages | **measured** as a crude proxy (dev) | auroc 0.855, 0.659, 0.918 on `musique`, `multihoprag`, `hoh`; not verification quality on drafted answers |
| the benchmark costs a few dollars | **modelled**, partly checked on dev | $2.16 to $4.01 for one test run of seven systems on 3 x 500 questions at 1 to 4 agentic searches; excludes `hybrid`, the `+asof` variants, `engine_single`, the search mode and calibration; assumes 120 output tokens per call and 3.5 characters per token. on dev the measured cost was us$0.00006 to 0.0008 per question and system, thinking disabled or default (`results/dev-fixes/thinking-default/comparison.md`, cost table) |
| the engine beats the baselines on the penalised score | **hypothesis** | the pre-registered 18-comparison family; not run |
| it is cheaper per correct answer than agentic search | **hypothesis** | bootstrap interval of the difference; not run |
| verification as a gate improves reliability | **measured** on dev: it did not (n = 100 per dataset, calibration data) | claim-level auroc 0.50 [0.36, 0.62] (163 claims of correct, 24 of wrong drafts); the single-draft engine abstained on 149 of 300 dev questions; the threshold grid is flat. [`results/dev-calibration/phase1/NOTES.md`](results/dev-calibration/phase1/NOTES.md), [`results/dev-fixes/NOTES.md`](results/dev-fixes/NOTES.md) |
| the redesigned engine (the model may search, with every search date-filtered; verification only grades) beats the single-draft engine and the baselines | **hypothesis** | built and tested offline (`tests/test_engine_search.py`); not measured. the check is a paid run on `dev2`, then the test split |
| the grade (min of support, version certainty, source coverage) orders answers by correctness | **hypothesis** | the support part had auroc about 0.5 on dev; version certainty and source coverage are constant in the benchmark corpora |
| the ask-back gate helps | **hypothesis**, not benchmarked | the benchmark attaches no classifier, so the gate cannot fire there |
| coverage grades improve calibration | **hypothesis**, not benchmarked | the benchmark datasets declare full coverage |
| explicit-edge expansion helps | **hypothesis**, off by default | not evaluated; the benchmark corpora have no edges |
| divergence (conflict) detection | not built | the decision rule has a branch for it; nothing produces the flag |
| the offline mode's rule-based verifier | a test fixture, lenient | token containment; not a demonstration of verification quality |
| portuguese | untested beyond tokenisation, dates and wording | no portuguese retrieval or verification evaluation; the verifier model is reported not to have been trained on portuguese data |
| the legal plug-in | a synthetic example | not legal advice and not a legal product |

rows move from *hypothesis* to *measured* only when a result with its confidence interval is
committed.

## quick start

python 3.11+. the core depends on numpy only. `local` adds onnx runtime for local models; `bench` adds
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
heuresis hash                                                           # locked-folder, surface and baseline-prompt hashes
```

offline, `ask` uses built-in fakes: an extractive "model" and a rule-based verifier. it shows the
mechanics (dates, citations, abstentions), not answer quality. a real model needs `--model` and a
required `--budget`; the key is read from `PROJECTS_ANTHROPIC_KEY`. see [docs/cli.md](docs/cli.md).

```python
from heuresis import Engine, AsOf

with Engine.open("demo.db", "legal_br") as eng:
    ans = eng.ask("Qual o texto do art. 2º?", as_of=AsOf(valid="2021-01-01"))
    print(ans.status, round(ans.grade, 2), ans.citations)
    # answered 0.95 [('urn:lex:br:federal:lei:2020-03-10;1!art2', 0)]
    print(ans.text)
    print(eng.unit("urn:lex:br:federal:lei:2020-03-10;1!art2", AsOf(valid="2023-01-01")).text)
```

an mcp server over the same engine is described in [docs/mcp.md](docs/mcp.md).

## plug-ins

a domain plug-in turns a path into sources, units, events and edges, and may add router rules, tools
and wording. everything domain-specific lives there.

| plug-in | reads | time comes from | notes |
|---|---|---|---|
| `text` | a folder of markdown or plain text | front-matter date, else file modification date | one unit per section |
| `git` | a local repository | commit dates | read-only git commands |
| `tables` | a sqlite file | file date | one schema-card unit per table; enables the bound `sql` tool |
| `jsonl` | the exchange format (`sources`, `units`, `events`, `edges`) | the events themselves | used by the benchmark |
| `legal_br` | the `jsonl` format with lexml-style ids | the events, plus `published` and `effects` axes | a synthetic example: portuguese date and reference rules and wording; not legal advice, not a legal product |

## law as the example domain: a citation-integrity test

the engine is generic; law is the example where its design should matter, because the failure it targets is
real: lawyers have been sanctioned after ai tools invented laws, citations and wording. the benchmarks above
grade whether an answer string appears; none measures whether a **citation exists, was in force on the date
asked about, or supports the claim**. [`docs/legal-citation-test.md`](docs/legal-citation-test.md) describes a
test that does, on brazilian federal law:

- a corpus in three tiers built into the exchange format (the legal texts of br-taxqa-r; about 29,000
  federal norms from `ctresb/leis`; and a small versioned tier whose provisions have two real, dated wordings
  downloaded from the câmara dos deputados), every id and date taken from a source, no provision written by
  anyone;
- in the core, only generic pieces: an optional `Domain.resolve_references`, a deterministic gate
  `references_traced` (a sentence may only name the provisions it cites, and they must exist), and a
  citation metric (`bench/citations.py`) applied identically to every system's answer text; in the `legal_br`
  plug-in, a resolver for citations as lawyers write them ("art. 8º, II, da Lei nº 9.250/1995", "CTN, art. 43");
- questions from br-taxqa-r with official answers and article-level gold, and date-dependent questions built
  by code from the version pairs.

status: **built and checked offline; no paid call has been made for it.** what it measures, what it does not,
and its limits (single-version tiers, an incomplete corpus, "norm not found" meaning fabricated *or* outside the
corpus) are in the document and in [`results/brlaw/NOTES.md`](results/brlaw/NOTES.md).

## the locked surface

the code is split into a part an outside optimiser may change and a part it may not.

- `src/heuresis/surface/` is the **mutable surface**: the configuration (`default.json`, one block per
  stage) and the prompts.
- `src/heuresis/locked/` is the **locked judge**: the verifier, the decision rule, the scoring and the
  guard. `locked_hash()` is the sha256 of its files, and every benchmark run records it.
- `check_diff(paths)` returns every changed path outside the surface. a candidate change that touches
  anything else is rejected.

the intent is that an external optimiser, such as [`aphesist/autopoiesis`](https://github.com/aphesist/autopoiesis),
proposes changes to the surface, scores them on the dev split with the locked scoring, and is refused
if it edits the judge. that is a contract between the two projects, not something this repository has
exercised: no optimiser has been run against it. the guard checks paths in a diff; it is not a
sandbox.

## related work

versioned retrieval over legislation already exists; one example is sat-graph rag. the contribution
claimed here is narrower: an integration of validity-filtered retrieval, a cost-ordered cascade and
claim-level verification with typed abstention; a general versioned-retrieval core with legal text as
one plug-in; and a pre-registered, cost-accounted comparison with standard rag and agentic search on
public datasets. it does not claim a new retrieval method, a better verifier or a result on legal
text.

where it sits: heuresis is the retrieval layer that [`aphesist/contraprova`](https://github.com/aphesist/contraprova)
calls, and its surface is what [`aphesist/autopoiesis`](https://github.com/aphesist/autopoiesis) is
meant to improve from outside, under the locked judge. neither integration is exercised in this
repository.

## budget

a hard cap of us$30 for every paid call this project makes, enforced by an append-only ledger that
stops a run at the cap minus a margin (us$1 by default; the dev runs used us$0.25). us$5.78 had been
spent by the end of the dev re-run (dev split only). the modelled cost of a test run is in the honesty table;
the figures are in [docs/pilot-dev.md](docs/pilot-dev.md) (item 6) and
[PREREGISTRATION.md](PREREGISTRATION.md) (section 9). everything else (the pilot, the tests, the
offline mode) costs nothing. the `dev2` check has its own ledger and a separate cap.

## licence

apache-2.0 ([LICENSE](LICENSE)). the benchmark datasets are not redistributed; their licences and open questions are in
[docs/datasets.md](docs/datasets.md).

the pictures in `assets/readme/` are drawn with the aphes.ist readme kit and embed subsets of Aphesis Script (SIL Open Font License 1.1, reserved font name "Aphesis Script") and Special Elite (apache-2.0, © 2010 Astigmatic), and the project's icon, a mark of aphesist's that is not covered by this project's licence.
