"""The understand stage: runs before any search and decides how to search.

Layer 1 is a set of zero-cost rules (date extraction and intent patterns, plus
any caller-supplied rules). Layer 2 is an optional classifier, consulted only
when no intent rule fired or when intent rules disagree. When the classifier is
not confident the router asks one short question instead of guessing.

Date conventions (the contract does not say; these are the choices made here):

* An explicit day (``2024-03-15``, ``15/03/2024``) maps to that day.
* A full day with a month name ("4th February 1928", "February 4, 1928",
  "4 de fevereiro de 1928", "1º de março de 2024") maps to that exact day.
* A month ("March 2024", "em março de 2024", "março/2024") maps to the LAST
  day of that month. "As of March 2024" is read as "the state of the corpus at
  the end of that month", which is the latest state a person naming the month
  can mean.
* A bare year ("in 2019", "em 2019") maps to 31 December of that year, for the
  same reason.
* "today" / "hoje" map to ``today`` (default: the UTC date).
* When several dates appear, the one that appears first in the text wins.
* ``dated`` is True whenever ``as_of.valid`` came from the question text.

Intent precedence when no classifier is supplied and several intent rules fire
with different intents: the first one in firing order wins (caller rules, then
built-ins in the order out_of_scope, compute, multi_hop, table).
"""
from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Sequence

import numpy as np

from .model import INTENTS, AsOf, Query, Scope

if TYPE_CHECKING:  # pragma: no cover
    from .interfaces import Embedder, Rule
    from .surface.config import RouterCfg

__all__ = ["understand", "NearestIntent"]

# ----------------------------------------------------------------------------
# Dates
# ----------------------------------------------------------------------------

_MONTHS: dict[str, int] = {}
for _i, _names in enumerate(
    [
        ("january", "janeiro"),
        ("february", "fevereiro"),
        ("march", "marco"),
        ("april", "abril"),
        ("may", "maio"),
        ("june", "junho"),
        ("july", "julho"),
        ("august", "agosto"),
        ("september", "setembro"),
        ("october", "outubro"),
        ("november", "novembro"),
        ("december", "dezembro"),
    ],
    start=1,
):
    for _n in _names:
        _MONTHS[_n] = _i


def _fold(text: str) -> str:
    """Lower-case and strip accents, keeping string length stable for most text."""
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.category(ch) == "Mn":
            continue
        out.append(ch.lower())
    return "".join(out)


_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_RE_ISO = re.compile(r"(?<![\d/.-])(\d{4})-(\d{2})-(\d{2})(?![\d])")
_RE_DMY = re.compile(r"(?<![\d/.-])(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})(?![\d])")
_RE_MONTH_YEAR = re.compile(
    rf"\b({_MONTH_ALT})(?:\s+de|\s*[/,-]|\s)\s*(\d{{4}})\b"
)
_ORD = r"(?:st|nd|rd|th|\u00ba|\u00b0|o)?"
_RE_DAY_MONTH_YEAR = re.compile(
    rf"(?<![\d/.-])(\d{{1,2}}){_ORD}\s+(?:de\s+|of\s+)?({_MONTH_ALT})"
    rf"(?:\s+de\s+|\s*,\s*|\s+)(\d{{4}})\b"
)
_RE_MONTH_DAY_YEAR = re.compile(
    rf"\b({_MONTH_ALT})\s+(\d{{1,2}}){_ORD}\s*,?\s*(\d{{4}})\b"
)
_RE_BARE_YEAR = re.compile(r"\b(?:in|em|during|durante)\s+((?:19|20)\d{2})\b")
_RE_TODAY = re.compile(r"\b(today|hoje)\b")


def _valid_date(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def _extract_date(text: str, today: str) -> str | None:
    folded = _fold(text)
    found: list[tuple[int, str]] = []
    for m in _RE_ISO.finditer(folded):
        iso = _valid_date(int(m[1]), int(m[2]), int(m[3]))
        if iso:
            found.append((m.start(), iso))
    for m in _RE_DMY.finditer(folded):
        iso = _valid_date(int(m[3]), int(m[2]), int(m[1]))
        if iso:
            found.append((m.start(), iso))
    day_spans: list[tuple[int, int]] = []
    for rx, order in ((_RE_DAY_MONTH_YEAR, (3, 2, 1)), (_RE_MONTH_DAY_YEAR, (3, 1, 2))):
        for m in rx.finditer(folded):
            y_i, mo_i, d_i = order
            mo = _MONTHS[m[mo_i]]
            iso = _valid_date(int(m[y_i]), mo, int(m[d_i]))
            if iso:
                found.append((m.start(), iso))
                day_spans.append(m.span())
    for m in _RE_MONTH_YEAR.finditer(folded):
        if any(a <= m.start() < b for a, b in day_spans):
            continue  # the month and year belong to a full date already found
        y, mo = int(m[2]), _MONTHS[m[1]]
        if 1 <= y <= 9999:
            last = calendar.monthrange(y, mo)[1]
            iso = _valid_date(y, mo, last)
            if iso:
                found.append((m.start(), iso))
    for m in _RE_BARE_YEAR.finditer(folded):
        found.append((m.start(), f"{int(m[1]):04d}-12-31"))
    for m in _RE_TODAY.finditer(folded):
        found.append((m.start(), today))
    if not found:
        return None
    return min(found, key=lambda t: t[0])[1]


# ----------------------------------------------------------------------------
# Intent rules
# ----------------------------------------------------------------------------

_GREETINGS = (
    "good morning", "good afternoon", "good evening", "good night", "thank you",
    "thanks", "hello", "hi", "hey", "ok", "okay", "bye", "goodbye", "please",
    "bom dia", "boa tarde", "boa noite", "muito obrigado", "muito obrigada",
    "obrigado", "obrigada", "ola", "oi", "tchau", "valeu", "por favor",
    "there", "tudo bem", "everyone", "pessoal", "a todos",
)
_RE_GREETING = re.compile(
    r"\b(?:" + "|".join(sorted((re.escape(g) for g in _GREETINGS), key=len, reverse=True)) + r")\b"
)


def _is_empty_or_greeting(text: str) -> bool:
    folded = _fold(text)
    if not re.search(r"[a-z0-9]", folded):
        return True
    rest = _RE_GREETING.sub(" ", folded)
    return not re.search(r"[a-z0-9]", rest)


_RE_DATES_STRIP = re.compile(
    r"\d{4}-\d{2}-\d{2}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}|\d{1,2}[/.\-]\d{4}"
)
_RE_ARITH = re.compile(
    r"\d\s*[+*/×÷^]\s*\d|\d\s+[-x]\s+\d|\d\s*%"
)
_RE_COMPUTE_WORDS = re.compile(
    r"\b(how\s+much|how\s+many|total|sum|average|percent|percentage|"
    r"calculate|compute|quanto|quantos|quanta|quantas|calcule|calcular|"
    r"soma|media|porcentagem|percentual|somar)\b"
)

_RE_HOP_OF_THE_THAT = re.compile(
    r"\bthe\s+(?:\w+\s+){1,3}of\s+the\s+(?:[\w'-]+\s+){1,4}(?:that|who|which|whose)\b"
)
_RE_HOP_WHO = re.compile(r"\bwho\b.*\bthe\b.*\bof\b")
_RE_HOP_COMPARE = re.compile(
    r"\b(compare|comparison|difference\s+between|versus|vs\.?|"
    r"(?:more|less|higher|lower|larger|smaller|older|newer)\s+\w+\s+than|"
    r"between\s+.+\s+and\s+.+)\b"
)
_RE_HOP_PT = re.compile(
    r"\b(?:o|a|os|as)\s+(?:\w+\s+){1,3}(?:do|da|dos|das|de)\s+(?:\w+\s+){1,4}"
    r"(?:que|cujo|cuja|onde)\b"
)
_RE_HOP_PT_WHO = re.compile(r"\bquem\b.*\b(?:o|a|os|as)\b.*\b(?:do|da|dos|das|de)\b")
_RE_HOP_PT_COMPARE = re.compile(
    r"\b(compare|comparacao|diferenca\s+entre|versus|"
    r"(?:mais|menos|maior|menor)\s+\w+\s+(?:do\s+)?que|entre\s+.+\s+e\s+.+)\b"
)

_RE_TABLE = re.compile(
    r"\b(sql|select\b.*\bfrom|join|group\s+by|order\s+by|tables?|columns?|rows?|"
    r"tabelas?|colunas?|linhas?)\b"
)


def _rule_out_of_scope(text: str, scope: Scope) -> str | None:
    return "out_of_scope" if _is_empty_or_greeting(text) else None


def _rule_compute(text: str, scope: Scope) -> str | None:
    folded = _fold(text)
    stripped = _RE_DATES_STRIP.sub(" ", folded)
    if _RE_ARITH.search(stripped) or _RE_COMPUTE_WORDS.search(stripped):
        return "compute"
    return None


def _rule_multi_hop(text: str, scope: Scope) -> str | None:
    f = _fold(text)
    for rx in (
        _RE_HOP_OF_THE_THAT, _RE_HOP_WHO, _RE_HOP_COMPARE,
        _RE_HOP_PT, _RE_HOP_PT_WHO, _RE_HOP_PT_COMPARE,
    ):
        if rx.search(f):
            return "multi_hop"
    return None


def _rule_table(text: str, scope: Scope) -> str | None:
    if "schema" in scope.kinds and _RE_TABLE.search(_fold(text)):
        return "table"
    return None


_BUILTIN_INTENT_RULES: tuple[Callable[[str, Scope], str | None], ...] = (
    _rule_out_of_scope,
    _rule_compute,
    _rule_multi_hop,
    _rule_table,
)

# ----------------------------------------------------------------------------
# Layer 2: nearest-neighbour classifier
# ----------------------------------------------------------------------------


class NearestIntent:
    """Nearest-neighbour intent classifier over an ``Embedder``.

    ``examples`` are ``(text, intent)`` pairs (a pair given as ``(intent, text)``
    is detected and swapped when only its first item is a known intent). The
    score of a label is the highest cosine similarity between the query and any
    example of that label. Confidence is the margin between the best and the
    runner-up label (runner-up floored at 0), clipped to 0..1; with a single
    label the runner-up score is taken as 0, so confidence is the similarity.
    """

    def __init__(self, embedder: "Embedder", examples: Sequence[tuple[str, str]]):
        self.embedder = embedder
        texts: list[str] = []
        labels: list[str] = []
        for a, b in examples:
            text, label = (b, a) if (a in INTENTS and b not in INTENTS) else (a, b)
            if isinstance(text, str) and text.strip():
                texts.append(text)
                labels.append(str(label))
        self.labels = labels
        self._vecs = (
            np.asarray(embedder.embed(texts), dtype=np.float32) if texts else None
        )

    def ranked(self, text: str) -> list[tuple[str, float]]:
        """Labels with their best similarity, highest first (ties by label)."""
        if self._vecs is None or not self.labels:
            return []
        q = np.asarray(
            self.embedder.embed([text], is_query=True), dtype=np.float32
        )[0]
        sims = self._vecs @ q
        best: dict[str, float] = {}
        for label, s in zip(self.labels, sims):
            s = float(s)
            if label not in best or s > best[label]:
                best[label] = s
        return sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))

    def __call__(self, text: str) -> tuple[str, float]:
        try:
            ranked = self.ranked(text if isinstance(text, str) else "")
        except Exception:
            return ("lookup", 0.0)
        if not ranked:
            return ("lookup", 0.0)
        best_label, s1 = ranked[0]
        s2 = ranked[1][1] if len(ranked) > 1 else 0.0
        if s1 <= 0.0:
            return (best_label, 0.0)
        conf = s1 - max(s2, 0.0)
        return (best_label, float(min(1.0, max(0.0, conf))))


# ----------------------------------------------------------------------------
# understand
# ----------------------------------------------------------------------------

_QUERY_FIELDS = {"text", "as_of", "scope", "intent", "confidence", "clarify",
                 "decided_by", "dated"}
_INTENT_LABEL = {
    "lookup": "a direct lookup",
    "multi_hop": "a question that chains several facts",
    "compute": "a calculation",
    "table": "a table query",
    "out_of_scope": "something outside this corpus",
}


def _clarify_question(a: str, b: str) -> str:
    return (
        f"Do you want {_INTENT_LABEL.get(a, a)} or "
        f"{_INTENT_LABEL.get(b, b)}?"
    )


def _as_asof(value: Any) -> AsOf | None:
    if isinstance(value, AsOf):
        return value
    if isinstance(value, dict):
        try:
            return AsOf(**value)
        except TypeError:
            return None
    return None


def understand(
    text: str,
    *,
    cfg: "RouterCfg",
    rules: "Sequence[Rule]" = (),
    classifier: Callable[[str], tuple[str, float]] | None = None,
    as_of: AsOf | None = None,
    scope: Scope | None = None,
    today: str | None = None,
) -> Query:
    """Turn a raw question into a ``Query``. Never raises on odd input."""
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    scope = scope if isinstance(scope, Scope) else Scope()
    default_intent = getattr(cfg, "default_intent", "lookup")
    threshold = float(getattr(cfg, "ask_threshold", 0.6))
    today_iso = today if isinstance(today, str) and today else (
        datetime.now(timezone.utc).date().isoformat()
    )

    fields: dict[str, Any] = {}
    fired: list[str] = []  # intents from intent rules, in firing order

    # Caller rules first; they can set any Query field.
    for rule in rules or ():
        try:
            out = rule(text)
        except Exception:
            continue
        if not isinstance(out, dict):
            continue
        for key, val in out.items():
            if key not in _QUERY_FIELDS or key == "text":
                continue
            if key == "intent":
                if val in INTENTS:
                    fired.append(val)
                continue
            if key == "as_of":
                val = _as_asof(val)
                if val is None:
                    continue
            fields[key] = val

    # Built-in intent rules.
    if not text.strip():
        fired.append("out_of_scope")
    else:
        for rule in _BUILTIN_INTENT_RULES:
            intent = rule(text, scope)
            if intent:
                fired.append(intent)

    # Date extraction: caller as_of > rule-set as_of > extracted from text.
    dated = bool(fields.get("dated", False))
    if as_of is not None:
        final_as_of = as_of
        dated = bool(fields.get("dated", False))
    elif "as_of" in fields:
        final_as_of = fields["as_of"]
    else:
        iso = _extract_date(text, today_iso)
        if iso:
            final_as_of = AsOf(valid=iso)
            dated = True
        else:
            final_as_of = AsOf()

    distinct = list(dict.fromkeys(fired))
    intent = default_intent
    confidence = 1.0
    decided_by = "default"
    clarify: str | None = fields.get("clarify")

    if len(distinct) == 1 or (distinct and classifier is None):
        # An empty/greeting text is never overridden by a collision.
        intent = "out_of_scope" if "out_of_scope" in distinct else distinct[0]
        decided_by = "rules"
    elif classifier is not None:
        c_intent, c_conf = None, 0.0
        try:
            c_intent, c_conf = classifier(text)
            c_conf = float(c_conf)
        except Exception:
            c_intent, c_conf = None, 0.0
        if c_intent in INTENTS and c_conf == c_conf:  # also filters NaN
            c_conf = min(1.0, max(0.0, c_conf))
            decided_by = "classifier"
            if c_conf < threshold:
                if clarify is None:
                    others: list[str] = []
                    ranked = getattr(classifier, "ranked", None)
                    if callable(ranked):
                        try:
                            others = [l for l, _ in ranked(text) if l in INTENTS]
                        except Exception:
                            others = []
                    cands = list(dict.fromkeys([c_intent, *others, *distinct,
                                                default_intent]))
                    cands = [c for c in cands if c in INTENTS]
                    first = c_intent
                    second = next((c for c in cands if c != first), default_intent)
                    clarify = _clarify_question(first, second)
                intent, confidence = default_intent, c_conf
            else:
                intent, confidence = c_intent, c_conf
        elif distinct:
            intent, decided_by = distinct[0], "rules"

    return Query(
        text=text,
        as_of=final_as_of,
        scope=fields.get("scope", scope) if isinstance(fields.get("scope", scope), Scope) else scope,
        intent=intent,
        confidence=confidence,
        clarify=clarify,
        decided_by=decided_by,
        dated=dated,
    )
