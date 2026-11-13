"""One cycle of the improvement loop (docs/design-v2.md section (f), "One cycle").

``run_cycle`` is resumable: the cycle's proposals, the stage results (in the archive) and the row
caches survive a stop, so a rerun with the same workdir continues the open cycle. It stops cleanly
when the ledger cap is reached (``BudgetExceeded``): no partial candidate is promoted. Everything
is deterministic given the seed (parent selection, perturbation, draws, bootstrap).
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable, Mapping

from ..bench.ledger import BudgetExceeded, Ledger
from . import candidates as cand_mod
from . import promotion as promo
from . import tripwires as tw
from .archive import Archive
from .canaries import write_decoy
from .evaluator import Evaluator, load_config
from .proposers import Parent, PerturbProposer
from .splits import SplitExhausted, SplitSource


def _summ(archive: Archive, ids: list[str]) -> list[dict]:
    out = []
    rows = archive.rows()
    for cid in ids:
        r = rows[cid]
        out.append({"id": cid, "status": r["status"], "reason": r["reason"], "score": r["score"],
                    "stages": {s: bool(rep.get("passed")) for s, rep in r["stages"].items()}})
    return out


def run_cycle(workdir: str | Path, *, k: int | None = None, cap_usd: float = 10.0, proposer: Any = None,
              runner: Callable | None = None, datasets: list[str] | None = None, seed: int | None = None,
              allow_unpinned: bool = False, smoke_runner: Callable | None = None,
              splits: SplitSource | None = None, config: Mapping | None = None,
              ledger: Ledger | None = None, root: str | Path | None = None,
              offline: bool | None = None, judge_model: str | None = None) -> dict:
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    over = dict(config or {})
    if datasets:
        over["datasets"] = list(datasets)
    is_offline = (runner is None) if offline is None else offline
    cfg = load_config(over, offline=is_offline)
    if ledger is None:
        spent0 = Ledger(str(wd / "ledger.jsonl"), 0.0).spent
        ledger = Ledger(str(wd / "ledger.jsonl"), spent0 + float(cap_usd), float(cfg["ledger_margin_usd"]))
    spent_start = ledger.spent
    ev = Evaluator(wd, runner=runner, smoke_runner=smoke_runner, splits=splits, config=over, ledger=ledger,
                   allow_unpinned=allow_unpinned, root=root, offline=is_offline, judge_model=judge_model)
    arch = ev.archive
    k = int(k if k is not None else cfg["k"])
    seed = int(cfg["seed"] if seed is None else seed)
    champ = arch.ensure_champion()
    state = arch.state()
    n = int(state["open_cycle"] or state["cycle"] + 1)
    cyc = arch.read_cycle(n) or {"cycle": n, "status": "running", "seed": seed, "candidates": None,
                                 "tripwires": [], "rollback": None, "promoted": None,
                                 "calibration": None, "judge_model": ev.judge_model}
    state["open_cycle"] = n
    arch.save_state(state)
    cycle_seed = seed * 1_000_003 + n
    result: dict = {}

    def finish(status: str, close: bool) -> dict:
        cyc["status"] = status
        arch.write_cycle(n, cyc)
        if close:
            st = arch.state()
            st["cycle"], st["open_cycle"] = n, None
            arch.save_state(st)
        c = arch.champion()
        return {"cycle": n, "status": status, "parent": cyc.get("parent"),
                "champion": {"id": c["id"], "surface_hash": c["surface_hash"]},
                "promoted": cyc.get("promoted"), "rollback": cyc.get("rollback"),
                "calibration": cyc.get("calibration"), "tripwires": cyc["tripwires"],
                "candidates": _summ(arch, cyc.get("candidates") or []),
                "judge_model": ev.judge_model,
                "cost_usd": round(ledger.spent - spent_start, 6), "spent_usd": round(ledger.spent, 6),
                "cap_usd": ledger.cap_usd}

    # -- protected tree ------------------------------------------------------------------------
    diffs = ev.protected_differences()
    if diffs:
        cyc["tripwires"] += [t.as_dict() for t in tw.protected_file_changed(diffs, ev.sev)]
        return finish("stopped_tripwire", close=False)

    try:
        # -- re-check the champion on this cycle's draw; roll back automatically ------------------
        champ = arch.champion()
        prev = arch.previous_champion()
        if (prev and not champ.get("rechecked") and not cyc.get("rechecked")
                and n - int(champ.get("since_cycle") or 0) <= int(cfg["recheck_window_cycles"])):
            draw = ev.cycle_draw(n)
            full = [q for qs in draw.values() for q in qs]
            canaries = ev.canaries(n)
            write_decoy(wd, canaries)
            c_surf = cand_mod.surface_of(champ["candidate"])
            p_surf = cand_mod.surface_of(prev["candidate"])
            c_rows = ev.rows(c_surf, full + canaries, tier="rotating", tag="champion")
            p_rows = ev.rows(p_surf, full, tier="rotating", tag="previous-champion")
            c_main = [r for r in c_rows if not r["qid"].startswith("canary-")]
            c_can = [r for r in c_rows if r["qid"].startswith("canary-")]
            pr = promo.paired(c_main, p_rows, t=ev.t, iters=int(cfg["bootstrap_iters"]),
                              perm_iters=int(cfg["permutation_iters"]), seed=cycle_seed)
            trips = tw.canary_marker(None, c_rows, ev.sev) + tw.canary_answered(
                c_can, float(cfg["tripwires"]["canary_answer_share"]), ev.sev)
            anchors = ev.anchor_sample()
            if anchors:
                trips += tw.tainted_anchor(ev.rows(c_surf, anchors, tier="anchor", tag="champion"), ev.sev)
            reason = None
            if pr["se"] is not None and pr["n"] >= int(cfg["min_pairs"]) and pr["diff"] < 0 and (
                    pr["se"] == 0 or pr["diff"] < -float(cfg["rollback_se"]) * pr["se"]):
                reason = (f"the champion scores {pr['diff']:.3f} below the previous champion on the new "
                          f"draw ({abs(pr['diff'] / pr['se']) if pr['se'] else float('inf'):.1f} standard errors)")
            elif tw.stops_candidate(trips):
                reason = "tripwire: " + ", ".join(t.name for t in trips)
            cyc["rechecked"] = True
            cyc["recheck"] = {"diff": pr["diff"], "se": pr["se"], "n": pr["n"]}
            if reason:
                cyc["rollback"] = arch.rollback(reason=reason, cycle=n)
                cyc["tripwires"] += [t.as_dict() for t in trips]
            arch.write_cycle(n, cyc)

        # -- propose ---------------------------------------------------------------------------
        if cyc.get("candidates") is None:
            rng = random.Random(cycle_seed)
            parent_id = arch.select_parent(rng)
            prow = arch.get(parent_id)
            parent = Parent(parent_id, prow["candidate"], cand_mod.surface_of(prow["candidate"]))
            prop = proposer or PerturbProposer(seed)
            traces = None
            if getattr(prop, "wants_traces", False):
                from .api import reflective_dataset
                traces = reflective_dataset(parent_id, workdir=wd)
            ids: list[str] = []
            for c in prop.propose(parent, k, seed=cycle_seed, traces=traces)[:k]:
                existing = arch.get(cand_mod.candidate_id(c.doc()))
                if existing is not None and (existing["cycle"] != n or c.id == arch.champion()["id"]):
                    continue
                cid = arch.add_candidate(c.doc(), parent_id, cycle=n, proposer=getattr(prop, "name", ""),
                                         note=c.note, judge_model=ev.judge_model)
                if cid not in ids:
                    ids.append(cid)
            cyc["parent"], cyc["candidates"] = parent_id, ids
            arch.write_cycle(n, cyc)
        ids = list(cyc["candidates"])
        rows = lambda: arch.rows()  # noqa: E731

        def stage(cid: str, name: str, fn: Callable[[dict], dict]) -> dict:
            rep = arch.stage_report(cid, name)
            if rep is None:
                ev.new_cost = 0.0
                rep = fn(rows()[cid]["candidate"])
                arch.record_stage(cid, name, rep, cycle=n)
            return rep

        def trips_of(rep: dict) -> list[tw.Trip]:
            return [tw.Trip(**t) for t in rep.get("tripwires", [])]

        # -- stage 0 and 1: free ---------------------------------------------------------------
        stop_cycle = False
        for cid in ids:
            if rows()[cid]["status"] != "proposed":
                continue
            rep = stage(cid, "static", lambda d: ev.evaluate(d, "static", cycle=n))
            if not rep["passed"]:
                arch.set_status(cid, "rejected_static", "; ".join(rep["reasons"] + rep["metrics"].get("problems", [])[:3]), cycle=n)
                cyc["tripwires"] += rep["tripwires"]
                stop_cycle = stop_cycle or tw.stops_cycle(trips_of(rep))
        if stop_cycle:
            return finish("stopped_tripwire", close=True)
        for cid in ids:
            r = rows()[cid]
            if r["status"] != "proposed" or "static" not in r["stages"]:
                continue
            rep = stage(cid, "smoke", lambda d: ev.evaluate(d, "smoke"))
            if rep["passed"]:
                arch.admit(cid, cycle=n)
                arch.set_status(cid, "admitted", "passed static and smoke", cycle=n)
            else:
                arch.set_status(cid, "rejected_smoke", "; ".join(rep["reasons"]), cycle=n)
                cyc["tripwires"] += rep["tripwires"]
                stop_cycle = stop_cycle or tw.stops_cycle(trips_of(rep))
        if stop_cycle:
            return finish("stopped_tripwire", close=True)

        # -- stage 2: screen -------------------------------------------------------------------
        for cid in ids:
            r = rows()[cid]
            if r["status"] == "admitted":
                rep = stage(cid, "screen", lambda d: ev.evaluate(d, "screen", cycle=n))
                arch.set_score(cid, rep["metrics"].get("score_normalised", 0.5), cycle=n)
                arch.set_status(cid, "screened" if rep["passed"] else "rejected_screen",
                                "; ".join(rep["reasons"]), cycle=n)
                cyc["tripwires"] += rep["tripwires"]
                stop_cycle = stop_cycle or tw.stops_cycle(trips_of(rep))
        if stop_cycle:
            return finish("stopped_tripwire", close=True)

        # -- stage 3: dev for the top candidates -------------------------------------------------
        screened = [cid for cid in ids if "screen" in rows()[cid]["stages"]
                    and rows()[cid]["stages"]["screen"]["passed"]]
        screened.sort(key=lambda c: (-(rows()[c]["stages"]["screen"]["metrics"].get("diff") or 0.0), c))
        top = screened[:int(cfg["dev_top"])]
        for cid in screened[int(cfg["dev_top"]):]:
            if rows()[cid]["status"] == "screened":
                arch.set_status(cid, "archived", "not among the top for the dev stage", cycle=n)
        for cid in top:
            rep = stage(cid, "dev", lambda d: ev.evaluate(d, "dev", cycle=n))
            arch.set_score(cid, rep["metrics"].get("score_normalised", 0.5), cycle=n)
            arch.set_status(cid, "dev_passed" if rep["passed"] else "rejected_dev",
                            "; ".join(rep["reasons"]), cycle=n)
            cyc["tripwires"] += rep["tripwires"]
            stop_cycle = stop_cycle or tw.stops_cycle(trips_of(rep))
        if stop_cycle:
            return finish("stopped_tripwire", close=True)

        # -- stage 4: promote at most one --------------------------------------------------------
        passers = [c for c in top if rows()[c]["stages"]["dev"]["passed"]]
        passers.sort(key=lambda c: (-(rows()[c]["stages"]["dev"]["metrics"].get("diff") or 0.0), c))
        for cid in passers[1:]:
            if rows()[cid]["status"] == "dev_passed":
                arch.set_status(cid, "archived", "dev passed; one promotion per cycle", cycle=n)
        if passers:
            cid = passers[0]
            r = rows()[cid]
            if cid != arch.champion()["id"] and r["status"] != "rejected_promotion":
                dev_rep = r["stages"]["dev"]
                rep = arch.stage_report(cid, "promote")
                if rep is None:
                    ev.new_cost = 0.0
                    rep = ev.evaluate(r["candidate"], "promote", dev=dev_rep)
                    arch.record_stage(cid, "promote", rep, cycle=n)
                cyc["tripwires"] += rep["tripwires"]
                if rep["passed"]:
                    arch.set_champion(cid, reason=f"promotion test passed at level "
                                                  f"{rep['metrics']['level']:.5f}", cycle=n,
                                      stats=rep["metrics"])
                    st = arch.state()
                    st["promotions"] += 1
                    arch.save_state(st)
                    cyc["promoted"] = cid
                    cyc["calibration"] = ev.refit_calibration()
                elif rep["metrics"].get("budget_limited"):
                    arch.set_status(cid, "archived", "; ".join(rep["reasons"]), cycle=n)
                    cyc["note"] = "promotion skipped: " + "; ".join(rep["reasons"])
                else:
                    arch.set_status(cid, "rejected_promotion", "; ".join(rep["reasons"]), cycle=n)
        return finish("complete", close=True)
    except BudgetExceeded as e:
        cyc["stopped"] = str(e)
        return finish("stopped_budget", close=False)
    except SplitExhausted as e:
        cyc["stopped"] = f"no fresh draw: {e}"
        return finish("stopped_exhausted", close=False)
