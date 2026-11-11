"""``sql``: one read-only SELECT against a SQLite file.

Args: ``{"db": path, "query": "SELECT ...", "max_rows": 50, "timeout_s": 2.0}``.

Safety layers: the file is opened with ``mode=ro``; the statement must start
with SELECT or WITH and be a single statement; a SQLite authorizer permits only
reads (anything else, including ATTACH, PRAGMA and writes, is denied); rows are
capped at ``max_rows`` (1..10000); a progress handler aborts after
``timeout_s`` seconds (0 < t <= 30).  ``value`` is
``{"columns": [...], "rows": [[...], ...], "truncated": bool}``; BLOBs are
returned as hex strings.
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from ..model import ToolResult

DEFAULT_MAX_ROWS = 50
DEFAULT_TIMEOUT_S = 2.0

_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    getattr(sqlite3, "SQLITE_RECURSIVE", 33),
}
_START = re.compile(r"(?is)\s*(select|with)\b")


class SqlError(ValueError):
    pass


def _authorizer(action, *_):
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


def _clean(v: Any) -> Any:
    return v.hex() if isinstance(v, (bytes, bytearray, memoryview)) else v


def run_query(db: Any, query: Any, max_rows: Any = None, timeout_s: Any = None) -> tuple[dict, list[str]]:
    if not isinstance(db, str) or not db:
        raise SqlError("'db' must be a path string")
    if not isinstance(query, str) or not query.strip():
        raise SqlError("'query' must be a non-empty string")
    max_rows = DEFAULT_MAX_ROWS if max_rows is None else max_rows
    timeout_s = DEFAULT_TIMEOUT_S if timeout_s is None else timeout_s
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or not 1 <= max_rows <= 10000:
        raise SqlError("'max_rows' must be an integer between 1 and 10000")
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not 0 < timeout_s <= 30:
        raise SqlError("'timeout_s' must be a number in (0, 30]")
    sql = query.strip()
    while sql.endswith(";"):
        sql = sql[:-1].rstrip()
    if not _START.match(sql):
        raise SqlError("only a single SELECT (or WITH ... SELECT) statement is allowed")
    path = Path(db)
    if not path.is_file():
        raise SqlError(f"database file not found: {db}")
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=timeout_s)
        conn.set_authorizer(_authorizer)
        deadline = time.monotonic() + timeout_s
        timed_out = False

        def progress() -> int:
            nonlocal timed_out
            if time.monotonic() > deadline:
                timed_out = True
                return 1
            return 0

        conn.set_progress_handler(progress, 1000)
        try:
            cur = conn.execute(sql)
            columns = [d[0] for d in cur.description or []]
            fetched = cur.fetchmany(max_rows + 1)
        except sqlite3.OperationalError as e:
            if timed_out:
                raise SqlError(f"time limit of {timeout_s} s exceeded") from None
            raise SqlError(f"sql error: {e}") from None
        except (sqlite3.Error, sqlite3.Warning) as e:
            raise SqlError(f"sql error: {e}") from None
    except sqlite3.Error as e:
        raise SqlError(f"cannot open database read-only: {e}") from None
    finally:
        if conn is not None:
            conn.close()
    truncated = len(fetched) > max_rows
    rows = [[_clean(v) for v in r] for r in fetched[:max_rows]]
    steps = [
        f"query: {sql}",
        f"returned {len(rows)} row(s) with columns {columns}" + (f", truncated at max_rows={max_rows}" if truncated else ""),
    ]
    return {"columns": columns, "rows": rows, "truncated": truncated}, steps


class SqlTool:
    name = "sql"
    description = (
        'Read-only SQLite. args: {"db": "path.sqlite", "query": "SELECT ...", "max_rows": 50 optional, '
        '"timeout_s": 2 optional}. One SELECT/WITH statement only.'
    )

    def run(self, mark: str, args: dict[str, Any]) -> ToolResult:
        a = dict(args) if isinstance(args, dict) else {}
        try:
            if not isinstance(args, dict):
                raise SqlError("args must be an object")
            value, steps = run_query(args.get("db"), args.get("query"), args.get("max_rows"), args.get("timeout_s"))
            return ToolResult(mark, self.name, a, True, value, steps)
        except SqlError as e:
            return ToolResult(mark, self.name, a, False, error=str(e))
        except Exception as e:
            return ToolResult(mark, self.name, a, False, error=f"internal error: {type(e).__name__}")
