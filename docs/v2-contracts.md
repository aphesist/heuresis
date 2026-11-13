# v2 contracts

The seams between the parts of the v2 engine. `docs/design-v2.md` gives the reasons; this
file gives the names, signatures and rules that code and tests rely on. Version 1
(`heuresis.engine.Engine`, `heuresis/locked/`, `heuresis/surface/`) stays in the tree
unchanged: it is the `engine` baseline of every comparison, and its hashes are registered.

General rules (unchanged from `docs/contracts.md`): Python 3.11+, core runtime
dependencies are the standard library and NumPy; everything works offline with
`heuresis.fakes`; no test touches the network or needs a key; code and comments in
English; no corpus text, dataset, store or model file is committed.

## 1. Layout

```
src/heuresis/v2/
  __init__.py            exports EngineV2, load_surface
  engine.py              EngineV2: the cascade end to end
  retrieve.py            search, lookup, open_unit (as-of and scope always inside the store)
  agent.py               the propose loop (search / open / answer actions), Evidence
  bind.py                citation binding: named references become cited passages
  repair.py              one bounded repair turn driven by gate failures
  locked/                the v2 judge: never edited by the improvement loop
    __init__.py
    schema.py            the surface schema: fields, bounds, prompt specs, load/validate/hash
    gates.py             deterministic gates per sentence
    judge.py             the model judge: prompt, parser, verdict type
    decide.py            the decision rule and the confidence score
    calibration.py       risk-controlled threshold (Clopper-Pearson, fixed sequence)
    policy.json          owner-set policy: risk target, confidence, defaults
    manifest.py          hashes of every protected file; candidate path guard
    PROTECTED.json       written by `heuresis lock`; a test pins it to the tree
  surface/               the mutable surface: DATA ONLY (no .py file)
    default.json         config values
    domain.<name>.json   optional overlay for a domain (e.g. domain.legal_br.json)
    prompts/<name>.txt   prompt texts; `<name>.<prompt_set>.txt` overrides for a prompt set
  calibration/           calibration files written by the locked calibrator (may be empty)
src/heuresis/bench/
  systems_v2.py          the `engine2` benchmark system
  splits.py              rotating splits from unused pools; held-out guard
  calibrate2.py          fits calibration files from a dev run of `engine2`
src/heuresis/evolve/     the improvement loop over the engine (section 9)
```

Additive changes to shared v1 modules (allowed, nothing else in them changes):
`model.Claim.kind: str = "cited"` (`"cited"` or `"derived"`), `model.Answer.meta: dict`
(default empty), `Store.passage_at`, `Store.adjacent`, `AnthropicLLM` cache break
(section 8). `heuresis/locked/*.py` and `heuresis/surface/*` must stay byte-identical
(their hashes are registered and one test pins the surface and prompts hashes).

## 2. Surface (`v2/locked/schema.py`, data in `v2/surface/`)

The surface is data. A candidate from the improvement loop can only change values the
schema names, inside the bounds the schema gives. It cannot add code, a gate, a judge
prompt, a threshold of the decision rule or a risk target.

```python
@dataclass(frozen=True)
class Field:
    kind: str                 # "int" | "float" | "bool" | "enum"
    default: Any
    lo: float | None = None   # inclusive bounds for int/float
    hi: float | None = None
    choices: tuple[str, ...] = ()

@dataclass(frozen=True)
class PromptSpec:
    max_chars: int
    required: tuple[str, ...] = ()   # substrings that must be present (protocol words)

SCHEMA: dict[str, dict[str, Field]]      # section -> key -> Field
PROMPTS: dict[str, PromptSpec]           # prompt name -> spec
FORBIDDEN: tuple[str, ...]               # substrings no prompt may contain (lower-cased match)

@dataclass(frozen=True)
class Surface:
    config: dict[str, dict[str, Any]]    # complete: every schema key present
    prompts: dict[str, str]              # complete: every prompt name present
    def get(self, section: str, key: str) -> Any
    def prompt(self, name: str) -> str

def load_surface(directory: str | Path | None = None, *, domain: str | None = None,
                 prompt_set: str | None = None) -> Surface
def validate(surface: Surface) -> list[str]          # violations; empty = valid
def apply_overrides(surface: Surface, candidate: dict) -> Surface   # raises ValueError on any violation
def surface_hash(surface: Surface) -> str            # sha256 of canonical JSON of config + prompts
def describe() -> dict                               # schema as JSON: fields, bounds, prompt specs
```

A candidate is `{"config": {"<section>.<key>": value, ...}, "prompts": {"<name>": "<text>", ...}}`.
Unknown sections, keys or prompt names, values out of bounds or of the wrong type, prompts
over `max_chars`, prompts missing a required substring, and prompts containing a forbidden
substring are violations. `load_surface` applies `default.json`, then `domain.<domain>.json`
if present, then prompt-set overrides, and raises `ValueError` if the result is not valid.

Schema (defaults are the packaged `default.json`):

| section | key | kind, bounds | default | meaning |
|---|---|---|---|---|
| retrieve | k_lexical | int 10..200 | 50 | lexical candidates |
| retrieve | k_dense | int 10..200 | 50 | dense candidates |
| retrieve | fusion | enum none, rrf, convex | convex | how lexical and dense lists combine (`none` = lexical only) |
| retrieve | alpha | float 0..1 | 0.7 | weight of the lexical list in convex fusion |
| retrieve | rrf_k | int 1..200 | 60 | RRF constant |
| retrieve | k_first | int 3..20 | 8 | passages shown before the first model call |
| retrieve | search_k | int 2..12 | 5 | new passages shown per search query |
| retrieve | prf_terms | int 0..12 | 0 | corpus-vocabulary expansion terms added from the first pass (0 = off) |
| retrieve | prf_docs | int 1..10 | 3 | first-pass passages the expansion terms come from |
| retrieve | open_radius | int 0..3 | 1 | neighbouring units shown when a unit is opened |
| retrieve | edge_expand | bool | false | follow explicit edges from the first-pass results |
| agent | max_turns | int 1..10 | 6 | model calls in the propose loop |
| agent | queries_per_turn | int 1..4 | 3 | search queries accepted in one reply |
| agent | max_context_chars | int 8000..200000 | 40000 | prompt size limit; passages are dropped, never cut |
| agent | max_sentences | int 0..20 | 0 | answer length limit (0 = none) |
| agent | max_tokens | int 256..16000 | 4096 | output cap of a propose call |
| repair | rounds | int 0..2 | 1 | repair turns after gate failures |
| route | lookup_direct | bool | true | fetch provisions the question names before searching |
| route | escalate | bool | false | retry once with the strong model after an `unsupported` abstention |
| judge | max_tokens | int 64..2000 | 400 | output cap of the judge call |

Prompts: `agent_system`, `agent_more`, `agent_last`, `repair`. `agent_system` must contain
`SEARCH:`, `OPEN:` and `ABSTAIN`; `FORBIDDEN` holds the judge's verdict words and the
canary marker (section 9), so a prompt cannot address the judge or name a canary.

## 3. Store additions (`store.py`)

Both apply the as-of and scope filters inside SQL, like `lexical` and `dense`.

```python
def passage_at(self, unit_id: str, as_of: AsOf) -> Passage | None
    # the version in force at as_of (as known at as_of.recorded), with title, source,
    # validity, coverage and certainty filled; stage "lookup"; None if nothing is in force
def adjacent(self, unit_id: str, as_of: AsOf, radius: int) -> list[Passage]
    # up to `radius` units before and after `unit_id` in the same source, in ingest order
    # (units.rowid), each as the version in force at as_of; excludes unit_id; stage "open"
```

## 4. Retrieval (`v2/retrieve.py`)

```python
def search(store, query: Query, cfg: dict, *, embedder=None, trace: list | None = None,
           k: int | None = None, exclude: set[tuple[str, int]] = frozenset()) -> list[Passage]
def lookup(store, domain, text: str, as_of: AsOf) -> tuple[list[Passage], list[Reference]]
def open_unit(store, unit_id: str, as_of: AsOf, radius: int) -> list[Passage]
def expansion_terms(question: str, passages: list[Passage], n_terms: int, n_docs: int) -> list[str]
```

- `search`: lexical first; if `prf_terms > 0` a second lexical pass with the question plus
  `expansion_terms` (terms from titles and text of the first-pass top `prf_docs`, ranked by
  frequency in those passages times rarity in the first-pass pool, question terms and stop
  words removed); if `fusion != "none"` and an embedder is given, dense and fusion
  (`rrf`, or `convex`: min-max normalised scores, `alpha * lexical + (1 - alpha) * dense`);
  if `edge_expand`, `store.neighbours` of the top results appended; returns at most `k`
  (default `k_first`) passages not in `exclude`, without marks. One `StageTrace` per stage
  that ran (`lexical`, `expand_terms`, `dense`, `edges`).
- `lookup`: runs the domain's reference resolver (if any) on `text`; for each `resolved`
  reference returns `store.passage_at` for its units (stage `lookup`); also returns the
  references so the caller can see which were not found or not in force.
- `open_unit`: the unit in force at the date plus `store.adjacent`.
- Nothing here takes a date from the model. Every call uses `query.as_of` and `query.scope`.

## 5. Propose loop (`v2/agent.py`), binding (`v2/bind.py`), repair (`v2/repair.py`)

```python
class Evidence:
    passages: list[Passage]                      # everything shown, in order, marks t1..tn
    rounds: list[tuple[str, list[Passage]]]      # (label, passages) blocks as shown
    def add(self, label: str, passages: Iterable[Passage]) -> list[Passage]   # new ones only, marked
    def by_mark(self, mark: str) -> Passage | None
    def seen(self) -> set[tuple[str, int]]

@dataclass
class Actions:
    searches: list[str]; opens: list[str]

def parse_actions(raw: str, max_queries: int) -> Actions | None
def build_prompt(surface, query: Query, evidence: Evidence, tools, turns_left: int,
                 feedback: str = "") -> str
def propose(llm, query, evidence, tools, surface, *, store, domain, embedder, trace,
            afford, feedback: str = "") -> tuple[Draft | None, tuple | None]
```

Reply protocol of a propose call (plain text; the `LLM` protocol is unchanged):
- **Actions.** If every non-empty line of the reply is `SEARCH: <query>` or `OPEN: <target>`,
  the reply is a set of actions (`parse_actions`; at most `queries_per_turn` searches and 3
  opens are run, the rest ignored). `<target>` is a mark of a shown passage (`t3`) or free
  text the domain resolver can resolve. Each search runs `retrieve.search` with the
  question's as-of and scope; each open runs `retrieve.open_unit` or `retrieve.lookup`.
  New passages are appended to the evidence as labelled blocks (`Search: <q>`,
  `Open: <target>`, `(nothing new)` when empty). Passages that no longer fit
  `max_context_chars` are not added.
- **Answer.** Otherwise the reply is parsed by `draft.parse_draft` (sentences with marks,
  `CALL` tool lines, `ABSTAIN <type>: reason`).
- On the last turn the prompt says no action remains; actions requested anyway end in an
  `unsupported` abstention with a trace note.
- `propose` returns `(draft, None)` or `(None, ("abstained", type, message))`; budget is
  checked with `afford` before every model call. Trace stages: `draft` per model call,
  `search` and `open` per executed action (tokens 0).
- Prompt layout: fixed header (as-of date, tools, question), evidence blocks in order, then
  the status line and instruction (`agent_more` / `agent_last`) and optional `feedback`.
  The text up to the end of the evidence is stable across turns; `llm.CACHE_BREAK` is
  inserted after it when the LLM has `supports_cache_break` (section 8).

`bind.bind(draft, evidence, store, domain, as_of) -> list[str]`: for every sentence, every
reference the domain resolver finds with status `resolved` whose unit is not cited by a
mark of that sentence: if `store.passage_at(unit, as_of)` exists, the passage is added to
the evidence (label `Bound`) and its mark is appended to the sentence. Returns notes. A
reference that does not resolve, or resolves to a unit with nothing in force at the date,
is left alone: the gate fails it. Domains without a resolver: no-op.

`repair.feedback(claims, verdict=None) -> str`: the text shown to the model on a repair
turn: each failed sentence with its reason in plain words (no mark, mark not shown,
provision not in force at the date, number not in the cited passages, reference not found,
reference not cited). The repair turn is a `propose` call with that feedback; it may act
(search, open) if turns remain.

## 6. The v2 judge (`v2/locked/`)

### 6.1 Deterministic gates (`gates.py`)

```python
CHECKS = ("exists", "valid_at_date", "numbers_traced", "references_traced")

def check(draft: Draft, passages: list[Passage], tool_results: list[ToolResult], store,
          as_of: AsOf, *, question: str = "", domain=None) -> list[Claim]
def deterministic_failure(claim: Claim) -> bool
def failure_reason(claim: Claim) -> str
```

One `Claim` per sentence. `kind = "derived"` when the sentence has no mark, else `"cited"`.

Cited sentence:
- `exists`: every passage mark is among `passages`, every tool mark is an `ok` tool result.
- `valid_at_date`: for every cited passage `store.text_at(unit_id, as_of)` exists and has the
  same `seq` (the store, not the passage copy, decides).
- `numbers_traced`: every number in the sentence appears in a cited passage (text or
  title), in a cited tool value, in the question, or is part of the as-of date; numbers
  inside a reference the resolver resolved to a cited unit are skipped.
- `references_traced` (domains with a resolver): every reference found in the sentence
  resolves, and resolves to a unit the sentence cites (same rule as v1 `references.py`).

Derived sentence (a conclusion that cites nothing):
- `exists` is true only if at least one cited sentence of the same draft passes all its
  gates; `numbers_traced`: every number appears in the question, in the as-of date, or in a
  cited sentence that passes; `references_traced`: the sentence contains no reference at
  all; `valid_at_date` is true.
- A derived sentence is kept only if the model judge also says it follows (6.3).

`check` never calls a model and never raises on malformed input (a failing sentence is the
result). Notes name each failure.

### 6.2 Model judge (`judge.py`)

One call per answer, on the sentences that passed the gates. The prompt and parser are
locked; the judge LLM is passed in by the caller and should be a different model or at
least a different configuration from the generator (thinking disabled, short output).

```python
JUDGE_SYSTEM: str
SENTENCE_VERDICTS = ("SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "FOLLOWS", "NOT_FOLLOWS")

@dataclass
class Verdict:
    sentences: dict[int, str]        # index in the kept list -> verdict
    answer: str                      # "DIRECT" | "PARTIAL" | "NO"
    sufficient: str                  # "YES" | "NO"
    premise: str                     # "OK" | "FALSE"
    conflict: tuple[str, str] | None # two passage marks, or None
    readable: bool
    raw: str = ""
    usage: Usage = field(default_factory=Usage)

def judge_prompt(question: str, as_of: str | None, claims: list[Claim],
                 passages: list[Passage], tool_results: list[ToolResult],
                 max_chars: int = 2500) -> str
def parse_verdict(raw: str, n: int) -> Verdict
def judge(llm, question, as_of, claims, passages, tool_results, *, max_tokens=400) -> Verdict
```

Reply format the parser reads (one line each; anything else is ignored):
`S<i>: SUPPORTED|PARTIAL|NOT_SUPPORTED` for cited sentences, `S<i>: FOLLOWS|NOT_FOLLOWS`
for derived ones, `ANSWER: DIRECT|PARTIAL|NO`, `SUFFICIENT: YES|NO`, `PREMISE: OK|FALSE`,
`CONFLICT: NONE` or `CONFLICT: t<a>, t<b>`. A missing sentence line reads as
`NOT_SUPPORTED` / `NOT_FOLLOWS`; a missing `ANSWER` or `SUFFICIENT` line makes the verdict
unreadable (`readable = False`), which the decision rule treats as a failed check.

What each line asks: *S*: do the cited passages state what the sentence states (all of it,
part, none)? For derived: does it follow from the supported sentences alone? *ANSWER*:
does the text answer the question that was asked, as of the date (directly, partly, not)?
*SUFFICIENT*: do the passages contain enough to settle the question? *PREMISE*: do the
passages contradict something the question assumes? *CONFLICT*: do two passages, both
shown as in force, give incompatible rules or facts for the question?

### 6.3 Decision rule (`decide.py`)

```python
@dataclass(frozen=True)
class Policy:                 # loaded from policy.json
    alpha: float              # risk target: share of answered questions that may be wrong
    delta: float              # 1 - confidence of the calibration bound
    default_tau: float        # threshold used when no calibration file matches
    grid: tuple[float, ...]   # candidate thresholds
    min_calibration_answers: int
    values: dict[str, float]  # verdict word -> score

@dataclass
class Decision:
    status: str                       # model.STATUSES
    confidence: float
    abstention: Abstention | None
    kept: list[int]                   # indexes of claims kept in the answer
    reasons: list[str]

def load_policy(path=None) -> Policy
def confidence(claims, kept, verdict, passages, policy) -> float
def decide(claims: list[Claim], verdict: Verdict | None, passages: list[Passage],
           query: Query, policy: Policy, *, tau: float | None = None, store=None,
           declined: str | None = None) -> Decision
```

The rule, in order:
1. `declined` (the model wrote `ABSTAIN <type>`): abstained with that type.
2. No passages: `no_source`. No claims: `unsupported`.
3. Deterministic gates: a claim with `deterministic_failure` is never kept. If no cited
   claim survives: `not_valid_at_date` when every failure is only the date check, else
   `unsupported`.
4. No verdict or an unreadable verdict: abstained `unsupported` (reason "judge unreadable").
5. `premise == FALSE`: abstained `false_premise`.
6. `conflict` names two marks that exist, cite different units, both pass `valid_at_date`,
   and their sources have equal `authority`: status `divergent`, abstention `conflict`
   listing both; with unequal authority the conflict is ignored (the higher source rules).
7. Sentence verdicts: `NOT_SUPPORTED` and `NOT_FOLLOWS` are dropped. A derived sentence is
   kept only with `FOLLOWS`. If no cited claim is kept: `unsupported`.
8. `answer == NO`: abstained `unsupported` ("does not answer the question").
   `sufficient == NO` and `answer != DIRECT`: abstained `no_source` ("the sources found do
   not settle the question").
9. Confidence = min of: lowest sentence value among kept claims, the `ANSWER` value, the
   `SUFFICIENT` value, lowest certainty of cited passages (`low` 0.33, `medium` 0.66,
   `high` 1.0), lowest coverage of cited passages / 4; multiplied by `values["dropped"]`
   when the judge dropped any sentence.
10. `confidence < tau` (`tau` from the calibration file, else `policy.default_tau`):
    abstained `unsupported` ("below the confidence threshold").
11. Otherwise `answered` if every claim is kept, else `partial` (dropped sentences removed
    from the text). The answer's `grade` is the confidence.

### 6.4 Calibration (`calibration.py`)

```python
def clopper_pearson_upper(errors: int, n: int, delta: float) -> float
@dataclass(frozen=True)
class Calibration:
    tau: float | None; alpha: float; delta: float
    n_questions: int; n_answered: int; errors: int; upper: float
    coverage: float; surface_hash: str; dataset: str; split: str; label: str; created: str
def fit(confidences: Sequence[float], wrong: Sequence[bool], *, alpha, delta, grid,
        min_answers) -> dict            # tau (or None), n_answered, errors, upper, table
def save(cal: Calibration, path) -> None
def load(path) -> Calibration
def find(directory, surface_hash: str, dataset: str | None = None) -> Calibration | None
```

`fit` walks the grid from the strictest threshold to the loosest (fixed-sequence testing,
so no multiplicity correction): at each `tau`, the answered set is the rows with
`confidence >= tau`; if it has fewer than `min_answers` rows the step is skipped; if the
Clopper-Pearson upper bound of its error rate at confidence `1 - delta` is at most
`alpha` the threshold is accepted and the walk continues; the walk stops at the first
threshold that fails. The result is the loosest accepted threshold, or `None` (nothing
certified). The engine uses a calibration file only when its `surface_hash` equals the
running surface's hash; otherwise `default_tau` applies and `Answer.meta["calibrated"]`
is false. `label` records what "wrong" meant (`containment`, `judge_equivalent`, ...).

### 6.5 Protected files (`manifest.py`)

```python
PROTECTED: tuple[str, ...]      # glob patterns relative to the repository root
SURFACE_DIR = "src/heuresis/v2/surface"
def protected_files(root=None) -> dict[str, str]     # path -> sha256
def protected_hash(root=None) -> str
def write_manifest(root=None) -> Path                # writes PROTECTED.json
def verify_manifest(root=None) -> list[str]          # changed, missing or new protected paths
def check_candidate_paths(paths: Iterable[str]) -> list[str]
    # violations: anything outside SURFACE_DIR, any file that is not .json or .txt,
    # any path with "..", absolute paths
```

Protected: `src/heuresis/locked/**`, `src/heuresis/v2/locked/**` (except `PROTECTED.json`
itself), `src/heuresis/store.py`, `model.py`, `interfaces.py`, `tools/**`, `references.py`,
`v2/bind.py`, `bench/{stats,datasets,brlaw,brlaw_versioned,citations,judge,ledger,splits,run,report,types,calibrate2}.py`,
and `src/heuresis/evolve/**`. `heuresis lock` rewrites `PROTECTED.json`; a test fails when
the tree and the file disagree, so a change to a protected file is always a visible,
separate step in review.

## 7. `EngineV2` (`v2/engine.py`)

```python
class EngineV2:
    def __init__(self, store, domain, *, surface=None, llm=None, judge_llm=None,
                 strong_llm=None, embedder=None, classifier=None, calibration=None,
                 policy=None, router_cfg=None)
    @classmethod
    def open(cls, path, domain=None, **kw) -> "EngineV2"     # same domain rules as Engine.open
    def ask(self, question, as_of=None, scope=None, budget_usd=None) -> Answer
    def search(self, question, as_of=None, scope=None, k=10) -> list[Passage]
    def close(self) -> None
```

`ask`, in order (trace stage names in brackets):
1. [understand] `router.understand` and the same date-settling rule as v1
   (`Engine._settle_date` logic). `needs_input` and `out_of_scope` exit here.
2. [lookup] if `route.lookup_direct` and the domain has a resolver: `retrieve.lookup` on
   the question. Passages go first in the evidence. A named provision that exists in the
   store but has no version in force at the date is recorded for the abstention message.
3. [retrieve] `retrieve.search`. No evidence at all: `not_valid_at_date` if
   `store.lexical_any_date` finds something, else `no_source`; all coverage 0:
   `outside_coverage`.
4. [draft, search, open] `agent.propose`.
5. [tools] tool calls run (`tools.run_calls`), same `sql` binding rule as v1.
6. [bind] `bind.bind`.
7. [gates] `locked.gates.check`.
8. [repair] if any claim fails a gate and `repair.rounds` and budget allow: one propose
   turn with `repair.feedback`, then tools, bind and gates again on the new draft. The new
   draft replaces the old one only if it has at least as many passing cited sentences.
9. [judge] `locked.judge.judge` on the claims that pass the gates (skipped when none pass
   or the model declined).
10. [decide] `locked.decide.decide` with `tau` from the matching calibration file.
11. [escalate] if the result is an `unsupported` abstention, `route.escalate` is on, a
    `strong_llm` was given and budget allows: steps 4-10 once more with the strong model
    and the evidence gathered so far.
12. [assemble] text of kept sentences with tool values filled; `Answer.claims` holds every
    claim with its checks, label (`supported` / `partial` / `unsupported`), `support`
    (the sentence value) and note; `Answer.passages` is exactly what the model was shown.

`Answer.meta`: `{"engine": "v2", "surface_hash", "confidence", "tau", "calibrated",
"verdict": {"answer", "sufficient", "premise", "conflict"}, "bound": n, "repairs": n,
"escalated": bool, "dropped": [{"text", "reason"}]}`.

Failure handling: a model error or unreadable reply in propose or judge ends in
`unsupported` with a trace note (`model error`), a budget stop in `budget`; `ask` does not
raise for these. `judge_llm` defaults to `llm`.

## 8. LLM cache break (`llm.py`)

`CACHE_BREAK = "\x00cache\x00"`. `AnthropicLLM(..., cache=False)`: when `cache` is true the
client has `supports_cache_break = True`, sends the system prompt as a text block with
`cache_control: {"type": "ephemeral"}`, and splits the user prompt at the last
`CACHE_BREAK` into two text blocks, the first carrying `cache_control`. Without `cache`,
and in every other LLM, the marker is never inserted (callers check
`getattr(llm, "supports_cache_break", False)`); `AnthropicLLM` strips any marker it
receives when `cache` is false. Usage already records cached tokens and prices them.

## 9. Improvement loop (`heuresis/evolve/`)

```python
# evolve/api.py: the interface an outer optimiser (autopoiesis, a cron job, a person) uses
def describe(root=None) -> dict
    # {"surface_schema", "champion": {"id", "surface_hash"}, "protected_hash",
    #  "stages": [...], "budget": {...}, "datasets": [...]}
def evaluate(candidate: dict | str | Path, *, stage: str, workdir, ledger=None,
             context=None) -> dict       # public report; never contains gold or sealed rows
def promote(candidate_id: str, *, workdir) -> dict
def rollback(*, workdir, to: str | None = None) -> dict
def status(*, workdir) -> dict
def reflective_dataset(candidate_id: str, *, workdir, limit=20) -> list[dict]
    # redacted failure traces for a proposer: question, the engine's answer, typed outcome,
    # gate and judge reasons; no gold answer, no gold unit, nothing from sealed sets
```

Stages of `evaluate` (each returns `{"stage", "passed", "metrics", "tripwires", "cost_usd"}`):
`static` (schema validation, path guard, protected hash check; free), `smoke` (offline run
on the packaged fixture with fakes; free), `screen` (small paired sample of the current
rotating dev split against the champion), `dev` (the whole rotating dev split, paired),
`promote` (the sealed promotion set: returns only pass/fail and the decision statistics,
never rows). The CLI mirrors the API: `heuresis evolve describe|evaluate|promote|rollback|
status|cycle|lock-check`, each with `--json`.

Files under the workdir (default `evolve_runs/`, git-ignored): `archive.jsonl` (one row per
candidate: id, parent, candidate, surface hash, stage results, status), `champion.json`
(current champion id, surface hash, history for rollback), `ledger.jsonl`, `cycles/`.
The loop, the splits, the tripwires and the promotion statistics are specified in
`docs/design-v2.md` section (f) and implemented in `evolve/loop.py`, `evolve/splits.py`,
`evolve/tripwires.py`, `evolve/promotion.py`, `evolve/proposers.py`.
