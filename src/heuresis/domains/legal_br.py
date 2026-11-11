"""EXAMPLE plug-in for Brazilian legislation. Not a legal product.

Reads the ``jsonl`` exchange format with LexML-style unit ids
(``urn:lex:br:<authority>:<type>:<date>;<number>!art<n>``).
"""
from __future__ import annotations

import re

from ..model import Scope
from .jsonl import JsonlDomain

_NORM = re.compile(
    r"\b(lei\s+complementar|lc|lei|decreto-lei|decreto|mp|medida\s+provis[óo]ria)"
    r"(?:\s+exemplo)?\s*(?:n[ºo°.]*\s*)?(\d{1,3}(?:\.\d{3})*|\d+)\s*/\s*(\d{4}|\d{2})\b",
    re.IGNORECASE,
)
_ART = re.compile(r"\bart(?:igo)?s?\.?\s*(\d+)(?:\s*-?\s*([A-Z])\b)?", re.IGNORECASE)
_PAR = re.compile(r"(?:§|\bpar[áa]grafo\s+)\s*(\d+)\s*[ºo°]?", re.IGNORECASE)
_TYPES = {
    "lei complementar": "lei.complementar", "lc": "lei.complementar", "lei": "lei",
    "decreto-lei": "decreto.lei", "decreto": "decreto",
    "mp": "medida.provisoria", "medida provisória": "medida.provisoria",
    "medida provisoria": "medida.provisoria",
}
_URN = re.compile(r"^(urn:lex:br:[^:]+:([^:]+):(\d{4})[^;]*;(\d+))")

_TEXTS = {
    "no_source": "Não encontrei, no acervo, dispositivo que trate desta pergunta.",
    "not_valid_at_date": "Há dispositivos sobre o tema, mas nenhum estava em vigor na data consultada.",
    "conflict": "As fontes de mesma hierarquia divergem; apresento ambas sem escolher.",
    "false_premise": "A pergunta parte de uma premissa que as fontes do acervo contradizem.",
    "outside_coverage": "O acervo declara não cobrir este assunto.",
    "unsupported": "Foi redigida uma resposta, mas ela não passou na verificação contra os dispositivos citados.",
    "needs_input": "Falta um dado que só você pode informar para responder.",
    "tool_failed": "Não foi possível concluir o cálculo necessário.",
    "out_of_scope": "Esta pergunta não é matéria deste acervo.",
    "budget": "O orçamento de custo acabou antes de uma resposta verificada.",
}


def extract_references(text: str) -> dict:
    """Pull norm, article and paragraph references from a question."""
    norms = []
    for m in _NORM.finditer(text):
        kind = _TYPES[re.sub(r"\s+", " ", m.group(1).lower())]
        year = m.group(3)
        year = year if len(year) == 4 else ("20" if int(year) < 50 else "19") + year
        norms.append({"type": kind, "number": m.group(2).replace(".", ""), "year": year})
    return {
        "norms": norms,
        "articles": [a.group(1) + (a.group(2) or "") for a in _ART.finditer(text)],
        "paragraphs": [p.group(1) for p in _PAR.finditer(text)],
    }


class LegalBRDomain(JsonlDomain):
    name = "legal_br"
    axes = ("published", "effects")

    def __init__(self):
        #: (type, number, year) -> norm urn prefix
        self._norms: dict[tuple[str, str, str], str] = {}

    def read(self, path: str):
        result = super().read(path)
        norms = {}
        for u in result[1]:
            m = _URN.match(u.id)
            if m:
                norms[(m.group(2), m.group(4), m.group(3))] = m.group(1)
        self._norms = norms
        return result

    def rules(self):
        def provision_rule(text: str):
            refs = extract_references(text)
            for n in refs["norms"]:
                prefix = self._norms.get((n["type"], n["number"], n["year"]))
                if prefix:
                    return {"scope": Scope(unit_prefix=prefix)}
            return None

        return [provision_rule]

    def abstention_text(self, kind, query):
        return _TEXTS.get(kind)
