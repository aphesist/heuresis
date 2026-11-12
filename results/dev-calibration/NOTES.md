# Dev calibration run: notes

Calibration data on the **dev split only** (100 questions per dataset). These are not results of the benchmark. Model `claude-haiku-5-5`; repository `main` at 8a0f281 (after the change that stops sending `temperature`; sampling is the API default, so this run is not at temperature 0). Hashes unchanged: locked 3c23fecd42520db9a36c3208d285d6d96465f42e1c2ef8e31d2d2b2d79de1b71, surface b7e767ecd37764e19220985ea959a16c650a2aec104f7f3a867013de736ed58f, prompts 1498745bcecca370bd94caef482d685ab41c84890ab5a208320f2dcbacc2a462. Tests: 487 passed, 16 skipped on 6f7cec6; 489 passed, 16 skipped on 8a0f281.

## Commands (in the order run)

```
pip install -e ".[dev,local,bench]" pyarrow ; python3 -m pytest -q
PYTHONPATH=src python3 -m heuresis.cli hash
# datasets: heuresis.bench.datasets.load(name, root="data") for musique, multihoprag, hoh (HF_HUB_OFFLINE=0)
# stores, real local embedder onnx:intfloat/multilingual-e5-small (scripts/pilot/p1_ingest.py):
for d in musique multihoprag hoh; do python3 scripts/pilot/p1_ingest.py $d; done      # -> runs/pilot-dev/$d/store.sqlite
# step B, dry run (offline fakes, own hash-embedded stores in runs/dev-calibration/dry/<ds>):
python -m heuresis.bench.run --dataset D --split dev --systems closed_book,bm25,vector,hybrid,hybrid_rerank,agentic,engine,oracle --out runs/dev-calibration/dry/D --dry-run --time-aware-variants --workers 4   # musique, multihoprag; hoh with --limit 10 (the full hoh dry run was stopped at 286 rows: too slow)
# step C, smoke (paid): first attempt (smoke/) failed on the temperature parameter, $0; after 8a0f281:
python -m heuresis.bench.run --dataset musique --split dev --systems closed_book,hybrid,engine --out runs/dev-calibration/smoke2 --limit 5 --paid --cap 3 --margin-usd 0.25 --ledger runs/dev-calibration/ledger.jsonl --model claude-haiku-5-5 --workers 4
# extra smoke for cost extrapolation (5 questions per dataset; closed_book,bm25,hybrid,agentic,engine,oracle) in smoke3/<ds>
# step D, each run in its own folder, store.sqlite = a copy of runs/pilot-dev/<ds>/store.sqlite (real embedder), same command shape:
python -m heuresis.bench.run --dataset D --split dev --systems SYSTEMS --out runs/dev-calibration/CFG/D --paid --cap 3 --margin-usd 0.25 --ledger runs/dev-calibration/ledger.jsonl --model claude-haiku-5-5 --workers 4 [FLAGS]
#   main:      SYSTEMS=closed_book,bm25,vector,hybrid,hybrid_rerank,agentic,engine,oracle  FLAGS=--time-aware-variants   (k=8, agentic 5 per search)
#   base-k4:   SYSTEMS=bm25,vector,hybrid,hybrid_rerank  --k 4
#   agent-k4:  SYSTEMS=agentic  --agent-k 4
#   base-k12:  SYSTEMS=bm25,vector,hybrid,hybrid_rerank  --k 12
#   agent-k12: NOT RUN (budget, see below)
# step E
python -m heuresis.bench.report runs/dev-calibration/CFG/{musique,multihoprag,hoh} --iters 1000 --family-out runs/dev-calibration/CFG/family.md
python -m heuresis.bench.calibrate runs/dev-calibration/main/{musique,multihoprag,hoh}      # -> calibration-grid.txt
python3 analyze.py     # reads the run folders and the ledger only; wrote analysis.md (spend, per-dataset tables, engine analysis, k sweep)
```

Store used by every paid run: the real-embedder store `runs/pilot-dev/<dataset>/store.sqlite` (copied into each run folder). Only the dry runs used hash-embedded stores. The agentic per-search default is 5 (not 8), so its grid is 4 / 5 / 12.

## Report

**Did not match expectations / failures.**
- The first paid attempt failed: the API rejects `temperature` for `claude-haiku-5-5` (HTTP 400). Spend $0. Fixed on main (8a0f281) by the orchestrating session; the error rows of that attempt were not carried forward (new folders).
- `agent-k12` was not run: after `base-k12` the ledger showed $2.61 spent of the $2.75 usable (cap 3 minus margin 0.25), and agentic at k=12 was estimated at about $0.35. I stopped the driver as soon as it moved on (no call made, spend unchanged). So the agentic per-search grid is 4 / 5 only.
- Full hoh dry run was not completed (see commands); the pipeline was checked with `--limit 10` (130 rows, no errors); musique and multihoprag dry runs were complete (1300 rows each, no errors).
- Error rows in all paid runs that count: 0.
- **Output-cap hits are common** (answer cap 600 output tokens per call, tokens per call >= 590): closed_book 41/100 on musique (34 of them have empty text and count as abstained), engine 34/100 on multihoprag (7 on musique, 0 on hoh), hybrid 16/100 on multihoprag. Haiku writes long replies here. A cut-off reply counts as an abstention for the baselines and, for the engine, a draft cut mid-sentence gives a claim with `exists: false`. This depresses the baselines' and the engine's scores in a way the pre-registration did not model. Engine drafts that are not ABSTAIN and end unterminated: multihoprag 10 of 20, musique 1 of 22, hoh 0 of 95.

**Spend (ledger, includes the smoke tests):** total $2.6068 over all runs (cap $3, margin $0.25). By system and tokens: see the first table of `analysis.md` (regenerated at the end, so it includes everything). Smoke tests $0.039 (smoke2 + smoke3). Main run $1.535 (musique 0.501, multihoprag 0.838, hoh 0.196). k=4 baselines $0.274, agentic k=4 $0.213, k=12 baselines $0.545.

**Per dataset and system on dev (n=100):** all in the tables below (correct / wrong / abstained, penalised score with bootstrap interval, accuracy, coverage, cost per question and per correct answer, median latency, mean calls, mean answer length, mean tokens in/out per question). Errors per system: 0 everywhere. Latency is wall-clock with 4 workers, indicative only.

**Calibration grid (45 pairs, pooled n=300, engine only):** argmax support 0.2, partial 0.1, penalised score 0.2467. Packaged pair (0.5, 0.3): 0.2000. Worst pair 0.1833 (0.9, 0.5 and higher). The grid is flat: 4 of 45 pairs lie within 0.02 of the best (support 0.1, 0.2, 0.3), 6 within 0.03, 35 within 0.05; every pair with support 0.2 to 0.8 and partial at most 0.4 is between 0.200 and 0.247. The best-versus-default gap (0.047) is about 14 questions out of 300 (correct 90 vs 75, wrong 16 vs 15).

**k that did best on dev (pooled penalised score, n=300, k4 / default / k12):** bm25 0.070 / 0.130 / 0.147 (best k=12); vector 0.100 / 0.120 / 0.110 (best k=8); hybrid 0.113 / 0.120 / 0.147 (best k=12); hybrid_rerank 0.073 / 0.117 / 0.147 (best k=12); agentic (per search) 0.240 at 4 / 0.220 at 5 (best 4, k=12 not run). Differences are within a few points at n=300; the intervals are wide.

**Engine abstentions (main run, k=8):** musique 86 of 100 abstained (unsupported 64, no_source 13, outside_coverage 6, not_valid_at_date 3); multihoprag 86 (unsupported 54, no_source 19, false_premise 11, outside_coverage 2); hoh 38 (unsupported 33, not_valid_at_date 1, conflict 1, no_source 1, false_premise 1, needs_input 1). On musique and multihoprag most abstentions (78 and 68) have no claim at all: the model itself wrote ABSTAIN (the engine's draft prompt). Verifier-level rejections after claims: musique 8, multihoprag 18, hoh 34. Engine correct/wrong: musique 8/6, multihoprag 12/2, hoh 55/7. Five dev examples of each kind, with claim entailment scores (support) and the abstention type, are in the "Engine" section below. In several hoh rejections the entailer gave 0.002 to 0.12 to a claim that restates the gold fact (e.g. "Delta Virginis has 1.4 times the mass of the Sun", 0.002); the accepted wrong answers were mostly claims that are true of the passage but do not answer the question (support 0.89 to 0.99).

**Discordance engine vs hybrid (correctness, dev, n=100 each; hybrid is the non-time-aware baseline):** musique 0.18 (engine-only correct 1, hybrid-only 17, both 7); multihoprag 0.23 (0, 23, both 12); hoh 0.41 (28, 13, both 27). For hoh the time-aware copy `hybrid+asof` (exploratory) scores 84 correct, so against it the engine would be behind; see `main/hoh/results.json` (`exploratory_paired`).

**Branch / commit:** branch `dev-calibration`, commit 75f15954ea8571b2996db0db5860f28251eec28c (last line of this file). Nothing was pushed to main; no pull request.

**Could not do:** agent-k12 (budget); full hoh dry run; the examples in (i) are drawn from abstentions whose draft contains a gold-answer string and none of whose claims is truncated (string match, so not necessarily a correct answer).


# Tables (regenerated after all runs)

## Spend (ledger)

Total $2.6068 over 8466 calls (includes smoke tests).

| tag | calls | tokens in | tokens out | USD |
|---|---|---|---|---|
| agentic | 1814 | 2977974 | 322362 | 0.4590 |
| bm25 | 915 | 2038847 | 224823 | 0.3163 |
| hybrid_rerank | 900 | 2057875 | 220573 | 0.3161 |
| hybrid | 920 | 2040166 | 219963 | 0.3140 |
| vector | 900 | 1988213 | 198204 | 0.2979 |
| agentic+asof | 862 | 1513532 | 156162 | 0.2294 |
| engine | 320 | 845338 | 90535 | 0.1298 |
| hybrid_rerank+asof | 300 | 687693 | 74872 | 0.1062 |
| bm25+asof | 300 | 674093 | 75250 | 0.1050 |
| hybrid+asof | 300 | 671016 | 73129 | 0.1037 |
| vector+asof | 300 | 665080 | 68571 | 0.1008 |
| closed_book | 320 | 42272 | 124836 | 0.0666 |
| oracle | 315 | 238244 | 76273 | 0.0620 |

## musique (dev, n=100): main run, k=8, agentic 5 per search

| system | n | correct | wrong | abstained | errors | penalised [95% CI] | accuracy | coverage | $/q | $/correct | median ms | calls | ans chars | tok in/q | tok out/q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 24 | 18 | 58 | 0 | 0.060 [-0.069, 0.186] | 0.24 | 0.42 | 0.00025 | 0.00103 | 2752 | 1.00 | 91 | 112 | 473 |
| bm25 | 100 | 18 | 4 | 78 | 0 | 0.140 [0.051, 0.232] | 0.18 | 0.22 | 0.00031 | 0.00170 | 1348 | 1.00 | 61 | 1841 | 243 |
| vector | 100 | 20 | 6 | 74 | 0 | 0.140 [0.042, 0.235] | 0.20 | 0.26 | 0.00029 | 0.00145 | 1469 | 1.00 | 58 | 1739 | 232 |
| hybrid | 100 | 24 | 6 | 70 | 0 | 0.180 [0.079, 0.273] | 0.24 | 0.30 | 0.00030 | 0.00124 | 1448 | 1.00 | 60 | 1771 | 242 |
| hybrid_rerank | 100 | 27 | 6 | 67 | 0 | 0.210 [0.110, 0.313] | 0.27 | 0.33 | 0.00032 | 0.00120 | 3418 | 1.00 | 79 | 1880 | 271 |
| agentic | 100 | 50 | 14 | 36 | 0 | 0.360 [0.214, 0.505] | 0.50 | 0.64 | 0.00088 | 0.00175 | 5144 | 3.46 | 129 | 5300 | 693 |
| engine | 100 | 8 | 6 | 86 | 0 | 0.020 [-0.059, 0.094] | 0.08 | 0.14 | 0.00037 | 0.00463 | 1816 | 1.00 | 13 | 2228 | 295 |
| oracle | 100 | 61 | 5 | 34 | 0 | 0.560 [0.437, 0.676] | 0.61 | 0.66 | 0.00020 | 0.00033 | 1437 | 1.00 | 122 | 737 | 255 |
| bm25+asof | 100 | 18 | 3 | 79 | 0 | 0.150 [0.059, 0.235] | 0.18 | 0.21 | 0.00030 | 0.00169 | 1400 | 1.00 | 65 | 1841 | 240 |
| vector+asof | 100 | 20 | 7 | 73 | 0 | 0.130 [0.038, 0.229] | 0.20 | 0.27 | 0.00029 | 0.00145 | 1392 | 1.00 | 66 | 1739 | 230 |
| hybrid+asof | 100 | 21 | 7 | 72 | 0 | 0.140 [0.039, 0.240] | 0.21 | 0.28 | 0.00030 | 0.00141 | 1518 | 1.00 | 57 | 1771 | 238 |
| hybrid_rerank+asof | 100 | 25 | 6 | 69 | 0 | 0.190 [0.088, 0.290] | 0.25 | 0.31 | 0.00032 | 0.00127 | 3362 | 1.00 | 72 | 1880 | 261 |
| agentic+asof | 100 | 47 | 12 | 41 | 0 | 0.350 [0.210, 0.490] | 0.47 | 0.59 | 0.00089 | 0.00190 | 5392 | 3.52 | 119 | 5454 | 694 |

## multihoprag (dev, n=100): main run, k=8, agentic 5 per search

| system | n | correct | wrong | abstained | errors | penalised [95% CI] | accuracy | coverage | $/q | $/correct | median ms | calls | ans chars | tok in/q | tok out/q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 39 | 6 | 55 | 0 | 0.330 [0.198, 0.448] | 0.39 | 0.45 | 0.00018 | 0.00047 | 1773 | 1.00 | 99 | 176 | 331 |
| bm25 | 100 | 39 | 4 | 57 | 0 | 0.350 [0.240, 0.468] | 0.39 | 0.43 | 0.00061 | 0.00155 | 2234 | 1.00 | 86 | 4175 | 375 |
| vector | 100 | 33 | 3 | 64 | 0 | 0.300 [0.198, 0.400] | 0.33 | 0.36 | 0.00057 | 0.00174 | 1920 | 1.00 | 70 | 4091 | 328 |
| hybrid | 100 | 35 | 5 | 60 | 0 | 0.300 [0.194, 0.402] | 0.35 | 0.40 | 0.00060 | 0.00172 | 2310 | 1.00 | 86 | 4168 | 368 |
| hybrid_rerank | 100 | 34 | 5 | 61 | 0 | 0.290 [0.176, 0.408] | 0.34 | 0.39 | 0.00061 | 0.00179 | 6941 | 1.00 | 77 | 4246 | 365 |
| agentic | 100 | 58 | 17 | 25 | 0 | 0.410 [0.259, 0.543] | 0.58 | 0.75 | 0.00125 | 0.00216 | 4751 | 3.06 | 195 | 9133 | 678 |
| engine | 100 | 12 | 2 | 86 | 0 | 0.100 [0.027, 0.182] | 0.12 | 0.14 | 0.00068 | 0.00565 | 2852 | 1.00 | 2 | 4583 | 440 |
| oracle | 100 | 48 | 8 | 44 | 0 | 0.400 [0.264, 0.524] | 0.48 | 0.56 | 0.00030 | 0.00062 | 1956 | 1.00 | 127 | 1300 | 331 |
| bm25+asof | 100 | 42 | 4 | 54 | 0 | 0.380 [0.263, 0.495] | 0.42 | 0.46 | 0.00061 | 0.00145 | 2111 | 1.00 | 95 | 4175 | 380 |
| vector+asof | 100 | 34 | 4 | 62 | 0 | 0.300 [0.186, 0.423] | 0.34 | 0.38 | 0.00057 | 0.00169 | 1908 | 1.00 | 73 | 4091 | 331 |
| hybrid+asof | 100 | 38 | 3 | 59 | 0 | 0.350 [0.236, 0.461] | 0.38 | 0.41 | 0.00060 | 0.00158 | 2215 | 1.00 | 77 | 4168 | 367 |
| hybrid_rerank+asof | 100 | 33 | 4 | 63 | 0 | 0.290 [0.181, 0.398] | 0.33 | 0.37 | 0.00061 | 0.00184 | 6833 | 1.00 | 69 | 4246 | 368 |
| agentic+asof | 100 | 56 | 17 | 27 | 0 | 0.390 [0.242, 0.535] | 0.56 | 0.73 | 0.00119 | 0.00213 | 4453 | 2.98 | 172 | 8654 | 657 |

## hoh (dev, n=100): main run, k=8, agentic 5 per search

| system | n | correct | wrong | abstained | errors | penalised [95% CI] | accuracy | coverage | $/q | $/correct | median ms | calls | ans chars | tok in/q | tok out/q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| closed_book | 100 | 7 | 43 | 50 | 0 | -0.360 [-0.470, -0.250] | 0.07 | 0.50 | 0.00019 | 0.00272 | 2085 | 1.00 | 95 | 108 | 359 |
| bm25 | 100 | 41 | 51 | 8 | 0 | -0.100 [-0.280, 0.080] | 0.41 | 0.92 | 0.00013 | 0.00032 | 1096 | 1.00 | 87 | 688 | 125 |
| vector | 100 | 37 | 45 | 18 | 0 | -0.080 [-0.260, 0.090] | 0.37 | 0.82 | 0.00013 | 0.00036 | 2434 | 1.00 | 80 | 790 | 109 |
| hybrid | 100 | 40 | 52 | 8 | 0 | -0.120 [-0.300, 0.060] | 0.40 | 0.92 | 0.00014 | 0.00034 | 5185 | 1.00 | 95 | 740 | 126 |
| hybrid_rerank | 100 | 36 | 51 | 13 | 0 | -0.150 [-0.330, 0.030] | 0.36 | 0.87 | 0.00013 | 0.00036 | 7022 | 1.00 | 84 | 716 | 116 |
| agentic | 100 | 42 | 53 | 5 | 0 | -0.110 [-0.300, 0.070] | 0.42 | 0.95 | 0.00021 | 0.00049 | 6595 | 2.22 | 111 | 1077 | 200 |
| engine | 100 | 55 | 7 | 38 | 0 | 0.480 [0.350, 0.590] | 0.55 | 0.62 | 0.00017 | 0.00031 | 1039 | 1.00 | 56 | 1144 | 118 |
| oracle | 100 | 61 | 9 | 30 | 0 | 0.520 [0.380, 0.650] | 0.61 | 0.70 | 0.00009 | 0.00015 | 940 | 1.00 | 72 | 213 | 141 |
| bm25+asof | 100 | 86 | 9 | 5 | 0 | 0.770 [0.650, 0.880] | 0.86 | 0.95 | 0.00014 | 0.00016 | 1102 | 1.00 | 96 | 725 | 133 |
| vector+asof | 100 | 79 | 9 | 12 | 0 | 0.700 [0.580, 0.830] | 0.79 | 0.88 | 0.00014 | 0.00018 | 2279 | 1.00 | 89 | 820 | 124 |
| hybrid+asof | 100 | 84 | 7 | 9 | 0 | 0.770 [0.650, 0.870] | 0.84 | 0.91 | 0.00014 | 0.00017 | 2295 | 1.00 | 90 | 771 | 127 |
| hybrid_rerank+asof | 100 | 80 | 9 | 11 | 0 | 0.710 [0.590, 0.830] | 0.80 | 0.89 | 0.00014 | 0.00017 | 3317 | 1.00 | 91 | 751 | 120 |
| agentic+asof | 100 | 87 | 10 | 3 | 0 | 0.770 [0.650, 0.880] | 0.87 | 0.97 | 0.00021 | 0.00024 | 3029 | 2.12 | 120 | 1027 | 210 |

## Engine (main run)

**musique**: correct 8, wrong 6, abstained 86. Abstention types: {'unsupported': 64, 'no_source': 13, 'not_valid_at_date': 3, 'outside_coverage': 6}. Abstained with no claim at all (the draft itself abstained or was unparseable): 78; abstained after claim verification: 8. Drafts that are not ABSTAIN: 22, of which 1 do not end in a sentence terminator or CONFIDENCE line (likely cut at the output cap).
  Engine vs hybrid correctness: engine-only correct 1, hybrid-only correct 17, both 7, discordance (b+c)/n = 0.18.
**multihoprag**: correct 12, wrong 2, abstained 86. Abstention types: {'unsupported': 54, 'no_source': 19, 'false_premise': 11, 'outside_coverage': 2}. Abstained with no claim at all (the draft itself abstained or was unparseable): 68; abstained after claim verification: 18. Drafts that are not ABSTAIN: 20, of which 10 do not end in a sentence terminator or CONFIDENCE line (likely cut at the output cap).
  Engine vs hybrid correctness: engine-only correct 0, hybrid-only correct 23, both 12, discordance (b+c)/n = 0.23.
**hoh**: correct 55, wrong 7, abstained 38. Abstention types: {'unsupported': 33, 'not_valid_at_date': 1, 'conflict': 1, 'no_source': 1, 'false_premise': 1, 'needs_input': 1}. Abstained with no claim at all (the draft itself abstained or was unparseable): 4; abstained after claim verification: 34. Drafts that are not ABSTAIN: 95, of which 0 do not end in a sentence terminator or CONFIDENCE line (likely cut at the output cap).
  Engine vs hybrid correctness: engine-only correct 28, hybrid-only correct 13, both 27, discordance (b+c)/n = 0.41.

### (i) Correct answer rejected (dev only): the draft contains a gold answer string but the engine abstained after verification

55 abstentions have a draft containing a gold string (string match, so not necessarily a correct answer); 43 of them have no truncated claim (all claims exist), and examples are drawn from those.

- musique `musique:2hop__16581_16569` gold ['Kalb']; abstention `unsupported`; claims (support, text): [(0.138, "Mu'awiyah introduced the postal service in Umayyad lands."), (0.252, 'His wife Maysum was the daughter of the chief of the Kalb tribe.')]
- multihoprag `multihoprag:q2276` gold ['no']; abstention `unsupported`; claims (support, text): [(0.062, "No, the McTominay article says he is United's top scorer this season with six goals."), (0.172, "The MLS article says Wondolowski leads the league's career scoring chart with 171 goals, which is a different ")]
- hoh `hoh:1469805#0@2024-07-01` gold ['13']; abstention `unsupported`; claims (support, text): [(0.005, 'Avanti West Coast operates 13 sets of British Rail Class 221 trains.')]
- hoh `hoh:43710666#0@2024-08-01` gold ['121']; abstention `unsupported`; claims (support, text): [(0.032, "As of May 2024, 121 songs are registered under B.I's name with KOMCA.")]
- hoh `hoh:93985#0@2024-06-01` gold ['3 days']; abstention `unsupported`; claims (support, text): [(0.003, 'The CPC (candidate preparation course) lasts 3 days for Royal Marines applicants.')]

### (ii) Wrong answer accepted (dev only)

15 wrong-and-answered cases in total.

- musique `musique:2hop__242938_18803` gold ['trying to find a potential buyer for all of its operations in Finland', 'FIN']; answered: "Hubbert worked at the Shell research lab in Houston, Texas. [t1]"; claims (support, text): [(0.977, 'Hubbert worked at the Shell research lab in Houston, Texas.'), (0.153, 'In April 2010, Shell announced it was trying to find a potential buyer for all of its Finnish operations.')]
- musique `musique:3hop1__145427_106426_157788` gold ['Yamanote Line loop', 'Yamanote Line']; answered: "Japan's Movie Eye Entertainment produced The Longest Night in Shanghai, and You Wenhui was born in Shanghai. [t1][t2]"; claims (support, text): [(0.888, "Japan's Movie Eye Entertainment produced The Longest Night in Shanghai, and You Wenhui was born in Shanghai."), (0.186, 'One railway line in Japan is the Yamanote Line, a loop line in Tokyo.')]
- multihoprag `multihoprag:q0599` gold ['Yes']; answered: "The Sporting News tracker says Dylan Cease, Corbin Burnes, and Tyler Glasnow are starters who could be moved this winter. [t1]"; claims (support, text): [(0.514, 'The Sporting News tracker says Dylan Cease, Corbin Burnes, and Tyler Glasnow are starters who could be moved t'), (0.0, 'The passages do not name Essentially Sports as the source, but one article says the Angels will have a hard ti')]
- hoh `hoh:36639582#0@2024-10-01` gold ['Peter Storey']; answered: "Storey taught divinity at the MCSA seminary, the John Wesley College, from 1994 to 1997. [t1]"; claims (support, text): [(0.986, 'Storey taught divinity at the MCSA seminary, the John Wesley College, from 1994 to 1997.')]
- hoh `hoh:6858494#0@2024-07-01` gold ['Geoffrey Chaucer']; answered: "Geoffrey Chaucer's literary works may be considered sex comedies. [t1]"; claims (support, text): [(0.968, "Geoffrey Chaucer's literary works may be considered sex comedies.")]

## k sweep (pooled over 3 datasets, n=300; penalised = (correct - wrong)/n, errors counted wrong)

| system | k4 | default (k8; agentic 5) | k12 | rows per k |
|---|---|---|---|---|
| bm25 | 0.070 (82c/61w) | 0.130 (98c/59w) | 0.147 (107c/63w) | [300, 300, 300] |
| vector | 0.100 (80c/50w) | 0.120 (90c/54w) | 0.110 (91c/58w) | [300, 300, 300] |
| hybrid | 0.113 (90c/56w) | 0.120 (99c/63w) | 0.147 (109c/65w) | [300, 300, 300] |
| hybrid_rerank | 0.073 (83c/61w) | 0.117 (97c/62w) | 0.147 (104c/60w) | [300, 300, 300] |
| agentic | 0.240 (148c/76w) | 0.220 (150c/84w) | not run | [300, 300, 0] |


Results commit on branch `dev-calibration`: 75f15954ea8571b2996db0db5860f28251eec28c (this line added in a following commit).


---

# Phase 1 report (dev fixes)

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
