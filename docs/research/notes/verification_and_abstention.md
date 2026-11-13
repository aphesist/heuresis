# Answer verification and calibrated selective answering (abstention) for RAG QA, as of Nov 2026

Scope note: research was capped at ~15 tool calls. Several key questions (Granite Guardian/Lynx/HHEM, CoVe, ALCE/AttributionBench/CiteEval reliability, ConflictBank, typed abstention numbers, Quach et al., 2026 legal follow-ups beyond commentary) were NOT researched in depth; they are listed under Gaps rather than filled from memory. Items marked [secondary] come from search-engine summaries or blogs rather than the primary paper.

## 1. Verification that catches "faithful to the passage but does not answer the question"

### Takeaway
Google's Sufficient Context work is the closest primary evidence: it separates "does the context contain a definitive answer to THIS question" from "is the answer entailed by the context", and shows that adding a question-conditioned sufficiency signal to self-rated confidence improves selective accuracy by roughly 2-10 points. Sufficiency alone is not enough, because models are right 35-62% of the time with insufficient context. Consistency-based signals (semantic entropy, conformal self-consistency) are the other main family and need no logprobs.

### Cited Findings
- Sufficient Context (Joren et al., ICLR 2025) defines context as sufficient if it supports a definitive answer to the query, insufficient if incomplete, inconclusive or contradictory. The label needs no ground-truth answer. — [arXiv 2411.06037](https://arxiv.org/abs/2411.06037), [ICLR page](https://proceedings.iclr.cc/paper_files/paper/2025/hash/33dffa2e3d2ab74a783d1a8c292f66d9-Abstract-Conference.html)
- Their sufficient-context autorater reaches 93% accuracy; Gemini 1.5 Pro (1-shot) is best on F1/accuracy; FLAMe (smaller) and TRUE-NLI trail (TRUE-NLI has high precision, low recall because it measures entailment, which implies sufficiency but is stricter). — [arXiv PDF 2411.06037](https://arxiv.org/pdf/2411.06037.pdf) (text read via local pdftotext)
- Standard RAG datasets contain many insufficient instances (55.4% in the mix they highlight in Fig. 1). Frontier models (Gemini 1.5 Pro, GPT-4o, Claude 3.5) answer well when context is sufficient but hallucinate rather than abstain when it is not, especially on multi-hop; models still answer correctly 35-62% of the time with insufficient context (often from parametric knowledge or ambiguity), so sufficiency should not be the sole gate. — same PDF
- Selective generation: logistic-regression intervention model combining self-rated confidence plus sufficient-context label gives better accuracy-vs-coverage than confidence alone: >10 points for Gemma 27B on HotpotQA at high-accuracy regions, >5 points for Gemini 1.5 Pro near 70% coverage on HotpotQA; gains small on low-accuracy sets (Gemma 27B on MuSiQue, base accuracy 18.4%). Abstract summary: +2-10% correct among answered. — same PDF; [arXiv abstract](https://arxiv.org/abs/2411.06037)
- Fine-tuning open models on sufficiency labels did not easily cut hallucination; for Mistral 3 it raised abstention at the cost of fewer correct answers. — same PDF
- Google blog summary and code/prompts are public (GitHub linked from paper). — [Google Research blog](https://www.research.google/blog/deeper-insights-into-retrieval-augmented-generation-the-role-of-sufficient-context/)
- Semantic entropy (Farquhar et al., Nature 2024): sample ~10 answers, cluster by bidirectional entailment, compute entropy over meaning clusters. Reported average AUROC about 0.790 over 30 task-model combos vs 0.691 naive entropy, 0.698 P(True), 0.687 embedding regression [secondary, unverified]. — [aggregator summary](https://neura.market/ai-and-ml-research-papers/detecting-hallucinations-in-large-language-models-using-semantic-entropy)
- Semantic Entropy Probes (Kossen et al. 2024): linear probes on hidden states predict semantic entropy from a single generation; generalize better OOD but do not beat sampled SE in-distribution [secondary]; needs white-box hidden states, so not usable with API Claude. — [review](https://liner.com/review/semantic-entropy-probes-robust-and-cheap-hallucination-detection-in-llms)
- Follow-up work argues SE degrades on longer, one-sentence-plus responses [secondary]. — same search results
- Conformal abstention (Yadkori et al. 2024) uses LLM self-evaluation of whether its own sampled answers match (consistency without logprobs), calibrates the threshold with conformal risk control, and beats logprob baselines on TriviaQA and Temporal Sequences with Gemini Pro. — [arXiv 2405.01563](https://arxiv.org/abs/2405.01563)

### Inferences
- The observed AUROC ~0.5 of a passage-vs-answer NLI verifier is expected: it tests entailment(passage, answer), while the failure is relevance/sufficiency(question, passage). The fix is a question-conditioned judge (is the passage sufficient to answer Q, and does answer A actually answer Q) plus a consistency signal, not a better NLI model.
- Sufficiency is a useful feature, not a gate: 35-62% correct-with-insufficient-context means a hard gate loses coverage. Combine it (logistic regression) with confidence/consistency features, as the paper did.
- Multi-draft agreement (sample k answers with different retrieval/query rewrites, judge equivalence) is the API-feasible analogue of SE and also addresses over-abstention from single-draft-then-verify, by turning one hard verify decision into a graded agreement score to threshold. This is inference; no measured multi-hop number found.

### Gaps
- Not researched: chain-of-verification (CoVe) numbers, answer-to-question back-translation, debate for verification, independent-retrieval cross-checking, autorater robustness to same-family bias. No measured AUROC found for "answer-addresses-question" checks specifically.
- Primary Nature paper numbers not read directly.

## 2. Claim-level grounding verifiers and attribution judges

### Takeaway
Small specialized verifiers (MiniCheck 0.8B-7B) match or approach frontier LLM judges at a tiny fraction of cost on LLM-AggreFact, but all of these measure support of a claim by a document, which is exactly the signal that failed for you. Leaderboard top is now commercial/closed entries at ~79%.

### Cited Findings
- MiniCheck (EMNLP 2024), LLM-AggreFact average balanced accuracy: MiniCheck-FT5 (770M) 74.7, MiniCheck-RoBERTa 72.7, MiniCheck-DeBERTa 72.6, AlignScore 70.4, GPT-4 75.3, Claude-3 Opus 74.1. Cost on 13K test examples about $0.24 vs about $107 for GPT-4 (>400x). — [arXiv 2404.10774](https://arxiv.org/html/2404.10774v2)
- Claim decomposition did not reliably help in MiniCheck: FT5 -1.4 points with decomposition, GPT-4 +0.3; decomposition raises inference cost 2-4x; authors recommend against unless clearly better. — same
- LLM-AggreFact leaderboard (fetched 2026-11-13, no date shown on page, "Average" column): nimble-v4-max 79.5, Clef 79.0, Decider v1.2 78.7, Jev 1.13.0 78.7, d1-ultra 78.5, nimble-v4 77.8, Bespoke-MiniCheck-7B 77.4, MiniCheck-Flan-T5-L 75.0 (0.8B). Top entries are not identifiable as open models; I could not confirm the metric label or release dates. — [LLM-AggreFact](https://llm-aggrefact.github.io/)
- "Verify with Caution" argues similar balanced accuracy on LLM-AggreFact can hide large per-example disagreement, and that Bespoke-7B and gpt-4-turbo topped the board at its time. — [arXiv 2501.14883](https://arxiv.org/html/2501.14883v2)
- Decomposition: results depend heavily on the decomposer; decomposition can strip context (pronouns) and inflate scores via repeated context (DnDScore); a 2026 trained 8B decomposer reports 71.75 macro-F1 downstream [secondary]. — [DnDScore](https://huggingface.co/papers/2412.13175.md), [search results listing](https://aclanthology.org/2026.acl-long.1468.pdf)

### Inferences
- Because decomposition did not help on MiniCheck and costs 2-4x, prefer whole-answer or sentence-level checks, but decompose numbers/entities deterministically (your existing number tracing), where decomposition is lossless.
- A grounding verifier is necessary but not sufficient; use it as one feature alongside sufficiency and consistency.

### Gaps
- Not researched: AlignScore details, HHEM, Granite Guardian, Lynx, long-context verifiers, FActScore/VeriScore/SAFE numbers, ALCE/AttributionBench/CiteEval and human-agreement of citation-support judges.

## 3. Correlated errors and heterogeneous ensembles

### Takeaway
Judges favor their own outputs and make errors correlated with the generator and with each other; adding same-type judges buys little. Diversity must be in signal type, not just count.

### Cited Findings
- Frontier LLMs show self-recognition and self-preference; fine-tuning shows a causal link (Panickssery et al., NeurIPS 2024; summarization with GPT-4, GPT-3.5, Claude 2, Llama-2-7b; effect not uniform across labels). — [arXiv 2404.13076](https://arxiv.org/html/2404.13076v1)
- "Great Models Think Alike" (Goel et al., Feb 2025): errors become more similar as capability grows; judges favor functionally similar models, r=0.84 between judge score and model similarity [secondary]. — [review](https://liner.com/review/great-models-think-alike-and-this-undermines-ai-oversight)
- "Nine Judges, Two Effective Votes" (Kohli, May 2026, single preprint): Kish effective sample size loses roughly three-quarters of nominal independence; same-family pairs only marginally more correlated than cross-family; more judges or other aggregation helps little. — [review](https://www.themoonlight.io/en/review/nine-judges-two-effective-votes-correlated-errors-undermine-llm-evaluation-panels)

### Inferences
- Do not use the generator family as sole judge; mix a deterministic rule layer, a trained small verifier, and an LLM judge from a different family, and measure effective independence (error correlation on a labeled set) rather than assuming it.

### Gaps
- No direct evidence found for NLI+LLM+rules ensembles in RAG verification; the case is inferential.

## 4. Calibrated abstention: conformal and selective prediction

### Takeaway
Conformal/risk-control methods give a distribution-free bound on average hallucination rate given exchangeable calibration data; they do not give per-question or per-subgroup guarantees and break under shift. For API models, consistency-based scores outperform verbalized confidence.

### Cited Findings
- Mohri and Hashimoto (ICML 2024): guarantees restricted to a fixed distribution, marginal over calibration and test draws, not conditional on input; lost under drastic input shift; achieves coverage by aggressive claim filtering (low retention). — [arXiv 2402.10978](https://arxiv.org/pdf/2402.10978), [follow-up critique](https://arxiv.org/html/2602.01285v1)
- Coherent factuality (Rubin-Toles et al., ICLR 2025) addresses claim-order dependence. — [paper](https://www.alphaxiv.org/abs/2505.17126.md)
- Yadkori et al. bound hallucination rate via conformal risk control over self-consistency; Gemini Pro; only v1 (2024) found. — [arXiv 2405.01563](https://arxiv.org/abs/2405.01563)
- Xiong et al. (ICLR 2024): verbalized confidence is overconfident; consistency-based methods usually beat verbalized; hybrids best; GPT-4 verbalized AUROC about 62.7% [secondary, unverified]; black-box vs white-box gap narrow (0.522 to 0.605 AUROC). — [arXiv 2306.13063](https://arxiv.org/abs/2306.13063)

### Inferences
- Practical protocol: calibrate a threshold on a hold-out of labeled (question, answer, correct?) from the target distribution (legal versions/regimes as strata); report marginal risk with a confidence bound and monitor per-stratum risk. Distribution shift (new statute versions) invalidates it; recalibrate on rolling windows.
- Sample size: I found no sourced number. Standard split-conformal risk control gives an error-bound slack of order 1/sqrt(n); to certify e.g. 5% risk at +-2 points needs on the order of several hundred labeled answers per stratum (my own arithmetic, not sourced).

### Gaps
- Not researched: Quach et al. conformal language modeling, learn-then-test, risk-coverage curves for Claude-class models, empirical sample-size studies, 2026 conformal RAG work.

## 5. Why models guess; benchmarks that score abstention

### Takeaway
Guessing is incentivized by accuracy-only grading; reasoning fine-tuning makes abstention worse, so a system must enforce abstention externally rather than rely on the model.

### Cited Findings
- Kalai, Nachum, Vempala, Zhang (OpenAI, Sept 2025): hallucination follows from training/eval incentives; accuracy-only scoring makes blank = wrong so guessing wins; propose penalizing confident errors more than abstentions with partial credit for hedging, and changing primary leaderboards; arbitrary low-frequency facts cannot be predicted from patterns. OpenAI SimpleQA example: gpt-5-thinking-mini abstained 52% vs o4-mini 1%, with o4-mini slightly higher accuracy but much higher error rate. — [OpenAI post](https://openai.com/index/why-language-models-hallucinate/) (paper full text not read)
- AbstentionBench (Kirichenko et al., NeurIPS 2025): 20 datasets, ~20 LLMs; reasoning fine-tuning lowers abstention recall about 24% on average vs instruct counterparts (DeepSeek R1 Distill, s1.1), even in math/science; longer reasoning budgets raise accuracy but lower abstention; system-prompt help is partial. — [arXiv 2506.09038](https://arxiv.org/pdf/2506.09038)

### Inferences
- Use an explicit utility (reward correct, penalize wrong by cost ratio c, abstain 0), which implies a confidence threshold of c/(1+c); set the threshold from that, then check with a risk-coverage curve.

### Gaps
- Did not read the Kalai et al. paper or check current Claude/GPT-5-class abstention behavior on AbstentionBench.

## 6. Typed abstention: conflicts, false premises, ambiguity

### Takeaway
Conflicting-evidence handling is hard and abstention-by-debate gives modest gains; I have little measured data on false-premise and clarification.

### Cited Findings
- RAMDocs and MADAM-RAG (Wang et al. 2025): Llama3.3-70B gets 32.6 EM on RAMDocs; MADAM-RAG (per-document agents plus aggregator debate) 34.4 for Llama, GPT-4o-mini peaks at 28.0; +11.4 (Llama3.3-70B) and +12.9 (Qwen2.5-72B) over Astute RAG on AmbigDocs and RAMDocs; gains shrink when misinformation outweighs support. Table values in snippets partly garbled. — [arXiv 2504.13079](https://arxiv.org/pdf/2504.13079)
- Sufficient Context treats contradictory context as insufficient, and ambiguity (two same-name entities) as a main cause of mislabeled insufficiency. — [arXiv PDF 2411.06037](https://arxiv.org/pdf/2411.06037.pdf)

### Inferences
- Version-in-force checks (your deterministic layer) are a legal-domain conflict detector; route "two valid versions or authorities disagree" to a typed abstain-with-explanation rather than a generic refusal.

### Gaps
- Not researched: ConflictBank, false-premise detection rates, clarification/ask-back results.

## 7. Legal-domain evidence

### Takeaway
Even RAG legal tools from major vendors produced wrong or misgrounded answers at 17-33% in the 2024 Stanford/Yale study, and court-sanction cases keep growing fast; much of the risk is citation-correct but proposition-wrong output, matching your failure mode.

### Cited Findings
- Magesh et al. (J. Empirical Legal Studies 2025; preprint 2024): Lexis+ AI and Westlaw AI-Assisted Research each hallucinate 17-33%, less than GPT-4; Lexis+ AI most accurate (65% correct); Westlaw AI-AR 42% accurate, hallucinating nearly twice as often as the other tools; Ask Practical Law AI incomplete (refusal/ungrounded) on >60% of queries. Vendors disputed methodology and cited later improvements; tested product versions are old. — [arXiv 2405.20362](https://arxiv.org/abs/2405.20362), [JELS PDF (via search summary)](https://nlp.stanford.edu/~manning/papers/Magesh-Hallucination%E2%80%90Free-2025.pdf), [LLRX 2026 commentary](https://www.llrx.com/2026/04/hallucinations-by-west-lexis-ai/)
- Vals Legal AI report (Oct 2025) [secondary]: legal tools 78-81% vs ChatGPT 80%; ~14-point drop on multi-jurisdiction surveys. — [LLRX](https://www.llrx.com/2026/02/what-the-science-says-about-hallucinations-in-legal-research/)
- U.S. v. Farris (6th Cir., Apr 2026): errors found in a brief prepared with Westlaw CoCounsel [secondary]. — [LLRX](https://www.llrx.com/2026/04/hallucinations-by-west-lexis-ai/)
- June 2026 preprint "Who Checks the Citations?": 1,300 brief excerpts with injected errors for legal hallucination detection (not read). — [papers.cool 2606.21155](https://papers.cool/arxiv/2606.21155)
- Charlotin AI Hallucination Cases database: 1,227 (early/April 2026), 1,598 (9 Jun 2026), 1,624 (18 Jun 2026), 1,981 (29 Aug 2026; 1,363 US); roughly 8 new cases/day in June; pro se about 1,136 vs lawyers about 793 in one tally. Figures from third-party trackers, not the database page itself, and they disagree slightly. — [UNC Law Library](https://library.law.unc.edu/2026/06/handling-hallucinations-a-reflection/), [HAQQ](https://haqq.ai/blog/ai-legal-hallucination-audit.html), [guide citing 1,981](https://blog.platinumids.com/blog/ai-hallucination-crisis-courts-2026)

### Inferences
- The Stanford "misgrounded" category (real citation, does not support the claim) is exactly what deterministic existence checks cannot catch; it requires proposition-level support checking.

### Gaps
- Could not retrieve the JELS PDF (HTTP 503); per-tool numbers beyond those above, dataset size and the hallucination typology definition are unverified. No 2026 independent re-run of the Stanford benchmark found.
