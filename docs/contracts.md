# Contracts

The seams between the parts of heuresis. Each work package owns its files; these
contracts are how they meet. `src/heuresis/model.py` and
`src/heuresis/interfaces.py` are shared and frozen: read them first, never edit
them. If a contract is wrong or missing something, say so in your hand-back
instead of changing it.

## Rules for every work package

- Python 3.11+. Core runtime dependencies: the standard library and NumPy only.
  Anything else is optional and imported lazily inside the function that needs it.
- Every component must work offline with the fakes in `heuresis/fakes.py`. No
  test may touch the network or need an API key.
- Edit only the files your brief lists. Tests go in the test file your brief names.
- Do not run `git` commands. Do not create documents other than those named.
- Code and comments in English. No mention of AI tools, agents or models that
  wrote the code. No secrets.
- Run `python3 -m pytest tests/<your test file> -q` from the repository root and
  make it pass before handing back.

## Layout and owners

| Path | Owner | Contents |
|---|---|---|
| `model.py`, `interfaces.py` | frozen | shared types and protocols |
| `fakes.py`, `surface/` | surface | offline fakes; the mutable configuration surface |
| `store.py` | store | SQLite store, event replay, as-of queries, FTS5, vectors, edges |
| `domains/` | domains | `text`, `git`, `tables`, `legal_br` plug-ins; `ingest.py` |
| `router.py` | router | understand stage: rules, classifier, ask-back |
| `retrieve.py`, `models_local.py` | retrieve | the cascade; optional local ONNX models |
| `tools/` | tools | `calc`, `dates`, `sql` deterministic tools |
| `llm.py`, `pricing.py`, `draft.py` | draft | model client, price table, drafting and mark parsing |
| `locked/` | locked | verifier, decision rule, scoring, content hash, surface guard |
| `engine.py`, `__init__.py` | integrator | `Engine` wiring the stages together |
| `bench/` | bench | datasets, baselines, runner, ledger, statistics, report |
| `cli.py`, `mcp_edge.py` | edge | command line and MCP server |

## Function contracts

All imports are from `heuresis.model` / `heuresis.interfaces` unless noted.

### surface (`heuresis/surface/config.py`, `heuresis/surface/default.json`, `heuresis/surface/prompts.py`)

```python
@dataclass
class Config:            # nested dataclasses, one per stage; every field has a default
    router: RouterCfg    # ask_threshold=0.6, default_intent="lookup"
    retrieve: RetrieveCfg  # k_lexical=50, k_dense=50, rrf_k=60, rerank_in=50, rerank_out=8,
                           # early_stop=True, early_stop_margin=0.35,
                           # dense=True, expand=False, expand_hops=1, rerank=False,
                           # rewrite=False, second_round=False
    draft: DraftCfg      # model="claude-haiku-5-5", max_tokens=600, max_context_chars=24000
    verify: VerifyCfg    # support_threshold=0.5, partial_threshold=0.3, atomic_claims=False
    decide: DecideCfg    # min_supported_fraction=1.0, partial_fraction=0.5, conflict_margin=0.1

def load_config(path: str | None = None) -> Config   # None -> packaged default.json
def config_to_dict(cfg) -> dict ; def config_from_dict(d) -> Config   # unknown keys raise
```

`prompts.py` holds `DRAFT_SYSTEM` and `draft_prompt(question, as_of, passages, tools) -> str`.

### fakes (`heuresis/fakes.py`)

`HashEmbedder(dim=256)` (hashed character n-grams), `OverlapReranker()`,
`RuleEntailer()` (token containment, with number and negation mismatch forcing a
low score), `EchoLLM(script=None)` (if `script` is given, returns scripted
replies in order; otherwise writes an extractive draft in the draft format below
from the first passages in the prompt). All implement the protocols in
`interfaces.py`, are deterministic, and report zero cost.

### store (`heuresis/store.py`)

```python
class Store:
    def __init__(self, path: str)                      # ":memory:" allowed
    def add(self, sources=(), units=(), events=(), edges=()) -> None   # idempotent by id
    def rebuild(self) -> None            # replay all events -> versions table + FTS index
    def versions(self, unit_id: str, as_of: AsOf | None = None) -> list[Version]
        # every version of the unit as known at as_of.recorded (None = now)
    def text_at(self, unit_id: str, as_of: AsOf) -> Version | None
    def lexical(self, text: str, as_of: AsOf, scope: Scope, k: int) -> list[Passage]
    def put_vectors(self, embedder_id: str, rows: list[tuple[str, int, np.ndarray]]) -> None
        # raises ValueError on an unknown (unit_id, seq); seq is 0-based, in replay order
    def missing_vectors(self, embedder_id: str) -> list[tuple[str, int, str]]  # unit_id, seq, text
    def dense(self, vec: np.ndarray, embedder_id: str, as_of: AsOf, scope: Scope, k: int) -> list[Passage]
    def neighbours(self, unit_ids: list[str], as_of: AsOf, types: tuple[str, ...] = ()) -> list[Passage]
    def get_source(self, source_id: str) -> Source | None
    def stats(self) -> dict            # counts of sources, units, events, versions, edges
    def close(self) -> None
```

- `as_of.valid = None` means today (UTC date). A version is in force when
  `valid_from <= d < valid_to` with `None` unbounded.
- `lexical`, `dense` and `neighbours` must apply the as-of and scope filters
  **inside the query, before ranking**. A version not in force at the date must
  never be returned. This is the engine's central invariant.
- When `as_of.recorded` is set and earlier than the newest event, replay only the
  events with `recorded_at <= as_of.recorded` (an in-memory replay is fine).
- Passages carry `coverage` from their source and `certainty` from their version.

### domains (`heuresis/ingest.py`, `heuresis/domains/*.py`)

`get_domain(name) -> Domain`; `ingest(store, path, domain) -> dict` (counts; calls
`store.add` then `store.rebuild`, embeds nothing).

### router (`heuresis/router.py`)

```python
def understand(text: str, *, cfg: RouterCfg, rules: list[Rule] = (), classifier=None,
               as_of: AsOf | None = None, scope: Scope | None = None,
               today: str | None = None) -> Query
class NearestIntent:      # optional second layer
    def __init__(self, embedder: Embedder, examples: list[tuple[str, str]])
    def __call__(self, text: str) -> tuple[str, float]      # intent, confidence
```

Built-in rules extract an explicit date from the question (ISO, `15/03/2024`,
"March 2024", "em março de 2024", "in 2019") into `as_of.valid` and set
`dated=True`; a caller-supplied `as_of` wins. Below `cfg.ask_threshold` the
router sets `clarify` to one short question and does not guess.

### retrieve (`heuresis/retrieve.py`)

```python
def cascade(store, query: Query, cfg: RetrieveCfg, *, embedder=None, reranker=None,
            trace: list[StageTrace]) -> list[Passage]
def rrf(lists: list[list[Passage]], k: int = 60) -> list[Passage]
```

Order: lexical, early-stop test, dense + RRF, expand (switch), rerank. Appends one
`StageTrace` per stage that ran. Returns at most `cfg.rerank_out` passages with
`mark` set to `t1..tn`. `models_local.py` offers `load_embedder(name)`,
`load_reranker(name)`, `load_entailer(name)` over ONNX Runtime, imported lazily.

### tools (`heuresis/tools/__init__.py`, `calc.py`, `dates.py`, `sql.py`)

`default_tools() -> list[Tool]`; `run_calls(tools, calls) -> list[ToolResult]`.
`calc` evaluates arithmetic safely (AST whitelist, `Decimal`, no names or calls
beyond `min max round abs sum`); `dates` does date differences, additions and
weekday checks; `sql` runs one read-only `SELECT` against a SQLite file with a
row cap and a time limit.

### draft (`heuresis/draft.py`, `heuresis/llm.py`, `heuresis/pricing.py`)

```python
def draft(llm: LLM, query: Query, passages: list[Passage], tools: list[Tool], cfg: DraftCfg) -> Draft
def parse_draft(raw: str) -> Draft
def render(draft: Draft, tool_results: list[ToolResult]) -> str
```

Draft format, one item per line:

```
CALL k1 calc {"expr": "1200 * 0.06"}        # optional tool requests, before the answer
The limit was R$ 4.8 million [t1].           # each sentence ends with its marks
The tax due is {k1} [t2][k1].                # {k1} is replaced by the tool result
ABSTAIN no_source: nothing covers this.      # instead of an answer
```

`llm.AnthropicLLM(model, api_key=None, key_env="PROJECTS_ANTHROPIC_KEY", ..., temperature=0.0)` (sent in the request body unless `None`) uses
the standard library HTTP client, reads the key from `PROJECTS_ANTHROPIC_KEY`
(never `ANTHROPIC_API_KEY`) only when first called, sends it only to the base URL
`https://api.anthropic.com` (no environment variable changes it), and prices usage
with `pricing.price(model, tokens_in, tokens_out, cached=0, batch=False)`.

### locked (`heuresis/locked/verify.py`, `decide.py`, `scoring.py`, `guard.py`)

```python
def verify(draft: Draft, passages, tool_results, store, as_of: AsOf, entailer: Entailer,
           cfg: VerifyCfg) -> list[Claim]
def decide(claims, passages, query: Query, cfg: DecideCfg, store=None) -> tuple[str, float, Abstention | None]
def locked_hash() -> str                       # sha256 over the bytes of heuresis/locked/*.py
def check_diff(changed_paths: list[str]) -> list[str]   # paths outside heuresis/surface/ (violations)
```

Per claim: `exists` (every cited mark resolves to a passage or tool result),
`valid_at_date` (each cited version is in force at `as_of`, checked against the
store), `supported` (entailment of the sentence by the cited passages at or
above the threshold), `numbers_traced` (every number in the sentence appears in a
cited passage or is a cited tool value). A sentence with no marks is unsupported.
Grade = min(lowest claim support, lowest cited certainty, lowest cited coverage),
mapped to 0..1. `scoring.py` holds answer normalisation, exact match and token
F1, the penalised score (+1 / 0 / -1), risk-coverage and AURC, and citation
precision and recall.

### engine (`heuresis/engine.py`)

`Engine.open(path, domain=None, *, config=None, llm=None, embedder=None, reranker=None, entailer=None)`,
`.ingest(path)`, `.index()` (embeds missing vectors), `.ask(question, as_of=None, scope=None, budget_usd=None) -> Answer`,
`.search(question, as_of=None, scope=None, k=10) -> list[Passage]`,
`.verify(text, passages, as_of=None) -> list[Claim]`, `.unit(unit_id, as_of=None) -> Version | None`.

`domain=None` means the domain stored in the database, or `text` for a new one; an
explicit domain that differs from the stored one raises `ValueError` naming both,
unless the database has no units. `Answer.trace` stage names: `understand`,
`lexical`, `dense`, `expand`, `rerank`, `retrieve`, `draft`, `tools`,
`draft_followup`, `verify`, `decide`, `assemble`.
