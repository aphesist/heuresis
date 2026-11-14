# Pre-registration (DRAFT): the second legal comparison, `engine2` on BR-TaxQA-R `test` and `temporal_test`

Status: **FILLED, awaiting the owner's freeze (tag) before any held-out run.** The placeholders were filled from command output on 2026-11-14; it becomes registered when the owner approves, commits and tags it.
Every placeholder is a value to be copied from a command's output, never guessed. Values marked **[proposed]** are choices made here, not measurements.
It follows `PREREGISTRATION-legal.md` (the first legal registration) in outcome definitions and statistics; nothing in that file is changed. The English `test` splits are registered separately in `PREREGISTRATION-v2.md`.
Companion documents: `docs/design-v2.md` (hypotheses H1, H3, H4, H6 in section (g)), `docs/v2-contracts.md`, `docs/v2-test-plan.md` (stage F: commands and cost).

## 0. Disclosure

**This is a second registered comparison on the same questions as the first** (`PREREGISTRATION-legal.md`, results in `results/brlaw/heldout/RESULTS.md`). The v2 design was **informed by the aggregate results of the first
run, never by its questions or rows**: the design reads the aggregates (tainted rates, useful-answer rates, gate-drop counts by type, cost per question) and nothing else from the held-out run. That is adaptive reuse of a
held-out set: the effect is expected to be small (one more query at n = 615, nothing tuned on the sets), but it is not zero and this is not a first look. A win supports the useful-answer claim **for this benchmark only**; it does not
show that the reading in `docs/design-v2.md` section (a) generalises. No new dated set is built for this registration (a third dated set from the 54 unused provisions is left as an owner decision). Nothing is tuned after registration.

## 1. Claim

On Brazilian federal law, `engine2` (the v2 engine at the frozen surface of section 3) (a) does not present a reference to a provision that does not exist in the corpus or that was not in force on the question's date at
a higher rate than the v1 `engine` (within 1 point) and at a lower rate than every baseline, and (b) gives a useful answer as often as `agentic` search (not below it by more than 3 points) and more often than the v1 `engine`.
The second question is exploratory and not a claim: support of its sentences by the cited provisions, as judged by the benchmark support judge.

## 2. Data

| Set | Questions | Id-list sha256 | Source |
|---|---|---|---|
| BR-TaxQA-R `test` | 615 | `ae73379dae98793769efbfa971ed4c5e28e570770d956d8c6687e124a06fbeda` | `data/corpora/brlaw-core-t/MANIFEST.json` (`questions.splits.test.ids_sha256`); equals the first registration's value |
| `temporal_test` | 240 | `1b46b7a35f9b619b3aaceca88b68e02aacb47e3ecf4b2fa4523ecde73a3ede49` | the same manifest (`questions.splits.temporal_test.ids_sha256`); equals the first registration's value |

Corpus, as-of dates, scope and limits: exactly as `PREREGISTRATION-legal.md` section 2 (corpus `brlaw-core-t` for both sets; existence and in-force checks against the full corpus). Corpus manifest file hashes (`data/corpora/brlaw-core-t/MANIFEST.json`, `files`): `edges.jsonl` e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855; `events.jsonl` 1ad381cdadfae6bc20fa7ce998ff66525004e2da67cbf81ad942c7a8c9957a55; `provisions.json` 1f95b4160bf2a895c4e0d08c458cdf7c2ae396fe4a7dfafc47892b3057ceff11; `questions.jsonl` 272e1425871da4ff92746119d6d7eefe00158840415558ddf7f3fe056c739d06; `sources.jsonl` 3f35864f0f59d6c619350dae0057bb356692233c400039f24309fd45202867ee; `units.jsonl` 279b46a335b6582a4eb3376000c722b531461bc3e7756be94d856c4c324c676a.
**Prior contact:** the first held-out run (sections 0 and 2 of `PREREGISTRATION-legal.md`, and the results above) and the design splits `dev` and `temporal`, on which `engine2` is first run in `docs/v2-test-plan.md` stage B and calibrated in stage C. The calibration file
(if the walk certifies a threshold; on law it is expected not to, `docs/v2-test-plan.md` stage C) is fitted on `dev` only. `bench.run` refuses these splits without `--registered-run PREREGISTRATION-legal-v2.md` and a matching hash.

## 3. Systems (frozen)

**All six systems are re-run together in one session**, so the comparisons are paired and same-day: `closed_book`, `hybrid` (k = 8, as of today), `agentic` (k = 5, at most 4 searches, as of today), `agentic+asof` (the same, as of the question's date),
`engine` (**v1 at its registered configuration**, section 9 of `PREREGISTRATION-legal.md`: legal prompt v2, `verify.support = "llm"`, `answer.mode = "search"`, `decide.mode = "grade"`, `references_traced` on, `draft.max_sentences` 3,
`max_context_chars` 24,000, no reranker), and `engine2` (the **reference system** of every paired comparison). Generator of all six: `claude-haiku-5-5`, thinking at the default, `draft.max_tokens` 4096, no temperature. Command:
`--systems closed_book,hybrid,agentic,engine,engine2 --time-aware-variants --variants-of agentic --thinking default --set draft.max_tokens=4096 --registered-run PREREGISTRATION-legal-v2.md`.

**`engine2` settings, frozen:**

- Surface: the packaged v2 surface for the dataset's domain and prompt set (`default.json`, `domain.legal_br.json`, `prompts/*.legal_br.txt`), hash `f108cf9817e0a526ad227c0d33ef6c0fda239b46348a4afadeb3a9c90bdfa652` (`v2_surface_hash` of the stage B run manifests on the legal corpus; the improvement loop and calibration were run on the English-domain champion surface `df02f70a1a6d20b39b1fa16f23407a1afc3ac31139f5d80d1613a3c32bb8e505`, which the loop left unchanged); no `--v2-set`, `--v2-candidate`.
- **Locked judge model: `claude-sonnet-5-5`**, thinking disabled, as `judge_model` of `src/heuresis/v2/locked/policy.json`; the run's manifest records the judge actually used and `judge_is_policy_model` (must be true). Generator `claude-haiku-5-5`; no strong model (`route.escalate` off).
- Policy: alpha 0.05, delta 0.10, `default_tau` 0.5 (`policy.json`); calibration file: none: nothing certified on any dataset (stage C, `results/v2/C`), so `default_tau` 0.5 applies and `engine2`'s confidence is uncalibrated; prompt caching `--v2-cache` on (it changes cost, not the prompts).
- Protected files hash `5caae6ef44e8634d2e03134bc6f08073627b9fd6112ca65b84b5ffd2bada9657` (`v2/locked/manifest.py`; the hash of the locked judge, store, tools, reference resolver and these benchmark modules).

**The benchmark judges are the v1 ones, unchanged and on `claude-haiku-5-5`, so that this run and the first are comparable:** the support judge (`bench.citations`) and the answer judge (`bench.judge`), thinking disabled. Prompt hashes (sha256 of the text), copied from `PREREGISTRATION-legal.md` section 3:

| Prompt | sha256 |
|---|---|
| `LEGAL_CLOSED` (closed_book) | `f12453657d919b7e05114ca35f8139a9298cf81391a00c51589b9a3c77a1357d` |
| `LEGAL_PASSAGES` (hybrid) | `177e3998d455235c5e605ca10fded72fbca4100c672e169321c2e39dbafb7e27` |
| `LEGAL_AGENT` (agentic, agentic+asof) | `b4079842a6cc69c962c5771d2b3f4723eac71452d1f79cd6fd9a8ab11323132d` |
| `LEGAL_ENGINE_SUFFIX_V2` (v1 engine drafting instruction) | `5b5ae5675cfdbdf6db2efcf07271a04fb2779d73efa8a41bd8cb9914a0ec0fbc` |
| `SUPPORT_GATE_SYSTEM` (v1 engine's own support gate) | `b5821484f4bdc730e852d407d93ef799a126c85da2dcb8a5d26b61644c8381a3` |
| `SUPPORT_SYSTEM` (benchmark support judge) | `ef1defd662c545aeb5a8666c7e2c5438112728669cfb3acfed25145796647be8` |
| `JUDGE_SYSTEM` (answer-equivalence judge) | `9542c78c11cb886000e6a25b07aee5461058c3c892c2b8da39bbf10843172399` |

Local models: embedder `onnx:intfloat/multilingual-e5-small`, reranker `onnx:cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, entailer `onnx:MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`, file hashes from the stage B run manifest `model_provenance`: embedder onnx ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665, tokenizer 0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39; entailer onnx 79f8cda2b1230585a95ea0514a6f1bd21c5c986ba0529bb3261213a3e195fa6e, tokenizer 098c131bb4423163db239755e309facaa6850059f850f9f3d88a78344a4b631c; reranker onnx 3e9a03ed1e966f7c5288dd4230e3d6a9bf5e3a170a06f1f4241c5bca12c6487c, tokenizer 62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626. Price table `anthropic-2026-11`.

## 4. Primary outcome and analysis: tainted answers

Definition, strict and covered-only variants, per-question coding and the guard that coverage is reported beside every rate: exactly `PREREGISTRATION-legal.md` section 4 (a *tainted* answer is answered and has at least one reference whose norm or article is not
found in the corpus, or that resolves to a unit with no version in force at the as-of date; an abstention is not tainted; the strict variant is primary). `engine2`'s cited units count as references, as the v1 engine's do.

**H3 (primary).** (i) *Superiority over each baseline:* `engine2`'s tainted rate is lower than each of `closed_book`, `hybrid`, `agentic`, `agentic+asof` on each set: 8 paired comparisons, exact McNemar (two-sided) on the per-question paired indicators.
(ii) *Non-inferiority to v1:* the tainted rate of `engine2` is not above that of `engine` by more than **1 percentage point** **[proposed]** on each set: one-sided paired bootstrap (5,000 resamples, seed 20261112), non-inferior if the upper 95% bound of
`engine2` minus `engine` is below +0.01. Holm at alpha 0.05 over the 8 McNemar p-values and the 2 non-inferiority tests (p-value of the sign of the bootstrap, one-sided), 10 in all. Effect: the paired difference with a bootstrap 95% interval and the discordant counts.
**Direction stated in advance:** the first run's engine had 1 tainted answer of 615 and 0 of 240 (`RESULTS.md` section 3); `engine2` is expected to be at or near that, and below the baselines (6.0%-16.1% on `test`). On `temporal_test` the baselines sit at 0.4%-2.1%, so
(i) cannot be shown there (floor effect, as in the first run) and only (ii) is informative.

## 5. Co-primary outcome: useful answers (BR-TaxQA-R `test` only)

A *useful* answer is answered, not tainted (strict), and judged EQUIVALENT to the official answer by the v1 answer judge run over every answered row (`PREREGISTRATION-legal.md` section 5; unreadable verdicts count as not EQUIVALENT).

**H1.** (i) `engine2`'s useful-answer rate is **not below `agentic`'s by more than 3 percentage points** **[proposed]** (one-sided paired bootstrap, 5,000 resamples, seed 20261112; non-inferior if the lower 95% bound of `engine2` minus `agentic` exceeds -0.03).
(ii) `engine2`'s useful-answer rate is **above the v1 `engine`'s** (paired bootstrap 95% interval of the difference excludes zero on the positive side). The same difference is reported against every other system. Not Holm-adjusted with section 4;
Holm over these two. Reference values from the first run (not targets): useful answers `closed_book` 22.6%, `hybrid` 33.3%, `agentic` 38.4%, `agentic+asof` 37.2%, `engine` 34.0% (`RESULTS.md` section 4). **`engine2` may fail either part; it is reported either way.**

## 6. Dated questions: H4

On `temporal_test`, `engine2` gives the version in force at the question's date **at least as often as `agentic+asof`**: the code-scored outcome of `bench/citations.temporal_outcome` ("gave the gold version"), over the 240 questions. Test: exact McNemar on the paired indicators; H4 is **not
supported if `engine2` gives the gold version fewer times than `agentic+asof` and the one-sided exact p-value for "fewer" is below 0.05** **[proposed]**; the counts, the interval of the difference and how often each gives the superseded wording are reported. First run (reference): engine 129, `agentic+asof` 141, `agentic` 63,
`hybrid` 69, `closed_book` 18 of 240 (`RESULTS.md` section 5).

## 7. Cost: H6 and secondary outcomes

**H6.** Cost per useful answer (`test`), total spend of the system over the useful answers, with a paired bootstrap interval of the difference `engine2` minus `engine` and `engine2` minus `agentic`. **`engine2`'s cost includes the locked judge on `claude-sonnet-5-5` (the ledger tag `engine2-judge`), and is expected to be
dominated by it**: modelled at about US$0.0098 per question, of which US$0.0075 is the judge (`docs/v2-test-plan.md`), against US$0.00265 for the v1 engine. At the first run's useful rate (34%) that is about US$0.029 per useful answer against US$0.0078 for v1: **H6 (below v1's) is expected to fail on law unless the
useful rate rises a lot; it is reported with this note**. Secondary and exploratory (two-sided, no correction): support share by the v1 support judge (Wilson intervals, paired), norm / article not found / not in force breakdown, abstention rates, answers with no reference, mean calls and searches, median latency, the
engine2 gate drops by type and verdicts (`replay` payloads), the confidence of answers against the judge's verdict (risk-coverage; no calibration claim is made on law), cost per question. The support results are model-reviewed, not human-reviewed, as in the first run; if a blind stronger-model review of 200 stratified rows
disagrees with the support judge on more than 20% of them, the support figures are reported as unreliable (`PREREGISTRATION-legal.md` section 7).

## 8. Rules of the run, threats to validity

One run; one session for all six systems; nothing tuned after registration; a stopped run is not restarted with other settings. If the ledger stops it, only the questions completed by all six systems are analysed (complete cases) and the number is reported. Error rows (API or model failure after retries) count against the
system, are listed per system, and a system with more than 2% error rows is flagged. The deviations log below starts empty.

Threats to validity: those of `PREREGISTRATION-legal.md` section 8, and (a) **adaptive reuse of the held-out sets** (section 0); (b) the locked judge (`claude-sonnet-5-5`) is a different model from the generator, but the benchmark judges and the baselines' generator are Haiku, so judge effects are not removed; (c) `engine2`'s confidence is not calibrated on law (the
legal calibration set is too small); (d) one model, one run, one domain; sampling is the API default; (e) the engine's tainted rate is partly its gates by construction, and the co-primary check of section 5 guards against a system that is clean only because it says little.

## 8b. Design-split evidence (stage B, not a result)

`engine2` was run on the law design splits (`dev` 100, `temporal` 120), data seen during design; the numbers are calibration data (`results/v2/B/NOTES.md`). On `dev`: tainted answers 0/100 for `engine2` (`closed_book` 14, `agentic` 9, `agentic+asof` 6, `hybrid` 5, `engine` 0); useful answers 25/100 for `engine2` against `agentic` 32, `agentic+asof` 37, `hybrid` 33, `engine` 25, `closed_book` 21; cost per useful answer for `engine2` US$0.048 (generator 0.016, judge 0.032), US$0.036 above the v1 `engine` and US$0.042 above `agentic`. On `temporal`: tainted 0/120, coverage 79%. **Directional expectations, stated honestly:** `engine2` is expected to have the lowest tainted rate (as the v1 `engine`), and is **not** expected to be non-inferior to `agentic` on useful answers (on `dev` the lower bound of the difference was -0.13 against the margin -0.03), nor to beat the v1 `engine` on them; H6 is expected to fail. The improvement loop (two cycles, nine candidates, none promoted) and the calibration (no certified threshold on any dataset) changed nothing in the engine.

## 9. Frozen items and budget

| Item | Value | How obtained |
|---|---|---|
| Code commit | `c0de81c6651f010d26ad271796c851731259aa2e` (origin/v2 head, the code of stages B to D) | `git rev-parse HEAD` at the tag |
| v1 locked hash | `f13783b57968b2b8b9313bb31d89f83aac1ea417520a9de70676aa890d52ad53` (first registration: `f13783b57968b2b8b9313bb31d89f83aac1ea417520a9de70676aa890d52ad53`) | `heuresis hash` |
| v1 default surface hash / English baseline prompts hash | `547d7f32387e2e4aff33eaa5ff39a388b52084f3680e54515ccc3d1433d878b3` / `c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b` (first registration: `547d7f32…78b3` / `c025db9e…a7b`) | `heuresis hash` |
| v1 legal engine configuration hash / surface hash | configuration (sha256 of `engine_config` of the stage B manifest as sorted JSON) `5f918cb5f08ac1ce26d027d48e249cfe0c3e4438a27fdac7e49bd021493085d1`; run surface hash (manifest `surface_hash`) `5e5f9afb2ae735c7fdc2ab9c8c3ae11cdefe0c88a2dd0354d165b203d7b299a4`. **These do not reproduce the first registration's `1a6c90d9…bbd5` / `eb2e2c74…d100`**; see the deviations log. (first registration: `1a6c90d9…bbd5` / `eb2e2c74…d100`) | `BenchContext.engine_config()` |
| v2 surface hash | `f108cf9817e0a526ad227c0d33ef6c0fda239b46348a4afadeb3a9c90bdfa652` (legal run manifest `v2_surface_hash`) | `heuresis hash` / run manifest `v2_surface_hash` |
| Protected files hash | `5caae6ef44e8634d2e03134bc6f08073627b9fd6112ca65b84b5ffd2bada9657` | `heuresis hash` / run manifest `protected_hash` |
| Locked judge model, policy | `claude-sonnet-5-5`; alpha 0.05, delta 0.10, `default_tau` 0.5 | `v2/locked/policy.json` |
| Calibration file | none (no threshold certified on any dataset; `default_tau` 0.5, uncalibrated) | `v2/calibration/` |
| Held-out question id hashes | section 2 | corpus manifest |
| Generator, price table | `claude-haiku-5-5`, `anthropic-2026-11` | `src/heuresis/pricing.py` |

**Budget (owner to approve):** the plan's modelled figure was US$16.05 for the whole of stage F (runs US$14.78, support judge US$1.02, answer judge US$0.25) at `engine2` about US$0.0098 per question; ledger `runs/v2/ledger-F.jsonl`, cap **US$24.10** (cumulative, final), margin 0.25. `engine2` is now measured (stage B, law, `brlaw-core`): US$0.0119 per question on `dev` and US$0.0041 on `temporal` (see `results/v2/B/NOTES.md`). Re-projection with the dev rate as the conservative one: `test` 615 x 0.0119 = US$7.3 and `temporal_test` 240 x 0.0041 to 0.0119 = US$1.0 to 2.9 for `engine2`; the five other systems at the stage B rates (about US$0.0100 per question on `dev`, 0.0034 on `temporal`) add about US$6.2 on `test` and US$0.8 on `temporal_test`; support judge about US$1.2 and answer judge about US$0.25: **about US$16.8 to 18.7 in all, within the cap**. Measured figures, not modelled; the cap is not raised.

## Deviations log

| Date | Change | Reason | Data seen at the time |
|---|---|---|---|
| | (empty at registration) | | |
| 2026-11-13 | Judge `max_tokens` raised from 400 to 4096 (`JUDGE_MAX_TOKENS`; surface default and schema range follow); a judge reply that stops at `max_tokens` now counts as unreadable | The judge model thinks by default and its thinking tokens count against `max_tokens`, so a smoke call was truncated at 400 | None: made before any registered run |
| 2026-11-13 | `AnthropicLLM` errors now carry the HTTP status and the API's error type and message; if the API rejects the `thinking` field the client retries that call once without it and stops sending it on that instance (`llm.py`, commit b9511bc) | A smoke call failed with an uninformative `LLMError` | None: made before any registered run |
| 2026-11-13 | During setup of stage B, a verification print of the English dataset objects showed some question texts from the loader output (including a few non-design questions); nothing was scored, used or read | Operator slip in a check command | No answers or held-out rows; stage B, C and D used only non-held-out splits |
| 2026-11-14 | The improvement loop (2 cycles, 9 candidates) and the calibration (stage C) changed nothing: no promotion, no certified threshold; engine2 runs at the packaged surface and `default_tau` 0.5 | Results of stages D and C | `rot0`, `rot1`, `rot2`, `cal0` (English only) |
| 2026-11-14 | The v1 legal engine configuration hash and surface hash computed from the stage B manifest (`5f918cb5…`, `5e5f9afb…`) do not reproduce those quoted in `PREREGISTRATION-legal.md` (`1a6c90d9…`, `eb2e2c74…`); the hash computation may differ or the shared surface sources changed on branch `v2`. Flagged to the owner; not resolved here | Found while filling section 9 | None |
