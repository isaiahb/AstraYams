# Organ identity review v1

A lightweight, post-hoc visual calibration set over the frozen 381 x 444 source.
Three regions, six candidate leaflet-surface anchors, two excluded dense regions.
Reference pixels, provisional points/ROIs and existing SAM3 tiled masks are shown
at the same enlarged scale. No new raster generation, ML, GPU or fitting pass.

The assistant inspected the enlarged reference and corrected two of its own
initial anchors: [174,241] lay on a stem; [267,381] lay in a gap/edge region.
The initial proposals remain in rejected-uninspected-anchors.json. Candidate
junction locations were refined. The central region is not assigned one common
leaf parent because it visibly contains a stem and overlapping separate fans.
All six final anchors were visually inspected; their boundaries remain untraced.
These are not expert-reviewed labels, binary masks or independent ground truth.

Do not score IoU against the rectangular review regions. A point hit does not
validate the remainder of a mask. Do not add leaflet counts to compound-leaf
counts. Parent IDs remain null pending a defensible visible grouping. Regions
were chosen after the model results, so this is not a held-out test set.

Existing connection, side and top views were inspected. Their thin depth and
unseen rear geometry remain hypotheses, not supported multi-view reconstruction.
No geometry or physical properties were changed in this pass. Do not use the
old approximate central downward leaf landmark as validated evidence; its
projected extension overlaps the stem in this review.

Next bounded step: trace the visible blade boundary in the upper-left region,
mark an explicit uncertain edge band, and test crop/full-frame mask correspondence
against it. Any raster mask scoring or inference runs remotely; keep the source
annotation inspectable and require independent review before accuracy claims.

Run `python3 research/hemp-defoliation/organ-review-v1/build_review.py` for the
static review at /runs/hemp-organ-review-v1/index.html. The script only writes
SVG/HTML and hashes a small input file; it does not process image pixels.
Reference provenance/license and coordinate conventions are in review.json.
