"""Command line for heuresis. ``heuresis --help`` lists the commands (see docs/cli.md)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from . import __version__

OFFLINE_NOTICE = "notice: running fully offline with the built-in fakes (no model, no cost); pass --model and --budget for a real one."

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?)?$")


class CliError(Exception):
    """A user-facing failure: printed to stderr, exit code 2."""


# ------------------------------------------------------------------ helpers


def _date(value: str) -> str:
    import datetime as _dt

    if not _DATE_RE.match(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a date (YYYY-MM-DD)")
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a real calendar date") from None
    return value


def _timestamp(value: str) -> str:
    if not _TS_RE.match(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not an ISO date or timestamp")
    return value


def _positive(value: str) -> float:
    try:
        f = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not (f > 0) or f == float("inf"):
        raise argparse.ArgumentTypeError("must be a positive number")
    return f


def _out(args: argparse.Namespace, data: Any, text: str) -> None:
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        print(text)


def _existing_db(path: str) -> str:
    if not Path(path).is_file():
        raise CliError(f"database {path!r} does not exist; run `heuresis init {path}` first")
    return path


def _fakes() -> dict[str, Any]:
    from .fakes import EchoLLM, HashEmbedder, OverlapReranker, RuleEntailer

    return {"llm": EchoLLM(), "embedder": HashEmbedder(), "reranker": OverlapReranker(), "entailer": RuleEntailer()}


def _models(local: bool) -> dict[str, Any]:
    """Embedder, reranker and entailer: the offline fakes, or the local ONNX models."""
    kw = _fakes()
    if local:
        try:
            from . import models_local

            kw["embedder"] = models_local.load_embedder()
            kw["reranker"] = models_local.load_reranker()
            kw["entailer"] = models_local.load_entailer()
        except ImportError as e:
            raise CliError(f"--local needs the optional dependencies (pip install 'heuresis[local]'): {e}") from None
        except Exception as e:
            raise CliError(f"--local could not load the models: {type(e).__name__}: {e}") from None
    return kw


def _open(db: str, domain: str | None, *, create: bool = False, local: bool = False, llm: Any = None):
    from .engine import Engine

    if not create:
        _existing_db(db)
    kw = _models(local)
    if llm is not None:
        kw["llm"] = llm
    try:
        return Engine.open(db, domain, **kw)
    except ValueError as e:
        raise CliError(str(e)) from None


def _open_v2(args: argparse.Namespace, llm: Any):
    """``EngineV2`` over the database: the offline fakes, or the real generator (``--model``) and a
    judge model (``--judge-model``, else the policy's fixed judge model, thinking disabled)."""
    from .v2.engine import EngineV2

    _existing_db(args.db)
    kw = _models(args.local)
    judge = None
    if args.model:
        from .llm import AnthropicLLM, BudgetedLLM
        from .v2.locked.decide import load_policy

        jm = args.judge_model or load_policy().judge_model
        judge = BudgetedLLM(AnthropicLLM(jm, thinking={"type": "disabled"}), float(args.budget))
    elif args.judge_model:
        raise CliError("--judge-model needs --model (the default run is offline)")
    try:
        return EngineV2.open(args.db, None, llm=llm if llm is not None else kw["llm"], judge_llm=judge,
                             embedder=kw["embedder"])
    except ValueError as e:
        raise CliError(str(e)) from None


def _span(c: dict[str, Any]) -> str:
    return f"{c['unit_id']} @ {c['valid_from'] or ''}..{c['valid_to'] or ''}"


def _fmt_answer(d: dict[str, Any], trace: bool) -> str:
    lines = [f"status: {d['status']}"]
    if d["text"]:
        lines += ["", d["text"]]
    if d["claims"]:
        lines += ["", "claims:"]
        for c in d["claims"]:
            lines.append(f"  [{c['label']}] {c['text']}  (support {c['support']:.2f})")
            for cit in c["citations"]:
                lines.append(f"      {_span(cit)}")
            if not c["citations"]:
                lines.append("      (no citation)")
    lines += ["", f"grade: {d['grade']:.2f}"]
    ab = d["abstention"]
    if ab:
        lines.append(f"abstention: {ab['type']}: {ab['message']}")
        if ab["searched"]:
            lines.append("searched:")
            lines += [f"  {s}" for s in ab["searched"]]
        else:
            lines.append("searched: nothing in force matched")
    lines.append(f"cost: ${d['usd']:.4f}   time: {d['ms']:.1f} ms")
    if trace:
        lines += ["", _table(d["trace"])]
    return "\n".join(lines)


def _table(rows: list[dict[str, Any]]) -> str:
    head = ("stage", "ms", "tokens", "usd", "note")
    body = [(r["stage"], f"{r['ms']:.1f}", f"{r['tokens_in']}/{r['tokens_out']}", f"{r['usd']:.4f}", r["note"]) for r in rows]
    widths = [max(len(str(x[i])) for x in [head, *body]) for i in range(5)]
    fmt = lambda r: "  ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)).rstrip()  # noqa: E731
    return "\n".join([fmt(head), fmt(["-" * w for w in widths]), *[fmt(r) for r in body]])


# ------------------------------------------------------------------ commands


def cmd_init(args: argparse.Namespace) -> int:
    eng = _open(args.db, args.domain or "text", create=True)
    eng.close()
    _out(args, {"db": args.db, "domain": args.domain or "text"}, f"initialised {args.db} (domain {args.domain or 'text'})")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    if not os.path.exists(args.path):
        raise CliError(f"path {args.path!r} does not exist")
    eng = _open(args.db, args.domain, create=True)
    try:
        counts = eng.ingest(args.path)
    finally:
        eng.close()
    _out(args, {"counts": counts}, "ingested: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    eng = _open(args.db, None, local=args.local)
    try:
        n = eng.index()
    finally:
        eng.close()
    _out(args, {"embedded": n}, f"embedded {n} version(s)")
    return 0


def _real_llm(args: argparse.Namespace):
    from .llm import AnthropicLLM, BudgetedLLM

    return BudgetedLLM(AnthropicLLM(args.model), float(args.budget))


def cmd_ask(args: argparse.Namespace) -> int:
    from .mcp_edge import answer_dict
    from .model import AsOf, Scope

    if args.model and args.budget is None:
        raise CliError("--model spends real money and requires --budget USD (a hard cap); refusing to run")
    if args.budget is not None and not args.model:
        raise CliError("--budget only applies together with --model (the default run is offline and free)")
    llm = _real_llm(args) if args.model else None
    if not args.model and not args.json:
        print(OFFLINE_NOTICE, file=sys.stderr)
    if args.engine == "v2":
        eng = _open_v2(args, llm)
    else:
        if args.judge_model:
            raise CliError("--judge-model only applies with --engine v2")
        eng = _open(args.db, None, local=args.local, llm=llm)
    try:
        ans = eng.ask(args.question, as_of=AsOf(valid=args.as_of, recorded=args.recorded),
                      scope=Scope(source_ids=tuple(args.source)) if args.source else None,
                      budget_usd=args.budget if args.model else None)
    finally:
        eng.close()
    d = answer_dict(ans)
    d["offline"] = not args.model
    if not args.trace and not args.json:
        d.pop("trace", None)
    _out(args, d, _fmt_answer(d, args.trace))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    from .mcp_edge import passage_dict
    from .model import AsOf

    eng = _open(args.db, None)
    try:
        ps = eng.search(args.question, as_of=AsOf(valid=args.as_of), k=args.k)
    finally:
        eng.close()
    rows = [passage_dict(p) for p in ps]
    lines = [f"{i}. {_span(r)}  score {r['score']:.3f}  [{r['stage']}]\n   {r['text'][:200]}" for i, r in enumerate(rows, 1)]
    _out(args, {"passages": rows}, "\n".join(lines) if lines else "no passage in force at that date matched")
    return 0


def cmd_unit(args: argparse.Namespace) -> int:
    from .mcp_edge import version_dict
    from .model import AsOf

    eng = _open(args.db, None)
    try:
        v = eng.unit(args.unit_id, AsOf(valid=args.as_of))
    finally:
        eng.close()
    if v is None:
        raise CliError(f"unit {args.unit_id!r} not found, or not in force at that date")
    d = version_dict(v)
    _out(args, d, f"{_span(d)}  (certainty {d['certainty']}, recorded {d['recorded_at']})\n{d['text']}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from .mcp_edge import verify_units

    eng = _open(args.db, None)
    try:
        res = verify_units(eng, args.text, args.unit, args.as_of)
    finally:
        eng.close()
    if not res["claims"]:
        raise CliError("none of the named units is in force at that date: " + ", ".join(res["missing"]))
    lines = []
    for c in res["claims"]:
        lines.append(f"[{c['label']}] {c['text']}  (support {c['support']:.2f})")
        lines += [f"    {_span(x)}" for x in c["citations"]]
    if res["missing"]:
        lines.append("not in force: " + ", ".join(res["missing"]))
    _out(args, res, "\n".join(lines))
    return 0


def surface_hash() -> str:
    """The surface hash exactly as a benchmark run manifest records it: one implementation,
    ``heuresis.bench.systems.surface_hash`` (effective engine config, ``DRAFT_SYSTEM`` and
    the source of ``surface/prompts.py``), over the packaged default configuration."""
    from .bench.systems import surface_hash as _surface_hash

    return _surface_hash()


def cmd_hash(args: argparse.Namespace) -> int:
    from .bench.systems import prompts_hash
    from .locked import locked_hash

    d = {"locked": locked_hash(), "surface": surface_hash(), "prompts": prompts_hash()}
    _out(args, d, f"locked:  {d['locked']}\nsurface: {d['surface']}\nprompts: {d['prompts']}")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    try:
        from .bench import report as bench_report
        from .bench import run as bench_run
    except ImportError:
        raise CliError("the benchmark package heuresis.bench is not available in this installation") from None
    if args.bench_cmd == "report":
        fn = getattr(bench_report, "main", None)
        if fn is None:
            raise CliError("heuresis.bench.report has no entry point")
        return int(fn(args.rest) or 0)
    if args.paid and args.cap is None:
        raise CliError("--paid requires --cap USD")
    if args.cap is not None and not args.paid:
        raise CliError("--cap only applies together with --paid")
    fn = getattr(bench_run, "main", None)
    if fn is None:
        raise CliError("heuresis.bench.run has no entry point")
    argv = list(args.rest)
    argv += ["--paid", "--cap", str(args.cap)] if args.paid else ["--dry-run"]
    return int(fn(argv) or 0)


def cmd_lock(args: argparse.Namespace) -> int:
    from .v2.locked import manifest

    if args.check:
        diffs = manifest.verify_manifest()
        if diffs:
            _out(args, {"ok": False, "differences": diffs}, "protected files differ from PROTECTED.json:\n  " + "\n  ".join(diffs))
            return 2
        h = manifest.protected_hash()
        _out(args, {"ok": True, "protected_hash": h}, f"ok: protected files match PROTECTED.json ({h})")
        return 0
    path = manifest.write_manifest()
    h = manifest.protected_hash()
    _out(args, {"manifest": str(path), "protected_hash": h}, f"wrote {path}\nprotected hash: {h}")
    return 0


def _evolve_paid(args: argparse.Namespace, workdir: str, cfg: dict[str, Any]):
    """(ledger, context) for a paid evolve command: only the NAME of the key variable is used."""
    from .bench.ledger import Ledger
    from .evolve.api import EvalContext
    from .evolve.splits import BenchSplits

    if args.cap is None:
        raise CliError("--paid requires --cap USD")
    if not args.ledger:
        raise CliError("--paid requires --ledger PATH")
    if not args.model:
        raise CliError("--paid requires --model")
    if not args.dataset:
        raise CliError("--paid requires --dataset NAME (repeatable)")
    if not os.environ.get(args.key_env):
        raise CliError(f"environment variable {args.key_env} is not set; nothing was run "
                       f"(use --key-env NAME to read another variable)")
    from . import models_local
    from .bench.systems import BENCH_TEMPERATURE, BENCH_THINKING
    from .llm import AnthropicLLM
    from .v2.locked.decide import load_policy

    jm = args.judge_model or load_policy().judge_model
    gen = AnthropicLLM(args.model, key_env=args.key_env, temperature=BENCH_TEMPERATURE, thinking=BENCH_THINKING)
    judge = AnthropicLLM(jm, key_env=args.key_env, temperature=BENCH_TEMPERATURE, thinking=BENCH_THINKING)
    spent = Ledger(args.ledger, 0.0).spent
    ledger = Ledger(args.ledger, spent + float(args.cap), float(cfg["ledger_margin_usd"]))
    splits = BenchSplits(args.data_root, args.dataset, cfg["anchors"], rotating_n=int(cfg["rotating_n"]),
                         promo_n=int(cfg["promotion_n"]))
    ctx = EvalContext(splits=splits, llm=gen, judge_llm=judge, embedder=models_local.load_embedder(),
                      ledger=ledger, judge_model=jm)
    print(f"paid run: keys are read from the environment variable {args.key_env} (value not shown); "
          f"generator {args.model}, judge {jm}; cap US${args.cap}", file=sys.stderr)
    return ledger, ctx


def _evolve_setup(args: argparse.Namespace) -> dict[str, Any]:
    from .evolve.evaluator import load_config

    cfg = load_config()
    kw: dict[str, Any] = {"allow_unpinned": bool(getattr(args, "allow_unpinned", False))}
    if getattr(args, "paid", False):
        ledger, ctx = _evolve_paid(args, args.workdir, cfg)
        kw.update(ledger=ledger, context=ctx)
    return kw


def cmd_evolve(args: argparse.Namespace) -> int:
    from .evolve import api
    from .evolve.evaluator import ProtectedTreeError

    sub = args.evolve_cmd
    if sub == "describe":
        d = api.describe(workdir=args.workdir if Path(args.workdir, "champion.json").exists() else None)
        _out(args, d, f"champion {d['champion']['id'][:12]}  protected hash {d['protected_hash'][:12]}  "
                      f"stages: {', '.join(s['name'] for s in d['stages'])}\n(use --json for the schema)")
        return 0
    if sub == "lock-check":
        args.check = True
        return cmd_lock(args)
    if sub == "status":
        d = api.status(workdir=args.workdir)
        _out(args, d, json.dumps(d, indent=2, default=str))
        return 0
    if sub == "rollback":
        try:
            d = api.rollback(workdir=args.workdir, to=args.to, reason=args.reason)
        except ValueError as e:
            raise CliError(str(e)) from None
        _out(args, d, f"rolled back {d['from'][:12]} -> {d['to'][:12]}")
        return 0
    kw = _evolve_setup(args)
    if sub == "evaluate":
        if bool(args.candidate) == bool(args.candidate_dir):
            raise CliError("give exactly one of --candidate FILE and --candidate-dir DIR")
        src = args.candidate or args.candidate_dir
        try:
            rep = api.evaluate(src, stage=args.stage, workdir=args.workdir, **kw)
            code = 0
        except (ProtectedTreeError, ValueError, OSError) as e:
            if not args.nonce:
                raise CliError(str(e)) from None
            rep, code = {"stage": args.stage, "passed": False, "error": str(e)}, 2
        if args.nonce:
            print(f"HEURESIS-EVAL {args.nonce} " + json.dumps(rep, separators=(",", ":"), sort_keys=True))
            return code
        _out(args, rep, f"{rep['stage']}: {'passed' if rep['passed'] else 'failed'}  "
                        f"{'; '.join(rep.get('reasons', []))}  cost ${rep.get('cost_usd', 0):.4f}")
        return 0
    if sub == "promote":
        try:
            rep = api.promote(args.candidate_id, workdir=args.workdir, **kw)
        except (ProtectedTreeError, ValueError) as e:
            raise CliError(str(e)) from None
        _out(args, rep, f"promote: {'promoted' if rep['promoted'] else 'not promoted'}  "
                        f"{'; '.join(rep.get('reasons', []))}")
        return 0
    if sub == "cycle":
        from .evolve.loop import run_cycle

        extra: dict[str, Any] = {}
        if args.paid:
            from .evolve.evaluator import BenchRunner

            ctx = kw["context"]
            extra = {"runner": BenchRunner(ctx.splits, args.workdir, llm=ctx.llm, judge_llm=ctx.judge_llm,
                                           embedder=ctx.embedder, ledger=kw["ledger"]),
                     "splits": ctx.splits, "ledger": kw["ledger"], "judge_model": ctx.judge_model,
                     "datasets": args.dataset}
        elif not args.offline:
            raise CliError("give --offline (fixture, fakes, free) or --paid --cap USD --ledger PATH "
                           "--model NAME --dataset NAME")
        rep = run_cycle(args.workdir, k=args.k, cap_usd=args.cap if args.cap is not None else 10.0,
                        seed=args.seed, allow_unpinned=kw["allow_unpinned"], **extra)
        _out(args, rep, f"cycle {rep['cycle']}: {rep['status']}; candidates {len(rep['candidates'])}; "
                        f"promoted {rep['promoted'] or 'none'}; rollback "
                        f"{'yes' if rep['rollback'] else 'no'}; cost ${rep['cost_usd']:.4f}")
        return 0
    raise CliError(f"unknown evolve command {sub!r}")


# ------------------------------------------------------------------ parser


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="heuresis", description="A time-aware, verified, abstaining retrieval engine.")
    ap.add_argument("--version", action="version", version=f"heuresis {__version__}")
    sub = ap.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def add(name: str, fn: Any, help: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help, description=help)
        p.set_defaults(func=fn)
        p.add_argument("--json", action="store_true", help="print JSON instead of text")
        return p

    p = add("init", cmd_init, "create an empty database")
    p.add_argument("db")
    p.add_argument("--domain", default=None)

    p = add("ingest", cmd_ingest, "load a path into the database")
    p.add_argument("db")
    p.add_argument("path")
    p.add_argument("--domain", default=None, help="domain plug-in (default: the database's, else text)")

    p = add("index", cmd_index, "embed versions that have no vector yet")
    p.add_argument("db")
    p.add_argument("--local", action="store_true", help="use the local ONNX models")

    p = add("ask", cmd_ask, "answer a question, verified, or abstain")
    p.add_argument("db")
    p.add_argument("question")
    p.add_argument("--as-of", type=_date, default=None, metavar="DATE")
    p.add_argument("--recorded", type=_timestamp, default=None, metavar="TS")
    p.add_argument("--source", action="append", default=[], metavar="ID", help="restrict to a source id (repeatable)")
    p.add_argument("--budget", type=_positive, default=None, metavar="USD")
    p.add_argument("--local", action="store_true", help="use the local ONNX models")
    p.add_argument("--model", default=None, help="a real model (needs --budget; key from PROJECTS_ANTHROPIC_KEY)")
    p.add_argument("--trace", action="store_true", help="print the stage table")
    p.add_argument("--engine", choices=["v1", "v2"], default="v1", help="the engine (default v1)")
    p.add_argument("--judge-model", default=None, metavar="MODEL",
                   help="v2 with --model: the judge model (default: the policy's fixed judge model)")

    p = add("search", cmd_search, "retrieve passages in force at a date")
    p.add_argument("db")
    p.add_argument("question")
    p.add_argument("--as-of", type=_date, default=None, metavar="DATE")
    p.add_argument("-k", type=int, default=10)

    p = add("unit", cmd_unit, "show one unit as it read at a date")
    p.add_argument("db")
    p.add_argument("unit_id")
    p.add_argument("--as-of", type=_date, default=None, metavar="DATE")

    p = add("verify", cmd_verify, "verify a text against named units in force at a date")
    p.add_argument("db")
    p.add_argument("--text", required=True)
    p.add_argument("--unit", action="append", required=True, metavar="UNIT_ID")
    p.add_argument("--as-of", type=_date, default=None, metavar="DATE")

    p = add("hash", cmd_hash, "print the locked-folder hash, the surface hash and the baseline prompts hash")

    p = add("lock", cmd_lock, "write PROTECTED.json (hashes of every protected file); --check verifies it")
    p.add_argument("--check", action="store_true", help="exit 2 listing the differences instead of writing")

    p = add("evolve", cmd_evolve, "the improvement loop over the v2 engine (docs/evolve.md)")
    ev = p.add_subparsers(dest="evolve_cmd", required=True, metavar="SUBCOMMAND")

    def eadd(name: str, help: str, paid: bool = False) -> argparse.ArgumentParser:
        q = ev.add_parser(name, help=help, description=help)
        q.add_argument("--json", action="store_true", help="print JSON instead of text")
        q.add_argument("--workdir", default="evolve_runs", help="working directory (default evolve_runs)")
        if name not in ("describe", "status", "rollback", "lock-check"):
            q.add_argument("--allow-unpinned", action="store_true",
                           help="run although the protected files differ from PROTECTED.json (pre-lock builds, tests)")
            q.add_argument("--paid", action="store_true", help="paid run; needs --cap --ledger --model --dataset")
            q.add_argument("--cap", type=_positive, default=None, metavar="USD")
            q.add_argument("--ledger", default=None, metavar="PATH")
            q.add_argument("--model", default=None)
            q.add_argument("--judge-model", default=None, help="default: the policy's fixed judge model")
            q.add_argument("--key-env", default="PROJECTS_ANTHROPIC_KEY", metavar="NAME",
                           help="name of the environment variable holding the key (only the name is used)")
            q.add_argument("--dataset", action="append", default=[], metavar="NAME")
            q.add_argument("--data-root", default="data")
        return q

    eadd("describe", "schema, bounds, champion, stages and budget as JSON")
    q = eadd("evaluate", "run one stage on one candidate")
    q.add_argument("--candidate", metavar="FILE")
    q.add_argument("--candidate-dir", metavar="DIR", help="a directory that mirrors v2/surface/")
    q.add_argument("--stage", required=True, choices=["static", "smoke", "screen", "dev", "promote"])
    q.add_argument("--nonce", default=None, help="print exactly one line 'HEURESIS-EVAL <nonce> <json>'")
    q = eadd("promote", "run the promotion test on an archived candidate and promote it if it passes")
    q.add_argument("candidate_id")
    q = eadd("rollback", "restore the previous champion")
    q.add_argument("--to", default=None, metavar="ID")
    q.add_argument("--reason", default="manual")
    eadd("status", "champion, counters, spend")
    q = eadd("cycle", "run one whole cycle")
    q.add_argument("--k", type=int, default=None, help="candidates per cycle (default from config.json)")
    q.add_argument("--seed", type=int, default=None)
    q.add_argument("--offline", action="store_true", help="the packaged fixture with fakes; free")
    eadd("lock-check", "exit 2 if a protected file differs from PROTECTED.json")

    p = add("bench", cmd_bench, "run or report the benchmark (dry run by default)")
    p.add_argument("bench_cmd", choices=["run", "report"])
    p.add_argument("--dry-run", action="store_true", help="the default: no paid call is made")
    p.add_argument("--paid", action="store_true", help="make paid calls (needs --cap)")
    p.add_argument("--cap", type=_positive, default=None, metavar="USD")
    p.add_argument("rest", nargs=argparse.REMAINDER, help="passed to the benchmark")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except CliError as e:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        print(f"error: {e}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
    except Exception as e:  # never a traceback for the user
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
