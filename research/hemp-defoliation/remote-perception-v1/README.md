# Remote perception pilot — prepared, not executed

User constraint: no model inference/training on the Mac. Do not install torch,
download weights or run a parameter/render sweep locally. `worker.py` exits
before importing ML packages unless it runs on Linux with RUNPOD_POD_ID, and
also requires CUDA with no CPU/MPS fallback. Mac work is lightweight editing,
file transfer and inspection of finished results only.

## Proposed first experiment

Use one reference photograph and the existing matched-camera broad/narrow
model renders. No private partner photos are in the initial bundle. Run the
same preprocessing on both domains. A public source photo is only381x444;
upsampling or generative enhancement cannot recover its occluded leaves.

1. SAM3 image model: separate prompts for `leaf`, `leaflet`, `plant stem`,
   `flower cluster`. These are competing annotation levels, not additive
   counts. A palmate leaf contains several leaflets. A flower mask does not
   automatically provide individual bud counts. Checkpoint access is gated;
   do not accept terms or bypass the gate on the user's behalf.
2. If SAM3 checkpoint access is unavailable, SAM2.1 large automatic masks
   provide an ungated baseline. It produces unlabeled region proposals, not
   classified leaves/flowers. Retain every proposal and mark semantics unknown.
3. DA3-Small predicts relative depth per image as a low-cost feasibility check.
   Never treat different specimens as multiple views of one plant. Depth is
   a hypothesis, particularly for thin/occluded foliage, not a mechanical
   measurement. Preserve depth/confidence/cameras and normalization details.
4. Only after inspecting pilot masks, select difficult local crops and frozen
   prompts/thresholds for a larger pass. Report failures rather than just the
   best-looking mask. Do not optimize the plant against unreviewed predictions.

## Compare three sources of information

**Real photo → predicted masks.** Manually review a small fixed selection of
clear and overlapping organs. Record false positives, missed visible organs,
merged instances, split instances and uncertainty. Confidence is not calibrated
accuracy. Hidden organs are unknown, not absent.

**Synthetic RGB → predicted masks.** Apply exactly the same inference to the
render, at the same size/crop/camera. Differences can come from rendering style
as well as anatomy; keep neutral and display-style renders as separate tests.

**Synthetic scene → exact visible organ-ID/depth buffers.** Export instance IDs
with a z-buffer, no lighting/antialias mixing. Group leaflet IDs into parent leaf
IDs; include petioles, stems and reproductive structures separately. This export
is the next integration step and is NOT implemented by this inference worker.
It reveals whether the segmenter undercounts our model or merges its organs.
Do not compare visible photo masks against total 3D organ count, or call a
predicted render mask synthetic ground truth.

Then compare projected foliage coverage by height, gaps, visible instance sizes,
orientations and flower-cluster occupancy. These are projected appearance
metrics, not true volumetric density or validated plant physics. For aligned
specimen reconstructions, also compare regional residuals; for different plants,
compare distributions rather than forcing one-to-one organ matches. Keep a
separate reference view/plant unused for fitting when one becomes available.

## Remote execution contract

One isolated RunPod GPU, one image at a time, one model process at a time.
Target a48GB A40/A6000-class worker with Python3.12 and compatible CUDA/PyTorch.
Set a hard job timeout including setup, a billing watchdog and artifact retrieval
before allocating. A stopped pod belonging to another experiment is not reused
without checking its purpose. Do not install anything into an active project pod.

Read-only RunPod check at preparation: no running GPU; stopped prior experiment
present; balance approximately$27.97. Quotes observed:A40$0.35/h,A6000$0.33/h,
4090$0.34/h. Availability/storage can change. Proposed first run budget:$1 maximum,
at most one hour, including setup, with stop verification. No billing action
has been taken and this proposal does not itself authorize a new charge.

`inputs.json` records source paths/checksums and native comparison resolution.
Stage those three images under the listed relative files on the worker.
Run each backend separately, with a supervisor enforcing the remaining deadline:

```sh
python worker.py --backend sam2 --manifest inputs.json --out results/sam2
python worker.py --backend depth --manifest inputs.json --out results/depth
# Only if existing SAM3 checkpoint access and compatible environment are verified:
python worker.py --backend sam3 --manifest inputs.json --out results/sam3
```

Code revisions checked on2026-09-13:

- SAM2:`2b90b9f5ceec907a1c18123530e92e794ad901a4`
- SAM3:`660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7`
- DA3:`3d835ec1a5802d64a8b8b15f817a1ab54809bfe4`

Install these pinned official repositories on the remote worker only. Also save
checkpoint hashes and dependency versions before treating the run as reproducible.
Remote dependency installation and inference are NOT yet tested. Local checks
cover parsing and refusal on macOS only.

## Primary sources

- SAM3 concepts, API and gated weights: https://github.com/facebookresearch/sam3
- SAM2 automatic proposals: https://github.com/facebookresearch/sam2
- DA3 model/API/license table: https://github.com/ByteDance-Seed/Depth-Anything-3
  Small/Base weights are Apache2.0; several larger models are noncommercial.
- Photo: https://doi.org/10.1371/journal.pone.0252985.g001 (CC BY).

This experiment evaluates botanical image reconstruction, not a cultivation or
pruning recipe. It cannot establish stiffness, bruise risk or safe contact force.
