# Residual SAM3 segmentation experiment

This experiment compares two second-pass strategies under an exactly matched
budget of 87 SAM3 crop inferences, using the frozen 381×444 original from the
prior grid search and its grid-11 leaf masks accepted at confidence 0.5.

The source is labeled **preharvest, pot not visible, and not fully suitable as
target evidence**. Detached-shoot images are rejected and are not used. The
reported foreground is a color proxy, not annotated ground truth.

- `black-fill`: black out initially accepted pixels, then rerun the same 87
  eligible grid-11 crop boxes.
- `original-context-residual`: rank crops by uncovered proxy tissue, but infer
  on unchanged original pixels with the same 48×56 crop size.

Raw crop-local masks, scores, boxes, edge flags, unions, logs and checksums are
preserved under `runs/hemp-residual-segmentation-v1/results`. The static report
separates proxy coverage, definite-background leakage, cross-crop duplication,
edge-truncated proposals, and qualitative boundary review. None is a ground-
truth accuracy or leaf-count claim.

## Result

The unchanged repeat exactly reproduced the frozen 0.5 baseline union: 30.47%
foreground-proxy coverage, proxy IoU 0.3030, and 79 definite-background pixels.
Black-fill reached 30.77% (+0.30 percentage points) and added one background
pixel. Original-context residual crops reached 31.94% (+1.47 points) and added
three background pixels. The latter recovered 622 residual proxy pixels versus
128 for black-fill, but produced 470 cross-crop duplicate pairs and 131 edge-
truncated accepted proposals. Equal call count did not mean equal compute.

Visual review of the fixed calibration regions shows that many original-context
additions are partial blades or small fragments; crop boundaries and overlap
remain visible in the individual-proposal view. Black-fill yielded almost no
accepted second-pass proposals at 0.5 and did not restore the missed upper-left
fan. The small proxy-coverage gain therefore does not establish better whole-
organ recovery.

The bounded full-image visual-region prompt completed, but each broad seed box
mostly selected its local region at 0.5; lower thresholds often leaked heavily
into background. The first point-refinement attempt omitted
`enable_inst_interactivity=True`, and the next called the low-level predictor
instead of the official processor-state API. These were implementation errors,
not checkpoint limitations. The original worker could not restart, so one
replacement worker ran the corrected six-prompt test and was verified stopped.
Each highest predicted-IoU candidate isolated a small local blade region with
foreground-proxy precision 0.926–1.000. These are post-hoc human prompts and
model confidence, not measured boundary accuracy; the result supports
interactive review, not autonomous organ discovery.

The residual scheduler ranks static uncovered-proxy mass with a small center
spacing, so it repeatedly samples dense regions. Its 470 duplicate pairs are a
property of this one-pass selector, not all context-preserving residual methods.

The newly identified living, upright, potted reference was not tested in this
run. It needs a separately checked foreground estimator and comparison protocol;
the green-on-dark proxy from this provisional reference cannot be reused.
