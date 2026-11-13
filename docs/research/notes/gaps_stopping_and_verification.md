# Gaps: agentic multi-hop stopping rules and answer verification for RAG QA (state as of Nov 2026)

Conventions: "measured" = number read from the primary paper's text/tables; "calc" = my own arithmetic; "claimed" = abstract/secondary claim not verified in tables. Older (2023-24) results are marked [old]. Figures that exist only in charts could not be read and are listed under Gaps.

## 1. Multi-hop agentic methods: per-dataset results, same-generator comparisons, marginal rounds, stopping rules

### Takeaway
Iterative/agentic retrieval helps strongly on HotpotQA-style bridge questions but results are NOT uniform: on 2Wiki and MuSiQue a training-free agent can underperform single-shot RAG with the same 7B backbone. Learned stop critics (Stop-RAG, SIM-RAG) give modest measured gains (about +0.4 to +3.3 EM) over fixed-iteration or LLM self-judged stopping, mostly by saving rounds; the SIM-RAG critic is poor at accepting correct answers on multi-hop data, and its gains were not independently reproduced as a critic.

### Cited Findings
Same-generator single-shot vs agentic (Qwen2.5-7B-based, Contain-EM, dense retriever):
- Single-shot dense RAG: HotpotQA 19.00 / 2Wiki 35.53 / MuSiQue 20.99. Training-free agent Search-o1-7B: 33.76 / 29.64 / 12.62. RL agent Search-R1-7B: 35.76 / 33.56 / 14.42. Avg search turns on HotpotQA: Search-o1 2.20, Search-R1 1.82. The paper does not confirm identical generators across rows; its F1 table is inconsistent with EM, so treat with caution (measured, 2026 benchmarking paper) — [Do We Still Need GraphRAG? 2604.09666](https://arxiv.org/html/2604.09666)
- Search-R1 paper (Qwen2.5-7B, EM, NQ/TQA/PopQA/HotpotQA/2wiki/MuSiQue/Bamboogle, avg): Direct 0.181; CoT 0.106; IRCoT 0.239; Search-o1 0.206; plain RAG 0.304; SFT 0.207; R1 (no search) 0.276; Search-R1-base 0.431 (HotpotQA 0.433, 2wiki 0.382, MuSiQue 0.196). Instruct variant avg 0.385. Plain RAG on 2wiki 0.235 vs Search-R1 0.382; on MuSiQue 0.058 vs 0.196 (measured). Masking retrieved tokens: avg EM 0.431 vs 0.343 without; top-3 passages best of k in {1,3,5}. Abstract claims +24% (7B) / +20% (3B) average relative to RAG baselines — [Search-R1](https://arxiv.org/html/2503.09516)
- DeepResearcher (Qwen2.5-7B-Instruct, live web, F1 / model-judged MBE): HotpotQA 52.8/64.3, 2Wiki 59.7/66.6, MuSiQue 27.1/29.3, Bamboogle 71.0/72.8, NQ 39.6/61.9, TQ 78.4/85.0, PopQA 48.5/52.7. Beats Search-o1 (web) and R1-Searcher on MBE everywhere; Search-r1-base (local RAG) is higher on F1 for NQ (45.4) and HotpotQA (55.9). CoT+RAG HotpotQA 37.1/43.8. Qualitative behaviours (plan revision, cross-checking after first hit, declining to answer when not found) are described but not measured; the paper says current metrics do not measure the refusal behaviour — [DeepResearcher](https://arxiv.org/html/2504.03160)
- IRCoT vs one-step retrieval (OneR) [old, 2022]: answer F1 gain Flan-T5-XXL / GPT3 code-davinci-002: HotpotQA +9.4 / +7.1; 2Wiki +15.3 / +13.2; MuSiQue +5.0 / +7.1; IIRC +2.5 / ~0. Recall gains up to +22.6 (GPT3, 2Wiki). Loop stops at an "answer is" statement or 8 steps, 15 paragraphs cap. IRCoT with Flan-T5-XL (3B) beat OneR with 58x larger GPT3 — [IRCoT](https://arxiv.org/html/2212.10509)
- Adaptive-RAG [old, 2024]: T5-Large router (no / single / multi-step). FLAN-T5-XL avg F1 46.94 vs 48.85 for always-multi-step, time/query 3.60 vs 8.81 relative units; GPT-3.5 roughly equal accuracy at about half the time. Small/base/large classifiers perform similarly — [Adaptive-RAG](https://arxiv.org/html/2403.14403) (summary-level numbers from fetch)
- FRAMES (824 multi-hop questions, Gemini-Pro-1.5) [old, 2024]: no retrieval 0.408; BM25 2 docs 0.452; BM25 4 docs 0.474; multi-step retrieval with planning 0.66; oracle (gold articles given) 0.729. So multi-step closes about 78% of the no-retrieval-to-oracle gap (calc: (0.66-0.408)/(0.729-0.408)) — [FRAMES](https://arxiv.org/html/2409.12941)
- MultiHop-RAG [old, 2024]: with retrieved chunks GPT-4 0.56, Claude-2.1 0.52, PaLM 0.47, ChatGPT 0.44, Mixtral 0.32; with ground-truth evidence GPT-4 0.89. Best retrieval Hits@10 0.7467 (voyage-02 + bge-reranker); GPT-4/Mixtral reported as "relatively good" on null queries (no exact figure in text) — [MultiHop-RAG](https://arxiv.org/html/2401.15391)
- Government-document study (Qwen3-32B judge-scored 0-100, 1,000 Qs): basic RAG 81.0; one-shot with token-constrained top-Kmax 87.5; one-shot + chunk filter 91.0; basic agentic loop 83.5; agentic + fallback + chunk delete 90.0. Agentic Qwen3 retrieves ~59% more often than basic RAG; DeepSeek-R1 agent 81.5 overall (93.1 only on non-refused). Nearly half of errors were failure to retrieve the golden chunk in top-k. Domain-specific, single-source — [Fishing for Answers](https://arxiv.org/html/2509.04820)
- BRIGHT (ICLR 2025): top MTEB retriever 59.0 on MTEB vs 18.0 nDCG@10 on BRIGHT; BM25 with GPT-4 reasoning query 26.5. BRIGHT-Pro (2026) evaluates 3-round agentic search with alpha-nDCG at k=5/10/15; I could not read its tables (leaderboard value ~44.9 unverified) — [BRIGHT search results](https://arxiv.org/pdf/2605.04018). A separate enterprise paper reports BRIGHT+FinanceBench recall@1 8.41% single-shot vs 43.49% (GPT-5-mini agent) and 49.59% (Claude Sonnet 4.5 agent), different models, retrieval metric only — [AgenticRAG 2605.05538](https://arxiv.org/pdf/2605.05538)
- Older iterative/adaptive methods under Llama3/E5-BM25 (SIM-RAG paper table, EM HotpotQA / 2Wiki): StandardRAG 25.1 / 8.6; FLARE 19.7 / 25.8; IRCoT 28.6 / 23.5; DRAGIN (Llama2/BM25) 23.7 / 22.4; Self-RAG 17.1 / 12.1; Auto-RAG 31.9 / 38.8. With GPT-4/BM25: StandardRAG 35.7 / 28.7 (measured, reproduced by SIM-RAG authors, so baselines may be under-tuned) — [SIM-RAG](https://arxiv.org/html/2505.02811v2)
- Probing-RAG (Gemma-2B / Mistral-7B, avg of 5 datasets, EM/ACC): Probing-RAG 22.8/35.8 and 23.0/34.7; Adaptive-RAG 14.0/26.8 and 20.7/30.2; DRAGIN 22.4/25.1 and 21.2/28.1; FLARE 11.8/21.3 and 18.8/29.9; single-step 14.0/27.4 and 19.4/32.4. Retrieval calls (Gemma-2B): Probing-RAG 1,988 vs DRAGIN 13,570, Adaptive-RAG 3,068, FLARE 5,317. Prober accuracy "near 0.7". Needs hidden-state access (open models only) — [Probing-RAG](https://arxiv.org/html/2410.13339v2)
- ReSP: claimed +4.1 F1 on HotpotQA and +5.9 on 2Wiki over prior SOTA (abstract level; tables not read) — [ReSP search summary](https://arxiv.org/abs/2407.13101)

Stopping rules (learned critic vs self-judgement):
- Stop-RAG (Llama-3.1-8B-Instruct, Contriever-MSMARCO + bge reranker, max 10 iterations, single run, no CIs). Own pipeline EM: MuSiQue fixed 34.5 / LLM-Stop 34.2 / Stop-RAG 36.8; HotpotQA 51.0 / 51.4 / 52.4; 2Wiki 64.9 / 64.9 / 68.2. Steps: MuSiQue 10.0 / 7.6 / 8.6; 2Wiki 10.0 / 5.0 / 5.1. On CoRAG (fine-tuned for fixed iterations) gains are tiny (MuSiQue 30.9 -> 31.5 EM) and negative on HotpotQA (55.0 -> 54.7). LLM self-judged stopping saved steps but gave no accuracy gain. Learning target ablation (MuSiQue EM): binary classifier 33.3, Monte Carlo 36.0, Q(0) 36.0, Q(lambda) 36.8. No oracle bound reported — [Stop-RAG](https://arxiv.org/html/2510.14337v1)
- SIM-RAG critic (Llama3 / GPT-4, BM25; EM HotpotQA, 2Wiki): full 32.7 / 34.1 (Llama3), 39.8 / 46.1 (GPT-4) vs StandardRAG GPT-4 35.7 / 28.7, i.e. +4.1 EM HotpotQA and +17.4 EM 2Wiki for GPT-4. On a 500-question HotpotQA dev subset the final-round gain is +10.1 over NaiveGen and an Oracle Critic reaches 47.2%. Critic accepts correct answers at only 13.6% (HotpotQA, 2Wiki) vs 60.3% on TriviaQA; correct rejection 63.9% / 65.0%. The weak accept rate implies over-retrieval (inference from measured rates) — [SIM-RAG](https://arxiv.org/html/2505.02811v2)
- 2026 reproducibility study (SIGIR '26) compares MetaRAG to SIM-RAG but explicitly does not reproduce it: SIM-RAG (Llama3.3, retrieval only) HotpotQA EM 43.1; with BGE/RankGPT reranking it collapses to 21.4 / 18.7 (2Wiki 38.3 -> 14.5 / 12.8), suggesting the fine-tuned critic is brittle to input distribution (hypothesis untested). Cost: 6.5 requests/question (GPT-3.5, $21.3 per 500 Qs) vs 14.1 (Llama3.3) — [Metacognitive RAG reproducibility](https://arxiv.org/html/2604.19899)
- Sufficient-context follow-up detail (beyond headline): selective generation combining sufficiency label + self-confidence gave >10 pts at high accuracy for Gemma 27B on HotpotQA and >5 pts for Gemini 1.5 Pro near 70% coverage, but nothing on MuSiQue (Gemma 27B 18.4% accuracy; sufficiency coefficient zero). Fine-tuning Mistral 7B to say "I don't know" did not raise abstention — [Sufficient Context](https://arxiv.org/html/2411.06037)

### Inferences
- Marginal accuracy per round is front-loaded: Search-R1 averages ~1.8 turns on HotpotQA, Stop-RAG saves ~15-50% of steps for flat-to-+3 EM. Rounds beyond 2-3 buy little unless the question is genuinely deep (MuSiQue/2Wiki), where the learned stopper helps most.
- A learned value/critic helps most when trained on the deployed pipeline's own trajectories; it generalises poorly across retrievers/rerankers (SIM-RAG collapse, Stop-RAG on CoRAG). Plan to retrain the stop controller whenever retriever/reranker changes.
- Prompted LLM self-stop is roughly neutral on accuracy (Stop-RAG LLM-Stop ~= fixed) and its sufficiency judgement is the weak point; combine with a calibrated sufficiency signal rather than relying on it.
- Agentic gains over strong single-shot are dataset dependent (2Wiki negative for training-free agent), so keep a single-shot path and route (Adaptive-RAG style) rather than always looping.

### Gaps
- No paper found that holds the generator fixed and compares single-shot / iterative / agentic with matched retriever on HotpotQA+2Wiki+MuSiQue+FRAMES+BRIGHT; closest is 2604.09666 (generator equality not confirmed).
- Self-Ask, ReAct, FLARE, PlanRAG/Plan*RAG, DRAGIN primary tables not read (only reproduced numbers via SIM-RAG/Probing-RAG). Self-RAG appears under-performing in reproductions, which may reflect setup.
- BRIGHT-Pro agentic round-by-round tables unreadable; MultiHop-RAG per-query-type numbers only in figures; no Search-R1 numbers for turn-count scaling.

## 2. Answer verification: CoVe, round-trip/back-question, relevance metrics, QA faithfulness, sampling-consistency, re-retrieval

### Takeaway
CoVe gives large gains on list/biography tasks but with many extra LLM calls and no RAG-specific QA evidence; sampling-based consistency (semantic entropy AUROC ~0.79 vs 0.69-0.70 for naive baselines) is the best-measured black-box confidence signal but costs ~5-10x generations; answer-relevancy-by-back-question is only 0.78 agreeable with humans and does not test correctness; re-retrieval with the answer as the query is only 70-80% accurate in the one primary study found.

### Cited Findings
- CoVe (Llama 65B) [old, 2023]: Wikidata list precision 0.17 baseline -> 0.29 joint / 0.36 two-step / 0.32 factored; Wiki-Category 0.12 -> 0.15 / 0.21 / 0.22; MultiSpanQA F1 0.39 -> 0.46 joint / 0.48 factored; biography FActScore 55.9 -> 60.8 joint / 63.7 factored / 71.4 factor+revise (ChatGPT 58.7, PerplexityAI 61.6, InstructGPT 41.1). Cost: factored variant needs "many more" LLM prompts (parallelisable); no exact call counts reported. No retrieval used in verification — [CoVe](https://arxiv.org/html/2309.11495)
- CoV-RAG (Llama2-13b backbone, accuracy): NQ 66.0, WebQ 68.5, Mintaka 78.5, TriviaQA 87.5, avg 75.1 vs WebGLM-Llama2-13b 73.8 (+1.3 avg) and Self-RAG 64.1; ChatGPT beats it on TriviaQA (88.0). Verification module: judgment accuracy 56.0 -> 60.0 with score->judge->revise chain; revise accuracy 45.8 -> 54.2. The verifier's judgment accuracy is only 60% (measured) — [CoV-RAG](https://arxiv.org/html/2410.05801v1)
- Answer-as-query re-retrieval check (gpt-3.5-turbo, MS MARCO V1, 6,980 Qs) [old, 2023 workshop paper]: neural stack+reader labels were correct 80% (Yes), 71% (No), 74% (Not Related) on manual checks; BM25 vs neural labels agree ~82%; authors conclude it "cannot be fully relied upon". BM25 passage was poor in 43.3% of 30 agreeing cases — [Retrieving Supporting Evidence](https://arxiv.org/html/2306.13781)
- RAGAS answer relevance = mean cosine (ada-002) between original question and n LLM-generated questions from the answer; does not check factuality. Agreement with humans on WikiEval: answer relevance 0.78 (GPT Score baseline 0.52, GPT Ranking 0.40), faithfulness 0.95 — [RAGAS](https://arxiv.org/html/2309.15217). I found no primary study measuring correlation of answer relevancy or the TruLens triad with answer correctness; the 0.78 is pairwise preference agreement on subtle variants, not correctness correlation.
- QAFactEval (SummaC benchmark, avg balanced accuracy): QAFactEval 77.8; supervised QAFactEval-NLI 79.5; MNLI 75.7; DAE 72.7; QuestEval 68.2. Ablation: dropping answerability penalty 77.5 -> 72.1; dropping both filter and penalty 67.4. QA-based check adds ~2 pts over best NLI alone and ~3.8 pts in combination (significant at 99%) — [QAFactEval](https://arxiv.org/html/2112.08542)
- Semantic entropy (Nature 2024), 30 task-model combinations, AUROC: semantic entropy 0.790; naive entropy 0.691; P(True) 0.698; embedding regression 0.687; 0.78-0.81 across LLaMA/Falcon/Mistral 7B-70B. Does not catch consistently wrong answers (training errors, misconceptions); clustering sensitive to dates/numbers. Sampling cost 5-10x — [Farquhar et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750); cost from [SEP](https://arxiv.org/html/2406.15927)
- Semantic entropy probes (single generation, hidden states): in-distribution AUROC difference vs accuracy probe -2.0 to +2.8 (mixed); on unseen tasks +2.2 to +10.5 AUROC points in SEP's favour (Mistral-7B +10.5, Llama-2-7B +7.7, Llama-2-70B short +7.9, Llama-3-70B long +6.2) — [SEP](https://arxiv.org/html/2406.15927)
- SelfCheckGPT (GPT-3 WikiBio passages, N=20 samples): NonFact AUC-PR: BERTScore 81.96, QA 84.26, Unigram 85.63, NLI 92.50, Prompt 93.42; harder NonFact* 45-53; passage Pearson 58-78. Prompt variant cost ~$200 (davinci) / ~$20 (ChatGPT) for 1,908 sentences x 20 samples [old pricing] — [SelfCheckGPT](https://arxiv.org/html/2303.08896)

### Inferences
- For an engine: use cheap NLI/QA-factuality entailment of each claim against retrieved evidence (QAFactEval-style, measured ~78-80 balanced accuracy) plus sampling agreement only for high-stakes or borderline items; re-retrieval verification should not be a sole gate (<=80% label accuracy, small old study).
- Back-question/answer-relevancy checks detect off-topic or incomplete answers, not wrong ones. Treat as a minor feature in an abstention scorer, not as evidence of correctness.
- Semantic entropy's blind spot (consistently wrong) is exactly the failure retrieval-grounded checks cover; the two are complementary (inference).

### Gaps
- No primary measure found of RAGAS answer relevancy / TruLens correlation with correctness; no FEQA primary numbers read; no CoVe cost in tokens; no 2025-26 paper found that measures "ask the question the answer answers" round-trip as a correctness verifier in RAG.

## 3. False-premise and unanswerable detection

### Takeaway
Models mostly fail to reject unanswerable or false-premise queries unless prompted or trained; RAG itself reduces abstention. Best measured abstention on unanswerable contexts is ~72% (best model, CoT) and negative-rejection rates in RGB are 5-31% (exact-match).

### Cited Findings
- FaithEval unanswerable (avg over 10 datasets, strict): Claude 3.5 Sonnet 0.621, GPT-4o 0.597, Gemma-2-27B 0.546, GPT-4o-mini 0.523, Llama-3.1-70B 0.479, GPT-4-turbo 0.468, Llama-3.1-8B 0.376, Phi-3-medium 0.074. Best 71.8% with CoT. Inconsistent: Claude 3.5 0.944, GPT-4o 0.932, GPT-4-turbo 0.855, GPT-4o-mini 0.570, Llama-3.1-70B 0.563. Counterfactual: GPT-4o 96.3% closed-book -> 47.5% with counterfactual context. CoT helped; task-specific "conflict" instruction did not and cost ~5 points on normal contexts for Claude 3.5; sampling gave marginal gains. Larger is not reliably more faithful — [FaithEval](https://arxiv.org/html/2410.03727v3)
- RGB (2023): negative-rejection (exact match / ChatGPT-judged): ChatGPT 24.67/45.00 (EN), 5.33/43.33 (ZH); Qwen-7B 31.0/35.67 (EN); ChatGLM-6B 9.0/25.0; BELLE 5.67/32.33. Noise robustness: ChatGPT EN accuracy 96.33 (0% noise) -> 76.00 (80% noise). Counterfactual docs: ChatGPT-en accuracy 89 -> 9 with counterfactual docs, error detection ~8 (units ambiguous in table) — [RGB](https://arxiv.org/html/2309.01431)
- CRAG [old, 2024]: 525 false-premise questions. GPT-4-Turbo straightforward RAG: accuracy 43.6%, hallucination 30.1%, missing 26.3%, truthfulness 13.4%. Industry SOTA (human eval): Copilot Pro 62.6% perfect / 17.9% hallucination; Gemini Advanced 60.8 / 16.6; ChatGPT Plus 59.8 / 25.0; Perplexity 55.8 / 25.3. False-premise per-category values only in figures — [CRAG](https://arxiv.org/html/2406.04744)
- (QA)^2 [old, 2022]: 602 questions, ~half with questionable assumptions (246 false + 55 unverifiable of 301). Human-judged acceptability: davinci zero-shot 28% (18% questionable vs 38% valid); text-davinci-003 in-context 56% (50% vs 62%); REALM 18%. In-context demos narrowed the gap (Flan-PaLM gap 40 -> 4 points) — [(QA)^2](https://arxiv.org/html/2212.10003)
- CREPE [old, 2022]: 26.0% (2,202 / 8,466) of ELI5 questions have false presuppositions. Detection macro-F1 test: retrieval-based c-REALM classifier 66.3 (67.1 with self-labelling), human 85.1 with most-voted comment and 70.9 without; correction uF1 37.4 (main track) — [CREPE](https://arxiv.org/html/2211.17257)
- Legal false-premise (Magesh et al.): Lexis+ AI, Westlaw AI-AR and GPT-4 "quite capable" at navigating false-premise queries; Ask Practical Law AI seldom hallucinated but refused most queries. 22 of 202 queries were false premise; accuracy highest on that category — [Magesh et al. HTML](https://arxiv.org/html/2405.20362)
- Large Legal Fictions [old, 2024] zero-shot contra-factual bias (SCOTUS false-premise): "false overruling" hallucination GPT-3.5 0.821, PaLM 2 1.000, Llama 2 0.027 (Llama 2's low rate partly from claiming the case does not exist); ECE PaLM 2 0.057, GPT-3.5 0.099, Llama 2 0.421 — [Large Legal Fictions](https://arxiv.org/html/2401.01301)
- Sufficient-context paper: RAG paradoxically reduces abstention (Claude 3.5 Sonnet 84.1% -> 52%, Gemini 1.5 Pro 100% -> 18.6%, GPT-4o 34.4% -> 31.2%); on human-labelled insufficient-context cases models abstain 50-73% but hallucinate 15-40% — [Sufficient Context](https://arxiv.org/html/2411.06037)

### Inferences
- Unanswerable detection is a separate trained/calibrated head, not a prompt: prompt-level "say IDK" instructions measured weak. CoT helps modestly. Abstention training on small models was inconsistent.
- Datasets conflate "unanswerable", "false premise", "inconsistent" and "counterfactual"; the engine's eval should keep these as separate slices.

### Gaps
- No 2026 measurements for current frontier models on FaithEval/CRAG false-premise slices found; AbstentionBench excluded per scope.

## 4. Conflicting evidence

### Takeaway
Models rarely flag conflict unprompted; prompting and multi-agent aggregation help, but absolute performance remains low (RAMDocs EM ≤ 34.4 for the best method on Llama3.3-70B; expected-behaviour adherence for opinion conflicts 36.2%).

### Cited Findings
- CONFLICTS (Google 2025): 458 queries (297 conflicting) from FreshQA, SituatedQA, QACC, ConflictingQA; five-type taxonomy with expected behaviour: no conflict; complementary information; conflicting opinions/research outcomes; freshness (outdated); misinformation. Conflict-type prediction accuracy: Gemini 2.5 Flash 65.3%, Gemini 2.0 Flash 60.5%, GPT-4o 59.2%, Gemma 3 27B 53.9%, Qwen 2.5 72B 53.1%. Oracle type prompting +~24 points adherence; pipeline (predict type then answer) +~9; taxonomy-aware one-pass +~5.5; "conflicting opinions" hardest at 36.2% adherence (Gemini 2.5 Flash Thinking, vanilla) — [DRAGged into Conflicts](https://arxiv.org/html/2506.08500)
- RAMDocs / MADAM-RAG (COLM 2025), EM: Llama3.3-70B: FaithEval 43.10 / AmbigDocs 58.20 / RAMDocs 34.40 for MADAM-RAG vs concatenated prompt 27.30 / 54.20 / 32.60, Astute RAG 37.10 / 46.80 / 31.80, no-RAG 26.70 / 4.30 / 5.80. Qwen2.5-72B: MADAM 57.70 / 52.70 / 26.40 (concat 38.50 / 41.20 / 20.60). GPT-4o-mini: MADAM 38.50 / 63.00 / 28.00. Under rising misinformation, concatenated and Astute baselines drop ~46% each. Cost: one agent per document plus multi-round debate — [MADAM-RAG](https://arxiv.org/html/2504.13079v2)
- Astute RAG (zero-shot, accuracy): Claude 3.5 Sonnet overall 61.7 (NQ 52.2, TQA 84.1, BioASQ 60.1, PopQA 44.4) vs plain RAG 55.5, no-RAG 54.5, USC 58.7, InstructRAG 58.8; Gemini 1.5 Pro 59.2 vs RAG 53.7. ~70% of retrieved web passages lack the true answer. In worst case (all passages negative) RAG underperforms no-RAG by >50 points; Astute is the only method close to no-RAG (value in figure) — [Astute RAG](https://arxiv.org/html/2410.07176)
- WikiContradict (human eval, 253 instances; fraction answers correctly reflecting the contradiction, explicit / implicit conflicts): no conflict prompt: Llama-3-70B 13.3 / 5.9, GPT-4 3.3 / 11.8; with conflict-aware prompt: Llama-3-70B 60.0 / 17.6, Llama-2-70B 26.7 / 17.6, Mixtral 16.7 / 11.8, GPT-4 10.0 / 11.8. Small n (30 explicit, 18 implicit). LLM judge (Llama-3-70B) F-score 80.4, GPT-4 judge 82.5 vs humans — [WikiContradict](https://arxiv.org/html/2406.13805v1)

### Inferences
- Conflict flagging must be an explicit pipeline stage (classify conflict type -> select behaviour: present both sides / prefer fresher / reject misinformation); one-pass vanilla prompting leaves 25-60 points on the table per the CONFLICTS oracle gap.
- Implicit (reasoning-requiring) conflicts are near floor for all models (<=17.6% in WikiContradict).

### Gaps
- ConflictBank primary numbers not read; no 2026 follow-up with frontier models found.

## 5. Clarification / ask-back

### Takeaway
Evidence is thin and mostly 2024: LLMs are close to chance at recognising ambiguity (CLAMBER best ~54% accuracy) and overconfident; I found no solid 2025-26 measurement of a calibrated "ask vs answer" decision in RAG.

### Cited Findings
- CLAMBER (~12K ambiguous queries, 5 evaluated LLMs): ambiguity identification average accuracy/F1: ChatGPT 54.25/52.77 (best, 57.38/56.91 with zero-shot CoT), Vicuna-13B 52.28/44.99, Llama2-13B 51.30/42.01, Llama2-70B 51.26/39.91. ECE: ChatGPT 29.74 -> 16.30 with CoT, but Llama2-13B 28.48 -> 45.14. Contradiction ambiguity: ChatGPT 38.00 Acc, 81.97% of errors false negatives. Clarifying-question quality: ChatGPT BertScore 31.33, Help 50.45 — [CLAMBER](https://arxiv.org/html/2405.12063)
- ClarQ-LLM: LLM seekers GPT-4o 50.8% and Llama3.1-405B 60.5% success vs 85% humans (secondary summary of paper; not read in full) — [search result](https://www.themoonlight.io/review/clarq-llm-a-benchmark-for-models-clarifying-and-requesting-information-in-task-oriented-dialog)
- AmbigQA: ~56% of NQ-Open queries marked ambiguous (secondary description) — [search result](https://arxiv.org/pdf/2410.13788)
- RAMDocs/AmbigDocs: listing all valid answers for ambiguous queries gives EM 54-63 for best systems (see section 4), i.e. an alternative to asking: answer all interpretations.

### Inferences
- A cheap default is "answer all interpretations with sources" (AmbigDocs-style) rather than a clarify turn; ask-back should be reserved for cases where interpretations would diverge in consequence (inference).

### Gaps
- No 2025-26 numbers for InfoQuest, ClarifyMT-Bench, or Zhang & Choi 2025 (only mentioned in a search snippet). ClariQ not examined.

## 6. Citation-support judging reliability

### Takeaway
Automatic citation judges agree with humans at roughly 78-85% on ALCE, and fine-tuned small judges (~77-84 macro-F1) match or beat zero-shot GPT-4 (73-79) on AttributionBench, yet error is dominated by fine-grained detail insensitivity; correct citations are often post-rationalised rather than faithful.

### Cited Findings
- ALCE [old, 2023]: ChatGPT vanilla top-5 on ASQA citation recall/precision 73.6/72.5 -> 84.8/81.6 with reranking; ~50% of ChatGPT/GPT-4 ELI5 generations not fully supported by citations. TRUE-NLI auto-metrics vs humans: agreement 85.1% (recall, kappa 0.698) and 77.6% (precision, kappa 0.525); cannot detect partial support, which depresses precision — [ALCE](https://arxiv.org/html/2305.14627)
- AttributionBench (macro-F1, average over test sets): GPT-4 CoT zero-shot ID 73.3 / OOD 78.9; T5-XXL-TRUE zero-shot 72.2 / 80.5, fine-tuned 77.2 / 83.4; AttrScore-FLAN-T5-3B zero-shot 68.1 / 74.6, fine-tuned 77.7 / 84.2; fine-tuned GPT-3.5 ~80. Error analysis (GPT-3.5 CoT, 321 errors): 66.0% fine-grained information insensitivity; 26.8% annotator/model information mismatch. No human ceiling reported — [AttributionBench](https://arxiv.org/html/2402.15089)
- "Correctness is not Faithfulness" (Command-R+ 104B 4-bit, NQ, KILT Wikipedia): when the model's answer statement is recovered, it cites an adversarial document 12% of the time for random docs, 57% for relevant-but-uncited docs (273/476) and 55% for docs cited for another reason (290/525) — i.e. up to 57% of citations are post-rationalised. One model, one dataset — [Correctness is not Faithfulness](https://arxiv.org/html/2412.18004)
- Legal citation detection (LePhantomCite, 2026, test n=390; precision/recall/F1): Claude Code with Opus 4.8 76.1/62.8/68.8; GPT-5 agentic 40.8/84.4/55.0; GPT-5 non-agentic 36.9/58.2/45.2; small open models 18.6-40.0 F1. Agentic harness raised GPT-5 F1 +9.8 but precision stays 41% — [Who Checks the Citations?](https://arxiv.org/html/2606.21155)
- LLM judge for conflict-aware correctness (WikiContradict): F 80.4 (Llama-3-70B) / 82.5 (GPT-4) vs humans — [WikiContradict](https://arxiv.org/html/2406.13805v1)

### Inferences
- Budget for ~15-25% judge disagreement on citation precision; use a fine-tuned NLI/attribution judge calibrated per domain, and verify cited text spans (not just pages) to counter fine-grained insensitivity and post-rationalisation.
- A correctness-only eval can overstate faithfulness by a large factor (57% unfaithful citation rate in worst case).

### Gaps
- CiteEval and CiteGuard numbers not retrieved; no human-vs-LLM agreement figure for 2025-26 frontier judges on citation support.

## 7. Calibration sample size for an abstention threshold with a risk guarantee

### Takeaway
To certify error rate <= 5% at 90% confidence with a Clopper-Pearson bound you need 45 examples with zero errors among accepted answers, 77 with one error, 132 with three; at 95% confidence 59 / 93 / 153. The guarantee is on accepted answers only, so the calibration set must contain enough ACCEPTED items, not just enough questions.

### Cited Findings (all calc; method = one-sided Clopper-Pearson / binomial tail, which is the LTT p-value for a fixed threshold)
- Zero observed errors: n = ceil(ln(delta)/ln(1-alpha)). alpha=5%: n=45 (delta .10), 59 (delta .05). alpha=10%: 22 / 29. alpha=2%: 114 / 149. alpha=1%: 230 / 299.
- With k observed errors (alpha 5%, delta 10% / 5%): k=1 -> 77 / 93; k=2 -> 105 / 124; k=3 -> 132 / 153; k=5 -> 184 / 208; k=10 -> 306 / 336.
- If true error is 2% and target 5% at delta 10%: ~105 accepted examples with 2 errors suffice; if true error is 3%: ~209 accepted with 6 errors (calc, rounding-based).
- Sanity: 100 accepted with 0 errors gives CP upper bound 2.28% at delta 10%; 59 with 0 errors gives 4.95% at delta 5%.
- Conformal risk control (expected-risk guarantee) is weaker: with bounded loss <= 1 the finite-sample correction is (n/(n+1)) * empirical risk + 1/(n+1) <= alpha, so zero empirical risk needs n >= 1/alpha - 1 (19 for alpha 5%) (calc from the CRC formula; I did not fetch Angelopoulos et al. here, formula stated from memory of the paper). It controls average risk over calibration draws, not a high-probability bound as LTT/CP does.
- Multiple thresholds: LTT with Bonferroni over m candidate thresholds replaces delta with delta/m, e.g. 10 thresholds at delta 10% needs the 0-error n for delta 1% = ceil(ln(.01)/ln(.95)) = 90 (calc); fixed-sequence testing over a monotone threshold grid avoids this penalty.
- Sufficient-context follow-up: selective accuracy gains were only observable at non-trivial base accuracy; on MuSiQue (Gemma 27B 18.4% acc) a sufficiency signal added nothing, so calibration data must be gathered per domain/model — [Sufficient Context](https://arxiv.org/html/2411.06037)

### Inferences
- Practical target: >=200-300 labelled accepted answers per slice (domain x question type) to certify 5% at 90% with 3-6 errors; far more (>=1,000) for a 1-2% target. Calibration needs human-verified labels, and re-calibration after any retriever, reranker, or generator change (supported by the brittleness evidence in section 1).

### Gaps
- Primary Angelopoulos et al. formulas (LTT, CRC) were not re-read here; the arithmetic is mine. Selective-risk (coverage-conditional) guarantees need an additional bound on the number accepted.

## 8. Legal AI hallucination typology and follow-ups

### Takeaway
The full-text HTML supports outcome shares but does NOT report the incorrect vs misgrounded split per tool in text (only in figures). 2025 independent tests show general LLMs matching legal tools on accuracy; no independent 2026 re-benchmark of newer Lexis/Westlaw products was found.

### Cited Findings
- Magesh et al. (202 queries), accurate / incomplete / hallucinated: Lexis+ AI 65% / 18% / ~17%; Westlaw AI-AR 41% (42% in intro) / 25% / ~33%; Ask Practical Law AI 19% (20% after inter-rater check) / 62% / ~17%. GPT-4: rate not stated in text (legal tools hallucinate less than GPT-4 per paper). Definitions: hallucinated = incorrect OR misgrounded; misgrounded = cited source does not support or is inapplicable; ungrounded (uncited) counted as incomplete; fabricated = cited source does not exist. Query mix: general legal research 80 (39.6%), jurisdiction/time-specific 70 (34.7%), false premise 22 (10.9%), factual recall 30 (14.9%). Hallucination slightly higher on jurisdiction/time-specific; Lexis+ AI rate significantly lower than Westlaw and Practical Law even conditional on responding. Headline range 17%-33% — [Magesh et al.](https://arxiv.org/html/2405.20362) and [abstract](https://arxiv.org/abs/2405.20362)
- Vals Legal AI Report, Oct 2025 (VLAIR Legal Research): accuracy ~80% Alexi, 78% Midpage, ChatGPT 80% (secondary source), lawyer baseline 71%; authoritativeness ChatGPT 70% vs 76% average for legal products. Aggregate weighting 50% accuracy / 40% authoritativeness / 10% appropriateness; Alexi 77% vs lawyer 69% aggregate. Question count 200 vs 210 across sources; vLex withdrew; Lexis+ AI withdrew from the earlier report. Secondary-source figures, vendor-participating — [Vals VLAIR](https://vals.ai/vlair), [LawNext](https://www.lawnext.com/2025/10/vals-ais-latest-benchmark-finds-legal-and-general-ai-now-outperform-lawyers-in-legal-research-accuracy.html), [Alexi report](https://www.vals.ai/application-reports/alexi)
- Large Legal Fictions [old, 2024] hallucination rates, general LLMs on case-law tasks: citation task SCOTUS/USCOA/USDC GPT-3.5 0.641/0.920/0.942; author 0.830/0.967/0.941; quotation ~1.0; doctrinal agreement near chance (0.45-0.50); all models overconfident — [Large Legal Fictions](https://arxiv.org/html/2401.01301)
- LePhantomCite 2026: best legal-citation hallucination detector F1 68.8 (see section 6) — [Who Checks the Citations?](https://arxiv.org/html/2606.21155)
- Secondary/news: 2026 court cases reportedly involved errors in briefs prepared with CoCounsel (US v. Farris, Sixth Circuit, April 2026) — unverified aggregator claim, not primary — [vaquill blog search result](https://www.vaquill.ai/blog/lexis-ai-vs-westlaw-ai-2026)

### Inferences
- The Magesh typology implies two distinct failure channels for an engine: wrong claims (incorrect) and right-looking citations that do not support the claim (misgrounded). Verification therefore needs a claim-to-span entailment check on top of an answer-correctness check, and an explicit "incomplete" (refuse/ungrounded) outcome is counted separately from hallucination.
- Refusal can look like safety: Practical Law AI had equal hallucination to Lexis (17%) but only 19% accuracy because it refused 62%; an eval for the engine must report accuracy, hallucination and abstention jointly.

### Gaps
- Per-tool incorrect vs misgrounded proportions (Figures 4/5 in Magesh et al.; Wiley page returned 403) not obtainable from text. GPT-4 exact hallucination/accuracy not extracted. LegalBench updates and any 2026 evaluation of Protégé/CoCounsel Legal not found.
