"""``dates``: calendar arithmetic on ISO dates.

Args by operation (dates are ``YYYY-MM-DD``; a full ISO timestamp is accepted
and its date part is used):

* ``{"op": "diff", "start": d, "end": d, "unit": "days"|"months"|"years"}``
  Signed ``end - start``. Months and years are whole units: the largest ``n``
  such that ``add(start, n units) <= end`` (same clamping as ``add``); negative
  when ``end`` is before ``start``. ``unit`` defaults to days.
* ``{"op": "add", "date": d, "days": n, "months": n, "years": n}``
  Any subset of the three integers (default 0). Years and months are applied
  first, clamped to the end of the target month (Jan 31 + 1 month = Feb 28/29,
  Feb 29 + 1 year = Feb 28), then days.
* ``{"op": "weekday", "date": d}`` -> English weekday name.
* ``{"op": "is_before", "a": d, "b": d}`` -> True when ``a`` is strictly before ``b``.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Any

from ..model import ToolResult

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_LIMIT = 10**6


class DateError(ValueError):
    pass


def _parse(v: Any, field: str) -> date:
    if not isinstance(v, str) or not v.strip():
        raise DateError(f"'{field}' must be an ISO date string")
    s = v.strip()
    try:
        return date.fromisoformat(s) if len(s) == 10 else datetime.fromisoformat(s).date()
    except ValueError:
        raise DateError(f"'{field}' is not a valid ISO date: {v!r}") from None


def _int(v: Any, field: str) -> int:
    n = None
    if isinstance(v, int) and not isinstance(v, bool):
        n = v
    elif isinstance(v, float) and v.is_integer():
        n = int(v)
    elif isinstance(v, str):
        try:
            n = int(v.strip())
        except ValueError:
            pass
    if n is None:
        raise DateError(f"'{field}' must be an integer")
    if abs(n) > _LIMIT:
        raise DateError(f"'{field}' out of range")
    return n


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    m += 1
    if not 1 <= y <= 9999:
        raise DateError("result out of range")
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _whole_months(s: date, e: date) -> int:
    m = (e.year - s.year) * 12 + e.month - s.month
    while add_months(s, m) > e:
        m -= 1
    return m


def _diff(a: dict) -> tuple[Any, list[str]]:
    s, e = _parse(a.get("start"), "start"), _parse(a.get("end"), "end")
    unit = a.get("unit", "days")
    if unit not in ("days", "months", "years"):
        raise DateError("unit must be days, months or years")
    sign, lo, hi = (1, s, e) if s <= e else (-1, e, s)
    days = (e - s).days
    steps = [f"{s.isoformat()} to {e.isoformat()}: {days} days ({_DAYS[s.weekday()]} to {_DAYS[e.weekday()]})"]
    if unit == "days":
        return days, steps
    m = _whole_months(lo, hi)
    if unit == "years":
        n = m // 12
        anchor = add_months(lo, 12 * n)
        steps.append(f"{n} whole years: {lo.isoformat()} + {n} years = {anchor.isoformat()}, remainder {(hi - anchor).days} days")
    else:
        n = m
        anchor = add_months(lo, n)
        steps.append(f"{n} whole months: {lo.isoformat()} + {n} months = {anchor.isoformat()}, remainder {(hi - anchor).days} days")
    if sign < 0:
        steps.append("end is before start, so the result is negative")
    return sign * n, steps


def _add(a: dict) -> tuple[Any, list[str]]:
    d = _parse(a.get("date"), "date")
    years, months, days = (_int(a.get(k, 0), k) for k in ("years", "months", "days"))
    steps = [f"start {d.isoformat()}"]
    cur = d
    if years or months:
        cur = add_months(d, years * 12 + months)
        note = " (clamped to the end of the month)" if cur.day != d.day else ""
        steps.append(f"+ {years} years {months} months = {cur.isoformat()}{note}")
    if days:
        try:
            cur = cur + timedelta(days=days)
        except OverflowError:
            raise DateError("result out of range") from None
        steps.append(f"+ {days} days = {cur.isoformat()}")
    return cur.isoformat(), steps


def _weekday(a: dict) -> tuple[Any, list[str]]:
    d = _parse(a.get("date"), "date")
    return _DAYS[d.weekday()], [f"{d.isoformat()} is a {_DAYS[d.weekday()]} (ISO weekday {d.isoweekday()})"]


def _is_before(a: dict) -> tuple[Any, list[str]]:
    x, y = _parse(a.get("a"), "a"), _parse(a.get("b"), "b")
    r = x < y
    rel = "<" if x < y else (">" if x > y else "==")
    return r, [f"{x.isoformat()} {rel} {y.isoformat()}, so is_before is {r}"]


_OPS = {"diff": _diff, "add": _add, "weekday": _weekday, "is_before": _is_before}


class DatesTool:
    name = "dates"
    description = (
        'Date arithmetic. args: {"op": "diff", "start", "end", "unit": days|months|years} | '
        '{"op": "add", "date", "days"/"months"/"years"} | {"op": "weekday", "date"} | '
        '{"op": "is_before", "a", "b"}. Dates are ISO (YYYY-MM-DD).'
    )

    def run(self, mark: str, args: dict[str, Any]) -> ToolResult:
        a = dict(args) if isinstance(args, dict) else {}
        try:
            if not isinstance(args, dict):
                raise DateError("args must be an object")
            fn = _OPS.get(args.get("op"))
            if fn is None:
                raise DateError("op must be one of diff, add, weekday, is_before")
            value, steps = fn(args)
            return ToolResult(mark, self.name, a, True, value, steps)
        except DateError as e:
            return ToolResult(mark, self.name, a, False, error=str(e))
        except Exception as e:
            return ToolResult(mark, self.name, a, False, error=f"internal error: {type(e).__name__}")
