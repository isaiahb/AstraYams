# Astra points → SAM3 boundaries

Bounded calibration experiment. Astra selects visible tissue points and reviews
returned masks, then adds positive/negative correction points. SAM3 generates the
pixel masks. This is assisted labeling, not a blind autonomous benchmark.

The same 381 × 444 source is tested as a full image at 1× and 2×, and an 80 × 80
crop at 1×, 2× and 4×. Upscaling is bicubic interpolation. No super-resolution or
generated detail is used. All raster operations and inference run on RunPod.
The Mac only transfers files, edits JSON/code and displays existing images.

The frozen plan is `plan.json`; follow-up plans and review decisions preserve
actual corrections. All three ambiguous mask candidates are retained, including
whole-canopy failures. Model-predicted IoU is confidence, not measured IoU.
No area/count-maximizing selection is used. Geometry from the earlier hand-traced
pass is not ground truth. Unannotated and occluded surfaces remain unknown.

Source: https://doi.org/10.1371/journal.pone.0252985.g001 (CC BY 4.0, derived crop).
Input SHA256: 2f338a5ce241e5844cb3bfaa517b611e9b1fc0b87270755a1dc4d9971c53fa7a.
SAM3 checkpoint SHA256: 9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e.
Official implementation: https://github.com/facebookresearch/sam3.

Use `worker.py PLAN.json` only on the RunPod worker with the official checkpoint
at `/workspace/sam3-comparison/sam3.pt`. Transfer `point-loop/round-*` into
`runs/hemp-point-loop-v1/`, then run `python3 build_review.py` locally to assemble
the static review. Generated datasets and raw masks stay out of git.

## Observed result

The initial full-image exposed target merged multiple blades. Cropping alone
already isolated a plausible single leaflet; an added negative point preserved
that separation. Enlarging the full image did not resolve fan merging. The
central candidate 0 was plausible before correction; the stem-negative point
also localized candidate 2. The dense initial anchor was misplaced. Replacing
it and adding two negatives recovered a plausible visible diagonal blade, not
the ambiguous cluster initially clicked.

Selected candidate 0 from each corrected native crop after visual inspection.
The native-versus-4× corrected-mask agreement IoUs are 0.900, 0.917 and 0.961
(exposed, overlap, dense). These compare predictions with predictions, **not
predictions with ground truth**. Only 9, 7 and 2 source pixels differ. Visual
review did not establish a boundary advantage for 4×. Native crops are retained.

There are seven final points across three targets, including one relocated
positive point; eight point placement/correction actions were made in total.
Crop selection and visual review also take effort. This is not a matched-effort
comparison against the previous 84 manually traced outlines. No complete plant,
petiole connectivity, hidden geometry, or independently validated labels were
produced. All other source pixels are unknown. Exports are provisional and
marked not trainable pending review.

Actual worker loop times were 8.33 s (15 prompts) and 3.23 s (9 prompts), including
loop-side image exports but excluding model initialization, provisioning and
transfers. These are not end-to-end labeling times. Source revision:
660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7. Checkpoint hash stayed frozen.
141 transferred artifact hashes were verified. The GPU was stopped after export.
