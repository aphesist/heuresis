"""A SQLite file: one schema-card unit per table."""
from __future__ import annotations

import os
import re
import sqlite3

from ..model import Edge, Event, Source, Unit
from . import utc_date


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class TablesDomain:
    name = "tables"
    axes: tuple[str, ...] = ()

    def __init__(self):
        self._names: set[str] = set()
        self._db_path: str | None = None

    def read(self, path: str):
        db_path = os.path.abspath(path)
        db_name = os.path.splitext(os.path.basename(db_path))[0]
        date = utc_date(os.path.getmtime(db_path))
        source = Source(id=f"table:{db_name}", kind="tables", meta={"path": db_path})
        units: list[Unit] = []
        events: list[Event] = []
        names: set[str] = set()
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            for t in tables:
                cols = con.execute(f"PRAGMA table_info({_q(t)})").fetchall()
                n = con.execute(f"SELECT COUNT(*) FROM {_q(t)}").fetchone()[0]
                sample = con.execute(f"SELECT * FROM {_q(t)} LIMIT 3").fetchall()
                col_names = [c[1] for c in cols]
                names.add(t.lower())
                names.update(c.lower() for c in col_names)
                lines = [f"Table {t}", "Columns: " + ", ".join(
                    f"{c[1]} ({c[2] or 'any'})" for c in cols), f"Rows: {n}"]
                for i, row in enumerate(sample, 1):
                    lines.append(f"Sample {i}: " + ", ".join(
                        f"{c}={v!r}" for c, v in zip(col_names, row)))
                uid = f"table:{db_name}.{t}"
                units.append(Unit(id=uid, source_id=source.id, kind="schema", title=t))
                events.append(Event(id=f"ev:{uid}:create", unit_id=uid, op="create",
                                    date=date, text="\n".join(lines),
                                    recorded_at=date, evidence=db_path))
        finally:
            con.close()
        self._names = names
        self._db_path = db_path
        return [source], units, events, []

    def rules(self):
        def table_rule(text: str):
            words = set(re.findall(r"\w+", text.lower()))
            if self._names and words & self._names:
                return {"intent": "table"}
            return None

        return [table_rule]

    def tools(self):
        try:
            from .. import tools as _tools
        except Exception:
            return []
        try:
            return [t for t in _tools.default_tools() if getattr(t, "name", "") == "sql"]
        except Exception:
            return []

    def abstention_text(self, kind, query):
        return None
