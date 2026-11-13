# Temporal / versioned retrieval and temporal reasoning for LLM QA over evolving corpora (state as of Nov 2026)

Scope note: ~15 tool calls; many snippets came via search summaries or abstract pages, flagged "(abstract/secondary)". Items I could not verify are in Gaps. Measured = reported by the paper's authors in their experiments; none independently replicated here.

## 1. Benchmarks and findings on outdated/evolving knowledge in RAG; what fails

### Takeaway
Across general-domain (HoH) and legal (2026) benchmarks, wrong-version evidence is both retrieved often and actively harmful: one outdated passage costs ~16-24 points for a strong LLM, and version-blind retrieval returns the in-force version 0-3% of the time on heavily amended legal corpora. As-of filtering/date-conditioned retrieval recovers most of the gap, but generation errors (numeric rule application, recency bias) remain. This supports the target system's measured 42-49% -> 92-100% effect.

### Cited Findings
- HoH (ACL 2025, Ouyang et al.): 96,124 QA pairs, 219,463 documents; main eval 10,000 QA; only 5,129 of 96,124 questions (~5.3%) had updated answers; HoH-SearchEngine keeps both current and historical docs. Authors: presence of outdated text lowers performance by at least 20% across mainstream LLMs, some models fall below random. — [HoH arXiv v3](https://arxiv.org/html/2503.04800v3), [search summary](https://arxiv.org/pdf/2503.04800)
- HoH Llama-70B: 89.12 with only relevant passages vs 72.95 with one relevant + one outdated passage (-16 pts; text says >24% relative fall). — [HoH v3](https://arxiv.org/html/2503.04800v3)
- HoH passage ordering matters for Llama-70B (no distractors): newest-first 83.88, relevance-ordered 72.95, oldest-first 61.04. — [HoH v3](https://arxiv.org/html/2503.04800v3)
- HoH retrieval: search engine without temporal decay has outdated hit@5 0.8837 vs relevant 0.8707 (outdated docs retrieved as often as current); Gaussian time decay drops outdated hit@5 to 0.495 but also relevant to 0.702; bge-m3 hit@5 0.731 relevant vs 0.551 outdated. Temporal blindness is symmetric; decay also hurts recall. — [HoH v3](https://arxiv.org/html/2503.04800v3)
- HoH: models told to identify outdated info still produced more harmful outputs in some cases (Llama-70B +11% harmful outputs with outdated-awareness info) (via search summary; verify). — [HoH pdf](https://arxiv.org/pdf/2503.04800)
- HoH uses "Current Date"/"Last Modified Time" in prompts but reports no no-timestamp ablation. — [HoH v3](https://arxiv.org/html/2503.04800v3)
- FiscalQA Pro / "Temporal Misgrounding in Legal RAG" (ICML 2026 workshop-level, arXiv 2608.09393): 32,436 article-versions of French tax code over 93 years (1938-2031); 209 scored questions on 33 articles; 11 models. Static current-version RAG retrieved the date-applicable version 0% of the time; mean strict accuracy 3.0% parametric, 2.7% static RAG, 98.3% with multi-version index retriever, 99.1% oracle-article. Remaining gap attributed to first-stage recall, not version selection. 69,208 version-aware jurisprudence citation links. Nugget (regex/numeric) scoring avoids LLM-judge bias. — [arXiv abstract](https://arxiv.org/abs/2608.09393), [ICML page](https://icml.cc/virtual/2026/80578)
- "Asking for an Old Friend" (TUM, German statutes, arXiv 2605.23497): 312 expert-validated QA, 3 categories (post-cutoff amendment n=115, pre-amendment n=113, multi-provision pre-amendment n=84), 5 LLMs, 4 settings. Outcome-correctness % (Table 1): ChatGPT-5.1 post-cutoff vanilla 40.0 -> RAG 83.5; Claude Sonnet 3.7 24.4 vanilla -> 63.5 web -> 83.5/87.0 RAG; Claude Opus 4.5 pre-amendment 35.4 -> 63.7 web -> 81.4 RAG; DeepSeek v3.2 pre-amendment 37.2 -> 44.3-50.4 RAG; multi-provision best RAG 78.6 (Opus 4.5), 61.9 (GPT-5.2). Web search showed recency bias: recent-question score +0.20-0.24 (p<0.05) vs +0.04-0.06 (n.s.) otherwise. RAG = fact-date extraction + version filtering. Ablation removing temporal filter "caused a substantial drop" but no number given. — [HTML v2](https://arxiv.org/html/2605.23497v2), [abstract](https://arxiv.org/abs/2605.23497)
- LawInForce-eCFR (Tsinghua, AACL 2026): 805 human-validated eCFR/CFR amendment pairs, 3,220 answer-flipping yes/no questions (94% acceptance after rule-based filtering; annotator agreement 95.28%). Recall@1: BM25+date filter 2.80%, citation-hybrid date filter 9.16% (R@10 77.17%), AuthorityFirst-RAG (authority -> temporal scope -> rule support) 30.90%. Generation with GoldOracle evidence only 53.8% avg (best open model Qwen2.5-32B 63.3% on N=300); 83-91% of residual errors are rule-application (numeric thresholds) not retrieval. Lesson: date filtering alone is not sufficient when old/new versions share citation and vocabulary; date filter does not rank. — [AACL paper PDF](https://aclanthology.org/2026.aacl-long.42.pdf) (read via pdftotext)
- NitiBench+ (Thai law, arXiv 2611.03576): 156,650 court decisions checked, "up to 67%" cite law since amended/repealed; 1,670 QA items/17 domains; corpus holds every dated version of each section. Across 13 open models: reading current text of amended law lowers Bar-standard score by 0.25; missing repealed law lowers it by 0.79; penalty 0.45 on 428 rule-changed items and ~0 on 331 wording-only items; Citation F1 does not detect the penalty. 26-model leaderboard: best 7.78/10, best open 6.39; with search tool 20/26 models gain, 6 lose. — [arXiv 2611.03576](https://arxiv.org/abs/2611.03576)
- evolveQA (arXiv 2510.19172): 922 QA from AWS/Azure/WHO time-stamped corpora; 6-31% accuracy drop on evolving vs static facts; in 32-45% of cases model answers open-ended question with outdated fact but picks right MCQ option; outdated-response rate 23-55% (sources disagree 54 vs 55, secondary summaries). — [evolveQA](https://arxiv.org/html/2510.19172v1)
- Other benchmarks surfaced only by name: "Question Answering under Temporal Conflict" (Temporal Wiki, Unified Clark; models misled when multiple versions in context), 2604.05096 (continuous knowledge drift; RAG often fails to aggregate/order temporal evidence), 2603.12271 (retrieval bias under multiple in-context knowledge updates), ChroKnowBench (24 LLMs). — [2506.07270 summary](https://www.emergentmind.com/papers/2506.07270), [2604.05096](https://www.alphaxiv.org/abs/2604.05096v2), [2603.12271](https://arxiv.org/html/2603.12271v1)
- Re3 / Re2 Bench (ACL 2026): >1.3M instances; time-aware relevance encoder + Conflict-Aware Recency Filter (listwise arbitration) to suppress obsolete versions when multiple dated versions coexist. — [ACL 2026 Re3](https://preview.aclanthology.org/ingest-acl/2026.acl-long.1180/)

### Inferences
- The target's un-filtered 42-49% figure is consistent with HoH (outdated hit@5 ~ relevant hit@5) and far better than the 0-3% seen on legal corpora with many versions per article; baseline depends on versions-per-unit (more versions -> lower chance of in-force version).
- Date filter fixes "which version" but not (a) ranking within version set (LawInForce R@1 30.9% even best-case), (b) numeric rule application. Budget evals for both retrieval and generation errors.
- Evaluate with deterministic/nugget scoring where possible since LLM judges can inherit recency bias.

### Gaps
- Did not retrieve exact numbers for FreshQA, TimeQA, TempReason, SituatedQA, StreamingQA, TimeR4, TimeBench, UnSeenTimeQA, ChronoQA (only name/description found; ChronoQA described as 5,176-question Chinese benchmark, not verified for retrieval), EvolveBench, DynamicQA (search found no hits for these two names). Mostly pre-2025 and not legal-specific.
- Wikipedia-revision benchmarks: no specific source retrieved.

## 2. Methods: time-aware retrievers, filtering vs learned scoring, query scope extraction, temporal KGs, version-aware stores

### Takeaway
Learned temporal scoring yields single-digit gains; hard metadata/validity filtering plus a symbolic temporal constraint yields much larger ones when versions share text. Temporal KGs (Zep/Graphiti) mainly help memory-style QA; legal-norm graph RAG (SAT-Graph RAG) is architecturally relevant but unquantified.

### Cited Findings
- TempRetriever (WSDM 2026): DPR extended with query date and document timestamp embeddings + time-based negatives. ArchivalQA +6.63% Top-1, +3.79% NDCG@10 vs DPR; ChroniclingAmericaQA +9.56% Top-1, +4.68% NDCG@10; beats a DateAsToken baseline (text timestamp) by >4% nDCG@10 on ChroniclingAmericaQA. — [arXiv 2502.21024](https://arxiv.org/pdf/2502.21024)
- MRAG / TempRAGEval (arXiv 2412.15540): TempRAGEval repurposes TimeQA and SituatedQA with temporal perturbations and gold evidence; existing retrievers struggle; MRAG is training-free: splits question into main content + temporal constraint, retrieves/summarizes, then semantic-temporal hybrid ranking; "significantly outperforms" baselines (abstract-level, no numbers extracted). — [arXiv 2412.15540](https://arxiv.org/abs/2412.15540)
- Query time-scope extraction is how the legal systems get their as-of date: TUM RAG variants use fact-date extraction then version filtering (83.5-87.0% post-cutoff outcome correctness for strong models). — [arXiv 2605.23497](https://arxiv.org/html/2605.23497v2)
- Zep/Graphiti bitemporal KG: tracks valid time and ingestion time; contradicting facts invalidate old edges instead of deleting (LLM judges contradiction). Reported: up to +18.5% accuracy and ~90% latency reduction on LongMemEval vs full-context; DMR 94.8% vs MemGPT 93.4% (authors say DMR too easy); blog table 71.2 vs 60.2 (GPT-4o). Vendor-authored; secondary summaries only. — [Zep blog](https://blog.getzep.com/zep-a-temporal-knowledge-graph-architecture-for-agent-memory), [arXiv 2501.13956](https://arxiv.org/abs/2501.13956v1)
- SAT-Graph RAG (Brazilian Federal Senate author, arXiv 2505.00039): separates abstract legal work from dated versions; amendments/repeals/enactments as action nodes; point-in-time retrieval by graph traversal; case study Brazilian Constitution Art. 6; author states quantitative evaluation still needed. — [arXiv 2505.00039](https://arxiv.org/abs/2505.00039)
- Practitioner: prompt-only "prefer recent" plus timestamps insufficient; version-status flags, authority ranking, retrieval-side filtering recommended (blog-level evidence). — [DEV post](https://dev.to/faraz_farhan_83ed23a154a2/the-rag-system-that-found-contradicting-answers-and-confidently-picked-the-wrong-one-5elh)

### Inferences
- Hard validity filter (code) is the right primary mechanism; learned time embeddings are a secondary ranker for within-valid-set ordering. Authority/unit identification before temporal scoping (AuthorityFirst) is a useful decomposition.
- If question date is implicit, extract from the question's fact date (not the question-asking date); distinguish "as of now" vs event date.

### Gaps
- No numbers found for TsContriever, time-fusion, TimeR4, T-GRAG, TimeRAG, temporal GraphRAG; no controlled comparison of metadata filter vs learned scoring on the same data; "event-sourced consolidation" of amended text had no dedicated source.

## 3. Temporal reasoning in the LLM; delegating date math to code

### Takeaway
Models handle simple date arithmetic but fail multi-step/interval reasoning; code execution (PAL/PoT-style, Python datetime) is the well-supported remedy, though I found no 2026 frontier-model numbers.

### Cited Findings
- Test of Time (ICLR 2025, Google): synthetic ToT-Semantic and ToT-Arithmetic; LLMs good on straightforward arithmetic, struggle on multi-step/complex time calculations; fact ordering in prompt matters. — [ToT](https://arxiv.org/pdf/2406.09170)
- TReMu (arXiv 2502.01630) translates temporal questions to Python executed with datetime/dateutil; Li et al. 2023 (2305.15014) extract structure then execute code; PAL date-understanding example uses datetime/relativedelta. — [TReMu](https://arxiv.org/pdf/2502.01630), [Li et al.](https://ar5iv.labs.arxiv.org/html/2305.15014)
- LawInForce: even with gold in-force evidence, accuracy only 53.8% avg, 83-91% of errors are rule application (e.g., day-counting against thresholds); example problem is filing on day 75 vs 60/90-day limits. — [LawInForce](https://aclanthology.org/2026.aacl-long.42.pdf)
- TUM: recency bias (prefer newer text although historical version governs) is a documented failure; multi-provision pre-amendment questions are hardest. — [arXiv 2605.23497](https://arxiv.org/abs/2605.23497)

### Inferences
- Compute intervals ("in force on D", "days between", deadlines) in code against stored valid-from/valid-to; give the LLM only the resolved version and computed facts. "What changed between X and Y" = diff two as-of snapshots deterministically, then summarize.

### Gaps
- No exact accuracy figures for date arithmetic by modern models or PoT gains on TempReason/TimeBench; only qualitative statements.

## 4. Legal temporal validity

### Takeaway
Official portals already expose point-in-time versions (with caveats about editorial lag), and 2026 benchmarks across FR/DE/US/TH show version-blind legal RAG fails; law's three dates and non-retroactivity rules mean "as of" must be tied to the operative fact date.

### Cited Findings
- legislation.gov.uk: per-provision "Point in Time" view alongside Latest/Original; changes not yet applied by editors are excluded from historical views (only in latest/prospective); Akoma Ntoso XML via /data.akn suffix. — [example page](https://legislation.gov.uk/eur/2013/1303/part/THREE/title/I/2020-07-18)
- EUR-Lex consolidated texts: initial act plus amendments/corrections; each consolidated version shows rules applicable at a point in time; header date = date latest included amendment becomes applicable; "Show all versions" lists all; consolidated texts have no legal effect (only OJ is authentic). — [EUR-Lex consolidation notice](https://eur-lex.europa.eu/content/legis/avis_consolidation.html)
- Empirical legal results: see Section 1 (FiscalQA Pro 0% static; NitiBench+ 67% decisions cite later-amended law; LawInForce; TUM).
- NitiBench+ shows the wrong-version penalty concentrates in rule-changed provisions (0.45) vs wording-only (~0). — [arXiv 2611.03576](https://arxiv.org/abs/2611.03576)
- SAT-Graph RAG models Brazilian constitutional amendments (FRBRoo-style work/version split). — [arXiv 2505.00039](https://arxiv.org/abs/2505.00039)

### Inferences
- Model three dates explicitly (publication, entry into force, effect/applicability) and keep separate fields; as-of filter should key on in-force/effect date chosen by the question's operative fact date (tempus regit actum), with transitional/retroactivity provisions flagged as exceptions requiring human or rule review.
- Editorial lag in official consolidations (legislation.gov.uk) means a consolidated "as of" can be stale relative to enacted-but-unapplied amendments; record this as uncertainty (see section 5).

### Gaps
- Not retrieved: Akoma Ntoso/LegalDocML temporal elements spec, ELI, LexML Brasil URN specifics, Normattiva multivigente, US Code release points, Legifrance versions, LexTime benchmark, Chinese/EU/Brazilian RAG amendment systems beyond SAT-Graph RAG; vacatio legis/retroactivity literature. Treat these as open; legal-informatics sources (JURIX/ICAIL) not searched directly.

## 5. Bitemporal modelling, as-known-at queries, uncertain validity, out-of-coverage abstention

### Takeaway
Little retrieval-specific literature found; the practice comes from Graphiti's design (valid time + ingestion time, invalidate not delete) and the legal portals' point-in-time views.

### Cited Findings
- Graphiti marks superseded edges invalid rather than deleting, preserving history. — [Zep blog](https://blog.getzep.com/zep-a-temporal-knowledge-graph-architecture-for-agent-memory)
- legislation.gov.uk excludes unapplied changes from historical views, i.e., its point-in-time reflects what editors had applied (a recorded-time effect). — [example page](https://legislation.gov.uk/eur/2013/1303/part/THREE/title/I/2020-07-18)
- FiscalQA's corpus extends to 2031 (future-dated versions), showing prospective versions can be modelled. — [arXiv 2608.09393](https://arxiv.org/abs/2608.09393)

### Inferences
- "As known at" = filter on recorded time <= T_known AND valid interval containing D; storing both makes past answers reproducible. Unknown end dates: use open-ended interval with status flag; uncertain start: store earliest/latest bounds and abstain or answer with caveat if D falls in the band.
- Abstain when D < earliest valid_from of the unit, D > corpus coverage end/last recorded time, or when the unit has no version covering D (gap) rather than falling back to nearest version (nearest-version fallback = the recency bias failure).

### Gaps
- No primary source found on abstention-by-coverage in temporal RAG or on uncertain-interval handling; above are design inferences, not findings.

## 6. Knowledge conflicts between versions; do version dates in the prompt help?

### Takeaway
Models are easily distracted by older versions in context, and recency/ordering cues help partially; retrieval-side exclusion is more reliable than asking the model to arbitrate.

### Cited Findings
- HoH: one outdated passage -16 pts (Llama-70B); passage order newest-first recovers to 83.88 vs 61.04 oldest-first; prompt includes dates yet harm persists. — [HoH v3](https://arxiv.org/html/2503.04800v3)
- evolveQA: models know current facts in MCQ but emit outdated ones open-ended in 32-45% cases (parametric staleness). — [evolveQA](https://arxiv.org/html/2510.19172v1)
- TUM: models show recency bias (prefer newer provisions for historical facts); web search worsens it. — [arXiv 2605.23497](https://arxiv.org/html/2605.23497v2)
- Re3 uses listwise arbitration to filter obsolete versions precisely because generators/rankers mix them. — [Re3](https://preview.aclanthology.org/ingest-acl/2026.acl-long.1180/)
- Practitioners: timestamps + "prefer recent" prompt insufficient. — [DEV post](https://dev.to/faraz_farhan_83ed23a154a2/the-rag-system-that-found-contradicting-answers-and-confidently-picked-the-wrong-one-5elh)

### Inferences
- Pass only the version in force at D to the generator; if both versions are needed (what-changed questions) label each with explicit valid-from/to and order by date; include the as-of date in the prompt but do not rely on it.

### Gaps
- No controlled ablation of "version dates shown vs not" found (HoH has none); no measurement of behaviour with explicit labelled old+new pairs in legal contexts.
