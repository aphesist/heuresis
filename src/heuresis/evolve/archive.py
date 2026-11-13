"""The archive of the improvement loop and the champion record. Everything is under the workdir.

``archive.jsonl`` is append-only: one event per line (candidate, stage, status, score, admitted).
``Archive.rows()`` folds the events into one row per candidate: id, parent, candidate (the overrides),
surface hash, stage results, status, score. ``champion.json`` holds the current champion and the
history that rollback restores from. ``state.json`` holds the counters the loop and the promotion
stage need across processes (cycle number, promotion tests and promotions so far, the promotion
block in use per dataset and its queries). JSON files are written atomically.
"""
from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path
from typing import Any

from .candidates import base_surface, candidate_id, normalise, surface_of
from ..v2.locked.schema import surface_hash


def write_json_atomic(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, ensure_ascii=False, default=str)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class Archive:
    def __init__(self, workdir: str | Path):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.path = self.workdir / "archive.jsonl"
        self.champion_path = self.workdir / "champion.json"
        self.state_path = self.workdir / "state.json"
        self.cycles_dir = self.workdir / "cycles"

    # -- the event log ----------------------------------------------------------------------

    def _append(self, event: dict) -> None:
        line = json.dumps(event, sort_keys=True, ensure_ascii=False, default=str) + "\n"
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def events(self) -> list[dict]:
        out: list[dict] = []
        if not self.path.exists():
            return out
        with open(self.path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if isinstance(e, dict):
                    out.append(e)
        return out

    def add_candidate(self, doc: dict, parent: str | None, *, cycle: int, proposer: str = "",
                      note: str = "", judge_model: str = "") -> str:
        """Record a candidate (once); returns its id. The id is the hash of the normalised doc."""
        doc = normalise(doc, base_surface())
        cid = candidate_id(doc)
        if cid in self.rows():
            return cid
        try:
            sh = surface_hash(surface_of(doc))
        except ValueError:
            sh = None  # invalid: recorded all the same, and rejected by the static stage
        self._append({"event": "candidate", "id": cid, "parent": parent, "candidate": doc,
                      "surface_hash": sh, "cycle": cycle, "proposer": proposer, "note": note,
                      "judge_model": judge_model})
        return cid

    def record_stage(self, cid: str, stage: str, report: dict, *, cycle: int) -> None:
        self._append({"event": "stage", "id": cid, "stage": stage, "passed": bool(report.get("passed")),
                      "report": report, "cycle": cycle})

    def set_status(self, cid: str, status: str, reason: str = "", *, cycle: int) -> None:
        self._append({"event": "status", "id": cid, "status": status, "reason": reason, "cycle": cycle})

    def set_score(self, cid: str, score: float, *, cycle: int) -> None:
        self._append({"event": "score", "id": cid, "score": float(score), "cycle": cycle})

    def admit(self, cid: str, *, cycle: int) -> None:
        self._append({"event": "admitted", "id": cid, "cycle": cycle})

    def rows(self) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        for e in self.events():
            cid = e.get("id")
            kind = e.get("event")
            if kind == "candidate":
                rows.setdefault(cid, {
                    "id": cid, "parent": e.get("parent"), "candidate": e.get("candidate", {}),
                    "surface_hash": e.get("surface_hash"), "cycle": e.get("cycle"),
                    "proposer": e.get("proposer", ""), "judge_model": e.get("judge_model", ""), "stages": {}, "status": "proposed",
                    "score": None, "admitted": False, "reason": ""})
            elif cid in rows:
                r = rows[cid]
                if kind == "stage":
                    r["stages"][e["stage"]] = e.get("report", {})
                elif kind == "status":
                    r["status"], r["reason"] = e.get("status", r["status"]), e.get("reason", "")
                elif kind == "score":
                    r["score"] = e.get("score")
                elif kind == "admitted":
                    r["admitted"] = True
        return rows

    def get(self, cid: str) -> dict | None:
        return self.rows().get(cid)

    def children(self, cid: str) -> int:
        return sum(1 for r in self.rows().values() if r["parent"] == cid)

    def stage_report(self, cid: str, stage: str) -> dict | None:
        r = self.get(cid)
        return None if r is None else r["stages"].get(stage)

    # -- parent selection: fixed code, the proposer cannot change it ----------------------------

    def select_parent(self, rng: random.Random) -> str:
        """weight = sigmoid(10 * (score - 0.5)) / (1 + children) over the admitted candidates and the
        champion; a candidate without a score counts as 0.5. ``ValueError`` if the archive is empty."""
        rows = self.rows()
        champ = (self.champion() or {}).get("id")
        pool = sorted(cid for cid, r in rows.items() if r["admitted"] or cid == champ)
        if not pool:
            raise ValueError("the archive holds no admitted candidate")
        counts: dict[str, int] = {}
        for r in rows.values():
            if r["parent"] is not None:
                counts[r["parent"]] = counts.get(r["parent"], 0) + 1
        weights = []
        for cid in pool:
            s = rows[cid]["score"]
            s = 0.5 if s is None else float(s)
            weights.append(sigmoid(10.0 * (s - 0.5)) / (1 + counts.get(cid, 0)))
        return rng.choices(pool, weights=weights, k=1)[0]

    # -- the champion --------------------------------------------------------------------------

    def champion(self) -> dict | None:
        return read_json(self.champion_path)

    def ensure_champion(self, *, cycle: int = 0) -> dict:
        """The champion, created from the packaged surface (empty overrides) when there is none."""
        c = self.champion()
        if c is not None:
            return c
        doc: dict = {}
        cid = self.add_candidate(doc, None, cycle=cycle, proposer="base", note="the packaged surface")
        self.admit(cid, cycle=cycle)
        self.set_status(cid, "champion", "initial champion", cycle=cycle)
        c = {"id": cid, "surface_hash": surface_hash(surface_of(doc)), "candidate": doc,
             "since_cycle": cycle, "reason": "initial champion", "stats": {}, "history": [],
             "rollbacks": []}
        write_json_atomic(self.champion_path, c)
        return c

    def set_champion(self, cid: str, *, reason: str, cycle: int, stats: dict | None = None) -> dict:
        cur = self.ensure_champion(cycle=cycle)
        row = self.get(cid)
        if row is None:
            raise ValueError(f"unknown candidate {cid}")
        hist = list(cur.get("history", []))
        hist.append({"id": cur["id"], "surface_hash": cur["surface_hash"], "candidate": cur["candidate"],
                     "since_cycle": cur.get("since_cycle"), "until_cycle": cycle,
                     "stats": cur.get("stats", {})})
        new = {"id": cid, "surface_hash": surface_hash(surface_of(row["candidate"])),
               "candidate": row["candidate"], "since_cycle": cycle, "reason": reason,
               "stats": stats or {}, "history": hist, "rollbacks": cur.get("rollbacks", [])}
        write_json_atomic(self.champion_path, new)
        self.set_status(cid, "champion", reason, cycle=cycle)
        return new

    def previous_champion(self) -> dict | None:
        c = self.champion()
        return None if not c or not c.get("history") else c["history"][-1]

    def rollback(self, *, to: str | None = None, reason: str = "manual", cycle: int = 0) -> dict:
        """Restore the previous champion (or the one with id ``to`` from the history)."""
        cur = self.ensure_champion(cycle=cycle)
        hist = list(cur.get("history", []))
        if not hist:
            raise ValueError("no previous champion to restore")
        if to is None:
            idx = len(hist) - 1
        else:
            idx = next((i for i in range(len(hist) - 1, -1, -1) if hist[i]["id"] == to), -1)
            if idx < 0:
                raise ValueError(f"{to} is not in the champion history")
        target = hist[idx]
        new = {"id": target["id"], "surface_hash": target["surface_hash"],
               "candidate": target["candidate"], "since_cycle": target.get("since_cycle", cycle),
               "reason": f"rollback: {reason}", "stats": target.get("stats", {}),
               "rechecked": True,
               "history": hist[:idx],
               "rollbacks": list(cur.get("rollbacks", [])) + [
                   {"from": cur["id"], "to": target["id"], "reason": reason, "cycle": cycle}]}
        write_json_atomic(self.champion_path, new)
        self.set_status(cur["id"], "rolled_back", reason, cycle=cycle)
        self.set_status(target["id"], "champion", f"restored: {reason}", cycle=cycle)
        return {"from": cur["id"], "to": target["id"], "reason": reason}

    # -- state and cycle files -------------------------------------------------------------------

    def state(self) -> dict:
        s = read_json(self.state_path, {}) or {}
        s.setdefault("cycle", 0)
        s.setdefault("open_cycle", None)
        s.setdefault("promotion", {})
        s.setdefault("promotion_tests", 0)
        s.setdefault("promotions", 0)
        s.setdefault("memo", {})
        return s

    def save_state(self, state: dict) -> None:
        write_json_atomic(self.state_path, state)

    def cycle_path(self, n: int) -> Path:
        return self.cycles_dir / f"{n:04d}.json"

    def read_cycle(self, n: int) -> dict | None:
        return read_json(self.cycle_path(n))

    def write_cycle(self, n: int, doc: dict) -> None:
        write_json_atomic(self.cycle_path(n), doc)
