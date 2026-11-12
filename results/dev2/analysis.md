# dev2 analysis (calibration data on the dev2 split, n = 100 per dataset; NOT benchmark results)

## Condition `off` (thinking disabled)

| scope | system | n | c/w/a | penalised [95% CI] | c/w/a (judge) | penalised (judge) | $/q | $/correct | calls | searches | median ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| musique | closed_book | 100 | 21/77/2 | -0.560 [-0.710, -0.390] | 21/77/2 | -0.560 | 0.00007 | 0.00034 | 1.00 | 0.00 | 1075 |
| musique | bm25 | 100 | 18/27/55 | -0.090 [-0.220, +0.050] | 19/26/55 | -0.070 | 0.00022 | 0.00120 | 1.00 | 1.00 | 878 |
| musique | hybrid | 100 | 23/23/54 | +0.000 [-0.130, +0.130] | 23/23/54 | +0.000 | 0.00021 | 0.00093 | 1.00 | 1.00 | 975 |
| musique | hybrid_rerank | 100 | 22/30/48 | -0.080 [-0.220, +0.060] | 22/30/48 | -0.080 | 0.00023 | 0.00103 | 1.00 | 1.00 | 3473 |
| musique | agentic | 100 | 41/35/24 | +0.060 [-0.120, +0.230] | 44/32/24 | +0.120 | 0.00046 | 0.00111 | 3.00 | 2.00 | 3133 |
| musique | engine | 100 | 29/11/60 | +0.180 [+0.060, +0.310] | 31/9/60 | +0.220 | 0.00095 | 0.00328 | 2.54 | 2.54 | 3006 |
| musique | engine_single | 100 | 12/12/76 | +0.000 [-0.100, +0.100] | 13/11/76 | +0.020 | 0.00030 | 0.00246 | 1.00 | 1.00 | 1457 |
| musique | hybrid+asof | 100 | 20/27/53 | -0.070 [-0.210, +0.060] | 22/25/53 | -0.030 | 0.00021 | 0.00106 | 1.00 | 1.00 | 1026 |
| musique | agentic+asof | 100 | 36/37/27 | -0.010 [-0.180, +0.160] | 38/35/27 | +0.030 | 0.00044 | 0.00121 | 2.96 | 1.96 | 2875 |
| multihoprag | closed_book | 100 | 36/25/39 | +0.110 [-0.040, +0.260] | 36/25/39 | +0.110 | 0.00005 | 0.00015 | 1.00 | 0.00 | 1014 |
| multihoprag | bm25 | 100 | 48/8/44 | +0.400 [+0.270, +0.520] | 50/6/44 | +0.440 | 0.00046 | 0.00096 | 1.00 | 1.00 | 997 |
| multihoprag | hybrid | 100 | 51/8/41 | +0.430 [+0.310, +0.550] | 53/6/41 | +0.470 | 0.00046 | 0.00091 | 1.00 | 1.00 | 1268 |
| multihoprag | hybrid_rerank | 100 | 47/5/48 | +0.420 [+0.310, +0.530] | 47/5/48 | +0.420 | 0.00047 | 0.00101 | 1.00 | 1.00 | 11786 |
| multihoprag | agentic | 100 | 45/34/21 | +0.110 [-0.060, +0.280] | 50/29/21 | +0.210 | 0.00062 | 0.00138 | 2.42 | 1.42 | 2365 |
| multihoprag | engine | 100 | 36/46/18 | -0.100 [-0.290, +0.080] | 48/34/18 | +0.140 | 0.00085 | 0.00237 | 1.40 | 1.40 | 5250 |
| multihoprag | engine_single | 100 | 23/13/64 | +0.100 [-0.020, +0.210] | 28/8/64 | +0.200 | 0.00053 | 0.00232 | 1.00 | 1.00 | 4291 |
| multihoprag | hybrid+asof | 100 | 51/8/41 | +0.430 [+0.310, +0.550] | 53/6/41 | +0.470 | 0.00046 | 0.00091 | 1.00 | 1.00 | 1289 |
| multihoprag | agentic+asof | 100 | 41/29/30 | +0.120 [-0.040, +0.280] | 45/25/30 | +0.200 | 0.00062 | 0.00152 | 2.45 | 1.45 | 2380 |
| hoh | closed_book | 100 | 6/85/9 | -0.790 [-0.890, -0.680] | 7/84/9 | -0.770 | 0.00005 | 0.00082 | 1.00 | 0.00 | 855 |
| hoh | bm25 | 100 | 33/58/9 | -0.250 [-0.420, -0.080] | 45/46/9 | -0.010 | 0.00010 | 0.00030 | 1.00 | 1.00 | 859 |
| hoh | hybrid | 100 | 34/53/13 | -0.190 [-0.370, +0.000] | 45/42/13 | +0.030 | 0.00011 | 0.00031 | 1.00 | 1.00 | 4222 |
| hoh | hybrid_rerank | 100 | 34/46/20 | -0.120 [-0.290, +0.070] | 44/36/20 | +0.080 | 0.00010 | 0.00030 | 1.00 | 1.00 | 10581 |
| hoh | agentic | 100 | 36/59/5 | -0.230 [-0.410, -0.040] | 46/49/5 | -0.030 | 0.00015 | 0.00042 | 2.18 | 1.18 | 10647 |
| hoh | engine | 100 | 78/16/6 | +0.620 [+0.480, +0.770] | 92/2/6 | +0.900 | 0.00017 | 0.00022 | 1.07 | 1.07 | 953 |
| hoh | engine_single | 100 | 67/16/17 | +0.510 [+0.360, +0.650] | 79/4/17 | +0.750 | 0.00016 | 0.00023 | 1.00 | 1.00 | 1016 |
| hoh | hybrid+asof | 100 | 73/14/13 | +0.590 [+0.440, +0.730] | 84/3/13 | +0.810 | 0.00011 | 0.00015 | 1.00 | 1.00 | 2967 |
| hoh | agentic+asof | 100 | 77/15/8 | +0.620 [+0.470, +0.760] | 88/4/8 | +0.840 | 0.00015 | 0.00019 | 2.12 | 1.12 | 3001 |
| pooled | closed_book | 300 | 63/187/50 | -0.413 [-0.507, -0.323] | 64/186/50 | -0.407 | 0.00006 | 0.00028 | 1.00 | 0.00 | 982 |
| pooled | bm25 | 300 | 99/93/108 | +0.020 [-0.070, +0.113] | 114/78/108 | +0.120 | 0.00026 | 0.00078 | 1.00 | 1.00 | 898 |
| pooled | hybrid | 300 | 108/84/108 | +0.080 [-0.017, +0.170] | 121/71/108 | +0.167 | 0.00026 | 0.00072 | 1.00 | 1.00 | 1384 |
| pooled | hybrid_rerank | 300 | 103/81/116 | +0.073 [-0.013, +0.160] | 113/71/116 | +0.140 | 0.00027 | 0.00078 | 1.00 | 1.00 | 7913 |
| pooled | agentic | 300 | 122/128/50 | -0.020 [-0.127, +0.083] | 140/110/50 | +0.100 | 0.00041 | 0.00101 | 2.53 | 1.53 | 3302 |
| pooled | engine | 300 | 143/73/84 | +0.233 [+0.143, +0.327] | 171/45/84 | +0.420 | 0.00066 | 0.00138 | 1.67 | 1.67 | 2782 |
| pooled | engine_single | 300 | 102/41/157 | +0.203 [+0.127, +0.277] | 120/23/157 | +0.323 | 0.00033 | 0.00097 | 1.00 | 1.00 | 1344 |
| pooled | hybrid+asof | 300 | 144/49/107 | +0.317 [+0.240, +0.403] | 159/34/107 | +0.417 | 0.00026 | 0.00054 | 1.00 | 1.00 | 1399 |
| pooled | agentic+asof | 300 | 154/81/65 | +0.243 [+0.143, +0.340] | 171/64/65 | +0.357 | 0.00040 | 0.00078 | 2.51 | 1.51 | 2841 |

### Paired differences (penalised score, engine minus X; 95% bootstrap CI), primary / judge-assisted

| scope | pair | primary | judge |
|---|---|---|---|
| musique | engine - hybrid | +0.180 [+0.020, +0.340] | +0.220 [+0.080, +0.370] |
| musique | engine - agentic | +0.120 [-0.070, +0.310] | +0.100 [-0.070, +0.270] |
| musique | engine - hybrid+asof | +0.250 [+0.080, +0.410] | +0.250 [+0.100, +0.400] |
| musique | engine - agentic+asof | +0.190 [+0.010, +0.360] | +0.190 [+0.010, +0.370] |
| musique | engine - engine_single | +0.180 [+0.060, +0.310] | +0.200 [+0.070, +0.320] |
| multihoprag | engine - hybrid | -0.530 [-0.720, -0.350] | -0.330 [-0.520, -0.130] |
| multihoprag | engine - agentic | -0.210 [-0.420, -0.010] | -0.070 [-0.280, +0.150] |
| multihoprag | engine - hybrid+asof | -0.530 [-0.720, -0.350] | -0.330 [-0.520, -0.150] |
| multihoprag | engine - agentic+asof | -0.220 [-0.450, +0.000] | -0.060 [-0.310, +0.200] |
| multihoprag | engine - engine_single | -0.200 [-0.380, -0.010] | -0.060 [-0.250, +0.130] |
| hoh | engine - hybrid | +0.810 [+0.610, +1.010] | +0.870 [+0.690, +1.050] |
| hoh | engine - agentic | +0.850 [+0.640, +1.060] | +0.930 [+0.740, +1.140] |
| hoh | engine - hybrid+asof | +0.030 [-0.090, +0.150] | +0.090 [-0.010, +0.190] |
| hoh | engine - agentic+asof | +0.000 [-0.120, +0.110] | +0.060 [-0.010, +0.140] |
| hoh | engine - engine_single | +0.110 [+0.020, +0.210] | +0.150 [+0.080, +0.240] |
| pooled | engine - hybrid | +0.153 [+0.040, +0.277] | +0.253 [+0.137, +0.367] |
| pooled | engine - agentic | +0.253 [+0.127, +0.377] | +0.320 [+0.193, +0.447] |
| pooled | engine - hybrid+asof | -0.083 [-0.183, +0.010] | +0.003 [-0.090, +0.093] |
| pooled | engine - agentic+asof | -0.010 [-0.113, +0.090] | +0.063 [-0.040, +0.170] |
| pooled | engine - engine_single | +0.030 [-0.053, +0.110] | +0.097 [+0.013, +0.177] |

### Engine details

- **musique** (n=100): answered in one call 13%; mean model searches 1.54; abstention types (all) {'no_source': 11, 'unsupported': 43, 'not_valid_at_date': 4, 'outside_coverage': 2}; on answerable {'no_source': 11, 'unsupported': 43, 'not_valid_at_date': 4, 'outside_coverage': 2}; claims checked 136 in 100 verified answers, failing `exists` 45 (no mark at all 45, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 13; answered 40, AURC (answered, by grade) 0.155, accuracy at 50% / 80% of answered by grade 0.80 / 0.78; replies cut at max_tokens 0
- **multihoprag** (n=100): answered in one call 65%; mean model searches 0.40; abstention types (all) {'no_source': 15, 'unsupported': 12, 'outside_coverage': 2, 'not_valid_at_date': 1}; on answerable {'no_source': 5, 'unsupported': 11, 'outside_coverage': 2}; claims checked 196 in 100 verified answers, failing `exists` 60 (no mark at all 60, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 13; answered 70, AURC (answered, by grade) 0.583, accuracy at 50% / 80% of answered by grade 0.40 / 0.36; replies cut at max_tokens 0
- **hoh** (n=100): answered in one call 94%; mean model searches 0.07; abstention types (all) {'unsupported': 2, 'no_source': 3, 'not_valid_at_date': 1}; on answerable {'unsupported': 2, 'no_source': 3, 'not_valid_at_date': 1}; claims checked 122 in 100 verified answers, failing `exists` 13 (no mark at all 13, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 6; answered 94, AURC (answered, by grade) 0.171, accuracy at 50% / 80% of answered by grade 0.87 / 0.84; replies cut at max_tokens 0
- **pooled** (n=300): answered in one call 57%; mean model searches 0.67; abstention types (all) {'no_source': 29, 'unsupported': 57, 'not_valid_at_date': 6, 'outside_coverage': 4}; on answerable {'no_source': 19, 'unsupported': 56, 'not_valid_at_date': 5, 'outside_coverage': 4}; claims checked 454 in 300 verified answers, failing `exists` 118 (no mark at all 118, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 32; answered 204, AURC (answered, by grade) 0.223, accuracy at 50% / 80% of answered by grade 0.84 / 0.69; replies cut at max_tokens 0

Zero-truncation check (calls stopped at max_tokens, per system): {'closed_book': 0, 'bm25': 0, 'hybrid': 0, 'engine_single': 0, 'hybrid_rerank': 0, 'engine': 0, 'agentic': 0, 'hybrid+asof': 0, 'agentic+asof': 0}; error rows: {'closed_book': 0, 'bm25': 0, 'hybrid': 0, 'engine_single': 0, 'hybrid_rerank': 0, 'engine': 0, 'agentic': 0, 'hybrid+asof': 0, 'agentic+asof': 0}

## Condition `default` (default thinking, draft.max_tokens 4096)

| scope | system | n | c/w/a | penalised [95% CI] | c/w/a (judge) | penalised (judge) | $/q | $/correct | calls | searches | median ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| musique | closed_book | 100 | 26/31/43 | -0.050 [-0.200, +0.100] | 28/29/43 | -0.010 | 0.00029 | 0.00113 | 1.00 | 0.00 | 2771 |
| musique | bm25 | 100 | 15/6/79 | +0.090 [+0.000, +0.180] | 17/4/79 | +0.130 | 0.00031 | 0.00207 | 1.00 | 1.00 | 1372 |
| musique | hybrid | 100 | 21/5/74 | +0.160 [+0.070, +0.260] | 23/3/74 | +0.200 | 0.00031 | 0.00150 | 1.00 | 1.00 | 1529 |
| musique | hybrid_rerank | 100 | 24/5/71 | +0.190 [+0.090, +0.290] | 25/4/71 | +0.210 | 0.00033 | 0.00138 | 1.00 | 1.00 | 3603 |
| musique | agentic | 100 | 55/8/37 | +0.470 [+0.350, +0.600] | 60/3/37 | +0.570 | 0.00092 | 0.00167 | 3.53 | 2.53 | 5278 |
| musique | engine | 100 | 47/21/32 | +0.260 [+0.100, +0.420] | 55/13/32 | +0.420 | 0.00177 | 0.00377 | 3.06 | 3.06 | 6232 |
| musique | engine_single | 100 | 13/8/79 | +0.050 [-0.040, +0.140] | 13/8/79 | +0.050 | 0.00041 | 0.00317 | 1.00 | 1.00 | 1935 |
| musique | hybrid+asof | 100 | 20/7/73 | +0.130 [+0.040, +0.230] | 22/5/73 | +0.170 | 0.00031 | 0.00155 | 1.00 | 1.00 | 1519 |
| musique | agentic+asof | 100 | 48/9/43 | +0.390 [+0.270, +0.520] | 52/5/43 | +0.470 | 0.00094 | 0.00195 | 3.55 | 2.55 | 5436 |
| multihoprag | closed_book | 100 | 44/9/47 | +0.350 [+0.230, +0.470] | 45/8/47 | +0.370 | 0.00020 | 0.00045 | 1.00 | 0.00 | 1966 |
| multihoprag | bm25 | 100 | 59/15/26 | +0.440 [+0.290, +0.590] | 59/15/26 | +0.440 | 0.00060 | 0.00101 | 1.00 | 1.00 | 1876 |
| multihoprag | hybrid | 100 | 56/10/34 | +0.460 [+0.320, +0.590] | 57/9/34 | +0.480 | 0.00059 | 0.00106 | 1.00 | 1.00 | 1881 |
| multihoprag | hybrid_rerank | 100 | 49/10/41 | +0.390 [+0.260, +0.520] | 50/9/41 | +0.410 | 0.00061 | 0.00125 | 1.00 | 1.00 | 6893 |
| multihoprag | agentic | 100 | 66/20/14 | +0.460 [+0.300, +0.620] | 71/15/14 | +0.560 | 0.00122 | 0.00185 | 3.03 | 2.03 | 4962 |
| multihoprag | engine | 100 | 42/52/6 | -0.100 [-0.280, +0.090] | 54/40/6 | +0.140 | 0.00159 | 0.00378 | 1.88 | 1.88 | 5795 |
| multihoprag | engine_single | 100 | 27/10/63 | +0.170 [+0.060, +0.280] | 32/5/63 | +0.270 | 0.00069 | 0.00254 | 1.00 | 1.00 | 4373 |
| multihoprag | hybrid+asof | 100 | 55/10/35 | +0.450 [+0.310, +0.580] | 56/9/35 | +0.470 | 0.00059 | 0.00107 | 1.00 | 1.00 | 2161 |
| multihoprag | agentic+asof | 100 | 70/20/10 | +0.500 [+0.340, +0.660] | 75/15/10 | +0.600 | 0.00120 | 0.00171 | 2.98 | 1.98 | 4769 |
| hoh | closed_book | 100 | 5/40/55 | -0.350 [-0.460, -0.240] | 8/37/55 | -0.290 | 0.00021 | 0.00412 | 1.00 | 0.00 | 2048 |
| hoh | bm25 | 100 | 36/56/8 | -0.200 [-0.380, -0.020] | 48/44/8 | +0.040 | 0.00014 | 0.00040 | 1.00 | 1.00 | 1130 |
| hoh | hybrid | 100 | 34/55/11 | -0.210 [-0.390, -0.030] | 45/44/11 | +0.010 | 0.00016 | 0.00046 | 1.00 | 1.00 | 2729 |
| hoh | hybrid_rerank | 100 | 32/50/18 | -0.180 [-0.350, +0.000] | 43/39/18 | +0.040 | 0.00015 | 0.00046 | 1.00 | 1.00 | 4035 |
| hoh | agentic | 100 | 37/58/5 | -0.210 [-0.400, -0.020] | 50/45/5 | +0.050 | 0.00024 | 0.00066 | 2.37 | 1.37 | 4787 |
| hoh | engine | 100 | 77/19/4 | +0.580 [+0.420, +0.720] | 90/6/4 | +0.840 | 0.00027 | 0.00034 | 1.18 | 1.18 | 1189 |
| hoh | engine_single | 100 | 70/15/15 | +0.550 [+0.410, +0.690] | 81/4/15 | +0.770 | 0.00018 | 0.00026 | 1.00 | 1.00 | 1084 |
| hoh | hybrid+asof | 100 | 74/15/11 | +0.590 [+0.440, +0.730] | 86/3/11 | +0.830 | 0.00016 | 0.00021 | 1.00 | 1.00 | 2573 |
| hoh | agentic+asof | 100 | 83/12/5 | +0.710 [+0.570, +0.830] | 92/3/5 | +0.890 | 0.00024 | 0.00029 | 2.27 | 1.27 | 3103 |
| pooled | closed_book | 300 | 75/80/145 | -0.017 [-0.100, +0.067] | 81/74/145 | +0.023 | 0.00023 | 0.00093 | 1.00 | 0.00 | 2290 |
| pooled | bm25 | 300 | 110/77/113 | +0.110 [+0.023, +0.203] | 124/63/113 | +0.203 | 0.00035 | 0.00096 | 1.00 | 1.00 | 1425 |
| pooled | hybrid | 300 | 111/70/119 | +0.137 [+0.053, +0.223] | 125/56/119 | +0.230 | 0.00035 | 0.00096 | 1.00 | 1.00 | 2087 |
| pooled | hybrid_rerank | 300 | 105/65/130 | +0.133 [+0.047, +0.213] | 118/52/130 | +0.220 | 0.00036 | 0.00104 | 1.00 | 1.00 | 4963 |
| pooled | agentic | 300 | 158/86/56 | +0.240 [+0.143, +0.330] | 181/63/56 | +0.393 | 0.00080 | 0.00151 | 2.98 | 1.98 | 4958 |
| pooled | engine | 300 | 166/92/42 | +0.247 [+0.150, +0.347] | 199/59/42 | +0.467 | 0.00121 | 0.00218 | 2.04 | 2.04 | 4569 |
| pooled | engine_single | 300 | 110/33/157 | +0.257 [+0.183, +0.330] | 126/17/157 | +0.363 | 0.00043 | 0.00116 | 1.00 | 1.00 | 1929 |
| pooled | hybrid+asof | 300 | 149/32/119 | +0.390 [+0.310, +0.460] | 164/17/119 | +0.490 | 0.00035 | 0.00071 | 1.00 | 1.00 | 2018 |
| pooled | agentic+asof | 300 | 201/41/58 | +0.533 [+0.450, +0.613] | 219/23/58 | +0.653 | 0.00079 | 0.00118 | 2.93 | 1.93 | 4293 |

### Paired differences (penalised score, engine minus X; 95% bootstrap CI), primary / judge-assisted

| scope | pair | primary | judge |
|---|---|---|---|
| musique | engine - hybrid | +0.100 [-0.040, +0.240] | +0.220 [+0.100, +0.350] |
| musique | engine - agentic | -0.210 [-0.360, -0.050] | -0.150 [-0.280, -0.020] |
| musique | engine - hybrid+asof | +0.130 [+0.000, +0.270] | +0.250 [+0.120, +0.380] |
| musique | engine - agentic+asof | -0.130 [-0.270, +0.030] | -0.050 [-0.180, +0.080] |
| musique | engine - engine_single | +0.210 [+0.050, +0.360] | +0.370 [+0.230, +0.520] |
| multihoprag | engine - hybrid | -0.560 [-0.740, -0.380] | -0.340 [-0.530, -0.160] |
| multihoprag | engine - agentic | -0.560 [-0.770, -0.340] | -0.420 [-0.620, -0.220] |
| multihoprag | engine - hybrid+asof | -0.550 [-0.750, -0.360] | -0.330 [-0.530, -0.140] |
| multihoprag | engine - agentic+asof | -0.600 [-0.810, -0.390] | -0.460 [-0.670, -0.250] |
| multihoprag | engine - engine_single | -0.270 [-0.460, -0.070] | -0.130 [-0.320, +0.050] |
| hoh | engine - hybrid | +0.790 [+0.590, +0.990] | +0.830 [+0.640, +1.030] |
| hoh | engine - agentic | +0.790 [+0.580, +1.000] | +0.790 [+0.600, +1.000] |
| hoh | engine - hybrid+asof | -0.010 [-0.140, +0.120] | +0.010 [-0.110, +0.120] |
| hoh | engine - agentic+asof | -0.130 [-0.250, -0.030] | -0.050 [-0.150, +0.050] |
| hoh | engine - engine_single | +0.030 [-0.080, +0.140] | +0.070 [-0.030, +0.160] |
| pooled | engine - hybrid | +0.110 [-0.013, +0.230] | +0.237 [+0.130, +0.357] |
| pooled | engine - agentic | +0.007 [-0.123, +0.137] | +0.073 [-0.047, +0.190] |
| pooled | engine - hybrid+asof | -0.143 [-0.240, -0.047] | -0.023 [-0.113, +0.073] |
| pooled | engine - agentic+asof | -0.287 [-0.387, -0.190] | -0.187 [-0.283, -0.090] |
| pooled | engine - engine_single | -0.010 [-0.100, +0.077] | +0.103 [+0.013, +0.193] |

### Engine details

- **musique** (n=100): answered in one call 22%; mean model searches 2.06; abstention types (all) {'unsupported': 5, 'no_source': 26, 'outside_coverage': 1}; on answerable {'unsupported': 5, 'no_source': 26, 'outside_coverage': 1}; claims checked 150 in 100 verified answers, failing `exists` 26 (no mark at all 26, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 5; answered 68, AURC (answered, by grade) 0.210, accuracy at 50% / 80% of answered by grade 0.82 / 0.72; replies cut at max_tokens 0
- **multihoprag** (n=100): answered in one call 61%; mean model searches 0.88; abstention types (all) {'no_source': 14, 'unsupported': 4}; on answerable {'no_source': 2, 'unsupported': 4}; claims checked 229 in 100 verified answers, failing `exists` 61 (no mark at all 61, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 11; answered 82, AURC (answered, by grade) 0.664, accuracy at 50% / 80% of answered by grade 0.22 / 0.33; replies cut at max_tokens 0
- **hoh** (n=100): answered in one call 94%; mean model searches 0.18; abstention types (all) {'unsupported': 2, 'no_source': 1, 'needs_input': 1}; on answerable {'unsupported': 2, 'no_source': 1, 'needs_input': 1}; claims checked 132 in 100 verified answers, failing `exists` 17 (no mark at all 17, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 10; answered 96, AURC (answered, by grade) 0.145, accuracy at 50% / 80% of answered by grade 0.90 / 0.83; replies cut at max_tokens 0
- **pooled** (n=300): answered in one call 59%; mean model searches 1.04; abstention types (all) {'unsupported': 11, 'no_source': 41, 'outside_coverage': 1, 'needs_input': 1}; on answerable {'unsupported': 11, 'no_source': 29, 'outside_coverage': 1, 'needs_input': 1}; claims checked 511 in 300 verified answers, failing `exists` 104 (no mark at all 104, mark that does not exist 0), `valid_at_date` 0, `numbers_traced` 26; answered 246, AURC (answered, by grade) 0.242, accuracy at 50% / 80% of answered by grade 0.80 / 0.64; replies cut at max_tokens 0

Zero-truncation check (calls stopped at max_tokens, per system): {'bm25': 0, 'hybrid': 0, 'closed_book': 0, 'hybrid_rerank': 0, 'engine_single': 0, 'hybrid+asof': 0, 'agentic': 0, 'agentic+asof': 0, 'engine': 0}; error rows: {'bm25': 0, 'hybrid': 0, 'closed_book': 0, 'hybrid_rerank': 0, 'engine_single': 0, 'hybrid+asof': 0, 'agentic': 0, 'agentic+asof': 0, 'engine': 0}

As-of check, hoh, condition off: 835 passages shown to the engine (all searches), 0 not in force at the question date.
As-of check, hoh, condition default: 890 passages shown to the engine (all searches), 0 not in force at the question date.

## Examples (dev2 only; engine, thinking disabled)

### Engine wrong answers

- `musique:2hop__108158_83769` (musique); gold ["Fred O'Bannion"]; status answered; note `engine status=answered`; calls 2; grade 0.00; text: 'The creator of Push, Nevada is Ben Affleck. [t2] The passages show Affleck played Matt Murdock in Daredevil and Bruce Wayne/Batman in Justice League, but none show him in Dazed and Confused. [t13][t12] Christin Hinojosa and Matthew McConaughey were in Dazed and Confused, but the passages do not link'; draft replies: ['SEARCH: Ben Affleck role in Dazed and Confused', 'The creator of Push, Nevada is Ben Affleck [t2]. The passages show Affleck played Matt Murdock in Daredevil and Bruce Wayne/Batman in Justice League, but none s']
- `musique:2hop__161915_78851` (musique); gold ['Brooklyn Nets NBA', 'Brooklyn']; status answered; note `engine status=partial`; calls 2; grade 0.01; text: "Cream's last concert performance in the passages was at Madison Square Garden in New York. [t9] The Knicks and Liberty play home games there, so you would not see the New York Knicks or New York Liberty at Madison Square Garden... [t4] Among the teams in the passages, the Washington Capitals play at"; draft replies: ['SEARCH: last place Cream performed concert arena', "Cream's last concert performance in the passages was at Madison Square Garden in New York [t9]. The Knicks and Liberty play home games there [t4], so you would "]
- `multihoprag:q0006` (multihoprag); gold ['Yes']; status answered; note `engine status=partial`; calls 1; grade 0.21; text: 'The Twitch article describes a shift from fixed 70/30 deals toward a points-based Partner Plus program and a stronger push on ad revenue. [t1][t4][t8] The Beeper article says Beeper Mini is free for now and subscriptions may return once things stabilize, so it does not describe a comparable revenue-'; draft replies: ['Yes. The Twitch article describes a shift from fixed 70/30 deals toward a points-based Partner Plus program and a stronger push on ad revenue [t1][t4][t8]. The ']
- `multihoprag:q0042` (multihoprag); gold ['Yes']; status answered; note `engine status=partial`; calls 1; grade 0.03; text: 'The TechCrunch article reports that Altman has been telling investors he plans to launch a new venture, with Brockman expected to join. [t5] The Fortune article describes Matt Huang as a former Sequoia partner and Gary Wang as a Bankman-Fried lieutenant, without mentioning any new venture for either'; draft replies: ['Yes. The TechCrunch article reports that Altman has been telling investors he plans to launch a new venture, with Brockman expected to join [t5]. The Fortune ar']
- `hoh:11171413#0@2024-08-01` (hoh); gold ['2/20 and 14/32']; status answered; note `engine status=answered`; calls 1; grade 0.97; text: 'The two asphalt runways at Delaware County Regional Airport are 14/32 and 2/20. [t1]'; draft replies: ['The two asphalt runways at Delaware County Regional Airport are 14/32 and 2/20. [t1]']

### Engine abstentions on answerable questions

- `musique:2hop__10620_79092` (musique); gold ['lava samples have been dated at 341 to 335 million years old']; status abstained; note `engine status=abstained; abstention=no_source`; calls 3; grade 0.00; text: ''; draft replies: ['SEARCH: Historia Regum Britanniae legendary king named Eldol volcano', 'SEARCH: Eldol volcano named after king', 'ABSTAIN no_source: The passages identify Eldol as a legendary king in Historia Regum Britanniae, but no passage links any volcano to Eldol or states when such a']
- `musique:2hop__144303_483189` (musique); gold ['Greek mythology']; status abstained; note `engine status=abstained; abstention=unsupported`; calls 3; grade 0.00; text: ''; draft replies: ['SEARCH: Eutychides birthplace city', 'SEARCH: Eutychides of Sicyon birthplace', 'ABSTAIN unsupported: The passages state Eutychides of Sicyon was a pupil of Lysippus and made a statue of Tyche for Antioch, but do not state where Eutychides w']
- `multihoprag:q0176` (multihoprag); gold ['Yes']; status abstained; note `engine status=abstained; abstention=no_source`; calls 1; grade 0.00; text: ''; draft replies: ["ABSTAIN no_source: The passages cover only The Verge's coverage of Epic v. Google and contain nothing about a Sporting News article or the Michigan Wolverines f"]
- `multihoprag:q0422` (multihoprag); gold ['Yes']; status abstained; note `engine status=abstained; abstention=no_source`; calls 2; grade 0.00; text: ''; draft replies: ['SEARCH: TechCrunch article Sam Bankman-Fried motivations personal gain', 'ABSTAIN no_source: The passages are all from The Verge; none is a TechCrunch article, so I cannot say what the TechCrunch article suggests.']
- `hoh:14966218#0@2024-10-01` (hoh); gold ['586th Flight Test Squadron']; status abstained; note `engine status=abstained; abstention=unsupported`; calls 2; grade 0.00; text: ''; draft replies: ['SEARCH: 30th Space Wing squadron redesignated', 'ABSTAIN unsupported: The passages do not say when the squadron became an element of the 30th Space Wing, so the one-year-later redesignation cannot be determine']


## Both conditions side by side (penalised score, primary / judge-assisted; c/w/a)

| scope | system | off | default |
|---|---|---|---|
| musique | closed_book | 21/77/2: -0.560 / -0.560 | 26/31/43: -0.050 / -0.010 |
| musique | bm25 | 18/27/55: -0.090 / -0.070 | 15/6/79: +0.090 / +0.130 |
| musique | hybrid | 23/23/54: +0.000 / +0.000 | 21/5/74: +0.160 / +0.200 |
| musique | hybrid_rerank | 22/30/48: -0.080 / -0.080 | 24/5/71: +0.190 / +0.210 |
| musique | agentic | 41/35/24: +0.060 / +0.120 | 55/8/37: +0.470 / +0.570 |
| musique | engine | 29/11/60: +0.180 / +0.220 | 47/21/32: +0.260 / +0.420 |
| musique | engine_single | 12/12/76: +0.000 / +0.020 | 13/8/79: +0.050 / +0.050 |
| musique | hybrid+asof | 20/27/53: -0.070 / -0.030 | 20/7/73: +0.130 / +0.170 |
| musique | agentic+asof | 36/37/27: -0.010 / +0.030 | 48/9/43: +0.390 / +0.470 |
| multihoprag | closed_book | 36/25/39: +0.110 / +0.110 | 44/9/47: +0.350 / +0.370 |
| multihoprag | bm25 | 48/8/44: +0.400 / +0.440 | 59/15/26: +0.440 / +0.440 |
| multihoprag | hybrid | 51/8/41: +0.430 / +0.470 | 56/10/34: +0.460 / +0.480 |
| multihoprag | hybrid_rerank | 47/5/48: +0.420 / +0.420 | 49/10/41: +0.390 / +0.410 |
| multihoprag | agentic | 45/34/21: +0.110 / +0.210 | 66/20/14: +0.460 / +0.560 |
| multihoprag | engine | 36/46/18: -0.100 / +0.140 | 42/52/6: -0.100 / +0.140 |
| multihoprag | engine_single | 23/13/64: +0.100 / +0.200 | 27/10/63: +0.170 / +0.270 |
| multihoprag | hybrid+asof | 51/8/41: +0.430 / +0.470 | 55/10/35: +0.450 / +0.470 |
| multihoprag | agentic+asof | 41/29/30: +0.120 / +0.200 | 70/20/10: +0.500 / +0.600 |
| hoh | closed_book | 6/85/9: -0.790 / -0.770 | 5/40/55: -0.350 / -0.290 |
| hoh | bm25 | 33/58/9: -0.250 / -0.010 | 36/56/8: -0.200 / +0.040 |
| hoh | hybrid | 34/53/13: -0.190 / +0.030 | 34/55/11: -0.210 / +0.010 |
| hoh | hybrid_rerank | 34/46/20: -0.120 / +0.080 | 32/50/18: -0.180 / +0.040 |
| hoh | agentic | 36/59/5: -0.230 / -0.030 | 37/58/5: -0.210 / +0.050 |
| hoh | engine | 78/16/6: +0.620 / +0.900 | 77/19/4: +0.580 / +0.840 |
| hoh | engine_single | 67/16/17: +0.510 / +0.750 | 70/15/15: +0.550 / +0.770 |
| hoh | hybrid+asof | 73/14/13: +0.590 / +0.810 | 74/15/11: +0.590 / +0.830 |
| hoh | agentic+asof | 77/15/8: +0.620 / +0.840 | 83/12/5: +0.710 / +0.890 |
| pooled | closed_book | 63/187/50: -0.413 / -0.407 | 75/80/145: -0.017 / +0.023 |
| pooled | bm25 | 99/93/108: +0.020 / +0.120 | 110/77/113: +0.110 / +0.203 |
| pooled | hybrid | 108/84/108: +0.080 / +0.167 | 111/70/119: +0.137 / +0.230 |
| pooled | hybrid_rerank | 103/81/116: +0.073 / +0.140 | 105/65/130: +0.133 / +0.220 |
| pooled | agentic | 122/128/50: -0.020 / +0.100 | 158/86/56: +0.240 / +0.393 |
| pooled | engine | 143/73/84: +0.233 / +0.420 | 166/92/42: +0.247 / +0.467 |
| pooled | engine_single | 102/41/157: +0.203 / +0.323 | 110/33/157: +0.257 / +0.363 |
| pooled | hybrid+asof | 144/49/107: +0.317 / +0.417 | 149/32/119: +0.390 / +0.490 |
| pooled | agentic+asof | 154/81/65: +0.243 / +0.357 | 201/41/58: +0.533 / +0.653 |
