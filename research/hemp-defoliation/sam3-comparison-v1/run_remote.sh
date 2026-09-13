#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -s)" = Linux && -n "${RUNPOD_POD_ID:-}" ]] || { echo 'REFUSED: RunPod Linux only'; exit 1; }
cd /workspace/sam3-comparison
# sam3.pt must be staged from official authenticated download and hash verified.
[[ -f checkpoint.json && -f sam3.pt ]] || { echo 'Official checkpoint not staged'; exit 1; }
if [[ ! -d sam3-src ]]; then git clone -q https://github.com/facebookresearch/sam3.git sam3-src; fi
git -C sam3-src checkout -q 660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7
python -m pip install -q -e ./sam3-src
python -m pip install -q einops pycocotools scipy matplotlib decord
timeout 900 python worker.py --backend sam3 --manifest inputs.json --out results/sam3 --checkpoint sam3.pt
timeout 600 python audit.py
python -m pip freeze > results/dependencies.txt
cp checkpoint.json results/checkpoint.json
