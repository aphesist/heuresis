"""Corpus ``brlaw``: Brazilian federal law as the example domain of the citation-integrity test.

Three tiers are built into the ``jsonl`` exchange format (``data/corpora/brlaw*``):

* ``tax``       the legal source texts shipped with BR-TaxQA-R (CC BY 4.0), split into articles;
* ``federal``   the federal norms of ``ctresb/leis`` at a pinned commit (the large tier);
* ``versioned`` provisions for which both an earlier and a later wording were downloaded as
                official text, with real ``create`` / ``replace`` / ``repeal`` events.

Nothing here writes, paraphrases or reconstructs a legal provision: every unit text is a slice of a
downloaded source, and every date comes from a source (a header, an annotation or a publication
record). What cannot be established is left out and counted. Nothing built here is committed.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import unicodedata
from typing import Iterable, Iterator

# ----------------------------------------------------------------------------
# Dates
# ----------------------------------------------------------------------------

MONTHS = {m: i for i, m in enumerate(
    ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
     "setembro", "outubro", "novembro", "dezembro"], 1)}
_MONTH_RE = "|".join(MONTHS)
_SLASH_DATE = re.compile(r"\b(\d{1,2})[ºo°]?\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b")
_LONG_DATE = re.compile(r"\b(\d{1,2})[ºo°]?\s+de\s+(" + _MONTH_RE + r")\s+de\s+(\d{4})\b", re.I)


def iso(y: int, m: int, d: int) -> str | None:
    try:
        return _dt.date(y, m, d).isoformat()
    except ValueError:
        return None


def slash_dates(text: str) -> list[str]:
    """Every ``d/m/yyyy`` date in the text, as ISO strings, in order."""
    out = []
    for m in _SLASH_DATE.finditer(text):
        v = iso(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if v:
            out.append(v)
    return out


def long_date(text: str) -> str | None:
    m = _LONG_DATE.search(text)
    return iso(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))) if m else None


def tokens_of(text: str) -> int:
    """The approximate token count used across the benchmark (characters / 4)."""
    return len(text) // 4


# ----------------------------------------------------------------------------
# Identifiers (LexML-style)
# ----------------------------------------------------------------------------

TYPE_SLUGS = {
    "lei complementar": "lei.complementar", "lei delegada": "lei.delegada", "lei": "lei",
    "decreto-lei": "decreto.lei", "decreto": "decreto", "medida provisória": "medida.provisoria",
    "emenda constitucional": "emenda.constitucional", "constituição": "constituicao",
    "instrução normativa": "instrucao.normativa", "portaria": "portaria",
    "ato declaratório interpretativo": "ato.declaratorio.interpretativo",
    "ato declaratório normativo": "ato.declaratorio.normativo",
    "ato declaratório executivo": "ato.declaratorio.executivo",
    "ato declaratório": "ato.declaratorio", "parecer normativo": "parecer.normativo",
    "parecer": "parecer", "resolução": "resolucao", "súmula": "sumula",
    "solução de consulta": "solucao.consulta", "solução de consulta interna": "solucao.consulta.interna",
    "solução de divergência": "solucao.divergencia", "nota": "nota", "circular": "circular",
    "despacho": "despacho",
}
#: Folder name of ``ctresb/leis`` -> LexML type slug (only the folders the federal tier reads).
FEDERAL_FOLDERS = {
    "leis-ordinarias": "lei", "leis-complementares": "lei.complementar",
    "decretos-lei": "decreto.lei", "leis-delegadas": "lei.delegada",
    "emendas-constitucionais": "emenda.constitucional",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", ".", strip_accents(s).lower()).strip(".") or "x"


def norm_urn(kind: str, date: str, number: str, authority: str = "federal") -> str:
    """``urn:lex:br:<authority>:<type>:<date>;<number>`` (LexML)."""
    return f"urn:lex:br:{authority}:{kind}:{date};{number}"


def article_key(label: str) -> str:
    """Canonical article key from a label such as ``Art. 8º``, ``Art. 15-A``, ``Artigo único``."""
    s = strip_accents(label).lower().replace("*", "")
    if re.search(r"\bunico\b", s):
        return "unico"
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:[ºo°]|\.)?\s*(?:-\s*([a-z]{1,2})\b)?", s)
    if not m:
        return ""
    n = m.group(1).replace(".", "")
    return n + ("-" + m.group(2).upper() if m.group(2) else "")


def unit_id(urn: str, key: str, part: int = 1, prefix: str = "art") -> str:
    base = f"{urn}!{prefix}{key}"
    return base if part == 1 else f"{base}!p{part}"


# ----------------------------------------------------------------------------
# Annotations: repeal
# ----------------------------------------------------------------------------

_REVOGADO = re.compile(r"\(\s*Revogad[oa]s?\b", re.I)
_DEFER = re.compile(r"(em vigor a partir de|produzindo efeitos a partir de|vigência a partir de|"
                    r"com efeitos a partir de|a partir de)\s+(\d{1,2}[ºo°]?\s*/\s*\d{1,2}\s*/\s*\d{4})", re.I)


def repeal_info(note: str) -> tuple[str | None, str]:
    """Date and certainty of a repeal annotation, only when the annotation settles them.

    Returns ``(date, certainty)``. ``date`` is ``None`` when the annotation names no date, names
    several unrelated dates (a provisional measure, its conversion law...) without saying which
    one takes effect, or when the date cannot be parsed. A single date, or a date introduced by
    "em vigor a partir de" / "produzindo efeitos a partir de", is taken from the source."""
    m = _DEFER.search(note)
    if m:
        d = slash_dates(m.group(2))
        if d:
            return d[0], "high"
    ds = slash_dates(note)
    if len(set(ds)) == 1:
        return ds[0], "high"
    return None, "low"


def is_whole_repeal(text: str) -> bool:
    """True when an article's text is nothing but a "(Revogado ...)" annotation after its label."""
    t = re.sub(r"^\s*Art(?:igo)?\.?\s*[^\s]+\s*", "", text.replace("*", ""), count=1)
    return bool(_REVOGADO.match(t.strip())) and len(t) < 600


# ----------------------------------------------------------------------------
# ctresb/leis markdown
# ----------------------------------------------------------------------------

_HDR = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_ADCT = re.compile(r"^#+\s.*DISPOSI..ES\s+CONSTITUCIONAIS\s+TRANSIT", re.I)
_ART_LINE = re.compile(r"^\*\*Art(?:igo)?\b")
MAX_UNIT_CHARS = 8000


def parse_header(text: str) -> tuple[dict, str]:
    """YAML-ish header of a ``ctresb/leis`` file: flat ``key: "value"`` lines."""
    m = _HDR.match(text)
    if not m:
        return {}, text
    hdr = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] == '"':
            v = v[1:-1]
        hdr[k.strip()] = v
    return hdr, text[m.end():]


def split_md_articles(body: str) -> list[tuple[str, str, str]]:
    """``(prefix, key, text)`` per top-level article of a markdown norm.

    Only lines that start with a bold ``Art`` open an article: quoted articles inside an amending
    law start with a quotation mark and stay in the text of the article that quotes them. A
    heading closes the article it follows. Articles after the "Ato das Disposições Constitucionais
    Transitórias" heading get the prefix ``adct`` (their numbers restart)."""
    out: list[tuple[str, str, list[str]]] = []
    prefix = "art"
    cur: list[str] | None = None
    for line in body.split("\n"):
        if line.startswith("#"):
            cur = None
            if _ADCT.match(line):
                prefix = "adct"
            continue
        if _ART_LINE.match(line):
            key = article_key(re.sub(r"[*]", "", line)[:48])
            if key:
                cur = [line]
                out.append((prefix, key, cur))
                continue
        if cur is not None:
            cur.append(line)
    return [(p, k, clean_md("\n".join(ls))) for p, k, ls in out]


def clean_md(text: str) -> str:
    """Drop emphasis markers and surplus blank lines; keep the words untouched."""
    t = text.replace("**", "").replace(" ", " ")
    t = re.sub(r"(?<!\w)\*(?=\S)|(?<=\S)\*(?!\w)", "", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def chunk_text(text: str, limit: int = MAX_UNIT_CHARS) -> list[str]:
    """Split a very long article at line breaks into chunks of at most ``limit`` characters."""
    if len(text) <= limit:
        return [text]
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # a single enormous line: cut at a space
            cut = line.rfind(" ", 0, limit) or limit
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:cut])
            line = line[cut:].lstrip()
        if cur and len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks


def markdown_units(urn: str, text_title: str, body: str, date: str, source_id: str,
                   *, evidence: str) -> Iterator[dict]:
    """Rows for one markdown norm: ``{"unit": ..., "events": [...], "repealed": bool,
    "repeal_unknown": bool}`` per article (a very long article yields several units)."""
    seen: dict[str, int] = {}
    for prefix, key, text in split_md_articles(body):
        n = seen.get(prefix + key, 0) + 1
        seen[prefix + key] = n
        k = key if n == 1 else f"{key}~{n}"
        label = text.split("\n", 1)[0][:60]
        repealed = is_whole_repeal(text)
        rdate, rcert = repeal_info(text) if repealed else (None, "low")
        if rdate and rdate <= date:
            rdate = None  # a repeal cannot precede the norm: the annotation is not settled
        for part, chunk in enumerate(chunk_text(text), 1):
            uid = unit_id(urn, k, part, prefix)
            title = f"{text_title} — {'Art. ' + key.replace('unico', 'único') if prefix == 'art' else 'ADCT art. ' + key}"
            ev = [{"id": f"{uid}@{date}", "unit_id": uid, "op": "create", "date": date,
                   "text": chunk, "recorded_at": date, "evidence": evidence,
                   "certainty": "low" if repealed else "high",
                   "axes": {"published": date}}]
            if repealed and rdate and part == 1:
                ev.append({"id": f"{uid}@{rdate}:repeal", "unit_id": uid, "op": "repeal",
                           "date": rdate, "recorded_at": rdate,
                           "evidence": f"{evidence}; annotation: {_note(text)}",
                           "certainty": rcert, "axes": {"published": rdate}})
            yield {"unit": {"id": uid, "source_id": source_id, "kind": "article",
                            "parent_id": None, "title": title},
                   "events": ev, "repealed": repealed and bool(rdate) and part == 1,
                   "repeal_unknown": repealed and not rdate and part == 1, "label": label}


def _note(text: str) -> str:
    m = _REVOGADO.search(text)
    return text[m.start(): m.start() + 300].replace("\n", " ") if m else ""


def jsonl_rows(rows: Iterable[dict]) -> Iterator[str]:
    for r in rows:
        yield json.dumps(r, ensure_ascii=False, sort_keys=True)


# ----------------------------------------------------------------------------
# Tier "federal": ctresb/leis
# ----------------------------------------------------------------------------

_AUTH = {"constituicao": 5, "emenda.constitucional": 5, "lei.complementar": 4}
LEIS_REPO = "https://github.com/ctresb/leis"


def iter_federal_files(leis_dir: str) -> Iterator[tuple[str, str]]:
    """``(type_slug, path)`` for every markdown norm of the federal tier, in a stable order,
    then the Constitution."""
    import os
    for folder, kind in FEDERAL_FOLDERS.items():
        base = os.path.join(leis_dir, "federal", folder)
        if not os.path.isdir(base):
            continue
        for year in sorted(os.listdir(base)):
            ydir = os.path.join(base, year)
            if not os.path.isdir(ydir):
                continue
            for fn in sorted(os.listdir(ydir)):
                if fn.endswith(".md"):
                    yield kind, os.path.join(ydir, fn)
    cf = os.path.join(leis_dir, "constituicao.md")
    if os.path.exists(cf):
        yield "constituicao", cf


def norm_source(urn: str, kind: str, hdr: dict, commit: str, coverage: int = 3) -> dict:
    meta = {"title": hdr.get("titulo", ""), "type": kind, "text_version": hdr.get("versao_texto", ""),
            "origin": hdr.get("fonte", ""), "retrieved": hdr.get("baixado_em", ""),
            "revoked_flag": hdr.get("revogada") == "true", "tier": "federal",
            "repo_commit": commit, "ementa": hdr.get("ementa", "")[:200]}
    if hdr.get("names"):
        meta["names"] = hdr["names"]
    return {"id": urn, "kind": "norm", "authority": _AUTH.get(kind, 3), "coverage": coverage,
            "licence": "official act (Lei 9.610/1998 art. 8, VI as stated by the repository); "
                       "not redistributed", "meta": meta}


def build_federal(leis_dir: str, out_dir: str, commit: str, *, skip_urns: frozenset = frozenset(),
                  limit: int | None = None, progress=None) -> dict:
    """Write the federal tier as jsonl files into ``out_dir``; returns the statistics."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    st = {"files_seen": 0, "norms": 0, "units": 0, "events": 0, "chars": 0, "skipped_no_header": 0,
          "skipped_no_articles": 0, "skipped_duplicate_urn": 0, "skipped_in_other_tier": 0,
          "units_repealed": 0, "units_repeal_date_unknown": 0, "norms_marked_revoked": 0,
          "by_type": {}, "by_text_version": {}}
    seen: set[str] = set()
    with open(os.path.join(out_dir, "sources.jsonl"), "w", encoding="utf-8") as fs, \
            open(os.path.join(out_dir, "units.jsonl"), "w", encoding="utf-8") as fu, \
            open(os.path.join(out_dir, "events.jsonl"), "w", encoding="utf-8") as fe:
        for kind, path in iter_federal_files(leis_dir):
            st["files_seen"] += 1
            if limit and st["files_seen"] > limit:
                break
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if kind == "constituicao":
                hdr = {"titulo": "Constituição da República Federativa do Brasil de 1988",
                       # the name BR-TaxQA-R gives to its copy of the text (file "Constituição Federal de 1988.txt")
                       "names": ["Constituição Federal de 1988"],
                       "urn": "urn:lex:br:federal:constituicao:1988-10-05;1988", "data": "1988-10-05",
                       "versao_texto": "compilada (texto vigente)",
                       "fonte": "https://www.planalto.gov.br/ccivil_03/constituicao/constituicaocompilado.htm"}
                body = text
            else:
                hdr, body = parse_header(text)
            urn, date = hdr.get("urn", ""), hdr.get("data", "")
            if not urn or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                st["skipped_no_header"] += 1
                continue
            if urn in seen:
                st["skipped_duplicate_urn"] += 1
                continue
            if urn in skip_urns:
                st["skipped_in_other_tier"] += 1
                continue
            rows = list(markdown_units(urn, hdr.get("titulo", urn), body, date, urn,
                                       evidence=f"{LEIS_REPO}@{commit}:{os.path.relpath(path, leis_dir)}"))
            if not rows:
                st["skipped_no_articles"] += 1
                continue
            seen.add(urn)
            fs.write(json.dumps(norm_source(urn, kind, hdr, commit), ensure_ascii=False, sort_keys=True) + "\n")
            st["norms"] += 1
            st["by_type"][kind] = st["by_type"].get(kind, 0) + 1
            tv = hdr.get("versao_texto", "") or "?"
            st["by_text_version"][tv] = st["by_text_version"].get(tv, 0) + 1
            st["norms_marked_revoked"] += hdr.get("revogada") == "true"
            for r in rows:
                fu.write(json.dumps(r["unit"], ensure_ascii=False, sort_keys=True) + "\n")
                st["units"] += 1
                st["units_repealed"] += r["repealed"]
                st["units_repeal_date_unknown"] += r["repeal_unknown"]
                for ev in r["events"]:
                    fe.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
                    st["events"] += 1
                    st["chars"] += len(ev.get("text") or "")
            if progress and st["norms"] % 2000 == 0:
                progress(st)
    st["tokens"] = st["chars"] // 4
    return st


# ----------------------------------------------------------------------------
# Tier "tax": BR-TaxQA-R legal texts (scraped, single-line)
# ----------------------------------------------------------------------------

_TYPE_RE = (r"(?i:Lei\s+Complementar|Lei\s+Delegada|Lei|Decreto-Lei|Decreto|Medida\s+Provisória|"
            r"Emenda\s+Constitucional|Instrução\s+Normativa|Portaria|"
            r"Ato\s+Declaratório\s+(?:Interpretativo|Normativo|Executivo)|Ato\s+Declaratório|"
            r"Parecer\s+Normativo|Parecer|Resolução|Solução\s+de\s+Consulta\s+Interna|"
            r"Solução\s+de\s+Consulta|Solução\s+de\s+Divergência|Circular|Despacho|Nota|Súmula)")
_ISSUER_RE = r"((?:\s+[A-Z][A-Za-z]{1,7}(?:/[A-Z]{2,5})?){0,2}?)"
_HEAD_RE = re.compile(
    r"(?P<type>" + _TYPE_RE + r")" + r"(?P<issuer>" + _ISSUER_RE[1:-1] + r")"
    r"\s+(?i:n)[ºo°.]{0,2}\s*(?P<num>\d[\d.]*(?:-\d{1,3})?)(?:\s*/\s*(?P<y2>\d{2,4}))?\s*[,–-]?\s*(?i:de)?\s*"
    r"(?P<d>\d{1,2})[ºo°]?\s+(?i:de)\s+(?P<m>(?i:" + _MONTH_RE + r"))\s+(?i:de)\s+(?P<y>\d{4})")
_HEAD_RE2 = re.compile(
    r"(?P<type>" + _TYPE_RE + r")" + r"(?P<issuer>" + _ISSUER_RE[1:-1] + r")"
    r"\s+(?i:n)[ºo°.]{0,2}\s*(?P<num>\d[\d.]*)\s*[,–-]?\s*(?i:de)?\s*"
    r"(?P<d>\d{1,2})[./](?P<mo>\d{1,2})[./](?P<y>\d{4})")
_FILE_NUM = re.compile(r"n[ºo°]\s*(\d[\d.]*)", re.I)
_ART_CAND = re.compile(
    r"(?<![\w“\"'«])Art(?:igo)?\.?\s+(\d{1,3}(?:\.\d{3})*)\s*(?:[ºo°])?(?:\s*-\s*([A-Z]{1,2})\b)?"
    r"(?=[\s.\-–—])|(?<![\w“\"'«])Artigo\s+[Úú]nico\b")
_SIGNATURE = re.compile(r"Bras[íi]lia,\s+\d{1,2}[ºo°]?\s+de\s+(?:" + _MONTH_RE + r")\s+de\s+\d{4}", re.I)
_OPEN_QUOTE = re.compile(r"[“\"«]\s*$")


def parse_norm_head(filedata: str, filename: str, dataset_title: str = "") -> dict | None:
    """Identify a scraped legal text: type, number, date, issuer, from its own heading.

    The match must carry the same number as the file name (the dataset names files after the act),
    so a citation of another act in the page's header is never taken for the heading. When the
    heading has no full date the dataset's own title is the fallback (``date_source`` says so)."""
    fn_num = _FILE_NUM.search(filename)
    want = fn_num.group(1).replace(".", "") if fn_num else None
    cands = []
    for text, label in ((filedata[:6000], "text"), (dataset_title, "dataset_title")):
        for rx in (_HEAD_RE, _HEAD_RE2):
            for m in rx.finditer(text):
                num = m.group("num").replace(".", "")
                if want and num.split("-")[0] != want:
                    continue
                mo = MONTHS[m.group("m").lower()] if rx is _HEAD_RE else int(m.group("mo"))
                d = iso(int(m.group("y")), mo, int(m.group("d")))
                if d:
                    cands.append((label, m, num, d))
                    break
            if cands:
                break
        if cands:
            break
    if not cands:
        return None
    label, m, num, d = cands[0]
    kind = TYPE_SLUGS[re.sub(r"\s+", " ", m.group("type").lower())]
    issuer = m.group("issuer").strip()
    authority = slug(issuer.split("/")[0]) if issuer else "federal"
    if kind in ("instrucao.normativa", "portaria", "resolucao", "parecer.normativo") or \
            kind.startswith("ato.declaratorio"):
        authority = authority if issuer else "federal"
    return {"kind": kind, "number": num, "date": d, "authority": authority,
            "title": re.sub(r"\s+", " ", m.group(0)).strip(), "date_source": label}


def split_flat_articles(text: str) -> list[tuple[str, str]]:
    """``(key, text)`` per article of a scraped single-line legal text.

    A candidate is a capitalised ``Art. N`` that is not an opening quotation (amending laws quote
    the articles they rewrite) and whose number continues the sequence: the next number, a
    lettered variant of the current one, or a short forward gap. Anything else is a citation or a
    quoted article and stays inside the article that contains it."""
    cands = []
    for m in _ART_CAND.finditer(text):
        before = text[max(0, m.start() - 4): m.start()]
        if _OPEN_QUOTE.search(before):
            continue
        key = "unico" if m.group(1) is None else m.group(1).replace(".", "") + \
            ("-" + m.group(2) if m.group(2) else "")
        cands.append((m.start(), key))
    accepted: list[tuple[int, str]] = []
    last_n, last_l = 0, ""
    for pos, key in cands:
        if key == "unico":
            if not accepted:
                accepted.append((pos, key))
            continue
        n_s, _, letter = key.partition("-")
        n = int(n_s)
        ok = False
        if not accepted:
            ok = n <= 3
        elif letter and n == last_n and letter > last_l:
            ok = True
        elif not letter and (last_n < n <= last_n + 12):
            ok = True
        if ok:
            accepted.append((pos, key))
            last_n, last_l = n, letter
    out = []
    for i, (pos, key) in enumerate(accepted):
        end = accepted[i + 1][0] if i + 1 < len(accepted) else len(text)
        seg = text[pos:end].strip()
        if i + 1 == len(accepted):
            sig = _SIGNATURE.search(seg)
            if sig:
                seg = seg[: sig.start()].strip()
        out.append((key, seg))
    return out


def flat_units(urn: str, title: str, text: str, date: str, source_id: str, *, evidence: str,
               certainty: str = "high") -> Iterator[dict]:
    """Rows (as ``markdown_units``) for one scraped text: articles when the text has them,
    otherwise the whole text as ``!doc`` (chunked)."""
    arts = split_flat_articles(text)
    seen: dict[str, int] = {}
    items: list[tuple[str, str, str]] = []
    if arts:
        for key, seg in arts:
            n = seen.get(key, 0) + 1
            seen[key] = n
            items.append(("art", key if n == 1 else f"{key}~{n}", seg))
    else:
        items.append(("doc", "", text.strip()))
    for prefix, key, seg in items:
        repealed = prefix == "art" and is_whole_repeal(seg)
        rdate, rcert = repeal_info(seg) if repealed else (None, "low")
        if rdate and rdate <= date:
            rdate = None
        for part, chunk in enumerate(chunk_text(seg), 1):
            uid = unit_id(urn, key, part, prefix)
            ttl = title + (f" — Art. {key.replace('unico', 'único')}" if prefix == "art" else "")
            ev = [{"id": f"{uid}@{date}", "unit_id": uid, "op": "create", "date": date, "text": chunk,
                   "recorded_at": date, "evidence": evidence,
                   "certainty": "low" if repealed else certainty, "axes": {"published": date}}]
            if repealed and rdate and part == 1:
                ev.append({"id": f"{uid}@{rdate}:repeal", "unit_id": uid, "op": "repeal", "date": rdate,
                           "recorded_at": rdate, "evidence": f"{evidence}; annotation: {_note(seg)}",
                           "certainty": rcert, "axes": {"published": rdate}})
            yield {"unit": {"id": uid, "source_id": source_id, "kind": "article" if prefix == "art" else "document",
                            "parent_id": None, "title": ttl},
                   "events": ev, "repealed": repealed and bool(rdate) and part == 1,
                   "repeal_unknown": repealed and not rdate and part == 1, "label": seg[:60]}


TAXQA_REPO = "unicamp-dl/BR-TaxQA-R"
TAXQA_REVISION = "9f0f4263928c6152a40f888da3e63375a24bb0f3"
TAXQA_FILES = ("questions_QA_2024_v1.1.json", "referred_legal_documents_QA_2024_v1.1.json")
_TYPE_NAMES = {}
for _k, _v in TYPE_SLUGS.items():
    _TYPE_NAMES.setdefault(_v, _k)
_MONTH_NAMES = {v: k for k, v in MONTHS.items()}


def canonical_title(h: dict, issuer: str = "") -> str:
    """Display title built from the parsed pieces: ``Lei nº 11.196, de 21 de novembro de 2005``."""
    y, m, d = h["date"].split("-")
    num = h["number"]
    n = num.split("-")
    ns = f"{int(n[0]):,}".replace(",", ".") + ("-" + n[1] if len(n) > 1 else "")
    name = _TYPE_NAMES[h["kind"]].capitalize()
    name = {"Decreto-lei": "Decreto-Lei"}.get(name, name)
    iss = f" {issuer}" if issuer else ""
    return f"{name}{iss} nº {ns}, de {int(d)}{'º' if int(d) == 1 else ''} de {_MONTH_NAMES[int(m)]} de {y}"


def _names_for(urn: str, best: dict, left_out: dict, file_titles: dict) -> tuple[list[str], list[str]]:
    """Names and acronyms the dataset itself gives one norm: the stems of the files that hold its
    text and the acronyms its reference titles spell out (``(CTN)``, ``- RIR/2018``)."""
    files = [best[urn]["file"]] + [f for f, w in left_out.items()
                                  if w.startswith("same urn as ") and w[12:].split(" (")[0] == best[urn]["file"]]
    names, aliases = [], []
    for f in files:
        stem = re.sub(r"\.txt$", "", f)
        if stem not in names:
            names.append(stem)
        num = urn.rsplit(";", 1)[-1].split("-")[0]
        dotted = f"{int(num):,}".replace(",", ".") if num.isdigit() else num
        for t in file_titles.get(f, ()):
            if not re.search(rf"n[ºo°]\s*{re.escape(dotted)}\b", t):
                continue  # only titles that name this very act
            for a in _explicit_acronyms(t):
                if a not in aliases:
                    aliases.append(a)
    for stem in list(names):
        for a in _explicit_acronyms(stem):
            if a not in aliases:
                aliases.append(a)
    return names, aliases


def _explicit_acronyms(name: str) -> list[str]:
    return [a or b for a, b in re.findall(r"\(([A-Z][A-Za-z0-9/.-]{1,12})\)|\s[-–—]\s([A-Z][A-Z0-9/]{1,12})(?=[,\s]|$)", name)]


def build_tax(raw_dir: str, out_dir: str) -> dict:
    """Tier ``tax``: units from the legal texts of BR-TaxQA-R. Returns the statistics
    (including ``files``: file name -> urn, and the lists of texts left out)."""
    import collections
    import os
    with open(os.path.join(raw_dir, TAXQA_FILES[1]), encoding="utf-8") as fh:
        docs = {d["filename"]: d["filedata"] for d in json.load(fh)}
    with open(os.path.join(raw_dir, TAXQA_FILES[0]), encoding="utf-8") as fh:
        questions = json.load(fh)
    f2t: dict[str, set] = collections.defaultdict(set)
    for q in questions:
        for lst in (q.get("all_formatted_references") or {}).values():
            for e in lst:
                f2t[e["file"]].add(e["título"])
    best: dict[str, dict] = {}
    left_out: dict[str, str] = {}
    file_titles = {fn: sorted(t) for fn, t in f2t.items()}
    for fn, text in docs.items():
        if fn.startswith("Constituição Federal"):
            left_out[fn] = "provided by the federal tier (ctresb/leis constituicao.md)"
            continue
        tit = sorted(f2t.get(fn, ()), key=len)[-1] if f2t.get(fn) else ""
        h = parse_norm_head(text, fn, tit)
        if not h:
            left_out[fn] = "no norm number and date could be read from the text or the dataset title"
            continue
        issuer = ""
        mm = _HEAD_RE.search(text[:6000]) or _HEAD_RE2.search(text[:6000])
        if mm and h["date_source"] == "text":
            issuer = mm.group("issuer").strip()
        urn = norm_urn(h["kind"], h["date"], h["number"], h["authority"])
        title = canonical_title(h, issuer)
        rows = list(flat_units(urn, title, text, h["date"], urn,
                               evidence=f"{TAXQA_REPO}@{TAXQA_REVISION}:{fn}",
                               certainty="high" if h["date_source"] == "text" else "medium"))
        prev = best.get(urn)
        if prev is None or len(rows) > len(prev["rows"]):
            if prev:
                left_out[prev["file"]] = f"same urn as {fn} (kept the text with more units)"
            best[urn] = {"rows": rows, "file": fn, "h": h, "title": title, "issuer": issuer}
        else:
            left_out[fn] = f"same urn as {prev['file']} (kept the text with more units)"
    os.makedirs(out_dir, exist_ok=True)
    st = {"norms": 0, "units": 0, "events": 0, "chars": 0, "units_repealed": 0,
          "units_repeal_date_unknown": 0, "docs_without_articles": 0, "date_from_dataset_title": 0,
          "files": {}, "left_out": left_out, "by_type": {}}
    with open(os.path.join(out_dir, "sources.jsonl"), "w", encoding="utf-8") as fs, \
            open(os.path.join(out_dir, "units.jsonl"), "w", encoding="utf-8") as fu, \
            open(os.path.join(out_dir, "events.jsonl"), "w", encoding="utf-8") as fe:
        for urn in sorted(best):
            b = best[urn]
            h = b["h"]
            names, aliases = _names_for(urn, best, left_out, file_titles)
            src = {"id": urn, "kind": "norm", "authority": _AUTH.get(h["kind"], 3), "coverage": 3,
                   "licence": f"CC BY 4.0 ({TAXQA_REPO}); the texts are scraped official acts",
                   "meta": {"title": b["title"], "type": h["kind"], "file": b["file"], "tier": "tax",
                            "date_source": h["date_source"], "revision": TAXQA_REVISION,
                            "names": names, "aliases": aliases}}
            fs.write(json.dumps(src, ensure_ascii=False, sort_keys=True) + "\n")
            st["norms"] += 1
            st["by_type"][h["kind"]] = st["by_type"].get(h["kind"], 0) + 1
            st["date_from_dataset_title"] += h["date_source"] != "text"
            st["files"][b["file"]] = urn
            for fn2, u2 in ():
                pass
            if not any(r["unit"]["kind"] == "article" for r in b["rows"]):
                st["docs_without_articles"] += 1
            for r in b["rows"]:
                fu.write(json.dumps(r["unit"], ensure_ascii=False, sort_keys=True) + "\n")
                st["units"] += 1
                st["units_repealed"] += r["repealed"]
                st["units_repeal_date_unknown"] += r["repeal_unknown"]
                for ev in r["events"]:
                    fe.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
                    st["events"] += 1
                    st["chars"] += len(ev.get("text") or "")
    # (names and aliases are added below, once every file's urn is known)
    # files that lost a URN tie still map to the urn that was kept
    for fn, why in left_out.items():
        if why.startswith("same urn as "):
            keep = why[len("same urn as "):].split(" (")[0]
            for u, b in best.items():
                if b["file"] == keep:
                    st["files"][fn] = u
    st["tokens"] = st["chars"] // 4
    return st


# ----------------------------------------------------------------------------
# Questions
# ----------------------------------------------------------------------------

TAXQA_AS_OF = "2024-12-31"
N_DEV = 100
SEED = 20261112
_ART_NUM = re.compile(r"^\s*(\d+)\s*[ºo°]?(?:\s*-\s*([A-Z]))?\s*$")
_ART_RANGE = re.compile(r"^\s*(\d+)\s*[ºo°]?\s+a\s+(\d+)\s*[ºo°]?\s*$")


def gold_article_keys(artigo: str) -> list[str]:
    """Article keys named by a BR-TaxQA-R ``artigo`` value ("8º", "15-A", "10 a 13"); anything else
    (a chapter, an inciso alone) names no article and yields nothing."""
    m = _ART_NUM.match(artigo)
    if m:
        return [m.group(1) + ("-" + m.group(2) if m.group(2) else "")]
    m = _ART_RANGE.match(artigo)
    if m and 0 <= int(m.group(2)) - int(m.group(1)) <= 60:
        return [str(i) for i in range(int(m.group(1)), int(m.group(2)) + 1)]
    return []


def taxqa_questions(raw_dir: str, files: dict[str, str], unit_ids: set[str]) -> tuple[list[dict], dict]:
    """BR-TaxQA-R questions as rows, with gold units resolved against the built corpus."""
    with open(f"{raw_dir}/{TAXQA_FILES[0]}", encoding="utf-8") as fh:
        qs = json.load(fh)
    rows, st = [], {"questions": 0, "with_article_gold": 0, "with_resolved_gold": 0,
                    "gold_refs": 0, "gold_refs_resolved": 0, "gold_refs_unresolved": 0}
    for q in qs:
        gold: list[str] = []
        has = False
        for lst in (q.get("all_formatted_references") or {}).values():
            for e in lst:
                for a in e.get("artigos") or []:
                    keys = gold_article_keys(str(a.get("artigo", "")))
                    if not keys:
                        continue
                    has = True
                    for key in keys:
                        st["gold_refs"] += 1
                        urn = files.get(e.get("file"))
                        uid = f"{urn}!art{key}" if urn else None
                        if uid and uid in unit_ids:
                            st["gold_refs_resolved"] += 1
                            if uid not in gold:
                                gold.append(uid)
                        else:
                            st["gold_refs_unresolved"] += 1
        ans = q.get("answer_cleaned") or q.get("answer") or []
        ans = " ".join(ans) if isinstance(ans, list) else str(ans)
        rows.append({"id": f"taxqa-{q['question_number']}", "text": q["question_text"].strip(),
                     "answers": [re.sub(r"\s+", " ", ans).strip()], "answerable": True,
                     "as_of": TAXQA_AS_OF, "gold_units": gold, "cluster": q.get("question_summary", ""),
                     "kind": "gold" if gold else ("gold_unresolved" if has else "no_article_gold")})
        st["questions"] += 1
        st["with_article_gold"] += has
        st["with_resolved_gold"] += bool(gold)
    return rows, st


def split_taxqa(rows: list[dict], n_dev: int = N_DEV, seed: int = SEED) -> dict[str, list[dict]]:
    """Deterministic split: ids ordered by sha256(seed:id); the first ``n_dev`` are ``dev``, the
    rest ``test``."""
    import hashlib
    order = sorted(rows, key=lambda r: hashlib.sha256(f"{seed}:{r['id']}".encode()).hexdigest())
    return {"dev": order[:n_dev], "test": order[n_dev:]}


def _day_before(d: str) -> str:
    return (_dt.date.fromisoformat(d) - _dt.timedelta(days=1)).isoformat()


def temporal_questions(provisions: list[dict]) -> list[dict]:
    """Date-dependent questions built by code from version pairs: the same question as of the day
    before and the day of each change. ``gold_units`` carries ``<unit id>#<version seq>`` (the
    version in force at that date); after a repeal nothing is in force and the question is
    unanswerable (the right behaviour is to say the provision no longer applies)."""
    rows = []
    for p in provisions:
        art = p["article"]
        head = f"Segundo a {p['title']}, o que dispunha o art. {art}"
        d0, d1 = _day_before(p["change_date"]), p["change_date"]
        for tag, date, seq in (("before", d0, 0), ("after", d1, 1)):
            repealed = p["op"] == "repeal" and tag == "after"
            rows.append({
                "id": f"temporal-{slug(p['unit'])}-{tag}",
                "text": f"{head} na data de {date[8:]}/{date[5:7]}/{date[:4]}?",
                "answers": [], "answerable": not repealed, "as_of": date,
                "gold_units": [] if repealed else [f"{p['unit']}#v{seq}"],
                "cluster": p["unit"], "kind": f"temporal_{p['op']}_{tag}"})
    return rows


# ----------------------------------------------------------------------------
# Merge, manifest, loader
# ----------------------------------------------------------------------------

CORPUS_NAME = "brlaw"
CORPUS_FILES = ("sources.jsonl", "units.jsonl", "events.jsonl", "edges.jsonl")
LICENCE = ("tax tier: CC BY 4.0 (unicamp-dl/BR-TaxQA-R); federal tier: texts are official acts "
           "(Lei 9.610/1998 art. 8 as stated by ctresb/leis, scripts MIT), referenced by commit and "
           "URN, not redistributed; versioned tier: official texts of the Câmara dos Deputados portal")


def _rows(path: str) -> Iterator[dict]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def _sha(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for ch in iter(lambda: fh.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def merge_tiers(tiers_dir: str, out_dir: str, *, federal_keep=None) -> dict:
    """Merge the three tier folders into one corpus folder. A norm present in the tax tier is
    dropped from the federal tier (same URN); a provision of the versioned tier replaces the same
    unit id of the other tiers. ``federal_keep(urn) -> bool`` restricts the federal tier (used to
    build the documented embedding subset). Returns per-tier counts of what the corpus holds."""
    import os
    tax_urns = {s["id"] for s in _rows(f"{tiers_dir}/tax/sources.jsonl")}
    vers_units = {u["id"] for u in _rows(f"{tiers_dir}/versioned/units.jsonl")}
    os.makedirs(out_dir, exist_ok=True)
    cnt = {t: {"norms": 0, "units": 0, "events": 0, "chars": 0} for t in ("tax", "versioned", "federal")}
    seen_src: set[str] = set()
    skipped_fed: set[str] = set()
    with open(f"{out_dir}/sources.jsonl", "w", encoding="utf-8") as fs, \
            open(f"{out_dir}/units.jsonl", "w", encoding="utf-8") as fu, \
            open(f"{out_dir}/events.jsonl", "w", encoding="utf-8") as fe, \
            open(f"{out_dir}/edges.jsonl", "w", encoding="utf-8"):
        keep_units: dict[str, str] = {}
        for tier in ("tax", "versioned", "federal"):
            for s in _rows(f"{tiers_dir}/{tier}/sources.jsonl"):
                if tier == "federal" and (s["id"] in tax_urns or (federal_keep and not federal_keep(s["id"]))):
                    skipped_fed.add(s["id"])
                    continue
                if s["id"] in seen_src:
                    continue
                seen_src.add(s["id"])
                fs.write(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n")
                cnt[tier]["norms"] += 1
            for u in _rows(f"{tiers_dir}/{tier}/units.jsonl"):
                if tier == "federal" and u["source_id"] in skipped_fed:
                    continue
                if tier != "versioned" and u["id"] in vers_units:
                    continue
                if u["id"] in keep_units:
                    continue
                keep_units[u["id"]] = tier
                fu.write(json.dumps(u, ensure_ascii=False, sort_keys=True) + "\n")
                cnt[tier]["units"] += 1
            for e in _rows(f"{tiers_dir}/{tier}/events.jsonl"):
                if keep_units.get(e["unit_id"]) != tier:
                    continue
                fe.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
                cnt[tier]["events"] += 1
                cnt[tier]["chars"] += len(e.get("text") or "")
    for c in cnt.values():
        c["tokens"] = c["chars"] // 4
    return cnt


def build_corpus(root: str, leis_dir: str, leis_commit: str, raw_hf: str, *, name: str = CORPUS_NAME,
                 federal_keep=None, versioned_limit: int | None = 60, refetch: bool = False) -> str:
    """Build the three tiers (unless present), merge them into ``<root>/corpora/<name>`` and write
    the questions and ``MANIFEST.json``. Idempotent. Returns the corpus dir."""
    import os
    import shutil
    from . import brlaw_versioned as V
    tiers = os.path.join(root, "tiers")
    os.makedirs(tiers, exist_ok=True)
    tax_stats = f"{tiers}/tax_stats.json"
    if refetch or not os.path.exists(tax_stats):
        st = build_tax(raw_hf, f"{tiers}/tax")
        with open(tax_stats, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)
    fed_stats = f"{tiers}/federal_stats.json"
    if refetch or not os.path.exists(fed_stats):
        st = build_federal(leis_dir, f"{tiers}/federal", leis_commit)
        with open(fed_stats, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=1)
    if refetch or not os.path.exists(f"{tiers}/versioned/provisions.json"):
        st = V.build_versioned(os.path.join(root, "raw", "brlaw"), f"{tiers}/versioned", limit=versioned_limit)
        with open(f"{tiers}/versioned_stats.json", "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)
    cdir = os.path.join(root, "corpora", name)
    tmp = cdir + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    counts = merge_tiers(tiers, tmp, federal_keep=federal_keep)
    with open(tax_stats, encoding="utf-8") as fh:
        tax = json.load(fh)
    unit_ids = {u["id"] for u in _rows(f"{tmp}/units.jsonl")}
    taxq, qst = taxqa_questions(raw_hf, tax["files"], unit_ids)
    splits = split_taxqa(taxq)
    with open(f"{tiers}/versioned/provisions.json", encoding="utf-8") as fh:
        prov = json.load(fh)
    splits["temporal"] = temporal_questions(prov)
    with open(f"{tmp}/questions.jsonl", "w", encoding="utf-8") as fh:
        for sp, rs in splits.items():
            for r in rs:
                fh.write(json.dumps({**r, "split": sp}, ensure_ascii=False, sort_keys=True) + "\n")
    shutil.copy(f"{tiers}/versioned/provisions.json", f"{tmp}/provisions.json")
    with open(f"{tiers}/federal_stats.json", encoding="utf-8") as fh:
        fed = json.load(fh)
    manifest = {
        "name": name, "licence": LICENCE, "domain": "legal_br", "prompt_set": "legal_br",
        "sources": {
            "tax": {"repo": TAXQA_REPO, "revision": TAXQA_REVISION, "licence": "CC BY 4.0",
                    "files": {f: _sha(os.path.join(raw_hf, f)) for f in TAXQA_FILES}},
            "federal": {"repo": LEIS_REPO, "commit": leis_commit, "licence_texts": "official acts, not redistributed",
                        "licence_scripts": "MIT"},
            "versioned": {"site": "https://www2.camara.leg.br/legin/", "fetch_log": "tiers/versioned/fetch_log.json"},
        },
        "tiers_built": {"tax": {k: v for k, v in tax.items() if k not in ("files", "left_out")},
                        "federal": fed},
        "tax_left_out": tax["left_out"],
        "counts_in_corpus": counts,
        "questions": {"as_of_taxqa": TAXQA_AS_OF, "taxqa": qst,
                      "splits": {sp: {"n": len(rs), "ids_sha256": _ids_sha([r["id"] for r in rs])}
                                 for sp, rs in splits.items()}},
        "files": {f: _sha(os.path.join(tmp, f)) for f in (*CORPUS_FILES, "questions.jsonl", "provisions.json")},
    }
    manifest["corpus_tokens"] = sum(c["tokens"] for c in counts.values())
    with open(f"{tmp}/MANIFEST.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    shutil.rmtree(cdir, ignore_errors=True)
    os.replace(tmp, cdir)
    return cdir


CORE_FROM = "1995-01-01"


def core_filter(urn: str) -> bool:
    """Federal norms of the embedded subset ``brlaw-core``: dated ``CORE_FROM`` or later, and the
    Constitution. (Embedding the whole federal tier with the default local model takes hours.)"""
    m = _URN_DATE.match(urn)
    return bool(m) and (m.group(1) == "constituicao" or m.group(2) >= CORE_FROM)


_URN_DATE = re.compile(r"^urn:lex:br:[^:]+:([^:]+):(\d{4}-\d{2}-\d{2});")


def _ids_sha(ids: list[str]) -> str:
    import hashlib
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def load(root: str = "data", name: str = CORPUS_NAME):
    """The built corpus as a ``Dataset``: splits ``dev`` and ``test`` (BR-TaxQA-R) and ``temporal``.
    ``meta['prompt_set'] == 'legal_br'`` selects the Portuguese citation prompts."""
    import os
    from .types import Dataset, Question
    cdir = os.path.join(root, "corpora", name)
    with open(f"{cdir}/MANIFEST.json", encoding="utf-8") as fh:
        m = json.load(fh)
    splits: dict[str, list] = {}
    for r in _rows(f"{cdir}/questions.jsonl"):
        splits.setdefault(r["split"], []).append(Question(
            id=r["id"], text=r["text"], answers=tuple(r["answers"]), answerable=r["answerable"],
            as_of=r["as_of"], gold_units=tuple(r["gold_units"]), cluster=r["cluster"], kind=r["kind"]))
    for sp, info in m["questions"]["splits"].items():
        if _ids_sha([q.id for q in splits.get(sp, [])]) != info["ids_sha256"]:
            raise RuntimeError(f"{name}: split {sp} differs from MANIFEST.json")
    meta = {"domain": m["domain"], "prompt_set": m["prompt_set"], "manifest": f"{cdir}/MANIFEST.json",
            "counts": m["counts_in_corpus"], "description": "Brazilian federal law (citation-integrity test)"}
    return Dataset(name=name, corpus_dir=cdir, questions={k: tuple(v) for k, v in splits.items()},
                   licence=m["licence"], corpus_tokens=m["corpus_tokens"], meta=meta)
