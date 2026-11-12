# The legal citation-integrity test (`brlaw`)

*Law is the example domain here. The engine, the gate and the metric below are generic; only the
Brazilian-law pieces (`domains/legal_br.py`, `bench/brlaw.py`, `bench/brlaw_versioned.py`) know about law.*

## What it measures, and why

Lawyers have been sanctioned after AI tools invented laws, citations and wording. The benchmarks run so
far (Wikipedia and news QA) graded only whether an answer string appears: nothing measured whether a
**citation exists**, **was in force on the date the question is about**, or **supports the claim**.
This test measures exactly that, for every system, from the answer text alone:

| # | Measure | Meaning |
|---|---|---|
| 1 | references per answer | citations found by the domain's resolver (free text) plus, for systems that cite by mark, the cited units |
| 2 | existence | share of references whose **norm** exists in the corpus and whose **article** exists in it; `norm not found` and `article not found` are reported separately, plus `norm only` (no article named) |
| 3 | in force | share of resolved references whose provision had a version in force at the question's date |
| 4 | support | whether the provision's text in force at the date supports the sentence: a model judge (paid, phase B) and a stratified CSV for human checking |
| 5 | **tainted answers** | answers with at least one fabricated (norm or article not found) or not-in-force reference: **the headline** |
| 6 | no reference | answers that cite nothing |

**Reading "norm not found".** It can mean a fabricated norm **or** a real norm that is outside this corpus.
The metric reports the headline both ways: `tainted` counts every `norm not found`; `tainted (covered only)`
counts it only for norm types the corpus covers almost completely (`LegalBRDomain.covers`: federal leis,
leis complementares, decretos-lei and emendas constitucionais dated 1946-2025). Coverage of those types is
**not 100 %**: a comparison with the Senate's own lists for sampled years found 95-100 % of the leis ordinárias and decretos-lei (and 4 of 5, 2 of 3 and 4 of 5 of the leis complementares of three sampled years) in the
corpus (see `results/brlaw/NOTES.md`), so even the restricted number is "probably does not exist", not
"certainly". The corpus does not claim to cover decretos, instruções normativas, portarias or any state or
municipal law: a missing one of those is only counted in the unrestricted headline.

**Stub texts.** Some scraped texts of BR-TaxQA-R hold only a preamble (the Código Civil file is 367 characters
long). A norm of an articulated type whose text yields no article is flagged `articles_missing`; when the federal
tier holds the same norm, that copy is used instead, otherwise an "article not found" inside it is reported as
`unit_not_found_in_incomplete_container` and is not counted as fabrication in the restricted headline.

The same code, `src/heuresis/bench/citations.py`, runs over every system's answer. It knows nothing about
law: it asks the domain's optional `resolve_references` and the store.

## The corpus: three tiers

Built into the `jsonl` exchange format under `data/` (git-ignored; nothing here is committed or
redistributed). Unit ids are LexML-style, `urn:lex:br:<authority>:<type>:<date>;<number>!art<n>`
(`!art15-A`, `!artunico`, `!adct1` for the transitional provisions of the Constitution; a very long article
continues in `!p2`...). Every unit text is a slice of a downloaded source; every date comes from a source.
**No provision was written, paraphrased or reconstructed.**

| Tier | Source | What it is |
|---|---|---|
| `tax` | `unicamp-dl/BR-TaxQA-R` (Hugging Face, CC BY 4.0, revision `9f0f4263928c6152a40f888da3e63375a24bb0f3`) | the legal texts shipped with the dataset, split into articles (documents without articles, such as *soluções de consulta*, are one `!doc` unit) |
| `federal` | `github.com/ctresb/leis` at commit `c9f21b4ab11aa0d7ca6fe861d75028e94219c2d6` (scripts MIT; the texts are official acts, referenced by commit and URN, not redistributed) | the large tier: federal *leis ordinárias, leis complementares, decretos-lei, leis delegadas, emendas constitucionais* and the Constitution |
| `versioned` | Câmara dos Deputados legislation portal (`www2.camara.leg.br/legin/`), downloaded 2026-11-12 | provisions with two real, dated wordings |

Counts are in `results/brlaw/NOTES.md` (they come from the build, not from this page). Norms present in both
the tax and the federal tier are kept once, as the tax copy (the version the dataset's references were
written against); a versioned provision replaces the same unit id of the other tiers.

### What is and is not versioned

* **`federal` and `tax` units have one version each**: the text as the source holds it, created on the norm's
  date. `ctresb/leis` keeps, for the norms that are in force, the *compiled* text with its annotations
  ("Redação dada pela...", "Revogado pela...") but **not the earlier wording**; for most norms (about
  two thirds) it holds the text as originally published, with **no later amendment or repeal**. So for those the
  store cannot know a provision was amended or repealed. "In force" is therefore only as good as the source
  allows (see Limits).
* **Repeal marks.** An article whose compiled text is only a "(Revogado ...)" annotation is a repealed
  article. If the annotation gives one unambiguous date (or one introduced by "em vigor a partir de" /
  "produzindo efeitos a partir de") the unit gets a `repeal` event on that date, certainty `high`; if it names
  several unrelated dates (a provisional measure and its conversion law) or none, the article stays in force
  and is counted as "repeal date unknown". The text kept for such an article is the annotation itself
  (certainty `low`): the earlier wording is not in the source. A norm flagged `revogada: true` in the source
  header has no date and gets no event; the flag is kept in the source's metadata.
* **`versioned`** (60 provisions, 54 of the CLT and 6 of Lei nº 7.713/1988, chosen by a deterministic
  round-robin over the amending acts from 234 candidates found on four base norms; the two tax laws of 1995 yield
  none, every provision of theirs being touched by several acts or by deferred effects): both the **original publication** and the **compiled text** of the
  base norm are downloaded from the Câmara portal; the compiled text's annotations name the amending act, and
  the base norm's "Vide Norma(s)" log (the Câmara's per-provision alteration log) links the act's page, which
  gives its publication date and its own "entra em vigor" clause. A provision enters only if: its annotations
  name exactly one act, none defers effects, converts a provisional measure or is a veto; the same article exists
  in the original publication with different words; the act's own clause settles the date (publication date,
  or a date it names: a period such as "cento e vinte dias" is **not** computed, the provision is left out).
  Events: `create` (original wording, from the base norm's entry into force) then `replace` or `repeal` (from the
  act's entry into force) with the literal annotation and the page URLs as evidence. The amending act's text is
  used for its date and clause; it is **not** diffed against the compiled wording, so the later wording is the
  portal's compiled text.

## The resolver (`legal_br`, optional `Domain.resolve_references`)

`extract_references(text)` (kept) pulls norm and article mentions from a question. The new
`resolve_references(text, store) -> list[Reference]` reads citations as lawyers write them ("art. 8º, II, da
Lei nº 9.250/1995", "Lei 9.250, de 1995, art. 8", "CTN, art. 43", "Constituição, art. 153, III", "Decreto nº
9.580/2018 (RIR/2018), art. 677", "IN RFB nº 2.178/2024, art. 2º") and returns, per reference, `resolved` (with
the unit id), `unit_not_found` (norm found, article not found), `container_not_found` (norm not found; with
what the text said: kind, number, year) or `norm_only`. Abbreviations (CF, CTN, CLT, CC, CPC, RIR/2018,
ECA...) come from a table the corpus builds from its **own** titles: file names and reference titles of the
dataset (`Name (ACR)`, `Name - ACR/2018`) and the initials of capitalised names ("Código de Processo Civil" ->
CPC); nothing from memory. A wrong year is "norm not found" (a fabricated citation); an alias shared by two
norms is tried on the newest, non-revoked one first. The core only knows the optional protocol
(`interfaces.Reference`, `ReferenceResolver`, `domain_references`): a domain without the method is unaffected.

**Ceiling.** Rendering every article-level gold reference of BR-TaxQA-R the way a lawyer would write it,
the resolver returns the gold unit for 1,815 of the 1,829 gold references whose unit exists in the corpus
(99.2 %); the 14 misses are mostly errors in the dataset's own titles (a wrong year: "Lei nº 9.250/2005"). 183 of the
2,012 gold article references name a unit the corpus does not hold (the norm was not parseable from the scraped
text, or an article was not split out).

## The gate: `references_traced` (engine, generic)

Every reference the domain's resolver finds in an answer sentence must resolve to a unit the **sentence cites
by mark** (a unit the model was shown and cited). A sentence that names a provision it does not cite, or one
that does not exist, fails and is dropped like the other deterministic failures. It is on when the domain has a
resolver and off otherwise (`Engine(references_traced=False)` switches it off for an ablation). Implementation
note: it sets `checks["references_traced"] = False` and also `checks["exists"] = False`, so the locked decision
rule drops the sentence without any change to `locked/`; the note says which reference failed. One related
change: for a domain with a resolver the verifier reads each passage with its title (norm and article)
prepended, because "art. 8º da Lei nº 9.250/1995" carries numbers that are in the label the drafter was shown
and not in the provision's words; without it the locked `numbers_traced` check would drop correct legal
sentences. Domains without a resolver are unchanged.

## The systems and the questions

All systems answer in Portuguese in at most three short sentences, citing "norma, número/ano e artigo" for each
statement, or `ABSTAIN`; passages are shown with their provision label (norm and article). The Portuguese
prompts live next to the English ones in `bench/systems.py` and are chosen by the dataset attribute
`meta["prompt_set"] == "legal_br"` (through a wrapper of the generator), so the Wikipedia-QA constants and
their hash are untouched (a test pins both hashes). Systems: `closed_book` (the failure behind the sanctioned
lawyers), `hybrid` (retrieval as of today), `agentic`, `agentic+asof`, `engine` (search mode, grade decision,
`references_traced` on).

* **BR-TaxQA-R questions**: 715 questions with the official answers and article-level gold references resolved
  to unit ids (546 questions name an article; 528 of them resolve to a unit of the corpus). Split by
  `sha256(seed:id)`: `dev` (100) and `test` (615). **As-of date 2024-12-31**: the Q&A is about the 2024 tax
  return (exercício 2024, income of 2023) and its references include acts up to July 2024, so a date at the end
  of 2024 is the first one at which every cited act exists. The tax-tier texts are the compiled versions
  scraped in 2024-25, so some are later than the date (a limit, below).
* **`temporal`** (120 questions, its own split): built by code from the version pairs of the versioned tier,
  the same question asked as of the day before and the day of each change ("Segundo a Lei nº ..., o que dispunha o
  art. N na data de dd/mm/aaaa?"). `gold_units` is `<unit id>#v<seq>` (the version in force); after a repeal
  nothing is in force and the question is unanswerable. No model writes questions. `bench.citations` scores
  these by code (`temporal_outcome`): the answer must cite the gold unit, and its words are compared with the words
  that distinguish the gold version from the other one (`gold_version`, `other_version`, `undetermined`,
  `unit_not_cited`, `abstained`; after a repeal `cited_repealed` is the error).

The runner's containment grade (does the gold answer string appear) is computed for these rows too but is not
meaningful here: BR-TaxQA-R's official answers are paragraphs, and the `temporal` split has no answer string.
The measures of this test are the ones of `bench.citations`.

## Limits

* The tax tier's texts are single-version, as scraped; the federal tier's are mostly original publications.
  Neither knows later amendments except through annotations. So `in force` can be wrong in both directions for
  those tiers; it is exact only for the 60 versioned provisions.
* 1,174 federal norms are flagged revoked in the source with no date; they stay in force in the store.
* BR-TaxQA-R gold references and answers were extracted by an LLM pipeline (per the dataset card); some titles
  carry wrong dates. The questions are personal-income-tax questions: the federal tier is mostly a haystack.
* The embedded subset (`brlaw-core`) is the tax tier, the versioned tier and the federal norms dated 1995
  or later plus the Constitution; the whole federal tier would take about four hours to embed with the default
  local model. Existence and in-force checks run against the **full** store.
* The 60 versioned provisions come from four base norms (three tax-related laws and the CLT); they are an exact
  but narrow test of dated wordings, not a sample of Brazilian law. The CLT's 2017 reform is not in it: its
  entry into force is "cento e vinte dias" after publication, which this build does not compute.
* Nothing here is legal advice, and a "supported" verdict from the judge is a model's opinion; the human-check
  CSV exists for that reason.

## Running it

```
python -m heuresis.bench.run --dataset brlaw --split dev --systems closed_book,hybrid,agentic,engine \
    --time-aware-variants --variants-of agentic --dry-run --out bench_out/brlaw-dev     # offline, free
python -m heuresis.bench.citations bench_out/brlaw-dev --db data/db/brlaw.db            # the metric, free
```

`--paid` additionally needs `--cap`, `--ledger` and the environment variable `PROJECTS_ANTHROPIC_KEY`; the
support judge is `bench.citations --paid` and writes a CSV sample for human checking.
