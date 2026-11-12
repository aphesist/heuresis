"""Compare the corpus with the Senate's lists of norms for sampled years (public API, no credentials).
Usage: check_coverage.py CORPUS_DIR"""
import json
import re
import sys
import time
import urllib.request

corpus = sys.argv[1]
src: dict = {}
for line in open(f"{corpus}/sources.jsonl", encoding="utf-8"):
    m = re.match(r"urn:lex:br:federal:([^:]+):(\d{4})-\d{2}-\d{2};(\d+)$", json.loads(line)["id"])
    if m:
        src.setdefault((m.group(1), int(m.group(2))), set()).add(m.group(3))
out = {}
YEARS = {"lei": (1960, 1975, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024),
         "lei.complementar": (1975, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024),
         "decreto.lei": (1940, 1950, 1960, 1970, 1975, 1980)}
for tipo, kind in (("LEI", "lei"), ("LCP", "lei.complementar"), ("DEL", "decreto.lei")):
    for year in YEARS[kind]:
        try:
            req = urllib.request.Request(
                f"https://legis.senado.leg.br/dadosabertos/legislacao/lista?tipo={tipo}&ano={year}",
                headers={"Accept": "application/json", "User-Agent": "heuresis-bench"})
            docs = json.load(urllib.request.urlopen(req, timeout=60))["ListaDocumento"]["documentos"]["documento"]
            docs = [docs] if isinstance(docs, dict) else docs
        except Exception as e:  # the API returns a different shape when a year has no norm of the type
            out[f"{kind}:{year}"] = f"no list ({type(e).__name__})"
            continue
        nums = {x["numero"] for x in docs if x.get("numero")}
        mine = src.get((kind, year), set())
        out[f"{kind}:{year}"] = {"senate": len(nums), "corpus": len(mine), "both": len(nums & mine),
                                 "missing_from_corpus_first6": sorted(nums - mine)[:6]}
        time.sleep(0.5)
print(json.dumps(out, indent=1))
