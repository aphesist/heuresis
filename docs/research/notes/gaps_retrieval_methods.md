# Gaps in retrieval methods for structured/hierarchical and time-versioned corpora (state as of Nov 2026)

Scope: CPU-only engine (SQLite FTS5 BM25 + small ONNX embedder, ~29k Portuguese legal norms split into provisions, plus generic corpora); which upgrades are worth building without LLM-built indexes. Only gaps not covered by earlier notes. "Measured" = numbers read from the primary paper in this session; "claimed" = vendor or secondary-source statements. Where a PDF could not be parsed by the fetcher it was converted locally with pdftotext. Dates of older results are marked.

## 1. Graph retrieval: HippoRAG / HippoRAG 2 / GraphRAG-Bench / RAG-vs-GraphRAG / LightRAG, and deterministic-edge expansion

### Takeaway
LLM-built graph indexes (HippoRAG 2) give measured but modest recall gains over strong dense retrievers (about +5 points avg recall@5, concentrated on multi-hop sets) at roughly 8x the indexing time and millions of LLM tokens; graph methods lose or tie on simple fact retrieval. The only evidence for expansion over deterministic edges (explicit citations/hyperlinks) is on statute/Wikipedia data and is positive but small to moderate and mostly from small or single-group studies; PPR is shown to matter in the original HippoRAG ablation, but HippoRAG 2 never ablates PPR.

### Cited Findings
- HippoRAG 2 (2025), passage recall@5 (Llama-3.3-70B setup; corpora 4k-23k passages, 1,000 queries each): HippoRAG 2 vs NV-Embed-v2 vs BM25: NQ 78.0 / 75.4 / 56.1; PopQA 51.7 / 51.0 / 35.7; MuSiQue 74.7 / 69.7 / 43.5; 2Wiki 90.4 / 76.5 / 65.3; HotpotQA 96.3 / 94.5 / 74.8; avg 78.2 / 73.4 / 55.1. Gain over the best dense model is largest on 2Wiki (+13.9) and MuSiQue (+5.0), about +1.8 on HotpotQA and +2.6 on NQ. — [HippoRAG 2 paper](https://arxiv.org/html/2502.14802)
- HippoRAG 2 QA F1: avg 59.8 vs NV-Embed-v2 57.0, GTE-Qwen2-7B 54.9, BM25 47.7, RAPTOR 48.8, GraphRAG 49.6, original HippoRAG 53.1; MuSiQue 48.6 vs 45.7 (NV-Embed-v2), 2Wiki 71.0 vs 61.5, HotpotQA 75.5 vs 75.3, NQ 63.3 vs 61.9. LightRAG scored 6.6 avg (NQ 16.6, HotpotQA 2.4), which the authors obtained with their own run (likely a setup/format issue; treat as not representative of LightRAG). — [HippoRAG 2 paper](https://arxiv.org/html/2502.14802)
- HippoRAG 2 indexing cost on MuSiQue (Table 12): 9.2M input + 3.0M output LLM tokens, 99.5 min, vs NV-Embed-v2 12.1 min with no LLM tokens; GraphRAG 115.5M/36.1M tokens, 277 min; LightRAG 68.5M/18.3M tokens, 235 min; RAPTOR 1.7M/0.2M tokens, 100.5 min. Query time 1.2 s vs 0.3 s dense. — [HippoRAG 2 paper](https://arxiv.org/html/2502.14802)
- HippoRAG 2 ablation (recall@5): replacing its triple-based query linking with NER-to-node or query-to-node drops avg recall to 74.6 and 59.6 (vs 87.1 full over MuSiQue/2Wiki/HotpotQA); removing passage nodes drops MuSiQue 74.7->63.7 and HotpotQA 96.3->88.9; removing the LLM recognition-memory filter costs only 0.7 avg. The paper has NO experiment that disables PPR itself. — [HippoRAG 2 paper](https://arxiv.org/html/2502.14802)
- Original HippoRAG (v3 of the paper) ablation, R@2/R@5: full (ColBERTv2) MuSiQue 40.9/51.9, 2Wiki 70.7/89.1, HotpotQA 60.5/77.7; PPR replaced by query nodes only 37.1/41.0, 59.1/61.4, 55.9/66.2; query nodes + 1-hop neighbours without PPR 25.4/38.5, 53.4/74.7, 47.8/64.5 (worse than query nodes alone). On HotpotQA the plain ColBERTv2 retriever (64.7/79.3) beats HippoRAG. HippoRAG 1 uses OpenIE extraction; REBEL extraction cut MuSiQue R@5 to 39.6, Llama-3.1-8B extraction matched GPT-3.5 on MuSiQue (51.9) but fell on 2Wiki (77.5 vs 89.1). Claimed (abstract): 10-20x cheaper and 6-13x faster than IRCoT online. — [HippoRAG paper](https://arxiv.org/html/2405.14831)
- GraphRAG-Bench ("When to use graphs in RAG", 2025; novel corpus from Gutenberg and a medical NCCN-guideline corpus; GPT-4o-mini reader): fact retrieval accuracy RAG-with-rerank 60.92 vs HippoRAG2 60.14 vs MS-GraphRAG 49.29; complex reasoning 42.93 vs 53.38 vs 50.93; contextual summarisation 51.30 vs 64.10 vs 64.40. On the structured medical set, fact retrieval RAG-with-rerank 64.73 vs HippoRAG2 66.28. Per-query prompt tokens on novel set: RAG 879, HippoRAG2 ~1,008, MS-GraphRAG global ~331k, LightRAG ~101k. — [GraphRAG-Bench](https://arxiv.org/html/2506.05690)
- "RAG vs GraphRAG" systematic evaluation (Llama-3.1-8B): NQ F1 RAG 64.78 vs HippoRAG2 61.03; HotpotQA 60.04 vs 63.01; MultiHop-RAG overall acc 67.02 (RAG) vs 70.27 (HippoRAG2) vs 69.01 (community-local), with the temporal sub-type 30.70 (RAG) vs 49.91 (HippoRAG2) vs 45.28 (RAPTOR); KG triples-only GraphRAG is far worse (NQ 34.28). Construction on MultiHop-RAG: RAG 135 s vs KG-GraphRAG 7,702 s vs community-GraphRAG 5,560 s. A token-matched RAG on MultiHop-RAG (70B) got 71.01 vs GraphRAG 71.17, i.e. a large part of the "graph" gain is explained by the longer context. Union of RAG+GraphRAG contexts gave +6.4% over best single (70B). — [RAG vs GraphRAG](https://arxiv.org/html/2502.11371)
- Deterministic-edge evidence, Korean statutes (SearchFireSafety, ACL 2026): 131 statutes, 4,467 atomic units split on native Article/Paragraph/Item hierarchy with law title prepended, graph from hyperlinks parsed out of the official law portal. Top-15 dense results act as seeds and propagate score along explicit citation links with log-degree penalties (SAR). Recall@10/20/50: BM25 23.39/30.40/40.63; Qwen3-Embedding-0.6B 48.70/57.72/69.02, +SAR 53.26/62.32/73.49 (+4.6/+4.6/+4.5); BGE-M3 53.77/61.66/72.79, +SAR 54.70/62.86/74.57 (+0.9/+1.2/+1.8). Adding RRF with an auxiliary list slightly hurt (BGE-M3 R@10 53.77->49.77); Rocchio PRF was mixed (BGE-M3 R@10 -1.2). Fine-tuning BGE-M3 on 13,331 synthetic QA pairs gave R@10 57.25 and SAR added +1.1 on top. The gain from the graph is thus bigger for the weaker embedder and small for the stronger one. — [SearchFireSafety, ACL 2026](https://aclanthology.org/2026.acl-long.2112.pdf) (read via local PDF conversion)
- Deterministic-edge evidence, Indonesian UU ITE law (JAIC, Oct 2026): 63 article-level chunks, 40 queries, 49 directed cross-reference edges from 26 chunks; hybrid RRF baseline recall 0.904 / full-hit 0.800; +single-hop citation expansion (up to 5 chunks) 0.948 / 0.875; quantity-matched control that simply retrieves more (+34% chunks) 0.910 / 0.800. Gain concentrated on multi-hop queries with an edge (full-hit 0.500->0.714, n=14); no effect on single-hop; Wilcoxon p=0.059, not significant; authors call it suggestive. — [JAIC paper](https://jurnal.polibatam.ac.id/index.php/JAIC/article/download/14131/4022/46061) (read via local PDF conversion)
- Hyperlink-graph retrieval (Asai et al., 2019/ICLR 2020, older): HotpotQA full-wiki, intro paragraphs only (5.2M nodes, 23.4M edges). Hyperlinks make all gold paragraphs reachable for 75.4% of questions with top-20 TF-IDF seeds (35.1% without links), 84.1% with 100 seeds. Retrieval F=20: TF-IDF AR 39.7 / path EM 10.0 vs their learned recurrent path retriever AR 87.0 / 72.7. Hyperlinks beat an off-the-shelf entity linker (QA F1 72.4 vs 70.1). No ablation removes the graph entirely, and the retriever is trained (not training-free). — [Asai et al.](https://arxiv.org/html/1911.10470)
- Code dependency graphs: RepoGraph (ICLR 2025) reports +32.8% relative SWE-bench-Lite resolve rate from a line-level call/containment graph used as an agent tool; this is a resolve rate, not recall, and I did not read its recall ablations. — [RepoGraph search summary](https://arxiv.org/html/2410.14684v2)

### Inferences
- For this engine, the defensible graph feature is deterministic: parse intra-corpus citations ("nos termos do art. X") into an edge table and expand 1 hop from top-k seeds with a degree-penalised score bonus, evaluated against a count-matched "just retrieve more" control. Evidence points to benefit mostly on queries whose answer lives in a provision that is lexically distant from the seed (delegations, sanction/definition articles) and to small gain when the embedder is already strong.
- HippoRAG-style LLM triple graphs are not justified by cost: 3M output tokens and ~100 min for a 11.6k-passage corpus, for ~+5 recall@5 on multi-hop sets and no gain on single-hop fact retrieval. The "PPR contributes" evidence exists only for HippoRAG 1 on LLM triples; evidence for PPR over deterministic edges was not found.
- Graph gains in end-to-end QA partly reflect larger contexts (token-matched RAG nearly closes the gap).

### Gaps
- No study found with PPR specifically over a statute cross-reference graph; no published ablation of PPR in HippoRAG 2.
- Did not read the second GraphRAG-Bench paper (domain-specific reasoning) nor LightRAG's own paper; LightRAG numbers here come only from the HippoRAG 2 authors' reproduction and look anomalous.
- Korean and Indonesian studies are single-group, with the Indonesian one on 63 chunks and 40 queries (not significant).

## 2. Hierarchy, tree navigation, chunk granularity, breadcrumbs, late chunking

### Takeaway
Chunking on the document's own units (article/subsection) with a deterministic title/heading prefix is the best-supported zero-LLM option; LLM-built summary trees (RAPTOR) are not better than flat BM25/dense under matched budgets in 2026 replications and are very costly to build; naive two-stage hierarchical retrieval hurts; late chunking is inconsistent.

### Cited Findings
- RAPTOR (ICLR 2024, claimed by authors): QuALITY accuracy with UnifiedQA-3B BM25 49.9 -> 52.1, SBERT 54.9 -> 56.6, DPR 53.1 -> 54.7 with RAPTOR; QASPER F1 SBERT 36.23 -> 36.70; NarrativeQA ROUGE SBERT 29.26 -> 30.87; 18.5%-57% of retrieved nodes were non-leaf; tree-building linear in length. Gains with the weaker readers are +0.5 to +2.2 points. — [RAPTOR](https://arxiv.org/html/2401.18059)
- Independent matched-reader replication, "Tree Navigation Without LLM Summaries" (arXiv 2610.06902, Oct 2026, single preprint): QuALITY dev N=2,086, gpt-4o-mini reader, budget 1,024 tokens: BM25 71.0, SBERT-flat 71.6, DPR 72.1, hybrid 72.2, RAPTOR-extractive 68.1, deterministic leaves-only NavTree 72.5; at 2,000 tokens BM25 76.4, hybrid 77.0, RAPTOR-ext 71.3, NavTree 76.7. NavTree is within ~1.5 pts of the BM25+SBERT hybrid everywhere (parity, not a win). Original RAPTOR made 682 LLM summary calls on a 60-document slice, estimated ~$60k at million-document scale. Its tree is built from chunk position, not headings. — [Tree Navigation Without LLM Summaries](https://arxiv.org/html/2610.06902)
- German Civil Code (BGB) chunking study (arXiv 2605.19806): 2,455 hierarchical sections, 525 validation questions (~1.7 gold sections each); Recall@10 subsection retrieval 0.47, section retrieval 0.46, RAPTOR in the middle tier, fixed-size windows 0.30-0.40, Lumber 0.39-0.44. Build time section 51 s vs RAPTOR 3h04-5h51 vs Lumber 9-11.7 h; index 33.2 MB vs RAPTOR 68.5-144.1 MB. — [Chunking German Legal Code](https://arxiv.org/html/2605.19806)
- Placebo-controlled structure ablation (Kuehlkamp et al., arXiv 2610.10170, Oct 2026): 200 Wikipedia Featured Articles/951 queries and 1,585 QASPER papers/4,303 questions, cov-nDCG@10. Structure-aligned chunks with real heading paths beat contextualised fixed windows by +0.022 (Wikipedia) and +0.012 (QASPER); real heading paths beat shuffled-path placebo by +0.010 and +0.016; naive two-stage hierarchical retrieval (section first, then chunk) lost -0.033 and -0.015 because first-stage section recall is the bottleneck. Effects are small (effect size 0.06-0.11) though significant. The abstract does not make explicit that "contextualised fixed windows" are LLM-generated; I infer it. — [Does Document Structure Help Dense Retrieval?](https://arxiv.org/abs/2610.10170)
- Title-chain prefix (the document's own header hierarchy, zero LLM calls), production Markdown KB, 1,600 queries: MRR@5 0.374 -> 0.463 (+23.8%) for header-split + semantic merge + title-chain prefix versus fixed-threshold splitting; answerable subset (n=563) 0.828 -> 0.925. This confounds splitting and prefix; single-author preprint. The same paper warns that judging prefix on/off by relevance annotation is flawed (kappa 0.45 -> 0.04). — [Title-Chain Prefixes](https://arxiv.org/pdf/2608.00824) (read via local PDF conversion)
- Late chunking independent comparison (Merola & Singh, arXiv 2504.19754, 2025): NFCorpus nDCG@5/10 early vs late: Jina-v3 fixed 0.374/0.346 vs 0.380/0.354; Jina-v2 0.261/0.237 vs 0.280/0.255; BGE-M3 0.246/0.225 vs 0.070/0.067 (collapse; not trained for it); MS MARCO Stella-V5 early 0.630/0.632 vs late 0.503/0.505; contextual retrieval vs late on a 50-query/~300-doc NFCorpus subset 0.317/0.308 vs 0.309/0.294. Authors' conclusion: late chunking does not consistently beat early chunking. — [Reconstructing Context](https://arxiv.org/html/2504.19754v1)
- A 2026 reproduction (Zhou et al., arXiv 2602.16974) reports contextualised chunking (including late chunking) improves in-corpus retrieval but degrades in-document (needle) retrieval; only abstract-level information was read, no numbers. — [Beyond Chunk-Then-Embed](https://arxiv.org/abs/2602.16974)
- PageIndex (vectorless, LLM tree-search over a table-of-contents tree): the 98.7% FinanceBench figure is vendor-reported (Mafin 2.5); I found no independent reproduction. — [Search results, vendor claim](https://adityatrivedi17.substack.com/p/pageindex-vectorless-reasoning-based)
- Parent expansion / HypRAG README: Recall@5 0.092 -> 0.203 on CPython stdlib, not statutes, project README, not peer-reviewed. — [HypRAG on PyPI](https://pypi.org/project/hyprag/)

### Inferences
- Index the provision as the unit, prepend a deterministic breadcrumb (law title > book/title > chapter > article), and keep the section/article as the parent to display. Expected effect: small but positive (about +0.01 to +0.02 nDCG per the placebo-controlled study); do not expect LLM-context-level gains, and do not add a section-first two-stage retrieval.
- A RAPTOR or LLM-summary tree is not warranted for a 29k-norm corpus; BGE-M3-style chunk-level dense and BM25 match it.
- Late chunking requires a long-context embedder trained for it; skip with a small ONNX model.

### Gaps
- No legal-statute measurement of deterministic breadcrumb vs LLM-generated context head-to-head with exact numbers (the closest are the Wikipedia/QASPER ablation above and the KB study).
- DocAgent/HiRAG/TreeRAG/LongRAG not read; not enough time to verify their numbers.
- Anthropic contextual-retrieval headline numbers excluded as already covered.

## 3. Learned sparse and late interaction on CPU

### Takeaway
BGE-M3 sparse and SPLADE-v3 clearly beat BM25 in English/multilingual benchmarks, but on legal sets BM25 is already hard to beat, and the CPU/index costs of ColBERT-style systems are large; multi-vector gains over single-vector dense are about +1 to +1.5 nDCG on MIRACL.

### Cited Findings
- BGE-M3 on MIRACL dev (nDCG@10 avg, 18 languages; no Portuguese in MIRACL): BM25 31.9, dense 69.2, sparse 53.9, multi-vector 70.5, dense+sparse 70.4, all three 71.5. On MLDR (long documents) BM25 53.6, dense 52.5, sparse 62.2, dense+sparse 64.8, all 65.0. MKQA cross-lingual recall@100: sparse 45.3 vs dense 75.1 (sparse fails when query and passage languages differ). — [BGE-M3 paper](https://arxiv.org/html/2402.03216)
- SPLADE-v3: BEIR average 51.7 vs 50.7 for SPLADE++ SelfDistil; significantly better than BM25 on 41 of 44 query sets; SBERT model-card comparison lists BEIR-13 avg 50.0 (splade-v3-distilbert) vs BM25 45.6 (different setup). No CPU latency or index-size numbers found. — [alphaxiv summary of SPLADE-v3](https://alphaxiv.org/overview/2403.06789v1), [SBERT pretrained sparse models](https://sbert.net/docs/sparse_encoder/pretrained_models.html)
- Jina-ColBERT-v2 (multilingual, 89 languages claimed): BEIR avg nDCG@10 53.1 vs 49.6 ColBERTv2 (paper; launch post says 52.1), MIRACL avg 0.627 (model card), but ArguAna 36.6 vs 46.5 for ColBERTv2. — [Jina-ColBERT-v2](https://arxiv.org/pdf/2408.16672), search summary
- PLAID (2022) CPU latency on MS MARCO v1 (8.8M passages): vanilla ColBERTv2 3,485 ms/query single CPU, PLAID 185.5 ms (k=10) to 352 ms (k=1000); index 21.6 GiB (PLAID) vs 24.6 GiB. A ColBERT index for 8.8M passages is 20+ GiB. — [PLAID](https://arxiv.org/html/2205.09707)
- MUVERA (fixed-dimensional encodings): 10,240-dim FDEs; on BEIR, on average 10% higher recall and 90% lower latency than PLAID, but within 0.4% recall of PLAID on MS MARCO (no gain there); PQ-256-8 gives 32x compression of FDEs; FDE needs 2-5x fewer candidates than single-vector heuristic. — [MUVERA](https://arxiv.org/html/2405.19504)
- Reason-ModernColBERT (149M params, LightOn): BRIGHT mean 22.62 per model card; re-evaluation by another group got 20.79; mirrors list cc-by-nc-4.0 (verify on original card). — [Reason-ModernColBERT search result](https://huggingface.co/lightonai/Reason-ModernColBERT)
- Brazilian Portuguese legal retrieval (JUÁ sub-corpora, Dutra et al., ENIAC 2026): nDCG@10 BM25 (accent-normalised, NFD) vs BGE-M3 dense vs hybrid RRF(k=60): Ulysses legislative (668 queries) 0.545 / 0.311 / 0.503; JurisTCU 0.375 / 0.173 / 0.253; BR-TaxQA 0.595 / 0.710 / not run; NormasTCU (12k-token norms, whole-document encoding) 0.354 / 0.000 / 0.216; multilingual MiniLM 0.190, 0.068. Fusion with the weak dense list reduced nDCG vs BM25 alone (all significant at p<0.001). — [Small Language Models for Legal RAG in Portuguese](https://sol.sbc.org.br/index.php/eniac/article/download/46934/46691/) (read via local PDF conversion)

### Inferences
- On SQLite, a learned-sparse index (SPLADE/BGE-M3 sparse as a second FTS-like table) is feasible for 29k norms but query-side encoding needs a transformer pass; the measured gain over BM25 is in standard benchmarks, not legal ones. ColBERT/PLAID adds heavy infrastructure; for tens of thousands of provisions, brute-force MaxSim re-scoring of a top-100 BM25+dense pool would be simpler than PLAID, but I found no measurement for that.
- Portuguese legal evidence: BM25 should be the anchor with accent normalisation, dense used selectively.

### Gaps
- No CPU latency/index size for SPLADE-v3 and no ModernColBERT BEIR/multilingual or legal numbers; no ColBERT-on-legal measurements found; MUVERA-on-CPU small-corpus numbers not found.

## 4. Query expansion with the corpus's own vocabulary

### Takeaway
LLM-based expansion helps BM25 but hurts dense and strong retrievers and fails when the LLM lacks knowledge; corpus-steered expansion (CSQE) is the best-supported variant, whereas RM3 is roughly neutral on BEIR; for statutes, Rocchio PRF on dense embeddings gave mixed results. Multi-query fusion recall gains vanish after reranking.

### Cited Findings
- CSQE (EACL 2024): across six BEIR sets nDCG@10 averages BM25 43.7, BM25+RM3 42.4, BM25+CSQE 49.7 (CSQE uses LLM to select key sentences from BM25 top documents plus LLM knowledge). — [CSQE search summary](https://arxiv.org/pdf/2402.18031)
- "LLM-based query expansion fails" (SIGIR 2025 short): for BM25 with Llama-8B, query2doc gains on NQ +7.42 (LLM lacks knowledge) vs +9.44 (has knowledge); MS MARCO -1.13 vs +4.00; with Contriever dense, Q2D on MS MARCO -14.10/-8.24 and BioASQ -10.02/-1.89; E5-base-v2 BioASQ -11.25/-4.27. High ambiguity reduces recall. Paraphrase-style expansion (GaQR) is least sensitive. — [LLM-based QE Fails](https://arxiv.org/html/2505.12694v1)
- Mackie et al. 2023 (older): expansions help weak retrievers and hurt strong ones; nDCG@10 changes from Q-LM PRF on DL19: BM25 -4.0, SPLADEv2 -4.3, ColBERTv2 -4.2, MonoT5-3B -2.8; on FiQA BM25 +4.5, SPLADEv2 +1.3, ColBERTv2 -0.4. — [When do generative query and document expansions fail?](https://arxiv.org/html/2309.08541)
- Statutes: Rocchio PRF on dense (SearchFireSafety, k=15) gave +0.45 R@10 on Qwen3-Emb-0.6B and -1.24 on BGE-M3. — [SearchFireSafety](https://aclanthology.org/2026.acl-long.2112.pdf)
- RAG-Fusion multi-query (industry study, March 2026, N=115 queries, one reformulation, RRF): fusion raises raw recall but gains are neutralised after reranking/truncation; Hit@10 fell from 0.51 to 0.48 in several configurations; added latency. Original RAG-Fusion evidence was manual and anecdotal. — [RAG Fusion industry deployment](https://arxiv.org/pdf/2603.02153v1) (read via local PDF conversion for N and Hit@10 text)
- Doc2Query--: filtering generated queries up to ~16% effectiveness gain over doc2query on MS MARCO; index size figures differ between versions (33% vs 48% reduction). Metric not confirmed. Requires a GPU seq2seq model at index time. — [Doc2Query--](https://arxiv.org/pdf/2301.03266)
- Knowledge leakage may inflate reported gains of LLM QE (arXiv 2504.14175; secondary summary only). — [search summary](https://arxiv.org/pdf/2504.14175)

### Inferences
- With a 29k-norm domain-specific corpus, an LLM that "lacks knowledge" of Portuguese statute vocabulary is exactly the failure condition; the safe variant is agent-side term feedback from first-pass results (CSQE-like), plus alias/title dictionaries built deterministically from the norms' own titles and defined terms. No measurement found for a statute-title/alias dictionary.
- RM3 on legal sets: no published number found (see Gaps).

### Gaps
- No RM3 numbers on legal statute sets found; COLIEE statute QE papers are LLM-based and not read in detail. No legal thesaurus measurement found.

## 5. Rerankers 2025-2026

### Takeaway
Rerankers reliably help but have measured failure modes: scaling candidate depth degrades quality, reasoning rerankers do not beat same-backbone non-reasoning rerankers, and legal Portuguese reranker evidence is thin. For CPU, only sub-1B cross-encoders on top-20 to top-50 candidates are plausible.

### Cited Findings
- "Rank1 loses to the same model without reasoning" (Jedidi, Chuang, Glass, Lin 2026, "Don't Overthink Pointwise Reranking"): with same Qwen2.5 backbone and training data, Rank0 beats Rank1 on MS MARCO avg nDCG@10 by 3.7/5.0/5.7 points at 3B/7B/14B (e.g. 7B: Rank0 62.4 vs Rank1 57.1) and on BRIGHT avg by 1.0/3.2/5.2 (7B: 31.0 vs 27.5; 14B: 33.9 vs 28.7); Rank1-NoReason (dummy reasoning) 58.3 vs Rank1 57.2 on MS MARCO at 3B; explanation: once Rank1 deems a passage relevant it gives near-identical scores, so it can't rank degrees of relevance. — [Don't Overthink Pointwise Reranking](https://cs.uwaterloo.ca/%7Ejimmylin/publications/Jedidi_etal_2026.pdf) (read via local PDF conversion)
- Earlier version (2025): StandardRR vs ReasonRR vs ReasonRR-NoReason, BRIGHT avg at 7B 31.0 / 27.8 / 30.8; DL19 74.6 / 70.3 / 73.3. Conclusion: reasoning gives no general advantage; reasoning helps somewhat only at smaller sizes on BRIGHT. Original Rank1 reported 27.5 on BRIGHT for the 7B with reasoning vs 17.5 without (different training), the claim the replications contest. — [Don't Overthink Passage Reranking](https://arxiv.org/html/2505.16886v1)
- "Drowning in Documents" (Nov 2024, v2 July 2025): rerankers tested jina-reranker-v2-base-multilingual, bge-reranker-v2-m3, Cohere rerank-english-v3.0, voyage-rerank-1, gpt-4o-mini listwise; 8 datasets (BRIGHT, BIRCO, SciFact, FinanceBench etc.); of 60 academic experiments the reranker helps at some K in 85%, never hurts in only 23.3%, scaling K ends below the retriever in 53.3% (44.4% enterprise); largest K is best in only 3.3%; "phantom hits" where bge-reranker-v2-m3 ranked an irrelevant document 2nd and the positive 34th. Listwise LLM kept improving with K. — [Drowning in Documents](https://arxiv.org/html/2411.11767)
- Qwen3-Reranker (Qwen's own run, reranking top-100 from Qwen3-Embedding-0.6B): MTEB-R/CMTEB-R/MMTEB-R 0.6B 65.80/71.31/66.36; 4B 69.76/75.94/72.74; 8B 69.02/77.45/72.94; bge-reranker-v2-m3 57.03/72.16/58.36; jina-multilingual-reranker-v2-base 58.22/63.37/63.73. Vendor numbers, no independent verification found. — [Qwen3 Embedding blog](https://qwenlm.github.io/blog/qwen3-embedding)
- jina-reranker-v3 (0.6B): BEIR nDCG@10 61.94 (paper abstract, own run); no head-to-head tables read; weights licence not verified (paper page shows CC BY-NC-SA, applying to paper). — [jina-reranker-v3](https://arxiv.org/abs/2509.25085)
- mxbai-rerank-v2 (Mixedbread, Apache 2.0): BEIR avg nDCG@10 large (1.5B) 57.49, base (0.5B) 55.57, Cohere rerank-3.5 55.39, bge-reranker-v2-gemma 55.38; Mr.TyDi avg 29.79 / 28.56 (vendor; conflicting Jina vs Mixedbread numbers for the same Jina model, 57.06 vs 54.35). — [mxbai-rerank-v2](https://mixedbread.com/blog/mxbai-rerank-v2)
- Portuguese: PROPOR 2026 cascade-of-rerankers paper for Portuguese legal search exists (bi-encoder then BGE and Qwen rerankers) but the PDF URL returned 404 and results were not read; JBCS 2026 compares BM25/ptT5/BGE-M3/RankGPT on Quati and Pirá 2.0, not read in detail. JUÁ's reranking baseline is a fine-tuned Qwen3-Embedding-4B. — [search result list](https://journals-sol.sbc.org.br/index.php/jbcs/article/view/5659)

### Inferences
- A cross-encoder rerank over a short pool (about 20-30) is supported; deeper pools risk phantom hits, so reranking should be fused with the first-stage score rather than replace it (inferred; not tested in a legal setting here).
- Reasoning/listwise rerankers are not worth the cost on CPU.

### Gaps
- No measured Qwen3-Reranker, jina-v3, mxbai or Cohere 4 results on Portuguese legal retrieval; no CPU latency numbers for any of these rerankers found; RankZephyr/FIRST/ReasonRank/Rank-K and Cohere rerank 4 not covered.

## 6. Fusion

### Takeaway
Tuned convex combination beats RRF in and out of domain; RRF with default k=60 gives most of the lift but is parameter-sensitive; a weak dense list hurts both RRF and score fusion; per-query alpha has measured gains but needs an LLM at query time.

### Cited Findings
- Bruch et al. (TOIS 2023) NDCG@1000 (NFCorpus, SciFact @100), lexical / semantic / convex (TM2C2, alpha 0.8) / RRF(k=60): MS MARCO 0.309/0.441/0.454/0.425; NQ 0.382/0.505/0.542/0.514; HotpotQA 0.682/0.520/0.699/0.675; FEVER 0.689/0.558/0.744/0.721; SciFact 0.698/0.681/0.753/0.730; NFCorpus 0.268/0.296/0.327/0.312; FiQA 0.315/0.467/0.496/0.464. RRF below the lexical-only baseline on HotpotQA (0.675 vs 0.682). RRF tuned in-domain (5,5) lifts HotpotQA 0.675->0.693 but (10,4) drops it to 0.621; alpha between 0.6 and 0.8 consistently helps; alpha converges with <5% of training data; normalisation choice is a minor detail. — [Analysis of Fusion Functions](https://ar5iv.labs.arxiv.org/html/2210.11934)
- Weak dense list hurts: Portuguese legal Ulysses BM25 0.545 vs RRF hybrid 0.503 (dense 0.311); JurisTCU 0.375 vs 0.253 (dense 0.173); SearchFireSafety RRF on dense lowered R@10 (BGE-M3 53.77->49.77). — [JUÁ study](https://sol.sbc.org.br/index.php/eniac/article/download/46934/46691/), [SearchFireSafety](https://aclanthology.org/2026.acl-long.2112.pdf)
- DAT (dynamic alpha, March 2025): an LLM scores each retriever's top-1 and sets alpha per query. SQuAD (585 paragraphs, 2,976 questions): P@1 BM25 0.7594, dense 0.7396, fixed alpha 0.6 0.8461, DAT (GPT-4o-mini) 0.8676, GPT-4o 0.8740. DRCD (3,000 questions): BM25 0.7630, dense 0.5743, fixed 0.8113, DAT 0.8417 (GPT-4o-mini). Gains over fixed alpha are +0.02 to +0.03 P@1 (larger on a "hybrid-sensitive" subset); needs LLM calls. Small corpora. — [DAT](https://arxiv.org/html/2503.23013v1)

### Inferences
- Use a convex combination with min-max/z-normalised scores and alpha tuned on a small labelled set (a few dozen queries); put weight toward BM25 on Portuguese legal text; include a no-dense baseline in every evaluation. Per-query routing could use cheap features (e.g. score gap, query length) but no measurement without an LLM was retrieved.

### Gaps
- No Portuguese-legal tuned-alpha measurement; no no-LLM query-adaptive fusion numbers read.

## 7. Small multilingual embedders (CPU)

### Takeaway
Qwen3-Embedding-0.6B (Apache-2.0, MTEB-Multilingual retrieval 64.64) is strongest among documented small models but 0.6B and 1024-d; EmbeddingGemma-300M is smaller with a restrictive licence; Jina v5 models are CC BY-NC. ONNX availability is not stated on most model cards.

### Cited Findings
- Qwen3-Embedding-0.6B: MTEB-Multilingual mean(task) 64.33, retrieval 64.64; 32K context; dim up to 1024; Apache-2.0; safetensors, ONNX not mentioned. Same table: multilingual-e5-large-instruct 63.22 / 57.12, BGE-M3 59.56 / 54.60. — [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- EmbeddingGemma-300M: ~308M params, 2,048 tokens, MTEB(Multilingual v2) mean(task) 61.15, mean(type) 54.31 at 768-d; Q8 60.93, Q4 60.62; Matryoshka 768/512/256/128; Gemma licence (accept-terms); retrieval-specific score not on the card; ONNX not mentioned. — [EmbeddingGemma-300m](https://huggingface.co/google/embeddinggemma-300m), [paper](https://arxiv.org/html/2509.20354)
- gte-multilingual-base: ~305M, 8,192 tokens, Apache-2.0, 70+ languages, optional sparse output; numeric scores only in images. — [gte-multilingual-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-base)
- snowflake-arctic-embed-m-v2.0: Apache-2.0, ONNX weights listed, 74 languages; scores and param count not obtained here (known to be ~305M, not verified in this session). — [arctic-embed-m-v2.0](https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0)
- jina-embeddings-v5-text (2026): nano 239M (MMTEB 65.5, 8,192 ctx), small 677M (MMTEB 67.0, MTEB-M retrieval 64.88 per search summary, 32,768 ctx); CC BY-NC 4.0 (non-commercial); GGUF yes, ONNX folder claimed for small but not confirmed for nano; self-reported. — [Jina v5 post](https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings), [HF card search](https://huggingface.co/jinaai/jina-embeddings-v5-text-small)
- BGE-M3 (568M) zero-shot on Portuguese legal text lost to BM25 on 3 of 4 sub-corpora (see Section 3); 8,192-token limit truncates long norms. Multilingual MiniLM-L12 (118M) near zero on legal. — [JUÁ study](https://sol.sbc.org.br/index.php/eniac/article/download/46934/46691/)

### Inferences
- If a licence-safe small embedder is needed, Qwen3-Embedding-0.6B (Apache) and gte-multilingual-base (Apache, 305M) are the candidates; EmbeddingGemma and Jina v5 carry licence restrictions. Provision-level chunks avoid the context-length problem.

### Gaps
- No MTEB(Multilingual) retrieval-only scores for EmbeddingGemma, gte-multilingual-base, arctic-m-v2.0, multilingual-e5-small obtained (leaderboard not read); no ONNX confirmation for Qwen3-Embedding-0.6B and EmbeddingGemma on their model cards; no Portuguese-specific per-model scores here (earlier notes cover MTEB-BR).

## 8. Temporal benchmarks

### Takeaway
Retrievers degrade sharply when queries carry temporal constraints; LLMs are poor at date arithmetic and neither web search nor code reliably fixes it (code interpreter hurt GPT-5 on implicit-constraint puzzles); explicit dates in prompts are the largest measured fix.

### Cited Findings
- FreshQA (500 questions, 125 each of fast/slow/never-changing/false-premise), strict accuracy: GPT-4 without search 28.6 (fast-changing 12.0, slow 4.0); with FreshPrompt search evidence 75.6 (fast 59.2); evidence count 1/5/10/15 gives 61.4/70.6/75.6/77.6; evidence ordering by time 74.8 vs random 72.4. — [FreshQA](https://arxiv.org/html/2310.03214)
- Test of Time (ICLR 2025): ToT-Arithmetic accuracy GPT-4 / Claude-3-Sonnet / Gemini 1.5 Pro: AddSubtract 76.3/58.6/71.1, Duration 16.0/15.0/13.5, Schedule 43.6/29.6/40.0, Timezone 88.0/74.0/90.0, MultiOp 46.9/26.6/62.6; ToT-Semantic Timeline 28.3/24.0/36.3; fact order matters (shuffled 60.7 GPT-4 vs best 65.4). Dataset size is inconsistent within the paper (1,850 vs 2,800 arithmetic). — [Test of Time](https://arxiv.org/html/2406.09170)
- Time Puzzles (arXiv 2601.07148, Jan 2026): tool-less exact match on implicit date constraints GPT-5 55.3, GPT-4.1 35.2, GPT-5-nano 15.8, GPT-4.1-nano 9.3; rewriting constraints as explicit dates raises GPT-4.1-nano to 41.8, GPT-5-nano to 60.2, GPT-5 to 84.7. Code interpreter lowered GPT-5's implicit-constraint performance; helped GPT-4.1 only with web search; exact tool-run values are only in figures. — [Time Puzzles](https://arxiv.org/html/2601.07148v3)
- TempRAGEval/MRAG (EMNLP Findings 2025): on perturbed TimeQA questions evidence recall@5 BM25 14.1, Contriever 28.7, Contriever+Gemma reranking 66.6, MRAG 74.3; SituatedQA ER@5 18.4, 17.1, 45.3, 59.2. Gemma on SituatedQA drops top-1 answer recall 85.8 -> 54.7 from original to perturbed questions. Llama3.1-8B EM/F1 on TimeQA 44.0/52.8 (concat RAG) vs 49.2/59.2 (MRAG); GPT-4o-mini no retrieval 19.6/30.6. — [MRAG](https://arxiv.org/html/2412.15540v2)
- Temporal retrieval, news archives: BM25 beat DPR on ArchivalQA (EM 64.60, F1 75.37); TempRetriever date-embedding fusion +6.63% top-1 over DPR on ArchivalQA. — [TempRetriever search summary](https://arxiv.org/html/2502.21024v2)
- MultiHop-RAG temporal sub-type: RAG 30.70 vs HippoRAG2 49.91 (see Section 1).
- Date tokenisation: a study finds errors from subword fragmentation of dates (arXiv 2505.16088; summary only).

### Inferences
- For a time-versioned legal corpus the data suggest doing version selection and date arithmetic outside the LLM (deterministic date filter on validity intervals, ISO dates), since both the retrievers and the models are weak when time is implicit; code execution is only a partial remedy.

### Gaps
- Not covered: TempReason, TimeBench numbers, ChronoQA (could not confirm existence), SituatedQA/TimeQA original papers; no clean with/without-code accuracy for date arithmetic in tabular form.
