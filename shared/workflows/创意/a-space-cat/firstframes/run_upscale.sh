#!/bin/bash
cd /workspace/kepu-pipeline
P=projects/a-space-cat
for n in 02 03 04 08 09 10 13 14 19 21 25 29 30 31 34 38 41 42 45 47; do
  f=$P/refs/shots/shot$n.png; case $n in 25|31|34) f=$P/refs/shots/shot${n}_r2.png;; esac
  echo "$(date '+%F %T') start shot$n <- $f"
  .venv-upscale/bin/python scripts/upscale_frame.py --in $f --out $P/firstframes/shot$n.png --method realesrgan-anime --size 1080x1920 --fit crop --log $P/firstframes/upscale_log.jsonl
  echo "$(date '+%F %T') end shot$n rc=$?"
done
for n in 31 34; do
  .venv-upscale/bin/python scripts/upscale_frame.py --in $P/refs/shots/shot${n}_r2.png --out $P/firstframes/compare/shot${n}__lanczos.png --method lanczos --size 1080x1920 --fit crop --log $P/firstframes/compare/upscale_log.jsonl
done
echo ALLDONE $(date '+%F %T')
