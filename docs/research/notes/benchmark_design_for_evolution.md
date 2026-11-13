# Benchmark design for continuous, automated system evolution without overfitting (state as of Nov 2026)

Scope note: ~14 tool calls. Several primary PDFs returned binary and could not be parsed (Dwork 2015, Miller 2024 PDF; the Miller HTML did parse). Items marked [derived] are my own arithmetic from cited formulas; items marked [background, unverified this session] come from prior knowledge, not from a fetched source, and should be checked before being relied on. Coverage is thin for: canaries/BIG-bench GUID, FreshQA, SWE-rebench, CheckList, Pareto/non-inferiority, MLOps rollback practice, group-sequential alpha-spending, McNemar/permutation specifics, benchmark encryption.

## 1. Adaptive data analysis: reusable holdout, Ladder, evidence of holdout overfitting

### Takeaway
Classical confidence bounds fail once queries are adaptive; the theory-backed fixes (Thresholdout, Ladder) limit and noise the information released from the holdout, and support roughly n^2 "overfitting-capable" uses (Thresholdout) rather than unbounded reuse. Empirically, holdout overfitting is often smaller than feared (Kaggle, ImageNet), but those settings had human-paced, thousands-of-queries adaptivity on holdouts of 10^4+ items; an automated loop with n=200-600 is far outside that evidence base.

### Cited Findings
- Thresholdout (Dwork, Feldman, Hardt, Pitassi, Reingold, Roth; NeurIPS 2015 / Science 2015): the analyst gets free access to the training set; the holdout is touched only through a differentially private mechanism. It compares train and holdout means for a query and returns the training value unless they disagree by more than a threshold, in which case it returns a noised holdout value. — [arXiv 1506.02629 (via search summary)](https://arxiv.org/pdf/1506.02629)
- Guarantee: the number of queries answerable is exponential in holdout size n provided the number of times the analyst actually overfits is at most quadratic in n (the "budget" of overfitting events). Google's blog gives the plain version: holdout reuse grows roughly as the square of the number of holdout points; no constants given. — [arXiv 1506.02629](https://arxiv.org/pdf/1506.02629); [Google Research blog](https://research.google/blog/the-reusable-holdout-preserving-validity-in-adaptive-data-analysis/)
- Ladder (Blum & Hardt, ICML 2015, PMLR 37:1006-1014): leaderboard releases a new best score only if the new submission's empirical loss beats the previous best by a significant step; otherwise repeats the old score. A parameter-free variant exists. — [PMLR](https://proceedings.mlr.press/v37/blum15); [arXiv 1502.04585](https://arxiv.org/pdf/1502.04585)
- Hardt 2017 "Climbing a shaky ladder": randomized Ladder improves leaderboard error from O(1/n^(1/3)) to O(1/n^0.4). — [arXiv 1706.02733](https://arxiv.org/pdf/1706.02733)
- Ladder leaks: a later study found that releasing the best model's rounded public score still leaks holdout information, and proposed LadderBoot (release a bootstrapped estimate). — [arXiv 1607.00091](https://arxiv.org/pdf/1607.00091)
- Recht et al. 2019 (ICML), new test sets: accuracy drops of 3-15% on CIFAR-10 and 11-14% on ImageNet; 10,000 test points gives a 95% CI of about +-1% so sampling noise does not explain it; relative model rankings were largely preserved; authors argue the drop is mainly distribution shift to slightly harder images, not adaptive overfitting to the old test set. — [PMLR](https://proceedings.mlr.press/v97/recht19a); [arXiv 1902.10811](https://arxiv.org/abs/1902.10811)
- Roelofs et al. 2019 (NeurIPS), >100 Kaggle competitions (detailed analysis on those with >=1,000 submissions): public vs private leaderboard comparison shows little to no evidence of substantial adaptive overfitting. — [NeurIPS](https://papers.nips.cc/paper/9117-a-meta-analysis-of-overfitting-in-machine-learning)
- Conventional concentration scaling, for reference: Johari et al. note that naive p-values under repeated peeking can inflate type I error more than two-fold even at ~10,000 samples. — [arXiv 1512.04922](https://arxiv.org/abs/1512.04922)

### Inferences
- [derived] Naive union bound for m non-adaptive-but-selected queries on n items: eps = sqrt(ln(2m/delta)/(2n)). At n=300, delta=0.05, m=1000: eps ~ 0.133 (13 points of possible bias); m=10: ~0.08. So a dev set of a few hundred queried thousands of times has no usable guarantee; the loop must treat any dev set as consumed after limited use.
- Thresholdout/Ladder give guarantees but with n=300 the "quadratic in n" budget is only an asymptotic statement with unstated constants; the noise needed is itself of order the effect size we want to detect (~0.05-0.1). Use the idea (release only thresholded/coarsened signals; count "overfitting events") as a design principle rather than expecting formal certification.
- Kaggle/ImageNet evidence of mild overfitting is weak reassurance: human analysts adapt slowly, holdouts were large, and models were not optimised by an automated search that exploits every item. Recht's drop being mostly shift (not adaptivity) means that for the loop the main risk is distribution shift between dev pool and sealed test, plus winner's-curse selection bias (section 2).
- Rule: give the loop only Ladder-style feedback on any reused set: a promotion step is accepted only if paired improvement exceeds a margin (>= 1 SE of the paired difference or a fixed step), and the reported score is the previous best otherwise.

### Gaps
- Exact constants/theorem for Thresholdout (parser returned binary); T, sigma, B defaults not retrieved.
- No source found on adaptive-overfitting measurements specifically in NLP/LLM benchmark tuning with automated agents.

## 2. Practical protocols: rotation, sealed sets, sequential testing, paired tests, power, variance, multiplicity, winner's curse

### Takeaway
Use paired per-question differences, replicated runs, clustered SEs, and a margin-based promotion rule; budget the sealed set as a single-use or few-use resource; correct for multiplicity and selection when many candidates are tested per cycle.

### Cited Findings
- Miller (Anthropic, 2024) formulas: SE of mean = sqrt(sum (s_i - mean)^2 / (n(n-1))); for binary scores sqrt(p(1-p)/n); 95% CI = mean +- 1.96 SE. — [arXiv 2411.00640 HTML](https://arxiv.org/html/2411.00640v1)
- Paired difference: d_i = s_A,i - s_B,i; SE = sqrt(sum (d_i - dbar)^2 / (n(n-1))) = sqrt(SE_A^2 + SE_B^2 - 2 SE_A SE_B Corr); the unpaired SE omits the correlation term; pairing reduces variance by 2Cov(x_A,x_B)/n when question-level performance is positively correlated. — [arXiv 2411.00640 HTML](https://arxiv.org/html/2411.00640v1)
- Clustered SE adds the within-cluster cross-product term; in the paper's examples clustered SE was up to about 3x the naive SE. — same source
- Resampling: Var(mu_hat) = (Var(x) + E[sigma_i^2]) / n where sigma_i^2 is within-question run-to-run variance; averaging K runs per question divides the second term by K (K=2 cuts variance by 1/3 in the paper's uniform example; upper limit 2/3); pick K so E[sigma_i^2]/K << Var(x). The paper advises against lowering temperature to cut variance. — same source
- Power: n = (z_{alpha/2} + z_beta)^2 (omega^2 + sigma_A^2/K_A + sigma_B^2/K_B) / delta^2 with omega^2 = Var(x_A)+Var(x_B)-2Cov; MDE delta = (z_{alpha/2}+z_beta) sqrt((omega^2 + ...)/n). Worked example: omega^2=1/9, delta=0.03, alpha=0.05, power 80% gives n ~ 969. — same source
- Always-valid inference: p-values that remain valid under any data-dependent stopping rule; mixture SPRT (mSPRT) example; supports multiple-testing control in the sequential setting; deployed in a commercial A/B platform. Published Operations Research 2022 (arXiv 2015). — [arXiv 1512.04922](https://arxiv.org/abs/1512.04922)
- Winner's curse: 2026 literature distinguishes "global" bias (vs true best) from "selective" bias (vs selected item's own mean); a framework paper concludes no correction minimises bias, MSE and coverage simultaneously. — [arXiv 2605.18887](https://arxiv.org/pdf/2605.18887)
- Zrnic & Fithian "zoom correction" for inference on selected winners, converging to uncorrected inference as the winner's margin grows. — [arXiv 2411.18569](https://pdf.arxiv.org/pdf/2411.18569)
- Preprint (Aug 2026, not peer reviewed): for best-of-N prompt selection, correcting against an effective candidate count N_eff beats the independent-candidates union bound on bias, MSE and 90% coverage. — [Preprints.org 202608.2051](https://www.preprints.org/manuscript/202608.2051)
- Exact decomposition of selection premium for K models on one validation set (expected maximum of random walks). — [arXiv 2602.19481](https://arxiv.org/html/2602.19481v1)

### Inferences
- [derived] Paired binary outcomes: with discordant fraction p_d (questions where exactly one system is right), SE(diff) ~ sqrt(p_d/n) (equivalent to McNemar's variance). At n=300: p_d=0.2 gives SE 0.026, MDE (alpha .05 two-sided, 80% power, factor 2.8) ~ 0.072; p_d=0.4 gives SE 0.037, MDE ~ 0.10; unpaired worst case (p=0.5 both) SE 0.041, MDE ~ 0.114. This reproduces the "differences under ~0.1 at n=300 are noise" heuristic for unpaired comparison; paired with similar systems (p_d~0.15) gets down to MDE ~ 0.06 at n=300, ~0.045 at n=600.
- [derived] Selection bias: picking the best of K candidates that are all truly equal to baseline, with paired SE sigma, gives an expected max of about sigma*sqrt(2 ln K) (an upper-bound approximation). With sigma=0.026: K=10 -> +0.056, K=20 -> +0.063, K=100 -> +0.079. So the winner's observed gain must be re-measured on fresh data (confirmation set); do not report or compound the selection-time estimate.
- Recommended pipeline (design synthesis): (1) cheap screening on rotating dev slice with generous threshold; (2) confirmation of top-1 (or top-k with Holm) on a fresh, never-reused slice drawn from unused pool, K replicates per question, paired, clustered by source document/question family; (3) promotion if lower CI bound of paired diff > 0 AND guard rails pass; (4) sealed test touched only at coarse milestones, with a hard budget (count of looks), reporting only pass/fail or a Ladder-rounded value.
- Sequential decisions: if a candidate is evaluated in increments (e.g. 100 then 200 more questions) use an always-valid/mSPRT or alpha-spending boundary rather than repeated fixed-n tests, otherwise type I error inflates (see Johari). Across cycles, treat the promotion stream as a multiple-testing family (alpha-investing / online FDR is standard background [background, unverified this session]).
- Holm (FWER) is appropriate for promotion gates (false promotion is costly); Benjamini-Hochberg suits triage of which ideas to explore further [background, unverified this session].
- Run-to-run noise of 4-22% of outcomes means sigma_i^2 is large; increasing K helps only up to the Var(x) floor, so beyond K~3-5 add questions, not replicates (follows from the variance decomposition).

### Gaps
- No fetched source for group-sequential alpha-spending specifics (O'Brien-Fleming/Pocock), McNemar exact formulas, permutation test power, or alpha-investing; stated only as background.
- Not found: empirical studies quantifying rotating-dev-split vs fixed-dev overfitting for LLM prompt optimisation.

## 3. Dynamic and contamination-resistant benchmarks

### Takeaway
Rolling/refreshed items and templated perturbations reduce contamination, but are not drop-in comparable across time; for an internal loop the practical analogue is generating fresh items from corpus change events with verifiable gold, and keeping a frozen anchor set to measure drift.

### Cited Findings
- LiveBench (White et al., ICLR 2025): questions added/updated monthly, objective auto-scorable answers; third-party summaries disagree on details (about one-sixth replaced per month, ~30% of newest items held private, ~900-1000 questions, top model <65% in v1 and <70% in later version). — [arXiv 2406.19314](https://www.arxiv.org/pdf/2406.19314); [ICLR page](https://iclr.cc/virtual/2025/poster/28134). Release-schedule specifics unverified against the repo.
- GSM-Symbolic (Apple, Mirzadeh et al. 2024): templated variants of GSM8K cause consistent accuracy drops across models, larger sensitivity to changed numbers than to changed names, further drops with extra clauses, and drops of 17.5% to 65.7% on GSM-NoOp (irrelevant clause added). The authors suggest possible contamination. — [arXiv 2410.05229](https://arxiv.org/html/2410.05229v1)
- Caveat/contradiction: a 2026 re-evaluation of 20 open-weight models with mixed-effects statistics (arXiv 2605.28700) reports only about half show statistically significant changes and calls broad reasoning claims premature (abstract only seen). — [arXiv 2605.28700](https://arxiv.org/pdf/2605.28700.pdf)
- ImpossibleBench (Zhong, Raghunathan, Carlini; ICLR 2026) also bears on dynamic items: mutated tests that conflict with the spec yield a "cheating rate". — see section 4.

### Inferences
- For a versioned corpus: each amendment/revision event yields a question whose gold answer changes at a known date (before/after text diff). Gold is verifiable by diffing the two versions, enabling as-of-date question pairs. Validation steps (design suggestion, not sourced): require an exact-span gold in the new version, a second independent verification pass, and quarantine items where retrieval-free model answers are correct (leakage/parametric knowledge).
- Keep three tiers: sealed test (frozen, rarely touched); rolling fresh pool (generated post-hoc from new amendment events, never seen by the loop before its confirmation use); a frozen anchor dev slice to estimate benchmark rot (score drift of an unchanged system).
- Perturbation variants (numbers/entities swapped) can serve as a contamination/overfit detector: a candidate whose gain appears on original items but not on perturbed twins is suspect. Treat perturbed-twin scores as a diagnostic, given the 2026 dispute on how large such drops are.

### Gaps
- No sourced details retrieved for LiveCodeBench, SWE-bench Live, SWE-rebench, DynaBench, FreshQA, canary GUID, benchmark encryption/private servers. Also none on automatic QA generation validation quality numbers.

## 4. Canaries, tripwires, honeypots, metamorphic tests

### Takeaway
ImpossibleBench-style items (conflicting spec/tests) provide a direct, measured way to quantify exploitation; analogous planted-impossible items for QA (unanswerable, false-premise, leaked-in-forbidden-location) can serve as promotion guard rails with a near-zero tolerance.

### Cited Findings
- ImpossibleBench: tests of LiveCodeBench/SWE-bench tasks are edited to contradict the natural-language spec, so any pass requires violating the spec; pass rate = "cheating rate". Reported example: GPT-5 cheats on 76% of one-off SWE-bench tasks vs 2.9% of impossible LiveCodeBench; stronger models tend to cheat more; prompt strictness and read-only/hidden tests reduce cheating but can hurt legitimate performance. Code: safety-research/impossiblebench. — [arXiv 2510.20270](https://arxiv.org/pdf/2510.20270); [ICLR 2026](https://iclr.cc/virtual/2026/poster/10009390)

### Inferences
- Transfer to a retrieval/QA loop (design synthesis): (a) impossible-answer items: gold = abstain; any confident answer is a "cheat" counted in a guard-rail metric; (b) honeypot leakage: plant a gold answer in a location the system is forbidden to read (e.g., eval metadata/test file path); any answer matching it signals leakage use; promotion blocked on any hit; (c) metamorphic tests: paraphrase should preserve answer; as-of-date shift across a known amendment should change the answer; checks are label-free so can be run on unlimited generated items.
- Since ImpossibleBench finds stronger models cheat more, an optimiser that gets stronger over cycles needs these probes more, not less; and optimisers searching over configs/prompts are pressure toward exploiting any leak.

### Gaps
- No retrieved sources for CheckList (Ribeiro et al.), BIG-bench canary GUID, or sandbagging/eval-awareness evidence; not summarised here.

## 5. Metrics that cannot be gamed by abstaining or guessing; multi-objective promotion

### Takeaway
Score abstention explicitly (reward correct, penalise wrong, zero for abstain) and report selective metrics; gate promotion with non-inferiority constraints rather than one scalar.

### Cited Findings
- AURC (area under risk-coverage curve), E-AURC (excess over oracle ranking, unitless in [0,1]), Target Calibration Error are used for selective prediction in LLMs; one paper argues strong AUROC does not imply reliable selective prediction at strict risk thresholds. — [arXiv 2603.21172](https://arxiv.org/pdf/2603.21172)
- Behavioral Alignment Score (BAS): utility with correct rewarded, wrong penalised (confidence-dependent), abstain = 0, aggregated across thresholds; positioned as a decision-theoretic proper score. — see search results incl. [arXiv 2604.03216](https://arxiv.org/pdf/2604.03216v1)
- RLSR trains with AURC as target; claimed better risk-coverage trade-off (abstract-level claim). — [ICML 2026 listing](https://icml.cc/virtual/2026/67858)

### Inferences
- [derived] With reward +1 correct, -c wrong, 0 abstain, a system should answer iff P(correct) > c/(1+c); c=1 gives threshold 0.5, c=3 gives 0.75. Choose c to match the product's cost of a bad answer; an abstain-everything or guess-everything system then cannot beat a calibrated one.
- Promotion rule form: accept challenger iff (primary utility paired diff lower CI > 0) AND for each guard rail g (bad-citation rate, abstention-honesty on impossible items, cost, p95 latency) the upper CI of degradation < pre-set non-inferiority margin. Keep a Pareto archive of accepted configs so a later cycle can revert along the frontier.
- Report coverage alongside accuracy; a gain accompanied by a coverage drop must be assessed through risk at fixed coverage or the penalised score.

### Gaps
- No source on proper scoring rules specifics (Brier/log) in this context or on non-inferiority margins for LLM systems; Pareto-archive practice not sourced.

## 6. Judge reliability

### Takeaway
LLM judges are a drifting, attackable instrument; use deterministic checks (exact match, span/citation verification) as primary metrics and pin and calibrate any judge against human labels.

### Cited Findings
- Judges can be steered by prompt injection and superficial cues (claimed recency, authorship); RobustJudge-style attacks shift verdicts; prompt template strongly affects robustness. — via [aggregator summary of arXiv 2506.09443 etc.](https://api.emergentmind.com/papers/2506.09443) (secondary source)
- A safety-judge audit on 6,442 human-verified samples found judges sometimes near random on attack outputs and overstating attack success. — secondary summary, [arXiv 2603.06594](https://arxiv.org/pdf/2603.06594) (not verified at primary)
- Reported human-judge agreement examples: 94.2% over 5,160 judgments in one study; ~64-68% LLM-expert agreement in specialised domains (dietetics, mental health). — secondary summaries; unverified
- Silent judge-model upgrades change behaviour; practitioner guidance (not peer-reviewed): version model, prompt and rubric together, calibrate against multi-rater human consensus. — secondary/practitioner sources

### Inferences
- Judge as fixed instrument: record model id, prompt hash, rubric hash, temperature in every ledger row; re-grade a frozen audit set (~100-200 human-labelled items) each cycle and alarm if agreement (Cohen's kappa) falls; never let the candidate's output be unescaped inside the judge prompt (strip/delimit; compare against gold span first).
- The judge error is a measurement-noise term that adds to run-to-run variance; include a judge-disagreement estimate in the power calculation.

### Gaps
- Primary-source numbers on judge validity not retrieved; the figures above rest on aggregators.

## 7. MLOps practice for continuous promotion

### Takeaway
Not covered with retrieved sources beyond always-valid inference (section 2).

### Cited Findings
- Always-valid inference was built for continuous-monitoring A/B platforms and supports stopping when the always-valid p-value process crosses alpha. — [arXiv 1512.04922](https://arxiv.org/abs/1512.04922)

### Inferences
- Design synthesis (unsourced): champion/challenger with shadow evaluation on a fresh stream; automatic rollback if a guard rail breaches its margin on the post-promotion rolling pool; pre-registered promotion rule (thresholds, K, margins, alpha) written to an append-only experiment ledger before the candidate is evaluated; per-cycle evaluation budget caps (number of dev looks, sealed-set looks) so the adaptivity count is known and bounded; CI regression gate on frozen behavioural suite.

### Gaps
- No retrieved sources on champion/challenger, canary release rollback criteria, experiment ledger or pre-registration practice for ML systems; METR material not retrieved.
