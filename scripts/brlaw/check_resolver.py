"""The resolver's ceiling on BR-TaxQA-R's gold article references, rendered the way a lawyer writes them.
Usage: check_resolver.py DATA_DIR RAW_HF_DIR DB"""
import collections
import json
import re
import sys

from heuresis.bench import brlaw as B
from heuresis.domains import get_domain
from heuresis.store import Store

data, raw, db = sys.argv[1:4]
st, dom = Store(db), get_domain("legal_br")
files = json.load(open(f"{data}/tiers/tax_stats.json"))["files"]
qs = json.load(open(f"{raw}/{B.TAXQA_FILES[0]}"))
NAT = re.compile(r"((?:Lei Complementar|Lei|Decreto-Lei|Decreto|Medida Provisória|Emenda Constitucional|"
                 r"Instrução Normativa(?: [A-Z]{2,6})?|Portaria(?: [A-Za-z]{2,6})?|Ato Declaratório(?: [A-Za-zç]+)?"
                 r"(?: [A-Z]{2,6})?|Parecer Normativo(?: [A-Za-z]{2,6})?|Solução de Consulta(?: [A-Za-z]+)?(?: [A-Za-z]+)?"
                 r"|Resolução(?: [A-Z]{2,6})?)\s+n[ºo°]\s*[\d.]+)(?:-\d+)?,?\s*"
                 r"(?:de\s+(?:\d{1,2}[ºo°]?\s+de\s+[a-zç]+\s+de\s+)?(\d{4}))?")
c = collections.Counter()
for q in qs:
    for lst in (q.get("all_formatted_references") or {}).values():
        for e in lst:
            for a in e["artigos"]:
                for key in B.gold_article_keys(str(a["artigo"])):
                    c["gold_article_refs"] += 1
                    urn = files.get(e["file"])
                    uid = f"{urn}!art{key}" if urn else None
                    if not (uid and st.has_unit(uid)):
                        c["gold_unit_absent_from_corpus"] += 1
                        continue
                    c["gold_unit_exists_in_corpus"] += 1
                    ac = B._explicit_acronyms(e["título"])
                    m = NAT.search(e["título"])
                    nat = (f"{m.group(1)}/{m.group(2)}" if m.group(2) else m.group(1)) if m else None
                    text = f"art. {key} do {ac[0]}" if ac else (f"art. {key} da {nat}" if nat else f"art. {key} da {e['título']}")
                    ok = [r for r in dom.resolve_references(text, st) if r.status == "resolved" and r.unit_ids == (uid,)]
                    c["resolved_to_the_gold_unit"] += bool(ok)
print(json.dumps(c, indent=1))
