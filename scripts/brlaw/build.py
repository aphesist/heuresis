"""Build the brlaw corpora. See README.md in this folder."""
import argparse
import hashlib
import json
import os
import sys
import urllib.request

from heuresis.bench import brlaw as B

PIN = "c9f21b4ab11aa0d7ca6fe861d75028e94219c2d6"


def fetch_hf(raw: str) -> None:
    os.makedirs(raw, exist_ok=True)
    for f in B.TAXQA_FILES:
        dest = os.path.join(raw, f)
        if not os.path.exists(dest):
            url = f"https://huggingface.co/datasets/{B.TAXQA_REPO}/resolve/{B.TAXQA_REVISION}/{f}"
            urllib.request.urlretrieve(url, dest)
        print(f, hashlib.sha256(open(dest, "rb").read()).hexdigest())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--leis", required=True, help="checkout of github.com/ctresb/leis at the pinned commit")
    ap.add_argument("--commit", default=PIN)
    a = ap.parse_args()
    raw = os.path.join(a.data, "raw", "hf")
    fetch_hf(raw)
    for name, keep in (("brlaw", None), ("brlaw-core", B.core_filter)):
        d = B.build_corpus(a.data, a.leis, a.commit, raw, name=name, federal_keep=keep)
        m = json.load(open(os.path.join(d, "MANIFEST.json")))
        print(name, json.dumps(m["counts_in_corpus"]))


if __name__ == "__main__":
    sys.exit(main())
