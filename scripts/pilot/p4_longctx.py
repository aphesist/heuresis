"""Item 4: is a reduced-corpus long-context tier possible for multihoprag? Nothing is saved
except a JSON summary. Articles are ordered by sha256(article id); the article id is the
unit id without the '#n' suffix, e.g. 'multihoprag:aab13a0697b'."""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from heuresis.bench.systems import _passage_line
from heuresis.model import Passage

name = "multihoprag"
ds, qs = load_dev(name)
cdir = ds.corpus_dir
texts, title = {}, {}
for l in open(os.path.join(cdir, "events.jsonl")):
    r = json.loads(l); texts[r["unit_id"]] = r["text"]
for l in open(os.path.join(cdir, "units.jsonl")):
    r = json.loads(l); title[r["id"]] = r["title"]
art = lambda u: u.split("#")[0]
by_art = {}
for u in texts:
    by_art.setdefault(art(u), []).append(u)


def prompt_chars(uids):
    """Characters of the document block as the long_context system would render it
    (one line per passage, header 'Documents:')."""
    tot = len("Documents:") + 1
    for u in uids:
        p = Passage(unit_id=u, seq=0, text=texts[u], title=u)
        tot += len(_passage_line("t1", p)) + 1 + 6  # mark width grows with n; +6 margin
    return tot


order = sorted(by_art, key=lambda a: hashlib.sha256(a.encode()).hexdigest())
res = {"n_articles": len(by_art), "n_passages": len(texts), "dev_n": len(qs)}
ans = [q for q in qs if q.answerable and q.gold_units]
unans = [q for q in qs if not q.answerable]
res["dev_answerable"], res["dev_unanswerable"] = len(ans), len(unans)
for label, div in (("chars_over_3.5", 3.5), ("chars_over_4", 4.0)):
    chosen, uids = [], []
    for a in order:
        trial = uids + by_art[a]
        if prompt_chars(trial) / div >= 80_000:
            break  # stop at the first article that would not fit (strict hash order)
        chosen.append(a); uids = trial
    S = set(chosen)
    full = [q for q in ans if all(art(g) in S for g in q.gold_units)]
    part = [q for q in ans if any(art(g) in S for g in q.gold_units)]
    res[label] = {"articles": len(chosen), "share_of_articles": len(chosen) / len(by_art),
                  "passages": len(uids), "prompt_chars": prompt_chars(uids),
                  "prompt_tokens_est": prompt_chars(uids) / div,
                  "dev_all_gold_inside": len(full), "dev_any_gold_inside": len(part),
                  "dev_unanswerable_valid": len(unans),
                  "dev_usable_total": len(full) + len(unans),
                  "full_ids": [q.id for q in full]}
# context: size needed to hold every gold article of the dev answerable questions
need = {art(g) for q in ans for g in q.gold_units}
nu = [u for a in need for u in by_art[a]]
res["gold_articles_union"] = {"articles": len(need), "passages": len(nu),
                              "tokens_est_chars_3.5": prompt_chars(nu) / 3.5}
# per-question number of distinct gold articles
from collections import Counter
res["gold_articles_per_q"] = dict(Counter(len({art(g) for g in q.gold_units}) for q in ans))
json.dump(res, open(os.path.join(OUT, name, "p4_longctx.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items()}, indent=1)[:3000])
