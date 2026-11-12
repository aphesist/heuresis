#!/usr/bin/env python3
"""Build site/index.html, heuresis's paper page (aphes.ist design system, system/page-types/paper), from README.md.

The honesty table and the dev-split date-filter table are read from README.md, so the page says nothing the README
does not. Run from the repository root: python3 site/build.py. A test (tests/test_site_page.py) checks the page is
current."""
import html, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
GH = "https://github.com/aphesist/heuresis/blob/main/"


def inline(md):
    """the README's inline markdown as html: code, bold, italics, links (relative ones to github)."""
    out, parts = [], re.split(r"(`[^`]*`)", md)
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append("<code>" + html.escape(p[1:-1]) + "</code>")
            continue
        t = html.escape(p, quote=False)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: '<a href="%s">%s</a>' % (
            m.group(2) if m.group(2).startswith("http") else GH + m.group(2), m.group(1)), t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", t)
        out.append(t)
    return "".join(out)


def table(section_heading, first_col):
    sec = README.split(section_heading, 1)[1]
    rows = []
    for line in sec.splitlines():
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] == first_col or set(cells[0]) <= set("-"):
            continue
        rows.append(cells)
    return rows


KINDS = ("measured", "modelled", "tested", "hypothesis")


def honesty_rows():
    out = []
    for claim, status, basis in table("## honesty table", "claim"):
        m = re.match(r"^\*\*(\w+)\*\*\s*(.*)$", status)
        if m and m.group(1) in KINDS:
            st = '<span class="lab-ev" data-ev="%s">%s</span>%s' % (m.group(1), m.group(1), (" " + inline(m.group(2))) if m.group(2) else "")
        else:
            st = inline(status)
        out.append("        <tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (inline(claim), st, inline(basis)))
    return "\n".join(out)


def date_filter():
    """[(system, (k, n, lo, hi) with the filter, (k, n, lo, hi) without)] from the README's date-filter table."""
    rows = []
    for sysname, a, b in table("**the date filter.**", "system"):
        f = lambda s: tuple(int(x) for x in re.match(r"(\d+)/(\d+) = \d+% \[(\d+), (\d+)\]", s).groups())
        rows.append((sysname, f(a), f(b)))
    return rows


def chart(rows):
    """a dot per system and condition, with its 95% wilson interval as a stippled band. x: share of questions."""
    L, R, W = 170, 500, 520
    X = lambda p: round(L + (R - L) * p / 100, 1)
    top, gap = 18, 30
    H = top + gap * len(rows) + 34
    g = ['<svg viewBox="0 0 %d %d" role="img" aria-label="on hoh dev, with the as-of filter the retrieved gold unit holds the version in force for 92 to 100 of 100 questions; searching as of today, for 42 to 49 of 100">' % (W, H)]
    g.append('<g class="lab-grid">' + "".join('<line x1="%s" x2="%s" y1="%d" y2="%d"/>' % (X(t), X(t), top - 8, H - 30) for t in (0, 25, 50, 75, 100)) + "</g>")
    g.append('<g class="lab-axis" transform="translate(0,%d)"><line class="domain" x1="%d" x2="%d" y1="0" y2="0"/>' % (H - 26, L, R))
    g += ['<g class="tick" transform="translate(%s,0)"><line y2="5"/><text y="18" text-anchor="middle">%d%%</text></g>' % (X(t), t) for t in (0, 25, 50, 75, 100)]
    g.append("</g>")
    for i, (name, a, b) in enumerate(rows):
        y = top + gap * i
        g.append('<text class="lab-label" x="0" y="%d">%s</text>' % (y + 4, html.escape(name)))
        for (k, n, lo, hi), cls in ((b, "lab-c2"), (a, "lab-c1")):
            g.append('<rect class="lab-band %s" x="%s" y="%d" width="%s" height="12" data-tip="%d/%d, 95%% wilson %d–%d"/>' % (cls, X(lo), y - 6, round(X(hi) - X(lo), 1), k, n, lo, hi))
            g.append('<rect class="lab-dot %s" x="%s" y="%d" width="6" height="6"/>' % (cls, round(X(100 * k / n) - 3, 1), y - 3))
    g.append("</svg>")
    return "\n        ".join(g)


def date_table(rows):
    return "\n".join('          <tr><th scope="row">%s</th><td class="num">%d/%d</td><td class="num">%d–%d</td><td class="num">%d/%d</td><td class="num">%d–%d</td></tr>'
                     % (html.escape(n), a[0], a[1], a[2], a[3], b[0], b[1], b[2], b[3]) for n, a, b in rows)


def main():
    rows = date_filter()
    page = (ROOT / "site" / "page.html").read_text(encoding="utf-8")
    page = page.replace("<!--HONESTY-->", honesty_rows()).replace("<!--DATE-CHART-->", chart(rows)).replace("<!--DATE-TABLE-->", date_table(rows))
    out = ROOT / "site" / "index.html"
    if "--check" in sys.argv:
        ok = out.exists() and out.read_text(encoding="utf-8") == page
        print("current" if ok else "stale: run python3 site/build.py")
        return 0 if ok else 1
    out.write_text(page, encoding="utf-8")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    sys.exit(main())
