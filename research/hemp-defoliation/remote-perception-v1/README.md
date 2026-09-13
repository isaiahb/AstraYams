# Remote perception pilot — completed 2026-09-13

User constraint: no model inference/training on the Mac. Do not install torch,
download weights or run a parameter/render sweep locally. `worker.py` exits
before importing ML packages unless it runs on Linux with RUNPOD_POD_ID, and
also requires CUDA with no CPU/MPS fallback. Mac work is lightweight editing,
file transfer and inspection of finished results only.

## Proposed first experiment

Use one reference photograph and the existing matched-camera broad/narrow
model renders. No private partner photos are in the initial bundle. Run the
same preprocessing on both domains. A public source photo is only 381x444;
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
IDs; include petioles, stems and reproductive structures separately. This export is implemented separately in `audit_synthetic.py` with remote
Open3D ray casting of pixel-center rays through the same exported mesh.
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
Executed on a 48 GB A40 with Python 3.11 and PyTorch 2.8 / CUDA 12.8.
Set a hard job timeout including setup, a billing watchdog and artifact retrieval
before allocating. A stopped pod belonging to another experiment is not reused
without checking its purpose. Do not install anything into an active project pod.

Read-only RunPod check at preparation: no running GPU; stopped prior experiment
present; balance approximately$27.97. Quotes observed:A40$0.35/h,A6000$0.33/h,
4090$0.34/h. Availability/storage can change. Proposed first run budget:$1 maximum,
at most one hour, including setup, with stop verification. User subsequently authorized this run and reasonable overruns without repeated
confirmation. An isolated A40 worker was started at $0.49/hour. A90-minute
shutdown watchdog and 60-minute job timeout were used. Artifacts were retrieved
and checksummed before the watchdog verified the worker stopped.

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
Remote dependency installation and both SAM2/DA3 inference are tested.
`run_remote.sh` captures the working pinned installation, including an isolated-pod
blinker dependency repair. Checkpoint hashes and dependency versions are in
`evidence/`. SAM3 was not run in this first pilot. Correction from the next pass: an
existing Hugging Face cached credential was overlooked; official checkpoint
access is available. See `../sam3-comparison-v1/README.md` for the actual SAM3 run.

## Primary sources

- SAM3 concepts, API and gated weights: https://github.com/facebookresearch/sam3
- SAM2 automatic proposals: https://github.com/facebookresearch/sam2
- DA3 model/API/license table: https://github.com/ByteDance-Seed/Depth-Anything-3
  Small/Base weights are Apache2.0; several larger models are noncommercial.
- Photo: https://doi.org/10.1371/journal.pone.0252985.g001 (CC BY).

This experiment evaluates botanical image reconstruction, not a cultivation or
pruning recipe. It cannot establish stiffness, bruise risk or safe contact force.

## Actual results

[Open the review](http://127.0.0.1:8793/runs/hemp-perception-pilot-v1/index.html).
Full raw masks, arrays and exact visible scene IDs remain in that run folder.
Compact evidence is committed here. `evidence/execution.json` records verified
shutdown and worker rate; it is not an exact billing invoice.

| Input | Default proposals | Denser proposals | Heuristic foliage candidates |
| --- | ---: | ---: | ---: |
| Real photo | 3 | 121 | 111 |
| Broad render | 30 | 146 | 139 |
| Narrow render | 3 | 102 | 99 |

These are NOT verified leaf counts. Default SAM2 took about 5 seconds/image;
the denser diagnostic took about 17 seconds/image. The latter uses a denser
point grid and lower thresholds, and also segments background. A post-hoc
green/area filter provides review candidates only, not semantic labels.

Against exact synthetic visible organ masks (at least 16 pixels, best proposal
IoU at least 0.5), the denser pass covers 62/134 broad whole leaves and 34/139
narrow whole leaves; only 18/441 broad leaflets and 19/402 narrow leaflets.
This is best-overlap coverage, not one-to-one precision/AP. It demonstrates
strong organ-granularity and shape-dependent failure at this resolution.

DA3-Small took about 0.2–1 second/image. Predicted depth rank correlation with
known synthetic depth was 0.091 (broad) and 0.012 (narrow), on visible geometry.
No real depth ground truth exists. The previews smooth thin structures and
cannot justify contact geometry or metric clearance.

## Next bounded experiment

First freeze a small human-reviewed set of clear versus overlapping organs.
Use existing higher-resolution source images if available, or explicitly retain
unresolvable regions in this source. Compare prompted masks against that sample
before using any mask count to change model density. Do not run automatic model
fitting against these unverified predictions. All inference remains remote.

`build_review.py` only packages HTML locally. `worker.py`, `audit_synthetic.py`
and `summarize.py` refuse non-RunPod execution before loading heavy libraries.
