"""Benchmark dataset loaders.

Each dataset is downloaded once from a pinned revision into ``<root>/raw/<name>``,
converted to the ``jsonl`` exchange folder (``sources.jsonl``, ``units.jsonl``,
``events.jsonl``, ``edges.jsonl``) under ``<root>/corpora/<name>`` and described
by a ``MANIFEST.json`` carrying the source revision and sha256 hashes of every
built file and of the ordered question-id list of each split. Nothing under
``root`` is meant to be committed or redistributed.

Public API: ``load(name, root="data", ...) -> Dataset``, ``available()``,
``build(name, root)``, ``split_questions`` and ``split_passages``.

Splits are a pure function of the question pool and the seed: ids are ordered by
``sha256(f"{seed}:{id}")`` and dev, test and sealed are cut from that order, per
stratum, so the unanswerable fraction (or any other stratum) is preserved.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import urllib.request
from typing import Any, Callable, Iterable

from .types import Dataset, Question

SEED = 20261111
BUILD_VERSION = 1
SPLITS = ("dev", "test", "sealed")
#: A fourth split, cut from the questions that are in none of the three above, in the same
#: hash order and with the same stratification. It exists so that a design change made on
#: dev evidence can be checked on questions that evidence never touched. The three splits
#: above are computed exactly as before (their id-list hashes are unchanged).
EXTRA_SPLITS = ("dev2",)
N_DEV2 = 100

#: Datasets with no usable public release (see docs/datasets.md).
UNAVAILABLE = {
    "lawinforce_ecfr": "no public release found (paper only: AACL 2026, long.42)",
    "fiscalqa_pro": "no public release found (paper only: ICML 2026 virtual, poster 80578)",
}

# ----------------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------------


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ids_hash(ids: Iterable[str]) -> str:
    """Hash of an ordered id list (newline-joined, UTF-8)."""
    return sha256_bytes("\n".join(ids).encode("utf-8"))


def order_key(seed: int, qid: str) -> str:
    return sha256_bytes(f"{seed}:{qid}".encode("utf-8"))


def _allocate(m: int, remaining: dict[Any, int], weights: dict[Any, int]) -> dict[Any, int]:
    """Largest-remainder allocation of ``m`` picks across strata, proportional to
    ``weights`` and capped by ``remaining``. Deterministic (ties by key repr)."""
    keys = sorted(remaining, key=repr)
    total_w = sum(weights[k] for k in keys) or 1
    exact = {k: m * weights[k] / total_w for k in keys}
    alloc = {k: min(int(exact[k]), remaining[k]) for k in keys}
    left = m - sum(alloc.values())
    order = sorted(keys, key=lambda k: (-(exact[k] - int(exact[k])), repr(k)))
    while left > 0:
        progressed = False
        for k in order:
            if left == 0:
                break
            if alloc[k] < remaining[k]:
                alloc[k] += 1
                left -= 1
                progressed = True
        if not progressed:
            break
    return alloc


def split_questions(
    questions: list[Question],
    *,
    n_dev: int = 100,
    n_test: int = 500,
    n_sealed: int = 300,
    seed: int = SEED,
    stratum: Callable[[Question], Any] = lambda q: q.answerable,
    n_dev2: int = N_DEV2,
) -> dict[str, tuple[Question, ...]]:
    """Disjoint, deterministic dev/test/sealed splits, stratified by ``stratum``, and a
    fourth split ``dev2`` taken after them from what is left.

    Sizes shrink in the order dev, test, sealed, dev2 when the pool is smaller than the
    request. Inside a split questions are ordered by their hash. ``dev2`` follows the three
    others in the same per-stratum order, so it cannot change which ids they hold.
    """
    ids = [q.id for q in questions]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate question ids")
    by_id = {q.id: q for q in questions}
    strata: dict[Any, list[str]] = {}
    for q in sorted(questions, key=lambda q: order_key(seed, q.id)):
        strata.setdefault(stratum(q), []).append(q.id)
    weights = {k: len(v) for k, v in strata.items()}
    n = len(questions)
    sizes = {}
    left = n
    names = SPLITS + EXTRA_SPLITS
    for name, want in zip(names, (n_dev, n_test, n_sealed, n_dev2)):
        sizes[name] = max(0, min(want, left))
        left -= sizes[name]
    pointer = {k: 0 for k in strata}
    out: dict[str, tuple[Question, ...]] = {}
    for name in names:
        remaining = {k: len(strata[k]) - pointer[k] for k in strata}
        alloc = _allocate(sizes[name], remaining, weights)
        picked: list[str] = []
        for k, c in alloc.items():
            picked.extend(strata[k][pointer[k] : pointer[k] + c])
            pointer[k] += c
        picked.sort(key=lambda i: order_key(seed, i))
        out[name] = tuple(by_id[i] for i in picked)
    return out


_SENT = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[A-Z0-9])")


def _words(s: str) -> int:
    return len(s.split())


def split_passages(
    text: str, *, min_words: int = 150, max_words: int = 250
) -> list[str]:
    """Split ``text`` into passages of roughly ``min_words``..``max_words`` words at
    paragraph boundaries. A paragraph longer than ``max_words`` is cut at sentence
    boundaries (and at word boundaries if one sentence is itself too long). A short
    tail is merged into the previous passage when the result stays within 1.2 x
    ``max_words``. Text shorter than ``max_words`` is returned whole."""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    pieces: list[str] = []
    for p in paras:
        if _words(p) <= max_words:
            pieces.append(p)
            continue
        cur: list[str] = []
        for s in _SENT.split(p):
            w = s.split()
            if len(w) > max_words:  # pathological sentence: hard cut
                if cur:
                    pieces.append(" ".join(cur))
                    cur = []
                for i in range(0, len(w), max_words):
                    pieces.append(" ".join(w[i : i + max_words]))
                continue
            if cur and _words(" ".join(cur)) + len(w) > max_words:
                pieces.append(" ".join(cur))
                cur = []
            cur.append(s)
        if cur:
            pieces.append(" ".join(cur))
    out: list[str] = []
    cur_txt = ""
    for pc in pieces:
        if not cur_txt:
            cur_txt = pc
        elif _words(cur_txt) < min_words and _words(cur_txt) + _words(pc) <= max_words:
            cur_txt += "\n\n" + pc
        elif _words(cur_txt) + _words(pc) <= max_words:
            cur_txt += "\n\n" + pc
        else:
            out.append(cur_txt)
            cur_txt = pc
    if cur_txt:
        out.append(cur_txt)
    if len(out) >= 2 and _words(out[-1]) < min_words // 2:
        if _words(out[-2]) + _words(out[-1]) <= int(max_words * 1.2):
            out[-2] += "\n\n" + out.pop()
    return out


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def locate_fact(passages: list[str], fact: str) -> tuple[int, bool]:
    """Index of the passage containing ``fact`` (normalised substring); otherwise
    the passage with the largest token overlap. Returns (index, exact)."""
    nf = _norm(fact)
    norm = [_norm(p) for p in passages]
    if nf:
        for i, p in enumerate(norm):
            if nf in p:
                return i, True
    ft = set(nf.split())
    best, bi = -1.0, 0
    for i, p in enumerate(norm):
        ov = len(ft & set(p.split())) / (len(ft) or 1)
        if ov > best:
            best, bi = ov, i
    return bi, False


# ----------------------------------------------------------------------------
# Download
# ----------------------------------------------------------------------------


def _hf_url(repo: str, rev: str, fname: str) -> str:
    return f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{fname}"


def _download(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "heuresis-bench"})
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh)
    os.replace(tmp, dest)


SPECS: dict[str, dict[str, Any]] = {
    "musique": {
        "repo": "osunlp/HippoRAG_2",
        "revision": "5ec05b38deecc3318bb432c69865959c56058990",
        "files": ["musique.json", "musique_corpus.json"],
        "licence": "CC BY 4.0 (MuSiQue, StonyBrookNLP/musique README); the Hugging Face "
        "card of osunlp/HippoRAG_2 states no licence",
        "description": "MuSiQue answerable dev, 1,000-question retrieval subset and passage "
        "corpus as released with HippoRAG 2",
    },
    "multihoprag": {
        "repo": "yixuantt/MultiHopRAG",
        "revision": "71ac0d0bd1f951d2d6b70311f7d2ae404e1ffa82",
        "files": ["MultiHopRAG.json", "corpus.json"],
        "licence": "ODC-By (Hugging Face dataset card, license: odc-by)",
        "description": "MultiHop-RAG: 2,556 news multi-hop queries (301 null) over 609 articles",
    },
    "hoh": {
        "repo": "russwest404/HoH-QAs",
        "revision": "8f12fd356240fa9386d20346fe1e1f9b928d1b64",
        "files": ["hoh_qas_240601_241201.parquet"],
        "licence": "Apache-2.0 for the HoH authors' contributions (Hugging Face card); "
        "Wikipedia evidence text CC BY-SA 4.0",
        "description": "HoH-QAs: Wikipedia facts that changed between monthly snapshots "
        "(2024-06 to 2024-12), each with dated versions of its evidence",
    },
}


def _raw_dir(root: str, name: str) -> str:
    return os.path.join(root, "raw", name)


def corpus_dir(root: str, name: str) -> str:
    return os.path.join(root, "corpora", name)


def download(name: str, root: str = "data") -> dict[str, str]:
    """Fetch the pinned raw files (skipping files already present); returns sha256s."""
    spec = SPECS[name]
    out = {}
    for f in spec["files"]:
        dest = os.path.join(_raw_dir(root, name), f)
        if not os.path.exists(dest):
            _download(_hf_url(spec["repo"], spec["revision"], f), dest)
        out[f] = sha256_file(dest)
    return out


# ----------------------------------------------------------------------------
# Builders: raw files -> (sources, units, events, questions, meta)
# ----------------------------------------------------------------------------

Built = dict[str, Any]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "unknown"


def _doc_id(*parts: str) -> str:
    return sha256_bytes("\n".join(parts).encode("utf-8"))[:10]


def _day(ts: str) -> str:
    return ts[:10]


def _create_event(unit_id: str, date: str, text: str, evidence: str, axes=None) -> dict:
    return {
        "id": f"{unit_id}@{date}",
        "unit_id": unit_id,
        "op": "create",
        "date": date,
        "text": text,
        "recorded_at": date,
        "evidence": evidence,
        "axes": axes or {},
    }


def _build_musique(raw: str) -> Built:
    with open(os.path.join(raw, "musique.json"), encoding="utf-8") as fh:
        qs = json.load(fh)
    with open(os.path.join(raw, "musique_corpus.json"), encoding="utf-8") as fh:
        corpus = json.load(fh)
    src = "musique:hipporag"
    sources = [
        {"id": src, "kind": "text", "authority": 0, "coverage": 4,
         "licence": "CC BY 4.0", "meta": {"origin": "MuSiQue answerable dev paragraphs"}}
    ]
    units, events, doc_of = [], [], {}
    for p in corpus:
        did = _doc_id(p["title"], p["text"])
        uid = f"musique:{did}#0"
        if (p["title"], p["text"]) in doc_of:
            continue
        doc_of[(p["title"], p["text"])] = uid
        units.append({"id": uid, "source_id": src, "kind": "passage", "title": p["title"]})
        events.append(_create_event(uid, "1970-01-01", p["text"], "musique paragraph"))
    questions = []
    for q in qs:
        gold = tuple(
            dict.fromkeys(
                doc_of[(p["title"], p["paragraph_text"])]
                for p in q["paragraphs"]
                if p["is_supporting"]
            )
        )
        family = q["id"].split("__")[0]
        answers = tuple(dict.fromkeys([q["answer"], *q.get("answer_aliases", [])]))
        questions.append(
            dict(id=f"musique:{q['id']}", text=q["question"], answers=answers,
                 answerable=bool(q.get("answerable", True)), as_of=None, gold_units=gold,
                 cluster=gold[0] if gold else q["id"], kind=family)
        )
    return {"sources": sources, "units": units, "events": events, "questions": questions,
            "stratum": "answerable", "meta": {"questions_in_pool": len(questions),
            "passages": len(units)}}


def _build_multihoprag(raw: str) -> Built:
    with open(os.path.join(raw, "MultiHopRAG.json"), encoding="utf-8") as fh:
        qs = json.load(fh)
    with open(os.path.join(raw, "corpus.json"), encoding="utf-8") as fh:
        arts = json.load(fh)
    sources, units, events = {}, [], []
    by_title: dict[str, list[str]] = {}
    texts: dict[str, list[str]] = {}
    art_doc: dict[str, str] = {}
    for a in arts:
        did = "a" + _doc_id(a["url"])
        art_doc[a["title"]] = did
        sid = "multihoprag:" + _slug(a.get("source") or "unknown")
        sources.setdefault(sid, {
            "id": sid, "kind": "news", "authority": 0, "coverage": 4, "licence": "ODC-By",
            "meta": {"outlet": a.get("source")}})
        date = _day(a["published_at"])
        parts = split_passages(a["body"])
        ids = []
        for n, part in enumerate(parts):
            uid = f"multihoprag:{did}#{n}"
            ids.append(uid)
            units.append({"id": uid, "source_id": sid, "kind": "passage",
                          "parent_id": None, "title": a["title"]})
            events.append(_create_event(
                uid, date, part, a["url"],
                {"published": a["published_at"]}))
        by_title[a["title"]] = ids
        texts[a["title"]] = parts
    questions, exact, fallback = [], 0, 0
    for i, q in enumerate(qs):
        null = q["question_type"] == "null_query"
        gold: list[str] = []
        first_doc = ""
        for e in q["evidence_list"]:
            t = e["title"]
            if t not in by_title:
                continue
            idx, ok = locate_fact(texts[t], e.get("fact", ""))
            exact += ok
            fallback += not ok
            gold.append(by_title[t][idx])
            first_doc = first_doc or art_doc[t]
        questions.append(
            dict(id=f"multihoprag:q{i:04d}", text=q["query"],
                 answers=() if null else (str(q["answer"]),), answerable=not null,
                 as_of=None, gold_units=tuple(dict.fromkeys(gold)),
                 cluster=f"multihoprag:{first_doc}" if first_doc else f"multihoprag:q{i:04d}",
                 kind=q["question_type"]))
    return {"sources": list(sources.values()), "units": units, "events": events,
            "questions": questions, "stratum": "answerable",
            "meta": {"articles": len(arts), "passages": len(units),
                     "gold_exact_match": exact, "gold_overlap_fallback": fallback}}


def _build_hoh(raw: str) -> Built:
    try:
        import pyarrow.parquet as pq
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("the hoh loader needs pyarrow (pip install pyarrow)") from e
    rows = pq.read_table(os.path.join(raw, "hoh_qas_240601_241201.parquet")).to_pylist()
    src = "hoh:wikipedia"
    sources = [{"id": src, "kind": "wikipedia", "authority": 0, "coverage": 4,
                "licence": "Apache-2.0 (HoH); Wikipedia text CC BY-SA 4.0",
                "meta": {"snapshots": "monthly, 2024-06-01 .. 2024-12-01"}}]
    units, events, questions = [], [], []
    per_doc: dict[str, int] = {}
    dropped = {"no_change": 0, "same_answer": 0, "date_clash": 0}
    for r in rows:
        did = r["document"]["id"]
        n = per_doc.get(did, 0)
        per_doc[did] = n + 1
        uid = f"hoh:{did}#{n}"
        vers = [(o["last_modified_time"][:10], o["evidence"], o["answer"])
                for o in r["outdated_infos"]]
        vers.append((str(r["last_modified_time"])[:10], r["evidence"], r["answer"]))
        vers.sort(key=lambda v: v[0])
        # one version per snapshot date; drop consecutive identical texts
        clean: list[tuple[str, str, str]] = []
        for v in vers:
            if clean and clean[-1][0] == v[0]:
                dropped["date_clash"] += 1
                clean[-1] = v
            elif clean and clean[-1][1] == v[1]:
                continue
            else:
                clean.append(v)
        units.append({"id": uid, "source_id": src, "kind": "passage",
                      "title": r["document"]["title"]})
        for j, (d, ev, _a) in enumerate(clean):
            e = _create_event(uid, d, ev, f"wikipedia snapshot {d}", {"observed": d})
            e["op"] = "create" if j == 0 else "replace"
            events.append(e)
        if len(clean) < 2:
            dropped["no_change"] += 1
            continue
        pick = int(_doc_id("hoh-asof", uid), 16) % len(clean)
        d, _ev, ans = clean[pick]
        others = {_norm(v[2]) for k, v in enumerate(clean) if k != pick}
        if _norm(ans) in others or not _norm(ans):
            dropped["same_answer"] += 1
            continue
        questions.append(dict(
            id=f"{uid}@{d}", text=r["question"], answers=(ans,), answerable=True, as_of=d,
            gold_units=(uid,), cluster=f"hoh:{did}",
            kind="current" if pick == len(clean) - 1 else "outdated"))
    return {"sources": sources, "units": units, "events": events, "questions": questions,
            "stratum": "kind", "meta": {"records": len(rows), "units": len(units),
            "dropped": dropped, "validity_note": "valid_from is the first monthly snapshot "
            "at which the text was observed; the true change happened up to one month earlier"}}


BUILDERS = {"musique": _build_musique, "multihoprag": _build_multihoprag, "hoh": _build_hoh}
STRATUM = {
    "answerable": lambda q: q.answerable,
    "kind": lambda q: q.kind,
}

# ----------------------------------------------------------------------------
# Build and load
# ----------------------------------------------------------------------------

_CORPUS_FILES = ("sources.jsonl", "units.jsonl", "events.jsonl", "edges.jsonl")


def _write_jsonl(path: str, rows: Iterable[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def _q_to_row(q: dict) -> dict:
    return {**q, "answers": list(q["answers"]), "gold_units": list(q["gold_units"])}


def _row_to_q(r: dict) -> Question:
    return Question(id=r["id"], text=r["text"], answers=tuple(r["answers"]),
                    answerable=r["answerable"], as_of=r["as_of"],
                    gold_units=tuple(r["gold_units"]), cluster=r["cluster"], kind=r["kind"])


def _manifest_path(cdir: str) -> str:
    return os.path.join(cdir, "MANIFEST.json")


def _read_manifest(cdir: str) -> dict | None:
    try:
        with open(_manifest_path(cdir), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _is_built(cdir: str) -> bool:
    m = _read_manifest(cdir)
    if not m or m.get("build_version") != BUILD_VERSION:
        return False
    try:
        return all(sha256_file(os.path.join(cdir, f)) == h for f, h in m["files"].items())
    except OSError:
        return False


def _compute_splits(rows: list[dict], stratum: str, n_dev, n_test, n_sealed, seed,
                    n_dev2: int = N_DEV2):
    qs = [_row_to_q(r) for r in rows]
    return split_questions(qs, n_dev=n_dev, n_test=n_test, n_sealed=n_sealed, seed=seed,
                           stratum=STRATUM[stratum], n_dev2=n_dev2)


def _split_record(splits: dict[str, tuple[Question, ...]], params: dict) -> dict:
    """The record of the three original splits. ``dev2`` is deliberately not in it: the
    record (and its id-list hashes) is what ``load`` checks and what the pre-registration
    quotes, and it must not change. See :func:`_dev2_record`."""
    base = {k: v for k, v in splits.items() if k in SPLITS}
    return {
        "params": params,
        "sizes": {k: len(v) for k, v in base.items()},
        "unanswerable": {k: sum(not q.answerable for q in v) for k, v in base.items()},
        "question_ids_sha256": {k: ids_hash(q.id for q in v) for k, v in base.items()},
    }


def _dev2_record(splits: dict[str, tuple[Question, ...]], n_dev2: int, n_pool: int) -> dict:
    """The record of ``dev2``, kept apart from the original split record. ``pool_unused`` is
    the number of questions in none of dev, test or sealed (what dev2 is cut from)."""
    v = splits["dev2"]
    used = sum(len(splits[k]) for k in SPLITS)
    return {"requested": n_dev2, "size": len(v), "pool_unused": n_pool - used,
            "unanswerable": sum(not q.answerable for q in v),
            "question_ids_sha256": ids_hash(q.id for q in v)}


def build(name: str, root: str = "data", *, n_test: int = 500, n_dev: int = 100,
          n_sealed: int = 300, seed: int = SEED, force: bool = False,
          n_dev2: int = N_DEV2) -> str:
    """Download (if needed) and build one corpus; idempotent. Returns the corpus dir."""
    if name in UNAVAILABLE:
        raise RuntimeError(f"{name}: {UNAVAILABLE[name]}")
    if name not in SPECS:
        raise KeyError(f"unknown dataset {name!r}; known: {sorted(SPECS) + sorted(UNAVAILABLE)}")
    cdir = corpus_dir(root, name)
    if not force and _is_built(cdir):
        _add_dev2_record(cdir, n_dev2, n_dev, n_test, n_sealed, seed)
        return cdir
    spec = SPECS[name]
    raw_hashes = download(name, root)
    built = BUILDERS[name](_raw_dir(root, name))
    tmp = cdir + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    _write_jsonl(os.path.join(tmp, "sources.jsonl"), built["sources"])
    _write_jsonl(os.path.join(tmp, "units.jsonl"), built["units"])
    _write_jsonl(os.path.join(tmp, "events.jsonl"), built["events"])
    _write_jsonl(os.path.join(tmp, "edges.jsonl"), [])
    _write_jsonl(os.path.join(tmp, "questions.jsonl"), (_q_to_row(q) for q in built["questions"]))
    chars = sum(len(e["text"] or "") for e in built["events"] if e["op"] == "create")
    # corpus_tokens counts the text of every version, i.e. what a store indexes
    chars_all = sum(len(e["text"] or "") for e in built["events"])
    rows = built["questions"]
    splits = _compute_splits(rows, built["stratum"], n_dev, n_test, n_sealed, seed, n_dev2)
    params = {"n_dev": n_dev, "n_test": n_test, "n_sealed": n_sealed, "seed": seed,
              "stratum": built["stratum"]}
    manifest = {
        "name": name,
        "build_version": BUILD_VERSION,
        "description": spec["description"],
        "licence": spec["licence"],
        "source": {"repo": spec["repo"], "revision": spec["revision"], "files": raw_hashes},
        "counts": {"sources": len(built["sources"]), "units": len(built["units"]),
                   "events": len(built["events"]), "questions": len(rows),
                   "unanswerable": sum(not q["answerable"] for q in rows),
                   "chars": chars_all, "chars_first_versions": chars},
        "corpus_tokens": chars_all // 4,
        "meta": built["meta"],
        "files": {f: sha256_file(os.path.join(tmp, f)) for f in (*_CORPUS_FILES, "questions.jsonl")},
        "splits": _split_record(splits, params),
        "dev2": _dev2_record(splits, n_dev2, len(rows)),
    }
    with open(_manifest_path(tmp), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    shutil.rmtree(cdir, ignore_errors=True)
    os.replace(tmp, cdir)
    return cdir


def _add_dev2_record(cdir: str, n_dev2: int, n_dev: int, n_test: int, n_sealed: int,
                     seed: int) -> None:
    """A corpus built before ``dev2`` existed has no ``dev2`` entry in its manifest: add it
    (only that key; the corpus files and the original ``splits`` record stay as they were)."""
    m = _read_manifest(cdir)
    if not m or "dev2" in m or "splits" not in m:
        return
    params = m["splits"]["params"]
    if (params["n_dev"], params["n_test"], params["n_sealed"], params["seed"]) != (
            n_dev, n_test, n_sealed, seed):
        return
    with open(os.path.join(cdir, "questions.jsonl"), encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    splits = _compute_splits(rows, params["stratum"], n_dev, n_test, n_sealed, seed, n_dev2)
    m["dev2"] = _dev2_record(splits, n_dev2, len(rows))
    with open(_manifest_path(cdir), "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
        fh.write("\n")


def load(name: str, root: str = "data", *, n_test: int = 500, n_dev: int = 100,
         n_sealed: int = 300, seed: int = SEED, n_dev2: int = N_DEV2) -> Dataset:
    """Build the corpus if needed and return the dataset with its splits: dev, test and
    sealed (hash-checked against the manifest) and dev2."""
    cdir = build(name, root, n_test=n_test, n_dev=n_dev, n_sealed=n_sealed, seed=seed,
                 n_dev2=n_dev2)
    manifest = _read_manifest(cdir)
    with open(os.path.join(cdir, "questions.jsonl"), encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    stratum = manifest["splits"]["params"]["stratum"]
    splits = _compute_splits(rows, stratum, n_dev, n_test, n_sealed, seed, n_dev2)
    params = {"n_dev": n_dev, "n_test": n_test, "n_sealed": n_sealed, "seed": seed,
              "stratum": stratum}
    rec = manifest["splits"]
    if rec["params"] == params:
        got = _split_record(splits, params)["question_ids_sha256"]
        if got != rec["question_ids_sha256"]:
            raise RuntimeError(f"{name}: split hashes differ from MANIFEST.json "
                               "(pre-registered splits changed)")
        rec2 = manifest.get("dev2")
        if rec2 is not None and rec2.get("requested") == n_dev2 and \
                _dev2_record(splits, n_dev2, len(rows))["question_ids_sha256"] != \
                rec2["question_ids_sha256"]:
            raise RuntimeError(f"{name}: dev2 hash differs from MANIFEST.json")
    meta = {**manifest["meta"], "manifest": _manifest_path(cdir),
            "source": manifest["source"], "counts": manifest["counts"],
            "splits": _split_record(splits, params),
            "dev2": _dev2_record(splits, n_dev2, len(rows)),
            "description": manifest["description"]}
    return Dataset(name=name, corpus_dir=cdir, questions=splits, licence=manifest["licence"],
                   corpus_tokens=manifest["corpus_tokens"], meta=meta)


def available(root: str = "data") -> dict[str, str]:
    """Status of every known dataset: built, raw_downloaded, not_downloaded,
    needs:<package>, or unavailable:<reason>."""
    out: dict[str, str] = {}
    for name, spec in SPECS.items():
        cdir = corpus_dir(root, name)
        if _is_built(cdir):
            out[name] = "built"
        elif name == "hoh" and not _has_pyarrow():
            out[name] = "needs:pyarrow"
        elif all(os.path.exists(os.path.join(_raw_dir(root, name), f)) for f in spec["files"]):
            out[name] = "raw_downloaded"
        else:
            out[name] = "not_downloaded"
    for name, why in UNAVAILABLE.items():
        out[name] = f"unavailable:{why}"
    return out


def _has_pyarrow() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


__all__ = ["load", "build", "available", "download", "split_questions", "split_passages",
           "locate_fact", "ids_hash", "SEED", "SPLITS", "EXTRA_SPLITS", "N_DEV2"]
