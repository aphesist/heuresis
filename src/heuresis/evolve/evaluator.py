"""The evaluator of the improvement loop: stages static, smoke, screen, dev and promote.

A stage returns a public report ``{"stage", "passed", "metrics", "tripwires", "cost_usd", ...}``
with aggregates only: never a gold answer, a gold unit, a question of the promotion set or a row.
Rows live in caches under the workdir (``cache/``): per (surface hash, tier), keyed by question,
so the champion's rows are computed once per draw and a stopped run resumes where it stopped. Rows
of the anchor and promotion tiers are stored without answer text.

The model side is an injectable ``runner(surface, questions, *, tag) -> list[dict]`` (rows with
``qid, status, text, outcome, score, confidence, usd, tainted, abstention, reasons``). The default
``BenchRunner`` runs the ``engine2`` benchmark system through ``bench.systems.build_context`` and
grades with ``bench.run.grade``; ``FixtureRunner`` does the same on the packaged fixture with
offline fakes. The evaluator refuses to run (beyond the static stage, which records the difference)
when ``manifest.verify_manifest()`` reports one, unless ``allow_unpinned=True``.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..bench.ledger import BudgetExceeded, Ledger
from ..locked.scoring import penalty_score
from ..model import Usage
from ..v2.locked import manifest
from ..v2.locked.schema import Surface, surface_hash
from . import candidates as cand_mod
from . import promotion as promo
from . import tripwires as tw
from .archive import Archive, read_json, write_json_atomic
from .canaries import contains_marker, is_canary, make_canaries, write_decoy
from .splits import (FixtureData, PoolQuestion, PromotionBook, SplitExhausted, SplitSource,
                     fixture_splits, load_fixture)

STAGES = ("static", "smoke", "screen", "dev", "promote")
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
_STRIPPED_TIERS = ("anchor", "promotion")


class ProtectedTreeError(RuntimeError):
    """The protected files differ from the manifest: the evaluator refuses to run."""


class IncompleteRun(RuntimeError):
    """A runner returned fewer rows than it was given questions."""


def load_config(overrides: Mapping | None = None, *, offline: bool = False) -> dict:
    """``config.json`` with ``overrides`` merged one level deep (nested dicts merge); with
    ``offline`` the ``offline`` section replaces the sizes for the packaged fixture."""
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    off = cfg.pop("offline", {})
    if offline:
        cfg.update(off)
    for k, v in (overrides or {}).items():
        if isinstance(v, Mapping) and isinstance(cfg.get(k), dict):
            cfg[k] = {**cfg[k], **v}
        else:
            cfg[k] = v
    return cfg


# ---------------------------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------------------------


class FixtureLLM:
    """A deterministic offline model for the packaged fixture. It answers a propose prompt with the
    first sentence of the shown passage that best covers the question (cited by its mark) and
    abstains when no passage covers it; it answers the locked judge prompt with favourable verdicts.
    It is a fake: it exists so that ``EngineV2`` really runs offline, not to model a language model."""

    id = "fixture"
    offline = True
    _STOP = frozenset("what when how many does did is are was were the a an of in on at to for who which "
                      "where do has have it its by and or".split())
    _LINE = re.compile(r"^\[(t\d+)\] \(([^)]*)\) (.*)$")

    def complete(self, system: str, prompt: str, *, max_tokens: int = 600) -> tuple[str, Usage]:
        from ..v2.locked.judge import JUDGE_SYSTEM
        text = self._judge(prompt) if system == JUDGE_SYSTEM else self._propose(prompt)
        return text, Usage(model=self.id, tokens_in=len(prompt.split()), tokens_out=len(text.split()))

    @staticmethod
    def _judge(prompt: str) -> str:
        lines = []
        for m in re.finditer(r"^S(\d+) \((derived|cited)", prompt, re.M):
            lines.append(f"S{m.group(1)}: {'FOLLOWS' if m.group(2) == 'derived' else 'SUPPORTED'}")
        return "\n".join(lines + ["ANSWER: DIRECT", "SUFFICIENT: YES", "PREMISE: OK", "CONFLICT: NONE"])

    def _words(self, text: str) -> set[str]:
        return {w[:4] for w in re.findall(r"\w+", text.lower()) if w not in self._STOP}

    def _propose(self, prompt: str) -> str:
        qm = re.search(r"^Question: (.*)$", prompt, re.M)
        q = self._words(qm.group(1)) if qm else set()
        best, best_cov = None, 0.0
        for line in prompt.splitlines():
            m = self._LINE.match(line)
            if not m:
                continue
            cov = len(q & self._words(m.group(3))) / len(q) if q else 0.0
            if cov > best_cov:
                best, best_cov = m, cov
        if best is None or best_cov < 0.99:
            return "ABSTAIN no_source: the passages shown do not address the question."
        body = best.group(3).strip()
        first = re.split(r"(?<=[.!?])\s", body)[0]
        if first and first[-1] not in ".!?":
            first += "."
        return f"{first} [{best.group(1)}]"


def _short(x: Any, n: int = 200) -> str:
    return str(x)[:n]


class BenchRunner:
    """Runs ``engine2`` of ``bench.systems_v2`` with the candidate's surface, one question at a
    time, and grades with ``bench.run.grade``. Selected for paid runs by giving it real clients."""

    charges_ledger = True

    def __init__(self, splits: SplitSource, workdir: str | Path, *, llm: Any = None,
                 judge_llm: Any = None, strong_llm: Any = None, embedder: Any = None,
                 ledger: Ledger | None = None, estimate_usd: float = 0.01, offline: bool = False):
        self.splits = splits
        self.workdir = Path(workdir)
        self.llm, self.judge_llm, self.strong_llm = llm, judge_llm, strong_llm
        self.embedder = embedder
        self.ledger = ledger
        self.estimate_usd = estimate_usd
        self.offline = offline

    def _context(self, dataset: str, surface: Surface):
        from ..bench.systems import build_context
        ds = self.splits.dataset(dataset)
        db = self.workdir / "stores" / f"{dataset}.sqlite"
        db.parent.mkdir(parents=True, exist_ok=True)
        return build_context(ds, str(db), llm=self.llm, embedder=self.embedder, ledger=self.ledger,
                             estimate_usd=self.estimate_usd, prepare=not db.exists(),
                             judge_llm=self.judge_llm, strong_llm=self.strong_llm, v2_llm=self.llm,
                             v2_surface=surface)

    def __call__(self, surface: Surface, questions: Sequence[Any], *, tag: str) -> list[dict]:
        from ..bench.run import grade
        from ..bench.systems import build_systems
        rows: list[dict] = []
        by_ds: dict[str, list] = {}
        default = self.splits.rotating_names()[0]
        for q in questions:
            by_ds.setdefault(getattr(q, "dataset", "") or default, []).append(q)
        for dataset, qs in by_ds.items():
            ctx = self._context(dataset, surface)
            system = build_systems(ctx, ["engine2"])[0]
            domain_name = ctx.dataset.meta.get("domain", "jsonl")
            for q in qs:
                rows.append(self._one(system, ctx, domain_name, q, grade))
        return rows

    def _one(self, system: Any, ctx: Any, domain_name: str, q: Any, grade: Callable) -> dict:
        try:
            res = system.answer(q)
        except BudgetExceeded:
            raise
        except Exception as e:  # a model or engine failure: a wrong answer, and a visible one
            return {"qid": q.id, "status": "abstained", "text": "", "outcome": "wrong", "score": -1.0,
                    "confidence": 0.0, "usd": 0.0, "tainted": None, "abstention": None,
                    "reasons": [_short(f"{type(e).__name__}: {e}")], "error": _short(type(e).__name__)}
        if res.error:
            return {"qid": q.id, "status": "abstained", "text": "", "outcome": "wrong", "score": -1.0,
                    "confidence": 0.0, "usd": float(res.usage.usd), "tainted": None,
                    "abstention": None, "reasons": [_short(res.error)], "error": "model"}
        g = grade(q, res.status, res.text)
        replay = res.replay or {}
        tainted = None
        if res.status == "answered":
            try:
                from ..bench import citations
                from ..domains import get_domain
                a = citations.analyse(res.text, q.as_of, ctx.store(), get_domain(domain_name),
                                      res.cited_units)
                tainted = bool(citations.is_tainted(a))
            except Exception:
                tainted = None
        reasons = [c.get("note", "") for c in replay.get("claims", [])
                   if c.get("label") != "supported" and c.get("note")]
        reasons += [d.get("reason", "") for d in (replay.get("meta") or {}).get("dropped", [])]
        return {"qid": q.id, "status": res.status, "text": res.text, "outcome": g["outcome"],
                "score": g["score"], "confidence": float(res.confidence), "usd": float(res.usage.usd),
                "tainted": tainted, "abstention": replay.get("abstention"),
                "reasons": [_short(r) for r in reasons if r][:8]}


class FixtureRunner(BenchRunner):
    """``BenchRunner`` on the packaged fixture, with the offline fakes (no model, no cost)."""

    def __init__(self, workdir: str | Path, splits: SplitSource | None = None):
        from ..fakes import HashEmbedder
        super().__init__(splits or fixture_splits(), workdir, llm=FixtureLLM(), judge_llm=FixtureLLM(),
                         embedder=HashEmbedder(), ledger=None, offline=True)


# ---------------------------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------------------------


def _shingles(text: str, n: int = 8) -> set[tuple]:
    w = re.findall(r"\w+", text.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def _qkey(q: Any) -> str:
    return f"{getattr(q, 'dataset', '')}:{q.id}"


def _json_safe(x: Any) -> Any:
    return json.loads(json.dumps(x, default=str, allow_nan=False)) if x is not None else None


def _clean(x: Any) -> Any:
    """Replace NaN and infinities by None, recursively, so reports are valid JSON."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    return x


class Evaluator:
    def __init__(self, workdir: str | Path, *, runner: Callable | None = None,
                 smoke_runner: Callable | None = None, splits: SplitSource | None = None,
                 config: Mapping | None = None, ledger: Ledger | None = None,
                 allow_unpinned: bool = False, root: str | Path | None = None, offline: bool | None = None,
                 archive: Archive | None = None, chunk: int = 25, judge_model: str | None = None):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        default_runner = runner is None
        self.offline = default_runner if offline is None else offline
        self.cfg = load_config(config, offline=self.offline)
        self.archive = archive or Archive(self.workdir)
        self.splits = splits or fixture_splits(
            seed=0, promo_n=int(self.cfg["promotion_n"]), promo_blocks=int(self.cfg["promotion_blocks"]))
        self.runner = runner if runner is not None else FixtureRunner(self.workdir, self.splits)
        self._smoke_runner = smoke_runner
        self.allow_unpinned = allow_unpinned
        self.root = root
        self.chunk = chunk
        self.t = float(self.cfg["penalty_t"])
        self.cache_dir = self.workdir / "cache"
        self.ledger = ledger or Ledger(str(self.workdir / "ledger.jsonl"), float(self.cfg["cap_usd"]),
                                       float(self.cfg["ledger_margin_usd"]))
        self.new_cost = 0.0
        if judge_model is None:
            if self.offline:
                judge_model = "offline-fixture"
            else:
                from ..v2.locked.decide import load_policy
                judge_model = load_policy().judge_model
        self.judge_model = judge_model

    # -- plumbing ---------------------------------------------------------------------------

    @property
    def sev(self) -> dict:
        return self.cfg.get("severity", {})

    def protected_differences(self) -> list[str]:
        if self.allow_unpinned:
            return []
        return manifest.verify_manifest(self.root)

    def require_pinned(self) -> None:
        diffs = self.protected_differences()
        if diffs:
            raise ProtectedTreeError("protected files differ from the manifest: " + "; ".join(diffs[:5]))

    def champion_surface(self) -> tuple[dict, Surface]:
        c = self.archive.ensure_champion()
        return c, cand_mod.surface_of(c["candidate"])

    def smoke_runner(self) -> Callable:
        if self._smoke_runner is None:
            self._smoke_runner = FixtureRunner(self.workdir)
        return self._smoke_runner

    def _charge(self, usd: float, tag: str) -> None:
        if usd > 0 and not getattr(self.runner, "charges_ledger", False):
            self.ledger.charge(Usage(model="runner", usd=usd), tag)

    def _budget_check(self, n: int) -> None:
        est = 0.0 if getattr(self.runner, "offline", False) else float(
            self.cfg["estimate_usd_per_question"]) * n
        self.ledger.check(est)

    def _norm_row(self, r: Mapping, q: Any, tier: str) -> dict:
        outcome = r.get("outcome")
        if outcome is None:
            from ..bench.run import grade
            outcome = grade(q, r.get("status", "abstained"), r.get("text", ""))["outcome"]
        text = str(r.get("text", "") or "")
        row = {
            "qid": q.id, "dataset": getattr(q, "dataset", ""), "split": getattr(q, "split", ""),
            "status": "answered" if r.get("status") == "answered" else "abstained", "text": text,
            "outcome": str(outcome), "score": penalty_score(str(outcome), self.t),
            "confidence": float(r.get("confidence") or 0.0), "usd": float(r.get("usd") or 0.0),
            "tainted": r.get("tainted"), "abstention": r.get("abstention"),
            "reasons": [_short(x) for x in (r.get("reasons") or [])][:8],
            "answerable": bool(q.answerable), "cluster": q.cluster, "kind": q.kind,
            "has_marker": contains_marker(text),
        }
        if r.get("error"):
            row["error"] = _short(r["error"], 80)
        if tier in ("rotating", "smoke", "canary"):
            row["question"] = q.text
        if tier in _STRIPPED_TIERS:
            row.update(text="", abstention=None, reasons=[])
        return _json_safe(row)

    def rows(self, surface: Surface, questions: Sequence[Any], *, tier: str, tag: str) -> list[dict]:
        """Rows for ``questions`` under ``surface``: cached per (surface hash, tier, question), the
        rest computed in chunks per dataset (each chunk is saved before the next one starts, so a
        stop at the ledger cap loses at most one chunk)."""
        sh = surface_hash(surface)
        path = self.cache_dir / f"{sh[:32]}.{tier}.json"
        doc = read_json(path, None) or {"surface_hash": sh, "tier": tier, "rows": {}}
        cache = doc["rows"]
        missing = [q for q in questions if _qkey(q) not in cache]
        by_ds: dict[str, list] = {}
        for q in missing:
            by_ds.setdefault(getattr(q, "dataset", ""), []).append(q)
        for qs in by_ds.values():
            for i in range(0, len(qs), self.chunk):
                part = qs[i:i + self.chunk]
                self._budget_check(len(part))
                new = self.runner(surface, part, tag=tag)
                got = {str(r.get("qid")): r for r in new}
                usd = 0.0
                for q in part:
                    if q.id not in got:
                        raise IncompleteRun(f"the runner returned no row for {len(part) - len(got)} "
                                            f"of {len(part)} questions")
                    row = self._norm_row(got[q.id], q, tier)
                    cache[_qkey(q)] = row
                    usd += row["usd"]
                self._charge(usd, tag)
                self.new_cost += usd
                write_json_atomic(path, doc)
        return [cache[_qkey(q)] for q in questions]

    def cycle_draw(self, cycle: int) -> dict[str, list[PoolQuestion]]:
        n = int(self.cfg["rotating_n"])
        return {ds: self.splits.rotating(ds, cycle, n) for ds in self._datasets()}

    def _datasets(self) -> list[str]:
        names = self.splits.rotating_names()
        wanted = self.cfg.get("datasets")
        return [n for n in names if not wanted or n in wanted]

    def canaries(self, cycle: int) -> list[PoolQuestion]:
        names = self._datasets()
        seed = int(self.cfg["seed"]) * 1000 + cycle
        out = make_canaries(seed, int(self.cfg["canary_n"]))
        fixed = [PoolQuestion(id=q.id, text=q.text, answers=q.answers, answerable=False, kind="canary",
                              dataset=names[i % len(names)], split="canary") for i, q in enumerate(out)]
        return fixed

    def anchor_sample(self) -> list[PoolQuestion]:
        """The first ``anchor_n`` questions (by hash order) of every anchor group."""
        n = int(self.cfg["anchor_n"])
        groups: dict[tuple, list] = {}
        for q in self.splits.anchors():
            groups.setdefault((q.dataset, q.split), []).append(q)
        out: list[PoolQuestion] = []
        for key in sorted(groups):
            out += sorted(groups[key], key=lambda q: hashlib.sha256(q.id.encode()).hexdigest())[:n]
        return out

    def affordable_promotion_n(self, n_datasets: int, anchors: int) -> int | None:
        """Questions per dataset the remaining budget allows for a promotion test (candidate and
        champion, plus anchors), at most ``promotion_n``; None when below ``promotion_min_n`` in total.
        An offline runner is never limited."""
        n = int(self.cfg["promotion_n"])
        if getattr(self.runner, "offline", False):
            return n
        est = float(self.cfg["estimate_usd_per_question"])
        left = self.ledger.remaining if not self.ledger.dry_run else float("inf")
        total = int((left - 2 * anchors * est) // (2 * est)) if est > 0 else n * n_datasets
        per = min(n, total // max(1, n_datasets))
        return per if per * n_datasets >= int(self.cfg["promotion_min_n"]) else None

    def current_cycle(self) -> int:
        s = self.archive.state()
        return int(s["open_cycle"] or (s["cycle"] + 1))

    # -- report helpers ----------------------------------------------------------------------

    def _report(self, stage: str, cid: str, passed: bool, metrics: dict, trips: Sequence[tw.Trip],
                reasons: Sequence[str], cost0: float, **extra: Any) -> dict:
        return _clean({"stage": stage, "candidate_id": cid, "passed": bool(passed), "metrics": metrics,
                       "tripwires": [t.as_dict() for t in trips], "reasons": list(reasons),
                       "judge_model": self.judge_model,
                       "cost_usd": round(self.new_cost - cost0, 6), **extra})

    # -- stage 0: static -----------------------------------------------------------------------

    def load(self, candidate: Any) -> tuple[dict, list[str], Surface | None]:
        """(normalised overrides, problems, surface or None)."""
        base = cand_mod.base_surface()
        loaded = cand_mod.load_candidate(candidate, base)
        problems = list(loaded.problems)
        surface = None
        try:
            surface = cand_mod.surface_of(loaded.overrides, base)
        except ValueError as e:
            problems += [p for p in str(e).split("; ") if p]
        return cand_mod.normalise(loaded.overrides, base), problems, surface

    def _lint_questions(self, cycle: int) -> list[str]:
        texts: list[str] = []
        try:
            for qs in self.cycle_draw(cycle).values():
                texts += [q.text for q in qs]
            texts += [q.text for q in self.splits.anchors()]
        except (SplitExhausted, ValueError, OSError, KeyError):
            pass
        try:
            texts += [q.text for q in load_fixture().smoke]
        except OSError:
            pass
        return texts

    def static(self, candidate: Any, *, cycle: int | None = None) -> dict:
        cost0 = self.new_cost
        overrides, problems, surface = self.load(candidate)
        cid = cand_mod.candidate_id(overrides)
        trips: list[tw.Trip] = []
        prompts = overrides.get("prompts") if isinstance(overrides.get("prompts"), dict) else {}
        trips += tw.canary_marker({k: v for k, v in prompts.items() if isinstance(v, str)}, (), self.sev)
        if surface is not None and prompts:
            texts = self._lint_questions(cycle or self.current_cycle())
            grams: set[tuple] = set()
            for t in texts:
                grams |= _shingles(t)
            for name, ptxt in prompts.items():
                if isinstance(ptxt, str) and _shingles(ptxt) & grams:
                    problems.append(f"prompt {name}: shares an 8-word sequence with an evaluation question")
        trips += tw.invalid_surface(problems, self.sev)
        diffs = self.protected_differences()
        trips += tw.protected_file_changed(diffs, self.sev)
        passed = not problems and not diffs and not trips
        metrics = {"valid": surface is not None and not problems,
                   "surface_hash": surface_hash(surface) if surface is not None else None,
                   "problems": problems[:10], "protected_ok": not diffs,
                   "pinned": not self.allow_unpinned}
        return self._report("static", cid, passed, metrics, trips,
                            [] if passed else ["static checks failed"], cost0)

    # -- stage 1: smoke -----------------------------------------------------------------------

    def smoke(self, candidate: Any) -> dict:
        cost0 = self.new_cost
        st = self.static(candidate)
        cid = st["candidate_id"]
        if not st["passed"]:
            return {**st, "stage": "smoke", "reasons": ["static stage failed"]}
        surface = self.load(candidate)[2]
        fx = load_fixture()
        qs = [PoolQuestion(id=q.id, text=q.text, answers=q.answers, answerable=q.answerable,
                           as_of=q.as_of, gold_units=q.gold_units, cluster=q.cluster, kind=q.kind,
                           dataset=fx.dataset.name, split="smoke") for q in fx.smoke]
        reasons: list[str] = []
        try:
            raw = self.smoke_runner()(surface, qs, tag="smoke")
            got = {str(r.get("qid")): r for r in raw}
            rows = [self._norm_row(got[q.id], q, "smoke") for q in qs if q.id in got]
        except BudgetExceeded:
            raise
        except Exception as e:
            rows = []
            reasons.append(f"the smoke run raised {type(e).__name__}")
        if not rows and not reasons:
            reasons.append("the smoke run returned no rows")
        if rows and len(rows) < len(qs):
            reasons.append("the smoke run returned fewer rows than questions")
        errors = [r for r in rows if r.get("error")]
        if errors:
            reasons.append(f"{len(errors)} smoke question(s) failed with an error")
        trips = tw.canary_marker(None, rows, self.sev) + tw.tainted_anchor(rows, self.sev)
        passed = not reasons and not trips
        return self._report("smoke", cid, passed, {"n": len(rows), **promo.metrics(rows, self.t)}, trips,
                            reasons, cost0)

    # -- stages 2 and 3: screen and dev --------------------------------------------------------

    def _split_canary(self, rows: Sequence[dict]) -> tuple[list[dict], list[dict]]:
        return ([r for r in rows if not is_canary(r["qid"])], [r for r in rows if is_canary(r["qid"])])

    def _compare(self, stage: str, candidate: Any, cycle: int | None, *, n_per_dataset: int | None,
                 with_anchors: bool) -> dict:
        cost0 = self.new_cost
        st = self.static(candidate, cycle=cycle)
        cid = st["candidate_id"]
        if not st["passed"]:
            return {**st, "stage": stage, "reasons": ["static stage failed"]}
        self.require_pinned()
        cycle = cycle or self.current_cycle()
        surface = self.load(candidate)[2]
        champ, champ_surface = self.champion_surface()
        draw = self.cycle_draw(cycle)
        full = [q for qs in draw.values() for q in qs]
        sub = [q for qs in draw.values() for q in (qs[:n_per_dataset] if n_per_dataset else qs)]
        canaries = self.canaries(cycle)
        write_decoy(self.workdir, canaries)
        champ_rows_all = self.rows(champ_surface, full, tier="rotating", tag="champion")
        cand_rows_all = self.rows(surface, sub + canaries, tier="rotating", tag=stage)
        cand_rows, cand_canary = self._split_canary(cand_rows_all)
        champ_by = {r["qid"]: r for r in champ_rows_all}
        champ_rows = [champ_by[r["qid"]] for r in cand_rows if r["qid"] in champ_by]
        ov = self.load(candidate)[0]
        prompts = ov.get("prompts") if isinstance(ov.get("prompts"), dict) else {}
        trips: list[tw.Trip] = []
        trips += tw.canary_marker(prompts, cand_rows_all, self.sev)
        trips += tw.canary_answered(cand_canary, float(self.cfg["tripwires"]["canary_answer_share"]), self.sev)
        pr = promo.paired(cand_rows, champ_rows, t=self.t, level=float(self.cfg["dev_lower_bound_level"]),
                          iters=int(self.cfg["bootstrap_iters"]), perm_iters=int(self.cfg["permutation_iters"]),
                          seed=int(self.cfg["seed"]) + cycle)
        mc, mb = promo.metrics(cand_rows, self.t), promo.metrics(champ_rows, self.t)
        trips += tw.cost_doubled(mc["cost_per_question"], mb["cost_per_question"],
                                 float(self.cfg["tripwires"]["cost_ratio"]), self.sev)
        metrics = {"n": pr["n"], "diff": pr["diff"], "se": pr["se"], "lower_bound": pr["lower_bound"],
                   "p_one_sided": pr["p_one_sided"], "score": mc["score"],
                   "score_normalised": promo.normalised_score(mc["score"], self.t),
                   "champion_score": mb["score"], "candidate": mc, "champion": mb,
                   "canary": {"n": len(cand_canary),
                              "answered": sum(1 for r in cand_canary if r["status"] == "answered")}}
        min_pairs = int(self.cfg["min_pairs"])
        if with_anchors:
            # Anchors are run only for the one candidate that reaches promotion (the judge makes an
            # engine question cost about US$0.010), so the dev stage checks the dev-row guard rails.
            a_cand, a_champ = [], []
            rails = promo.guard_rails(cand_rows, champ_rows, a_cand, a_champ, self.cfg["guard_rails"],
                                      t=self.t, min_pairs=min_pairs, seed=int(self.cfg["seed"]))
            trips += tw.implausible_jump(pr["diff"], pr["se"], float(self.cfg["tripwires"]["implausible_se"]),
                                         self.sev)
            ok, why = promo.decide_dev(pr, rails, min_pairs=min_pairs)
            metrics["guard_rails"] = rails
            metrics["winners_curse"] = promo.winners_curse_note(pr["n"], max(2, int(self.cfg["k"])), pr["se"])
        else:
            ok, why = promo.decide_screen(pr, reject_se=float(self.cfg["screen_reject_se"]), min_pairs=min_pairs)
        passed = ok and not tw.stops_candidate(trips)
        if ok and not passed:
            why = "a tripwire stopped the candidate"
        return self._report(stage, cid, passed, metrics, trips, [why], cost0, cycle=cycle)

    def screen(self, candidate: Any, *, cycle: int | None = None) -> dict:
        return self._compare("screen", candidate, cycle, n_per_dataset=int(self.cfg["screen_n"]),
                             with_anchors=False)

    def dev(self, candidate: Any, *, cycle: int | None = None) -> dict:
        return self._compare("dev", candidate, cycle, n_per_dataset=None, with_anchors=True)

    # -- stage 4: promote ----------------------------------------------------------------------

    def promote(self, candidate: Any, *, dev: Mapping | None = None) -> dict:
        """Pass or fail and the decision statistics on the sealed promotion set; never rows."""
        cost0 = self.new_cost
        st = self.static(candidate)
        cid = st["candidate_id"]
        if not st["passed"]:
            return {**st, "stage": "promote", "reasons": ["static stage failed"]}
        self.require_pinned()
        surface = self.load(candidate)[2]
        champ, champ_surface = self.champion_surface()
        if cid == champ["id"]:
            return self._report("promote", cid, False, {}, [], ["the candidate is the champion"], cost0)
        state = self.archive.state()
        book = PromotionBook(state, int(self.cfg["promotion_query_budget"]))
        names = self._datasets()
        blocks = {ds: book.block(ds) for ds in names}
        memo_key = f"{cid}|{champ['id']}|" + ",".join(f"{ds}:{b}" for ds, b in sorted(blocks.items()))
        if memo_key in state["memo"]:
            return {**state["memo"][memo_key], "cost_usd": 0.0, "memo": True}
        anchors = self.anchor_sample()
        n = self.affordable_promotion_n(len(names), len(anchors))
        if n is None:
            return self._report("promote", cid, False, {"budget_limited": True}, [],
                                ["the remaining budget does not allow a promotion test of the minimum size"],
                                cost0)
        memo_key += f"|n{n}"
        if memo_key in state["memo"]:
            return {**state["memo"][memo_key], "cost_usd": 0.0, "memo": True}
        try:
            qs = [q for ds in names for q in self.splits.promotion(ds, blocks[ds], n)]
        except SplitExhausted as e:
            return self._report("promote", cid, False, {}, [], [f"no promotion block left: {e}"], cost0)
        cand_rows = self.rows(surface, qs, tier="promotion", tag="promote")
        champ_rows = self.rows(champ_surface, qs, tier="promotion", tag="promote-champion")
        a_cand = self.rows(surface, anchors, tier="anchor", tag="promote") if anchors else []
        a_champ = self.rows(champ_surface, anchors, tier="anchor", tag="promote-champion") if anchors else []
        t_index = int(state["promotion_tests"]) + 1
        level = promo.alpha_t(float(self.cfg["alpha"]), t_index, int(state["promotions"]))
        pr = promo.paired(cand_rows, champ_rows, t=self.t, iters=int(self.cfg["bootstrap_iters"]),
                          perm_iters=int(self.cfg["permutation_iters"]),
                          seed=int(self.cfg["seed"]) + t_index)
        min_pairs = int(self.cfg["min_pairs"])
        rails = promo.guard_rails(cand_rows, champ_rows, a_cand, a_champ, self.cfg["guard_rails"],
                                  t=self.t, min_pairs=min_pairs, seed=int(self.cfg["seed"]))
        ok, why = promo.decide_promotion(pr, level, rails, min_pairs=min_pairs)
        trips = tw.canary_marker(None, cand_rows + a_cand, self.sev) + tw.tainted_anchor(a_cand, self.sev)
        if dev and dev.get("metrics") and pr["se"] is not None and dev["metrics"].get("se") is not None:
            trips += tw.dev_promotion_gap(dev["metrics"]["diff"], dev["metrics"]["se"], pr["diff"], pr["se"],
                                          float(self.cfg["tripwires"]["gap_se"]), self.sev)
        passed = ok and not tw.stops_candidate(trips)
        metrics = {"statistic": pr["diff"], "se": pr["se"], "p_value": pr["p_one_sided"], "level": level,
                   "test_index": t_index, "promotions_so_far": int(state["promotions"]), "n": pr["n"],
                   "lower_bound": pr["lower_bound"],
                   "guard_rails": {k: v["ok"] for k, v in rails.items()}}
        report = self._report("promote", cid, passed, metrics, trips, [why], cost0)
        for ds in names:  # the queries are spent only once the whole test has run
            book.consume(ds)
        state["promotion_tests"] = t_index
        state["memo"][memo_key] = report
        self.archive.save_state(state)
        return report

    # -- calibration of a new champion -----------------------------------------------------------

    def refit_calibration(self) -> dict:
        """After a promotion: run the champion on the calibration block (``cal0``, never used by a
        rotating draw or a promotion test) and fit the locked risk-controlled threshold, but only if
        the budget allows; otherwise record that the champion is uncalibrated."""
        from ..v2.locked import calibration as cal_mod
        from ..v2.locked.decide import load_policy
        champ, surface = self.champion_surface()
        names = self._datasets()
        n = int(self.cfg["cal_n"])
        try:
            qs = [q for ds in names for q in self.splits.calibration(ds, 0, n)]
        except (SplitExhausted, NotImplementedError, ValueError) as e:
            return {"status": "uncalibrated", "reason": f"no calibration block: {e}"}
        if not qs:
            return {"status": "uncalibrated", "reason": "no calibration block"}
        est = 0.0 if getattr(self.runner, "offline", False) else float(self.cfg["estimate_usd_per_question"])
        if not self.ledger.dry_run and est * len(qs) > self.ledger.remaining:
            return {"status": "uncalibrated", "reason": "the remaining budget does not cover the calibration block"}
        self.new_cost = 0.0
        try:
            rows = self.rows(surface, qs, tier="calibration", tag="calibration")
        except BudgetExceeded:
            return {"status": "uncalibrated", "reason": "the budget ran out during the calibration run"}
        pol = load_policy()
        ans = [r for r in rows if r["status"] == "answered"]
        res = cal_mod.fit([r["confidence"] for r in ans], [r["outcome"] == "wrong" for r in ans],
                          alpha=pol.alpha, delta=pol.delta, grid=pol.grid, min_answers=pol.min_calibration_answers)
        answered = [r for r in rows if r["status"] == "answered"]
        cal = cal_mod.Calibration(
            tau=res.get("tau"), alpha=pol.alpha, delta=pol.delta, n_questions=len(rows),
            n_answered=int(res.get("n_answered", len(answered))), errors=int(res.get("errors", 0)),
            upper=float(res.get("upper", 1.0)), coverage=len(answered) / max(1, len(rows)),
            surface_hash=surface_hash(surface), dataset="+".join(names), split="cal0",
            label="containment", created="")
        cal_mod.save(cal, self.workdir / "calibration" / f"{surface_hash(surface)[:16]}.json")
        return {"status": "fitted" if cal.tau is not None else "uncalibrated",
                "reason": "" if cal.tau is not None else "no threshold certified at the policy's risk target",
                "tau": cal.tau, "n": len(rows), "n_answered": cal.n_answered, "cost_usd": round(self.new_cost, 6)}

    # -- dispatcher ---------------------------------------------------------------------------

    def evaluate(self, candidate: Any, stage: str, *, cycle: int | None = None,
                 dev: Mapping | None = None) -> dict:
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage!r}; stages: {', '.join(STAGES)}")
        self.new_cost = 0.0
        if stage == "static":
            return self.static(candidate, cycle=cycle)
        if stage == "smoke":
            return self.smoke(candidate)
        if stage == "screen":
            return self.screen(candidate, cycle=cycle)
        if stage == "dev":
            return self.dev(candidate, cycle=cycle)
        return self.promote(candidate, dev=dev)
