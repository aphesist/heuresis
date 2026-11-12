"""Drafting prompt. This is the main token cost: keep it compact."""
from __future__ import annotations

import re
from typing import Any, Sequence

from ..model import ABSTENTIONS, Passage

#: The first drafting instruction, kept verbatim so a run can A/B it (``draft.prompt = "v1"``).
DRAFT_SYSTEM_V1 = (
    "Answer ONLY from the numbered passages. Never use outside knowledge.\n"
    "Format, one item per line:\n"
    "- Write short sentences. End EVERY sentence with the marks of the passages "
    "that support it, like [t1] or [t1][t2].\n"
    "- Never do arithmetic or date math yourself. Request it before the answer with "
    'a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write '
    "{k1} where the result goes and add the mark [k1] to that sentence.\n"
    "- Use the as-of date you are given; passages show their validity as "
    "(title; valid from..to).\n"
    "- If the passages do not answer the question, write only "
    "`ABSTAIN <type>: <reason>` with type one of: " + ", ".join(ABSTENTIONS) + "."
)

#: The default drafting instruction (changed on dev evidence: see PREREGISTRATION.md,
#: deviations log). It asks for an answer whenever the passages contain it, also when
#: facts from several passages must be combined, with the answer in the first sentence.
DRAFT_SYSTEM_V2 = (
    "Answer ONLY from the numbered passages. Never use outside knowledge.\n"
    "Answer whenever the passages contain the answer, also when you must combine facts "
    "from two or more passages (for example, one passage names the person and another "
    "gives the fact about that person). A passage that is only partly relevant, or that "
    "does not repeat the question's wording, is no reason to abstain.\n"
    "Format, one item per line:\n"
    "- State the answer in the first sentence, then add only what is needed. Write short "
    "sentences. End EVERY sentence with the marks of ALL the passages that support it, "
    "like [t1] or [t1][t2].\n"
    "- Never do arithmetic or date math yourself. Request it before the answer with "
    'a line `CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write '
    "{k1} where the result goes and add the mark [k1] to that sentence.\n"
    "- Use the as-of date you are given; passages show their validity as "
    "(title; valid from..to).\n"
    "- Only if the answer is not in the passages, write only "
    "`ABSTAIN <type>: <reason>` with type one of: " + ", ".join(ABSTENTIONS) + "."
)

DRAFT_SYSTEM = DRAFT_SYSTEM_V2
PROMPTS = {"v1": DRAFT_SYSTEM_V1, "v2": DRAFT_SYSTEM_V2}


def draft_system(name: str = "v2") -> str:
    """The drafting instruction named by ``draft.prompt`` in the configuration."""
    try:
        return PROMPTS[name]
    except KeyError:
        raise ValueError(f"unknown drafting prompt {name!r}; have {sorted(PROMPTS)}") from None


def _span(p: Passage) -> str:
    return f"valid {p.valid_from or ''}..{p.valid_to or ''}"


def source_label(source_id: str) -> str:
    """A readable label for a source id: the part after the first colon, split at hyphens,
    underscores and spaces and capitalised ("multihoprag:sporting-news" -> "Sporting News");
    the id itself when nothing readable is left."""
    tail = (source_id or "").split(":", 1)[-1]
    words = [w for w in re.split(r"[-_\s]+", tail) if w]
    return " ".join(w[:1].upper() + w[1:] for w in words) or (source_id or "")


def passage_line(mark: str, p: Passage) -> str:
    """The one rendering of a passage in every prompt of every system (the engine's draft
    prompt and the baselines', the agentic search results and the oracle alike), so that
    they cannot drift apart: mark, title, source, validity, then the text."""
    parts = [p.title]
    if p.source_id:
        parts.append(f"source: {source_label(p.source_id)}")
    parts.append(_span(p))
    return f"[{mark}] ({'; '.join(parts)}) {' '.join(p.text.split())}"


def draft_prompt(
    question: str,
    as_of: str | None,
    passages: Sequence[Passage],
    tools: Sequence[Any] = (),
    max_sentences: int = 0,
) -> str:
    lines = [f"As-of date: {as_of or 'today'}"]
    if tools:
        lines.append("Tools: " + "; ".join(f"{t.name} ({t.description})" for t in tools))
    lines.append("Passages:")
    if passages:
        for i, p in enumerate(passages, 1):
            lines.append(passage_line(p.mark or f"t{i}", p))
    else:
        lines.append("(none)")
    lines.append(f"Question: {question}")
    if max_sentences > 0:
        lines.append(f"Answer in at most {max_sentences} short sentences.")
    return "\n".join(lines)


#: The instruction of the "search" answer mode (``answer.mode = "search"``). One model call per
#: turn: the model either answers in the draft format or replies with one ``SEARCH:`` line.
#: Every search is run by the engine with the question's own as-of date and scope.
SEARCH_SYSTEM = (
    "Answer ONLY from the numbered passages. Never use outside knowledge. They are what was in "
    "force at the as-of date, and so is everything a search returns.\n"
    "If the passages lack the answer, or only a step of it (for a multi-step question, first "
    "find the entity, then the fact about it), reply with exactly one line `SEARCH: <query>` and "
    "nothing else; a good query is short and names what you still need. Otherwise answer, "
    "combining passages when needed.\n"
    "Format, one item per line:\n"
    "- State the answer in the first sentence, then add only what is needed. Write short "
    "sentences. End EVERY sentence with the marks of ALL the passages that support it, like "
    "[t1] or [t1][t2].\n"
    "- Never do arithmetic or date math yourself. Request it before the answer with a line "
    '`CALL k1 calc {"expr": "..."}` (k1, k2, ... one per call), then write {k1} where the '
    "result goes and add the mark [k1] to that sentence.\n"
    "- Abstain only when no search remains and the answer is still not in the passages: write "
    "only `ABSTAIN <type>: <reason>` with type one of: " + ", ".join(ABSTENTIONS) + "."
)

SEARCH_MORE = "Answer now, or reply with exactly one line `SEARCH: <query>`."
SEARCH_LAST = "No searches remain. Answer from the passages, or ABSTAIN."


def search_prompt(question: str, as_of: str | None, rounds: Sequence[tuple[str, Sequence[Passage]]],
                  searches_left: int, max_searches: int, tools: Sequence[Any] = (),
                  max_sentences: int = 0) -> str:
    """The user prompt of the "search" mode. ``rounds[0]`` is the passages of the engine's
    first retrieval (its query text is ignored); each later round is (query, the passages
    that search added, not shown before). Passages carry their marks and are rendered by
    ``passage_line``, as in every other prompt."""
    lines = [f"As-of date: {as_of or 'today'}"]
    if tools:
        lines.append("Tools: " + "; ".join(f"{t.name} ({t.description})" for t in tools))
    lines.append("Passages:")
    first = rounds[0][1] if rounds else ()
    lines += [passage_line(p.mark, p) for p in first] or ["(none)"]
    for i, (query, found) in enumerate(rounds[1:], 1):
        lines.append(f"Search {i}: {query}")
        lines += [passage_line(p.mark, p) for p in found] or ["(no new passages)"]
    lines.append(f"Question: {question}")
    lines.append(f"Searches used: {max_searches - searches_left} of {max_searches}.")
    if max_sentences > 0:
        lines.append(f"Answer in at most {max_sentences} short sentences.")
    lines.append(SEARCH_MORE if searches_left > 0 else SEARCH_LAST)
    return "\n".join(lines)


ANSWERS_QUESTION_SYSTEM = (
    "You check whether an answer addresses a question. Reply with exactly one word: YES if "
    "the answer states what the question asks for (the specific person, number, date, place, "
    "thing, or yes/no it requests), NO if it only states something else, an intermediate "
    "fact, a partial answer, or repeats the question. Do not judge whether the answer is true."
)


def answers_question_prompt(question: str, answer: str) -> str:
    """The user prompt of the optional ``verify.answers_question`` stage (marks removed)."""
    clean = re.sub(r"\[[tk]\d+\]", "", answer)
    return f"Question: {question}\nAnswer: {' '.join(clean.split())}\nDoes the answer state what the question asks for? YES or NO."
