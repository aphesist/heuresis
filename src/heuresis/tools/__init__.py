"""Deterministic tools: the model requests a call, code computes."""
from __future__ import annotations

from typing import Any, Sequence

from ..interfaces import Tool
from ..model import ToolResult
from .calc import CalcTool
from .dates import DatesTool
from .sql import SqlTool

__all__ = ["CalcTool", "DatesTool", "SqlTool", "default_tools", "run_calls"]


def default_tools() -> list[Tool]:
    return [CalcTool(), DatesTool(), SqlTool()]


def run_calls(tools: Sequence[Tool], calls: Sequence[dict[str, Any]]) -> list[ToolResult]:
    """Run each ``{"mark", "tool", "args"}`` call in order; never raises."""
    by_name = {t.name: t for t in tools}
    out: list[ToolResult] = []
    for i, call in enumerate(calls or []):
        c = call if isinstance(call, dict) else {}
        mark = c.get("mark") if isinstance(c.get("mark"), str) and c.get("mark") else f"k{i + 1}"
        name = c.get("tool")
        args = c.get("args", {})
        shown = dict(args) if isinstance(args, dict) else {}
        tool = by_name.get(name) if isinstance(name, str) else None
        if tool is None:
            out.append(ToolResult(mark, str(name), shown, False, error=f"unknown tool: {name!r}"))
            continue
        if not isinstance(args, dict):
            out.append(ToolResult(mark, name, shown, False, error="args must be an object"))
            continue
        try:
            out.append(tool.run(mark, args))
        except Exception as e:  # a misbehaving tool must not break the batch
            out.append(ToolResult(mark, name, shown, False, error=f"tool failed: {type(e).__name__}"))
    return out
