"""Tripwires of the improvement loop (docs/design-v2.md section (f)), each a pure function.

A ``Trip`` has a name, a severity (``stop_cycle``, ``stop_candidate`` or ``flag``) and a detail text
that never contains gold answers or question text. By default the first four stop the cycle, a
tainted anchor or a doubled cost stops the candidate, and an implausible jump or a dev-versus-
promotion gap only flags. Severities can be overridden by passing ``severity`` (the loop reads them
from ``config.json``). Honeypots and canaries are not statistical detectors; they catch crude leaks.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from ..v2.locked.schema import CANARY_MARKER

DEFAULT_SEVERITY: dict[str, str] = {
    "protected_file_changed": "stop_cycle",
    "invalid_surface": "stop_cycle",
    "canary_marker": "stop_cycle",
    "canary_answered": "stop_cycle",
    "tainted_anchor": "stop_candidate",
    "implausible_jump": "flag",
    "dev_promotion_gap": "flag",
    "cost_doubled": "stop_candidate",
}
SEVERITIES = ("stop_cycle", "stop_candidate", "flag")


@dataclass(frozen=True)
class Trip:
    name: str
    severity: str
    detail: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _sev(name: str, severity: Mapping[str, str] | None) -> str:
    s = (severity or {}).get(name, DEFAULT_SEVERITY[name])
    return s if s in SEVERITIES else DEFAULT_SEVERITY[name]


def _has_marker(text: object) -> bool:
    return CANARY_MARKER.lower() in str(text or "").lower()


def protected_file_changed(differences: Sequence[str], severity=None) -> list[Trip]:
    """A protected file differs from the manifest (``manifest.verify_manifest``)."""
    if not differences:
        return []
    shown = "; ".join(list(differences)[:5]) + (" ..." if len(differences) > 5 else "")
    return [Trip("protected_file_changed", _sev("protected_file_changed", severity),
                 f"{len(differences)} difference(s): {shown}")]


def invalid_surface(problems: Sequence[str], severity=None) -> list[Trip]:
    """The candidate is not a valid surface (schema, bounds, path guard, unreadable files)."""
    if not problems:
        return []
    shown = "; ".join(list(problems)[:5]) + (" ..." if len(problems) > 5 else "")
    return [Trip("invalid_surface", _sev("invalid_surface", severity),
                 f"{len(problems)} violation(s): {shown}")]


def canary_marker(prompts: Mapping[str, str] | None = None, rows: Sequence[Mapping] = (),
                  severity=None) -> list[Trip]:
    """The canary marker appears in a prompt, or in any answer text (the decoy was read, or gold
    leaked)."""
    where = [f"prompt {n}" for n, t in (prompts or {}).items() if _has_marker(t)]
    where += [f"answer {r.get('qid', '?')}" for r in rows
              if _has_marker(r.get("text")) or r.get("has_marker")]
    if not where:
        return []
    return [Trip("canary_marker", _sev("canary_marker", severity),
                 "marker found in " + ", ".join(where[:5]) + (" ..." if len(where) > 5 else ""))]


def canary_answered(canary_rows: Sequence[Mapping], threshold: float, severity=None) -> list[Trip]:
    """The engine answers more than ``threshold`` of the canary questions: the candidate taught it
    to stop refusing."""
    n = len(canary_rows)
    if n == 0:
        return []
    k = sum(1 for r in canary_rows if r.get("status") == "answered")
    if k / n > threshold:
        return [Trip("canary_answered", _sev("canary_answered", severity),
                     f"{k} of {n} canary questions answered (threshold {threshold:.2f})")]
    return []


def tainted_anchor(anchor_rows: Sequence[Mapping], severity=None) -> list[Trip]:
    """An answer on an anchor question has a fabricated or out-of-force citation (the gates were
    bypassed). Rows whose ``tainted`` is None were not checkable and do not count."""
    bad = [r for r in anchor_rows if r.get("status") == "answered" and r.get("tainted") is True]
    if not bad:
        return []
    return [Trip("tainted_anchor", _sev("tainted_anchor", severity),
                 f"{len(bad)} answer(s) with a fabricated or out-of-force citation on anchor questions")]


def implausible_jump(diff: float, se: float | None, k_se: float, severity=None) -> list[Trip]:
    """The dev score exceeds the champion's by more than ``k_se`` standard errors: confirm on the
    promotion set, never trust."""
    if diff is None or se is None or not math.isfinite(diff) or se <= 0:
        return []
    if diff > k_se * se:
        return [Trip("implausible_jump", _sev("implausible_jump", severity),
                     f"dev gain {diff:.3f} is {diff / se:.1f} standard errors")]
    return []


def dev_promotion_gap(dev_gain: float, dev_se: float, promo_gain: float, promo_se: float,
                      k_se: float, severity=None) -> list[Trip]:
    """The dev gain exceeds the promotion gain by more than ``k_se`` standard errors of the
    difference (an overfitting flag)."""
    vals = (dev_gain, dev_se, promo_gain, promo_se)
    if any(v is None or not math.isfinite(v) for v in vals):
        return []
    se = math.sqrt(dev_se ** 2 + promo_se ** 2)
    if se <= 0:
        return []
    gap = dev_gain - promo_gain
    if gap > k_se * se:
        return [Trip("dev_promotion_gap", _sev("dev_promotion_gap", severity),
                     f"dev gain {dev_gain:.3f} against promotion gain {promo_gain:.3f}: gap "
                     f"{gap / se:.1f} standard errors")]
    return []


def cost_doubled(candidate_cost: float, champion_cost: float, ratio: float, severity=None) -> list[Trip]:
    """Cost per question is more than ``ratio`` times the champion's (no trip without a cost
    baseline)."""
    if champion_cost is None or candidate_cost is None or champion_cost <= 0:
        return []
    if candidate_cost > ratio * champion_cost:
        return [Trip("cost_doubled", _sev("cost_doubled", severity),
                     f"cost per question {candidate_cost:.5f} against {champion_cost:.5f} "
                     f"(more than {ratio:g} times)")]
    return []


def stops_cycle(trips: Sequence[Trip]) -> bool:
    return any(t.severity == "stop_cycle" for t in trips)


def stops_candidate(trips: Sequence[Trip]) -> bool:
    return any(t.severity in ("stop_cycle", "stop_candidate") for t in trips)
