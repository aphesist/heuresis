"""Resumable benchmark runner.

Output folder: ``results.jsonl`` (one row per (system, question id)) and
``manifest.json``. Rows are graded at write time with ``heuresis.locked.scoring``.

Grading rule: an answerable question is answered correctly when any gold answer,
normalised (SQuAD rules plus accent folding), occurs in the normalised answer text
on token boundaries. Citation marks such as ``[t1]`` are removed first. Token F1
against the best gold answer is stored alongside.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Sequence

from ..locked import scoring
from ..locked.guard import locked_hash
from ..surface.config import config_to_dict
from .ledger import BudgetExceeded, Ledger
from .systems import (
    BENCH_TEMPERATURE, BENCH_THINKING, SYSTEM_NAMES, BenchContext, System, prompts_hash,
)
from .systems import surface_hash as _surface_hash
from .types import Dataset, Question

PRICE_TABLE = "anthropic-2026-11"
DEFAULT_KEY_ENV = "PROJECTS_ANTHROPIC_KEY"
_MARK = re.compile(r"\[[tk]\d+\]")


def _norm(s: str) -> str:
    return scoring.normalize_answer(s, fold_accents=True)


def is_correct(text: str, golds: Sequence[str]) -> bool:
    """True when any gold answer is contained (on token boundaries) in the text."""
    hay = f" {_norm(_MARK.sub(' ', text))} "
    return any(g and f" {g} " in hay for g in map(_norm, golds))


def grade(q: Question, status: str, text: str) -> dict:
    clean = _MARK.sub(" ", text)
    if q.answerable and status == "answered":
        ok: bool | None = is_correct(text, q.answers)
    else:
        ok = None
    out = scoring.outcome(status, ok, q.answerable)
    f1 = scoring.best_over_golds(scoring.token_f1, clean, q.answers, fold_accents=True) \
        if (q.answerable and status == "answered") else None
    return {"outcome": out, "correct": out == "correct", "score": scoring.penalised_score(out),
            "f1": f1}


def surface_hash(ctx: BenchContext) -> str:
    """The run's surface hash: the one implementation in ``systems.surface_hash`` (also
    printed by ``heuresis hash``), over the context's configuration."""
    return _surface_hash(ctx.config)


def select_questions(questions: Sequence[Question], limit: int | None, seed: int) -> list[Question]:
    qs = sorted(questions, key=lambda q: q.id)
    if limit is not None and limit < len(qs):
        qs = random.Random(seed).sample(qs, limit)
        qs.sort(key=lambda q: q.id)
    return qs


def _read_rows(path: str) -> list[dict]:
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    if isinstance(r, dict):
                        rows.append(r)
                except ValueError:
                    continue
    return rows


def _meta(q: Question, split: str, s: System) -> dict:
    return {"system": s.name, "qid": q.id, "split": split, "answerable": q.answerable,
            "as_of": q.as_of, "kind": q.kind, "cluster": q.cluster,
            "gold_units": list(q.gold_units), "time_aware": s.time_aware,
            "exploratory": s.exploratory}


def _error_row(q: Question, split: str, s: System, error: str, ms: float,
               res: Any = None) -> dict:
    """The row for an API or model failure after retries, the same for every system. The
    report counts it as outcome "wrong"; a restart retries it."""
    row = {**_meta(q, split, s), "status": "error", "outcome": "error", "error": error[:500],
           "ms": ms}
    if res is not None:
        row.update({"tokens_in": res.usage.tokens_in, "tokens_out": res.usage.tokens_out,
                    "usd": res.usage.usd, "calls": res.calls, "searches": res.searches,
                    "stage_ms": res.stage_ms, "note": res.note})
    return row


def _row(q: Question, split: str, s: System, res: Any) -> dict:
    g = grade(q, res.status, res.text)
    row = {
        "system": s.name, "qid": q.id, "split": split, "status": res.status, "text": res.text,
        "confidence": res.confidence, "cited_units": list(res.cited_units),
        "retrieved_units": list(res.retrieved_units), "tokens_in": res.usage.tokens_in,
        "tokens_out": res.usage.tokens_out, "usd": res.usage.usd, "ms": res.ms,
        "calls": res.calls, "searches": res.searches, "note": res.note,
        "answerable": q.answerable, "as_of": q.as_of, "kind": q.kind, "cluster": q.cluster,
        "gold_units": list(q.gold_units), "time_aware": s.time_aware,
        "exploratory": s.exploratory, "stage_ms": res.stage_ms, **g,
    }
    if res.usage.stop_reason:  # one entry per model call, as the API reported it
        row["stop_reasons"] = res.usage.stop_reason.split(",")
        row["blocks"] = dict(res.usage.blocks)
        row["text_chars"] = int(res.usage.text_chars)
    if res.replay is not None:
        row["replay"] = res.replay
    return row


def run(dataset: Dataset, split: str, systems: Sequence[System], out_dir: str,
        ledger: Ledger | None, *, limit: int | None = None, workers: int = 4, seed: int = 0,
        dry_run: bool = False, params: dict | None = None) -> dict:
    if split not in dataset.questions:
        raise ValueError(f"unknown split {split!r}; have {sorted(dataset.questions)}")
    os.makedirs(out_dir, exist_ok=True)
    results_path = os.path.join(out_dir, "results.jsonl")
    manifest_path = os.path.join(out_dir, "manifest.json")
    if ledger is not None and dry_run:
        ledger.dry_run, ledger.margin_usd = True, 0.0  # a $0 run is never stopped by the cap
    active = [s for s in systems if s.available]
    qs = select_questions(dataset.questions[split], limit, seed)

    if os.path.exists(results_path):
        with open(results_path, "rb") as fh:
            data = fh.read()
        if data and not data.endswith(b"\n"):
            with open(results_path, "ab") as fh:
                fh.write(b"\n")
    done = {(r["system"], r["qid"]) for r in _read_rows(results_path) if r.get("status") != "error"}

    ctx = systems[0].ctx if systems else None
    prior = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8") as fh:
                prior = json.load(fh)
        except ValueError:
            prior = {}
    manifest = {
        "dataset": dataset.name, "licence": dataset.licence, "corpus_tokens": dataset.corpus_tokens,
        "split": split, "n_questions": len(qs), "question_ids": [q.id for q in qs],
        "limit": limit, "seed": seed, "workers": workers, "dry_run": dry_run,
        "systems": [s.describe() for s in systems], "locked_hash": locked_hash(),
        "prompts_hash": prompts_hash(), "price_table": PRICE_TABLE, "params": params or {},
        "latency_note": (f"ms is wall-clock around System.answer, measured the same way for every "
                         f"system, with {workers} concurrent workers; stage_ms (engine only) is "
                         f"the sum of the engine's stage timings"),
        "first_started": prior.get("first_started") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ledger": None if ledger is None else {"path": ledger.path, "cap_usd": ledger.cap_usd,
                                               "margin_usd": ledger.margin_usd},
    }
    if ctx is not None:
        manifest["config"] = config_to_dict(ctx.config)
        manifest["engine_config"] = config_to_dict(ctx.engine_config())
        manifest["surface_hash"] = surface_hash(ctx)
        manifest["models"] = ctx.models()
        manifest["model_provenance"] = ctx.provenance()

    pending = [(q, s) for q in qs for s in active if (s.name, q.id) not in done]
    stats = {"written": 0, "skipped": len(qs) * len(active) - len(pending), "errors": 0,
             "stopped": None}
    wlock = threading.Lock()

    def work(item: tuple[Question, System]) -> dict:
        q, s = item
        if ledger is not None and not dry_run:
            ledger.check(0.0)
        t0 = time.perf_counter()
        try:
            res = s.answer(q)
        except BudgetExceeded:
            raise
        except Exception as e:  # recorded; retried on the next start
            return _error_row(q, split, s, f"{type(e).__name__}: {e}",
                              (time.perf_counter() - t0) * 1000.0)
        res.ms = (time.perf_counter() - t0) * 1000.0  # the same clock for every system
        if res.error:  # a model failure the system could detect but not raise
            return _error_row(q, split, s, res.error, res.ms, res)
        return _row(q, split, s, res)

    with open(results_path, "a", encoding="utf-8") as out, ThreadPoolExecutor(max(1, workers)) as ex:
        it = iter(pending)
        inflight: set = set()
        stop = False
        while True:
            while not stop and len(inflight) < max(1, workers) * 2:
                item = next(it, None)
                if item is None:
                    break
                inflight.add(ex.submit(work, item))
            if not inflight:
                break
            finished, inflight = wait(inflight, return_when=FIRST_COMPLETED)
            for f in finished:
                try:
                    row = f.result()
                except BudgetExceeded:
                    stop = True
                    stats["stopped"] = "budget"
                    continue
                with wlock:
                    out.write(json.dumps(row, sort_keys=True) + "\n")
                    out.flush()
                stats["written"] += 1
                if row.get("status") == "error":
                    stats["errors"] += 1
                if ledger is not None and not dry_run and ledger.remaining <= 0.0:
                    stop = True
                    stats["stopped"] = "budget"

    manifest["last_run"] = dict(stats)
    manifest["spent_usd"] = None if ledger is None else ledger.spent
    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    os.replace(tmp, manifest_path)
    return stats


# ----------------------------------------------------------------------------
# Command line
# ----------------------------------------------------------------------------


def _load_dataset(name: str) -> Dataset:
    from . import datasets  # owned by another package; imported only when needed
    for fn in ("load_dataset", "load", "get_dataset"):
        if hasattr(datasets, fn):
            return getattr(datasets, fn)(name)
    raise SystemExit("heuresis.bench.datasets offers no loader (load_dataset/load/get_dataset)")


def main(argv: Sequence[str] | None = None) -> int:
    from ..fakes import EchoLLM, HashEmbedder, OverlapReranker, RuleEntailer
    from .systems import build_context, build_systems
    ap = argparse.ArgumentParser(prog="python -m heuresis.bench.run")
    ap.add_argument("--dataset", help="dataset name, resolved by heuresis.bench.datasets")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--systems", default=",".join(SYSTEM_NAMES))
    ap.add_argument("--out", help="output folder (default: bench_out/<dataset>-<split>)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="offline fakes, costs nothing (the default)")
    ap.add_argument("--paid", action="store_true", help="call the paid model; needs --cap")
    ap.add_argument("--cap", "--cap-usd", dest="cap_usd", type=float, default=None,
                    help="spend cap in USD")
    ap.add_argument("--margin-usd", type=float, default=1.0)
    ap.add_argument("--estimate-usd", type=float, default=0.02)
    ap.add_argument("--ledger", help="ledger path (default for a dry run: <out>/ledger.jsonl); "
                                     "REQUIRED with --paid, so that every paid run shares one ledger")
    ap.add_argument("--key-env", default=DEFAULT_KEY_ENV, metavar="NAME",
                    help=f"name of the environment variable that holds the API key "
                         f"(default: {DEFAULT_KEY_ENV}); only the name is ever printed")
    ap.add_argument("--model", help="generator model (default: the config's draft model)")
    ap.add_argument("--time-aware", action="store_true", help="baselines 2-6 search as of the question date")
    ap.add_argument("--time-aware-variants", action="store_true",
                    help="also build time-aware copies of bm25, vector, hybrid, hybrid_rerank and "
                         "agentic, named with the suffix +asof (exploratory in the report)")
    ap.add_argument("--agent-rerank", action="store_true",
                    help="the agentic search tool uses hybrid_rerank instead of hybrid")
    ap.add_argument("--thinking", choices=("disabled", "default"), default="disabled",
                    help="'disabled' (default) sends thinking={'type': 'disabled'} on every call of "
                         "every system, so max_tokens bounds the visible answer; 'default' sends "
                         "nothing and leaves the model's own default (adaptive thinking on)")
    ap.add_argument("--set", dest="overrides", action="append", default=[], metavar="SECTION.KEY=VALUE",
                    help="override one packaged config value for this run (repeatable), e.g. "
                         "--set draft.prompt=v1 or --set verify.answers_question=true; the value is read "
                         "as JSON when it parses, else as text; the manifest records the resulting config")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--agent-k", type=int, default=5)
    ap.add_argument("--max-actions", type=int, default=4)
    ap.add_argument("--long-context-limit", type=int, default=90_000)
    ap.add_argument("--embedder")
    ap.add_argument("--reranker")
    ap.add_argument("--entailer")
    a = ap.parse_args(argv)
    if not a.dataset:
        print("error: --dataset is required", file=sys.stderr)
        return 2
    if a.paid and a.cap_usd is None:
        print("error: --paid requires --cap USD", file=sys.stderr)
        return 2
    if a.paid and not a.ledger:
        print("error: --paid requires --ledger PATH: one ledger shared by every paid run, so two "
              "runs can never each believe they have the whole cap", file=sys.stderr)
        return 2
    if a.paid and not os.environ.get(a.key_env):
        print(f"error: environment variable {a.key_env} is not set; nothing was run "
              f"(use --key-env NAME to read another variable)", file=sys.stderr)
        return 2
    a.dry_run = a.dry_run or not a.paid  # a paid run is never the default
    if a.cap_usd is None:
        a.cap_usd = 10.0
    a.out = a.out or os.path.join("bench_out", f"{a.dataset}-{a.split}")

    from ..surface.config import load_config
    cfg = load_config()
    if a.overrides:
        from ..surface.config import config_from_dict, config_to_dict
        d = config_to_dict(cfg)
        for item in a.overrides:
            try:
                path, raw = item.split("=", 1)
                section, key = path.split(".", 1)
                if section not in d or key not in d[section]:
                    raise KeyError(path)
            except (ValueError, KeyError):
                print(f"error: --set {item!r}: expected an existing SECTION.KEY=VALUE", file=sys.stderr)
                return 2
            try:
                value = json.loads(raw)
            except ValueError:
                value = raw
            d[section][key] = value
        try:
            cfg = config_from_dict(d)
        except ValueError as e:
            print(f"error: --set: {e}", file=sys.stderr)
            return 2
    paid_llm = None
    if a.paid:  # built, and announced, before any work: only the variable NAME is shown
        from ..llm import AnthropicLLM
        paid_llm = AnthropicLLM(a.model or cfg.draft.model, key_env=a.key_env,
                                temperature=BENCH_TEMPERATURE,
                                thinking=BENCH_THINKING if a.thinking == "disabled" else None)
        print(f"paid run: the API key is read from the environment variable {a.key_env} "
              f"(value not shown); requests go to {paid_llm.base_url}; no temperature "
              f"is sent; thinking {'disabled' if a.thinking == 'disabled' else 'left at the model default'}",
              file=sys.stderr)
    ds = _load_dataset(a.dataset)
    os.makedirs(a.out, exist_ok=True)
    # A dry run costs nothing: no safety margin, and the ledger never stops it.
    ledger = Ledger(a.ledger or os.path.join(a.out, "ledger.jsonl"), a.cap_usd,
                    a.margin_usd, dry_run=a.dry_run)
    if a.dry_run:
        llm, emb, rr, ent = EchoLLM(), HashEmbedder(), OverlapReranker(), RuleEntailer()
    else:
        from .. import models_local
        llm = paid_llm
        emb = models_local.load_embedder(a.embedder) if a.embedder else models_local.load_embedder()
        rr = models_local.load_reranker(a.reranker) if a.reranker else models_local.load_reranker()
        ent = models_local.load_entailer(a.entailer) if a.entailer else models_local.load_entailer()
    ctx = build_context(ds, os.path.join(a.out, "store.sqlite"), llm=llm, embedder=emb,
                        reranker=rr, entailer=ent, config=cfg, ledger=ledger,
                        estimate_usd=a.estimate_usd)
    systems = build_systems(ctx, [s for s in a.systems.split(",") if s], k=a.k,
                            agent_k=a.agent_k, max_actions=a.max_actions,
                            time_aware=a.time_aware, long_context_limit=a.long_context_limit,
                            agent_rerank=a.agent_rerank,
                            time_aware_variants=a.time_aware_variants)
    stats = run(ds, a.split, systems, a.out, ledger, limit=a.limit, workers=a.workers,
                seed=a.seed, dry_run=a.dry_run, params=vars(a))
    print(json.dumps({**stats, "spent_usd": ledger.spent}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
