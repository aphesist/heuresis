# Pre-registration: the legal citation-integrity test (`brlaw`)

Status: **proposed for registration; not yet frozen.** It becomes registered when the orchestrator tags the commit that adds this file.
Every number below is copied from the file named next to it. Values marked **[proposed]** are choices made here, not measurements.
This registers a study that is separate from `PREREGISTRATION.md` (the Wikipedia/news benchmark); nothing in that document is changed.
The registration is written **before any system has seen the held-out questions**.

## 1. Claim

On Brazilian federal law, the `engine` (heuresis with the legal settings of section 3) **does not present a reference to a provision that does not
exist in the corpus or that was not in force on the question's date**, while the four standard approaches (`closed_book`, `hybrid`, `agentic`,
`agentic+asof`) sometimes do. This is the claim the primary outcome (section 4) tests.

A second question is asked but **is not a claim**: do the provisions the engine cites support its sentences as often as the baselines' citations
support theirs? On dev, as judged by the benchmark judge (a model), the engine's share of supported references was 75.9 % (195/257) on BR-TaxQA-R `dev`
and 94.7 % (179/189) on `temporal` (`results/brlaw/phaseC/analysis_c.json`), against 25 %, 79 %, 86 % and 84 % for `closed_book`, `hybrid`, `agentic`,
`agentic+asof` on dev (`results/brlaw/NOTES.md`, Phase B). **The engine is not expected to exceed the best baseline (`agentic`, 86 % on dev).** Support is
registered as a two-sided secondary comparison (section 6), not as a claim.

## 2. Data

**Held-out questions** (built by code; none was read, and no system has been run on any of them):

| Set | Questions | Id-list sha256 | Source | As-of date |
|---|---|---|---|---|
| BR-TaxQA-R `test` | 615 | `ae73379dae98793769efbfa971ed4c5e28e570770d956d8c6687e124a06fbeda` | `unicamp-dl/BR-TaxQA-R`, revision `9f0f4263928c6152a40f888da3e63375a24bb0f3` (CC BY 4.0), official answers and article-level gold references; split by `sha256(20261112:id)`, the first 100 are `dev`, the rest `test` | 2024-12-31 (end of exercício 2024; the dataset's cited acts go to July 2024) |
| `temporal_test` | 240 (120 provisions x before/after a change) | `1b46b7a35f9b619b3aaceca88b68e02aacb47e3ecf4b2fa4523ecde73a3ede49` | built by `bench/brlaw.temporal_questions` from the 120 provisions selected out of the 174 qualifying version candidates that the design split `temporal` did not use (cap 120, same rule) | the day before and the day of each change |

Both hashes are in `data/corpora/brlaw-core-t/MANIFEST.json` (copy to be committed under `results/brlaw/prereg/manifest_core_t.json`).
`dev` (100 questions, hash `bc7d55c5cfc963d158e35251a03d5786d1c3d5d842784b3cd6bea3f2bf8e89d2`) and `temporal` (120 questions, hash
`2e8a312a56c10cedada763b42b0bbd0d2ac26a251adeb407b1a1fe20906e1e58`) are the **design** splits.

**Prior contact, stated honestly.** The design splits were used to build and change the system: phase A (free offline checks, including BM25 and hybrid
recall of gold provisions on `dev`), phase B (the five systems on `dev` and `temporal`) and phase C (the engine with the support gate and the second
drafting instruction, once, on `dev` and `temporal`) are in `results/brlaw/NOTES.md`. The support gate and the drafting instruction v2 were chosen
because phase B showed the engine's sentences were less supported than the baselines'. The held-out sets were built by code and never read or run.
`temporal_test` shares its base norms (the CLT, Lei nº 7.713/1988) and its sources with `temporal`; BR-TaxQA-R `test` shares the corpus and the document
collection with `dev`. A test question whose answer lies in a text the design split also used is not independent of that text.

**Corpus.** `brlaw-core-t` = the corpus `brlaw-core` of phases A to C plus the 120 held-out provisions' 240 versions (manifest:
`data/corpora/brlaw-core-t/MANIFEST.json`, `results/brlaw/manifest_core.json` for `brlaw-core`). Both held-out sets run against this one store. Phase B
and C ran on `brlaw-core` without those units; the difference is 120 units in about 64,800. Counts (`brlaw-core-t` manifest, tokens = characters / 4):
tax tier 421 norms, 11,072 units; federal tier 6,552 norms, 53,573 units (norms dated 1995-01-01 or later and the Constitution); versioned tier 60
units; held-out versioned tier 120 units; 14,432,544 tokens in all. Manifest file hashes (sha256): `sources.jsonl`
`3f35864f0f59d6c619350dae0057bb356692233c400039f24309fd45202867ee`, `units.jsonl` `279b46a335b6582a4eb3376000c722b531461bc3e7756be94d856c4c324c676a`,
`events.jsonl` `1ad381cdadfae6bc20fa7ce998ff66525004e2da67cbf81ad942c7a8c9957a55`, `questions.jsonl`
`272e1425871da4ff92746119d6d7eefe00158840415558ddf7f3fe056c739d06`. The existence and in-force checks of the metric run against the **full** corpus
(`brlaw` plus the held-out versions; 29,353 norms, about 220,800 units; `results/brlaw/manifest_full.json` for the phase A/B build).

**What is in and out.** In: federal leis ordinárias, leis complementares, decretos-lei, leis delegadas, emendas constitucionais and the Constitution
(from `ctresb/leis`, commit `c9f21b4ab11aa0d7ca6fe861d75028e94219c2d6`) and the legal texts shipped with BR-TaxQA-R (decretos, instruções normativas,
atos declaratórios, pareceres, soluções de consulta, 421 norms). **Out: decretos not in BR-TaxQA-R's files, medidas provisórias, resoluções, all
state and municipal law, and court decisions.** Coverage against the Senate's own lists for sampled years (`results/brlaw/coverage_vs_senate.json`):
leis ordinárias 95.2 % to 99.4 %, decretos-lei 96 % to 100 %, leis complementares 67 % to 100 % (few norms per year). **No norm type is covered
completely.** 29 tax texts of articulated types are stubs (no article could be read); 4 were replaced by the federal copy and 25 are flagged
(`results/brlaw/NOTES.md`).

**Limits of the versioned tier.** 60 design provisions (54 CLT, 6 Lei nº 7.713/1988; 47 replaced and 13 repealed) and 120 held-out provisions, all from
the same few base norms; the later wording is the Câmara portal's compiled text, not diffed against the amending act; several changes are small
(spelling). Only for these provisions is "in force" exact: for the rest of the corpus the source holds one version per unit, and most federal norms
are original publications with no later amendment (2,243 of 29,040 are compiled texts).

## 3. Systems (frozen)

Five systems, one run each: `closed_book`, `hybrid` (k = 8, retrieval as of today), `agentic` (k = 5, at most 4 searches, as of today), `agentic+asof`
(the same, searching as of the question's date), `engine`. Generator `claude-haiku-5-5`, thinking left at the default, `draft.max_tokens` 4096, no
temperature (the model rejects it). The engine: legal prompt v2, `verify.support = "llm"`, `answer.mode = "search"` (up to 4 searches, 5 passages each),
`decide.mode = "grade"`, `references_traced` on, `draft.max_sentences` 3, `max_context_chars` 24,000, no reranker (`results/brlaw/phaseC/c-dev/manifest.json`,
`engine_config`). Models: embedder `onnx:intfloat/multilingual-e5-small` (onnx sha256 `ca456c06…8665`), reranker `onnx:cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
(`3e9a03ed…487c`), entailer `onnx:MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli` (`79f8cda2…fa6e`), full hashes in `results/brlaw/phaseB/dev/manifest.json`.
The support model of the engine's gate is the same model with thinking disabled. Price table `anthropic-2026-11`.

Prompts, by sha256 of their text (the instruction constants of `bench/systems.py`, `support_llm.py`, `bench/citations.py`, `bench/judge.py`):

| Prompt | sha256 |
|---|---|
| `LEGAL_CLOSED` (closed_book) | `f12453657d919b7e05114ca35f8139a9298cf81391a00c51589b9a3c77a1357d` |
| `LEGAL_PASSAGES` (hybrid) | `177e3998d455235c5e605ca10fded72fbca4100c672e169321c2e39dbafb7e27` |
| `LEGAL_AGENT` (agentic, agentic+asof) | `b4079842a6cc69c962c5771d2b3f4723eac71452d1f79cd6fd9a8ab11323132d` |
| `LEGAL_ENGINE_SUFFIX_V2` (engine drafting instruction, appended to the engine's own) | `5b5ae5675cfdbdf6db2efcf07271a04fb2779d73efa8a41bd8cb9914a0ec0fbc` |
| `SUPPORT_GATE_SYSTEM` (the engine's own support gate) | `b5821484f4bdc730e852d407d93ef799a126c85da2dcb8a5d26b61644c8381a3` |
| `SUPPORT_SYSTEM` (the benchmark's support judge) | `ef1defd662c545aeb5a8666c7e2c5438112728669cfb3acfed25145796647be8` |
| `JUDGE_SYSTEM` (the answer-equivalence judge) | `9542c78c11cb886000e6a25b07aee5461058c3c892c2b8da39bbf10843172399` |

Other hashes: the English (Wikipedia/news) baseline prompts hash `c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b` and the default surface hash
`547d7f32387e2e4aff33eaa5ff39a388b52084f3680e54515ccc3d1433d878b3` are unchanged from `main`; the **locked hash** is
`f13783b57968b2b8b9313bb31d89f83aac1ea417520a9de70676aa890d52ad53`; the **legal engine configuration hash** (sha256 of the engine's effective configuration for a legal
dataset as sorted JSON) is `1a6c90d9d606ebe0ab09a47a1f17c6126fb9f480f7c7ab6ac3ba4a60929bbbd5`; the **legal engine surface hash** (that configuration, `DRAFT_SYSTEM`,
the source of `surface/prompts.py`, `LEGAL_ENGINE_SUFFIX_V2`, `SUPPORT_GATE_SYSTEM`, `LEGAL_FORMAT`) is `eb2e2c74b8ade4905851c73b404043bae69860fea5a649f5d6ef0398533ad100`.

## 4. Primary outcome and analysis

**Tainted answer.** A question's answer is *tainted* if it is answered and has at least one reference (a citation the resolver `legal_br.resolve_references` finds in the text, or a
unit the engine cites by mark) whose **norm is not found in the corpus, or whose article is not found in that norm** (*strict*), or which resolves to a
unit with **no version in force at the question's as-of date**. The strict rule counts every "norm not found", which may be a real norm outside the corpus
(sections 2 and 8); the **covered-only** variant counts it only for the types `LegalBRDomain.covers` lists (leis, leis complementares, decretos-lei, emendas
constitucionais dated 1946-2025) and does not count "article not found" inside a stub text. **The primary outcome is the strict one.**

**Per question, over all questions:** `tainted = 1` if answered and tainted, else 0; **an abstention is not tainted.** Because a system that always abstains
is never tainted, the answered share (coverage) is reported beside every tainted rate, and the rate over answered questions is reported too.

**Primary family: 8 paired comparisons** = the engine against each of the 4 baselines on each of the 2 held-out sets. Test: **exact McNemar** on the per-question
paired tainted indicators (two-sided); **Holm correction at alpha 0.05** over the 8. Effect: the per-question difference engine minus baseline with a paired
bootstrap 95 % interval (5,000 resamples, seed 20261112 **[proposed]**) and the discordant counts.

**Directional expectation, stated in advance:** the engine's tainted rate is lower than every baseline's on BR-TaxQA-R `test`. On `temporal_test` the differences
may be small: on `temporal` (design split) the baselines were 2 % to 8 % of answered rows (`results/brlaw/NOTES.md`), and the questions name the norm and article.
On BR-TaxQA-R `dev` the baselines were 10.5 % to 27.8 % (strict, of answered rows) and the engine 0 %. The engine's rate is partly its gate by construction
(`references_traced` removes untraced sentences before the answer exists); the claim is about what the user is shown.

## 5. Guard against "safe by abstaining": a co-primary non-inferiority check

A *useful* answer (BR-TaxQA-R only) is **answered, not tainted, and judged EQUIVALENT to the official answer** by the answer judge (`bench.judge`, the prompt of section 3,
run over every answered row). **Co-primary check: the engine's useful-answer rate is not worse than `hybrid`'s by more than 10 percentage points** (margin 10 points
**[proposed]**; one-sided paired bootstrap, 5,000 resamples, seed 20261112; non-inferior if the lower 95 % bound of engine minus `hybrid` exceeds -0.10). The same difference
is reported against every other system. Design-split values for orientation (judge-equivalent answers of 100, before the tainted filter): `closed_book` 24, `hybrid` 32,
`agentic` 35, `agentic+asof` 41, engine (phase C) 29. **The engine may fail this check against `agentic+asof` (and is closer to the margin against `agentic`); it is reported
either way.** The deterministic containment grader and the penalised score are **not used** (the official answers are paragraphs; `results/brlaw/NOTES.md`).

## 6. Secondary outcomes (two-sided, no correction, exploratory)

Support share by the benchmark support judge (supported / judged resolved, in-force references, with Wilson intervals; paired where both systems answered); the version in
force on `temporal_test` (the code-scored outcome of `bench/citations.temporal_outcome`) and how often a system gives the superseded wording; covered-only tainted;
"norm not found" against "article not found" against "not in force"; abstention rates; answers with no reference; cost per question and per useful answer; mean calls and
searches; median latency; the engine's gate drops by type (`references_traced`, `numbers_traced`, `exists`/`valid_at_date`, model support). The support comparison is a two-sided
secondary comparison (section 1), not a claim.

## 7. The judges, and human validation

**The support judge, the answer judge, the engine's own support gate and the generator are all `claude-haiku-5-5`.** The gate and the judge have different prompts (hashes in section 3)
but the same model family, so their errors may be correlated; agreement between them is not evidence of support. On the design splits the judge agreed with the gate's SUPPORTED
verdicts on 173 of 183 kept sentences (`results/brlaw/phaseC/analysis_c.json`), which says nothing about whether either is right. **Human validation:** the stratified CSV of the test run
(20 rows per system per split, `bench.citations --sample 20`) will be read by a person after the run; the agreement rate between the person and the judge will be reported. **If the judge's
verdict differs from the human's on more than 20 % of the rows, the support results are reported as unreliable** (the primary outcome does not use the judge). The answer judge is not
validated by a human sample here; the co-primary check that uses it is reported with that caveat.

## 8. Rules of the run, threats to validity

* One run: each system answers each held-out question once, on the frozen settings of section 3; nothing is tuned after registration; a stopped run is not restarted with other settings.
* If the ledger stops a run, only the questions completed by all five systems are analysed (complete cases), and the number is reported. API or model failures after retries are error rows;
  they count against the system (not answered, hence not useful, never silently dropped), are listed per system, and a system with more than 2 % error rows is flagged.
* Reproducibility: the resolver, the in-force check and the questions are deterministic; sampling of the model is the API default and cannot be set; repeat runs may differ.
* **Deviations log: empty at registration; entries are in the section "Deviations log" at the end of this file.**

Threats to validity: (1) **"norm not found" can be real law outside the corpus** (decretos, medidas provisórias, resoluções, state law, ~2 to 5 % of sampled federal norms missing; stub texts), which is why the
covered-only variant is reported; the strict primary outcome overstates fabrication for systems that cite real norms outside the corpus. (2) The versioned tier is small (60 + 120 provisions from a few base norms)
and "in force" is exact only there; elsewhere a repealed or amended provision may look in force. (3) The judge is the generator's family; support and equivalence results are model opinions. (4) One model, one run, one
domain; sampling not controllable. (5) The official answers are paragraphs, so correctness relies on the judge. (6) Dev and `temporal` were used for design, and the held-out sets share corpus and base norms with them.
(7) BR-TaxQA-R's references and answers were extracted by an LLM pipeline and its titles contain errors (e.g. a wrong year); the 546 questions that name an article are a subset. (8) The engine's tainted rate is partly
its gate by construction, and its abstention rate differs from the baselines'; the guard of section 5 is meant to expose a system that is clean only because it says little. (9) Everything here is Brazilian law as
a worked example; no claim extends to other domains or to legal advice.

## 9. Frozen items and budget

| Item | Value | File |
|---|---|---|
| Code commit | `c6fa97e3cf2e85cf3b238e00f375087a41fd7f0d` (branch `legal-citations`, the merge of `main` at `0808d15`; this file is added in the next commit) | git |
| Locked hash | `f13783b57968b2b8b9313bb31d89f83aac1ea417520a9de70676aa890d52ad53` | `heuresis hash`, `locked/guard.py` |
| Default surface hash | `547d7f32387e2e4aff33eaa5ff39a388b52084f3680e54515ccc3d1433d878b3` | `bench/systems.surface_hash` |
| Legal engine configuration hash / surface hash | `1a6c90d9…bbd5` / `eb2e2c74…d100` (full values in section 3) | computed from `BenchContext.engine_config()` |
| English baseline prompts hash | `c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b` | `bench/systems.prompts_hash` |
| Corpus and question manifests | section 2 | `data/corpora/brlaw-core-t/MANIFEST.json` |
| Held-out question id hashes | `ae73379d…beda` (test), `1b46b7a3…de49` (temporal_test) | the same manifest |
| Generator, price table | `claude-haiku-5-5`, `anthropic-2026-11` ($0.10 per million input tokens, $0.50 per million output tokens, prompts up to 100,000 tokens) | `src/heuresis/pricing.py` |
| Local models | section 3 | `results/brlaw/phaseB/dev/manifest.json` |

**Budget (owner-approved): ledger cap US$10.00 for the test run, margin 0.25.** Modelled cost from the measured per-question costs (phase B for the baselines, phase C for the engine; `results/brlaw/phaseB/*/analysis.json`,
`results/brlaw/phaseC/analysis_c.json`): on a BR-TaxQA-R-like question, `closed_book` $0.00066, `hybrid` $0.00099, `agentic` $0.00179, `agentic+asof` $0.00201, engine $0.00271, together $0.00816, so 615
questions cost about $5.02; on a `temporal`-like question $0.00047 + $0.00042 + $0.00181 + $0.00124 + $0.00108 = $0.00502, so 240 questions about $1.20. The support judge cost about $0.000136 per row in phase B
($0.15 for 1,100 rows): 4,275 rows about $0.58; the answer judge about $0.000086 per row ($0.0432 for 500 rows): 3,075 test rows about $0.27. **Modelled total about $7.1, which leaves about 30 % below the cap.**
Phase B and C spent US$1.629 and US$0.4527 (`results/brlaw/phaseB/ledger.jsonl`, `results/brlaw/phaseC/ledger-c.jsonl`). The test run uses one new ledger.

## Deviations log

| Date | Change | Reason | Data seen at the time |
|---|---|---|---|
| 2026-11-12 | The registered human validation of the support judge (section 7) is replaced, by the owner's decision, by a **blind review by a stronger model from the same vendor** (Claude Opus, via a subagent with no access to the judge's verdicts). This reduces but does not remove correlated errors with the Haiku judge and the Haiku support gate; results are labelled "model-reviewed, not human-reviewed". The registered rule (support results reported as unreliable if the reviewer and the judge disagree on more than 20 % of the sample rows) is applied to the reviewer. | The owner chose an independent reviewer agent instead of a person. | The held-out run was in progress; no held-out result had been looked at. |

| date | deviation | data seen |
|---|---|---|
| 2026-11-13 | The registered answer judge (`bench.judge`, section 5) was **not run** on the held-out splits: `src/heuresis/bench/judge.py` refuses any manifest split other than `dev`/`dev2` (a guard written for the older datasets), and the brief forbids changing `src/`. The co-primary non-inferiority check and the "useful answer" secondary outcomes are therefore **not evaluated** (reported as inconclusive). The support judge ran as registered. A first support-judge pass was cut by a client-side timeout I set and rerun in full (about 1,700 duplicate calls, under US$0.15, counted in the ledger). | Held-out run and support judge complete; the primary-family tables had been computed when this entry was written (the guard was met before any of them). |
