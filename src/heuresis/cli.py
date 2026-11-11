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
    """sha256 of the canonical JSON of the default surface configuration."""
    from .surface import config_to_dict, load_config

    blob = json.dumps(config_to_dict(load_config()), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cmd_hash(args: argparse.Namespace) -> int:
    from .locked import locked_hash

    d = {"locked": locked_hash(), "surface": surface_hash()}
    _out(args, d, f"locked:  {d['locked']}\nsurface: {d['surface']}")
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

    p = add("hash", cmd_hash, "print the locked-folder hash and the surface config hash")

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
