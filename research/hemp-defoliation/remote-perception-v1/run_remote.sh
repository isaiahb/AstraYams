#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -s)" == Linux && -n "${RUNPOD_POD_ID:-}" ]] || { echo 'Remote RunPod only'; exit 2; }
cd /workspace/plant-pilot
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 HF_HOME=/workspace/plant-pilot/cache PYTHONUNBUFFERED=1
python -m pip install -q hydra-core iopath huggingface_hub safetensors pillow tqdm
[[ -d vendor-sam2 ]] || git clone -q https://github.com/facebookresearch/sam2.git vendor-sam2
git -C vendor-sam2 checkout -q 2b90b9f5ceec907a1c18123530e92e794ad901a4
SAM2_BUILD_CUDA=0 python -m pip install -q --no-deps --no-build-isolation ./vendor-sam2
echo 'SAM2_STARTED'
python worker.py --backend sam2 --manifest inputs.json --out results/sam2
echo 'SAM2_FINISHED'
[[ -d vendor-da3 ]] || git clone -q https://github.com/ByteDance-Seed/Depth-Anything-3.git vendor-da3
git -C vendor-da3 checkout -q 3d835ec1a5802d64a8b8b15f817a1ab54809bfe4
# Base image carries a distutils blinker package; isolate the replacement to this disposable worker.
python -m pip install -q --ignore-installed blinker
python -m pip install -q 'numpy<2' einops imageio 'opencv-python<4.12' trimesh open3d fastapi uvicorn typer omegaconf evo e3nn 'moviepy==1.0.3' plyfile pillow_heif pycolmap
python -m pip install -q --no-deps ./vendor-da3
echo 'DEPTH_STARTED'
python worker.py --backend depth --manifest inputs.json --out results/depth
python -m pip freeze > results/dependencies.txt
find cache -type f -size +10M -exec sha256sum {} \; > results/checkpoint-hashes.txt
echo 'PILOT_FINISHED'
