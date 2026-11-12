"""EXAMPLE plug-in for Brazilian legislation. Not a legal product.

Reads the ``jsonl`` exchange format with LexML-style unit ids
(``urn:lex:br:<authority>:<type>:<date>;<number>!art<n>``).
"""
from __future__ import annotations

import re
import unicodedata

from ..interfaces import Reference
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


# ----------------------------------------------------------------------------
# Free-text citation resolver
# ----------------------------------------------------------------------------

_STOP = {"de", "da", "do", "das", "dos", "e", "a", "o", "para", "no", "na", "em", "com"}
#: citation words -> unit-type slug used in the corpus ids (folded, lower case)
_CITE_TYPES = [
    ("lei complementar", "lei.complementar"), ("lei delegada", "lei.delegada"), ("decreto-lei", "decreto.lei"),
    ("decreto lei", "decreto.lei"), ("medida provisoria", "medida.provisoria"),
    ("emenda constitucional", "emenda.constitucional"), ("instrucao normativa", "instrucao.normativa"),
    ("parecer normativo", "parecer.normativo"), ("ato declaratorio interpretativo", "ato.declaratorio.interpretativo"),
    ("ato declaratorio normativo", "ato.declaratorio.normativo"), ("ato declaratorio executivo", "ato.declaratorio.executivo"),
    ("ato declaratorio", "ato.declaratorio"), ("solucao de consulta", "solucao.consulta"),
    ("portaria", "portaria"), ("resolucao", "resolucao"), ("decreto", "decreto"), ("lei", "lei"),
    ("lc", "lei.complementar"), ("mp", "medida.provisoria"), ("ec", "emenda.constitucional"),
    ("in", "instrucao.normativa"), ("dl", "decreto.lei"),
]
_SHORT_TYPES = {"lc", "mp", "ec", "in", "dl"}
_INFRALEGAL = {"instrucao.normativa", "portaria", "resolucao", "parecer.normativo", "solucao.consulta",
               "ato.declaratorio", "ato.declaratorio.interpretativo", "ato.declaratorio.normativo",
               "ato.declaratorio.executivo"}
_TYPE_ALT = "|".join(re.escape(t) for t, _ in sorted(_CITE_TYPES, key=lambda x: -len(x[0])))
_NUM = r"\d{1,3}(?:\.\d{3})+|\d+"
_NORM_RE = re.compile(
    r"(?<![a-z0-9])(?P<type>" + _TYPE_ALT + r")(?![a-z])(?P<issuer>(?:\s+[a-z]{2,8}(?:/[a-z]{2,5})?){0,2}?)"
    r"\s*(?P<nn>n[oº°.]{0,2}s?\.?)?\s*(?P<num>" + _NUM + r")(?:-\d{1,3})?"
    r"(?:\s*/\s*(?P<y1>\d{4}|\d{2})|\s*,?\s+de\s+(?:\d{1,2}[o°]?\s+de\s+[a-z]+\s+de\s+)?(?P<y2>\d{4}))?")
_ART_RE = re.compile(r"(?<![a-z])(?:artigos?|arts?)\.?\s*(?P<list>\d[^a-z]{0,2}(?:[^.;:()\n]{0,60}?))(?=\s*(?:,|\b)|$)")
_ARTNUM = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{3})+|\d+)\s*[o°º]?(?:\s*-\s*([a-z])\b)?")
_CONNECT_NEXT = re.compile(
    r"^[\s,;(§\d.o°ºivxlc\"'a-z)-]{0,90}?\b(?:da|do|das|dos|de|na|no|nas|nos|desta|deste|dessa|desse|pela|pelo)\s+$")
_SUB = re.compile(r"^(?:[\s,;.§()\"']|\bparagrafo\b|\bunico\b|\binciso\b|\balinea\b|\bcaput\b|\bc/c\b|\be\b|\bou\b|"
                  r"\b[ivxlc]+\b|\b\d+[o°º]?\b|\b[a-z]\)|\bitem\b|\bnos?\b|\bsubitem\b)*$")


def fold(text: str) -> str:
    """Lower-case, accent-free text of the same length (character by character), so spans found in
    it are spans of the original."""
    out = []
    for ch in text:
        d = unicodedata.normalize("NFD", ch)
        out.append("".join(c for c in d if unicodedata.category(c) != "Mn")[:1].lower() or ch.lower())
    return "".join(out)


def acronym_of(name: str) -> str:
    """Initials of a capitalised name ("Código de Processo Civil" -> "CPC"); "" when the name is
    not made of capitalised words or is too short or long."""
    words = [w for w in re.split(r"[\s,]+", re.sub(r"\s+de\s+\d{4}\b.*$", "", name.strip(" .")))
             if w and w.lower() not in _STOP]
    if not 2 <= len(words) <= 6 or not all(w[0].isupper() and w.isalpha() for w in words):
        return ""
    return "".join(w[0] for w in words).upper()


def explicit_acronyms(name: str) -> list[str]:
    """Acronyms a title spells out: ``Name (CTN)`` and ``Name - RIR/2018``."""
    return re.findall(r"\(([A-Z][A-Za-z0-9/.-]{1,12})\)|\s-\s([A-Z][A-Z0-9/]{1,12})(?=[,\s]|$)", name) and [
        a or b for a, b in re.findall(r"\(([A-Z][A-Za-z0-9/.-]{1,12})\)|\s-\s([A-Z][A-Z0-9/]{1,12})(?=[,\s]|$)", name)]


class _Norm:
    __slots__ = ("urn", "kind", "authority", "date", "number", "title")

    def __init__(self, urn: str, title: str):
        m = _URN_FULL.match(urn)
        self.urn, self.title = urn, title
        self.authority, self.kind, self.date, self.number = m.groups() if m else ("", "", "", "")


_URN_FULL = re.compile(r"^urn:lex:br:([^:]+):([^:]+):(\d{4}-\d{2}-\d{2});(.+)$")


class NormIndex:
    """Norms of a corpus, looked up by (type, number) and by name or acronym. Built from the
    corpus's own sources: their ids (URNs), titles, and the ``names`` / ``aliases`` / ``ementa``
    they carry. The acronym table is derived from those names, never from outside knowledge."""

    def __init__(self, sources):
        self.by_num: dict[tuple[str, str], list[_Norm]] = {}
        self.names: dict[str, list[_Norm]] = {}      # folded full name -> norms
        self.acronyms: dict[str, list[_Norm]] = {}   # exact-case acronym -> norms
        for s in sources:
            if s.kind != "norm":
                continue
            n = _Norm(s.id, s.meta.get("title", ""))
            if not n.kind:
                continue
            self.by_num.setdefault((n.kind, n.number.split("-")[0]), []).append(n)
            names = list(s.meta.get("names", [])) + [s.meta.get("ementa", "")]
            for name in names:
                name = (name or "").strip()
                if name and len(name.split()) <= 8 and not re.match(r"^(Lei|Decreto|Instru|Portaria|Medida)\b.*n[ºo°]", name):
                    stem = re.sub(r"\s*\([^)]*\)", "", name).strip(" .")
                    stem = re.sub(r"\s+de\s+\d{4}$", "", stem)
                    self.names.setdefault(fold(stem), []).append(n)
                    for a in explicit_acronyms(name) or []:
                        self.acronyms.setdefault(a, []).append(n)
                    a = acronym_of(stem)
                    if a:
                        self.acronyms.setdefault(a, []).append(n)
            for a in s.meta.get("aliases", []):
                self.acronyms.setdefault(a, []).append(n)
        # the head noun alone ("Constituição, art. 153") when no other name starts with it
        heads: dict[str, set[str]] = {}
        for nm, ns in list(self.names.items()):
            first = nm.split()[0] if nm.split() else ""
            if len(first) >= 6 and len(nm.split()) >= 2:
                heads.setdefault(first, set()).update(n.urn for n in ns)
        for first, urns in heads.items():
            if len(urns) == 1 and first not in self.names:
                self.names[first] = next(ns for nm, ns in self.names.items() if nm.split()[0] == first)
        self._alias_re = None

    def alias_regex(self):
        if self._alias_re is None and (self.acronyms or self.names):
            alts = sorted([re.escape(a) for a in self.acronyms] , key=len, reverse=True)
            self._alias_re = re.compile(r"(?<![A-Za-z0-9/])(" + "|".join(alts) + r")(?:/(?:\d{2}|\d{4}))?(?![A-Za-z0-9])") if alts else None
            names = sorted((re.escape(n) for n in self.names), key=len, reverse=True)
            self._name_re = re.compile(r"(?<![a-z])(" + "|".join(names) + r")(?![a-z])") if names else None
        return self._alias_re


def _year(y: str | None) -> str | None:
    if not y:
        return None
    return y if len(y) == 4 else ("20" if int(y) < 50 else "19") + y


def find_norm_mentions(text: str, index: NormIndex) -> list[dict]:
    """Norm mentions in ``text``: dicts with start, end, candidates (``_Norm`` list), written, found."""
    f = fold(text)
    out = []
    for m in _NORM_RE.finditer(f):
        tname = m.group("type")
        kind = dict(_CITE_TYPES)[tname]
        if tname in _SHORT_TYPES and not (m.group("nn") or tname in ("lc", "mp", "ec", "dl")):
            continue
        issuer = m.group("issuer").strip()
        if issuer and kind not in _INFRALEGAL:
            continue
        if not issuer and kind in _INFRALEGAL and not m.group("nn"):
            continue
        num = m.group("num").replace(".", "")
        year = _year(m.group("y1") or m.group("y2"))
        if not m.group("nn") and not year and tname not in _SHORT_TYPES and len(num) < 3:
            continue
        cands = list(index.by_num.get((kind, num), ()))
        if issuer:
            iss = issuer.split("/")[0].split()[-1]
            cands = [c for c in cands if c.authority == iss]
        if year:
            cands = [c for c in cands if c.date[:4] == year]
        out.append({"start": m.start(), "end": m.end(), "cands": cands, "written": text[m.start():m.end()],
                    "meta": {"kind": kind, "number": num, "year": year or ""}})
    if index.alias_regex() is not None:
        for m in index._alias_re.finditer(text):
            out.append({"start": m.start(), "end": m.end(), "cands": list(index.acronyms[m.group(1)]),
                        "written": m.group(0)})
    if getattr(index, "_name_re", None) is not None:
        for m in index._name_re.finditer(f):
            out.append({"start": m.start(), "end": m.end(), "cands": list(index.names[m.group(1)]),
                        "written": text[m.start():m.end()]})
    out.sort(key=lambda d: (d["start"], -(d["end"] - d["start"])))
    res, last = [], -1
    for d in out:                       # drop mentions inside a longer one
        if d["start"] >= last:
            res.append(d)
            last = d["end"]
    return res


def find_article_mentions(text: str) -> list[dict]:
    """Article mentions ("art. 8º", "arts. 7º, 8º e 12", "artigo 15-A"): dicts with start, end, keys."""
    f = fold(text)
    out = []
    for m in re.finditer(r"(?<![a-z])(?:artigos?|arts?)\.?\s*(?=\d)", f):
        pos = m.end()
        keys, end = [], pos
        while True:
            n = _ARTNUM.match(f, end)
            if not n:
                break
            keys.append(n.group(1).replace(".", "") + ("-" + n.group(2).upper() if n.group(2) else ""))
            end = n.end()
            sep = re.match(r"\s*(?:,\s*|\se\s+|\sa\s+|\sao\s+|\sou\s+)(?=\d)", f[end:])
            if not sep:
                break
            if re.match(r"\s*a\s", f[end:]) or re.match(r"\s*ao\s", f[end:]):
                end2 = end + sep.end()
                n2 = _ARTNUM.match(f, end2)
                if n2 and n2.group(1).isdigit() and keys[-1].isdigit() and 0 < int(n2.group(1)) - int(keys[-1]) <= 60:
                    keys.extend(str(i) for i in range(int(keys[-1]) + 1, int(n2.group(1)) + 1))
                    end = n2.end()
                    continue
            end += sep.end()
        if keys:
            out.append({"start": m.start(), "end": end, "keys": keys})
    return out


def associate(text: str, arts: list[dict], norms: list[dict]) -> list[tuple[dict, dict | None]]:
    """Pair each article mention with the norm it belongs to: the norm that follows it after a
    connector ("art. 8º, II, da Lei ...") or the one that precedes it ("CTN, art. 43")."""
    f = fold(text)
    pairs: list[tuple[dict, dict | None]] = []
    chosen: dict[int, dict | None] = {}
    for i in range(len(arts) - 1, -1, -1):
        a = arts[i]
        nxt = next((n for n in norms if n["start"] >= a["end"]), None)
        norm = None
        if nxt is not None:
            gap = f[a["end"]: nxt["start"]]
            between_art = i + 1 < len(arts) and arts[i + 1]["start"] < nxt["start"]
            if between_art:
                nxt_art = arts[i + 1]
                g2 = f[a["end"]: nxt_art["start"]]
                if len(g2) <= 40 and re.match(r"^[\s,;.§ºo°()\"'\divxlc]*(?:e|ou|c/c)?[\s,;.]*$", g2) and chosen.get(i + 1):
                    norm = chosen[i + 1]
            elif len(gap) <= 90 and _CONNECT_NEXT.match(gap) and not re.search(r"[.;]\s", gap.strip() + " "):
                norm = nxt
        if norm is None:
            prev = next((n for n in reversed(norms) if n["end"] <= a["start"]), None)
            if prev is not None:
                gap = f[prev["end"]: a["start"]]
                if len(gap) <= 30 and re.match(r"^[\s,;():–—-]*(?:c/c|e|ou)?[\s,;():–—-]*$", gap):
                    norm = prev
        chosen[i] = norm
    for i, a in enumerate(arts):
        pairs.append((a, chosen.get(i)))
    return pairs


class Resolver:
    """Resolve the citations of a text against a store holding a Brazilian-law corpus."""

    def __init__(self, store):
        self.store = store
        self.index = NormIndex(store.sources("norm"))

    def resolve(self, text: str) -> list[Reference]:
        norms = find_norm_mentions(text, self.index)
        arts = find_article_mentions(text)
        refs: list[Reference] = []
        used: set[int] = set()
        for a, n in associate(text, arts, norms):
            if n is None:
                continue
            used.add(id(n))
            for key in a["keys"]:
                span = (min(a["start"], n["start"]), max(a["end"], n["end"]))
                refs.append(self._ref(text, span, n, key))
        for n in norms:
            if id(n) not in used:
                refs.append(self._ref(text, (n["start"], n["end"]), n, ""))
        # "Decreto nº 9.580/2018 (RIR/2018), art. 677": the bare mention of the norm is the same
        # citation as the aliased one that carries the article
        owned = [r for r in refs if r.unit and r.container]
        refs = [r for r in refs if not (r.status == "norm_only" and any(
            o.container == r.container and 0 <= o.start - r.end <= 30 for o in owned))]
        refs.sort(key=lambda r: (r.start, r.unit))
        return refs

    def _ref(self, text: str, span: tuple[int, int], n: dict, key: str) -> Reference:
        written = text[span[0]: span[1]]
        if not n["cands"]:
            return Reference(written, span[0], span[1], "container_not_found", unit=key,
                             meta=n.get("meta", {}))
        if not key:
            return Reference(written, span[0], span[1], "norm_only", container=n["cands"][0].urn)
        for c in n["cands"]:
            uid = f"{c.urn}!art{key}"
            if self.store.has_unit(uid):
                return Reference(written, span[0], span[1], "resolved", container=c.urn, unit=key, unit_ids=(uid,))
        return Reference(written, span[0], span[1], "unit_not_found", container=n["cands"][0].urn, unit=key)


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

    def resolve_references(self, text, store):
        """Citations in ``text`` as lawyers write them, resolved to unit ids of ``store``, or to
        "norm found, article not found" (``unit_not_found``) or "norm not found"
        (``container_not_found``)."""
        key = id(store)
        cache = getattr(self, "_resolvers", None)
        if cache is None:
            cache = self._resolvers = {}
        r = cache.get(key)
        if r is None or r.store is not store:
            r = cache[key] = Resolver(store)
        return r.resolve(text)
