"""The text of a repair turn: what failed, in plain words, with the previous answer."""
from __future__ import annotations

from ..model import Claim
from .locked.gates import deterministic_failure, failure_reason

__all__ = ["feedback"]


def _marked(c: Claim) -> str:
    marks = "".join(f"[{m}]" for m in (*c.passage_marks, *c.tool_marks))
    return f"{c.text} {marks}".rstrip()


def feedback(claims: list[Claim], verdict=None) -> str:
    """The failed sentences with a reason each (a missing or unshown mark, a provision not in
    force at the date, a number not in the cited passages, a reference not found or not cited)
    and, when a judge ``verdict`` is given, the sentences it did not accept. Empty when nothing
    failed. The previous answer is included so the model can write it again."""
    problems: list[str] = []
    for c in claims:
        if deterministic_failure(c):
            problems.append(f'- "{c.text}": {failure_reason(c)}')
    if verdict is not None:
        judged = [c for c in claims if not deterministic_failure(c)]
        for j, c in enumerate(judged):
            w = getattr(verdict, "sentences", {}).get(j, "")
            if w == "NOT_SUPPORTED":
                problems.append(f'- "{c.text}": the cited passages do not state this')
            elif w == "NOT_FOLLOWS":
                problems.append(f'- "{c.text}": it does not follow from the supported sentences')
            elif w == "PARTIAL":
                problems.append(f'- "{c.text}": the cited passages state only part of this')
    if not problems:
        return ""
    prev = [f"- {_marked(c)}" for c in claims]
    return "Your previous answer:\n" + "\n".join(prev) + "\n\nFailed sentences:\n" + "\n".join(problems)
