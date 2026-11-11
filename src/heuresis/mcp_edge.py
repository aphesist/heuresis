"""MCP edge: a thin stdio facade over the heuresis engine.

Outside harnesses talk to heuresis through this module only. The engine never
imports it; it imports the engine (lazily, on the first tool call).

Transport: newline-delimited JSON-RPC 2.0 over stdin/stdout, standard library
only. Protocol handling follows the sibling project's edge (see docs/mcp.md):
it is *dual-era* in the sense of MCP revision 2026-07-28.

* A request whose ``params._meta`` carries ``io.modelcontextprotocol/protocolVersion``
  is served statelessly under 2026-07-28.
* An ``initialize`` request selects legacy semantics for the rest of this
  stdio process.

Every input is untrusted. The only tool that takes a file path is ``ingest``
(and only when started with ``--allow-ingest``). The server never reads or
returns environment variables; the model key is read by the model client.

Run: ``python -m heuresis.mcp_edge --db PATH [--domain NAME] [--allow-ingest]
[--model MODEL --budget USD]``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping

from . import __version__

# ------------------------------------------------------------------ protocol constants

MODERN_VERSION = "2026-07-28"
SUPPORTED_MODERN = (MODERN_VERSION,)
SUPPORTED_LEGACY = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
UNSUPPORTED_PROTOCOL_VERSION = -32022

SERVER_INFO = {"name": "heuresis", "version": __version__}

# ------------------------------------------------------------------ input limits

MAX_LINE_BYTES = 1024 * 1024
MAX_DEPTH = 32
MAX_QUESTION_CHARS = 2000
MAX_TEXT_CHARS = 8000
MAX_ID_CHARS = 512
MAX_PATH_CHARS = 1024
MAX_UNIT_IDS = 32
MAX_SOURCES = 32
MAX_K = 50
MAX_BUDGET_USD = 100.0
DEFAULT_CALLS_PER_MINUTE = 600

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?)?$")
_MARK_RE = re.compile(r"\[\s*[tkTK]\d+")

_DATE_SCHEMA = {
    "type": "string",
    "minLength": 10,
    "maxLength": 10,
    "pattern": r"^\d{4}-\d{2}-\d{2}$",
    "description": "ISO date YYYY-MM-DD",
}
_TS_SCHEMA = {
    "type": "string",
    "minLength": 10,
    "maxLength": 40,
    "description": "ISO date or timestamp: only what the corpus knew by then",
}
_ID_SCHEMA = {"type": "string", "minLength": 1, "maxLength": MAX_ID_CHARS}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "ask",
        "title": "Ask a question",
        "description": (
            "Answer a question from the corpus as of a date. The answer is verified claim by claim "
            "against the cited units; when it cannot be, the result is a typed abstention, not a guess."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "minLength": 1, "maxLength": MAX_QUESTION_CHARS},
                "as_of": _DATE_SCHEMA,
                "recorded": _TS_SCHEMA,
                "sources": {"type": "array", "items": _ID_SCHEMA, "maxItems": MAX_SOURCES, "description": "restrict to these source ids"},
                "budget_usd": {"type": "number", "exclusiveMinimum": 0, "maximum": MAX_BUDGET_USD},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "idempotentHint": False},
    },
    {
        "name": "search",
        "title": "Search units",
        "description": "Retrieve the passages in force at a date for a question, without drafting an answer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "minLength": 1, "maxLength": MAX_QUESTION_CHARS},
                "as_of": _DATE_SCHEMA,
                "k": {"type": "integer", "minimum": 1, "maximum": MAX_K},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
    {
        "name": "verify",
        "title": "Verify a text against units",
        "description": (
            "Check each sentence of a text against the named units as they read at the date. "
            "Sentences with no [tN] marks are checked against all named units."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT_CHARS},
                "unit_ids": {"type": "array", "items": _ID_SCHEMA, "minItems": 1, "maxItems": MAX_UNIT_IDS},
                "as_of": _DATE_SCHEMA,
            },
            "required": ["text", "unit_ids"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
    {
        "name": "get_unit",
        "title": "Read one unit",
        "description": "The text of one unit as it read at a date, with its validity interval.",
        "inputSchema": {
            "type": "object",
            "properties": {"unit_id": _ID_SCHEMA, "as_of": _DATE_SCHEMA},
            "required": ["unit_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
]

INGEST_TOOL: dict[str, Any] = {
    "name": "ingest",
    "title": "Ingest a path",
    "description": "Load a file or directory on the server's machine into the corpus, then embed it. Only present when the server was started with --allow-ingest.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "minLength": 1, "maxLength": MAX_PATH_CHARS},
            "domain": {"type": "string", "minLength": 1, "maxLength": 64, "description": "domain plug-in name; default: the server's domain"},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
}

INSTRUCTIONS = (
    "heuresis retrieval engine. ask answers a question as of a date with verified citations or a typed "
    "abstention; search returns passages; verify checks a text against units; get_unit reads one unit."
)


# ------------------------------------------------------------------ helpers


class ToolInputError(Exception):
    """Arguments failed validation; reported as a tool execution error."""


class _RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-standard JSON constant {name}")


def _loads(text: str) -> Any:
    return json.loads(text, parse_constant=_reject_constant)


def _depth_ok(value: Any, limit: int = MAX_DEPTH) -> bool:
    stack = [(value, 1)]
    while stack:
        v, d = stack.pop()
        if isinstance(v, (dict, list)):
            if d > limit:
                return False
            children = v.values() if isinstance(v, dict) else v
            stack.extend((c, d + 1) for c in children)
    return True


def _check_text(name: str, value: Any, max_chars: int, *, min_chars: int = 0, multiline: bool = False) -> str:
    if not isinstance(value, str):
        raise ToolInputError(f"{name} must be a string")
    if not (min_chars <= len(value) <= max_chars):
        raise ToolInputError(f"{name} must be {min_chars}..{max_chars} characters")
    allowed = "\n\t" if multiline else ""
    if any((ord(c) < 32 and c not in allowed) or ord(c) == 127 for c in value):
        raise ToolInputError(f"{name} must not contain control characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ToolInputError(f"{name} is not valid Unicode") from None
    return value


def _check_date(name: str, value: Any) -> str:
    _check_text(name, value, 10, min_chars=10)
    if not _DATE_RE.match(value):
        raise ToolInputError(f"{name} must be an ISO date YYYY-MM-DD")
    import datetime as _dt

    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        raise ToolInputError(f"{name} is not a real calendar date") from None
    return value


def _check_ts(name: str, value: Any) -> str:
    _check_text(name, value, 40, min_chars=10)
    if not _TS_RE.match(value):
        raise ToolInputError(f"{name} must be an ISO date or timestamp")
    return value


def _check_ids(name: str, value: Any, max_items: int, *, min_items: int = 0) -> list[str]:
    if not isinstance(value, list) or not (min_items <= len(value) <= max_items):
        raise ToolInputError(f"{name} must be a list of {min_items}..{max_items} strings")
    return [_check_text(f"{name}[{i}]", v, MAX_ID_CHARS, min_chars=1) for i, v in enumerate(value)]


def _only_keys(args: Mapping[str, Any], allowed: tuple[str, ...]) -> None:
    extra = sorted(set(args) - set(allowed))
    if extra:
        raise ToolInputError(f"unexpected argument(s): {', '.join(map(str, extra))}")


def _require(args: Mapping[str, Any], *keys: str) -> None:
    for k in keys:
        if k not in args:
            raise ToolInputError(f"{k} is required")


class RateLimiter:
    """At most ``max_calls`` tool calls in any sliding ``window`` seconds."""

    def __init__(self, max_calls: int, window: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.max_calls, self.window, self.clock = max_calls, window, clock
        self._calls: deque[float] = deque()

    def allow(self) -> bool:
        now = self.clock()
        while self._calls and now - self._calls[0] >= self.window:
            self._calls.popleft()
        if len(self._calls) >= self.max_calls:
            return False
        self._calls.append(now)
        return True


# ------------------------------------------------------------------ shared serialisation (also used by the CLI)


def citation_dict(p: Any) -> dict[str, Any]:
    return {"unit_id": p.unit_id, "seq": p.seq, "valid_from": p.valid_from, "valid_to": p.valid_to}


def claim_dict(c: Any, by_mark: Mapping[str, Any]) -> dict[str, Any]:
    cites = [citation_dict(by_mark[m]) for m in c.passage_marks if m in by_mark]
    return {
        "text": c.text,
        "label": c.label,
        "support": round(float(c.support), 4),
        "citations": cites,
        "tool_marks": list(c.tool_marks),
        "checks": dict(c.checks),
        "note": c.note,
    }


def trace_dict(t: Any) -> dict[str, Any]:
    return {"stage": t.stage, "ms": round(float(t.ms), 3), "tokens_in": t.tokens_in, "tokens_out": t.tokens_out,
            "usd": float(t.usd), "n_out": t.n_out, "note": t.note}


def answer_dict(a: Any, *, trace: bool = True) -> dict[str, Any]:
    by_mark = {p.mark: p for p in a.passages}
    out: dict[str, Any] = {
        "status": a.status,
        "text": a.text,
        "claims": [claim_dict(c, by_mark) for c in a.claims],
        "grade": round(float(a.grade), 4),
        "abstention": None,
        "usd": float(a.usd),
        "ms": round(float(a.ms), 3),
    }
    if a.abstention is not None:
        out["abstention"] = {"type": a.abstention.type, "message": a.abstention.message, "searched": list(a.abstention.searched)}
    if trace:
        out["trace"] = [trace_dict(t) for t in a.trace]
    return out


def passage_dict(p: Any) -> dict[str, Any]:
    return {"unit_id": p.unit_id, "seq": p.seq, "title": p.title, "source_id": p.source_id, "text": p.text,
            "score": round(float(p.score), 6), "stage": p.stage, "valid_from": p.valid_from, "valid_to": p.valid_to,
            "coverage": p.coverage, "certainty": p.certainty}


def version_dict(v: Any) -> dict[str, Any]:
    return {"unit_id": v.unit_id, "seq": v.seq, "text": v.text, "valid_from": v.valid_from, "valid_to": v.valid_to,
            "certainty": v.certainty, "recorded_at": v.recorded_at, "axes": dict(v.axes)}


def resolve_domain(db: str | Path, explicit: str | None) -> str:
    """The domain to open ``db`` with: the explicit name, else the one stored in the
    database, else ``text``. (Opening an engine records its domain in the database,
    so reading it must happen first.)"""
    if explicit:
        return explicit
    p = Path(db)
    if p.is_file():
        from .store import Store

        st = Store(str(p))
        try:
            return st.meta_get("domain") or "text"
        finally:
            st.close()
    return "text"


def verify_units(engine: Any, text: str, unit_ids: list[str], as_of: str | None) -> dict[str, Any]:
    """Verify ``text`` against the named units as they read at ``as_of``.

    Returns ``{"claims": [...], "missing": [unit ids not in force]}``. Sentences
    that carry no ``[tN]`` marks are cited to every named unit.
    """
    from .model import AsOf, Passage

    asof = AsOf(valid=as_of)
    passages: list[Any] = []
    missing: list[str] = []
    for uid in dict.fromkeys(unit_ids):
        v = engine.unit(uid, asof)
        if v is None:
            missing.append(uid)
            continue
        passages.append(Passage(unit_id=v.unit_id, seq=v.seq, text=v.text, valid_from=v.valid_from,
                                valid_to=v.valid_to, certainty=v.certainty, stage="named", mark=f"t{len(passages) + 1}"))
    if not passages:
        return {"claims": [], "missing": missing}
    if not _MARK_RE.search(text):
        marks = "".join(f"[{p.mark}]" for p in passages)
        parts = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
        text = " ".join(f"{s} {marks}" for s in parts)
    claims = engine.verify(text, passages, asof)
    by_mark = {p.mark: p for p in passages}
    return {"claims": [claim_dict(c, by_mark) for c in claims], "missing": missing}


# ------------------------------------------------------------------ server


class McpEdge:
    """Handles one JSON-RPC message at a time. ``handle_line`` is the whole protocol."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        domain: str | None = None,
        allow_ingest: bool = False,
        model: str | None = None,
        budget_usd: float | None = None,
        engine: Any = None,
        llm: Any = None,
        max_calls_per_minute: int = DEFAULT_CALLS_PER_MINUTE,
        clock: Callable[[], float] = time.monotonic,
    ):
        if model is not None and (budget_usd is None or budget_usd <= 0):
            raise ValueError("--model requires a positive --budget")
        self.db_path = str(db_path)
        self.domain = domain  # None: the domain stored in the database
        self.allow_ingest = allow_ingest
        self.model = model
        self.budget_usd = budget_usd
        self._engine = engine
        self._llm = llm  # a BudgetedLLM when a real model is used
        self.limiter = RateLimiter(max_calls_per_minute, 60.0, clock)
        self.legacy_version: str | None = None

    # ---- engine (lazy)

    def _get_engine(self) -> Any:
        if self._engine is None:
            self._engine = self._open_engine(resolve_domain(self.db_path, self.domain))
        return self._engine

    def _open_engine(self, domain: str) -> Any:
        from .engine import Engine
        from .fakes import EchoLLM, HashEmbedder, OverlapReranker, RuleEntailer

        llm = self._llm
        if llm is None:
            if self.model:
                from .llm import AnthropicLLM, BudgetedLLM

                llm = self._llm = BudgetedLLM(AnthropicLLM(self.model), float(self.budget_usd))
            else:
                llm = EchoLLM()
        return Engine.open(self.db_path, domain, llm=llm, embedder=HashEmbedder(), reranker=OverlapReranker(),
                           entailer=RuleEntailer())

    def tools(self) -> list[dict[str, Any]]:
        return TOOLS + ([INGEST_TOOL] if self.allow_ingest else [])

    def close(self) -> None:
        if self._engine is not None:
            try:
                self._engine.close()
            finally:
                self._engine = None

    # ---- framing

    def handle_line(self, line: str | bytes) -> str | None:
        """Process one message; return the response line (no newline) or None for notifications."""
        if isinstance(line, bytes):
            if len(line) > MAX_LINE_BYTES:
                return self._error_line(None, INVALID_REQUEST, f"message exceeds {MAX_LINE_BYTES} bytes")
            try:
                line = line.decode("utf-8")
            except UnicodeDecodeError:
                return self._error_line(None, PARSE_ERROR, "Parse error: message is not UTF-8")
        elif len(line.encode("utf-8", "surrogatepass")) > MAX_LINE_BYTES:
            return self._error_line(None, INVALID_REQUEST, f"message exceeds {MAX_LINE_BYTES} bytes")
        if not line.strip():
            return None
        try:
            msg = _loads(line)
        except (ValueError, RecursionError):
            return self._error_line(None, PARSE_ERROR, "Parse error")
        return self.handle_message(msg)

    def handle_message(self, msg: Any) -> str | None:
        if isinstance(msg, list):
            return self._error_line(None, INVALID_REQUEST, "JSON-RPC batches are not supported by MCP")
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            return self._error_line(None, INVALID_REQUEST, "Invalid Request: expected a JSON-RPC 2.0 object")
        if not _depth_ok(msg, MAX_DEPTH + 4):
            return self._error_line(None, INVALID_REQUEST, "Invalid Request: nesting too deep")
        method = msg.get("method")
        if not isinstance(method, str):
            if "method" not in msg and ("result" in msg or "error" in msg):
                return None
            return self._error_line(_safe_id(msg), INVALID_REQUEST, "Invalid Request: method must be a string")
        is_notification = "id" not in msg
        req_id = msg.get("id")
        if not is_notification and (isinstance(req_id, bool) or not isinstance(req_id, (str, int))):
            return self._error_line(None, INVALID_REQUEST, "Invalid Request: id must be a string or integer")
        params = msg.get("params", {})
        if not isinstance(params, dict):
            if is_notification:
                return None
            return self._error_line(req_id, INVALID_PARAMS, "params must be an object")
        if is_notification:
            return None
        try:
            result = self._dispatch(method, params)
        except _RpcError as e:
            return self._error_line(req_id, e.code, e.message, e.data)
        except Exception:  # never leak internals to an untrusted client
            print("heuresis.mcp_edge: internal error", file=sys.stderr)
            return self._error_line(req_id, INTERNAL_ERROR, "Internal error")
        return _dump({"jsonrpc": "2.0", "id": req_id, "result": result})

    # ---- dispatch

    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        meta = params.get("_meta")
        modern = isinstance(meta, dict) and META_VERSION in meta
        if modern:
            self._check_modern_meta(meta)
        elif method == "initialize":
            return self._initialize(params)
        elif self.legacy_version is None:
            raise _RpcError(
                INVALID_PARAMS,
                f"missing required _meta field {META_VERSION}: this server speaks MCP {MODERN_VERSION} "
                f"per request, or send initialize for one of {', '.join(SUPPORTED_LEGACY)}",
                {"supported": list(SUPPORTED_MODERN), "legacy": list(SUPPORTED_LEGACY)},
            )

        if method == "server/discover":
            return self._result({"supportedVersions": list(SUPPORTED_MODERN), "capabilities": {"tools": {}},
                                 "instructions": INSTRUCTIONS, "ttlMs": 3_600_000, "cacheScope": "public"})
        if method == "tools/list":
            return self._result({"tools": self.tools(), "ttlMs": 3_600_000, "cacheScope": "public"})
        if method == "tools/call":
            return self._result(self._call_tool(params))
        if method == "ping" and not modern:
            return {}
        if method == "initialize":
            raise _RpcError(METHOD_NOT_FOUND, f"initialize is not part of MCP {MODERN_VERSION}")
        raise _RpcError(METHOD_NOT_FOUND, f"Method not found: {method[:100]}")

    def _check_modern_meta(self, meta: dict[str, Any]) -> None:
        version = meta.get(META_VERSION)
        if not isinstance(version, str):
            raise _RpcError(INVALID_PARAMS, f"{META_VERSION} must be a string")
        if version not in SUPPORTED_MODERN:
            raise _RpcError(UNSUPPORTED_PROTOCOL_VERSION, "Unsupported protocol version",
                            {"supported": list(SUPPORTED_MODERN), "requested": version[:64]})
        if not isinstance(meta.get(META_CLIENT_CAPS), dict):
            raise _RpcError(INVALID_PARAMS, f"missing required _meta field {META_CLIENT_CAPS}")

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_LEGACY else SUPPORTED_LEGACY[0]
        self.legacy_version = version
        return {"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS}

    @staticmethod
    def _result(body: dict[str, Any]) -> dict[str, Any]:
        return {"resultType": "complete", **body, "_meta": {META_SERVER_INFO: SERVER_INFO}}

    # ---- tools

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        known = [t["name"] for t in self.tools()]
        if not isinstance(name, str) or name not in known:
            shown = name[:100] if isinstance(name, str) else repr(type(name).__name__)
            raise _RpcError(INVALID_PARAMS, f"Unknown tool: {shown}")
        args = params.get("arguments", {})
        if not isinstance(args, dict):
            raise _RpcError(INVALID_PARAMS, "arguments must be an object")
        if not self.limiter.allow():
            return _tool_error("RateLimited", "too many tool calls; try again later")
        try:
            return getattr(self, "_tool_" + name)(args)
        except ToolInputError as e:
            return _tool_error("InvalidArguments", str(e))
        except Exception as e:
            kind = type(e).__name__
            if kind == "BudgetExceeded":
                return _tool_error("BudgetExhausted", str(e))
            if kind == "LLMError":
                return _tool_error("ModelError", "the model call failed")
            print(f"heuresis.mcp_edge: tool {name} failed: {kind}", file=sys.stderr)
            return _tool_error("EngineError", f"{name} failed ({kind})")

    @staticmethod
    def _asof(args: Mapping[str, Any], with_recorded: bool = False) -> Any:
        from .model import AsOf

        valid = _check_date("as_of", args["as_of"]) if "as_of" in args else None
        recorded = _check_ts("recorded", args["recorded"]) if with_recorded and "recorded" in args else None
        return AsOf(valid=valid, recorded=recorded)

    def _tool_ask(self, args: dict[str, Any]) -> dict[str, Any]:
        _only_keys(args, ("question", "as_of", "recorded", "sources", "budget_usd"))
        _require(args, "question")
        question = _check_text("question", args["question"], MAX_QUESTION_CHARS, min_chars=1)
        asof = self._asof(args, with_recorded=True)
        sources = _check_ids("sources", args["sources"], MAX_SOURCES) if "sources" in args else []
        budget = None
        if "budget_usd" in args:
            b = args["budget_usd"]
            if isinstance(b, bool) or not isinstance(b, (int, float)) or not (0 < b <= MAX_BUDGET_USD) or b != b:
                raise ToolInputError(f"budget_usd must be a number in (0, {MAX_BUDGET_USD}]")
            budget = float(b)
        if self.model:
            llm = self._llm
            if llm is not None and llm.spent >= llm.cap_usd:
                return _tool_error("BudgetExhausted",
                                   f"the server's budget of ${llm.cap_usd:.4f} is spent; no further ask is served")
            if llm is not None:
                budget = min(budget, llm.remaining) if budget is not None else llm.remaining
        from .model import Scope

        engine = self._get_engine()
        ans = engine.ask(question, as_of=asof, scope=Scope(source_ids=tuple(sources)) if sources else None,
                         budget_usd=budget)
        data = {"ok": True, **answer_dict(ans)}
        if self.model and self._llm is not None:
            data["server_budget"] = {"cap_usd": self._llm.cap_usd, "spent_usd": self._llm.spent,
                                     "remaining_usd": self._llm.remaining}
        return _tool_ok(data)

    def _tool_search(self, args: dict[str, Any]) -> dict[str, Any]:
        _only_keys(args, ("question", "as_of", "k"))
        _require(args, "question")
        question = _check_text("question", args["question"], MAX_QUESTION_CHARS, min_chars=1)
        asof = self._asof(args)
        k = args.get("k", 10)
        if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= MAX_K:
            raise ToolInputError(f"k must be an integer 1..{MAX_K}")
        passages = self._get_engine().search(question, as_of=asof, k=k)
        return _tool_ok({"ok": True, "passages": [passage_dict(p) for p in passages]})

    def _tool_verify(self, args: dict[str, Any]) -> dict[str, Any]:
        _only_keys(args, ("text", "unit_ids", "as_of"))
        _require(args, "text", "unit_ids")
        text = _check_text("text", args["text"], MAX_TEXT_CHARS, min_chars=1, multiline=True)
        ids = _check_ids("unit_ids", args["unit_ids"], MAX_UNIT_IDS, min_items=1)
        as_of = _check_date("as_of", args["as_of"]) if "as_of" in args else None
        res = verify_units(self._get_engine(), text, ids, as_of)
        if not res["claims"]:
            return _tool_error("NotFound", "none of the named units is in force at that date", {"missing": res["missing"]})
        return _tool_ok({"ok": True, **res})

    def _tool_get_unit(self, args: dict[str, Any]) -> dict[str, Any]:
        _only_keys(args, ("unit_id", "as_of"))
        _require(args, "unit_id")
        uid = _check_text("unit_id", args["unit_id"], MAX_ID_CHARS, min_chars=1)
        asof = self._asof(args)
        v = self._get_engine().unit(uid, asof)
        if v is None:
            return _tool_error("NotFound", "no such unit, or it is not in force at that date")
        return _tool_ok({"ok": True, "unit": version_dict(v)})

    def _tool_ingest(self, args: dict[str, Any]) -> dict[str, Any]:
        _only_keys(args, ("path", "domain"))
        _require(args, "path")
        path = _check_text("path", args["path"], MAX_PATH_CHARS, min_chars=1)
        from .domains import available

        domain = _check_text("domain", args["domain"] if "domain" in args else resolve_domain(self.db_path, self.domain), 64, min_chars=1)
        if domain not in available():
            raise ToolInputError(f"domain must be one of {', '.join(available())}")
        p = Path(path).expanduser()
        if not p.exists():
            return _tool_error("NotFound", "path does not exist")
        eng = self._open_engine(domain)
        try:
            counts = eng.ingest(str(p))
            eng.index()
        finally:
            eng.close()
        return _tool_ok({"ok": True, "domain": domain, "counts": counts if isinstance(counts, dict) else {}})

    # ---- output

    @staticmethod
    def _error_line(req_id: Any, code: int, message: str, data: Any = None) -> str:
        err: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return _dump({"jsonrpc": "2.0", "id": req_id, "error": err})

    # ---- stdio loop

    def serve(self, instream: BinaryIO, outstream: BinaryIO) -> None:
        """Read newline-delimited messages until EOF; write one response line per request."""
        while True:
            raw = instream.readline(MAX_LINE_BYTES + 1)
            if not raw:
                return
            if len(raw) > MAX_LINE_BYTES and not raw.endswith(b"\n"):
                while True:
                    rest = instream.readline(MAX_LINE_BYTES)
                    if not rest or rest.endswith(b"\n"):
                        break
                out = self._error_line(None, INVALID_REQUEST, f"message exceeds {MAX_LINE_BYTES} bytes")
            else:
                out = self.handle_line(raw.rstrip(b"\r\n"))
            if out is not None:
                outstream.write(out.encode("utf-8") + b"\n")
                outstream.flush()


def _safe_id(msg: dict[str, Any]) -> Any:
    i = msg.get("id")
    return i if isinstance(i, (str, int)) and not isinstance(i, bool) else None


def _dump(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _tool_ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": _dump(data)}], "structuredContent": data, "isError": False}


def _tool_error(kind: str, message: str, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = {**(extra or {}), "ok": False, "error": {"kind": kind, "message": message}}
    return {"content": [{"type": "text", "text": _dump(data)}], "structuredContent": data, "isError": True}


# ------------------------------------------------------------------ entry point


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m heuresis.mcp_edge", description="heuresis MCP edge (stdio)")
    ap.add_argument("--db", required=True, help="path to the heuresis database; the only store this server opens")
    ap.add_argument("--domain", default=None, help="domain plug-in (default: the one stored in the database, else text)")
    ap.add_argument("--allow-ingest", action="store_true", help="expose the ingest tool (it takes a file path)")
    ap.add_argument("--model", default=None, help="use this real model for ask (needs --budget); default is offline")
    ap.add_argument("--budget", type=float, default=None, help="USD cap shared by every ask for the life of this process")
    ap.add_argument("--max-calls-per-minute", type=int, default=DEFAULT_CALLS_PER_MINUTE)
    args = ap.parse_args(argv)

    if args.model and (args.budget is None or args.budget <= 0):
        print("error: --model requires --budget USD greater than zero", file=sys.stderr)
        return 2
    if args.budget is not None and not args.model:
        print("error: --budget only applies together with --model", file=sys.stderr)
        return 2
    if args.max_calls_per_minute < 1:
        print("error: --max-calls-per-minute must be at least 1", file=sys.stderr)
        return 2
    from .domains import available

    if args.domain is not None and args.domain not in available():
        print(f"error: unknown domain {args.domain!r}; available: {', '.join(available())}", file=sys.stderr)
        return 2
    path = Path(args.db).expanduser().resolve()
    if not path.parent.is_dir():
        print(f"error: directory {path.parent} does not exist", file=sys.stderr)
        return 2
    server = McpEdge(path, domain=args.domain, allow_ingest=args.allow_ingest, model=args.model,
                     budget_usd=args.budget, max_calls_per_minute=args.max_calls_per_minute)
    try:
        server.serve(sys.stdin.buffer, sys.stdout.buffer)
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
