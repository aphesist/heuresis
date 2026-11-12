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
