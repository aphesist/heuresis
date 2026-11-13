"""The decision rule: answered, partial, divergent or abstained, with a confidence score."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ...model import Abstention, Claim, Passage, Query
from .gates import deterministic_failure
from .judge import Verdict

_CERT = {"low": 0.33, "medium": 0.66, "high": 1.0}
POLICY_PATH = Path(__file__).with_name("policy.json")


@dataclass(frozen=True)
class Policy:
    alpha: float
    delta: float
    default_tau: float
    grid: tuple[float, ...]
    min_calibration_answers: int
    values: dict[str, float]


@dataclass
class Decision:
    status: str
    confidence: float = 0.0
    abstention: Abstention | None = None
    kept: list[int] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def load_policy(path=None) -> Policy:
    d = json.loads(Path(path or POLICY_PATH).read_text(encoding="utf-8"))
    return Policy(float(d["alpha"]), float(d["delta"]), float(d["default_tau"]),
                  tuple(float(x) for x in d["grid"]), int(d["min_calibration_answers"]),
                  {k: float(v) for k, v in d["values"].items()})


def _judged(claims: list[Claim]) -> list[int]:
    """Indexes (in ``claims``) of the claims the judge saw: those that passed the gates.
    Verdict sentence ``j`` (0-based) is the ``j``-th of these."""
    return [i for i, c in enumerate(claims) if not deterministic_failure(c)]


def _word(claim: Claim, verdict: Verdict, j: int) -> str:
    w = verdict.sentences.get(j, "NOT_SUPPORTED" if claim.kind != "derived" else "NOT_FOLLOWS")
    if claim.kind == "derived":
        return "FOLLOWS" if w == "FOLLOWS" else "NOT_FOLLOWS"
    return w if w in ("SUPPORTED", "PARTIAL") else "NOT_SUPPORTED"


def _by_mark(passages: list[Passage]) -> dict[str, Passage]:
    return {p.mark: p for p in passages if p.mark}


def confidence(claims, kept, verdict, passages, policy) -> float:
    """Min of the lowest kept-sentence value, the ANSWER value, the SUFFICIENT value, the
    lowest certainty and the lowest coverage / 4 of the cited passages; times ``dropped`` when
    the judge dropped a sentence."""
    if not kept:
        return 0.0
    v = policy.values
    judged = _judged(claims)
    pos = {i: j for j, i in enumerate(judged)}
    parts: list[float] = []
    for i in kept:
        w = _word(claims[i], verdict, pos.get(i, -1))
        parts.append(v.get(w, 0.0))
    parts.append(v["DIRECT"] if verdict.answer == "DIRECT" else v["ANSWER_PARTIAL"])
    parts.append(v["SUFFICIENT_YES"] if verdict.sufficient == "YES" else v["SUFFICIENT_NO"])
    bm = _by_mark(passages)
    cited = [bm[m] for i in kept for m in claims[i].passage_marks if m in bm]
    if cited:
        parts.append(min(_CERT.get(p.certainty, 0.0) for p in cited))
        parts.append(min(p.coverage for p in cited) / 4)
    score = min(parts)
    dropped = any(_word(claims[i], verdict, pos[i]) in ("NOT_SUPPORTED", "NOT_FOLLOWS")
                  for i in judged)
    if dropped:
        score *= v["dropped"]
    return max(0.0, min(1.0, score))


def _abstain(typ: str, msg: str, passages: list[Passage], reason: str | None = None) -> Decision:
    return Decision("abstained", 0.0,
                    Abstention(typ, msg, [p.title or p.unit_id for p in passages]),
                    [], [reason or msg])


def _valid_at(p: Passage, query: Query, store) -> bool:
    if store is not None:
        v = store.text_at(p.unit_id, query.as_of)
        return v is not None and v.seq == p.seq
    d = query.as_of.valid
    return d is None or ((p.valid_from is None or p.valid_from <= d)
                         and (p.valid_to is None or d < p.valid_to))


def _authority(p: Passage, store) -> int:
    if store is None:
        return 0
    s = store.get_source(p.source_id)
    return s.authority if s is not None else 0


def decide(claims: list[Claim], verdict: Verdict | None, passages: list[Passage],
           query: Query, policy: Policy, *, tau: float | None = None, store=None,
           declined: str | None = None) -> Decision:
    # 1. the model declined
    if declined:
        return _abstain(declined, "The model declined to answer.", passages,
                        f"model declined: {declined}")
    # 2. nothing to work with
    if not passages:
        return _abstain("no_source", "No relevant source was found.", passages)
    if not claims:
        return _abstain("unsupported", "The draft made no checkable claim.", passages)
    # 3. deterministic gates
    failing = [c for c in claims if deterministic_failure(c)]
    for c in failing:
        c.label, c.support = "unsupported", 0.0
    cited_ok = [c for c in claims if c.kind != "derived" and not deterministic_failure(c)]
    if not cited_ok:
        cited_fail = [c for c in failing if c.kind != "derived"] or failing
        only_date = bool(cited_fail) and all(
            not c.checks.get("valid_at_date", True) and c.checks.get("exists", True)
            and c.checks.get("numbers_traced", True)
            and c.checks.get("references_traced", True) for c in cited_fail)
        if only_date:
            return _abstain("not_valid_at_date", "No cited source was in force at the date.",
                            passages)
        return _abstain("unsupported", "The draft could not be verified.", passages)
    # 4. the judge
    if verdict is None or not verdict.readable:
        return _abstain("unsupported", "The judge's reply could not be read.", passages,
                        "judge unreadable")
    # 5. false premise
    if verdict.premise == "FALSE":
        return _abstain("false_premise", "The sources contradict what the question assumes.",
                        passages)
    judged = _judged(claims)
    bm = _by_mark(passages)
    # 6. conflict between two equal-authority passages in force
    if verdict.conflict:
        a, b = (bm.get(m) for m in verdict.conflict)
        if (a is not None and b is not None and a.unit_id != b.unit_id
                and _valid_at(a, query, store) and _valid_at(b, query, store)
                and _authority(a, store) == _authority(b, store)):
            ma, mb = verdict.conflict
            kept = [i for j, i in enumerate(judged)
                    if _word(claims[i], verdict, j) in ("SUPPORTED", "PARTIAL", "FOLLOWS")]
            conf = confidence(claims, kept, verdict, passages, policy) if kept else 0.0
            return Decision(
                "divergent", conf,
                Abstention("conflict", f"Sources of equal authority disagree: {ma} and {mb}.",
                           [p.title or p.unit_id for p in (a, b)]),
                kept, [f"conflict between {ma} and {mb}"])
    # 7. sentence verdicts
    kept: list[int] = []
    reasons: list[str] = []
    for j, i in enumerate(judged):
        c = claims[i]
        w = _word(c, verdict, j)
        if w in ("SUPPORTED", "FOLLOWS"):
            c.label, c.support = "supported", policy.values.get(w, 0.0)
            kept.append(i)
        elif w == "PARTIAL":
            c.label, c.support = "partial", policy.values.get("PARTIAL", 0.0)
            kept.append(i)
        else:
            c.label, c.support = "unsupported", 0.0
            reasons.append(f"dropped by the judge: {c.text}")
            c.note = "; ".join(x for x in (c.note, "dropped by the judge") if x)
    if not any(claims[i].kind != "derived" for i in kept):
        return _abstain("unsupported", "No sentence is supported by the sources.", passages,
                        "no cited sentence is supported")
    # 8. does it answer
    if verdict.answer == "NO":
        return _abstain("unsupported", "The text does not answer the question.", passages)
    if verdict.sufficient == "NO" and verdict.answer != "DIRECT":
        return _abstain("no_source", "The sources found do not settle the question.", passages)
    # 9-10. confidence and threshold
    conf = confidence(claims, kept, verdict, passages, policy)
    t = policy.default_tau if tau is None else tau
    if conf < t:
        d = _abstain("unsupported", "The confidence is below the threshold.", passages,
                     f"below the confidence threshold ({conf:.2f} < {t:.2f})")
        d.confidence, d.kept = conf, []
        return d
    # 11.
    status = "answered" if len(kept) == len(claims) else "partial"
    return Decision(status, conf, None, kept, reasons)
