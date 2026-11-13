"""Join the blind reviewer's verdicts with the support judge's verdicts (via the key file).

usage: agreement.py KEY_JSON REVIEWER_CSV OUT_DIR
Writes agreement.json, reviewer_labels.csv (row id, split, system, judge, reviewer, reason without
provision text beyond what the reviewer wrote) -- no corpus text from the provision is copied.
"""
import csv, json, re, sys, collections

_QUOTE = re.compile(r'"[^"]*"|“[^”]*”|\'[^\']{12,}\'|«[^»]*»')


def trim(reason):
    """Drop quoted provision words: the committed labels carry no corpus text."""
    return _QUOTE.sub("…", reason or "")[:240]

LAB = ["SUPPORTED", "PARTIAL", "NOT_SUPPORTED"]


def kappa(pairs, labels):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca = collections.Counter(a for a, _ in pairs); cb = collections.Counter(b for _, b in pairs)
    pe = sum(ca[l] * cb[l] for l in labels) / (n * n)
    return None if pe == 1 else (po - pe) / (1 - pe)


def table(pairs):
    t = {j: {r: 0 for r in LAB} for j in LAB}
    for j, r in pairs:
        t[j][r] += 1
    return t


def main(key, rev, out):
    key = {k["row_id"]: k for k in json.load(open(key))}
    rv = {r["row_id"]: r for r in csv.DictReader(open(rev, encoding="utf-8"))}
    rows = []
    for rid, k in key.items():
        r = rv.get(rid)
        if r:
            rows.append({**k, "reviewer": r["verdict"].strip().upper(), "reason": r["reason"]})
    res = {"rows": len(rows), "missing": sorted(set(key) - set(rv))}

    def block(rs):
        pairs = [(x["judge"], x["reviewer"]) for x in rs]
        sup = [(x["judge"] == "SUPPORTED", x["reviewer"] == "SUPPORTED") for x in rs]
        dis = sum(a != b for a, b in sup)
        return {"n": len(rs), "table_judge_rows_by_reviewer_cols": table(pairs),
                "disagree_supported_vs_not": [dis, len(rs), dis / len(rs) if rs else None],
                "kappa_3x3": kappa(pairs, LAB),
                "kappa_supported_vs_not": kappa([("S" if a else "N", "S" if b else "N") for a, b in sup], ["S", "N"]),
                "judge_support_share": sum(a for a, _ in sup) / len(rs) if rs else None,
                "reviewer_support_share": sum(b for _, b in sup) / len(rs) if rs else None,
                "reviewer_supported_or_partial": sum(x["reviewer"] in ("SUPPORTED", "PARTIAL") for x in rs) / len(rs) if rs else None}
    res["overall"] = block(rows)
    res["by_system"] = {s: block([x for x in rows if x["system"] == s]) for s in sorted({x["system"] for x in rows})}
    res["by_split"] = {s: block([x for x in rows if x["split"] == s]) for s in sorted({x["split"] for x in rows})}
    res["rule_fires_over_20pct"] = res["overall"]["disagree_supported_vs_not"][2] > 0.20
    json.dump(res, open(f"{out}/agreement.json", "w"), indent=1)
    with open(f"{out}/reviewer_labels.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["row_id", "split", "system", "qid", "unit", "judge", "reviewer", "reason"])
        for x in rows:
            w.writerow([x["row_id"], x["split"], x["system"], x["qid"], x["unit"], x["judge"], x["reviewer"], trim(x["reason"])])
    print(json.dumps(res["overall"], indent=1)); print("rule fires:", res["rule_fires_over_20pct"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
