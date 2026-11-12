#!/bin/bash
cd /home/user/heuresis
export PYTHONPATH=src
SYS=closed_book,bm25,hybrid,hybrid_rerank,agentic,engine,engine_single
for T in off default; do
  if [ $T = off ]; then EXTRA="--thinking disabled"; else EXTRA="--thinking default --set draft.max_tokens=4096"; fi
  for D in musique multihoprag hoh; do
    OUT=runs/dev2/$T/$D; mkdir -p $OUT; [ -f $OUT/store.sqlite ] || cp runs/stores/$D/store.sqlite $OUT/store.sqlite
    python3 -m heuresis.bench.run --dataset $D --split dev2 --systems $SYS --time-aware-variants --variants-of hybrid,agentic --workers 4 --out $OUT --paid --cap 4.00 --margin-usd 0.25 --ledger runs/dev2/ledger.jsonl $EXTRA 2>&1 | grep -v Warning
    rm -f $OUT/store.sqlite*   # keep disk; the store is a copy
  done
done
echo ALLDONE
