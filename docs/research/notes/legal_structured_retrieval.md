# Retrieval recall on legal / structured hierarchical corpora (state: Nov 2026)

Method note: ~17 web searches/fetches, mostly search-snippet summaries; only BR-TaxQA-R and Reasoning-Focused Legal Retrieval were page-fetched. Numbers marked (snippet) were not checked against the paper's tables. Many items in the brief (LeCaRD, AILA, LePaRD tables, voyage-law-2, Legal-BERTimbau, RAPTOR/HippoRAG2 exact numbers, VCB thesaurus, late chunking, SPLADE/ColBERT on legal, jina/mxbai/Qwen3 rerankers, RankGPT/FIRST) were NOT researched; see Gaps.

## 1. Legal retrieval benchmarks and best-known results

### Takeaway
Across statute/legal benchmarks, BM25 is a strong and often hard-to-beat zero-shot baseline, especially at small k; dense models only clearly win after in-domain fine-tuning (BSARD, STARD) or when they are strong commercial/large models (JurisTCU). Lay-query-to-statute vocabulary mismatch is the dominant failure mode and absolute recall is low on every benchmark with lay queries.

### Cited Findings
- BR-TaxQA-R: 715 questions from the 2024 Brazilian tax authority Q&A, over 478 statutory/regulatory documents and 7,204 CARF rulings; baseline uses only dense retrieval (OpenAI text-embedding-3-small, FAISS flat L2), chunking by 2,048-token sliding window (1,024 stride) or a recursive splitter with statutory-hierarchy separators (1,000 chars, 100 overlap). No BM25/hybrid/rerank recall numbers reported in the paper's text. — [arXiv 2505.15916](https://arxiv.org/html/2505.15916v1)
- BSARD (French, Belgian law; 1,100+ questions, 22,600+ articles): best baseline R@100 74.8% (fine-tuned two-tower bi-encoder); leaderboard lists BM25 R@100 51.33, Siamese 71.63, two-tower 74.78 (marked unverified there). Dense beats BM25 by ~15-25 pts, but the dense models are fine-tuned on in-domain data. — [ACL 2022 / BSARD listing](https://www.hyper.ai/cn/sota/tasks/information-retrieval/benchmark/information-retrieval-on-bsard), [paper page](https://huggingface.co/papers/2108.11792) (snippet)
- STARD (Chinese, 1,543 real non-professional queries, 55,348 statutes): best method only R@100 = 0.907; non-fine-tuned lexical/neural models are weak at mapping life issues to legal facts; a follow-up reports BM25/QL beat several zero-shot neural models (RoBERTa, SAILER) because statutes carry distinctive legal keywords. — [STARD](https://arxiv.org/pdf/2406.15313), [Generative Chinese Statute Retrieval](https://arxiv.org/pdf/2607.11109) (snippet; no per-model table seen)
- Reasoning-Focused Legal Retrieval (Bar Exam QA, Housing Statute QA; corpus ~1.84M statute passages, 6,853 yes/no questions): Bar Exam QA Recall@10 BM25 5.03%, E5-large-v2 7.00% (vs 40.4/68.7 on Natural Questions). Housing Statute QA Recall@10: BM25 18.3 (all gold) to 40.8 (any gold); E5-large-v2 24.4 to 50.6. Structured reasoning-rollout query expansion: BM25 +10.27 +/-1.08 pts, E5 only +2.16 +/-1.15 — i.e. expansion helps lexical retrievers far more than dense. — [arXiv 2505.03970](https://arxiv.org/html/2505.03970v1)
- LegalBench-RAG (original benchmark, 2024): Recursive character splitting beat naive chunking; Cohere rerank-english-v3.0 on top of OpenAI embeddings gave lower performance than no reranking (secondary summaries, exact numbers not retrieved). A 2025 follow-up claims SBERT/GTE with tailored retrieval improved Recall@K by 30-95% — claimed, not verified. — [summary](https://www.themoonlight.io/review/legalbench-rag-a-benchmark-for-retrieval-augmented-generation-in-the-legal-domain), [follow-up arXiv 2508.13107](https://arxiv.org/html/2508.13107v2)
- CLERC (US case law): zero-shot BGE 42.4 vs BM25 48.3 (metric not confirmed in snippet); a 2026 paper confirms zero-shot dense underperforms BM25 on CLERC. LeCaRD-v2: R@100 BM25 48.79, bge-m3 37.05, SAILER 28.28, ReaKase 42.05 (BM25 better at small cutoffs; dense competitive only at R@1000). — [CLERC](https://arxiv.org/pdf/2406.17186), [2026 fenced-citation paper](https://arxiv.org/pdf/2607.17142), [LeCaRD-v2 Findings ACL 2026](https://aclanthology.org/2026.findings-acl.2152.pdf) (snippets)
- JurisTCU (Brazilian TCU jurisprudence; 16,045 docs, 150 queries): OpenAI embeddings beat lexical and BERT-based; BERT-based models performed poorly (authors do not recommend); document expansion (docT5query + LLM synonyms) improves BM25, >45% on P@10/R@10/nDCG@10 for short keyword queries (secondary summary). — [arXiv 2503.08379](https://arxiv.org/pdf/2503.08379)
- COLIEE 2025 statute task: test set 73 questions over 768 Civil Code articles; approaches BM25 + sentence-transformer, LLM extraction + rerank + majority vote. No per-run recall retrieved. — [ANLP 2026 paper](https://www.anlp.jp/proceedings/annual_meeting/2026/pdf_dir/TS3-11.pdf) (snippet)
- MLEB (Oct 2025, 10 legal datasets, NDCG@10): Isaacus Kanon 2 Embedder 86.03, Voyage 3 Large 85.71, Voyage 3.5 84.07; Gemini Embedding (MTEB #1) ranks 7th on MLEB, i.e. general leaderboard rank does not transfer to legal. Benchmark authors are a vendor (self-interest). — [arXiv 2510.19365](https://arxiv.org/pdf/2510.19365)
- German legal NanoGerDaLIR (leaderboard page): BM25 R@100 0.8426 vs reranking_hybrid 0.8553 — hybrid+rerank gives small gain at depth 100. — [leaderboard](https://hakari-bench-leaderboard.hf.space/docs/benchmark-tasks/NanoLaw/NanoGerDaLIRSmall) (not peer reviewed)

### Inferences
- The user's 58% BM25 hit@8 on BR-TaxQA-R is in a plausible range relative to lay-query benchmarks (BSARD BM25 R@100 ~51%, Housing Statute R@10 18-41%); the BR-TaxQA-R paper itself publishes no BM25 baseline, so the user's number may be among the first.
- Dense models should not be expected to beat BM25 zero-shot on statutes unless they are large or in-domain tuned; the user's e5-small hybrid result is consistent with literature.

### Gaps
- No numbers found for ColBERT/late interaction or SPLADE on legal corpora, AILA, LePaRD, Ulysses, BEIR/BRIGHT legal subsets, or Portuguese legal IR beyond JurisTCU.

## 2. Why hybrid can underperform BM25; fusion; embedders

### Takeaway
Hybrid fusion only helps when the two rankers have comparable quality; a weak dense list injects noise into RRF. Convex combination with a tuned weight (few dozen labelled queries) is the better-supported fusion; with a weak embedder the optimal weight collapses toward BM25. Stronger embedders for Portuguese run on CPU via ONNX.

### Cited Findings
- Bruch et al.: tuned convex combination outperforms RRF in- and out-of-domain, is sample efficient (one parameter), RRF is sensitive to its parameters; RRF k=60 remains the zero-label default. — [arXiv 2210.11934](https://arxiv.org/abs/2210.11934v2)
- Example of RRF degradation: Touché BM25 0.650 nDCG@10, dense 0.390, RRF 0.604 (blog, source unverified). — [tianpan.co](https://tianpan.co/blog/2026-04-12-hybrid-search-production-bm25-dense-embeddings)
- Claim (vendor blog): 50-100 labelled query pairs suffice to tune alpha — not from Bruch et al. — [bigdataboutique](https://bigdataboutique.com/blog/hybrid-search-fusion-methods-compared)
- Portuguese MTEB-BR retrieval (model-card, self-reported): colibri-embed-ptbr (~157M) 0.6501; embeddinggemma-300m 0.6490; multilingual-e5-large-instruct 0.6409; bge-m3 0.6157; multilingual-e5-large 0.5909. ONNX CPU latency ~33 ms (Colibri) vs 38 ms (embeddinggemma-300m), single-node indicative. No independent Qwen3-Embedding MTEB-BR number found. — [model card](https://huggingface.co/tardellirs/colibri-embed-ptbr)
- Dense models in the legal domain: general MTEB rank is not predictive (MLEB above); BERT-style (non-embedding-tuned) models perform poorly (JurisTCU above).

### Inferences
- Move from e5-small to multilingual-e5-large-instruct / embeddinggemma-300m / bge-m3 and fuse with convex combination (min-max or z-score normalised BM25 + cosine, alpha tuned on a few dozen dev questions per set), keeping alpha biased to BM25. A cheap guard: fall back to BM25-only when tuned alpha ~1.
- Dense mainly adds value on queries where BM25 misses entirely; evaluate fusion per-query (wins vs losses), not only aggregate.

### Gaps
- No legal-specific Portuguese models (Legal-BERTimbau, JurisBERT) or voyage-law-2 numbers retrieved; no verified ONNX throughput for bge-m3/Qwen3-Embedding-0.6B.

## 3. Bridging lay-to-statutory vocabulary gap

### Takeaway
Expansion helps lexical retrieval most; LLM-generated expansion beats RM3 PRF in general benchmarks; in legal, reasoning-based query expansion adds ~10 pts R@10 for BM25. Deterministic, LLM-free alternatives (document-side expansion, headings, thesauri) are less measured in legal.

### Cited Findings
- Structured legal-reasoning query expansion: BM25 +10.27 pts Recall@10 on Housing Statute QA; E5 +2.16. — [arXiv 2505.03970](https://arxiv.org/html/2505.03970v1)
- query2doc: +3 to +15% on BM25 on MS-MARCO/TREC DL; RM3 only 52.2 vs 51.2 nDCG@10 baseline on DL19 vs query2doc 66.2. — [arXiv 2303.07678](https://arxiv.org/pdf/2303.07678)
- Jedidi & Lin (SIGIR 2026), 14 datasets: feedback models work better with LLM-generated documents than with BM25 top-ranked documents. — [PDF](https://cs.uwaterloo.ca/%7Ejimmylin/publications/Jedidi_Lin_SIGIR2026.pdf)
- GuRE trains an LLM to rewrite queries for LePaRD passage retrieval; BM25+GuRE outperforms BM25+Query2Doc-CoT (columns unclear in snippet). — [arXiv 2505.12950](https://arxiv.org/html/2505.12950v2)
- Portuguese legal precedent study: HyDE outperforms dense retrieval (Recall@1 0.086 to higher; comparison vs dense, not BM25). — [ENIAC](https://sol.sbc.org.br/index.php/eniac/article/download/47018/46775/)
- JurisTCU document expansion (docT5query, LLM synonyms) >45% improvement for short queries — see section 1.

### Inferences
- Offline document expansion (doc2query-style or synonyms per article) has legal evidence on Brazilian data (JurisTCU) but needs an LLM at index time; cheap for 29k norms if done once with a small model, but this conflicts with the "no LLM index" constraint only partially.
- Query-time LLM expansion with a legal-reasoning prompt is the best measured lever for BM25 on lay queries; RM3-style PRF has weak evidence.

### Gaps
- No measurements found for CSQE, VCB/Tesauro thesaurus expansion, or deterministic statute-name/citation recognition effects.

## 4. Structure-aware retrieval and LLM-built graphs

### Takeaway
Contextual headers have vendor-measured large gains; deterministic breadcrumb prefixes are the LLM-free analogue but unmeasured in sources found. LLM-built graph indexes are costly and not consistently better than plain RAG.

### Cited Findings
- Anthropic contextual retrieval: top-20 failure rate 5.7% to 2.9% (contextual embeddings + contextual BM25, -49%) and to 1.9% with reranking (-67%); vendor's own datasets, and the context is LLM-generated per chunk. — [Anthropic](https://anthropic.com/research/contextual-retrieval), [critique](https://medium.com/almond-ai/responding-to-anthropics-contextual-retrieval-for-rag-apps-why-context-is-not-all-you-need-af503985aa55)
- LegalBench-RAG: recursive splitting beats naive chunking (above). BR-TaxQA-R paper uses hierarchy-aware separators in its splitter.
- PageIndex (tree/ToC LLM navigation, no vectors): vendor reports 98.7% on FinanceBench for Mafin 2.5; no independent verification found; commentators note slower/costlier than vector lookup. — [GitHub mirror](https://github.com/fglogan/PageIndex), [overview](https://yuv.ai/blog/pageindex)
- RAG vs GraphRAG (Han et al.): methods complementary; plain RAG better on single-hop NQ, graph methods (HippoRAG2, community GraphRAG local) better on multi-hop; GraphRAG construction requires the whole corpus through an LLM. — [arXiv 2502.11371](https://arxiv.org/pdf/2502.11371)
- GraphRAG-Bench indexing times (snippet): KGP ~205 s, ToG ~1,080 s, MS GraphRAG ~1,797 s; HippoRAG longest; corpus/hardware unstated. LazyGraphRAG ~0.1% of GraphRAG cost: vendor claim, unverified. — [arXiv 2506.02404](https://arxiv.org/pdf/2506.02404)

### Inferences
- Statutes already have an explicit hierarchy (norm > title > chapter > article > paragraph/inciso); a deterministic breadcrumb (law name, chapter, article heading) prepended to each indexed chunk for BM25 and embedding is the zero-LLM analogue of contextual retrieval; expect gains mostly for short/ambiguous provisions (my inference; not measured here).

### Gaps
- No numbers for RAPTOR, late chunking, small-to-big, article vs paragraph granularity on legal; HippoRAG 2 paper numbers not read.

## 5. Deterministic citation / cross-reference graphs

### Takeaway
Multiple 2025-2026 papers report large recall gains from graph expansion over statute structure and citations, but controls are weak in several.

### Cited Findings
- Chinese Civil Code (LawExamQA_Civil): ExpertGraph raises Recall@8 27.99% to 72.53%, R@20 50.52% to 81.07% vs naive RAG (the graph is LLM/expert-built, not purely deterministic). — [LEGO, arXiv 2609.27009](https://arxiv.org/pdf/2609.27009) (snippet)
- Indonesian ITE law: RRF hybrid + citation-graph expansion overall recall 0.948, Full-Hit Rate 0.875, with a quantity-matched RRF control. — [CEUR Vol-4312](https://ceur-ws.org/Vol-4312/paper26.pdf) (snippet; small corpus likely)
- German legal codes: ~22,000 intra-code edges from citation tagging, covers ~90% of ground-truth citations; one-hop expansion compared across chunk granularities. — [arXiv 2604.06173](https://arxiv.org/pdf/2604.06173) (snippet)
- BSARD GNN work uses statute hierarchy to enrich article representations. — [fugumt summary](https://fugumt.com/fugumt/paper_check/2301.12847v1_enmode)
- NyayGraph (Indian penal law): KG inference improves recall but KG context in prompts reduces precision; reranking needed. — [NLLP 2025](https://preview.aclanthology.org/ingest-emnlp/2025.nllp-1.11.pdf) (snippet)

### Inferences
- One-hop expansion (referenced articles, same-chapter neighbours, parent caput) appended after top-k raises candidate recall at cost of precision; evaluate against a quantity-matched control (extra k from the base retriever).

### Gaps
- No PPR-specific legal results, G-DSR or CaseGNN numbers retrieved.

## 6. Rerankers

### Takeaway
Rerankers help precision, not first-stage recall, and general-domain cross-encoders can hurt legal; reasoning rerankers help on BRIGHT-style tasks but no legal-statute evidence found.

### Cited Findings
- Cohere reranker lowered results vs none on LegalBench-RAG (above).
- LexPath: with gold in top-5 pre-rerank, 1.62% (STARD), 2.27% (LexRAG), 1.10% (StatuteRAG) lose it from the top-5 after a general neural reranker. — [arXiv 2605.30205](https://arxiv.org/pdf/2605.30205)
- Multi-phase COLIEE-style pipeline: some queries drop recall after LLM rerank; ~3% of samples have zero recall after BERT rerank, which LLM rerank cannot fix (first-stage ceiling). — [arXiv 2403.18093](https://arxiv.org/pdf/2403.18093)
- BRIGHT: non-reasoning RankZephyr barely beats/does not beat BM25 on most sets; Rank1-32B averages 28.34 nDCG@10, ReasonRank-32B reported 40.6 (secondary). — [ReasonRank](https://arxiv.org/pdf/2508.07050), [Rank-R1](https://arxiv.org/pdf/2503.06034)
- Candidate depth: dense top-300 reaches high-recall region but gold may sit below output cutoff — rerank depth must be large enough. — LexPath above (snippet)

### Inferences
- Rerank only a deep pool (e.g. 50-100), use reranker score as one feature fused with first-stage rank, never as sole ordering, and gate by validated per-dataset comparison (consistent with user's 2/3 dev sets regression).

### Gaps
- bge-reranker-v2-m3, jina-reranker, mxbai-rerank-v2, Qwen3-Reranker, RankGPT/FIRST, sliding-window comparisons and costs not researched.

## 7. Agentic / iterative retrieval

### Takeaway
Iterated multi-perspective reformulation with pooling is reported to beat single-shot RAG on Chinese statute retrieval, but no clean ablation vs a better first stage was found.

### Cited Findings
- LegalMALR (Jan 2026): multi-agent rewrites, up to 4 retrieve rounds, pooled candidates, zero-shot LLM rerank to top 10; reports substantial gains over RAG baselines on 118-query CSAID and STARD (Recall@10, MRR@10); LLM variability across reformulations noted. — [arXiv 2601.17692](https://arxiv.org/html/2601.17692)
- COLIEE 2026 entry: QRHead reranking after dense retrieval; recall maintained but low F2 due to article selection. — [NOWJ](https://arxiv.org/pdf/2607.16603)

### Inferences
- The reformulation-and-pool pattern is the agentic equivalent of query expansion; combine with BM25 keyword tools plus "open neighbouring articles" (graph expansion) and measure recall of the pooled set, not just the final answer.

### Gaps
- No direct "agentic vs better first-stage" ablation; no grep-style tool studies for statutes found.
