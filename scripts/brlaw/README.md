# scripts/brlaw

Scripts that build and check the `brlaw` corpus (see `docs/legal-citation-test.md`). They write only under
`--data` (default `data/`, git-ignored). Run from the repository root with `PYTHONPATH=src`.

| Script | What it does | Cost |
|---|---|---|
| `build.py` | downloads BR-TaxQA-R (pinned revision), builds the three tiers and the corpora `brlaw` (full) and `brlaw-core` (embedded subset); the federal tier needs a checkout of `ctresb/leis` at the pinned commit (`--leis`) and the versioned tier needs the Câmara portal | free |
| `embed.py` | ingests a corpus into a SQLite store and embeds it with the default local model | free (CPU) |
| `check_resolver.py` | the resolver's ceiling on the gold references of BR-TaxQA-R | free |
| `check_recall.py` | BM25 (and, once embedded, hybrid) recall of the gold provisions on the `dev` split at k = 8 | free |
| `check_coverage.py` | compares the corpus with the Senate's own lists of norms for sampled years | free (public API, no credentials) |
