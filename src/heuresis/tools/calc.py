"""``calc``: safe decimal arithmetic.

The expression is parsed with ``ast`` and only a whitelist of nodes is
evaluated, with ``decimal.Decimal`` (never binary floats).

Args: ``{"expr": str, "locale": "en" | "pt" (optional)}``.

Grammar: numeric literals, ``+ - * / // %``, ``**`` (integer exponent with
absolute value <= 100), unary ``+``/``-``, parentheses, and the functions
``min``, ``max`` (varargs or one list literal), ``sum`` (one list literal),
``abs`` and ``round``.  ``//`` and ``%`` follow Python's floor semantics.
``round(x, n)`` rounds half up (accounting convention, unlike Python's
half-even) to ``n`` decimals, ``-30 <= n <= 30``.  Arithmetic runs at 60
significant digits; ``+ - *`` of ordinary figures are exact, a division that
does not terminate is rounded at 60 digits.

Numbers, separators and percent signs:

* No ``locale``: ``.`` is the decimal point, ``,`` only separates function
  arguments, and no thousands separators are accepted (``1,234.56`` and
  ``1.234,56`` are both rejected as ambiguous).  ``_`` may group digits.
* ``locale="en"``: ``1,234.56`` is 1234.56 (comma groups of three, ``.``
  decimal).  ``locale="pt"``: ``1.234,56`` is 1234.56.  In both locales a
  mis-grouped number is rejected, and arguments are separated by ``;`` or by a
  comma followed by a space.
* ``;`` always works as an argument separator.
* ``N%`` after a numeric literal means ``N/100`` (``5%`` is 0.05, with no
  "percent of" semantics).  A ``%`` followed by an operand (digit, ``(``, name,
  ``-``) is the modulo operator: ``10 % 3`` is 1, ``5% * 2`` is 0.1.
"""
from __future__ import annotations

import ast
import decimal
import re
from decimal import Decimal
from typing import Any

from ..model import ToolResult

MAX_EXPR_CHARS = 500
MAX_NODES = 300
MAX_EXPONENT = 100
_CTX = decimal.Context(
    prec=60,
    rounding=decimal.ROUND_HALF_EVEN,
    Emin=-1000,
    Emax=1000,
    traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow],
)

_NUM_TOKEN = re.compile(r"\d+(?:[.,]\d+)*")
_EN_GROUPED = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
_EN_PLAIN = re.compile(r"\d+(?:\.\d+)?")
_PT_GROUPED = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?")
_PT_PLAIN = re.compile(r"\d+(?:,\d+)?")
_PERCENT = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?|\.\d+)\s*%(?!\s*[\d.(\-A-Za-z_\[])"
)


class CalcError(ValueError):
    pass


def _normalise_numbers(expr: str, locale: str | None) -> str:
    if locale is None:
        return expr

    def fix(m: re.Match) -> str:
        tok = m.group(0)
        if locale == "en":
            if _EN_GROUPED.fullmatch(tok):
                return tok.replace(",", "")
            if _EN_PLAIN.fullmatch(tok):
                return tok
        else:
            if _PT_GROUPED.fullmatch(tok) or _PT_PLAIN.fullmatch(tok):
                return tok.replace(".", "").replace(",", ".")
        raise CalcError(
            f"number '{tok}' is not valid for locale '{locale}' "
            "(use comma+space or ';' to separate function arguments)"
        )

    return _NUM_TOKEN.sub(fix, expr)


def _fmt(d: Decimal) -> str:
    if d == 0:
        return "0"
    return format(d.normalize(_CTX), "f")


def _to_int(d: Decimal, what: str) -> int:
    if d != d.to_integral_value():
        raise CalcError(f"{what} must be an integer, got {_fmt(d)}")
    return int(d)


class _Evaluator:
    def __init__(self, source: str):
        self.source = source
        self.steps: list[str] = []

    def eval(self, node: ast.AST) -> Decimal:
        m = getattr(self, "_" + type(node).__name__, None)
        if m is None:
            if isinstance(node, ast.Tuple):
                raise CalcError(
                    "comma outside a function call; thousands separators need "
                    'locale "en" or "pt"'
                )
            raise CalcError(f"construct not allowed: {type(node).__name__}")
        return m(node)

    def _Expression(self, node: ast.Expression) -> Decimal:
        return self.eval(node.body)

    def _Constant(self, node: ast.Constant) -> Decimal:
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalcError(f"literal not allowed: {node.value!r}")
        seg = ast.get_source_segment(self.source, node) or ""
        if not re.fullmatch(r"[0-9_]*\.?[0-9_]*", seg) or not re.search(r"\d", seg):
            raise CalcError(f"numeric literal not allowed: {seg!r}")
        if len(seg.replace("_", "")) > 60:
            raise CalcError("numeric literal too long")
        return Decimal(seg.replace("_", ""))

    def _UnaryOp(self, node: ast.UnaryOp) -> Decimal:
        v = self.eval(node.operand)
        if isinstance(node.op, ast.USub):
            r = _CTX.minus(v)
            self.steps.append(f"-({_fmt(v)}) = {_fmt(r)}")
            return r
        if isinstance(node.op, ast.UAdd):
            return v
        raise CalcError(f"operator not allowed: {type(node.op).__name__}")

    def _BinOp(self, node: ast.BinOp) -> Decimal:
        a = self.eval(node.left)
        b = self.eval(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            sym, r = "+", _CTX.add(a, b)
        elif isinstance(op, ast.Sub):
            sym, r = "-", _CTX.subtract(a, b)
        elif isinstance(op, ast.Mult):
            sym, r = "*", _CTX.multiply(a, b)
        elif isinstance(op, ast.Div):
            if b == 0:
                raise CalcError("division by zero")
            sym, r = "/", _CTX.divide(a, b)
        elif isinstance(op, (ast.FloorDiv, ast.Mod)):
            if b == 0:
                raise CalcError("division by zero")
            q = _CTX.divide_int(a, b)
            rem = _CTX.remainder(a, b)
            if rem != 0 and ((rem < 0) != (b < 0)):
                q = _CTX.subtract(q, 1)
                rem = _CTX.add(rem, b)
            if isinstance(op, ast.FloorDiv):
                sym, r = "//", q
            else:
                sym, r = "%", rem
        elif isinstance(op, ast.Pow):
            e = _to_int(b, "exponent")
            if abs(e) > MAX_EXPONENT:
                raise CalcError(f"exponent {e} too large (limit {MAX_EXPONENT})")
            if e == 0:
                r = Decimal(1)
            elif a == 0 and e < 0:
                raise CalcError("division by zero")
            else:
                r = _CTX.power(a, e)
            sym = "**"
        else:
            raise CalcError(f"operator not allowed: {type(op).__name__}")
        r = _CTX.plus(r)
        self.steps.append(f"{_fmt(a)} {sym} {_fmt(b)} = {_fmt(r)}")
        return r

    def _list_items(self, node: ast.AST) -> list[Decimal]:
        if not isinstance(node, ast.List):
            raise CalcError("expected a list literal like [1, 2, 3]")
        if not node.elts:
            raise CalcError("empty list")
        return [self.eval(e) for e in node.elts]

    def _Call(self, node: ast.Call) -> Decimal:
        if not isinstance(node.func, ast.Name) or node.func.id not in (
            "min", "max", "round", "abs", "sum",
        ):
            raise CalcError("call not allowed (only min, max, round, abs, sum)")
        if node.keywords:
            raise CalcError("keyword arguments not allowed")
        name = node.func.id
        args = node.args
        if any(isinstance(a, ast.Starred) for a in args):
            raise CalcError("starred arguments not allowed")
        if name == "sum":
            if len(args) != 1:
                raise CalcError("sum takes one list literal")
            vals = self._list_items(args[0])
            total = Decimal(0)
            for v in vals:
                total = _CTX.add(total, v)
            r = total
            shown = "[" + ", ".join(_fmt(v) for v in vals) + "]"
        elif name in ("min", "max"):
            if len(args) == 1 and isinstance(args[0], ast.List):
                vals = self._list_items(args[0])
            elif args:
                vals = [self.eval(a) for a in args]
            else:
                raise CalcError(f"{name} needs at least one value")
            r = min(vals) if name == "min" else max(vals)
            shown = ", ".join(_fmt(v) for v in vals)
        elif name == "abs":
            if len(args) != 1:
                raise CalcError("abs takes one value")
            v = self.eval(args[0])
            r = abs(v)
            shown = _fmt(v)
        else:  # round
            if len(args) not in (1, 2):
                raise CalcError("round takes a value and optional digits")
            v = self.eval(args[0])
            n = _to_int(self.eval(args[1]), "digits") if len(args) == 2 else 0
            if not -30 <= n <= 30:
                raise CalcError("round digits must be between -30 and 30")
            r = v.quantize(
                Decimal(1).scaleb(-n), rounding=decimal.ROUND_HALF_UP, context=_CTX
            )
            shown = f"{_fmt(v)}, {n}"
        self.steps.append(f"{name}({shown}) = {_fmt(r)}")
        return r


def evaluate(expr: str, locale: str | None = None) -> tuple[Decimal, list[str]]:
    """Evaluate ``expr``; raises ``CalcError`` on any problem."""
    if not isinstance(expr, str) or not expr.strip():
        raise CalcError("expr must be a non-empty string")
    if locale not in (None, "en", "pt"):
        raise CalcError("locale must be 'en' or 'pt'")
    if len(expr) > MAX_EXPR_CHARS:
        raise CalcError("expression too long")
    if "\n" in expr or "\r" in expr:
        raise CalcError("expression must be a single line")
    text = _normalise_numbers(expr.strip(), locale).replace(";", ",")
    text = _PERCENT.sub(lambda m: f"({m.group(1)}/100)", text)
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, RecursionError, MemoryError, ValueError) as e:
        raise CalcError(
            f"cannot parse expression ({type(e).__name__}); '%' as a percent "
            "sign must directly follow a numeric literal"
        ) from None
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise CalcError("expression too complex")
    ev = _Evaluator(text)
    try:
        value = ev.eval(tree)
    except decimal.DecimalException as e:
        raise CalcError(f"arithmetic error: {type(e).__name__}") from None
    except RecursionError:
        raise CalcError("expression too deeply nested") from None
    return value, [f"expression: {text}"] + ev.steps


class CalcTool:
    name = "calc"
    description = (
        'Exact decimal arithmetic. args: {"expr": "1200 * 6%", "locale": "en"|"pt" optional}. '
        "Supports + - * / // % **, parentheses, min max round abs sum. Returns the exact value as a string."
    )

    def run(self, mark: str, args: dict[str, Any]) -> ToolResult:
        a = dict(args) if isinstance(args, dict) else {}
        try:
            if not isinstance(args, dict):
                raise CalcError("args must be an object")
            value, steps = evaluate(args.get("expr"), args.get("locale"))
            return ToolResult(mark, self.name, a, True, _fmt(value), steps)
        except CalcError as e:
            return ToolResult(mark, self.name, a, False, error=str(e))
        except Exception as e:  # never raise
            return ToolResult(mark, self.name, a, False, error=f"internal error: {type(e).__name__}")
