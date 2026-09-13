# Residual segmentation review — frozen before results

Date: 2026-09-13. User authorized three parallel agents: residual A/B,
living-plant dataset discovery, and alternative segmentation methods.

All inference, raster processing and model preparation run on one isolated
RunPod worker managed by the residual-experiment agent. Local work is source
editing, metadata review, transfer and inspection of returned artifacts.

## Questions and controls

1. Does blacking out the first-pass predictions recover additional visible
   plant tissue, compared with an unchanged repeat?
2. Do residual-guided crops from the original pixels do better under the same
   number of model calls? Retain context around the residual.
3. Can a different prompting/segmentation method recover meaningful organ
   boundaries, rather than just foreground area?
4. Does a suitable living, upright, potted reference expose different failures?

The frozen baseline masks are high-score model predictions, not manually
accepted labels. Initial acceptance errors remain possible in both arms.
The original image is a provisional, preharvest reference with no pot visible;
it is retained for continuity, not promoted to an ideal facility reference.
Detached shoots are excluded from target-reference selection.

## Quantitative reporting

- Use the same input, first-pass mask, thresholds and foreground proxy for
  residual conditions. Report source hash and exact crop boxes.
- Report both second-pass additions and final union with the baseline.
- Report proxy coverage, proxy IoU and definite-background leakage together.
- Include primary confidence 0.5 and clearly labeled lower-confidence diagnostics.
- Report processed crops, wall time and model/prompt differences. Equal call
  count is not an assertion of equal information or total compute.
- Counts of masks, contour vertices or perimeter are not quality scores.
- New references need their own explicitly checked foreground estimator; a
  green-on-black heuristic may misclassify pots, supports and pale/dark tissue.

## Visual review

Reuse the three calibration regions in organ-review-v1/review.json, selected
before this experiment: upper-left fan, central overlap, lower-right fan.
For each, inspect original pixels beside baseline and each condition. Record:

- missed visible blades or parts of blades;
- visible background holes incorrectly filled;
- separate blades merged, or one blade fragmented;
- outlines following artificial blackout or crop boundaries;
- stem versus leaflet confusion and unresolved parent-leaf identity.

These are assistant diagnostic observations, not independent annotations or
held-out ground truth. Point hits are not boundary accuracy. Hidden tissue is
unknown. Do not report organ-count accuracy, biological validation or automatic
model fitting from these results.

## Completion

Retrieve and checksum actual outputs, visually inspect them, preserve rejected
conditions, publish a static research comparison, and verify the GPU stopped.
Choose subsequent work from the dominant observed error, not maximum coverage.
