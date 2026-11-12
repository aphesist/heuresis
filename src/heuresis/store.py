"""SQLite store: a time-versioned corpus that filters by validity before it searches.

Events are the source of truth. ``rebuild`` replays them per unit into the
``versions`` table (with an FTS5 index over title and text). Every search applies
the as-of and scope filters inside the SQL, so a version that is not in force at
the date can never reach the ranking step.

Choices where the contract is silent:

* Event replay order is ``(date, recorded_at, id)``. ``seq`` is 0-based and
  follows that order; zero-length versions (closed on the day they opened) are
  dropped before numbering.
* ``add`` with changed sources or units updates them; only events are immutable.
* Query methods rebuild first when events or units were added since the last
  ``rebuild``, so results are never stale.
* ``recorded`` comparisons are prefix based: a date-only ``recorded`` covers the
  whole day.
* A corrected version carries the correction's ``event_id`` and ``recorded_at``
  and keeps the certainty and axes of the event that opened it.
* Vectors are keyed by (embedder, unit, seq, text hash), so they survive a
  rebuild that does not change that version's text.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Sequence

import numpy as np

from .model import OPS, AsOf, COVERAGE_MAX, Edge, Event, Passage, Scope, Source, Unit, Version

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_MAX_QUERY_TOKENS = 64
_TOKENIZER = "unicode61 remove_diacritics 2"

_VERSION_COLS = (
    "id INTEGER PRIMARY KEY, unit_id TEXT NOT NULL, seq INTEGER NOT NULL, "
    "text TEXT NOT NULL, valid_from TEXT, valid_to TEXT, event_id TEXT NOT NULL, "
    "recorded_at TEXT NOT NULL, certainty TEXT NOT NULL, axes TEXT NOT NULL, "
    "text_hash TEXT NOT NULL, title TEXT NOT NULL, source_id TEXT NOT NULL, "
    "ukind TEXT NOT NULL"
)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, authority INTEGER NOT NULL,
    coverage INTEGER NOT NULL, licence TEXT, meta TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS units (
    id TEXT PRIMARY KEY, source_id TEXT NOT NULL, kind TEXT NOT NULL,
    parent_id TEXT, title TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY, unit_id TEXT NOT NULL, op TEXT NOT NULL, date TEXT NOT NULL,
    text TEXT, recorded_at TEXT NOT NULL, evidence TEXT NOT NULL,
    certainty TEXT NOT NULL, axes TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS events_unit ON events(unit_id);
CREATE INDEX IF NOT EXISTS events_rec ON events(recorded_at);
CREATE TABLE IF NOT EXISTS edges (
    key TEXT PRIMARY KEY, src TEXT NOT NULL, dst TEXT NOT NULL, type TEXT NOT NULL,
    valid_from TEXT, valid_to TEXT);
CREATE INDEX IF NOT EXISTS edges_src ON edges(src);
CREATE TABLE IF NOT EXISTS versions ({_VERSION_COLS});
CREATE UNIQUE INDEX IF NOT EXISTS versions_unit_seq ON versions(unit_id, seq);
CREATE INDEX IF NOT EXISTS versions_source ON versions(source_id);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    title, text, content='versions', content_rowid='id', tokenize='{_TOKENIZER}');
CREATE TABLE IF NOT EXISTS vec (
    embedder_id TEXT NOT NULL, unit_id TEXT NOT NULL, seq INTEGER NOT NULL,
    text_hash TEXT NOT NULL, dim INTEGER NOT NULL, blob BLOB NOT NULL,
    PRIMARY KEY (embedder_id, unit_id, seq, text_hash));
"""


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _known(recorded_at: str, recorded: str) -> bool:
    """True when something recorded at ``recorded_at`` was known by ``recorded``."""
    return recorded_at[: len(recorded)] <= recorded


def fts_query(text: str) -> str:
    """Turn free text into a safe FTS5 query: quoted tokens joined by OR."""
    seen: dict[str, None] = {}
    for tok in _TOKEN.findall(text or ""):
        seen.setdefault(tok.lower(), None)
        if len(seen) >= _MAX_QUERY_TOKENS:
            break
    return " OR ".join(f'"{t}"' for t in seen)


# ----------------------------------------------------------------------------
# Replay
# ----------------------------------------------------------------------------


@dataclass
class _Seg:
    valid_from: str
    valid_to: str | None
    text: str
    event_id: str
    recorded_at: str
    certainty: str
    axes: dict[str, str]


def _describe(e: Event) -> str:
    return f"event {e.id!r} (unit {e.unit_id!r}, op {e.op!r}, date {e.date!r})"


def _in_force(segs: list[_Seg], d: str) -> _Seg | None:
    for s in reversed(segs):
        if s.valid_from <= d and (s.valid_to is None or d < s.valid_to):
            return s
    return None


def _close(segs: list[_Seg], seg: _Seg, d: str) -> None:
    seg.valid_to = d
    if seg.valid_from == d:  # closed the day it opened: empty interval
        segs.remove(seg)


def _replay(events: Sequence[Event]) -> list[_Seg]:
    """Replay the events of one unit, already sorted. Raises ValueError."""
    segs: list[_Seg] = []
    repealed_text: str | None = None
    for e in events:
        if e.op not in OPS:
            raise ValueError(f"{_describe(e)}: unknown op")
        d = e.date
        cur = _in_force(segs, d)
        if e.op in ("create", "replace", "correct") and e.text is None:
            raise ValueError(f"{_describe(e)}: op requires text")
        if e.op == "create":
            if segs:
                raise ValueError(f"{_describe(e)}: unit already created")
            segs.append(_Seg(d, None, e.text, e.id, e.recorded_at, e.certainty, dict(e.axes)))
        elif e.op == "replace":
            if cur is None:
                raise ValueError(f"{_describe(e)}: no version in force to replace")
            _close(segs, cur, d)
            segs.append(_Seg(d, None, e.text, e.id, e.recorded_at, e.certainty, dict(e.axes)))
        elif e.op == "repeal":
            if cur is None:
                raise ValueError(f"{_describe(e)}: no version in force to repeal")
            repealed_text = cur.text
            _close(segs, cur, d)
        elif e.op == "restore":
            if cur is not None:
                raise ValueError(f"{_describe(e)}: unit is in force, nothing to restore")
            text = e.text if e.text is not None else repealed_text
            if text is None:
                raise ValueError(f"{_describe(e)}: nothing to restore")
            segs.append(_Seg(d, None, text, e.id, e.recorded_at, e.certainty, dict(e.axes)))
        else:  # correct
            if cur is None:
                raise ValueError(f"{_describe(e)}: no version in force to correct")
            cur.text = e.text
            cur.event_id = e.id
            cur.recorded_at = e.recorded_at
    return segs


def _event_key(e: Event) -> tuple[str, str, str]:
    return (e.date, e.recorded_at, e.id)


def _replay_all(
    events: Sequence[Event], units: dict[str, Unit], strict: bool
) -> list[tuple]:
    """Version rows (without id) for every unit, ordered by (unit_id, seq).

    With ``strict`` False a unit whose events do not replay is skipped.
    """
    by_unit: dict[str, list[Event]] = {}
    for e in events:
        by_unit.setdefault(e.unit_id, []).append(e)
    rows: list[tuple] = []
    for unit_id in sorted(by_unit):
        evs = sorted(by_unit[unit_id], key=_event_key)
        unit = units.get(unit_id)
        if unit is None:
            if strict:
                raise ValueError(f"{_describe(evs[0])}: unknown unit")
            continue
        try:
            segs = _replay(evs)
        except ValueError:
            if strict:
                raise
            continue
        for seq, s in enumerate(segs):
            rows.append(
                (unit_id, seq, s.text, s.valid_from, s.valid_to, s.event_id, s.recorded_at,
                 s.certainty, json.dumps(s.axes, sort_keys=True), _hash(s.text),
                 unit.title, unit.source_id, unit.kind)
            )
    return rows


_INSERT_VERSION = (
    "INSERT INTO {t} (id, unit_id, seq, text, valid_from, valid_to, event_id, recorded_at, "
    "certainty, axes, text_hash, title, source_id, ukind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)


# ----------------------------------------------------------------------------
# Store
# ----------------------------------------------------------------------------


class Store:
    def __init__(self, path: str):
        self.path = path
        self._time_profile: dict | None = None
        self._con = sqlite3.connect(path)
        self._con.row_factory = sqlite3.Row
        if path != ":memory:":
            self._con.execute("PRAGMA journal_mode=WAL")
            self._con.execute("PRAGMA synchronous=NORMAL")
        self._con.executescript(_SCHEMA)
        self._con.commit()

    # -- writing -------------------------------------------------------------

    def add(self, sources=(), units=(), events=(), edges=()) -> None:
        """Insert corpus objects. Idempotent by id; an event id seen before with
        different content raises ValueError and nothing from the call is kept."""
        with self._con:
            for s in sources:
                if self.get_source(s.id) != s:
                    self._con.execute(
                        "INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?)",
                        (s.id, s.kind, s.authority, s.coverage, s.licence,
                         json.dumps(s.meta, sort_keys=True)),
                    )
            for u in units:
                row = self._con.execute("SELECT * FROM units WHERE id=?", (u.id,)).fetchone()
                old = (
                    Unit(row["id"], row["source_id"], row["kind"], row["parent_id"], row["title"])
                    if row else None
                )
                if old != u:
                    self._con.execute(
                        "INSERT OR REPLACE INTO units VALUES (?,?,?,?,?)",
                        (u.id, u.source_id, u.kind, u.parent_id, u.title),
                    )
                    self._set_dirty()
            for e in events:
                old_e = self._get_event(e.id)
                if old_e is not None:
                    if old_e != e:
                        raise ValueError(
                            f"event {e.id!r} was already recorded with different content"
                        )
                    continue
                self._con.execute(
                    "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                    (e.id, e.unit_id, e.op, e.date, e.text, e.recorded_at, e.evidence,
                     e.certainty, json.dumps(e.axes, sort_keys=True)),
                )
                self._set_dirty()
            for g in edges:
                key = json.dumps([g.src, g.dst, g.type, g.valid_from, g.valid_to])
                self._con.execute(
                    "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?,?)",
                    (key, g.src, g.dst, g.type, g.valid_from, g.valid_to),
                )

    def rebuild(self) -> None:
        """Replay all events into the versions table and the FTS index."""
        units = {u.id: u for u in self._all_units()}
        rows = _replay_all(self._all_events(), units, strict=True)  # may raise
        with self._con:
            self._con.execute("DELETE FROM versions")
            self._con.executemany(
                _INSERT_VERSION.format(t="versions"),
                [(i + 1, *r) for i, r in enumerate(rows)],
            )
            self._con.execute("INSERT INTO fts(fts) VALUES('rebuild')")
            self._con.execute("INSERT OR REPLACE INTO meta VALUES ('dirty', '0')")
        self._time_profile = None

    def time_profile(self) -> dict:
        """How much history the corpus holds: ``{"versioned": bool, "min_valid_from":
        str | None, "max_valid_from": str | None}``. ``versioned`` is true when any unit
        has more than one version or any version has a ``valid_to``. Cached until the
        next rebuild."""
        self._ensure_built()
        if self._time_profile is None:
            multi = self._con.execute(
                "SELECT 1 FROM versions GROUP BY unit_id HAVING COUNT(*) > 1 LIMIT 1"
            ).fetchone()
            closed = self._con.execute(
                "SELECT 1 FROM versions WHERE valid_to IS NOT NULL LIMIT 1"
            ).fetchone()
            lo, hi = self._con.execute(
                "SELECT MIN(valid_from), MAX(valid_from) FROM versions"
            ).fetchone()
            self._time_profile = {"versioned": multi is not None or closed is not None,
                                  "min_valid_from": lo, "max_valid_from": hi}
        return dict(self._time_profile)

    def put_vectors(self, embedder_id: str, rows: list[tuple[str, int, np.ndarray]]) -> None:
        self._ensure_built()
        with self._con:
            for unit_id, seq, vec in rows:
                h = self._con.execute(
                    "SELECT text_hash FROM versions WHERE unit_id=? AND seq=?", (unit_id, seq)
                ).fetchone()
                if h is None:
                    raise ValueError(f"no version ({unit_id!r}, {seq}) to attach a vector to")
                v = np.ascontiguousarray(np.asarray(vec, dtype=np.float32).ravel())
                self._con.execute(
                    "INSERT OR REPLACE INTO vec VALUES (?,?,?,?,?,?)",
                    (embedder_id, unit_id, seq, h["text_hash"], int(v.size), v.tobytes()),
                )

    # -- reading: versions ---------------------------------------------------

    def versions(self, unit_id: str, as_of: AsOf | None = None) -> list[Version]:
        """Every version of the unit as known at ``as_of.recorded`` (None = now)."""
        rec = as_of.recorded if as_of else None
        if self._needs_history(rec):
            units = {u.id: u for u in self._all_units() if u.id == unit_id}
            evs = [
                e for e in self._events_of(unit_id) if _known(e.recorded_at, rec)  # type: ignore[arg-type]
            ]
            rows = _replay_all(evs, units, strict=False)
            return [self._row_to_version(r) for r in rows]
        self._ensure_built()
        cur = self._con.execute(
            "SELECT * FROM versions WHERE unit_id=? ORDER BY seq", (unit_id,)
        )
        return [self._row_to_version(r) for r in cur]

    def text_at(self, unit_id: str, as_of: AsOf) -> Version | None:
        d = as_of.valid or _today()
        for v in self.versions(unit_id, as_of):
            if (v.valid_from is None or v.valid_from <= d) and (
                v.valid_to is None or d < v.valid_to
            ):
                return v
        return None

    # -- reading: search -----------------------------------------------------

    def lexical(self, text: str, as_of: AsOf, scope: Scope, k: int) -> list[Passage]:
        q = fts_query(text)
        if not q or k <= 0:
            return []
        with self._view(as_of) as (vt, ft):
            where, params = self._filters(as_of, scope)
            sql = (
                f"SELECT {_PASSAGE_COLS}, bm25({ft}, 2.0, 1.0) AS rank "
                f"FROM {ft} JOIN {vt} v ON v.id = {ft}.rowid "
                f"LEFT JOIN sources s ON s.id = v.source_id "
                f"WHERE {ft} MATCH :q AND {where} "
                f"ORDER BY rank, v.unit_id, v.seq LIMIT :k"
            )
            try:
                rows = self._con.execute(sql, {**params, "q": q, "k": k}).fetchall()
            except sqlite3.OperationalError:
                return []
            return [self._row_to_passage(r, -r["rank"], "lexical") for r in rows]

    def dense(
        self, vec: np.ndarray, embedder_id: str, as_of: AsOf, scope: Scope, k: int
    ) -> list[Passage]:
        q = np.asarray(vec, dtype=np.float32).ravel()
        if k <= 0 or q.size == 0:
            return []
        with self._view(as_of) as (vt, _ft):
            where, params = self._filters(as_of, scope)
            sql = (
                f"SELECT {_PASSAGE_COLS}, vec.blob AS blob "
                f"FROM {vt} v JOIN vec ON vec.embedder_id = :emb AND vec.unit_id = v.unit_id "
                f"AND vec.seq = v.seq AND vec.text_hash = v.text_hash AND vec.dim = :dim "
                f"LEFT JOIN sources s ON s.id = v.source_id "
                f"WHERE {where} ORDER BY v.unit_id, v.seq"
            )
            rows = self._con.execute(
                sql, {**params, "emb": embedder_id, "dim": int(q.size)}
            ).fetchall()
            if not rows:
                return []
            mat = np.frombuffer(b"".join(r["blob"] for r in rows), dtype=np.float32)
            mat = mat.reshape(len(rows), q.size)
            scores = mat @ q
            order = np.argsort(-scores, kind="stable")[:k]
            return [self._row_to_passage(rows[i], float(scores[i]), "dense") for i in order]

    def neighbours(
        self, unit_ids: list[str], as_of: AsOf, types: tuple[str, ...] = ()
    ) -> list[Passage]:
        ids = list(dict.fromkeys(unit_ids))
        if not ids:
            return []
        out: list[Passage] = []
        seen: set[tuple[str, int]] = set()
        with self._view(as_of) as (vt, _ft):
            _, params = self._filters(as_of, Scope())
            vwhere = "(v.valid_from IS NULL OR v.valid_from <= :d) AND (v.valid_to IS NULL OR :d < v.valid_to)"
            for i in range(0, len(ids), 500):
                chunk = ids[i : i + 500]
                p: dict[str, Any] = {"d": params["d"]}
                marks = []
                for j, u in enumerate(chunk):
                    p[f"s{j}"] = u
                    marks.append(f":s{j}")
                tclause = ""
                if types:
                    tm = []
                    for j, t in enumerate(types):
                        p[f"t{j}"] = t
                        tm.append(f":t{j}")
                    tclause = f"AND e.type IN ({','.join(tm)}) "
                sql = (
                    f"SELECT DISTINCT {_PASSAGE_COLS} FROM edges e "
                    f"JOIN {vt} v ON v.unit_id = e.dst "
                    f"LEFT JOIN sources s ON s.id = v.source_id "
                    f"WHERE e.src IN ({','.join(marks)}) {tclause}"
                    f"AND (e.valid_from IS NULL OR e.valid_from <= :d) "
                    f"AND (e.valid_to IS NULL OR :d < e.valid_to) AND {vwhere} "
                    f"ORDER BY v.unit_id, v.seq"
                )
                for r in self._con.execute(sql, p):
                    key = (r["unit_id"], r["seq"])
                    if key not in seen:
                        seen.add(key)
                        out.append(self._row_to_passage(r, 1.0, "expand"))
        return out

    # -- reading: misc -------------------------------------------------------

    def missing_vectors(self, embedder_id: str) -> list[tuple[str, int, str]]:
        self._ensure_built()
        cur = self._con.execute(
            "SELECT v.unit_id, v.seq, v.text FROM versions v LEFT JOIN vec ON "
            "vec.embedder_id = ? AND vec.unit_id = v.unit_id AND vec.seq = v.seq "
            "AND vec.text_hash = v.text_hash WHERE vec.unit_id IS NULL "
            "ORDER BY v.unit_id, v.seq",
            (embedder_id,),
        )
        return [(r["unit_id"], r["seq"], r["text"]) for r in cur]

    def meta_get(self, key: str) -> str | None:
        """Read a caller-owned value from the small key-value table."""
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        r = self._con.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return None if r is None else r["value"]

    def meta_set(self, key: str, value: str) -> None:
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        with self._con:
            self._con.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, value))

    def lexical_any_date(self, text: str, scope: Scope, k: int) -> list[Passage]:
        """Lexical search that ignores validity. For diagnosing an abstention
        only (is there text that is just not in force?); never use it to answer."""
        q = fts_query(text)
        if not q or k <= 0:
            return []
        self._ensure_built()
        clauses, params = self._scope_filters(scope)
        where = " AND ".join(clauses) or "1=1"
        sql = (
            f"SELECT {_PASSAGE_COLS}, bm25(fts, 2.0, 1.0) AS rank "
            "FROM fts JOIN versions v ON v.id = fts.rowid "
            "LEFT JOIN sources s ON s.id = v.source_id "
            f"WHERE fts MATCH :q AND {where} "
            "ORDER BY rank, v.unit_id, v.seq LIMIT :k"
        )
        try:
            rows = self._con.execute(sql, {**params, "q": q, "k": k}).fetchall()
        except sqlite3.OperationalError:
            return []
        return [self._row_to_passage(r, -r["rank"], "lexical") for r in rows]

    def get_source(self, source_id: str) -> Source | None:
        r = self._con.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if r is None:
            return None
        return Source(
            r["id"], r["kind"], r["authority"], r["coverage"], r["licence"], json.loads(r["meta"])
        )

    def sources(self, kind: str | None = None) -> list[Source]:
        """Every source (optionally of one kind), in id order. Read-only; used by domain
        plug-ins that need to know which sources a corpus holds."""
        q, args = "SELECT * FROM sources", ()
        if kind is not None:
            q, args = q + " WHERE kind=?", (kind,)
        return [Source(r["id"], r["kind"], r["authority"], r["coverage"], r["licence"],
                       json.loads(r["meta"]))
                for r in self._con.execute(q + " ORDER BY id", args)]

    def has_unit(self, unit_id: str) -> bool:
        """True when a unit with this id exists (whatever its versions)."""
        return self._con.execute("SELECT 1 FROM units WHERE id=?", (unit_id,)).fetchone() is not None

    def stats(self) -> dict:
        def n(t: str) -> int:
            return self._con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

        return {t: n(t) for t in ("sources", "units", "events", "versions", "edges")}

    def close(self) -> None:
        self._con.close()

    # -- internals -----------------------------------------------------------

    def _set_dirty(self) -> None:
        self._con.execute("INSERT OR REPLACE INTO meta VALUES ('dirty', '1')")

    def _ensure_built(self) -> None:
        r = self._con.execute("SELECT value FROM meta WHERE key='dirty'").fetchone()
        if r is not None and r["value"] == "1":
            self.rebuild()

    def _needs_history(self, recorded: str | None) -> bool:
        if not recorded:
            return False
        newest = self._con.execute("SELECT MAX(recorded_at) FROM events").fetchone()[0]
        return newest is not None and not _known(newest, recorded)

    def _all_units(self) -> list[Unit]:
        return [
            Unit(r["id"], r["source_id"], r["kind"], r["parent_id"], r["title"])
            for r in self._con.execute("SELECT * FROM units")
        ]

    @staticmethod
    def _to_event(r: sqlite3.Row) -> Event:
        return Event(
            r["id"], r["unit_id"], r["op"], r["date"], r["text"], r["recorded_at"],
            r["evidence"], r["certainty"], json.loads(r["axes"]),
        )

    def _get_event(self, event_id: str) -> Event | None:
        r = self._con.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return self._to_event(r) if r else None

    def _all_events(self) -> list[Event]:
        return [self._to_event(r) for r in self._con.execute("SELECT * FROM events")]

    def _events_of(self, unit_id: str) -> list[Event]:
        cur = self._con.execute("SELECT * FROM events WHERE unit_id=?", (unit_id,))
        return [self._to_event(r) for r in cur]

    @contextmanager
    def _view(self, as_of: AsOf) -> Iterator[tuple[str, str]]:
        """Yield (versions table, fts table) answering for ``as_of.recorded``."""
        if not self._needs_history(as_of.recorded):
            self._ensure_built()
            yield "versions", "fts"
            return
        rec = as_of.recorded
        units = {u.id: u for u in self._all_units()}
        events = [e for e in self._all_events() if _known(e.recorded_at, rec)]  # type: ignore[arg-type]
        rows = _replay_all(events, units, strict=False)
        con = self._con
        con.execute(f"CREATE TEMP TABLE versions_h ({_VERSION_COLS})")
        con.execute(
            f"CREATE VIRTUAL TABLE temp.fts_h USING fts5(title, text, tokenize='{_TOKENIZER}')"
        )
        try:
            con.executemany(
                _INSERT_VERSION.format(t="versions_h"),
                [(i + 1, *r) for i, r in enumerate(rows)],
            )
            con.execute(
                "INSERT INTO fts_h(rowid, title, text) SELECT id, title, text FROM versions_h"
            )
            yield "versions_h", "fts_h"
        finally:
            con.execute("DROP TABLE IF EXISTS temp.fts_h")
            con.execute("DROP TABLE IF EXISTS temp.versions_h")
            con.commit()

    @staticmethod
    def _scope_filters(scope: Scope) -> tuple[list[str], dict[str, Any]]:
        """SQL clauses and parameters that restrict a query to ``scope``."""
        params: dict[str, Any] = {}
        parts: list[str] = []
        if scope.source_ids:
            names = []
            for i, s in enumerate(scope.source_ids):
                params[f"src{i}"] = s
                names.append(f":src{i}")
            parts.append(f"v.source_id IN ({','.join(names)})")
        if scope.kinds:
            names = []
            for i, s in enumerate(scope.kinds):
                params[f"kind{i}"] = s
                names.append(f":kind{i}")
            parts.append(f"v.ukind IN ({','.join(names)})")
        if scope.unit_prefix:
            params["pfx"] = scope.unit_prefix
            params["pfxlen"] = len(scope.unit_prefix)
            parts.append("substr(v.unit_id, 1, :pfxlen) = :pfx")
        return parts, params

    @staticmethod
    def _filters(as_of: AsOf, scope: Scope) -> tuple[str, dict[str, Any]]:
        params: dict[str, Any] = {"d": as_of.valid or _today()}
        parts = [
            "(v.valid_from IS NULL OR v.valid_from <= :d)",
            "(v.valid_to IS NULL OR :d < v.valid_to)",
        ]
        scope_parts, scope_params = Store._scope_filters(scope)
        parts.extend(scope_parts)
        params.update(scope_params)
        return " AND ".join(parts), params

    @staticmethod
    def _row_to_version(r: Any) -> Version:
        if isinstance(r, sqlite3.Row):
            return Version(
                r["unit_id"], r["seq"], r["text"], r["valid_from"], r["valid_to"],
                r["event_id"], r["recorded_at"], r["certainty"], json.loads(r["axes"]),
            )
        # tuple from _replay_all: (unit_id, seq, text, vf, vt, event_id, rec, cert, axes, ...)
        return Version(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], json.loads(r[8]))

    @staticmethod
    def _row_to_passage(r: sqlite3.Row, score: float, stage: str) -> Passage:
        return Passage(
            unit_id=r["unit_id"], seq=r["seq"], text=r["text"], title=r["title"],
            source_id=r["source_id"], score=float(score), stage=stage,
            valid_from=r["valid_from"], valid_to=r["valid_to"],
            coverage=int(r["cov"]), certainty=r["certainty"],
        )


_PASSAGE_COLS = (
    "v.unit_id AS unit_id, v.seq AS seq, v.text AS text, v.title AS title, "
    f"v.source_id AS source_id, v.valid_from AS valid_from, v.valid_to AS valid_to, "
    f"v.certainty AS certainty, COALESCE(s.coverage, {COVERAGE_MAX}) AS cov"
)
