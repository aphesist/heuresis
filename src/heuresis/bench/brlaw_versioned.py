"""Tier ``versioned`` of the ``brlaw`` corpus: provisions with two real wordings.

For a base norm the Câmara dos Deputados publishes (a) the original publication and (b) the compiled
text, whose annotations name each amending act and link to its page. A provision enters this tier
only when its compiled article is touched by exactly one act (all its annotations are plain
"redação dada" or "revogado" notes, none deferring effects), the same article exists in the
original publication with different words, and the amending act's own page gives a publication
date. Both wordings are downloaded official text; nothing is composed, and every event stores the
page URLs and the literal annotation. Pages are cached under ``<raw>/camara`` with their sha256.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import os
import re
import time
import urllib.request
from typing import Any

from . import brlaw as B

UA = "heuresis-bench"
CAMARA = "https://www2.camara.leg.br/legin/"
#: Câmara pages of the base norms (found by search; verified when fetched).
BASE_NORMS = (
    "https://www2.camara.leg.br/legin/fed/lei/1995/lei-9250-26-dezembro-1995-362566-normaatualizada-pl.html",
    "https://www2.camara.leg.br/legin/fed/lei/1995/lei-9249-26-dezembro-1995-349062-normaatualizada-pl.html",
    "https://www2.camara.leg.br/legin/fed/lei/1988/lei-7713-22-dezembro-1988-372153-normaatualizada-pl.html",
    "https://www2.camara.leg.br/legin/fed/declei/1940-1949/decreto-lei-5452-1-maio-1943-415500-normaatualizada-pe.html",
)


def fetch(url: str, raw_dir: str, log: list[dict], *, delay: float = 1.0, tries: int = 5) -> str | None:
    """Download ``url`` once into the cache; returns the local path, or None when it cannot be had.
    Every fetch is logged with its sha256 and the retrieval date."""
    url = url.replace("http://www2.camara.gov.br/", CAMARA.replace("legin/", "")).replace(
        "www2.camara.gov.br", "www2.camara.leg.br")
    path = os.path.join(raw_dir, "camara", hashlib.sha256(url.encode()).hexdigest()[:16] + ".html")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = None
        for i in range(tries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code in (403, 429):
                    log.append({"url": url, "error": f"HTTP {e.code}: blocked, stopped"})
                    raise RuntimeError(f"{url}: HTTP {e.code}; site refuses automated access") from None
                if e.code == 404:
                    log.append({"url": url, "error": "HTTP 404"})
                    return None
                time.sleep(2 * (i + 1))
            except Exception:  # transient network failure
                time.sleep(2 * (i + 1))
        if data is None:
            log.append({"url": url, "error": "unreachable"})
            return None
        with open(path, "wb") as fh:
            fh.write(data)
        time.sleep(delay)
    with open(path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    log.append({"url": url, "file": os.path.basename(path), "sha256": sha,
                "retrieved": time.strftime("%Y-%m-%d", time.gmtime(os.path.getmtime(path)))})
    return path


def page_lines(path: str) -> list[str]:
    """Page body as one string per paragraph; anchors keep their target as ``⟦href⟧``."""
    t = open(path, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S | re.I)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', lambda m: m.group(2) + "⟦" + m.group(1) + "⟧", t, flags=re.S)
    t = re.sub(r"<br\s*/?>|</p>|</div>|</tr>|</li>|</h\d>|</table>", "\n", t, flags=re.I)
    t = _html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in t.split("\n")]
    return [ln for ln in lines if ln]


_HEADING = re.compile(r"^(CAP[ÍI]TULO|SE[ÇC][ÃA]O|T[ÍI]TULO|LIVRO|Subse[çc][ãa]o|DISPOSI[ÇC][ÕO]ES)\b")
_ARTL = re.compile(r"^Art(?:igo)?\.?\s*(\d{1,3}(?:\.\d{3})*)\s*(?:[ºo°])?(?:\s*-\s*([A-Z]{1,2})\b)?(?=[\s.\-–—]|$)")
_ANN = re.compile(r"\((?:[^()]|\([^()]*\))*\)")
_KW = re.compile(r"reda[çc][ãa]o|acrescid|inclu[íi]d|revogad|vetad|vig[êe]ncia|vide|efeitos|convertid", re.I)
_HREF = re.compile(r"⟦([^⟧]*)⟧")


def parse_articles(lines: list[str]) -> dict[str, dict]:
    """Articles of a compiled or original text: key -> {raw, clean, annotations}.

    ``annotations`` are the parenthesised notes of the article (text without anchors, plus the
    pages they link to). When a key repeats, the first occurrence wins."""
    out: dict[str, dict] = {}
    cur: list[str] | None = None
    key = ""
    for ln in lines:
        plain = _HREF.sub("", ln)
        m = _ARTL.match(plain)
        if m and re.match(r"Art", plain):
            key = m.group(1).replace(".", "") + ("-" + m.group(2) if m.group(2) else "")
            cur = [ln]
            out.setdefault(key, {"lines": cur})
            if out[key]["lines"] is not cur:
                cur = None
            continue
        if _HEADING.match(plain):
            cur = None
            continue
        if cur is not None:
            cur.append(ln)
    res = {}
    for k, v in out.items():
        raw = "\n".join(v["lines"])
        anns = []
        for a in _ANN.finditer(raw):
            if _KW.search(a.group(0)):
                anns.append({"text": re.sub(r"\s+", " ", _HREF.sub("", a.group(0))),
                             "hrefs": sorted(set(_HREF.findall(a.group(0))))})
        clean = _strip_annotations(raw)
        res[k] = {"raw": _HREF.sub("", raw), "clean": clean, "annotations": anns}
    return res


def _strip_annotations(raw: str) -> str:
    def repl(m):
        return "" if _KW.search(m.group(0)) else m.group(0)
    t = _ANN.sub(repl, raw)
    t = _HREF.sub("", t)
    return re.sub(r"[ \t]+\n", "\n", re.sub(r" {2,}", " ", t)).strip()


def norm_words(t: str) -> str:
    return re.sub(r"\W+", " ", B.strip_accents(t).lower()).strip()


_PUB = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4}),\s*P[áa]gina")
_ENTRY = re.compile(r"(?:Esta|Este|[ÊE]ste|[ÊE]sse|O\s+presente|A\s+presente)\s+(?:Lei|Decreto|Medida\s+Provis[óo]ria)[^.]{0,40}?"
                    r"(?:entra|entrará|entrar[áa])\s+em\s+vigor([^.]*)\.", re.I)


def publication_date(norma_lines: list[str]) -> str | None:
    """Publication date of the original text from a Câmara "Dados da Norma" page."""
    for i, ln in enumerate(norma_lines):
        if ln.startswith("Texto - Publicação Original"):
            for nxt in norma_lines[i: i + 6]:
                m = _PUB.search(nxt)
                if m:
                    return B.iso(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def entry_into_force(orig_lines: list[str], pub: str) -> tuple[str | None, str, str]:
    """``(date, certainty, clause)`` from the act's own "entra em vigor" clause.

    The date is the publication date when the clause says "na data de sua publicação", the date the
    clause names when it names one, and ``None`` otherwise (a period such as "cento e vinte dias"
    is not computed here: the provision is then left out rather than dated by guess)."""
    text = " ".join(orig_lines)
    m = _ENTRY.search(text)
    if not m:
        return None, "low", ""
    clause = re.sub(r"\s+", " ", m.group(0)).strip()
    if re.search(r"efeito", m.group(1), re.I):
        return None, "low", clause   # effects differ by article or are deferred: not one date for the act
    if re.search(r"data\s+de\s+sua\s+publica[çc][ãa]o", m.group(1), re.I):
        return pub, "high", clause
    d = B.long_date(m.group(1)) or (B.slash_dates(m.group(1)) or [None])[0]
    if d and re.search(r"\b(a\s+partir\s+d[eo]|em)\b", m.group(1), re.I) and not re.search(r"dias|ano|m[êe]s", m.group(1), re.I):
        return d, "high", clause
    return None, "low", clause


def sibling(url: str, kind: str) -> str:
    """Page of the same norm: ``norma`` (data page) or ``orig`` (original publication)."""
    m = re.search(r"-(normaatualizada|norma|publicacaooriginal-\d+)-(pl|pe)\.(html|doc|docx|pdf)$", url)
    base, ext = url[: m.start()], m.group(2)
    suffix = f"-norma-{ext}.html" if kind == "norma" else f"-publicacaooriginal-1-{ext}.html"
    return base + suffix




_VIDE = re.compile(
    r"^(Lei Ordinária|Lei Complementar|Decreto-Lei|Decreto|Medida Provisória|Emenda Constitucional)\s+nº\s*(\d+)"
    r"\s+de\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})", re.I)
_VIDE_KIND = {"lei ordinária": "lei", "lei complementar": "lei.complementar", "decreto-lei": "decreto.lei",
              "decreto": "decreto", "medida provisória": "medida.provisoria",
              "emenda constitucional": "emenda.constitucional"}
_ACT = re.compile(r"(Lei Complementar|Lei|Decreto-Lei|Decreto|Emenda Constitucional)\s+n[ºo°]\s*(\d[\d.]*)\s*,?\s+de\s+"
                  r"(\d{1,2}[ºo°]?\s*/\s*\d{1,2}\s*/\s*\d{4})", re.I)


def vide_map(norma_lines: list[str], norma_url: str) -> dict[tuple[str, str, str], str]:
    """``(type, number, date) -> page url`` of every act in the "Vide Norma(s)" log of a norm page
    (the Câmara's own per-provision alteration log; it links each act's data page)."""
    from urllib.parse import urljoin
    out = {}
    for ln in norma_lines:
        ln = ln.replace("Vide Norma(s):", "").strip()
        m = _VIDE.match(ln)
        h = _HREF.search(ln)
        if not (m and h):
            continue
        d = B.long_date(m.group(3))
        if d:
            out[(_VIDE_KIND[m.group(1).lower()], m.group(2), d)] = urljoin(norma_url, h.group(1))
    return out


def annotation_acts(text: str) -> set[tuple[str, str, str]]:
    """Acts named by an annotation: ``(type, number, iso date)``."""
    out = set()
    for m in _ACT.finditer(text):
        ds = B.slash_dates(m.group(3))
        if ds:
            out.add((_VIDE_KIND["lei ordinária" if m.group(1).lower() == "lei" else m.group(1).lower()],
                     m.group(2).replace(".", ""), ds[0]))
    return out


_EDIT = re.compile(r"reda[çc][ãa]o\s+dada|nova\s+reda[çc][ãa]o|revogad|acrescid|inclu[íi]d", re.I)
_REJECT = re.compile(r"efeito|convertid|vetad|em\s+vigor\s+a\s+partir|vig[êe]ncia\s+a\s+partir|Medida\s+Provis", re.I)
_ORIG_LINK = re.compile(r'href="([^"]*publicacaooriginal-\d+-p[le]\.html)"')


def _original_url(norma_path: str, norma_url: str) -> str | None:
    t = open(norma_path, encoding="utf-8", errors="replace").read()
    m = _ORIG_LINK.search(t)
    if not m:
        return None
    from urllib.parse import urljoin
    return urljoin(norma_url, m.group(1))


def _identify(lines: list[str]) -> dict | None:
    head = " ".join(lines[:60])
    m = B._HEAD_RE.search(head)
    if not m:
        return None
    d = B.iso(int(m.group("y")), B.MONTHS[m.group("m").lower()], int(m.group("d")))
    kind = B.TYPE_SLUGS[re.sub(r"\s+", " ", m.group("type").lower())]
    num = m.group("num").replace(".", "")
    return {"kind": kind, "number": num, "date": d, "urn": B.norm_urn(kind, d, num),
            "title": B.canonical_title({"kind": kind, "number": num, "date": d})}


def load_norm(url: str, raw_dir: str, log: list[dict]) -> dict | None:
    """Everything one Câmara norm offers: identity, publication date, entry into force, original
    and compiled articles. ``url`` may be any page of the norm."""
    norma_url = sibling(url, "norma")
    npath = fetch(norma_url, raw_dir, log)
    if not npath:
        return None
    nlines = page_lines(npath)
    pub = publication_date(nlines)
    ourl = _original_url(npath, norma_url)
    opath = fetch(ourl, raw_dir, log) if ourl else None
    if not (pub and opath):
        return None
    olines = page_lines(opath)
    ident = _identify(olines) or _identify(nlines)
    if not ident:
        return None
    eff, cert, clause = entry_into_force(olines, pub)
    settled = eff is not None
    if eff is None:
        eff, cert = pub, "medium"   # only the base norm's own date may fall back to publication
    return {**ident, "vides": vide_map(nlines, norma_url), "url_norma": norma_url, "url_original": ourl, "pub": pub, "effective": eff,
            "effective_certainty": cert, "entry_clause": clause, "effective_settled": settled, "original": parse_articles(olines),
            "original_lines": olines}


def select_provisions(prov: list[dict], limit: int | None) -> list[dict]:
    """Deterministic selection of at most ``limit`` provisions, round-robin over the amending acts
    (acts and provisions ordered by sha256 of their ids), so that no single reform dominates."""
    if not limit or len(prov) <= limit:
        return prov
    groups: dict[str, list[dict]] = {}
    for p in prov:
        groups.setdefault(p["act"], []).append(p)
    h = lambda x: hashlib.sha256(x.encode()).hexdigest()
    order = sorted(groups, key=h)
    for a in order:
        groups[a].sort(key=lambda p: h(p["unit"]))
    picked: list[dict] = []
    i = 0
    while len(picked) < limit:
        added = False
        for a in order:
            if i < len(groups[a]) and len(picked) < limit:
                picked.append(groups[a][i])
                added = True
        if not added:
            break
        i += 1
    keep = {p["unit"] for p in picked}
    return sorted((p for p in prov if p["unit"] in keep), key=lambda p: p["unit"])


def _write_tier(out_dir: str, prov: list[dict], units: list[dict], events: list[dict], sources: dict) -> None:
    os.makedirs(out_dir, exist_ok=True)
    used = {u["source_id"] for u in units}
    srcs = [v for k, v in sources.items() if v and k in used]
    for name, rows in (("sources", srcs), ("units", units), ("events", events)):
        with open(os.path.join(out_dir, name + ".jsonl"), "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    with open(os.path.join(out_dir, "provisions.json"), "w", encoding="utf-8") as fh:
        json.dump(prov, fh, ensure_ascii=False, indent=1)


def build_versioned(raw_dir: str, out_dir: str, base_urls=BASE_NORMS, limit: int | None = 60,
                    test_limit: int | None = 120) -> dict:
    log: list[dict] = []
    os.makedirs(out_dir, exist_ok=True)
    sources: dict[str, dict] = {}
    units, events = [], []
    prov: list[dict] = []
    st: dict[str, Any] = {"base_norms": [], "provisions": 0, "replaced": 0, "repealed": 0,
                          "excluded": {}, "acts": {}}

    def excl(why):
        st["excluded"][why] = st["excluded"].get(why, 0) + 1

    acts: dict[str, dict | None] = {}
    for url in base_urls:
        base = load_norm(url, raw_dir, log)
        cpath = fetch(url, raw_dir, log)
        if not base or not cpath:
            st["base_norms"].append({"url": url, "error": "could not load"})
            continue
        compiled = parse_articles(page_lines(cpath))
        st["base_norms"].append({"urn": base["urn"], "title": base["title"], "url": url,
                                 "articles_compiled": len(compiled), "articles_original": len(base["original"])})
        for key, art in compiled.items():
            edits = [a for a in art["annotations"] if _EDIT.search(a["text"])]
            if not edits:
                continue
            if any(_REJECT.search(a["text"]) for a in art["annotations"]):
                excl("annotation defers effects, converts a provisional measure or adds text")
                continue
            named = [annotation_acts(a["text"]) for a in edits]
            all_acts = set().union(*named)
            if len(all_acts) != 1 or any(not n for n in named):
                excl("amended by more than one act, or the act is not named")
                continue
            akey = next(iter(all_acts))
            href = base["vides"].get(akey)
            if not href:
                excl("amending act not in the Câmara alteration log")
                continue
            orig = base["original"].get(key)
            if not orig:
                excl("no such article in the original publication")
                continue
            if href not in acts:
                acts[href] = load_norm(href, raw_dir, log)
            act = acts[href]
            if not act:
                excl("amending act page could not be downloaded")
                continue
            if not act["effective_settled"]:
                excl("entry into force of the amending act is not settled by its clause")
                continue
            ann_dates = {d for a in edits for d in B.slash_dates(a["text"])}
            if act["date"] not in ann_dates:
                excl("annotation date differs from the act's own date")
                continue
            repeal = all(re.search(r"revogad", a["text"], re.I) for a in edits) and \
                B.is_whole_repeal(art["raw"])
            if not repeal and norm_words(orig["clean"]) == norm_words(art["clean"]):
                excl("wording unchanged between original and compiled text")
                continue
            if len(orig["clean"]) < 20 or (not repeal and len(art["clean"]) < 20):
                excl("text too short")
                continue
            uid = B.unit_id(base["urn"], key)
            if len(orig["clean"]) > B.MAX_UNIT_CHARS or len(art["clean"]) > B.MAX_UNIT_CHARS:
                excl("article longer than one unit")
                continue
            ann = "; ".join(a["text"] for a in edits)
            sources.setdefault(base["urn"], {
                "id": base["urn"], "kind": "norm", "authority": B._AUTH.get(base["kind"], 3), "coverage": 3,
                "licence": "official act; texts from the Câmara dos Deputados legislation portal",
                "meta": {"title": base["title"], "type": base["kind"], "tier": "versioned",
                         "origin": base["url_norma"], "entry_clause": base["entry_clause"]}})
            units.append({"id": uid, "source_id": base["urn"], "kind": "article", "parent_id": None,
                          "title": f"{base['title']} — Art. {key}"})
            events.append({"id": f"{uid}@{base['effective']}", "unit_id": uid, "op": "create",
                           "date": base["effective"], "text": orig["clean"], "recorded_at": base["pub"],
                           "evidence": f"{base['url_original']} (original publication, {base['pub']}); "
                                       f"entry into force: {base['entry_clause'] or 'not stated, publication date used'}",
                           "certainty": base["effective_certainty"],
                           "axes": {"published": base["pub"], "effects": base["effective"]}})
            vers = [{"from": base["effective"], "text": orig["clean"]}]
            op_date = act["effective"]
            if op_date <= base["effective"]:
                excl("amending act not later than the base norm")
                units.pop()
                events.pop()
                continue
            ev = {"id": f"{uid}@{op_date}", "unit_id": uid, "op": "repeal" if repeal else "replace",
                  "date": op_date, "recorded_at": act["pub"],
                  "evidence": f"{act['url_original']} (amending act, published {act['pub']}); "
                              f"{url} (compiled; annotation: {ann}); "
                              f"entry into force: {act['entry_clause'] or 'not stated, publication date used'}",
                  "certainty": act["effective_certainty"],
                  "axes": {"published": act["pub"], "effects": op_date}}
            if not repeal:
                ev["text"] = art["clean"]
                vers.append({"from": op_date, "text": art["clean"]})
            events.append(ev)
            st["acts"][act["urn"]] = act["title"]
            st["repealed" if repeal else "replaced"] += 1
            st["provisions"] += 1
            prov.append({"unit": uid, "norm": base["urn"], "title": base["title"], "article": key,
                         "op": ev["op"], "act": act["urn"], "act_title": act["title"],
                         "versions": vers, "change_date": op_date})
    st["candidates"] = len(prov)
    st["candidates_by_act"] = {}
    for p in prov:
        st["candidates_by_act"][p["act_title"]] = st["candidates_by_act"].get(p["act_title"], 0) + 1
    all_prov, all_units, all_events = prov, units, events
    prov = select_provisions(all_prov, limit)
    keep = {p["unit"] for p in prov}
    units = [u for u in all_units if u["id"] in keep]
    events = [e for e in all_events if e["unit_id"] in keep]
    st["provisions"] = len(prov)
    st["replaced"] = sum(p["op"] == "replace" for p in prov)
    st["repealed"] = sum(p["op"] == "repeal" for p in prov)
    st["acts"] = {p["act"]: p["act_title"] for p in prov}
    _write_tier(out_dir, prov, units, events, sources)
    # The qualifying candidates that were not selected: a held-out tier, written to its own folder
    # (``<out_dir>_test``), selected by the same rule and never read by this code.
    unused = [p for p in all_prov if p["unit"] not in keep]
    tprov = select_provisions(unused, test_limit)
    tkeep = {p["unit"] for p in tprov}
    st["candidates_unused"], st["test_provisions"] = len(unused), len(tprov)
    _write_tier(out_dir + "_test", tprov, [u for u in all_units if u["id"] in tkeep],
                [e for e in all_events if e["unit_id"] in tkeep], sources)
    seen, uniq = set(), []
    for r in log:
        k = (r.get("url"), r.get("sha256"))
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    with open(os.path.join(out_dir, "fetch_log.json"), "w", encoding="utf-8") as fh:
        json.dump(uniq, fh, ensure_ascii=False, indent=1)
    st["fetched_pages"] = len(uniq)
    st["tokens"] = sum(len(e.get("text") or "") for e in events) // 4
    st["units"], st["events"] = len(units), len(events)
    return st
