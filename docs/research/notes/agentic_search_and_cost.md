# Agentic search / agentic RAG: accuracy drivers and cost control (as of Nov 2026)

Scope note: ~15 web tool calls. Several numbers come from search-tool summaries of primary pages; those are flagged. Items I did not verify are in Gaps, not stated as findings.

## What drives accuracy in agentic search (rounds, planning, sufficiency, tools)

### Takeaway
On a fixed corpus, accuracy tracks how much the agent searches and how strong the retriever and model are; weak or untrained models barely use the search tool. Retriever quality is a first-order lever and also cuts search calls. Sufficiency-aware abstention and step-level rewards are the best-evidenced ways to improve precision and cut wasted searches.

### Cited Findings
- BrowseComp-Plus (fixed corpus, human-verified evidence docs, hard negatives). gpt-5: BM25 55.90% acc / 61.70% recall / 23.23 search calls; Qwen3-Embedding-8B 70.12% / 78.98% / 21.74 calls. o3: 49.28% to 63.49% (25.93 to 23.97 calls). gpt-4.1: 14.58% to 35.42%. Gemini 2.5 Pro: 19.04% to 28.67% (7.44 calls). Sonnet 4: 14.34% to 36.75%. Opus 4: 15.54% to 36.14%. Search-R1 32B: 3.86% to 10.36%; Qwen3-32B 3.49% to 10.36% — [arXiv 2508.06600](https://arxiv.org/html/2508.06600v1) (ACL 2026 version: [aclanthology](https://aclanthology.org/2026.acl-long.1023/))
- Same paper: gpt-5/o3 average >20 search calls per query; Qwen3-32B and Search-R1 make <2 even when prompted to search. The better retriever cut calls by roughly 1-3 for most proprietary models — [arXiv 2508.06600](https://arxiv.org/html/2508.06600v1)
- Search-R1 (RL-trained search agent, older 2025 result): abstract reports +24% (Qwen2.5-7B) and +20% (Qwen2.5-3B) over RAG baselines across seven QA datasets. Secondary summaries give conflicting figures (41%, 26%), so use the abstract's 24%/20% — [arXiv 2503.09516](https://arxiv.org/abs/2503.09516)
- IRCoT (2023, GPT-3 / Flan-T5; older result): interleaving retrieval with CoT raised retrieval recall by up to 21 points and QA by up to 15 points over one-step retrieval on HotpotQA, 2Wiki, MuSiQue, IIRC; a 3B Flan-T5-XL with IRCoT beat 58x larger GPT-3 with one-step retrieval — [ACL 2023](https://aclanthology.org/2023.acl-long.557), [arXiv 2212.10509](https://arxiv.org/pdf/2212.10509.pdf)
- Sufficient Context (ICLR 2025): frontier models answer well when context is sufficient but often answer wrongly instead of abstaining when it is not; correct answers still occur 35-62% of the time with insufficient context; sufficiency-guided selective generation raised the fraction correct among answered queries by 2-10% for Gemini, GPT, Gemma; small open models (Mistral, Gemma 2) hallucinate or abstain even with sufficient context — [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/33dffa2e3d2ab74a783d1a8c292f66d9-Abstract-Conference.html), [arXiv 2411.06037](https://arxiv.org/abs/2411.06037)
- Adaptive retrieval survey-style benchmark (ACL 2025, 35 methods): simple uncertainty estimators often match complex pipelines (FLARE, DRAGIN, Self-RAG, Adaptive-RAG) on QA accuracy with better efficiency; no method dominates all axes — [arXiv 2501.12835](https://arxiv.org/html/2501.12835v1) (via search summary; exact numbers not read)
- Anthropic Contextual Retrieval: top-20 chunk retrieval failure rate 5.7% to 3.7% (contextual embeddings, -35%), 2.9% (+ contextual BM25, -49%), 1.9% (+ reranking, -67%). This is failure-rate reduction, not accuracy gain — [Anthropic](https://anthropic.com/research/contextual-retrieval)
- Tool design: Anthropic reports rewriting tool descriptions cut task completion time by 40% for later agents — [Anthropic multi-agent post](https://www.anthropic.com/engineering/multi-agent-research-system)
- Grep vs vectors: "Is Grep All You Need?" (PwC, arXiv 2605.15184) on 116 LongMemEval questions, 4 harnesses x 5 models: lexical grep 83.6-93.1% vs vector 62.9-83.6%; harness and result delivery format (inline vs file) could erase the grep lead. Conversational memory, not enterprise docs or code; I read only secondary summaries — [summary](https://academy.dair.ai/papers/is-grep-all-you-need). Practitioner claims (Claude Code dropped its vector DB for staleness reasons; Augment says embeddings still matter on large codebases; Cursor combines both) are unmeasured anecdotes — [Augment lessons](https://jxnl.co/writing/2025/09/11/why-grep-beat-embeddings-in-our-swe-bench-agent-lessons-from-augment/)

### Inferences
- The engine's "up to 4 more searches" loop is far below the 20+ calls the strongest agents use on BrowseComp-Plus-class tasks, but those are very hard puzzle tasks; for HotpotQA-style multi-hop, 2-4 rounds is the range the older literature (IRCoT) used. A cap of 4 is unlikely to be the main limiter; the retriever and the stop/continue judgement are likelier levers (retriever swap gave +9 to +22 points; loop depth no comparable measured effect here).
- Weak/uncalibrated models under-search (Qwen3-32B, Search-R1 <2 calls): a loop that merely permits extra searches yields little unless the model reliably uses them.
- Using a sufficiency autorater as the continue/stop and abstain signal is the best-supported addition.

### Gaps
- No exact per-dataset numbers found for Self-Ask, ReAct, Search-o1, DeepResearcher, PlanRAG, Plan*RAG, Adaptive-RAG, SIM-RAG, stop-RAG or 2026 successors; not retrieved.
- No measured effect size isolating number of search rounds for HotpotQA/MuSiQue/2Wiki/FRAMES/MultiHop-RAG with a modern model.
- Sufficient Context per-dataset sufficiency fractions not read.

## Reasoning budget / extended thinking and search agents

### Takeaway
More reasoning effort raises agentic retrieval accuracy but mostly by inducing many more searches, so accuracy and cost rise together.

### Cited Findings
- BrowseComp-Plus, gpt-oss: higher reasoning effort improves accuracy and recall at all sizes/retrievers; oss-20B calls rise from ~2 (low) to ~24 (high); oss-120B with Qwen3-Embed-8B 24.94% (low) to 42.89% (high); calibration error falls with effort — [arXiv 2508.06600](https://arxiv.org/html/2508.06600v1)
- Anthropic: extended thinking used as a controllable scratchpad for planning and tool selection; reported improvements are qualitative, no numbers — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- Anthropic: token usage alone explained ~80% of BrowseComp performance variance; tokens + tool-call count + model choice explain 95% — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)

### Inferences
- Because effort acts via search count, a thinking budget without a search budget is not an independent knob; control both and measure accuracy per token.

### Gaps
- No clean numbers on thinking budget with fixed search count; no BRIGHT, FRAMES or MultiHop-RAG reasoning-model data found.

## Query rewriting / HyDE / expansion

### Takeaway
Generative expansion helps weak retrievers and distribution-shifted or long queries and tends to hurt strong retrievers.

### Cited Findings
- Weller et al. (EACL Findings 2024; 11 expansion methods, 12 datasets, 24 retrievers): expansion improves weaker models and generally harms stronger ones due to added noise; exception is long-query shift where it helps most models. Authors advise using it only for weak retrievers or format-shifted data — [paper](https://ar5iv.labs.arxiv.org/html/2309.08541)
- 2026 work: LLM rewriting effectiveness depends on whether substitution moves toward or away from corpus terms ([arXiv 2603.13301](https://arxiv.org/pdf/2603.13301)); LLM rewriting fails under adversarial conditions while pseudo-document methods give modest robust gains ([arXiv 2604.06097](https://arxiv.org/pdf/2604.06097)). Summaries only.
- Anthropic: overly long, specific queries returning few results listed as an observed agent failure — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)

### Gaps
- No HyDE-versus-modern-reranker numbers found; no multi-query fusion measurements located.

## Parallel fan-out and diminishing returns

### Takeaway
Parallelism buys latency, not accuracy per token; token spend is the accuracy driver.

### Cited Findings
- Parallel tool calling cut research time by up to 90% on complex queries (3-5 subagents, 3+ parallel tools each). Multi-agent uses ~15x tokens of chat, single agent ~4x; the 90.2% gain was on an internal research eval (not BrowseComp), Opus 4 lead + Sonnet 4 subagents vs single Opus 4 — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- Effort-scaling rules: simple fact-finding 1 agent / 3-10 calls; comparisons 2-4 subagents / 10-15 calls each; complex research 10+ subagents — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)

### Gaps
- No per-round marginal accuracy curve found.

## Cost control

### Takeaway
Biggest measured levers: cache stable prefixes, route easy queries to cheap paths, train/prompt against over-search. Router savings from primary papers were not verified by me.

### Cited Findings
- Prompt caching: 5-min write 1.25x base, 1-hour write 2x, read 0.1x (lower on newest models, e.g. 0.05x Opus 5.5 per pricing page snippet); break-even after 1 read (5-min) or 2 reads (1-hour); stacks with Batch API discount — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing). Check live page for per-model values.
- Over-search RL: SAAS reports 45.8% acc with 1.13 searches/question on Qwen2.5-3B, 40.2% fewer searches than best baseline and +2.2 points; AdaSearch 34-38% fewer unnecessary calls, ~20% lower latency; SlimSearcher 17-58% fewer rounds; HiPRAG step-level process rewards. AdaSearch notes raw call counts conflate necessary and unnecessary calls and penalties can be gamed — via [search summary](https://www.themoonlight.io/en/review/saas-self-aware-reinforcement-learning-for-over-search-mitigation-in-agentic-search), [HiPRAG](https://arxiv.org/html/2510.07794v1). Not primary-verified.
- Routing: FrugalGPT up to 98% cost reduction at matched quality (best case); RouteLLM ~26% of queries to GPT-4 reaches 95% of its MT-Bench score (14% with extra data); AutoMix beats FrugalGPT/HybridLLM on cost-performance curves — secondary summaries of [FrugalGPT 2305.05176](https://arxiv.org/abs/2305.05176), [RouteLLM](https://arxiv.org/html/2406.18665v4), [AutoMix](https://arxiv.org/pdf/2310.12963). Benchmarks are chat, not retrieval QA.
- Adaptive-RAG: classifier (T5-large) picks no / single / multi-step retrieval — [via summary](https://arxiv.org/html/2501.12835v1)

### Inferences
- A small-model-first loop with escalation when a sufficiency check fails mirrors Self-Route (below) and over-search work; no direct measurement for retrieval agents found.
- Stable system prompt + tool defs + accumulated passages is cache-friendly across rounds; break-even of one read makes caching nearly always worthwhile for multi-round loops.

### Gaps
- Semantic/answer caching and batch-API accuracy/cost measurements for QA agents: none found.
- No cascade-with-confidence-early-exit numbers for agentic RAG.

## Long context vs retrieval

### Takeaway
Long context beats plain RAG on accuracy; RAG is much cheaper; routing by model self-assessment recovers most LC accuracy at a fraction of tokens.

### Cited Findings
- Self-Route (Google DeepMind, EMNLP 2024 industry; Contriever, 300-word chunks, top-5): averages LC / RAG / Self-Route: Gemini-1.5-Pro 49.70 / 37.33 / 46.41 (76.78% routed to RAG, 38.39% of LC tokens); GPT-4O 48.67 / 32.60 / 48.89 (57.36%, 61.40%); GPT-3.5-Turbo 32.07 / 30.33 / 35.32. Reported cost cuts 65% (Gemini) and 39% (GPT-4O). ~63% of LC and RAG predictions identical. Paper has internal inconsistencies (e.g. routed share 76.78% vs 81.74% in text) — [arXiv 2407.16833](https://arxiv.org/html/2407.16833v2)
- Top-k ablation (Gemini): RAG 20.24 (k=1), 37.92 (5), 41.20 (10), 44.06 (50), 44.12 (100) with token ratio up to ~100% of LC at k>=50 — same paper
- Older models (2024); no 2026 long-context threshold found. A claim of "26x per-query token cost" from intuitionlabs is unverified.

### Gaps
- No late-2026 reported crossover threshold (corpus size) with current models.

## Failure modes

### Takeaway
Documented failures: over-searching, wrong abstention behaviour, unsupported answers, over-long queries.

### Cited Findings
- Anthropic-observed: 50 subagents for simple queries, endless search for nonexistent sources, continuing after sufficient results, over-specific queries, wrong tool choice — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- Outcome-only RL increases over-search by reducing no-search trajectories (SAAS summary, above); heuristics against searching can teach avoiding needed searches (HiPRAG summary).
- Frontier models answer instead of abstaining on insufficient context ([ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/33dffa2e3d2ab74a783d1a8c292f66d9-Abstract-Conference.html)); under-searching in weak models (BrowseComp-Plus, above).
- Weaker-model premature stopping evidenced indirectly: Search-R1 / Qwen3-32B <2 calls vs >20 for gpt-5/o3.
- March 2026 systematization names stable adaptive retrieval and cost-aware orchestration as open problems — [arXiv 2603.07379](https://arxiv.org/html/2603.07379)

### Gaps
- No measured citation-fabrication rates with retrieval found (BrowseComp-Plus reports citation accuracy but I did not read those numbers); no quantified query-drift study found.
