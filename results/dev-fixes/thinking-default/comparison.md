## Thinking disabled (main1) vs thinking default with a 4096-token cap: per dataset and system (n = 100)

c/w/a = correct / wrong / abstained under the containment grade; pen = penalised score (c - w)/n; J = the same with the judge-assisted grade.

| dataset | system | off: c/w/a | off: pen | off: pen J | default: c/w/a | default: pen | default: pen J |
|---|---|---|---|---|---|---|---|
| musique | closed_book | 21/73/6 | -0.520 | -0.420 | 28/28/44 | +0.000 | +0.120 |
| musique | bm25 | 19/24/57 | -0.050 | -0.010 | 20/5/75 | +0.150 | +0.170 |
| musique | hybrid | 25/23/52 | +0.020 | +0.040 | 21/9/70 | +0.120 | +0.180 |
| musique | hybrid+asof | 26/23/51 | +0.030 | +0.050 | 23/8/69 | +0.150 | +0.230 |
| musique | agentic | 42/35/23 | +0.070 | +0.090 | 47/15/38 | +0.320 | +0.480 |
| musique | engine | 16/11/73 | +0.050 | +0.070 | 16/8/76 | +0.080 | +0.140 |
| multihoprag | closed_book | 32/27/41 | +0.050 | +0.050 | 37/6/57 | +0.310 | +0.310 |
| multihoprag | bm25 | 52/11/37 | +0.410 | +0.450 | 57/19/24 | +0.380 | +0.440 |
| multihoprag | hybrid | 52/12/36 | +0.400 | +0.440 | 58/18/24 | +0.400 | +0.420 |
| multihoprag | hybrid+asof | 49/12/39 | +0.370 | +0.410 | 60/17/23 | +0.430 | +0.490 |
| multihoprag | agentic | 39/34/27 | +0.050 | +0.170 | 64/22/14 | +0.420 | +0.440 |
| multihoprag | engine | 25/10/65 | +0.150 | +0.210 | 27/12/61 | +0.150 | +0.150 |
| hoh | closed_book | 8/81/11 | -0.730 | -0.670 | 6/45/49 | -0.390 | -0.250 |
| hoh | bm25 | 42/51/7 | -0.090 | -0.030 | 39/55/6 | -0.160 | -0.080 |
| hoh | hybrid | 43/49/8 | -0.060 | +0.000 | 42/52/6 | -0.100 | -0.020 |
| hoh | hybrid+asof | 85/8/7 | +0.770 | +0.910 | 80/12/8 | +0.680 | +0.900 |
| hoh | agentic | 42/53/5 | -0.110 | -0.030 | 44/53/3 | -0.090 | +0.010 |
| hoh | engine | 82/7/11 | +0.750 | +0.890 | 80/11/9 | +0.690 | +0.810 |
| pooled | closed_book | 61/181/58 | -0.400 | -0.347 | 71/79/150 | -0.027 | +0.060 |
| pooled | bm25 | 113/86/101 | +0.090 | +0.137 | 116/79/105 | +0.123 | +0.177 |
| pooled | hybrid | 120/84/96 | +0.120 | +0.160 | 121/79/100 | +0.140 | +0.193 |
| pooled | hybrid+asof | 160/43/97 | +0.390 | +0.457 | 163/37/100 | +0.420 | +0.540 |
| pooled | agentic | 123/122/55 | +0.003 | +0.077 | 155/90/55 | +0.217 | +0.310 |
| pooled | engine | 123/28/149 | +0.317 | +0.390 | 123/31/146 | +0.307 | +0.367 |

## Paired differences (penalised score, engine minus system, per question) under each condition [95% bootstrap CI]; primary grade and judge-assisted grade

| scope | pair | off primary | off judge | default primary | default judge |
|---|---|---|---|---|---|
| musique | engine - hybrid | +0.030 [-0.100, +0.150] | +0.030 [-0.100, +0.150] | -0.040 [-0.140, +0.060] | -0.040 [-0.130, +0.050] |
| musique | engine - agentic | -0.020 [-0.200, +0.160] | -0.020 [-0.200, +0.160] | -0.240 [-0.370, -0.110] | -0.340 [-0.470, -0.220] |
| multihoprag | engine - hybrid | -0.250 [-0.400, -0.110] | -0.230 [-0.370, -0.100] | -0.250 [-0.420, -0.090] | -0.270 [-0.440, -0.110] |
| multihoprag | engine - agentic | +0.100 [-0.060, +0.250] | +0.040 [-0.130, +0.200] | -0.270 [-0.440, -0.110] | -0.290 [-0.460, -0.130] |
| hoh | engine - hybrid | +0.810 [+0.610, +1.010] | +0.890 [+0.690, +1.090] | +0.790 [+0.600, +0.970] | +0.830 [+0.630, +1.030] |
| hoh | engine - agentic | +0.860 [+0.650, +1.060] | +0.920 [+0.720, +1.120] | +0.780 [+0.590, +0.970] | +0.800 [+0.600, +0.990] |
| pooled | engine - hybrid | +0.197 [+0.093, +0.310] | +0.230 [+0.127, +0.337] | +0.167 [+0.063, +0.270] | +0.173 [+0.067, +0.280] |
| pooled | engine - agentic | +0.313 [+0.197, +0.423] | +0.313 [+0.203, +0.427] | +0.090 [-0.017, +0.200] | +0.057 [-0.053, +0.170] |

## Cost, tokens and truncation (pooled over the three datasets)

| system | condition | $/question | $/correct (primary) | output tokens / call | visible tokens / call (chars/3.5) | hidden share | replies cut at the cap | calls |
|---|---|---|---|---|---|---|---|---|
| closed_book | off | 0.00006 | 0.00029 | 90 | 66 | 27% | 0 | 300 |
| closed_book | default | 0.00023 | 0.00095 | 424 | 37 | 91% | 0 | 300 |
| bm25 | off | 0.00026 | 0.00069 | 57 | 38 | 34% | 0 | 300 |
| bm25 | default | 0.00036 | 0.00093 | 258 | 38 | 85% | 0 | 300 |
| hybrid | off | 0.00026 | 0.00065 | 57 | 38 | 34% | 0 | 300 |
| hybrid | default | 0.00036 | 0.00089 | 260 | 37 | 86% | 0 | 300 |
| hybrid+asof | off | 0.00026 | 0.00049 | 57 | 37 | 35% | 0 | 300 |
| hybrid+asof | default | 0.00036 | 0.00066 | 257 | 38 | 85% | 0 | 300 |
| agentic | off | 0.00039 | 0.00095 | 49 | 34 | 31% | 0 | 747 |
| agentic | default | 0.00078 | 0.00151 | 180 | 28 | 85% | 0 | 876 |
| engine | off | 0.00033 | 0.00080 | 89 | 70 | 22% | 0 | 300 |
| engine | default | 0.00044 | 0.00107 | 310 | 54 | 82% | 0 | 300 |
