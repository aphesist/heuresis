# MCP edge

`heuresis.mcp_edge` is a thin Model Context Protocol server over the engine: stdio, newline-delimited
JSON-RPC 2.0, standard library only. The engine never imports it. Its protocol handling is adapted
from the sibling project's edge (contraprova, same owner) and the two behave alike: same dual-era
rules, same error codes, same `server/discover`.

```
python -m heuresis.mcp_edge --db PATH [--domain NAME] [--allow-ingest] [--model MODEL --budget USD]
```

| Flag | Meaning |
|---|---|
| `--db PATH` | the database; the only store the server opens (required) |
| `--domain NAME` | domain plug-in (default: the one stored in the database, else `text`) |
| `--allow-ingest` | expose the `ingest` tool (the only one that takes a file path) |
| `--model MODEL --budget USD` | answer with a real model; one cap shared by every `ask` for the life of the process, refused once reached. Without these the server is offline (fakes, zero cost). `--model` without `--budget` is refused at start-up. The key is read by the model client from the environment; the server never reads, returns or logs environment variables. |
| `--max-calls-per-minute N` | sliding-window rate limit on `tools/call` (default 600) |

Claude Code: `claude mcp add --transport stdio heuresis -- python -m heuresis.mcp_edge --db /abs/corpus.db`.

## Protocol

Dual-era, as in contraprova. A request whose `params._meta` carries
`io.modelcontextprotocol/protocolVersion` is served statelessly under `2026-07-28` (`server/discover`,
`tools/list`, `tools/call`); both `protocolVersion` and `clientCapabilities` are required (`-32602`
otherwise), an unsupported version gives `-32022` with `data.supported` / `data.requested`. An
`initialize` request switches the process to legacy semantics (`2025-11-25`, `2025-06-18`,
`2025-03-26`, `2024-11-05`; an unknown requested version is answered with `2025-11-25`), after which
`tools/list`, `tools/call` and `ping` work without `_meta`. A request with neither is `-32602`.
Batches are rejected (`-32600`), malformed JSON is `-32700`, lines over 1 MiB and nesting over about
32 levels are refused, `NaN`/`Infinity` are refused, notifications are ignored. Nothing but protocol
messages is written to stdout; diagnostics go to stderr.

## Tools

Every input schema has `additionalProperties: false` and length limits. Arguments are validated
(types, ranges, real calendar dates, no control characters). Success returns `structuredContent`
plus the same JSON as a text block; failure returns `isError: true` and
`{"ok": false, "error": {"kind", "message"}}`. Error kinds: `InvalidArguments`, `NotFound`,
`BudgetExhausted`, `RateLimited`, `ModelError`, `EngineError` (no traceback, no paths).

| Tool | Arguments (required in bold) | Result |
|---|---|---|
| `ask` | **question** (1..2000), `as_of` (YYYY-MM-DD), `recorded` (ISO), `sources` (<=32 ids), `budget_usd` (0..100] | `status`, `text`, `claims[]` (label, support, `citations[]` with unit_id, seq, valid_from, valid_to), `grade`, `abstention`, `usd`, `ms`, `trace[]`; with `--model` also `server_budget` |
| `search` | **question**, `as_of`, `k` (1..50, default 10) | `passages[]` |
| `verify` | **text** (1..8000), **unit_ids** (1..32), `as_of` | `claims[]`, `missing[]` (units not in force); `NotFound` if none is in force |
| `get_unit` | **unit_id**, `as_of` | `unit` (text, validity interval, certainty, recorded_at, axes); `NotFound` otherwise |
| `ingest` (only with `--allow-ingest`) | **path** (<=1024), `domain` (a registered plug-in) | `counts`; the new content is embedded with the offline embedder |

Example:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}},"name":"get_unit","arguments":{"unit_id":"urn:lex:br:federal:lei:2020-03-10;1!art2","as_of":"2021-01-01"}}}
```

## Security notes

All input is untrusted. No tool but `ingest` accepts a path, and it is absent unless the operator
opted in; `ingest` reads whatever path the client names on the server's machine, so enable it only
for clients you trust. The server runs offline unless a model and a budget are given; the shared cap
is enforced by a wrapper around the model and by the engine's own budget check. stdio has no
authentication: whoever can start the process can use it.

## What was verified

Verified against this code, by `tests/test_mcp_edge.py` (in-process and one real subprocess):
discover; `tools/list` with `ingest` hidden by default and shown with the flag; each tool's happy
path and validation failure; the legacy handshake; `-32022` on an unsupported version; batch
rejection; malformed JSON; stdout carrying only protocol messages; the shared budget refusing the
third call once spent; rate limiting; no traceback on engine failure.

Taken from contraprova's document without re-checking against the specification (nor against a live
MCP client, nor `schema.json`): that `2026-07-28` is the current revision; the `_meta` keys; the
`-32022` code and its `data` shape; `resultType`, `ttlMs` and `cacheScope` on results; removal of
`ping`, sessions and the handshake in the modern era; that dual-era servers may answer `initialize`
with legacy semantics; stdio framing rules. The legacy version list is likewise copied.
