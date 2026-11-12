# Phase 1 (dev fixes, $0): diagnosis and fixes

Dev split only; no paid call was made in this phase. Branch `dev-fixes` from `origin/main` 8a0f281. Evidence comes from the stored rows of the dev calibration run (`results.jsonl` of `main/<dataset>`, kept in the container under `runs/dev-calibration/`, not in git) and from the local ONNX models. The scripts are `scripts/dev_fixes/verifier_replay.py` and `scripts/dev_fixes/verifier_paired.py`.

## A. Cut-off replies

**What the stored rows show.** The client (`AnthropicLLM._finish`) concatenates only `text` blocks and kept neither the stop reason nor any block information, so the stop reason was NOT recorded. The rows do show what the billed output was spent on. Per system on the main run (3 datasets, 300 questions per system, `+asof` copies left out):

| system | calls | billed output tokens / call | visible tokens / call (chars/3.5) | rows with a call at the cap (>=590 tokens/call) | of which empty visible text |
|---|---|---|---|---|---|
| bm25 | 300 | 248 | 22 | 22 | 12 |
| vector | 300 | 223 | 20 | 14 | 7 |
| hybrid | 300 | 246 | 23 | 21 | 9 |
| closed_book | 300 | 388 | 27 | 60 | 42 |
| engine | 300 | 284 | 39 | 41 | 26 |
| hybrid_rerank | 300 | 251 | 23 | 21 | 12 |
| oracle | 300 | 242 | 31 | 6 | 2 |
| agentic | 874 | 180 | 14 | 0 | 0 |

"Visible" is the length of the reply the client kept (for the engine the raw draft, for the others the answer text without its CONFIDENCE line, about 8 tokens more). So about 85 to 95 percent of the billed output tokens of a normal call are not in the visible reply. Direct examples: engine rows whose raw draft has 0 characters and 600 output tokens (26 rows); a baseline reply `ABSTAIN` (7 characters) billed at 100 to 380 output tokens; on `hoh` the same model answers short questions with about 28 output tokens for 55 to 60 characters, i.e. it does not always do this. That pattern (a hidden, variable block that counts against `max_tokens`) is what a thinking block looks like.

**Documentation relied on** (read on 2026-11-12, `platform.claude.com`):
- `/docs/en/build-with-claude/adaptive-thinking`: "Claude's thinking is adaptive: the model evaluates each request and determines whether to think and how much." "Tokens Claude uses while thinking (billed as output tokens)". "A max_tokens sized for a response with no thinking is often too small once Claude starts thinking ... If you see stop_reason: "max_tokens" in responses, you have two remedies: Raise max_tokens ... Lower the effort level". "In Anthropic's testing, telling Claude Haiku 5.5 in the prompt to answer directly didn't stop it from thinking."
- `/docs/en/about-claude/models/overview`: `claude-haiku-5-5`: Thinking "Adaptive", default effort "medium".
- `/docs/en/build-with-claude/effort`: effort is set at `output_config.effort`; `max_tokens` is "a hard limit on total output (thinking plus response text)"; medium is the default on Haiku 5.5 and setting it explicitly is identical to omitting it.
- `/docs/en/build-with-claude/thinking`: "Claude Haiku 5.5 also has thinking on by default and accepts thinking: {type: "disabled"} at effort high or below. At xhigh or max effort, that combination returns a 400 error. To get less thinking, lower the effort level first." (table of accepted values: Haiku 5.5, `"disabled"`: "Thinking off at high effort or below").

**Cause.** Adaptive thinking is on by default for this model; the thinking tokens are billed and count against `max_tokens = 600`, but `llm.py` reads only text blocks. When the model thinks long, the budget is spent before or during the visible answer: empty or cut-off replies (41 of 100 `closed_book` replies on `musique`, 34 of 100 engine replies on `multihoprag`). It affects every system, but unevenly (`closed_book` and the engine most).

**Fix (implemented).** `AnthropicLLM(thinking=...)`: the field is sent as given and a rejection is not dropped silently. `bench.run --thinking disabled` (default) sends `thinking: {"type": "disabled"}` on every call of every system (they share one client), so `max_tokens` bounds the visible answer; `--thinking default` restores the old behaviour. Recorded: the manifest (`model_provenance.generator.thinking`), and, per call, the ledger (`stop_reason`, `blocks`, `text_chars`) and, per result row, `stop_reasons`, `blocks`, `text_chars` (engine included). Tests: `tests/test_llm.py` (2), `tests/test_bench_run.py` (2).

**Not confirmed without a paid call.** That the live API accepts `thinking: disabled` for `claude-haiku-5-5` as documented and returns text blocks only. The one-call test for phase 2 (before anything else, about US$0.0003): `closed_book` on one `musique` dev question with `--thinking disabled --limit 1`, then check in the ledger row that `blocks` is `{"text": 1}`, `stop_reason` is `end_turn` and `tokens_out` is close to `text_chars` / 3.5 (plus the CONFIDENCE line). If the API answers 400, stop; the fallback is `output_config.effort = "low"` behind the same constructor argument (not implemented, name taken from the documentation above).

## B. Drafting instruction

What the 100 engine questions of each of `musique` and `multihoprag` showed: 78 and 68 abstentions are the model's own `ABSTAIN` (no claim). Only 22 of those drafts (3 on `musique`, 19 on `multihoprag`) are cases where all gold passages were among those shown, so I read all 22 (fewer than the 30 asked for) and looked at the others by category (some gold passage shown: 64 and 43; none: 11 and 6). Findings:
- On `musique`, the abstentions are almost all retrieval gaps (the second hop was not among the 8 passages), which no prompt fixes: 64 of the 78 had some but not all gold passages shown, 11 none, 3 all.
- On `multihoprag`, many drafts abstain because "the passages do not name Sporting News / The Age / Fortune as the source": the question names an outlet, the passage line shows the title and validity but NOT the outlet (`source_id` is known, e.g. `multihoprag:sporting-news`, but `draft_prompt` and the baselines' `_passage_line` do not print it). This is an input-format problem, not a wording problem, and it hits every system equally. **Proposal, not implemented** (it changes `prompts_hash` and every system's input): show the source name in each passage line for every system.
- The old text told the model to abstain whenever the passages "do not answer the question", with no instruction to combine passages and with the answer not required first.

Old instruction (`DRAFT_SYSTEM_V1`, kept verbatim, `draft.prompt = "v1"`):

```
Answer ONLY from the numbered passages. Never use outside knowledge.
Format, one item per line:
- Write short sentences. End EVERY sentence with the marks of the passages that support it, like [t1] or [t1][t2].
- Never do arithmetic or date math yourself. Request it before the answer with a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write {k1} where the result goes and add the mark [k1] to that sentence.
- Use the as-of date you are given; passages show their validity as (title; valid from..to).
- If the passages do not answer the question, write only `ABSTAIN <type>: <reason>` with type one of: no_source, not_valid_at_date, conflict, false_premise, outside_coverage, unsupported, needs_input, tool_failed, out_of_scope, budget.
```

New instruction (`DRAFT_SYSTEM_V2`, the default):

```
Answer ONLY from the numbered passages. Never use outside knowledge.
Answer whenever the passages contain the answer, also when you must combine facts from two or more passages (for example, one passage names the person and another gives the fact about that person). A passage that is only partly relevant, or that does not repeat the question's wording, is no reason to abstain.
Format, one item per line:
- State the answer in the first sentence, then add only what is needed. Write short sentences. End EVERY sentence with the marks of ALL the passages that support it, like [t1] or [t1][t2].
- Never do arithmetic or date math yourself. Request it before the answer with a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write {k1} where the result goes and add the mark [k1] to that sentence.
- Use the as-of date you are given; passages show their validity as (title; valid from..to).
- Only if the answer is not in the passages, write only `ABSTAIN <type>: <reason>` with type one of: no_source, not_valid_at_date, conflict, false_premise, outside_coverage, unsupported, needs_input, tool_failed, out_of_scope, budget.
```

This cannot be verified without paid calls. Phase 2 would run the engine once with `v1` and once with `v2` (same everything else) for the A/B. Test: `tests/test_surface.py::test_drafting_prompt_v2_is_default_and_v1_stays_selectable`.

## C. Verifier

**Cause of the 0.002.** Offline, with the local model (`MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`; label order entailment / neutral / contradiction):
- Order is right (premise first, hypothesis second; reversing the order does not help consistently).
- The premise is the cited passages' text joined, with no title and no marks; the claim usually names the entity that only the passage TITLE carries. Example: premise "The population was 3,767 at the 2020 census.", claim "The population of Horicon was 3,767 at the 2020 census.": entailment 0.003, neutral 0.993. With the title prepended ("Horicon, Wisconsin. The population ..."): entailment 0.989. Same for "Delta Virginis has 1.4 times the mass of the Sun" (0.002 to 0.971), "The main hall at Oslo Concert Hall has ..." (0.004 to 0.981), "Mario Tremblay was hired six games into ..." (0.072 to 0.986).
- Truncation: tokenizer truncation is 512 tokens for the pair; premise plus claim exceeds it for 16 of 194 claims (8%, mostly long `multihoprag` passages), median pair length 61 tokens. A secondary cause.
- Tool values: 1 of 216 claims has a tool mark; not a factor.

**Replay on the stored dev rows** (216 claims in the 138 engine rows with claims; no model call except the local NLI; the locked labelling and decision rule re-applied through `heuresis.bench.calibrate.replay`). Candidates: C1 current; C1t current with the title prefixed; C2 max over single cited passages (`t` = with title); C3 max over windows of up to 3 consecutive sentences of each cited passage (`t` = with title); C4 deterministic lexical support (share of the claim's content tokens, accent- and case-folded, found in the cited passages; 0 if any number of the claim is missing); C5 max(C3, C4) (`t` = with C3t).

Penalised score, pooled n = 300 and per dataset at the default thresholds (0.5, 0.3); the best pair is chosen on the same 300 questions (in-sample, optimistic); intervals are bootstrap over questions:

| candidate | pooled at (0.5, 0.3) [95% CI] | best pooled pair | pooled at best pair [95% CI] (in-sample) | musique / multihoprag / hoh at (0.5, 0.3) |
|---|---|---|---|---|
| C1_current | 0.200 [0.14, 0.26] | (0.2, 0.1) | 0.247 [0.18, 0.31] | 0.02 / 0.10 / 0.48 |
| C1t_current_with_title | 0.303 [0.24, 0.36] | (0.2, 0.1) | 0.327 [0.26, 0.39] | 0.04 / 0.13 / 0.74 |
| C2_max_passage | 0.200 [0.14, 0.26] | (0.1, 0.1) | 0.250 [0.18, 0.32] | 0.01 / 0.11 / 0.48 |
| C2t_max_passage_title | 0.297 [0.23, 0.36] | (0.2, 0.2) | 0.327 [0.26, 0.39] | 0.02 / 0.13 / 0.74 |
| C3_max_sentence_window | 0.223 [0.16, 0.28] | (0.1, 0.1) | 0.257 [0.19, 0.32] | 0.03 / 0.16 / 0.48 |
| C3t_max_window_title | 0.333 [0.27, 0.40] | (0.2, 0.1) | 0.347 [0.28, 0.41] | 0.04 / 0.22 / 0.74 |
| C4_lexical | 0.347 [0.28, 0.41] | (0.3, 0.3) | 0.350 [0.28, 0.41] | 0.08 / 0.21 / 0.75 |
| C5_max(C3,C4) | 0.347 [0.28, 0.41] | (0.5, 0.5) | 0.347 [0.28, 0.41] | 0.08 / 0.21 / 0.75 |
| C5t_max(C3t,C4) | 0.347 [0.28, 0.41] | (0.6, 0.5) | 0.347 [0.28, 0.41] | 0.08 / 0.21 / 0.75 |

Paired comparison at the default thresholds (correct / wrong / abstained; difference to C1 [95% CI]):

```
counts at (0.5,0.3): correct/wrong/abstained, pooled and per dataset; paired difference vs C1_current [95% CI]
C1_current                 pooled: (75, 15, 210) diff +0.000 [+0.000,+0.000] | musique: (8, 6, 86) diff +0.000 [+0.000,+0.000] | multihoprag: (12, 2, 86) diff +0.000 [+0.000,+0.000] | hoh: (55, 7, 38) diff +0.000 [+0.000,+0.000]
C1t_current_with_title     pooled: (104, 13, 183) diff +0.103 [+0.067,+0.143] | musique: (9, 5, 86) diff +0.020 [+0.000,+0.060] | multihoprag: (13, 0, 87) diff +0.030 [+0.000,+0.070] | hoh: (82, 8, 10) diff +0.260 [+0.160,+0.360]
C2_max_passage             pooled: (75, 15, 210) diff +0.000 [-0.013,+0.013] | musique: (7, 6, 87) diff -0.010 [-0.050,+0.020] | multihoprag: (13, 2, 85) diff +0.010 [+0.000,+0.030] | hoh: (55, 7, 38) diff +0.000 [+0.000,+0.000]
C2t_max_passage_title      pooled: (103, 14, 183) diff +0.097 [+0.057,+0.140] | musique: (8, 6, 86) diff +0.000 [-0.040,+0.050] | multihoprag: (13, 0, 87) diff +0.030 [+0.000,+0.070] | hoh: (82, 8, 10) diff +0.260 [+0.160,+0.360]
C3_max_sentence_window     pooled: (82, 15, 203) diff +0.023 [+0.000,+0.050] | musique: (10, 7, 83) diff +0.010 [-0.040,+0.060] | multihoprag: (17, 1, 82) diff +0.060 [+0.010,+0.110] | hoh: (55, 7, 38) diff +0.000 [+0.000,+0.000]
C3t_max_window_title       pooled: (115, 15, 170) diff +0.133 [+0.087,+0.180] | musique: (11, 7, 82) diff +0.020 [-0.040,+0.090] | multihoprag: (22, 0, 78) diff +0.120 [+0.060,+0.190] | hoh: (82, 8, 10) diff +0.260 [+0.170,+0.360]
C4_lexical                 pooled: (120, 16, 164) diff +0.147 [+0.103,+0.193] | musique: (14, 6, 80) diff +0.060 [+0.000,+0.130] | multihoprag: (23, 2, 75) diff +0.110 [+0.050,+0.170] | hoh: (83, 8, 9) diff +0.270 [+0.170,+0.370]
C5_max(C3,C4)              pooled: (120, 16, 164) diff +0.147 [+0.103,+0.193] | musique: (14, 6, 80) diff +0.060 [+0.000,+0.130] | multihoprag: (23, 2, 75) diff +0.110 [+0.050,+0.180] | hoh: (83, 8, 9) diff +0.270 [+0.170,+0.370]
C5t_max(C3t,C4)            pooled: (120, 16, 164) diff +0.147 [+0.103,+0.193] | musique: (14, 6, 80) diff +0.060 [+0.000,+0.130] | multihoprag: (23, 2, 75) diff +0.110 [+0.050,+0.170] | hoh: (83, 8, 9) diff +0.270 [+0.170,+0.380]

C3t_max_window_title vs C4_lexical (paired):
  pooled: -0.013 [-0.037,+0.007]
  musique: -0.040 [-0.090,+0.000]
  multihoprag: +0.010 [-0.020,+0.040]
  hoh: -0.010 [-0.030,+0.000]
```

AUROC for separating claims of correct drafts from claims of wrong drafts (draft graded by the run's containment grader; only claims whose `exists`, `valid_at_date` and `numbers_traced` checks passed; counts positive/negative in brackets):

| candidate | pooled AUROC [95% bootstrap] (claims of correct / wrong drafts) | musique | multihoprag | hoh |
|---|---|---|---|---|
| C1_current | 0.49 [0.37, 0.60] (163/24) | 0.44 [0.21, 0.67] (29/10) | 0.32 [0.00, 0.71] (21/4) | 0.47 [0.28, 0.65] (113/10) |
| C1t_current_with_title | 0.57 [0.47, 0.69] (163/24) | 0.43 [0.20, 0.66] (29/10) | 0.48 [0.14, 0.81] (21/4) | 0.53 [0.35, 0.69] (113/10) |
| C2_max_passage | 0.48 [0.36, 0.58] (163/24) | 0.40 [0.18, 0.60] (29/10) | 0.36 [0.05, 0.75] (21/4) | 0.47 [0.28, 0.65] (113/10) |
| C2t_max_passage_title | 0.57 [0.46, 0.68] (163/24) | 0.41 [0.17, 0.62] (29/10) | 0.46 [0.13, 0.81] (21/4) | 0.53 [0.35, 0.69] (113/10) |
| C3_max_sentence_window | 0.44 [0.32, 0.56] (163/24) | 0.31 [0.09, 0.53] (29/10) | 0.68 [0.44, 0.88] (21/4) | 0.47 [0.28, 0.65] (113/10) |
| C3t_max_window_title | 0.50 [0.36, 0.62] (163/24) | 0.32 [0.11, 0.54] (29/10) | 0.74 [0.52, 0.92] (21/4) | 0.52 [0.35, 0.69] (113/10) |
| C4_lexical | 0.57 [0.46, 0.68] (163/24) | 0.54 [0.31, 0.76] (29/10) | 0.62 [0.26, 0.93] (21/4) | 0.55 [0.40, 0.71] (113/10) |
| C5_max(C3,C4) | 0.55 [0.44, 0.66] (163/24) | 0.43 [0.21, 0.65] (29/10) | 0.66 [0.31, 0.93] (21/4) | 0.55 [0.39, 0.70] (113/10) |
| C5t_max(C3t,C4) | 0.55 [0.44, 0.66] (163/24) | 0.42 [0.20, 0.64] (29/10) | 0.66 [0.31, 0.93] (21/4) | 0.54 [0.39, 0.70] (113/10) |

Reading, with n = 100 per dataset and 24 / 10 / 4 / 10 negative claims in the AUROC: the AUROC of every candidate is about 0.5 with wide intervals, so no support score tells claims of wrong drafts from claims of correct ones here (see D: the wrong answers' claims are true of their passages). What the candidates change is how many CORRECT answers are no longer rejected: pooled correct at (0.5, 0.3) rises from 75 to 104 (title only), 115 (title + windows) or 120 (lexical) while accepted wrong answers stay at 13 to 16. The three upgrades beat the current scoring clearly (paired differences +0.10, +0.13, +0.15, intervals above 0, no dataset worse); the differences among them are noise (title + windows versus lexical -0.013 [-0.037, +0.007]). Differences of 0.01 to 0.04 between candidates are not interpreted.

**Implemented as the default:** `verify.support = "window_title"` (C3t): best entailment over title-prefixed windows of up to three consecutive sentences of each cited passage (tool values appended to each window). It fixes both diagnosed causes and keeps an entailment check; the lexical score was numerically the highest but not distinguishable, and it checks no meaning, so I did not adopt it. **The choice between them is yours**; `current` stays selectable. Thresholds are unchanged (0.5 / 0.3): the best pair for the new scoring is about (0.2, 0.1) at 0.347 versus 0.333 at the default, a difference I do not tune to. They are to be recalibrated on the phase-2 rows. The entailer now scores about 3 times the sentence count of each cited passage in pairs per claim (local, about 60 to 190 pairs/s on 4 cores). Tests: `tests/test_locked_verify.py` (3), `tests/test_surface.py`.

## D. Wrong answers that are true of the passage

Engine answers graded wrong on dev (`musique` 6, `multihoprag` 2, `hoh` 7 = 15 of the 300 questions; per-row list in `engine_wrong_answers.json`, no question texts). My reading of each answer (not an automated judgement):
- **8 of 15 (53%)** are true statements of their passage that do not answer the question: an intermediate hop given as the answer (2: "Jay Z", "Japan ... Shanghai"), an echo of the question with a different fact (Hubbert / Shell lab), a partial answer (the male and female counts without the total; the surname without the first name), an off-target figure (Clarkson: "most recent one was in 2007" to "how many"), an approximate year ("early 1980s" for 1981), and no yes/no where the question asks for one. First-claim support was 0.53 to 0.99 in all of them (current scoring), so the verifier is doing its job: the claim IS supported.
- **7 of 15 (47%)** read as correct answers that the containment grader rejects ("Nanjing has 140 miles" vs gold "140 mi"; "consisted largely of" vs "consisting largely of"; word order; "Chaucer's" vs "Chaucer"; "positive, not negative" for gold "no"; a two-part answer split over two sentences; "285 students in grades PreK-8 as of the 2022-23 school year" vs the gold wording). This is a property of the pre-registered string-containment grader (`bench.run.is_correct`), not of the engine; it penalises verbose, paraphrasing systems and cannot be changed after registration, so **it is worth a decision before the test run**. I did not change it. I did not measure it for the baselines.

**Cheapest check to catch the 8, proposed, not implemented.** An "answers the question" test on the first sentence: (a) free and deterministic: by question type, require a number for "how many/much", a year or date for "when", yes/no for questions opening with an auxiliary verb, and a capitalised token absent from the question for "who" (by my count it catches about 2 of the 8: the missing yes/no, the answer that only repeats the surname from the question; the number and date types pass on numbers that are not the answer); (b) one extra cheap model call after drafting, on answered questions only: "Does this answer state what the question asks for? yes/no" (about 300 input tokens, about US$0.00004 per answered question). (b) is the one I would test; it is an A/B arm for phase 2 and needs a design decision on where it sits (surface, not locked).

## E. Tests and hashes

`python3 -m pytest -q`: 497 passed, 16 skipped. `heuresis hash`:
- locked: `d98f86a5969279db434645acb8585f512999c60789068afdfa3cfdff4aa2eb88` (CHANGED, was `3c23fecd...`; `locked/verify.py` now builds several premises per claim and the config gained `verify.support`).
- surface: `ca69c121b7a9d2a47da5f6ad04f31caf6dad9587a5afcf3c7dafe858350ea173` (CHANGED, was `b7e767ec...`; new drafting instruction and the two new config fields `draft.prompt`, `verify.support`).
- prompts: `1498745bcecca370bd94caef482d685ab41c84890ab5a208320f2dcbacc2a462` (unchanged: baseline prompts were not touched).

The pre-registration draft (sections 3, 3.4, 7 and the deviations log) was updated for the three changes, each marked as made on dev evidence with the evidence file cited.

## Phase 2 (NOT started; waits for your reply)

Estimated from the measured input tokens of the dev calibration rows and visible output (reply characters / 3.5 plus about 30 tokens per call for the CONFIDENCE line and format), at $0.1 / $0.5 per million input / output tokens. Output is much smaller with thinking off, so input dominates; the estimate is about 30 percent below what the same runs cost with thinking on:

| step | what | estimated cost |
|---|---|---|
| 0 | one-call test of `--thinking disabled` (1 `musique` question, `closed_book`) | $0.0003 |
| 1 | full re-run, all systems, 3 x 100 dev questions, `--time-aware-variants`, v2 prompt, window_title, thinking disabled (the "main" configuration) | $1.1 |
| 2 | engine only with `draft.prompt = v1` under the same settings, for the prompt A/B (3 x 100) | $0.1 |
| 3 | k sweep as before: baselines at k = 4 and 12 ($0.17 + $0.43), agentic at 4 per search ($0.15) and at 12 (about $0.25; not run last time) | $1.0 |
| 4 | optional: an "answers the question" judge arm (D(b)) on the engine's answers | about $0.05 |
| 5 | optional: a second identical run of step 1 for run-to-run variance (no seed exists) | $1.1 |
| | **Total without the optional steps** | **about $2.2** (range $1.6 to $3.0) |

Already spent: $2.6068 of the single ledger; with the cap at $8.60 and margin $0.25 the usable remainder is about $5.7, so steps 0 to 5 fit with room. No step runs without `--ledger runs/dev-calibration/ledger.jsonl`.
