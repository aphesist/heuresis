# Benchmark datasets

Date checked: 2026-11-11. Everything below was read on that day from the
Hugging Face dataset card or the official repository. Data is downloaded into
`data/raw/<name>` and built into `data/corpora/<name>` (both git-ignored). Nothing
is redistributed by this repository; results are published, data is not.

Use of the loaders: `from heuresis.bench.datasets import load, available`;
`load("musique" | "multihoprag" | "hoh", root="data")` downloads the pinned
revision on first use, builds the corpus in the `jsonl` exchange format and
returns a `Dataset`. Building is idempotent (a corpus whose file hashes match its
`MANIFEST.json` is not rebuilt).

## Splits and manifests

- Question ids are ordered by `sha256("<seed>:<id>")` (default seed 20261111) and
  cut into dev, then test, then sealed (defaults 100 / 500 / 300), per stratum, so
  the unanswerable fraction (MultiHop-RAG) or the current/outdated mix (HoH) is
  preserved in every split. If the pool is smaller than the request, dev is filled
  first, then test, then sealed.
- **`dev2`** (added with the engine redesign): a fourth split of up to 100 questions per dataset, cut
  *after* the three above from the questions that are in none of them, in the same hash order and with
  the same per-stratum allocation, so it cannot change which ids dev, test and sealed hold (their
  id-list hashes are identical, checked by a test against the hashes in PREREGISTRATION.md section 2).
  It exists so that a design change made on dev evidence can be checked on questions that evidence never
  touched. Its size is whatever is left when the pool is smaller than the request (`musique`: 100 of the
  1,000 are in none of the three, so `dev2` is exactly those 100). It is a tuning split, not a test
  split: `bench.calibrate` and `bench.judge` accept `dev` and `dev2`, and nothing else.
- `MANIFEST.json` next to each corpus records: source repo and pinned commit hash,
  sha256 of each raw file, sha256 of `sources/units/events/edges/questions.jsonl`,
  counts, `corpus_tokens` (characters of all version texts / 4), the split
  parameters and, per split, the sha256 of the newline-joined ordered question-id
  list. `load` refuses to continue if the default-parameter split hashes differ from
  the manifest. The `dev2` record (`requested`, `size`, `pool_unused`, `unanswerable`,
  `question_ids_sha256`) is the separate key `dev2`; the `splits` record, and with it the three
  original hashes, is unchanged.
- Unit ids are `<dataset>:<doc id>#<n>`. Passages of long articles are cut at
  paragraph boundaries into about 150 to 250 words; the article title is kept in
  `Unit.title` of every passage.
- Prior contact with the test split (see PREREGISTRATION.md, prior contact): retrieval-only checks read part of it. BM25 at k = 50 on the first 20 answerable test questions of each of `musique`, `multihoprag` and `hoh` found the gold units for 20 of 20 each, and the `hoh` "Sanity" row below was computed on 100 test questions. No model was called and no system answered. The sealed split has not been read by any script that computes or prints anything.

## Confirmatory sets

### 1. MuSiQue (built: `musique`)

| Item | Value |
|---|---|
| Source used | https://huggingface.co/datasets/osunlp/HippoRAG_2 files `musique.json`, `musique_corpus.json`, commit `5ec05b38deecc3318bb432c69865959c56058990` |
| Licence as written | The Hugging Face card of `osunlp/HippoRAG_2` carries only `language: en`; it states **no licence**. The upstream MuSiQue release (https://github.com/StonyBrookNLP/musique, README) says: "MuSiQue is distributed under a CC BY 4.0 License." |
| Corpus | 11,656 unique (title, paragraph) passages, ~5.6 M characters, ~1.41 M tokens (chars/4). One unit per paragraph, no splitting needed (paragraphs are short). |
| Questions | 1,000, all answerable, the retrieval subset used by HippoRAG / IRCoT. Families `2hop`, `3hop1`, `3hop2`, `4hop1`, `4hop2`, `4hop3`. |
| Gold | `is_supporting` paragraphs (2,648 over 1,000 questions) mapped to units. |
| Checks done | All 1,000 ids, questions and answers are identical to the official `musique_ans_v1.0_dev` (checked against the mirror `bdsaglam/musique`, 2,417 dev questions); every paragraph of every question is present in the corpus file. |
| Restrictions | MuSiQue's README cautions that its dev/test single-hop questions come from SQuAD, NQ, T-REx, MLQA and Zero Shot RE; do not train on those seed sets' overlapping questions. We only evaluate. The corpus has no dates: each passage gets a placeholder `create` event on 1970-01-01 and questions have `as_of=None`. |
| Caveat | **The licence on the file actually downloaded is missing; only the upstream licence is stated.** I judged the subset to be a verbatim derivative of the CC BY 4.0 data (ids and texts match), and built it. If that is not acceptable, the next-best alternative is the original answerable dev set from the official repository (Google Drive link in the MuSiQue README, same licence), with a corpus built from its paragraphs. This was not built (it needs a Drive download, and it has 2,417 questions with a per-question 20-paragraph pool rather than a shared corpus). |
| Manifest | `data/corpora/musique/MANIFEST.json` |

### 2. MultiHop-RAG (built: `multihoprag`)

| Item | Value |
|---|---|
| Source | https://huggingface.co/datasets/yixuantt/MultiHopRAG, commit `71ac0d0bd1f951d2d6b70311f7d2ae404e1ffa82` (files `MultiHopRAG.json`, `corpus.json`) |
| Licence as written | `license: odc-by` (card metadata). The card text itself adds no further terms. |
| Corpus | 609 news articles (2023-09-26 to 2023-12-25) from 49 outlets, split into 5,048 passages (about 200 words), ~6.3 M characters, ~1.57 M tokens. One `Source` per outlet. |
| Questions | 2,556 (comparison 856, inference 816, temporal 583, null 301). The 301 `null_query` items become `answerable=False` with empty answers; the original label is "Insufficient information.". |
| Dates | Article `published_at` is the `create` event date (day precision, so that an article is visible on its publication day; the full timestamp is kept in `axes["published"]`). Questions carry no date, so `as_of=None`. |
| Gold | Each evidence item gives a `fact`; the passage that contains it (normalised substring) is the gold unit: 5,974 exact matches and 110 by token-overlap fallback. `cluster` is the first evidence article. |
| Restrictions | ODC-By licenses the database and requires attribution; copyright in the article texts stays with the outlets and the card says nothing about it. Research benchmarking without redistribution is the intended use; I could not verify more. |
| Splits (default) | unanswerable 12 / 59 / 35 in dev / test / sealed (pool 301 of 2,556 = 11.8 %). |
| Manifest | `data/corpora/multihoprag/MANIFEST.json` |

### 3. Temporal / versioned QA (built: `hoh`; the two named candidates are not obtainable)

Requirement: a corpus with several dated versions of the same unit and questions
whose answer depends on the date.

| Candidate | Finding on 2026-11-11 | Verdict |
|---|---|---|
| LawInForce-eCFR (AACL 2026, https://aclanthology.org/2026.aacl-long.42/) | Paper exists (805 eCFR amendment pairs, 3,220 yes/no answer-flipping questions). The Anthology page gives no code or data link. Searches of Hugging Face (`lawinforce`, `law-in-force`, `authorityfirst`, `ecfr`) and GitHub find no release. Licence: none stated for data (the Anthology footer's CC BY 4.0 covers the paper only). | Not obtainable. Not built. |
| FiscalQA Pro (ICML 2026 virtual poster 80578) | Abstract: 32,436 article-versions of the French CGI and LPF (1938 to 2031), 35 expert questions, "all corpus, benchmark, and pipeline artifacts" released, but the page links only to an OpenReview forum (`zokLD8KM1A`); no Hugging Face or GitHub location found, no licence read. Only 35 questions anyway, too few for a powered test. | Not obtainable, too small. Not built. |
| TimeQA (`hugosousa/TimeQA`, bsd-3-clause-clear) | Time-scoped questions over Wikipedia pages, but the corpus is one page text, not dated versions of a unit. | Fails "multiple dated versions". Not built. |
| HoH (ACL 2025, `russwest404/HoH-QAs`) | See below. | **Chosen.** |

**HoH-QAs** (`hoh`)

| Item | Value |
|---|---|
| Source | https://huggingface.co/datasets/russwest404/HoH-QAs, commit `8f12fd356240fa9386d20346fe1e1f9b928d1b64`, file `hoh_qas_240601_241201.parquet` (29 MB, 111,972 records; needs `pyarrow`) |
| Licence as written | Card: `license: apache-2.0` for "the portions of HoH-QAs that the HoH authors have the right to license"; "Evidence passages reproduced or adapted from Wikipedia remain subject to the applicable source license, typically CC BY-SA 4.0" with attribution and ShareAlike for public adaptations. The code repository (0russwest0/HoH) lists Apache-2.0. |
| Restrictions | Attribution to Wikipedia contributors; ShareAlike applies if the passages are publicly shared. We do not redistribute them. Evidence is a short snippet (about 21 words), not a full page. |
| Corpus | One unit per record, `hoh:<wiki page id>#<n>` (n counts records of the same page), title = page title. Versions come from the record's evidence at each monthly snapshot (2024-06-01 to 2024-12-01): the earliest observed is a `create` event, each later one a `replace` event dated by its snapshot (`axes["observed"]`). 111,972 units, 230,746 versions, ~29.2 M characters, ~7.30 M tokens. 95 % of units have two versions, the rest up to six. |
| Questions | One per record whose chosen version's answer differs from every other version's answer: 110,721 in the pool (1,251 records dropped because the answers were equal). The version is chosen by a fixed hash (`sha256("hoh-asof\n"+unit id)`) among the record's versions; `as_of` = that snapshot date; `answers` = that version's answer; `gold_units` = the unit; `kind` = `current` (latest snapshot) or `outdated`; stratified by `kind`; `cluster` = Wikipedia page. All answerable. |
| Date semantics | A snapshot date is when the text was first observed. The real change happened up to one month earlier, so `valid_from` is late by up to a month, and the first version is only known from its first snapshot (no question is asked before 2024-06-01). Using the snapshot date itself as `as_of` keeps every question inside a validity interval. The "current" answer is current for the data's horizon (2024-12-01), not today. |
| Sanity | On the test split (see PREREGISTRATION.md, prior contact): with the date filter, the retrieved gold unit holds the question's gold answer in 86 of 100 test questions; with no date (today) only 41, so the date does matter. Retrieval only; no model was called. |
| Manifest | `data/corpora/hoh/MANIFEST.json` |

Recommendation: use HoH as the temporal set, with the stated weaknesses: single
short snippets, monthly granularity, facts changed over six months only, and
question texts that were LLM-generated from diffs. It is not legal and has no
repeal or retroactive correction, so it exercises `create`/`replace` and the as-of
filter but not `repeal`, `restore`, `correct` or the transaction-time axis.

### If no real temporal set were enough: deriving one from a revision history (not built)

A versioned test can be derived from any public revision history, for example the
eCFR (versioner API and bulk XML, with dated versions per section and an amendment
file giving effective dates), a Git repository's tags, or Wikipedia
revisions. Procedure: (1) take each unit (a section, a file, an article) and its
dated versions; keep only the units whose text changed in a numeric or enumerable
way (a threshold, a date, a rate); (2) generate a question whose answer is a
function of that value, with a gold answer for each version, using a deterministic
template or a pre-registered extraction rule (no paid API); (3) ask each question
at a date inside each version's validity interval (and one date before the first
version, where the expected answer is "not in force"); (4) score the same question
across dates so that an answer valid only in another version counts as wrong
(answer-flip pairs). The licence of the source decides whether it can be built:
US federal works (eCFR) are public domain; Wikipedia text is CC BY-SA 4.0.

## Exploratory sets (availability and licence only; no loader)

| Set | Source and revision | Licence as written | Size / content | Restriction / note |
|---|---|---|---|---|
| BIRD Mini-Dev | https://huggingface.co/datasets/birdsql/bird_mini_dev, commit `5b256b5a9c17478f06ed6912612e9a14d17065c8` (card updated 2026-10-27) | `license: cc-by-sa-4.0` | 500 aligned text-to-SQL questions in SQLite, MySQL and PostgreSQL variants, with evidence and gold SQL. The databases are not in the Hugging Face repo: they are Docker images on Docker Hub (`3036197201/bird-mini-dev-*`) and a Harbor Hub dataset. | ShareAlike on adaptations. Database image licence not stated on the card: unverified. Evaluation needs execution accuracy against the databases, so it also needs the `sql` tool path. Available; not loaded. |
| BR-TaxQA-R | https://huggingface.co/datasets/unicamp-dl/BR-TaxQA-R, commit `9f0f4263928c6152a40f888da3e63375a24bb0f3` | `license: cc-by-4.0` (also a LICENSE file with the CC BY 4.0 text) | 715 questions on Brazilian personal income tax (2024 Receita Federal Q&A), 478 referenced legal documents as text, 7,204 CARF 2023 rulings (files `questions_QA_2024_v1.1.json`, `referred_legal_documents_QA_2024_v1.1.json`, `acordaos_CARF_2023.json`). Portuguese. | The card states the legal documents are the version in force for the 2024 declaration (one version per document, so not a versioned test). Licence applies to the compilation; the underlying official texts are Brazilian public documents. Available; not loaded. |

## Not verified

- Whether the HippoRAG 2 redistribution of MuSiQue is licence-clean (card empty).
- Copyright of the MultiHop-RAG news article texts.
- Licence of the BIRD database Docker images.
- Existence of a LawInForce-eCFR or FiscalQA Pro release after the date checked, or
  under a name I did not search for; the OpenReview page could not be read.
- HoH data quality (LLM-generated questions and diffs) beyond the checks listed.
