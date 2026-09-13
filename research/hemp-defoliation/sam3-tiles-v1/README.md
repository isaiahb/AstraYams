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
