"""A local git repository, read with read-only git commands."""
from __future__ import annotations

import datetime as _dt
import os
import subprocess

from ..model import Edge, Event, Source, Unit

MAX_BYTES = 200_000
_SEP = "\x1f"
_REC = "\x01"


def _utc(iso: str) -> str:
    try:
        d = _dt.datetime.fromisoformat(iso.strip())
        if d.tzinfo is None:
            d = d.replace(tzinfo=_dt.timezone.utc)
        return d.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return iso.strip()


class GitDomain:
    name = "git"
    axes: tuple[str, ...] = ()

    def __init__(self, max_commits: int = 500, max_bytes: int = MAX_BYTES):
        self.max_commits = max_commits
        self.max_bytes = max_bytes

    def _git(self, repo: str, *args: str) -> bytes:
        cmd = ["git", "-C", repo, "-c", "core.quotepath=off", *args]
        res = subprocess.run(cmd, capture_output=True, check=False)
        if res.returncode != 0:
            raise ValueError(f"git {args[0]} failed: {res.stderr.decode(errors='replace').strip()}")
        return res.stdout

    def read(self, path: str):
        repo = os.path.abspath(path)
        out = self._git(
            repo, "log", "--no-renames", f"-n{int(self.max_commits)}", "--name-status",
            f"--format={_REC}%H{_SEP}%aI{_SEP}%cI",
        ).decode("utf-8", errors="replace")
        commits = []
        for rec in out.split(_REC)[1:]:
            head, _, rest = rec.partition("\n")
            h, ai, ci = head.split(_SEP)
            changes = []
            for ln in rest.splitlines():
                if "\t" in ln:
                    st, p = ln.split("\t", 1)
                    changes.append((st[:1], p))
            commits.append((h, ai, ci, changes))
        commits.reverse()  # oldest first

        source = Source(id=f"git:{os.path.basename(repo)}", kind="git")
        units: dict[str, Unit] = {}
        events: list[Event] = []
        state: dict[str, str] = {}  # path -> "live" | "dead"
        skipped: set[str] = set()
        for h, ai, ci, changes in commits:
            date = _utc(ai)[:10]
            rec = _utc(ci)
            for st, p in changes:
                if p in skipped:
                    continue
                uid = f"git:{p}"
                if st == "D":
                    if state.get(p) != "live":
                        continue
                    op, text = "repeal", None
                    state[p] = "dead"
                else:
                    text = self._blob(repo, h, p)
                    if text is None:
                        skipped.add(p)
                        if state.get(p) == "live":  # became binary/large: treat as removed
                            op, text, state[p] = "repeal", None, "dead"
                        else:
                            continue
                    else:
                        prev = state.get(p)
                        op = "create" if prev is None else ("restore" if prev == "dead" else "replace")
                        state[p] = "live"
                if uid not in units:
                    units[uid] = Unit(id=uid, source_id=source.id, kind="file", title=p)
                ev = Event(id=f"ev:{uid}:{h[:12]}", unit_id=uid, op=op, date=date,
                           text=text, recorded_at=rec, evidence=h)
                # Same unit, same day: keep only the later commit so replay is unambiguous.
                for i in range(len(events) - 1, -1, -1):
                    if events[i].unit_id == uid:
                        if events[i].date == date:
                            first = events[i].op
                            if first in ("create", "restore") and op == "replace":
                                ev = Event(**{**ev.__dict__, "op": first})
                            del events[i]
                        break
                events.append(ev)
        return [source], list(units.values()), events, []

    def _blob(self, repo: str, commit: str, path: str) -> str | None:
        try:
            raw = self._git(repo, "show", f"{commit}:{path}")
        except ValueError:
            return None
        if len(raw) > self.max_bytes or b"\x00" in raw:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def rules(self):
        return []

    def tools(self):
        return []

    def abstention_text(self, kind, query):
        return None
