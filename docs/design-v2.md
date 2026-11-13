# heuresis v2: design

Status: **design and offline build; nothing in this document has been measured for v2.**
Every statement carries one of three labels.

- **measured**: a number this project measured, with the file it is in, or a number a
  cited paper measured (then the label of the research report applies: see below).
- **modelled**: arithmetic from measured numbers and stated assumptions.
- **hypothesis**: expected, not tested. The test that would settle it is named in section (g).

`R§x.y` cites `docs/research/validated-agentic-retrieval-and-safe-evolution.md`. That
report labels each of its own claims measured / vendor-claimed / secondary / inference, and
its section 10 lists what could not be verified; a citation here inherits that label.
Signatures and exact rules are in `docs/v2-contracts.md`.

## The goal

An engine that answers as often and as well as an agentic model would, but gives only
(1) an answer whose every statement was checked against the sources it cites, as of a
date, or (2) a typed refusal. And that keeps improving itself against benchmarks it cannot
game. The five goals: correct most of the time; no answer when it does not know; validated
answers; works through dates; continuously self-improving.

---

## (a) What exists, and what the evidence says

### The current engine (v1), in one paragraph

A SQLite store keeps units, events and the dated versions computed from them, on two time
axes (valid time and recorded time). Retrieval is BM25 (FTS5) with the as-of date and scope
inside the SQL, optionally fused with a small local embedder (RRF). The model sees eight
passages and may answer, abstain, or ask for up to four more searches; each search runs
with the question's own date. A locked verifier checks each sentence (cited mark exists,
cited version in force at the date, numbers traced to a cited source or tool); for law it
also requires every provision named in a sentence to be cited by mark, and a model support
gate drops sentences the cited passage does not support. A locked decision rule returns
answered / partial / a typed abstention. A benchmark harness with a spending ledger compares
it with closed-book, hybrid retrieval, agentic search and agentic search given the date.

### What works

| Finding | Evidence | Label |
|---|---|---|
| The date filter is the robust win. Without the date, retrievers return the in-force version 42-49% of the time and 0/51 on outdated-fact questions; with it 92-100%. | `README.md`, `docs/pilot-dev.md` (HoH dev, n=100) | measured |
| Any retriever given the date gains massively: hybrid −0.06 → +0.77 penalised on HoH dev. Version-blind retrieval is a general failure: 0% date-applicable version on a heavily amended tax code; 24-40% → 83-87% with fact-date extraction and version filtering on German statutes. | `README.md`; R§4.1, R§4.2 | measured |
| Citation integrity holds on held-out law. Answers with a fabricated or out-of-force citation: engine 1/615 (0.2%) against 6.0-16.1% for the four baselines, all significant after Holm; the engine answered the most questions (78.2%). | `results/brlaw/heldout/RESULTS.md` | measured (held-out, registered) |
| Letting the model search recovers multi-hop questions a single draft cannot: abstention fell from 61-86% to the level of the agentic baseline. | `results/dev2/NOTES.md` | measured (dev2) |
| Deterministic gates are safe gates. Of 1,625 references in engine answers on held-out law, 0 norms not found, 1 article not found, 0 not in force. | `results/brlaw/heldout/RESULTS.md` | measured |

### What does not work, and why

| Finding | Evidence | Why |
|---|---|---|
| **The engine gives fewer useful answers than agentic search on law**: 34.0% against 38.4% of 615 (−4.4 points, 95% interval [−8.3, −0.5]); cost per useful answer US$0.0078 against US$0.0047. | `results/brlaw/heldout/RESULTS.md` (measured, held-out) | See the next table: the gates remove content that was not wrong. |
| On fresh multi-hop questions the engine is level with plain agentic search (+0.247 vs +0.240) and far behind agentic search given the date (+0.533). | `results/dev2/NOTES.md` (measured, dev2) | The date filter carries the engine's lead; everything else in v1 adds nothing over an agent with the same filter. |
| Dropping uncited sentences removes the conclusion. Replay keeping them: MultiHop-RAG −0.10 → +0.54, pooled +0.247 → +0.493. | `results/dev2/NOTES.md`, offline replay (measured, dev2, in-sample) | "Yes, they agree." cites nothing; the rule treats it like an unsourced fact. |
| Passage-entailment verification cannot tell right answers from wrong ones (claim-level AUROC 0.50 [0.36, 0.62]). | `README.md` (measured, dev) | Wrong answers are true of their passage and do not answer the question. This is by construction: an entailment check reads passage → sentence and never sees the question (R§2.1). |
| `numbers_traced` drops correct sentences: 35% of dated legal sentences on dev, whose dates and article numbers the cited passage does not repeat. | `results/brlaw/NOTES.md` (measured, dev) | The check allows only numbers in the cited text; it ignores the question, the passage title and the provision number being cited. |
| Retrieval recall is the bottleneck on law: BM25 finds a gold provision in the top 8 for 58% of questions; adding the small embedder by RRF lowers it to 51%; the cross-encoder lowers recall on 2 of 3 dev sets. | `results/brlaw/NOTES.md`, `docs/pilot-dev.md` (measured, dev) | Lay question, statutory wording; a weak dense list degrades rank fusion (R§5.1, R§5.6: accent-normalised BM25 beats a strong dense model on 3 of 4 Portuguese legal sets and RRF falls below BM25). |
| Judged support of cited provisions is lower for the engine (74%) than for the retrieval baselines (78-79%). | `results/brlaw/heldout/RESULTS.md` (measured; judge is a model, checked by a second model, not by a person) | The engine cites more (3.66 references per answer) and is forced to attach a mark to every sentence. |
| Conflict and false-premise abstentions exist as types but nothing produces them; coverage grades and ask-back were never exercised. | `README.md` honesty table | Not built / not tested. |
| The lock is a convention. `locked_hash()` is never compared with a stored value, `check_diff` is never called, and `bench.run` does not refuse held-out splits. | code (`locked/guard.py`, `bench/run.py`) | A loop over the engine needs these to be enforced, not documented. |

### Where the useful-answer gap comes from (reading of the held-out aggregates)

On held-out law the engine answered 481 questions and agentic search 477, yet the judge
found the engine's answer equivalent to the official one in 210 cases against 264
(measured). The engine does not answer less; its answers are worse as answers. Its gates
dropped, of 1,798 claims: 408 for a provision named but not cited by mark, 315 for an
untraced number, 111 by the support gate, and the `exists` count of 693 includes those and
every uncited sentence (measured; the counts overlap). Meanwhile its reference check found
essentially nothing false (1 of 1,625). **Reading (hypothesis): most dropped sentences were
correct content removed for a formal reason, and the answer that remained was a fragment.**
The three-sentence cap on legal answers, whose official answers are paragraphs, points the
same way. v2 is built around this reading; section (g) tests it.

---

## (b) The v2 architecture

One idea: **propose like an agent, then bind, check, repair and judge; refuse on any doubt.**
v1 constrained the writer so that the output would pass the checks and then deleted what
failed. v2 lets the model work the way the strongest baseline does, and moves the guarantee
to what happens after: a failed formal check is first repaired with evidence, and only then
removed; what remains is judged against the *question*, not only against the passage.

| # | Component | What changes from v1 | Evidence | Status |
|---|---|---|---|---|
| 1 | **Direct lookup** of provisions the question names, before any search, by the domain's resolver | new | A named provision is a key, not a search problem; 2.8% recall@1 for BM25 plus date filter on a regulation set shows ranking is the weak step (R§4.1) | hypothesis for the gain; zero model cost |
| 2 | **Lexical-anchored retrieval**: BM25 first; dense list combined by convex combination of normalised scores (weight tunable, lexical-only for law); optional corpus-vocabulary expansion from first-pass results | RRF and reranker replaced; expansion new, off by default | Convex fusion beats RRF in and out of domain (R§5.6); RRF with a weak dense list falls below BM25 on Portuguese legal sets (R§5.1) and here (58% → 51%, measured); expansion helps a lexical leg far more than a dense one (+10.3 vs +2.2 R@10, R§5.5) | fusion: adopted on evidence; the default weight and the expansion are hypotheses for the loop to tune |
| 3 | **Agentic propose loop** with three actions, all date-filtered in code: several `SEARCH:` queries per turn, `OPEN:` a passage's neighbours or a named provision, answer | v1 allowed one query per turn and no reading around a hit | Agentic search with default thinking is the strongest approach here (measured, dev2); strong agents issue many searches, weak ones under 2 (R§1.1); gold paragraphs reachable from the same seeds for 75% vs 35% of questions when links can be followed (R§5.3); one-hop expansion over explicit references gives small positive gains (R§5.3) | adopted; the size of the gain is a hypothesis |
| 4 | **Free-form answer**: no sentence cap by default; a concluding sentence that only combines cited sentences may stand without a mark (a *derived* sentence) | v1 dropped every uncited sentence and capped law at 3 sentences | Replay: pooled +0.247 → +0.493 with uncited conclusions kept (measured, dev2, in-sample) | adopted; derived sentences are bounded by rules in (d) |
| 5 | **Citation binding**: a provision named in a sentence that resolves to a unit in force at the date is fetched and cited automatically | v1 dropped the sentence (408 claims on held-out) | Reading of the held-out gate counts (above) | hypothesis |
| 6 | **Deterministic gates v2** (locked): mark exists; version in force (checked in the store); numbers traced, now also allowing numbers in the question, in the passage title and inside a resolved, cited reference; references traced | relaxed where v1 dropped correct sentences, never where integrity is at stake | 35% of dated legal sentences dropped by the old number rule (measured, dev) | adopted |
| 7 | **Repair turn**: failed sentences go back to the model once, with the reason in plain words; it may search or open again | new; v1 deleted | Verification that only deletes over-abstains (61-86%, measured); iterative retrieve-and-revise methods gain on multi-hop sets, with dataset-dependent size (R§1.2) | hypothesis |
| 8 | **Question-conditioned model judge** (locked prompt, one call): per sentence, do the cited passages state it; for derived sentences, does it follow; does the text answer the question asked; is the evidence sufficient; false premise; conflict | replaces local NLI and the v1 support gate; adds the two checks that see the question | The failure is invisible to passage → sentence entailment (R§2.1); a sufficiency rater reaches 93% accuracy and, combined with confidence, adds 2-10 points of selective accuracy (R§1.3, R§2.1); small NLI verifiers do not beat LLM judges on grounding and decomposition does not pay (R§2.2) | adopted as the design; **its ability to separate right from wrong answers on these datasets is the central hypothesis of v2** |
| 9 | **Different kinds of checker**: rules in code for what code can decide; a model judge for meaning, run as a different configuration (or family) from the generator | v1 used the same model for writing, gating and judging | Panels of similar judges share errors (about two effective votes out of nine in one preprint); diversity has to be in the kind of signal (R§2.4) | adopted; same-family judge error correlation stays a stated limit |
| 10 | **Calibrated refusal**: a confidence score from the judge's verdicts, source certainty and coverage; the answer is given only above a threshold fitted on labelled dev answers so that the error rate among answered questions is at most α with confidence 1 − δ | v1 had thresholds nobody could calibrate (flat grid) | Clopper-Pearson with fixed-sequence testing (R§3.1, R§3.2); guarantees are marginal and break under shift (R§3.1) | adopted; what is and is not guaranteed is in (d) |
| 11 | **Typed abstention incl. false premise and conflict**: both produced by the judge and, for conflict, confirmed in code | types existed, nothing produced them | Models flag conflicts poorly unprompted (13% → 60% with a conflict-aware prompt on explicit conflicts) and abstain on about 72% at best on unanswerable sets (R§3.4) | built; accuracy of these two types is a hypothesis and is measured as its own slice |
| 12 | **Cost control**: lookup before search; one judge call with thinking off and a short output; prompt-prefix caching across turns; optional escalation to a stronger model only after an `unsupported` refusal | v1: 2.9 calls, no caching | Cache reads are priced at 0.1× (R§6, vendor pricing); small-first with escalation is supported by routing studies on other tasks only (R§6) | caching adopted (saving is modelled, see (c)); escalation off by default, hypothesis |
| 13 | **Data-only surface with a locked schema**; protected files pinned by a manifest that a test checks | v1's surface contained Python and its lock was never enforced | Code self-modification is where checkers get removed (DGM); evaluator locking eliminated tampering; marker boundaries and instructions did not (R§7.2, R§7.4) | adopted |
| 14 | **Improvement loop over the engine** with rotating dev splits, a sealed promotion set, canaries and tripwires | new | R§7, R§8; section (f) | built offline; never run paid |

### Evaluated and not adopted

| Idea | Decision | Reason |
|---|---|---|
| HyDE / LLM query rewriting before retrieval | rejected as a stage | Helped one dataset, hurt two, half the latency (measured here, as reported in the brief); harms strong retrievers (R§1.4). The agent's own reformulated `SEARCH:` after seeing corpus titles does this job without an extra call. |
| RAPTOR summary tree; LLM-built graphs (GraphRAG, HippoRAG 2) | rejected | A matched-reader replication finds RAPTOR no better than flat BM25; token-matched plain RAG nearly closes the GraphRAG gap; indexing costs millions of LLM tokens per small corpus (R§5.2, R§5.3). |
| Navigation tree from the corpus's own hierarchy, used to steer search | adapted: `OPEN:` reads neighbours in document order | Section-then-chunk two-stage retrieval hurts (R§5.2). The law corpus has no stored hierarchy above the article (`Unit.parent_id` is always empty), so only document order is available without a corpus rebuild. A real hierarchy is future work on the corpus builder. |
| Contextual chunk prefixes written by a model; late chunking | rejected | Vendor-only gains for the first; inconsistent or negative for the second with small embedders (R§5.2). Units already carry a deterministic title (`<norm> — Art. n`), which FTS weights 2:1. |
| Personalised PageRank over cross-references | not built | No statute study found (R§5.3); the law corpus has no edges yet. One-hop expansion over explicit edges is kept as a switch (`edge_expand`). |
| Cross-encoder or LLM listwise reranking | rejected by default | Lowered recall on 2 of 3 dev sets (measured); rerankers end below first stage in half of published experiments; reasoning rerankers lose to the same model without reasoning (R§5.4). |
| ColBERT-style late interaction, learned sparse | not built | No legal evidence; index sizes and CPU cost (R§5.6). |
| Self-consistency / several drafts with agreement | not built | 5-10× cost and blind to consistent errors (R§2.3). Named as the first thing to try if the judge alone does not separate right from wrong (see (g), H2). |
| Claim decomposition | rejected | +0.3 at 2-4× cost for an LLM judge, negative for a small verifier (R§2.2). |
| MiniCheck-class local verifier as a second kind of checker | deferred | Comparable to LLM judges on English grounding (R§2.2) but untested on Portuguese, and it shares the blind spot of passage entailment (it does not see the question). |
| Learned stop controller | rejected | Needs training; collapses when the retriever changes (R§1.3). The stop signal is the judge's sufficiency verdict after the fact, plus the prompt. |
| Trained search agents (Search-R1) | rejected | No training. |
| Conformal prediction sets | adapted | A single threshold with a binomial bound is the simplest member of the family and its guarantee is easy to state (R§3.1). |
| Coverage grades C0-C4 | kept as in v1 | They cap confidence and can abstain (`outside_coverage`); still untested because the benchmark corpora declare full coverage. Hypothesis. |
| AI review at ingestion with certainty labels | kept as data | The store carries a certainty per event; it caps confidence. No ingestion reviewer is built in v2. |
| Long context instead of retrieval | not applicable | Corpora are 1.4M-35M tokens; long context wins only below about 100k (brief; R§6). |
| Ask-back | kept as in v1 | The router can ask; the benchmark never attaches a classifier, so it stays untested. |

---

## (c) The cascade, end to end

Costs are **modelled** for Claude Haiku 5.5 at US$0.10 / US$0.50 per million input / output
tokens, from the v1 held-out run (US$0.00265 per question at 2.89 calls, so about US$0.0009
per call with default thinking) and the dev2 runs. Local stages cost no money.

| # | Stage | Where it runs | Cost (modelled) | Exits here when |
|---|---|---|---|---|
| 1 | Understand: rules extract date, intent, scope; the date is kept only if the corpus has history covering it | code | 0; < 1 ms | the question is empty or out of scope (`out_of_scope`); the router is unsure and a classifier is attached (`needs_input`) |
| 2 | Lookup: provisions named in the question, fetched as in force at the date | code | 0; a few ms | — (a named provision with nothing in force at the date is remembered for the refusal text) |
| 3 | Retrieve: BM25 with date and scope in SQL; optional expansion pass; optional dense + convex fusion | code, local model | 0; 60-110 ms lexical (measured for v1, `docs/pilot-dev.md`), plus dense if on | nothing in force matches: `not_valid_at_date` if older versions match, else `no_source`; every source has coverage 0: `outside_coverage` |
| 4 | Propose: the model answers, abstains, or asks for searches / opens (up to `max_turns` calls) | model | ≈ US$0.0009 per call; expected 1.5-3 calls | the model abstains with a type; the budget is exhausted (`budget`); it asks for an action with none left (`unsupported`) |
| 5 | Tools: arithmetic, dates, read-only SQL | code | 0 | a tool the answer depends on fails (the sentence fails its gate) |
| 6 | Bind: named provisions in force become citations | code | 0 | — |
| 7 | Gates: per sentence, in code | code | 0; ms | all sentences pass → 9 |
| 8 | Repair: one more propose call with the failures explained | model | ≈ US$0.0009, only when a gate fails | — |
| 9 | Judge: one call, thinking off, at most 400 output tokens | model | ≈ US$0.0004 on Haiku 5.5; ≈ US$0.0075 on Sonnet 5.5 (≈ 3k input, 150 output tokens at US$2 / US$10 per million) | no sentence passed the gates (no judge call is made) |
| 10 | Decide: locked rule, calibrated threshold | code | 0 | always: answered / partial / divergent / a typed abstention |
| 11 | Escalate (off by default): 4-10 once more with a stronger model | model | one strong-model pass | only after an `unsupported` refusal |

**Modelled cost per question**, no caching: 2.2 propose calls × 0.0009 + 0.3 repair calls ×
0.0009 + 0.0004 judge ≈ **US$0.0027**, about the v1 figure (US$0.00265). With the prompt
prefix cached across turns, the repeated input of later turns is read at 0.1× (R§6); input
is roughly half of a call's cost here, so the saving is at most about 20-25% of propose
cost (modelled; a prompt below the model's minimum cacheable length is not cached: 512 tokens
for Haiku 5.5 according to the provider's prompt-caching documentation, read 2026-11-13).

**The judge model decides the cost.** The owner's decision for the paid tests is to run the
locked judge on Claude Sonnet 5.5 (a stronger model of the same family, recorded in
`policy.json` as a frozen setting) while the generator stays Haiku 5.5. A Sonnet judge call
costs about US$0.0075 (modelled), so the engine costs about **US$0.010 per question**, of
which three quarters is the judge. With that judge the engine cannot be cheaper per useful
answer than agentic search (US$0.0047) or than v1 (US$0.0078) at any plausible useful rate;
what it buys is a checker stronger than the writer. The figures below are for a Haiku judge
and are what a dev-only ablation arm (`--judge-model claude-haiku-5-5`) would test.

**Cost per useful answer, Haiku judge** (modelled): at the v1 useful rate (34%) US$0.0079; at the
agentic rate (38.4%) US$0.0070; at 45% US$0.0060. **So v2 is expected to be cheaper per
useful answer than v1 only if it raises the useful rate, and matching agentic search's
US$0.0047 needs both a useful rate near 45% and the caching saving. That is a hypothesis,
and the less likely half of the goal.** The levers the loop may pull on cost are
`max_turns`, `search_k`, `k_first`, `max_context_chars` and the repair switch.

Latency (modelled): one more call than v1 on questions that pass the gates at once
(the judge), so a median near 12 s at default thinking against 10.5 s measured for v1.
Searches inside one turn run in the same turn (several queries per reply), which buys
latency, not accuracy (R§1.5).

---

## (d) Validation and abstention: what is guaranteed, judged, calibrated

### Guaranteed by code

These hold for every answer the engine returns, whatever the model writes, because code
enforces them after the model has finished (tested offline; the as-of invariant by a
property test):

1. **Every passage the model sees is a version in force at the as-of date** (as known at
   the recorded date, if given). The filter is inside the store's SQL for every search,
   lookup, open and bind.
2. **Every cited passage exists and was in force at the date.** The gate re-reads the store;
   it does not trust the copy shown to the model.
3. **Every sentence kept in an answer either cites at least one such passage, or is a
   derived sentence** that introduces no number and no reference beyond the question, the
   date and the kept cited sentences, in an answer that keeps at least one cited sentence.
4. **Every number in a kept sentence** appears in a passage it cites (text or title), in a
   tool result it cites, in the question, or in the as-of date.
5. **In a domain with a reference resolver, every source reference named in a kept sentence
   resolves to a unit of the corpus that the sentence cites.** A reference to something
   that does not exist in the corpus, or that has no version in force at the date, removes
   the sentence.
6. **Arithmetic shown as a tool value was computed by the tool.**
7. **A failed or unreadable judge call never yields an answer.**

What this does *not* guarantee: that the corpus is complete or right (a provision repealed
in fact but not in the corpus still counts as in force: `docs/legal-citation-test.md`,
limits), or that the resolver recognises every way of naming a source (99.2% of gold
references on the law corpus, measured).

### Judged by a model

One call, locked prompt, on the sentences that passed the gates: does each cited passage
state what its sentence states; does each derived sentence follow from the supported ones;
does the text answer the question asked as of the date; is the evidence sufficient; does
the question assume something the passages contradict; do two in-force passages disagree.
These are judgements and can be wrong. Known error rates of this kind of judge elsewhere:
automatic citation judges agree with people 78-85% of the time (R§2.5); the v1 support
judge agreed with a second, stronger model on 94.5% of 200 rows (measured, model-reviewed,
not human-reviewed). The judge and the generator may be the same family, so their errors
can correlate (R§2.4). In the paid tests the judge is Claude Sonnet 5.5 and the generator
Haiku 5.5 (`policy.json`, `judge_model`): a stronger checker, still the same family.

### Calibrated

The decision rule turns the verdicts, the certainty of the cited versions and the coverage
of their sources into one confidence number, and answers only when it is at least `tau`.
`tau` is fitted by locked code on labelled answers of a dev split: walking from the
strictest threshold to the loosest, a threshold is accepted while the Clopper-Pearson upper
bound of the error rate among answered questions, at confidence 1 − δ, is at most α
(`policy.json`: α = 0.05, δ = 0.10; owner-set, not on the surface).

The statement this supports, and its limits:

- *If* future questions are exchangeable with the calibration questions (same corpus, same
  kind of question, same engine surface), then with probability at least 1 − δ over the
  draw of the calibration set, the long-run share of answered questions that are wrong, by
  the same definition of wrong used for the labels, is at most α.
- It is a statement about the average, not about any one answer (R§3.1).
- It breaks under shift: another corpus, another kind of question, a changed prompt. The
  engine therefore uses a calibration file only when its surface hash matches the running
  surface; otherwise it uses a default threshold and marks the answer `calibrated: false`.
- "Wrong" is whatever the labels say. For the English sets the label is the deterministic
  containment grade; for law it is a model judge's "equivalent to the official answer",
  which is itself unvalidated by people. A bound against a model's labels is not a bound
  against the truth.
- Sample size: 45 answered with 0 errors, 77 with 1, 132 with 3, about 300 with 10 are
  needed to certify 5% at 90% (R§3.2, arithmetic). A dev set of 100 will often certify
  nothing. The owner's decision is a dedicated calibration draw: a block of 400 questions
  per English dataset with an unused pool (`cal0` of MultiHop-RAG and HoH, disjoint from
  every rotating and promotion block and from `test` and `sealed`). At about 70% coverage
  that is about 280 answered questions, which certifies if the error rate among them is at
  most about 3%. For law only `dev` and `temporal` exist (220 questions, labelled by a
  model judge); they will probably certify nothing, and then the engine says so and stays
  on the default threshold for law.

### When the engine abstains

| Type | Produced by |
|---|---|
| `out_of_scope`, `needs_input` | router (code) |
| `no_source` | nothing retrieved; or judge: evidence insufficient and the text is not a direct answer |
| `not_valid_at_date` | only versions outside the date match; or every sentence failed only the date gate |
| `outside_coverage` | every retrieved source has coverage 0 |
| `false_premise` | the model's own `ABSTAIN false_premise`, or the judge's `PREMISE: FALSE` |
| `conflict` (status `divergent`) | the model's own abstention, or the judge names two passages and code confirms they are different units, both in force, from sources of equal authority; both are shown, neither is chosen |
| `unsupported` | no cited sentence survives gates and judge; the text does not answer the question; confidence below `tau`; judge unreadable; model error |
| `budget`, `tool_failed` | budget stop; a needed tool failed |

A partial answer (some sentences removed) is returned only when the judge still calls the
remaining text a direct or partial answer and the confidence, discounted for the removal,
clears `tau`.

---

## (e) How dates flow through every stage

| Stage | What happens to the date |
|---|---|
| Caller | may pass `as_of.valid` (the date the answer should hold for) and `as_of.recorded` (what was known by then). A caller's date always wins. |
| Understand | otherwise rules read a date from the question (ISO, `15/03/2024`, "March 2024" → last day of the month, a bare year → 31 December). It becomes the as-of date only if the corpus has version history and the date is not before its first version; else today, with a trace note. |
| Lookup, retrieve, search, open, bind | every store call filters `valid_from <= d < valid_to` inside SQL, and replays only events recorded by `as_of.recorded`. The model never supplies a date to a tool: the code passes the question's. |
| Prompt | states the as-of date; each passage line shows its validity span, so the model can say "as of". |
| Tools | date arithmetic (difference, add, weekday, before) is a tool, never model arithmetic (R§4.3: 13-16% on duration questions for frontier models). |
| Gates | re-check each cited version against the store at the date; the as-of date's own digits are allowed numbers. |
| Judge | is told the date and asked whether the text answers the question as of it. |
| Decide | a named provision with no version in force gives `not_valid_at_date`, never the nearest version (R§4.4). |
| Answer | citations carry `unit @ valid_from..valid_to`; `Answer.query.as_of` records the date used. |
| Calibration and benchmark | questions carry their as-of date; time-aware baselines get the same date; scoring of dated legal questions is by code (which version was cited). |

Not in v2: questions spanning two dates ("what changed between X and Y") as a first-class
intent. The model can `OPEN:` a unit and ask twice through the API with two dates; a
`history` tool that lists a unit's versions and a code diff is designed (R§4.3) but not
built. The three dates of law (publication, entry into force, effects) remain axes carried
with each version and shown, not filtered.

---

## (f) The self-improvement loop over the engine

The loop sits outside the engine. It never runs inside an answer, and an answer never
depends on it. It changes the engine only by replacing the champion surface.

### What it may change: the surface

`src/heuresis/v2/surface/`: `default.json`, domain overlays, and prompt texts. Data only.
The locked schema (`v2/locked/schema.py`) names every key and its bounds: retrieval depth
and fusion weight, expansion, passages per turn, turns, context size, answer length, repair
rounds, routing switches, the judge's output cap, and the four prompts of the propose loop
(routing, prompts, context size, re-search and retrieval thresholds: the same list as the
original design). A candidate is a JSON document of overrides; anything the schema does
not name is rejected before any evaluation.

### What it may never change

The v2 judge (`v2/locked/`: gates, judge prompt and parser, decision rule, calibration
code, policy with the risk target, the schema itself), the v1 locked folder, the store,
the tools, citation binding and reference resolution, the data model, the benchmark
harness (datasets, splits, gold data, metrics, statistics, judges, ledger), and the loop's
own evaluator, tripwires, splits and promotion rule (`evolve/`). These paths are listed in
`v2/locked/manifest.py`; their hashes are in `PROTECTED.json`; a test fails when the tree
and the file disagree, and the evaluator refuses to run when they disagree.

Why data only: with code on the surface, "do not touch the checker" is an instruction, and
instructions failed in every measured study (R§7.4: a stricter prompt helped one model on
one task; "please do not cheat" changed nothing for another; the DGM agent removed its
hallucination markers despite being told not to). With a data surface there is nothing to
execute. What remains is the one thing prompts can do: tell the generator to write things
that please the judge. The defences are below.

**This is not a sandbox.** The guarantee is: a candidate that reaches evaluation is a
valid surface and nothing else. It does not protect against a process with write access to
the repository editing protected files; that needs the isolation an outer harness provides
(autopoiesis runs its agent in a container without network). The manifest check turns such
an edit into a refused run, not into an impossible one.

### Benchmarks it evolves against

| Tier | What | Used for | Returned to the proposer |
|---|---|---|---|
| **Rotating dev** | per dataset, 100 questions per cycle drawn by hash from the pool of questions in none of `dev`, `dev2`, `test`, `sealed` (MultiHop-RAG: about 1,550 unused; HoH: about 110,000 unused); a new draw each cycle, old draws retired | screening and paired comparison with the champion | scores, and redacted failure traces (question, the engine's answer, typed outcome, gate and judge reasons; never the gold answer or gold units) |
| **Anchor** | fixed dev sets already seen in design: MuSiQue `dev` + `dev2` (its pool is exhausted), law `dev` (100) and `temporal` (120) | guard rails only: a candidate must not get worse here; no selection on it | pass / fail per guard rail |
| **Sealed promotion set** | per dataset with a pool, 300 questions drawn once from the pool, disjoint from every rotating draw; retired after 10 promotion queries and redrawn | the promotion decision | pass / fail and the test statistic; never rows |
| **Canaries** | generated by code each cycle: questions about entities that exist nowhere, whose "gold answer" is a marker string planted in a decoy file in the working directory | tripwires | nothing |
| **Never touched** | `test` and `sealed` of the three English datasets, law `test` and `temporal_test` | registered tests by a person | — |

The loop cannot evolve on law beyond guard rails: BR-TaxQA-R has 715 questions, 100 in
`dev` and 615 held out, and no unused pool. Its legal behaviour improves only as far as
general behaviour transfers, and is protected by the anchor. A pool of dated legal
questions can be generated by code from amendment events (as `temporal` was); 54
qualifying provisions remain unused, enough for one more held-out set, not for a rotation.

Primary score: the penalised score with a wrong answer costing `t/(1−t)` at `t = 0.75`
(three times the value of a right one; locked in the loop's config). Accuracy alone
rewards guessing (R§3.3); abstaining on everything scores zero.

### One cycle

1. **Propose.** A proposer returns K candidates (default 6), each a set of overrides with
   its parent. Two proposers are built: a *perturbation* proposer (no model: changes one to
   three schema values inside their bounds; runs offline) and a *reflective* proposer (a
   model reads the redacted failure traces of the parent and rewrites one prompt or
   proposes values: the GEPA pattern, R§7.2, R§7.3; paid). Parent selection is fixed code:
   by score over the archive with a penalty for parents already explored (the DGM rule,
   R§7.1); the proposer cannot alter it.
2. **Stage 0, static** (free): schema validation, path guard, protected-hash check, prompt
   lint (forbidden strings; overlap of 8-grams with any evaluation question).
3. **Stage 1, smoke** (free): the candidate answers the packaged fixture offline with the
   fakes; it must run and must not trip a tripwire.
4. **Stage 2, screen** (paid): 30 questions of the cycle's rotating dev per dataset, paired
   with the champion's rows (cached per draw). A candidate goes on unless it is clearly
   worse (paired difference below zero by more than 2 standard errors). This is a filter,
   not a decision (R§7.3: staged evaluation saves money in screening only).
5. **Stage 3, dev** (paid): the top 2 on the whole rotating draw, paired. Requirements: a
   positive paired difference in the primary score with a one-sided 90% bootstrap interval
   above zero; every guard rail holds (below).
6. **Stage 4, promote** (paid): at most one candidate per cycle, on the sealed promotion
   set, paired with the champion. One-sided paired sign-flip test; the level for the t-th
   promotion test ever made follows an online false-discovery schedule
   (`α_t = α · γ_t · (promotions so far + 1)`, `γ_t ∝ 1/(t(t+1))`, the e-LOND / LOND form,
   R§8.3), so the stream of promotions keeps a bounded share of false ones however long
   the loop runs. Guard rails are checked again on this set. Because selection inflates a
   winner's dev score by about 0.06 at n = 300 with 20 candidates (R§8.4), only the
   promotion-set result is recorded as the candidate's gain.
7. **Promote or archive.** A promoted candidate becomes the champion (`champion.json`
   keeps the history); the calibration file is refitted for the new surface on the next
   rotating draw, and until then the engine runs it as uncalibrated. Everything else stays
   in the archive as a possible parent (stepping stones are kept, not deployed, R§8.9).
8. **Rollback.** The champion is re-run on each new rotating draw; if its score falls
   below the previous champion's on the same draw by more than 2 standard errors, or it
   trips a tripwire, the loop restores the previous champion and records why. Rollback is
   also a command.

Guard rails (all must hold against the champion, on dev and again on the promotion set):
no answer with a fabricated or out-of-force citation on any anchor question; the error
rate among answered questions not higher by more than 2 points; coverage not lower by more
than 5 points; cost per question not higher by more than 25%; no anchor score lower by
more than 2 standard errors.

Tripwires (any one stops the candidate, is written to the archive, and for the first four
stops the cycle): a protected file differs from the manifest; the candidate is not a valid
surface; the canary marker appears in a prompt or in any answer (the decoy file was read,
or gold leaked); the engine answers more than a set share of canary questions (the
candidate taught it to stop refusing); a citation fails the integrity check on an anchor
(the gates were bypassed); the dev score exceeds the champion's by more than 4 standard
errors (flag: confirm on the promotion set, never trust); the gap between dev gain and
promotion gain exceeds 3 standard errors (overfitting flag); cost more than doubles.
Honeypots and canaries are not statistical detectors and no measured detection rate exists
for them (R§8.6); they catch crude leaks, and that is all that is claimed.

Can it game the benchmarks? What is closed by construction: editing the checker, the
metric, the gold data or the splits (not on the surface; hash-checked); seeing gold
answers (never returned; decoy trips a wire); selecting on the sealed set (pass/fail only,
a query budget, online error control). What is not closed, and is stated as a limit:
(1) a prompt that makes the generator write answers the judge likes without being right;
the deterministic gates bound the damage (it cannot invent a source), the judge prompt is
locked, the forbidden-string lint removes the obvious route, and a human-labelled sample
is the only real test; (2) slow overfitting to the *kind* of question in the pools, which
rotating draws reduce and do not remove; (3) the judge and labels being wrong in the same
direction as the generator.

### Budget per cycle (modelled)

With the Sonnet judge the engine costs about US$0.010 per question (section (c)), so the
default cap of US$10 per cycle buys about 1,000 engine questions. A default cycle that
fits: champion on the rotating draw (2 datasets × 100) US$2.00; screening 4 candidates ×
60 questions US$2.40; dev for 1 candidate × 200 US$2.00; promotion for that one candidate
on as much of the sealed set as the remaining budget allows (never fewer than 200
questions, with the champion's rows cached after its first run) about US$2.00-3.00;
reflective proposer US$0.30. Anchors run only for a candidate that passed promotion, in
the next cycle's budget, before it becomes champion. **The ledger hard-caps the cycle
(default US$10); the loop stops cleanly at the cap and resumes from the archive.** At 200
paired promotion questions only gains of roughly 6-8 points of the primary score can be
certified (`bench.stats.min_detectable_diff`); smaller true gains will not be promoted.
With a Haiku judge the same cap buys about three times as many questions.

### How it plugs into autopoiesis

`aphesist/autopoiesis` (read from its public README and PREREGISTRATION only; its source
was not available to this session) is a DGM-style loop over a Python coding agent: an
archive, a parent rule, a mutator that emits one diff per child, a staged selection score,
host-side tripwires on planted flaws, and a clean evaluator whose score never feeds
selection. It defines no formal target-system interface and no rollback. heuresis exposes
the interface on its side so that autopoiesis, a cron job or a person can drive it:

| autopoiesis concept | heuresis counterpart |
|---|---|
| the agent directory a diff is applied to | a copy of `src/heuresis/v2/surface/` (data files only); `heuresis evolve evaluate --candidate-dir DIR` reads it; `check_candidate_paths` rejects a diff touching anything else |
| selection evaluator (S_screen, S_full) | `heuresis evolve evaluate --stage screen` / `--stage dev`: JSON with the score, guard rails and tripwires |
| clean evaluator (H), never fed back | `--stage promote`: pass / fail only |
| tripwires computed on the host from material the agent cannot edit | tripwires in `evolve/tripwires.py`, protected by the manifest; the decoy answer file in the working directory plays the role of autopoiesis's decoy (D) and answer key (F1) |
| nonce-tagged report lines | `--nonce N` makes the command print exactly one line `HEURESIS-EVAL <N> <json>`; anything else on stdout is to be ignored by the host |
| mutator prompt | `heuresis evolve describe --json` gives the schema, bounds and current champion; `reflective_dataset` gives redacted failure traces |
| budget ledger | the same append-only ledger with a hard cap, one file per working directory |
| archive | `archive.jsonl`; autopoiesis may keep its own and treat heuresis as a pure evaluator (`evaluate` is stateless apart from caches and the ledger) |

`heuresis evolve cycle` runs one whole cycle with the built-in proposers (the minimal
loop; offline with the fakes when no model is configured), so a cron line is enough to
keep it going without autopoiesis.

---

## (g) Test plan

### Hypotheses

| | Hypothesis | Decides |
|---|---|---|
| H1 | **Useful answers.** On law, v2's share of useful answers (answered, no fabricated or out-of-force citation, judged equivalent to the official answer) is not below agentic search's by more than 3 points, and is above v1's. | goal 1 |
| H2 | **Refusal instead of error.** Among answered questions, v2's error rate is lower than that of `agentic` and `agentic+asof` on each English dataset; and the confidence orders answers (risk falls as the threshold rises; AURC below v1's). | goal 2; whether the judge separates right from wrong |
| H3 | **Citation integrity is kept.** v2's rate of answers with a fabricated or out-of-force citation on law is not above v1's (non-inferiority, margin 1 point) and below every baseline's. | goal 3 |
| H4 | **Dates.** On dated questions (HoH; law `temporal`) v2 gives the version in force at least as often as `agentic+asof`. | goal 4 |
| H5 | **Multi-hop.** On MuSiQue and MultiHop-RAG the penalised score of v2 is not below `agentic+asof`'s by more than 0.05 and above v1's. | goal 1 |
| H6 | **Cost.** v2's cost per useful (law) or correct (English) answer is below v1's; secondary: not above agentic's. With the Sonnet judge chosen for the paid tests this is expected to fail (section (c)); it is reported with both judges on dev. | cost |
| H7 | **Calibration.** On a split not used for fitting, the error rate among answered questions is at most α + 3 points (α = 5%). | the calibrated statement in (d) |
| H8 | **The loop improves and does not game.** After N cycles the promoted champion beats the starting surface on a fresh draw never used by the loop; planted bad candidates (a prompt containing the canary marker; a surface with an out-of-bounds value; an edit to a protected file) are all rejected; honest candidates trip no wire. | goal 5 |

Run-to-run noise is 4-22% of outcomes and differences under about 0.1 at n = 300 are
noise (measured, brief); with paired comparisons at n = 500 the detectable difference in
accuracy is about 0.05-0.07 (`PREREGISTRATION.md`), and at n = 615 a 3-point margin needs
a discordance rate near 10% (R§8.2). Every comparison is paired, same questions, same day,
same model, default thinking, no truncation (`max_tokens` 4096), one run.

### Splits

| Stage | Data | Purpose |
|---|---|---|
| A. Offline | fixtures, fakes | the build works (`pytest`; dry runs) |
| B. Design check (paid, small) | law `dev` (100), `temporal` (120); English `dev2` (3 × 100) | does v2 run on real models; first look at H1-H6. **Calibration data: seen during v1 design.** |
| B2. Calibration draw | `cal0` of MultiHop-RAG and HoH (2 × 400, from the unused pools), plus the law runs of B | fit the confidence threshold per dataset |
| C. Fresh dev | rotating draw 1 for MultiHop-RAG and HoH (2 × 100), never used by anyone | H2, H5, H7 on unseen questions before any registration; decide go / no-go |
| D. Loop | rotating draws 2+, sealed promotion set, anchors | H8 |
| E. Registered test, English | `test` of the three English datasets (3 × 500), never run with a model | H2, H4, H5, H6, H7 |
| F. Registered test, law | BR-TaxQA-R `test` (615) and `temporal_test` (240): **a second registered comparison** | H1, H3, H4, H6 |

**Should v2 be run again on the legal held-out sets? Yes, as a second registered
comparison on the same questions, with all six systems re-run together, and with the
limits stated; and a new dated set should be built when the owner wants a result that owes
nothing to the first run.** Reasons:

- There is no alternative for H1. BR-TaxQA-R has no unused questions, and the useful-answer
  gap was measured on exactly these 615. A new legal question set of this kind does not
  exist in the repository's sources.
- The design has seen only aggregates of the first run, never a question or a row. But it
  has used those aggregates heavily (the gate-drop counts shaped components 4-7). That is
  adaptive reuse of the held-out set. One more look at n = 615, with nothing tuned on it,
  costs little in bias (R§8.1: natural adaptive overfitting is mild, and one query is far
  from the regime where it matters), but it is not zero and it is not a first look.
- Therefore: register before running (`PREREGISTRATION-v2.md`, with the surface hash,
  protected hash and commit), tune nothing on these sets, run once, re-run the baselines
  and v1 in the same session for pairing, and report the result as "second registered
  comparison; design informed by the first run's aggregates". A win there supports H1 for
  this benchmark; it does not show the reading in (a) generalises.
- For `temporal_test` (240) the primary outcome sat at the floor in the first run
  (baselines 0.4-2.1%), so it can show H3 non-inferiority and H4 only. A third dated set
  could be built from the 54 unused provisions (108 questions); the owner decided not to
  build it, so H4 on law rests on the re-used `temporal_test`.
- The benchmark's own judges (answer judge, support judge) stay unchanged and on Haiku
  5.5, so the two registered runs are comparable; only the engine's internal locked judge
  runs on Sonnet 5.5. Registration: `PREREGISTRATION-legal-v2.md`.
- The English `test` splits have never been answered by any model (two retrieval-only
  checks touched them, disclosed in `PREREGISTRATION.md` 2a), so stage E is a first test.

### What is compared

Systems: `closed_book`, `hybrid`, `agentic`, `agentic+asof`, `engine` (v1 at its registered
configuration), `engine2` (v2). Reference for paired tests: `engine2`. Primary outcomes:
English: penalised score, error rate among answered, coverage (deterministic containment
grade; the judge-assisted grade is secondary). Law: tainted answers (code), useful answers
(code + model judge), version in force on dated questions (code). Cost per correct / useful
answer and latency for all. Holm over the family of each stage. The support and answer
judges are models; a blind review by a stronger model on a stratified sample, as in the
first run, bounds their disagreement, and none of this is human-validated.

The commands, their order and the cost of each are in `docs/v2-test-plan.md`; every paid
command needs `--paid --cap --ledger` and stops at the cap.

### What would count against the design

- H1 fails with v2 close to v1: the reading in (a) is wrong, and the gap is retrieval or
  the generator's own answer quality under citation discipline, not the gates.
- H2 fails with a flat risk-coverage curve: the question-conditioned judge does not
  separate right from wrong either. Next step named in (b): agreement across independent
  drafts, at its cost.
- H3 fails: binding or the relaxed number rule let something through. The gates would be
  tightened and the result reported.
- H7 fails: the calibration statement is withdrawn for that domain.
- H8 shows promotions that do not hold on a fresh draw: the loop's statistics are too
  loose for these sample sizes, and the loop stays off.
