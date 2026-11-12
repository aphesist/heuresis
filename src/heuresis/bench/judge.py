"""Secondary, judge-assisted grade (exploratory). The deterministic containment grade of
``bench.run.grade`` stays the PRIMARY measure and is never changed or overwritten.

For every ANSWERED row of EVERY system that the containment grader marked wrong on an
answerable question, ``claude-haiku-5-5`` (the generator's own model family; thinking turned
off, the shared ledger) is asked one question: given the question, the gold answers and the
system's answer, does the answer state the same answer as a gold answer? Reply
EQUIVALENT or NOT_EQUIVALENT, nothing else. Unanswerable questions, abstentions, correct rows
and error rows are never judged. Verdicts go to ``<run_dir>/judge.jsonl`` (one JSON row per
judged (system, question), resumable); ``bench.report`` reads that file and adds the secondary
columns. Dev run folders only.

Command line: ``python -m heuresis.bench.judge RUN_DIR [RUN_DIR ...] [--paid --cap USD
--ledger PATH ...]``. Without ``--paid`` nothing is called and the number of rows to judge is
printed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Sequence

from . import report
from .ledger import BudgetExceeded, Ledger, LedgerLLM

__all__ = ["JUDGE_SYSTEM", "judge_prompt", "parse_verdict", "candidates", "judge_folder",
           "load_verdicts", "main"]

JUDGE_FILE = "judge.jsonl"
_MARK = re.compile(r"\[[tk]\d+\]")

JUDGE_SYSTEM = (
    "You compare a system's answer with the gold answers to a question. Reply with exactly one "
    "word: EQUIVALENT if the answer states the same answer as at least one gold answer (a "
    "paraphrase, a different word order or unit spelling, or extra correct detail around the "
    "gold answer is fine), NOT_EQUIVALENT otherwise (a different answer, an intermediate or "
    "partial answer, or a statement that does not answer the question)."
)


def judge_prompt(question: str, golds: Sequence[str], answer: str) -> str:
    clean = " ".join(_MARK.sub(" ", answer).split())
    gold = " | ".join(g for g in golds if g)
    return (f"Question: {question}\nGold answers: {gold}\nSystem answer: {clean}\n"
            "EQUIVALENT or NOT_EQUIVALENT?")


def parse_verdict(raw: str) -> str | None:
    word = (raw or "").strip().upper().replace(" ", "_").split("\n")[0]
    if word.startswith("NOT_EQUIVALENT") or word.startswith("NOT"):
        return "NOT_EQUIVALENT"
    if word.startswith("EQUIVALENT"):
        return "EQUIVALENT"
    return None


def candidates(rows: Sequence[dict]) -> list[dict]:
    """The rows to judge: answered, answerable, graded wrong by the containment grader."""
    return [r for r in rows if r.get("status") == "answered" and r.get("answerable", True)
            and r.get("outcome") == "wrong"]


def load_verdicts(run_dir: str) -> dict[tuple[str, str], dict]:
    path = os.path.join(run_dir, JUDGE_FILE)
    out: dict[tuple[str, str], dict] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    out[(r["system"], r["qid"])] = r
                except (ValueError, KeyError, TypeError):
                    continue
    return out


def judge_folder(run_dir: str, questions: dict[str, Any], llm: Any, *, workers: int = 4,
                 max_tokens: int = 10, dry_run: bool = False) -> dict:
    """Judge one dev run folder. ``questions`` maps question id to a ``Question`` (dev only);
    ``llm`` is the metered generator. Returns counts. A budget stop ends the folder cleanly."""
    manifest, rows, _ = report.load(run_dir)
    if manifest.get("split") != "dev":
        raise ValueError(f"{run_dir}: manifest split is {manifest.get('split')!r}, not 'dev'; refusing")
    cand = candidates(rows)
    done = load_verdicts(run_dir)
    todo = [r for r in cand if done.get((r["system"], r["qid"]), {}).get("verdict") is None]
    stats = {"candidates": len(cand), "already": len(cand) - len(todo), "judged": 0,
             "unreadable": 0, "stopped": False}
    if dry_run:
        stats["to_judge"] = len(todo)
        return stats
    path = os.path.join(run_dir, JUDGE_FILE)

    def one(r: dict):
        q = questions[r["qid"]]
        raw, u = llm.complete(JUDGE_SYSTEM, judge_prompt(q.text, q.answers, r.get("text") or ""),
                              max_tokens=max_tokens)
        return r, raw, u

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex, open(path, "a", encoding="utf-8") as fh:
        futs = [ex.submit(one, r) for r in todo]
        for f in futs:
            try:
                r, raw, u = f.result()
            except BudgetExceeded:
                stats["stopped"] = True
                continue
            v = parse_verdict(raw)
            stats["judged"] += 1
            stats["unreadable"] += v is None
            fh.write(json.dumps({"system": r["system"], "qid": r["qid"], "verdict": v,
                                 "raw": (raw or "")[:40], "tokens_in": u.tokens_in,
                                 "tokens_out": u.tokens_out, "usd": u.usd,
                                 "stop_reason": u.stop_reason}, sort_keys=True) + "\n")
            fh.flush()
    return stats


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m heuresis.bench.judge", description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir", nargs="+")
    ap.add_argument("--paid", action="store_true", help="call the paid model; needs --cap and --ledger")
    ap.add_argument("--cap", "--cap-usd", dest="cap_usd", type=float)
    ap.add_argument("--margin-usd", type=float, default=1.0)
    ap.add_argument("--estimate-usd", type=float, default=0.02)
    ap.add_argument("--ledger")
    ap.add_argument("--key-env", default="PROJECTS_ANTHROPIC_KEY", metavar="NAME")
    ap.add_argument("--model", default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=20,
                    help="output cap of each judge call (default 20: ten cuts NOT_EQUIVALENT)")
    a = ap.parse_args(argv)
    if a.paid and (a.cap_usd is None or not a.ledger):
        print("error: --paid needs --cap USD and --ledger PATH (the one shared ledger)", file=sys.stderr)
        return 2
    if a.paid and not os.environ.get(a.key_env):
        print(f"error: environment variable {a.key_env} is not set; nothing was run", file=sys.stderr)
        return 2
    from .run import _load_dataset
    from .systems import BENCH_THINKING
    from ..surface.config import load_config
    llm = None
    if a.paid:
        from ..llm import AnthropicLLM
        inner = AnthropicLLM(a.model or load_config().draft.model, key_env=a.key_env,
                             thinking=BENCH_THINKING)
        print(f"judge run: the API key is read from the environment variable {a.key_env} (value not "
              f"shown); requests go to {inner.base_url}; thinking disabled", file=sys.stderr)
        ledger = Ledger(a.ledger, a.cap_usd, a.margin_usd)
        llm = LedgerLLM(inner, ledger, "judge", a.estimate_usd)
    rc = 0
    for d in a.run_dir:
        manifest, _rows, _ = report.load(d)
        if manifest.get("split") != "dev":
            print(f"error: {d}: manifest split is {manifest.get('split')!r}, not 'dev'; refusing",
                  file=sys.stderr)
            return 2
        ds = _load_dataset(manifest["dataset"])
        qs = {q.id: q for q in ds.questions["dev"]}
        st = judge_folder(d, qs, llm, workers=a.workers, max_tokens=a.max_tokens, dry_run=not a.paid)
        print(json.dumps({"run_dir": d, **st}))
        if st["stopped"]:
            rc = 1
            print("the ledger stopped the judge run; stopping", file=sys.stderr)
            break
    return rc


if __name__ == "__main__":
    sys.exit(main())
