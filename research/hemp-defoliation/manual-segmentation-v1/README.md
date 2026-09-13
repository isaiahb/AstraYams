# Astra manual botanical annotation — first pass

[Open the side-by-side review](http://127.0.0.1:8793/runs/hemp-manual-segmentation-v1/index.html).

The user requested a direct Astra annotation attempt, using a 5 × 5 grid and
stitching the result. This pass uses the same 381 × 444 historical photograph
as the SAM3 experiments so differences are inspectable. No new inference,
training, raster processing or model execution ran on the Mac. The browser
displayed existing source pixels in enlarged SVG viewports; annotation and
export work consists of hand-entered vectors and small JSON/SVG files.

## What was actually done

- Inspected all five rows, each divided into five column cells, with 10-pixel
  vertical context around row boundaries. Eight cells contain no visible plant;
  empty/background regions were inspected, not filled with predictions.
- Entered explicit vertex coordinates by visual interpretation of the source,
  without copying SAM3 masks or calling an image-generation model.
- Produced **84 candidate leaflet contours, 6 exposed stem spans, 2 support
  contours and 23 unresolved review regions**. These are annotation records,
  not a verified count of the plant's organs.
- Inspected every row with overlays and the stitched whole-image view. Corrected
  a displaced upper-right review region, an overextended narrow blade and a
  low hanging tip. Other boundary errors remain possible.
- Preserved a global ID/coordinate system. Tile SVGs clip these shared vectors
  rather than inventing separate instances at tile boundaries.
- Checked coordinates, positive polygon area and proper edge crossings. All
  115 records passed those geometry checks; that does not validate their
  correspondence to the photograph.

## How to judge the result

The outlines often identify exposed blades coherently, including the clear
upper-left fan missed by the residual model pass. They are approximate:
some edges overshoot/undershoot the tissue, serrations are simplified, narrow
petioles remain missing and the dense interior is substantially unresolved.
This is not complete segmentation, independent ground truth, or evidence that
Astra's hand-entered boundaries outperform SAM3's pixel masks. Prior model
outputs were already seen in this task, so this is not a blind comparison.

Pink dashed regions are **ignore/review areas**, not flower/leaf masks. They
can contain multiple organs and background gaps. Unannotated pixels remain
unknown; never implicitly convert them to background during training. Do not
infer invisible attachments or parent compound-leaf identities: those fields
remain null. The support labels are non-plant exclusions. Every record remains
`trainable: false` until a separate acceptance/review step.

## Files

- `annotations.json`: full editable labels, uncertainty and source provenance.
- `trace_labels.py`: reproducible hand-entered coordinate source.
- `coco-draft.json`: COCO-style polygon draft, with uncertainty/ignore extensions.
  A consumer must honor the review flags; do not treat this as ready training data.
- `grid-manifest.json`: 25 reviewed cells and shared global IDs.
- `validation.json`: lightweight vector checks and counts.
- `export_labels.py`: vector exports; no rasterization or local image processing.
- `build_review.py`: static inspection page, original/overlay and instance views.
- `runs/hemp-manual-segmentation-v1/{labels,overlay}.svg` and `tiles/`: stitched
  vectors and 25 clipped tile views; source pixels stay separate from labels.

Source: Anderson et al., PLOS ONE Fig. 1,
https://doi.org/10.1371/journal.pone.0252985.g001, CC BY 4.0, derived crop.
The caption establishes preharvest context; this crop does not show the pot.
The newer APPF native image is a separate specimen and has not been manually
annotated in this pass.
