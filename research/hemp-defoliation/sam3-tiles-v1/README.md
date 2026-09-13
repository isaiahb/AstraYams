# Overlapping SAM3 crops — 2026-09-13

Hypothesis: small organs occupy more of the image encoder's input after cropping,
which may help detection. Cropping does not reveal occluded parts or recover
missing source detail, and can remove context or split one leaf into fragments.

Frozen test: same reference, broad render and narrow render as prior comparison;
full image, 2x2 and 3x3 grids; 30% overlap; official SAM3 image checkpoint and
`leaf` prompt. Confidence 0.5 primary; 0.1 explicitly diagnostic. Both thresholds
are filtered from the same inference, avoiding a confound from separate runs.

Map binary masks back into original-image pixel coordinates. Keep raw masks,
scores, tile coordinates and a two-pixel internal-crop-edge flag. Suppress
near-duplicate masks at IoU >= 0.5, preferring complete masks then confidence.
Do not union overlapping masks: that could fuse neighboring leaves. Report both
all retained masks and a conservative subset excluding crop-edge fragments.
The latter can miss genuine long leaves; full-frame context remains available.

Compare synthetic masks with exact projected whole-leaf IDs, >=16 visible pixels.
Use maximum-cardinality one-to-one matching at IoU >=0.5, then precision and
recall. Synthetic matching is not real-photo validation or a count of real leaves.
Whole compound leaves and leaflets are different targets; this experiment uses
whole leaves only. Inspect overlays alongside scores.

Run only on RunPod Linux with CUDA. Mac: source edits, metadata, SSH transfer and
viewing retrieved artifacts only. Deadline 30 minutes; verified stop after
retrieval. Previous worker could not resume because its host had no free GPU;
use one replacement worker, leaving the previous pod stopped.

## Observed outcome

Actual review: /runs/hemp-sam3-tiles-v1/index.html. Same 0.5 confidence threshold:
reference full / 2x2 / 3x3 complete proposals = 0 / 15 / 51. Visual inspection
shows recovered leaf surfaces but no real-photo ground-truth accuracy claim.
Broad synthetic whole-leaf matches rise 27 -> 42 -> 58 (of 134 visible leaves),
while precision falls from 93% to 87% for full versus 3x3. Narrow geometry has
an important granularity shift: full image matches 10/139 whole leaves and
0/402 leaflets; 3x3 matches 3/139 whole leaves and 81/402 leaflets (88% leaflet
precision, 20% leaflet recall). Do not present 92 proposals as 92 whole leaves.
Supplemental leaflet audit was added after observing the shift, explicitly
separate from the frozen whole-leaf metric; no threshold or labels changed.

0.1 yields many more candidates with reduced precision. It remains diagnostic.
Tiling is a useful component, not validated complete plant segmentation. Next:
keep full-frame context and crop proposals at separate anatomical levels, review
small real-photo annotation samples, and assess fusion without double counting
leaflets inside compound leaves. No automatic model-fitting acceptance yet.

## Execution and verification

Ran on replacement RunPod A40 dvayjyonatj1n6. All artifacts retrieved and archive
hash verified; worker verified EXITED. No ML or image processing on the Mac.
SSH did not inherit RUNPOD_POD_ID initially; guard refused imports. The known pod
ID was supplied only on the authenticated remote command after host/GPU checks.

The first implementation spent too long comparing full-sized binary masks.
Its process was interrupted after masks had been cached. Bounding-box IoU and
per-instance pixel histograms accelerated exact postprocessing; cached masks
were reused, not regenerated. Completed first-pass metrics were checked against
the accelerated pass and all agree (see acceleration-check.json). Timings in
final report may include cached masks and are not inference latency claims.
Source syntax, all 18 result rows, required image assets, and browser rendering
were checked. The reference and narrow comparison sheets were visually reviewed.
