"""Folder of Markdown / plain-text files."""
from __future__ import annotations

import os
import re
import unicodedata
from urllib.parse import unquote

from ..model import Edge, Event, Source, Unit
from . import utc_date

MAX_CHUNK = 1200
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_WIKI = re.compile(r"\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|[^\]]*)?\]\]")
_MDLINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")
    return slug or "section"


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    lines = raw.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, raw
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            meta: dict[str, str] = {}
            for ln in lines[1:i]:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip("'\"")
            return meta, "\n".join(lines[i + 1 :])
    return {}, raw


def _chunk_paragraphs(body: str) -> list[str]:
    chunks: list[str] = []
    cur = ""
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        while len(para) > MAX_CHUNK:
            cut = para.rfind(" ", 0, MAX_CHUNK)
            cut = cut if cut > 0 else MAX_CHUNK
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(para[:cut].strip())
            para = para[cut:].strip()
        if cur and len(cur) + 2 + len(para) > MAX_CHUNK:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        chunks.append(cur)
    return chunks


def split_units(body: str, stem: str) -> list[tuple[str, str, str]]:
    """Return (slug, title, text) triples for one file body."""
    lines = body.split("\n")
    sections: list[tuple[list[str], list[str]]] = [([], [])]  # (heading path, lines)
    stack: list[tuple[int, str]] = []
    in_fence = False
    has_heading = False
    for ln in lines:
        if _FENCE.match(ln):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(ln)
        if m:
            has_heading = True
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            sections.append(([t for _, t in stack], [ln]))
        else:
            sections[-1][1].append(ln)
    out: list[tuple[str, str, str]] = []
    if not has_heading:
        for i, chunk in enumerate(_chunk_paragraphs(body), 1):
            title = stem if i == 1 and len(_chunk_paragraphs(body)) == 1 else f"{stem} (part {i})"
            out.append((f"p{i}", title, chunk))
        return out
    seen: dict[str, int] = {}
    for path, sec in sections:
        text = "\n".join(sec).strip()
        if not path:
            if text:
                out.append(("top", stem, text))
            continue
        if not "\n".join(sec[1:]).strip():
            continue  # heading with no body of its own
        slug = "/".join(slugify(p) for p in path)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        out.append((slug, " > ".join(path), text))
    return out


class TextDomain:
    name = "text"
    axes: tuple[str, ...] = ()

    def read(self, path: str):
        root = os.path.abspath(path)
        files: list[str] = []
        for dp, dns, fns in os.walk(root):
            dns[:] = sorted(d for d in dns if not d.startswith("."))
            for fn in sorted(fns):
                if fn.lower().endswith((".md", ".txt")) and not fn.startswith("."):
                    files.append(os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, "/"))
        source = Source(id=f"text:{os.path.basename(root)}", kind="text")
        units: list[Unit] = []
        events: list[Event] = []
        edges: list[Edge] = []
        by_file: dict[str, list[tuple[str, str]]] = {}  # rel -> [(slug, unit id)]
        file_date: dict[str, str] = {}
        supersedes: list[tuple[str, str]] = []
        bodies: dict[str, list[tuple[str, str]]] = {}  # rel -> [(unit id, text)]
        for rel in files:
            full = os.path.join(root, rel)
            with open(full, encoding="utf-8", errors="replace") as fh:
                raw = fh.read().replace("\r\n", "\n")
            meta, body = parse_front_matter(raw)
            d = meta.get("date", "")
            date = d[:10] if _DATE.match(d) else utc_date(os.path.getmtime(full))
            file_date[rel] = date
            stem = os.path.splitext(os.path.basename(rel))[0]
            by_file[rel] = []
            bodies[rel] = []
            for slug, title, text in split_units(body, stem):
                uid = f"text:{rel}#{slug}"
                by_file[rel].append((slug, uid))
                bodies[rel].append((uid, text))
                units.append(Unit(id=uid, source_id=source.id, kind="passage", title=title))
                events.append(
                    Event(id=f"ev:{uid}:create", unit_id=uid, op="create", date=date,
                          text=text, recorded_at=date, evidence=rel)
                )
            if meta.get("supersedes"):
                supersedes.append((rel, meta["supersedes"].strip()))

        stems: dict[str, str] = {}
        for rel in files:
            stems.setdefault(os.path.splitext(os.path.basename(rel))[0].lower(), rel)

        def target(rel: str, anchor: str | None) -> str | None:
            slugs = by_file.get(rel)
            if not slugs:
                return None
            if anchor:
                a = slugify(anchor)
                for slug, uid in slugs:
                    if slug == a or slug.split("/")[-1] == a:
                        return uid
            return slugs[0][1]

        seen: set[tuple[str, str]] = set()

        def add_edge(src: str, dst: str | None) -> None:
            if dst and dst != src and (src, dst) not in seen:
                seen.add((src, dst))
                edges.append(Edge(src=src, dst=dst, type="cites"))

        for rel in files:
            base = os.path.dirname(rel)
            for uid, text in bodies[rel]:
                for m in _WIKI.finditer(text):
                    name = m.group(1).strip()
                    tgt = name if name in by_file else (
                        name + ".md" if name + ".md" in by_file else stems.get(name.lower()))
                    add_edge(uid, target(tgt, m.group(2)) if tgt else None)
                for m in _MDLINK.finditer(text):
                    href = m.group(1)
                    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith("#"):
                        continue
                    p, _, frag = href.partition("#")
                    tgt = os.path.normpath(os.path.join(base, unquote(p))).replace(os.sep, "/")
                    add_edge(uid, target(tgt, frag or None) if tgt in by_file else None)

        for rel, old in supersedes:
            old_rel = os.path.normpath(os.path.join(os.path.dirname(rel), old)).replace(os.sep, "/")
            if old_rel not in by_file:
                old_rel = os.path.normpath(old).replace(os.sep, "/")
            if old_rel not in by_file or old_rel == rel:
                continue
            for _, uid in by_file[old_rel]:
                events.append(
                    Event(id=f"ev:{uid}:repeal:{rel}", unit_id=uid, op="repeal",
                          date=file_date[rel], recorded_at=file_date[rel], evidence=rel)
                )
        return [source], units, events, edges

    def rules(self):
        return []

    def tools(self):
        return []

    def abstention_text(self, kind, query):
        return None
