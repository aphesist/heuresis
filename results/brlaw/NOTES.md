# brlaw: the legal citation-integrity test, phase A (free): what was built and how it was checked offline

**No paid call has been made for this work. No `test` or `sealed` split of `musique`, `multihoprag` or `hoh`
was read.** Branch `legal-citations` (from `main` at e1ad84c). Everything here is code, tests, documents,
manifests (ids and hashes) and offline checks. What the test measures and its limits are in
`docs/legal-citation-test.md`; this file is the record of the build and the measurements.

## Sources actually used

| Source | Pin | Licence as written | Files and sha256 |
|---|---|---|---|
| `unicamp-dl/BR-TaxQA-R` (Hugging Face) | revision `9f0f4263928c6152a40f888da3e63375a24bb0f3` | card: `license: cc-by-4.0`; the repository's `LICENSE` file is the CC BY 4.0 legal code | `questions_QA_2024_v1.1.json` `097abfc4...1585`, `referred_legal_documents_QA_2024_v1.1.json` `49ade2d9...aecd3`, `README.md` `55261b1c...e66`, `LICENSE` `9e5f1b3c...d94` (full hashes in `manifest_full.json`). The 7,204 CARF rulings (`acordaos_CARF_2023.json`) were **not** downloaded or used. |
| `github.com/ctresb/leis` | commit `c9f21b4ab11aa0d7ca6fe861d75028e94219c2d6` (2026-11-02) | `LICENSE`: MIT (scripts). README, "Licença": the texts "são atos oficiais do poder público e, pelo art. 8º, I, da Lei nº 9.610/98, não são objeto de proteção autoral". Not redistributed: referenced by commit and URN | `LICENSE` `e71449c8...6d8f`, `README.md` `bd5525d2...15e9` |
| Câmara dos Deputados, `www2.camara.leg.br/legin/` | downloaded 2026-11-12; 168 pages, each with its sha256 in `versioned_fetch_log.json` | no licence statement was read on the pages; the texts are official acts (same Lei 9.610/1998 art. 8, I, as above) | `versioned_fetch_log.json`; pages are not committed |
| Senado Federal open data, `legis.senado.leg.br/dadosabertos/legislacao/...` | queried 2026-11-12, no credentials | public API; no licence statement read | used for the coverage check (`coverage_vs_senate.json`) and to inspect the alteration log; the Câmara's own "Vide Norma(s)" log (which links each amending act) was what the build used, because the Senate's `vides`/`edivs` of the norms tried carried no provision-level items and no text |

Planalto (`planalto.gov.br`) was not used: it did not answer from this environment (empty reply) and is not
in the list of sources. No site refused automated access with a 403 or 429 on the sources used.

The brief says BR-TaxQA-R has 598 questions with article-level gold references. In the v1.1 file the
`all_formatted_references` field names an article for **546** questions (2,012 article references after
expanding ranges such as "10 a 13"); 528 of those questions have at least one gold reference whose unit exists
in the corpus. The 7,204 rulings and the 478 legal documents: 478 documents are in the file as the card says; 425
norms are in the corpus (see "left out").

## Corpus counts (from `manifest_full.json` and `manifest_core.json`; tokens = characters / 4)

| Tier | Norms | Units | Events | Tokens |
|---|---|---|---|---|
| `tax` (BR-TaxQA-R texts; 425 read, 4 stub texts replaced by the federal copy) | 421 | 11,074 | 11,074 | 3,196,108 |
| `federal` (ctresb/leis, as built: leis ordinárias 16,472, decretos-lei 12,169, leis complementares 228, emendas constitucionais 157, leis delegadas 13, the Constitution) | 29,040 read; **28,932 after removing the norms also kept in `tax`** | 209,513 | 211,004 | 31,560,587 |
| `versioned` | 2 base norms (CLT, Lei nº 7.713/1988; 54 + 6 provisions) | 60 | 120 | 14,156 |
| **`brlaw` (full), all tiers merged** | **29,353** | **220,647** | 222,198 | **34,770,851** |
| `brlaw-core` (the embedded subset: `tax`, `versioned`, the Constitution and federal norms dated 1995-01-01 or later) | 6,973 | 64,707 | 65,269 | 14,404,906 |

The brief says "about 29,000 federal norms ... (Constitution, leis, leis complementares, decretos-lei)": the
repository's `federal/` folder holds 207,287 markdown files in 17 folders (109,616 decretos, 21,359 decretos
legislativos, 14,510 decretos não numerados, 7,499 medidas provisórias, 6,574 resoluções do Senado...); the
tier reads only the five folders above plus the Constitution (29,585 files, 545 of which have no article
and were skipped), which matches the brief's "about 29,000". **Decretos, medidas provisórias, resoluções and
all state and municipal law are not in the corpus**: a citation of one is "norm not found" unless it is in
the tax tier (for example Decreto nº 9.580/2018, the RIR/2018).

**Text versions in the federal tier** (header field `versao_texto`): original publication 18,648 norms,
"republicação/retificação" 8,136, **compiled, in force 2,243**, other 13. Only the 2,243 compiled texts carry
amendment annotations.

**Repeal marks.** In the full corpus: **1,504 units are marked repealed** from a date the annotation gives
(1,491 from annotations, 13 from the versioned tier, `certainty` `high` for the date, `low` for the
annotation-only text that is kept); **641 units are annotation-only repealed articles whose repeal date is
unknown** (the annotation names several unrelated dates, or none) and stay in force. 1,174 federal norms
carry `revogada: true` in the source header with no date: no event, flag kept in the source metadata. In
`brlaw-core`: 515 and 353.

**Stub texts:** 29 norms of articulated types have a tax text with no readable article (the Código Civil, Decreto nº 3.000/1999, several MPs, INs and portarias); 4 of them have a complete federal copy, which replaces the stub; for the other 25 the source is flagged `articles_missing` and an "article not found" in them is reported separately and kept out of the restricted headline.

**Left out of the tax tier** (53 files, listed with reasons in the manifests): 44 documents with no norm
number and date that could be read (court decisions, treaties, forms such as DIRF/Dmed, *pareceres* and
*notas* of the PGFN with year-only titles), the Constitution (provided by the federal tier), and 9 duplicates
of a norm already kept (the copy with more units is kept). 39 norms take their date from the dataset's own
title because the text had none (`date_source` `dataset_title`, `certainty` `medium`); the dataset's titles
sometimes carry a wrong year, which the text's own date overrides when present.

## The versioned tier

Built from the Câmara portal as described in `docs/legal-citation-test.md`. Four base norms were tried
(Lei nº 9.250/1995, Lei nº 9.249/1995, Lei nº 7.713/1988 and the CLT, Decreto-Lei nº 5.452/1943); 168 pages
downloaded. **234 provisions qualified; 60 were selected** deterministically (round-robin over the 60 amending
acts, ordered by sha256) so that no act dominates: **47 replaced and 13 repealed, 54 of the CLT and 6 of
Lei nº 7.713/1988, from 60 different acts** (1944-2024). Excluded, with counts (`versioned_build_stats.json`):
annotation defers effects / converts a provisional measure / vetoed: 74; amended by more than one act or the
act not named: 124; no such article in the original publication: 75; entry into force of the amending act not
settled by its own clause: 69; amending act not in the Câmara log: 2.
The two 1995 tax laws yield **none**: every provision of theirs is touched by several acts or by deferred
effects. The CLT's 2017 reform (Lei nº 13.467) is not in it: its clause says "após decorridos cento e vinte
dias", which the build does not compute. Every event stores the page URLs and the literal annotation; all 120
events have `certainty` `high`. Consistency check (`scripts` + the store): for all 120 `temporal` questions
the gold version `#v<seq>` is exactly the version the store returns at the question's date, and after a repeal
the store returns nothing.

Honest limits: the later wording is the portal's compiled text (the amending act's own text was downloaded
for its date and entry-into-force clause but not diffed against it); several selected changes are small
(spelling, punctuation, a number written out); and the sample is narrow (one old labour code, one tax law).

## Resolver accuracy on the gold references (the resolver's ceiling)

`scripts/brlaw/check_resolver.py`: 2,012 gold article references; **1,829** name a unit that exists in the
corpus; rendered as a lawyer writes them ("art. 8º da Lei nº 9.250/1995", "art. 677 do RIR/2018") the resolver
returns the gold unit for **1,815 (99.2 %)**. The misses (14) are errors in the dataset's own reference titles
(wrong year, for example "Lei nº 9.250/2005"), which the resolver rightly calls "norm not found". 183 gold
references name a unit the corpus does not hold. The rendering used the dataset's own titles (type, number,
year; the acronym when the title has one); the free-text forms in `tests/test_legal_resolver.py` cover the
brief's examples, including "Constituição, art. 153, III" and "Decreto nº 9.580/2018 (RIR/2018), art. 677".

## Coverage of the corpus against the Senate's lists (what "norm not found" can mean)

`scripts/brlaw/check_coverage.py`, `coverage_vs_senate.json` (public Senate API, sampled years): leis
ordinárias, 10 years between 1960 and 2024: **95.2 % to 99.4 %** of the Senate's list is in the corpus (the
missing ones are, for example, laws whose text has no article in the source); leis complementares, 9 years:
100 % in 6 years, 80 % / 67 % / 80 % in the others (5, 3 and 5 norms); decretos-lei, 4 sampled years that the
API answers for: 96 % to 100 %. **No type is covered completely**, so "norm not found" cannot be split cleanly
into "fabricated" and "real but outside": the metric reports the headline both ways and the restricted number
is "probably does not exist". For decretos, instruções normativas, portarias and all state and municipal law
the corpus makes no coverage claim.

## Retrieval recall of the gold provisions on `dev` (k = 8, free)

The `dev` split has 100 questions; 77 of them have gold provisions that exist in the corpus. Query = the
question text, as-of 2024-12-31 (`scripts/brlaw/check_recall.py`). Gold units are article units; a hit is a gold
unit among the 8 passages.

| Corpus | Method | Questions with a gold unit among the 8 | Mean recall |
|---|---|---|---|
| `brlaw-core` | BM25 | 58.4 % | 0.400 |
| `brlaw` (full) | BM25 | 50.6 % | 0.365 |
| `brlaw-core` | hybrid (BM25 + `multilingual-e5-small`, RRF, no reranker) | 50.6 % | 0.337 |

Hybrid retrieval is **lower** than BM25 here (small multilingual embedder; article texts are long and similar to one another). Reported as measured; nothing was tuned on it.

## Embedding and store size

Default local embedder `intfloat/multilingual-e5-small` (ONNX, CPU, 4 cores), 384-d. Embedding the **whole** corpus
would take about 4.4 hours (15 texts/s on a sample; 11-12/s sustained), above the 90-minute bar, so the embedded subset is
`brlaw-core`: the tax tier, the versioned tier, the Constitution and the federal norms dated 1995 or later. **Time:** about 75 minutes
of embedding in total (two passes, the first cut short by a corpus fix and its vectors carried over), plus 69 s for the 2,075 units
added by the stub fix; ingest takes 8 s (core) and 24 s (full). **Store size:** `brlaw-core.db` 397 MB with vectors (64,707 units);
`brlaw.db` 704 MB without vectors (220,647 units). Existence and in-force checks use the full store; retrieval uses the core.

## Dry run, end to end, with the fakes

`python -m heuresis.bench.run --dataset brlaw-core --split dev ... --time-aware-variants --variants-of agentic
--limit 8 --dry-run` and `--split temporal --limit 6`: five systems (`closed_book`, `hybrid`, `agentic`,
`agentic+asof`, `engine`), 40 and 18 rows, 0 errors, $0; `bench.citations` then produced the per-system table
over the rows. The rows are the fakes' extractive output (not results). The offline test
`tests/test_legal_systems.py` runs the same path on a synthetic corpus and pins the old prompts hash
(`c025db9e...a7b`) and surface hash (`547d7f32...78b3`), which are unchanged from `main`.

## Test suite

`python3 -m pytest -q`: **612 passed, 19 skipped** (main: 561 passed, 19 skipped; the 51 new tests are in
`test_brlaw.py`, `test_brlaw_versioned.py`, `test_legal_resolver.py`, `test_engine_references.py`,
`test_citations.py`, `test_legal_systems.py`). The environment needed `pytest`, `hypothesis` and `pyarrow` installed
to reproduce the baseline of 561 / 19.

## Phase B: cost estimate (not run; waiting for the go)

From measured prompt sizes on `brlaw-core` with BM25-shaped retrieval (`scripts/brlaw/check_recall.py`
retrieval, k = 8 and k = 5 as the systems use): dev prompts hold on average **13,842 characters of passages**
at k = 8 (max 24,069, the context cap of 24,000) and 9,146 at k = 5; `temporal` prompts 2,942 and 1,912.
Tokens are estimated as characters / 3.2 (Portuguese). Price table `anthropic-2026-11`,
`claude-haiku-5-5`: $0.10 / M input, $0.50 / M output. Thinking left at the default with `max_tokens` 4,096
(the brief's setting): typical output assumed 1,200 tokens per call (thinking plus at most three sentences);
upper bound 4,096 on every call. Agentic assumed 2 searches (3 calls) typically and 4 searches (5 calls) at
the upper bound; the engine 1.3 calls typically and 5 at the upper bound.

| Split | closed_book | hybrid | agentic | agentic+asof | engine | Total, typical | Total, upper bound |
|---|---|---|---|---|---|---|---|
| `dev` (100 questions) | $0.06 | $0.11 | $0.27 | $0.27 | $0.15 | **$0.86** | $4.52 |
| `temporal` (120 questions) | $0.07 | $0.09 | $0.24 | $0.24 | $0.12 | **$0.76** | $4.47 |

Support judge (thinking disabled, 10-token output): about 600 items on dev and 720 on temporal (answered
answers x resolved, in-force references; provisions up to 3,000 characters): about **$0.08 + $0.03**.
**Typical total about $1.8; hard upper bound about $9.1 plus the judge.** The local models (embedder,
reranker, entailer) are free. A paid run needs the prepared store: copy `data/db/brlaw-core.db` to
`<out>/store.sqlite` so that nothing is re-embedded, and run `bench.citations` with `--db data/db/brlaw.db` (the
full corpus, for existence and in-force checks). The `test` split (615) is not part of this estimate.

## What could not be obtained, and what was left out

* The **Senate's per-provision alteration log** (`edivs`) came back with no provision-level items for the norms
  tried (Lei nº 9.250/1995); the Câmara's "Vide Norma(s)" log was used instead.
* **The earlier wording** of a provision exists as downloaded text only for the 60 versioned provisions. For the
  federal and tax tiers the earlier wording is not in the source; amended provisions of original-text norms
  are not known to be amended.
* **Repeal dates** for 641 annotation-only articles and the 1,174 flagged norms (see above).
* **The CLT's 2017 reform** (entry into force by a period), **Lei nº 9.250/1995 and Lei nº 9.249/1995 provisions** (deferred
  effects, several acts) and the 44 + 9 tax-tier documents listed in the manifests.
* **The 7,204 CARF rulings** were not downloaded (the test is about legislation).
* A **human check** of the versioned pairs or of the resolver beyond the gold references has not been done.

# Phase B: the paid check on `dev` and `temporal` (calibration data, NOT the registered result)

Run after the orchestrator's go. Model `claude-haiku-5-5`, thinking left at the default, `draft.max_tokens` 4096, ledger
`runs/brlaw/ledger.jsonl` (cap US$6.00, margin 0.25; copy in `phaseB/ledger.jsonl`). **Spent US$1.629, remaining US$4.371.** Smoke
(5 dev questions x 5 systems) US$0.055 gave a projection of about US$0.011 per question, so (a) `temporal` (120) and (b) BR-TaxQA-R `dev`
(100) ran in full, five systems each (`closed_book`, `hybrid`, `agentic`, `agentic+asof`, `engine`) on `brlaw-core`; (c) the support judge and the
dev answer judge followed. 1,100 rows, 0 errors, nothing skipped. The BR-TaxQA-R `test` split and the old datasets were not touched.
The citation metric reads the answer text a user would receive; **the engine's 0 % tainted is partly by construction**: the `references_traced`
gate removes sentences with an untraced reference before the answer exists (counts below). Existence/in-force checks use the full store.
Files: `results/brlaw/phaseB/{temporal,dev}/` (`analysis.json`, `citations_summary.json`, `citations.jsonl` without text, judge verdicts, `report.md`, manifest).
The human-check CSVs (100 rows each, provision text included) stay in `runs/brlaw/*/citation_support_sample.csv` (not committed: corpus text).

## Citation integrity (answered rows; Wilson 95 % intervals)

| Split | System | Answered / abstained | Tainted, strict | Tainted, covered only | Refs per answer | Norm not found | Article not found | Resolved, not in force | Resolved and in force (of checkable) | No reference | Judge: supported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| temporal | closed_book | 26 / 94 | 2/26 = 7.7 % [2.1, 24.1] | 7.7 % | 3.81 | 0/50 | 1/50 | 1/49 | 48/50 | 0/26 | 56 % (36) |
| temporal | hybrid | 43 / 77 | 1/43 = 2.3 % [0.4, 12.1] | 2.3 % | 3.14 | 0/109 | 1/109 | 0/108 | 108/109 | 0/43 | 84 % (68) |
| temporal | agentic | 48 / 72 | 2/48 = 4.2 % [1.2, 14.0] | 4.2 % | 3.35 | 0/110 | 1/110 | 1/109 | 108/110 | 0/48 | 84 % (89) |
| temporal | agentic+asof | 103 / 17 | 7/103 = 6.8 % [3.3, 13.4] | 5.8 % [2.7, 12.1] (6/103) | 3.04 | 1/246 | 2/246 | 4/243 | 239/246 | 0/103 | 87 % (199) |
| temporal | engine | 95 / 25 | 0/95 = 0 % [0, 3.9] | 0 % | 1.88 | 0/169 | 0/169 | 0/169 | 169/169 | 0/95 | 85 % (149) |
| dev | closed_book | 72 / 28 | 20/72 = 27.8 % [18.8, 39.1] | 16/72 = 22.2 % [14.2, 33.1] | 2.50 | 4/147 | 18/147 | 1/125 | 124/147 | 1/72 | 25 % (107) |
| dev | hybrid | 64 / 36 | 8/64 = 12.5 % [6.5, 22.8] | 5/64 = 7.8 % [3.4, 17.0] | 3.45 | 3/187 | 4/187 | 1/180 | 179/187 | 0/64 | 79 % (168) |
| dev | agentic | 73 / 27 | 11/73 = 15.1 % [8.6, 25.0] | 8/73 = 11.0 % [5.7, 20.2] | 3.08 | 4/186 | 8/186 | 0/174 | 174/186 | 0/73 | 86 % (170) |
| dev | agentic+asof | 76 / 24 | 8/76 = 10.5 % [5.4, 19.4] | 6/76 = 7.9 % [3.7, 16.2] | 3.33 | 3/211 | 8/211 | 0/200 | 200/211 | 0/76 | 84 % (196) |
| dev | engine | 87 / 13 | 0/87 = 0 % [0, 4.2] | 0 % | 4.16 | 0/334 | 0/334 | 0/334 | 334/334 | 0/87 | 60 % (329) |

(Judge sample sizes are the number of judged references; the human-check CSVs hold 100 stratified rows per split, 20 per system.
The judge is a model's opinion, unchecked by a human.) "Not found" shares are of checkable references (resolved + not found); norm-only
mentions are excluded.

**Reading.** On dev, the system with no retrieval (`closed_book`) names a provision that does not exist or is not in force in
28 % of its answers (22 % counting only the norm types the corpus almost completely covers) and its references are judged to support the
sentence 25 % of the time; the retrieval systems are at 10-15 %; the engine delivers none. On `temporal` every system is low because
the questions name the norm and article; the differences there are small and the intervals overlap. The dev
"norm not found" for baselines are mostly real norms outside the corpus (e.g. INs of the 1990s), which is why the restricted column is lower.
The engine's judged support (60 % on dev) is its weak spot: it cites correctly but its sentences are often more
general than the provision (the judge says NOT_SUPPORTED); a model-judge verdict, not checked by a human.

## Paired differences, engine minus system (mean per question, bootstrap 95 %)

Tainted-rate difference (a negative number favours the engine): dev: closed_book -0.20 [-0.28, -0.13]; hybrid -0.08 [-0.13, -0.03]; agentic -0.11 [-0.17, -0.05];
agentic+asof -0.08 [-0.14, -0.03]. temporal: closed_book -0.017 [-0.042, 0]; hybrid -0.008 [-0.025, 0]; agentic -0.017 [-0.042, 0];
agentic+asof -0.058 [-0.10, -0.017]. A tainted answer is counted only for answered rows (an abstention is not tainted), so the engine's
lower rate is partly its gate and partly abstention behaviour; see the abstention counts.

**Penalised score (+1 / 0 / -1), deterministic containment grader, dev:** meaningless here. The official answers are paragraphs, so every
answered row is graded "wrong" and the score only rewards abstaining (the paired score differences in `analysis.json` follow abstention counts and
are not reported as results). The judge-assisted grade below is the usable correctness number, and it is secondary and exploratory.

## BR-TaxQA-R dev: correctness against the official answers (judge-assisted, `bench.judge`, exploratory)

| System | Answered | Abstained | Judged EQUIVALENT to a gold answer | Cost per question | Cost per equivalent answer | Calls | Searches | Median latency |
|---|---|---|---|---|---|---|---|---|
| closed_book | 72 | 28 | 24 (24 % of 100) | $0.00066 | $0.0027 | 1.00 | 0 | 6.6 s |
| hybrid | 64 | 36 | 32 | $0.00099 | $0.0031 | 1.00 | 1 | 5.3 s |
| agentic | 73 | 27 | 35 | $0.00179 | $0.0051 | 2.92 | 1.92 | 7.6 s |
| agentic+asof | 76 | 24 | 41 | $0.00201 | $0.0049 | 3.02 | 2.02 | 7.6 s |
| engine | 87 | 13 | 32 | $0.00245 | $0.0077 | 2.16 | 2.16 | 9.5 s |

The engine abstains least and answers more but with the same number of equivalent answers as `hybrid`; the model judge is lenient or strict by its
own rule and no human checked it.

## Dated questions (`temporal`, code-scored: which version did the answer give?)

| System | Abstained | Gave the version in force at the date | Gave the superseded / other version | Undetermined | Unit not cited | Cited a repealed provision as in force | No second version to compare |
|---|---|---|---|---|---|---|---|
| closed_book | 94 | 10 | 8 | 6 | 0 | 1 | 1 |
| hybrid (today's text) | 77 | 37 | 2 | 4 | 0 | 0 | 0 |
| agentic | 72 | 35 | 7 | 4 | 1 | 1 | 0 |
| agentic+asof | 17 | 66 | 12 | 14 | 0 | 4 | 7 |
| engine | 25 | 51 | 4 | 19 | 5 (+5 answered without the unit) | 0 | 11 |

Share of all 120 questions answered with the version in force: engine 43 %, agentic+asof 55 %, hybrid 31 %, agentic 29 %, closed_book 8 %; of answers
whose version could be told apart: engine 51/55 = 93 %, agentic+asof 66/78 = 85 %, hybrid 37/39 = 95 %, agentic 35/42 = 83 %, closed_book 10/18 = 56 %.
Citing the superseded wording happened 2-12 times per system, most often for `agentic+asof` (12) and `closed_book` (8). "No second version" are
repealed provisions asked about before the repeal (the store holds one version). Note that `hybrid` and `agentic` search as of today, yet mostly
return the wording in force at the date: many provisions had a single later change and the question names the article. This is calibration, 60 provisions from two base norms.

## The engine's `references_traced` gate (offline replay of the stored drafts)

dev: 88 engine rows replayed, 312 drafted sentences, **48 failed the gate** (16 of them failed only the gate; the rest also failed another check);
temporal: 111 rows, 314 sentences, **42 failed** (23 only the gate). Examples (from `analysis.json`):
1. `taxqa-053`: "...observada a IN SRF nº 21/1997, alterada pela IN SRF nº 73/1997": **norm not found in the corpus** (a norm the passage did not contain; real or not, the answer could not have verified it); dropped.
2. `taxqa-013`: "Essa solução cita a Lei nº 9.250/1995, arts. 8º e 10": the articles are **named but not among the cited passages**; dropped.
3. temporal `art314-before`: "...art. 7º do regulamento aprovado pelo Decreto nº 3.590, de 11 de janeiro de 1939": **norm not found**; dropped.
(also `art. 318 da CLT` named in a sentence that cites a different unit; `taxqa-066`: arts. of IN SRF 283/2003 and IN RFB 2.178/2024 named but not cited.)
Some drops are conservative: a sentence about what a norm says, naming another norm in passing, is dropped.

## Three engine wrong answers (dev, judge NOT_EQUIVALENT)

`taxqa-033` (requirements of the IRPF 2024 program): the engine answers about filing deadline and means, not the Java/platform requirements. `taxqa-045`
(where to file a rectifying return): it gives the rule for a refund claim and a floppy-disk delivery from an old IN, not the 2024 rule (stale source in the
corpus, not a citation error). `taxqa-053`: it answers with the 1999 Ato Declaratório and the 1999 return field, an obsolete procedure. These show retrieval
choosing older acts on an as-of date of 2024-12-31 because the tax tier holds one version of each text.

## Caveats

* Calibration data on `dev` and `temporal`, n = 100 and 120, one model, one run; nothing here is the registered result.
* The tainted metric counts a system's final text; the engine's number includes its gate. The gate and `abstention` rates differ across systems.
* All "in force" numbers except the 60 versioned provisions rest on single-version sources; the 1,000-odd human-check rows have not been read by a human.
* The deterministic containment grader and the penalised score are not meaningful on BR-TaxQA-R (long official answers); the judge-assisted grade is exploratory.
