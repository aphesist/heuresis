# Dev re-run with the fixes (phase 2): notes and report

**Calibration data on the dev split only (100 questions per dataset). Not benchmark results.** Model `claude-haiku-5-5`; code on branch `dev-fixes` (the runs used 755385e plus c658b22, which only adds `--set`). Defaults: drafting prompt v2, `verify.support = window_title`, thinking disabled, source label in every passage line, `verify.answers_question` off. Every paid command used `--paid --cap 8.60 --margin-usd 0.25 --ledger runs/dev-calibration/ledger.jsonl` (the one ledger; copy in `ledger.jsonl`); the raise from the original US$3 cap was approved by the user in this session. Stores: a copy of the real-embedder store `runs/pilot-dev/<dataset>/store.sqlite` for every run.

Hashes at the time of the runs (`heuresis hash`): locked `d98f86a5969279db434645acb8585f512999c60789068afdfa3cfdff4aa2eb88`, surface `a7fe2849f9a81805785afbcc818dff39953e0d8f6ff459a5648c61d40332d8d7`, prompts `c025db9efc35daf759babe28848d6db14a0f8c2fbc853ea21cd60e01505d3a7b` (changed from 3c23fecd / b7e767ec / 1498745b by the phase 1 and phase 2 code changes; see the deviations log in `PREREGISTRATION.md`). Test suite on the last commit before the runs: 508 passed, 16 skipped.

## Commands

```
# step 0
python -m heuresis.bench.run --dataset musique --split dev --systems closed_book --out runs/dev-fixes/step0 --limit 1 --paid ...
# step 1 (main1) and step 5 (main2, identical):
python -m heuresis.bench.run --dataset D --split dev --systems closed_book,bm25,vector,hybrid,hybrid_rerank,agentic,engine,oracle --time-aware-variants --workers 4 --out runs/dev-fixes/main{1,2}/D --paid --cap 8.60 --margin-usd 0.25 --ledger runs/dev-calibration/ledger.jsonl --model claude-haiku-5-5
# step 2, engine only: armA-v1: --set draft.prompt=v1   armB-answersq: --set verify.answers_question=true
# step 4: python -m heuresis.bench.judge runs/dev-fixes/main1/{musique,multihoprag,hoh} --paid --cap 8.60 --margin-usd 0.25 --ledger ... --workers 4
# step 3 (k sweep): base-k4/base-k12: --systems bm25,vector,hybrid,hybrid_rerank --k 4|12 ; agent-k4/agent-k12: --systems agentic --agent-k 4|12
# step 6, reports: python -m heuresis.bench.report FOLDERS --iters 1000 ; python -m heuresis.bench.calibrate main1/{musique,multihoprag,hoh}
python3 scripts/dev_fixes/phase2_analysis.py runs/dev-fixes > analysis.md
```

## Report

**Step 0 (thinking disabled).** The API accepted `thinking: {"type": "disabled"}` for `claude-haiku-5-5` (no fallback needed). `step0.json`: `blocks` `{"text": 1}`, `stop_reason` `end_turn`, 257 output tokens for 675 visible characters (about 193 tokens plus the CONFIDENCE line): no hidden output. Before the change the same kind of call showed about 85 to 95 percent of output tokens outside the visible reply.

**Hidden output and truncation now (all generator calls of this phase, 15,142 calls with the judge).** Every call of every system returned text blocks only; no thinking block anywhere. `stop_reason` was `end_turn` on every generator call and `max_tokens` on none (before: 41 of 100 closed_book replies on musique and 34 of 100 engine replies on multihoprag at the cap). Output tokens per call fell from 388 to about 90 (closed_book) and from 284 to about 79 (engine). The "hidden-output share" column of the spend table in `analysis.md` (22 to 37 percent) is only my estimator (characters / 3.5 against billed tokens, with the CONFIDENCE line) and not hidden output: there are no non-text blocks. The judge calls are the exception: they were given `max_tokens` 10, which cuts `NOT_EQUIVALENT` after ten tokens (783 of 908 stopped at `max_tokens`); the verdict is unambiguous from the prefix and was read from it, 8 replies began with prose and were counted as "not flipped" (conservative). A cap of 20 would have been cleaner; I did not re-run.

**Spend.** Ledger total **US$5.7819** (cap 8.60, margin 0.25; US$2.5681 usable remains). This phase US$3.1751: main run 1.01 (with step 0), A/B arms about 0.20, repeat run 1.0, judge 0.032, k sweep about 0.93. By tag and tokens: first table of `analysis.md`.

**Main run, per dataset and system (n = 100):** correct / wrong / abstained, penalised score with interval, accuracy, coverage, cost per question and per correct, median latency, mean calls, mean answer length, tokens per question, errors (0 everywhere), and the judge columns are in the tables below (`results.md` of each folder has the full tables). Pooled (c - w) / 300 under the containment grade and the judge-assisted grade, with rows flipped by the judge (the judge grade is secondary and exploratory, same model family as the generator, applied to all systems alike):

| system | primary | judge-assisted | flipped |
|---|---|---|---|
| closed_book | -0.400 (61c/181w) | -0.347 (69c/173w) | 8 |
| bm25 | 0.090 (113c/86w) | 0.137 (120c/79w) | 7 |
| vector | 0.113 (103c/69w) | 0.140 (107c/65w) | 4 |
| hybrid | 0.120 (120c/84w) | 0.160 (126c/78w) | 6 |
| hybrid_rerank | 0.060 (103c/85w) | 0.107 (110c/78w) | 7 |
| agentic | 0.003 (123c/122w) | 0.077 (134c/111w) | 11 |
| engine | 0.317 (123c/28w) | 0.390 (134c/17w) | 11 |
| oracle | 0.580 (200c/26w) | 0.667 (213c/13w) | 13 |
| bm25+asof | 0.380 (155c/41w) | 0.453 (166c/30w) | 11 |
| vector+asof | 0.387 (148c/32w) | 0.433 (155c/25w) | 7 |
| hybrid+asof | 0.390 (160c/43w) | 0.457 (170c/33w) | 10 |
| hybrid_rerank+asof | 0.353 (149c/43w) | 0.427 (160c/32w) | 11 |
| agentic+asof | 0.333 (172c/72w) | 0.460 (191c/53w) | 19 |

With thinking off the baselines answer far more often and are wrong far more often than in the first calibration run (for example closed_book on musique: 73 wrong of 100, was 18; hoh baselines without the date still about 50 wrong of 100), so their penalised scores fall or stay near zero while the engine's rise (pooled engine 0.317 at the default thresholds, was 0.200). Against the non-time-aware baselines the engine is ahead on dev; the time-aware copies (exploratory) are at 0.33 to 0.39, level with or above it, and the oracle is at 0.58. Per dataset, engine: musique 16 / 11 / 73, multihoprag 25 / 10 / 65, hoh 82 / 7 / 11 (correct / wrong / abstained).

**Engine now.** Abstention types and the share that is the draft's own ABSTAIN are in the "Engine (main1)" section of `analysis.md`: draft's own ABSTAIN fell from 78 to 37 (musique) and from 68 to 11 (multihoprag), hoh 6; abstentions after claim verification are now 36 / 54 / 5. musique: unsupported 35, no_source 22, not_valid_at_date 14; multihoprag: unsupported 52, outside_coverage 4, no_source 4, not_valid_at_date 3. Five examples of correct answers rejected and of wrong answers accepted, with per-claim support, are in the same section (dev only). Of the rejected correct answers, several now are rejected because the draft adds a hedging second sentence ("the passages do not say ...") whose claim has no support; of the accepted wrong answers several are grader false negatives that the judge flips (11 of the engine's 28 wrong answers).

**Engine against hybrid (discordance of correctness, n = 100 each):** musique 0.15 (engine-only 3, hybrid-only 12), multihoprag 0.33 (3, 30), hoh 0.53 (46, 7).

**A/B arms against the main run (paired, engine only, penalised-score difference [95% bootstrap CI]):** v1 prompt: pooled -0.053 [-0.107, +0.000] (musique -0.03, multihoprag -0.05, hoh -0.08; none clearly different alone; v2 is at least not worse). `answers_question` on: pooled +0.027 [-0.010, +0.067] (musique +0.05, multihoprag +0.04, hoh -0.01): wrong answers 28 to 16, correct 123 to 119, abstained 149 to 165, 1.47 calls per question; not distinguishable from zero on 300 questions, so there is no case to turn it on yet.

**Run to run (main1 vs main2, identical settings, no seed):** per system the difference in pooled penalised score and the share of questions whose outcome changed are in the "Run-to-run" table of `analysis.md`: single-shot systems change 4 to 12 percent of outcomes and 0.00 to 0.04 in score; the engine 11 percent and -0.013; the agentic systems 20 to 22 percent and up to 0.05. Differences of that size between systems on n = 300 are noise.

**Thresholds by replay on the main1 engine rows (45 pairs, pooled n = 300; defaults not changed):** argmax support 0.7, partial 0.7 (ties to the higher pair; (0.7, 0.3) scores the same), penalised score 0.3300; packaged (0.5, 0.3) 0.3167; worst 0.27. The grid is very flat: 25 of 45 pairs are within 0.02 of the best, 43 within 0.05 (supports 0.3 to 0.7 are all within 0.02). Full grid in `calibration-grid.txt`. The `answers_question` arm is not modelled by the replay.

**k sweep (pooled penalised score, k4 / default / k12):** bm25 .080 / .090 / .103; vector .050 / .113 / .077; hybrid .073 / .120 / .147; hybrid_rerank -.003 / .060 / .097; agentic (per search 4 / 5 / 12) -.023 / .003 / .027. The best k on dev is 12 for bm25, hybrid, hybrid_rerank and agentic and 8 for vector; the gaps are a few points on n = 300.

**What failed or was skipped.** Nothing was stopped by the ledger; no error rows in any run. The judge's `max_tokens` of 10 was too small (see above). The `answers_question` arm was run for the engine only, as planned. The k sweep includes agentic at 12 (not run in the first calibration). Hashes, tests and the deviations log are described above and in `PREREGISTRATION.md`. The `runs/` folders (stores, raw results with replay payloads) are only in the container.


# Tables

## Spend

Ledger total $5.7819 over 23608 calls; this phase (from step 0) $3.1751 over 15142 calls.

| tag | calls | tokens in | tokens out | USD | hidden-output share | calls cut at max_tokens | stop reasons |
|---|---|---|---|---|---|---|---|
| agentic | 2979 | 4775294 | 145543 | 0.5503 | 31% | 0 | {'end_turn': 2979} {'text': 2979} |
| engine | 1342 | 3393482 | 106250 | 0.3925 | 22% | 0 | {'end_turn': 1342} {'text': 1342} |
| hybrid_rerank | 1200 | 2823667 | 65931 | 0.3153 | 35% | 0 | {'end_turn': 1200} {'text': 1200} |
| bm25 | 1200 | 2757413 | 67783 | 0.3096 | 34% | 0 | {'end_turn': 1200} {'text': 1200} |
| hybrid | 1200 | 2748826 | 66178 | 0.3080 | 35% | 0 | {'end_turn': 1200} {'text': 1200} |
| vector | 1200 | 2731894 | 59154 | 0.3028 | 37% | 0 | {'end_turn': 1200} {'text': 1200} |
| agentic+asof | 1512 | 2064948 | 74026 | 0.2435 | 31% | 0 | {'end_turn': 1512} {'text': 1512} |
| hybrid_rerank+asof | 600 | 1416216 | 33929 | 0.1586 | 34% | 0 | {'end_turn': 600} {'text': 600} |
| bm25+asof | 600 | 1388796 | 34485 | 0.1561 | 34% | 0 | {'end_turn': 600} {'text': 600} |
| hybrid+asof | 600 | 1382842 | 34535 | 0.1556 | 34% | 0 | {'end_turn': 600} {'text': 600} |
| vector+asof | 600 | 1370958 | 30417 | 0.1523 | 37% | 0 | {'end_turn': 600} {'text': 600} |
| oracle | 600 | 449354 | 36737 | 0.0633 | 32% | 0 | {'end_turn': 600} {'text': 600} |
| closed_book | 601 | 78737 | 54344 | 0.0350 | 27% | 0 | {'end_turn': 601} {'text': 601} |
| judge | 908 | 277000 | 9080 | 0.0322 | 68% | 783 | {'max_tokens': 783, 'end_turn': 125} {'text': 908} |

Hidden-output share = 1 - (visible characters / 3.5) / billed output tokens. A share above 0 on a system without thinking blocks is the CONFIDENCE line and format tokens.


## musique (dev, n=100): main1

| system | n | correct | wrong | abstained | errors | penalised [95% CI] | accuracy | coverage | $/q | $/correct | median ms | calls | ans chars | tok in/q | tok out/q | judge: flipped | correct (judge) | penalised (judge) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 21 | 73 | 6 | 0 | -0.520 [-0.673, -0.356] | 0.21 | 0.94 | 0.00007 | 0.00033 | 1003 | 1.00 | 288 | 111 | 118 | 5 | 26 | -0.420 [-0.574, -0.242] |
| bm25 | 100 | 19 | 24 | 57 | 0 | -0.050 [-0.168, 0.067] | 0.19 | 0.43 | 0.00022 | 0.00113 | 820 | 1.00 | 93 | 1904 | 50 | 2 | 21 | -0.010 [-0.131, 0.115] |
| vector | 100 | 24 | 22 | 54 | 0 | 0.020 [-0.118, 0.140] | 0.24 | 0.46 | 0.00021 | 0.00085 | 966 | 1.00 | 93 | 1802 | 50 | 1 | 25 | 0.040 [-0.096, 0.168] |
| hybrid | 100 | 25 | 23 | 52 | 0 | 0.020 [-0.119, 0.153] | 0.25 | 0.48 | 0.00021 | 0.00084 | 1049 | 1.00 | 98 | 1834 | 51 | 1 | 26 | 0.040 [-0.097, 0.176] |
| hybrid_rerank | 100 | 23 | 25 | 52 | 0 | -0.020 [-0.155, 0.102] | 0.23 | 0.48 | 0.00022 | 0.00097 | 4169 | 1.00 | 110 | 1943 | 55 | 2 | 25 | 0.020 [-0.113, 0.152] |
| agentic | 100 | 42 | 35 | 23 | 0 | 0.070 [-0.108, 0.230] | 0.42 | 0.77 | 0.00045 | 0.00108 | 2714 | 2.99 | 215 | 3860 | 136 | 1 | 43 | 0.090 [-0.080, 0.255] |
| engine | 100 | 16 | 11 | 73 | 0 | 0.050 [-0.049, 0.144] | 0.16 | 0.27 | 0.00029 | 0.00181 | 1405 | 1.00 | 38 | 2400 | 99 | 1 | 17 | 0.070 [-0.020, 0.170] |
| oracle | 100 | 64 | 10 | 26 | 0 | 0.540 [0.402, 0.674] | 0.64 | 0.74 | 0.00011 | 0.00017 | 768 | 1.00 | 146 | 736 | 68 | 4 | 68 | 0.620 [0.490, 0.732] |
| bm25+asof | 100 | 21 | 21 | 58 | 0 | 0.000 [-0.124, 0.119] | 0.21 | 0.42 | 0.00021 | 0.00102 | 798 | 1.00 | 93 | 1904 | 49 | 0 | 21 | 0.000 [-0.124, 0.119] |
| vector+asof | 100 | 25 | 20 | 55 | 0 | 0.050 [-0.080, 0.174] | 0.25 | 0.45 | 0.00021 | 0.00082 | 1024 | 1.00 | 96 | 1802 | 51 | 1 | 26 | 0.070 [-0.061, 0.202] |
| hybrid+asof | 100 | 26 | 23 | 51 | 0 | 0.030 [-0.102, 0.155] | 0.26 | 0.49 | 0.00021 | 0.00081 | 1030 | 1.00 | 105 | 1834 | 54 | 1 | 27 | 0.050 [-0.080, 0.183] |
| hybrid_rerank+asof | 100 | 27 | 25 | 48 | 0 | 0.020 [-0.132, 0.158] | 0.27 | 0.52 | 0.00022 | 0.00083 | 3734 | 1.00 | 124 | 1943 | 60 | 0 | 27 | 0.020 [-0.132, 0.158] |
| agentic+asof | 100 | 47 | 31 | 22 | 0 | 0.160 [-0.010, 0.333] | 0.47 | 0.78 | 0.00047 | 0.00100 | 2807 | 3.02 | 213 | 4021 | 138 | 3 | 50 | 0.220 [0.039, 0.378] |

## multihoprag (dev, n=100): main1

| system | n | correct | wrong | abstained | errors | penalised [95% CI] | accuracy | coverage | $/q | $/correct | median ms | calls | ans chars | tok in/q | tok out/q | judge: flipped | correct (judge) | penalised (judge) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 32 | 27 | 41 | 0 | 0.050 [-0.118, 0.208] | 0.32 | 0.59 | 0.00005 | 0.00017 | 952 | 1.00 | 171 | 175 | 74 | 0 | 32 | 0.050 [-0.118, 0.208] |
| bm25 | 100 | 52 | 11 | 37 | 0 | 0.410 [0.253, 0.548] | 0.52 | 0.63 | 0.00046 | 0.00089 | 1005 | 1.00 | 167 | 4244 | 73 | 2 | 54 | 0.450 [0.311, 0.586] |
| vector | 100 | 41 | 6 | 53 | 0 | 0.350 [0.216, 0.472] | 0.41 | 0.47 | 0.00044 | 0.00108 | 1113 | 1.00 | 109 | 4161 | 53 | 0 | 41 | 0.350 [0.216, 0.472] |
| hybrid | 100 | 52 | 12 | 36 | 0 | 0.400 [0.263, 0.521] | 0.52 | 0.64 | 0.00046 | 0.00088 | 1171 | 1.00 | 163 | 4238 | 71 | 2 | 54 | 0.440 [0.308, 0.557] |
| hybrid_rerank | 100 | 44 | 12 | 44 | 0 | 0.320 [0.187, 0.447] | 0.44 | 0.56 | 0.00046 | 0.00106 | 13519 | 1.00 | 144 | 4316 | 65 | 2 | 46 | 0.360 [0.223, 0.485] |
| agentic | 100 | 39 | 34 | 27 | 0 | 0.050 [-0.121, 0.211] | 0.39 | 0.73 | 0.00057 | 0.00146 | 2232 | 2.37 | 238 | 5009 | 138 | 6 | 45 | 0.170 [0.000, 0.327] |
| engine | 100 | 25 | 10 | 65 | 0 | 0.150 [0.032, 0.266] | 0.25 | 0.35 | 0.00054 | 0.00214 | 4995 | 1.00 | 49 | 4762 | 119 | 3 | 28 | 0.210 [0.100, 0.326] |
| oracle | 100 | 54 | 8 | 38 | 0 | 0.460 [0.316, 0.600] | 0.54 | 0.62 | 0.00016 | 0.00030 | 865 | 1.00 | 136 | 1299 | 62 | 2 | 56 | 0.500 [0.368, 0.630] |
| bm25+asof | 100 | 49 | 13 | 38 | 0 | 0.360 [0.200, 0.500] | 0.49 | 0.62 | 0.00046 | 0.00094 | 1083 | 1.00 | 169 | 4244 | 74 | 5 | 54 | 0.460 [0.318, 0.598] |
| vector+asof | 100 | 42 | 6 | 52 | 0 | 0.360 [0.233, 0.473] | 0.42 | 0.48 | 0.00044 | 0.00106 | 1185 | 1.00 | 110 | 4161 | 54 | 0 | 42 | 0.360 [0.233, 0.473] |
| hybrid+asof | 100 | 49 | 12 | 39 | 0 | 0.370 [0.227, 0.500] | 0.49 | 0.61 | 0.00046 | 0.00094 | 1311 | 1.00 | 154 | 4238 | 69 | 2 | 51 | 0.410 [0.275, 0.533] |
| hybrid_rerank+asof | 100 | 46 | 8 | 46 | 0 | 0.380 [0.261, 0.495] | 0.46 | 0.54 | 0.00046 | 0.00101 | 13828 | 1.00 | 138 | 4316 | 64 | 2 | 48 | 0.420 [0.306, 0.531] |
| agentic+asof | 100 | 40 | 31 | 29 | 0 | 0.090 [-0.093, 0.259] | 0.40 | 0.71 | 0.00061 | 0.00153 | 2513 | 2.45 | 243 | 5398 | 144 | 9 | 49 | 0.270 [0.126, 0.419] |

## hoh (dev, n=100): main1

| system | n | correct | wrong | abstained | errors | penalised [95% CI] | accuracy | coverage | $/q | $/correct | median ms | calls | ans chars | tok in/q | tok out/q | judge: flipped | correct (judge) | penalised (judge) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 8 | 81 | 11 | 0 | -0.730 [-0.850, -0.610] | 0.08 | 0.89 | 0.00005 | 0.00063 | 827 | 1.00 | 185 | 107 | 79 | 3 | 11 | -0.670 [-0.790, -0.530] |
| bm25 | 100 | 42 | 51 | 7 | 0 | -0.090 [-0.280, 0.080] | 0.42 | 0.93 | 0.00010 | 0.00024 | 994 | 1.00 | 89 | 759 | 49 | 3 | 45 | -0.030 [-0.220, 0.150] |
| vector | 100 | 38 | 41 | 21 | 0 | -0.030 [-0.210, 0.140] | 0.38 | 0.79 | 0.00011 | 0.00028 | 3248 | 1.00 | 73 | 861 | 43 | 3 | 41 | 0.030 [-0.150, 0.210] |
| hybrid | 100 | 43 | 49 | 8 | 0 | -0.060 [-0.240, 0.110] | 0.43 | 0.92 | 0.00011 | 0.00025 | 6706 | 1.00 | 93 | 811 | 50 | 3 | 46 | 0.000 [-0.180, 0.170] |
| hybrid_rerank | 100 | 36 | 48 | 16 | 0 | -0.120 [-0.300, 0.050] | 0.36 | 0.84 | 0.00010 | 0.00028 | 9418 | 1.00 | 78 | 787 | 45 | 3 | 39 | -0.060 [-0.240, 0.110] |
| agentic | 100 | 42 | 53 | 5 | 0 | -0.110 [-0.300, 0.070] | 0.42 | 0.95 | 0.00015 | 0.00035 | 9439 | 2.11 | 129 | 1011 | 90 | 4 | 46 | -0.030 [-0.230, 0.150] |
| engine | 100 | 82 | 7 | 11 | 0 | 0.750 [0.640, 0.850] | 0.82 | 0.89 | 0.00016 | 0.00019 | 998 | 1.00 | 80 | 1324 | 49 | 7 | 89 | 0.890 [0.830, 0.940] |
| oracle | 100 | 82 | 8 | 10 | 0 | 0.740 [0.620, 0.850] | 0.82 | 0.90 | 0.00005 | 0.00006 | 735 | 1.00 | 102 | 212 | 52 | 7 | 89 | 0.880 [0.810, 0.940] |
| bm25+asof | 100 | 85 | 7 | 8 | 0 | 0.780 [0.670, 0.880] | 0.85 | 0.92 | 0.00010 | 0.00012 | 950 | 1.00 | 93 | 796 | 50 | 6 | 91 | 0.900 [0.830, 0.960] |
| vector+asof | 100 | 81 | 6 | 13 | 0 | 0.750 [0.630, 0.860] | 0.81 | 0.87 | 0.00011 | 0.00014 | 3706 | 1.00 | 84 | 891 | 48 | 6 | 87 | 0.870 [0.800, 0.930] |
| hybrid+asof | 100 | 85 | 8 | 7 | 0 | 0.770 [0.650, 0.880] | 0.85 | 0.93 | 0.00011 | 0.00013 | 2920 | 1.00 | 88 | 842 | 48 | 7 | 92 | 0.910 [0.840, 0.970] |
| hybrid_rerank+asof | 100 | 76 | 10 | 14 | 0 | 0.660 [0.530, 0.780] | 0.76 | 0.86 | 0.00011 | 0.00014 | 3816 | 1.00 | 81 | 822 | 46 | 9 | 85 | 0.840 [0.760, 0.910] |
| agentic+asof | 100 | 85 | 10 | 5 | 0 | 0.750 [0.620, 0.870] | 0.85 | 0.95 | 0.00015 | 0.00018 | 3419 | 2.11 | 131 | 1055 | 92 | 7 | 92 | 0.890 [0.800, 0.960] |

## Engine (main1)

**musique**: correct 16, wrong 11, abstained 73. Abstention types {'unsupported': 35, 'no_source': 22, 'not_valid_at_date': 14, 'false_premise': 1, 'outside_coverage': 1}; the draft's own ABSTAIN (no claim): 37; rejected after claim verification: 36; rows with a reply cut at the cap: 0.
  Engine vs hybrid correctness: engine-only 3, hybrid-only 12, both 13; discordance (b+c)/n = 0.15.
**multihoprag**: correct 25, wrong 10, abstained 65. Abstention types {'not_valid_at_date': 3, 'unsupported': 52, 'no_source': 4, 'false_premise': 1, 'outside_coverage': 4, 'conflict': 1}; the draft's own ABSTAIN (no claim): 11; rejected after claim verification: 54; rows with a reply cut at the cap: 0.
  Engine vs hybrid correctness: engine-only 3, hybrid-only 30, both 22; discordance (b+c)/n = 0.33.
**hoh**: correct 82, wrong 7, abstained 11. Abstention types {'not_valid_at_date': 3, 'unsupported': 6, 'no_source': 2}; the draft's own ABSTAIN (no claim): 6; rejected after claim verification: 5; rows with a reply cut at the cap: 0.
  Engine vs hybrid correctness: engine-only 46, hybrid-only 7, both 36; discordance (b+c)/n = 0.53.

### (i) Correct answer rejected after verification (dev; the draft contains a gold string, no truncated claim): 24 cases; five shown

- musique `musique:2hop__147212_60904` gold ['Jack Michel']; `unsupported`; claims (support, text): [(0.064, 'The rehabilitation center where Hank Moonjean died is not identified in the passages, because they only say he'), (0.003, "The Rehabilitation Center at Hollywood Hills is owned by Jack Michel, but nothing ties it to Moonjean's death,")]
- musique `musique:3hop1__139773_88110_21193` gold ['LZX']; `unsupported`; claims (support, text): [(0.004, "The TV channel hosting Rachel Maddow's show is MSNBC, but none of the passages state MSNBC's original partners"), (0.008, "The passages do say LZX is used in Microsoft's CAB format, but they do not link Microsoft to MSNBC.")]
- multihoprag `multihoprag:q0896` gold ['no']; `unsupported`; claims (support, text): [(0.038, "Yes, the Fortune article says Franke's daughter was repeatedly told she was evil and possessed and that the pu"), (0.085, 'However, the passages do not say that The Verge article exonerates Catherine Tan of accusations of sexual hara')]
- multihoprag `multihoprag:q2266` gold ['Sam Altman']; `unsupported`; claims (support, text): [(0.492, 'Sam Altman is the individual described: he was ousted as OpenAI\'s CEO after a review found he was "not consist'), (0.034, 'However, the passages do not mention The Age, and nothing in them states he was not ousted by co-founders of a')]
- hoh `hoh:93985#0@2024-06-01` gold ['3 days']; `unsupported`; claims (support, text): [(0.158, 'The CPC (candidate preparation course) lasts 3 days for Royal Marine Commando applicants.')]

### (ii) Wrong answer accepted (dev): 28 cases; five shown

- musique `musique:2hop__151750_141308` gold ['Apple Corps']; "Magic Christian Music is the debut album by Badfinger, released on Apple Records. [t1]"; claims (support, text): [(0.985, 'Magic Christian Music is the debut album by Badfinger, released on Apple Records.'), (0.0, 'The passages do not state which company Apple Records is part of, so I cannot answer the question.')]
- musique `musique:3hop1__45612_502967_84283` gold ['Warner Music Group', 'Warner Music']; "The guitarist on the Top Gun theme was Steve Stevens. [t2]"; claims (support, text): [(0.938, 'The guitarist on the Top Gun theme was Steve Stevens.'), (0.0, 'The passages do not state who owns the record label of Steve Stevens, so the answer cannot be determined from ')]
- multihoprag `multihoprag:q0672` gold ['Sam Bankman-Fried']; "He is on trial for wire fraud and related charges over allegedly stealing customer funds. [t1][t2][t5]"; claims (support, text): [(0.0, 'The individual is Sam Bankman-Fried, founder of FTX and Alameda Research.'), (0.691, 'He is on trial for wire fraud and related charges over allegedly stealing customer funds.')]
- hoh `hoh:1606930#0@2024-06-01` gold ['122,311 - 61,198 males and 61,113 females']; "The estimated population of Bukittinggi as at mid 2022 is 122,311, comprising 61,198 males and 61,113 females. [t1]"; claims (support, text): [(0.969, 'The estimated population of Bukittinggi as at mid 2022 is 122,311, comprising 61,198 males and 61,113 females.')]
- hoh `hoh:74765960#0@2024-09-01` gold ["Bad Bunny's World's Hottest Tour"]; "Bad Bunny has the highest-grossing concert tour by a Latin artist, with World's Hottest Tour. [t1]"; claims (support, text): [(0.984, "Bad Bunny has the highest-grossing concert tour by a Latin artist, with World's Hottest Tour.")]

## Engine A/B arms against main1 (paired per question; penalised-score difference arm - main1 [95% bootstrap CI]; counts correct/wrong/abstained)

| arm | scope | main1 engine | arm | difference | calls/q (arm) | USD/q (arm) |
|---|---|---|---|---|---|---|
| armA-v1 | pooled | 0.317 (123, 28, 149) | 0.263 (112, 33, 155) | -0.053 [-0.107, +0.000] | 1.00 | 0.00031 |
| armA-v1 | musique | 0.050 (16, 11, 73) | 0.020 (12, 10, 78) | -0.030 [-0.120, +0.060] | 1.00 | 0.00028 |
| armA-v1 | multihoprag | 0.150 (25, 10, 65) | 0.100 (24, 14, 62) | -0.050 [-0.170, +0.070] | 1.00 | 0.00052 |
| armA-v1 | hoh | 0.750 (82, 7, 11) | 0.670 (76, 9, 15) | -0.080 [-0.170, +0.000] | 1.00 | 0.00015 |
| armB-answersq | pooled | 0.317 (123, 28, 149) | 0.343 (119, 16, 165) | +0.027 [-0.010, +0.067] | 1.47 | 0.00034 |
| armB-answersq | musique | 0.050 (16, 11, 73) | 0.100 (13, 3, 84) | +0.050 [-0.010, +0.120] | 1.26 | 0.00030 |
| armB-answersq | multihoprag | 0.150 (25, 10, 65) | 0.190 (25, 6, 69) | +0.040 [-0.040, +0.130] | 1.28 | 0.00055 |
| armB-answersq | hoh | 0.750 (82, 7, 11) | 0.740 (81, 7, 12) | -0.010 [-0.050, +0.030] | 1.88 | 0.00018 |

## Run-to-run variance: main1 vs main2 (identical settings; no seed exists)

| system | pooled penalised main1 | main2 | difference main2 - main1 | share of questions whose outcome changed (pooled) | per dataset: difference / changed |
|---|---|---|---|---|---|
| bm25 | 0.090 | 0.130 | +0.040 | 4% | musi +0.06 / 6%; mult +0.06 / 6%; hoh +0.00 / 0% |
| closed_book | -0.400 | -0.403 | -0.003 | 12% | musi +0.02 / 14%; mult +0.02 / 17%; hoh -0.05 / 4% |
| hybrid | 0.120 | 0.110 | -0.010 | 7% | musi +0.04 / 10%; mult -0.05 / 8%; hoh -0.02 / 3% |
| vector | 0.113 | 0.113 | +0.000 | 7% | musi +0.01 / 6%; mult +0.06 / 10%; hoh -0.07 / 5% |
| oracle | 0.580 | 0.577 | -0.003 | 9% | musi -0.03 / 15%; mult +0.00 / 9%; hoh +0.02 / 4% |
| engine | 0.317 | 0.303 | -0.013 | 11% | musi +0.00 / 15%; mult -0.02 / 15%; hoh -0.02 / 4% |
| bm25+asof | 0.380 | 0.383 | +0.003 | 4% | musi +0.02 / 4%; mult +0.00 / 6%; hoh -0.01 / 3% |
| vector+asof | 0.387 | 0.360 | -0.027 | 4% | musi -0.04 / 6%; mult -0.04 / 5%; hoh +0.00 / 2% |
| agentic | 0.003 | 0.023 | +0.020 | 22% | musi +0.09 / 26%; mult -0.07 / 32%; hoh +0.04 / 7% |
| hybrid+asof | 0.390 | 0.407 | +0.017 | 6% | musi +0.01 / 11%; mult +0.02 / 6%; hoh +0.02 / 1% |
| hybrid_rerank | 0.060 | 0.073 | +0.013 | 9% | musi +0.05 / 13%; mult +0.01 / 8%; hoh -0.02 / 6% |
| hybrid_rerank+asof | 0.353 | 0.327 | -0.027 | 8% | musi -0.05 / 7%; mult -0.06 / 12%; hoh +0.03 / 4% |
| agentic+asof | 0.333 | 0.283 | -0.050 | 20% | musi -0.07 / 29%; mult -0.08 / 25%; hoh +0.00 / 5% |

## k sweep (pooled penalised score (c-w)/n, n=300; thinking off, source shown)

| system | k4 | default (k8; agentic 5) | k12 |
|---|---|---|---|
| bm25 | 0.080 (101c/77w) | 0.090 (113c/86w) | 0.103 (121c/90w) |
| vector | 0.050 (85c/70w) | 0.113 (103c/69w) | 0.077 (104c/81w) |
| hybrid | 0.073 (96c/74w) | 0.120 (120c/84w) | 0.147 (125c/81w) |
| hybrid_rerank | -0.003 (89c/90w) | 0.060 (103c/85w) | 0.097 (117c/88w) |
| agentic | -0.023 (115c/122w) | 0.003 (123c/122w) | 0.027 (116c/108w) |
