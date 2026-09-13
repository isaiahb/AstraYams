# Segmentation alternatives v1 — SAM3 visual-region exemplars

This is a bounded, runnable comparison of the existing **SAM3 checkpoint** in a
different inference mode. It is not an independent model benchmark. Meta
documents that SAM3 accepts visual prompts and an exemplar box can identify
matching objects; its official image processor exposes this as
`add_geometric_prompt(box=..., label=True, state=...)`.

The experiment runs three independent full-image visual-**region**-exemplar passes. The
boxes are exactly the three `crop_xywh` rectangles in
`../organ-review-v1/review.json`; results are not unioned. That review file was
chosen post-hoc and supplies provisional rectangles and six points, so its
region pixel totals and anchor hits are diagnostic only. They cannot establish
leaflet, compound-leaf, stem, or boundary accuracy.

Each rectangle contains multiple visible blades and can contain stem or
background. It is therefore a reproducible **region-exemplar** condition, not
a test of a tight single-leaf visual exemplar. A poor result must not be read
as evidence against SAM3 visual prompting; a later interactive experiment must
use independently reviewed, tight visible-blade prompts and explicit uncertain
boundary bands.

The score report uses the frozen color foreground proxy, ROI and thresholds
(0.5, 0.25, 0.1) from `../sam3-grid-search-v1/run_search.py`: coverage,
proxy precision, proxy IoU, core coverage, and definite-background leakage.
Those are common diagnostic quantities, not a ground-truth score. More masks
or greater proxy coverage is not evidence of correct organ identity.

## Remote execution

This program deliberately exits before importing ML or image libraries unless
it runs on the shared RunPod Linux worker. It needs no new package beyond the
already installed official `sam3`, PyTorch, NumPy and Pillow:

```bash
RUNPOD_POD_ID="$RUNPOD_POD_ID" \
ALT_INPUT=/workspace/sam3-comparison/input.png \
ALT_OUT=/workspace/sam3-comparison/visual-exemplar \
ALT_REVIEW=/workspace/AstraFactory/research/hemp-defoliation/organ-review-v1/review.json \
BASELINE_SCORES=/workspace/sam3-comparison/residual-guided/leaf-11/scores.npz \
python /workspace/AstraFactory/research/hemp-defoliation/segmentation-alternatives-v1/run_visual_exemplar.py
```

`BASELINE_SCORES` is optional. When present and shape-compatible it gets the
same global proxy and review diagnostics so the visual method can be compared
to the residual/tiled result without changing criteria. It is intentionally
not a claim that either method is accurate.

## Targeted point-refinement add-on

`run_point_refinement.py` is a distinct, bounded labeling technique. It embeds
the full image once, then for each of the six existing review anchors supplies
that anchor as a positive click and the other anchor in its same review region
as a negative click. It saves all three SAM3 ambiguous-click masks, predicted
quality values, low-resolution logits and visualizations. This costs one image
encode plus six prompt calls and uses no additional dependency. It explicitly
passes `enable_inst_interactivity=True` to the official SAM3 image builder;
that option defaults to false and must be enabled for its SAM1-style image
predictor. It uses the official image route: `Sam3Processor.set_image()` then
`model.predict_inst(state, point_coords=..., point_labels=...)`, which supplies
the populated SAM2 backbone features required by the interactive predictor:

```bash
RUNPOD_POD_ID="$RUNPOD_POD_ID" \
ALT_INPUT=/workspace/sam3-comparison/input.png \
POINT_OUT=/workspace/sam3-comparison/point-refinement \
ALT_REVIEW=/workspace/AstraFactory/research/hemp-defoliation/organ-review-v1/review.json \
python /workspace/AstraFactory/research/hemp-defoliation/segmentation-alternatives-v1/run_point_refinement.py
```

It is oracle-assisted: those points were manually selected after seeing model
failures. It therefore tests whether click-based refinement can separate a
visible blade from a neighboring reviewed surface, not whether a system can
find leaves automatically. Predicted IoU is model confidence only. No raw
candidate is selected by the foreground proxy, and the proxy/ROI numbers do
not validate its boundary or organ identity.

After the returned output directories are placed under `evidence/`, build the
inspectable static report without running inference or processing raster data:

```bash
python3 research/hemp-defoliation/segmentation-alternatives-v1/build_review.py
```

It shows every region-exemplar threshold image and every raw point multimask
candidate. It keeps executed results separate from untested research candidates.

## Research basis, candidate methods, and rank

- Meta’s [SAM 3 research page](https://ai.meta.com/research/sam3/) describes
  visual clicks and exemplar boxes alongside text prompts. The [official image
  processor](https://github.com/facebookresearch/sam3/blob/main/sam3/model/sam3_image_processor.py)
  documents the normalized `cx,cy,w,h` box interface used here.
- The [CVPPP Leaf Segmentation Challenge](https://www.plant-phenotyping.org/CVPPP2017-challenge)
  makes clear why individual-leaf grouping is a separate task from plant
  foreground segmentation. Its limited controlled imagery is not valid
  ground truth for this different, occluded photograph.
Candidate methods are ranked by task fit and the evidence they could add:

0. **SAM 3.1, scoped correctly.** Meta released SAM 3.1 on March 27, 2026:
   [the official release notes](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md)
   say it provides new checkpoints and Object Multiplex, with measured gains
   and a large speedup for *multi-object video tracking*. The gated
   [checkpoint repository](https://huggingface.co/facebook/sam3.1) is live;
   its published config is `Sam3VideoModel` and it provides
   `sam3.1_multiplex.pt`. The release supplies a video-predictor notebook and
   video benchmark tables, while the current image-predictor example remains
   documented generically as SAM3. The release material does **not** provide
   a SAM3.1 still-image result or image-predictor checkpoint/usage claim.
   Therefore it is the first candidate for a separately versioned, temporal
   multi-view/video experiment when frames exist, after gated-checkpoint
   access and a fresh environment install. It is not evidence that replacing
   the frozen SAM3 checkpoint improves this single-still-image A/B; that
   baseline remains unchanged.
1. **SAM3 interactive refinement with tight, independently reviewed visible
   blade prompts.** SAM3 already supplies clicks/visual prompts, and its source
   includes the interactive predictor. This is the next method to test after a
   reviewer supplies a defensible tight blade boundary/uncertain band: positive
   points on one blade and negative points on adjacent blade/stem test
   separation, without claiming automatic instance discovery. It costs no
   model download and tests the actual overlap failure directly. This run is a
   cheaper region-exemplar precursor, not that tight test.
2. **SAM 2 interactive and automatic-mask baseline.** The [official SAM 2
   page](https://ai.meta.com/research/sam2/) supports click, box and mask
   prompts plus corrections; the [official repository](https://github.com/facebookresearch/sam2)
   supplies `SAM2AutomaticMaskGenerator` and says its models/code are Apache
   2.0. It is a genuinely separate foundation-model baseline, worth a bounded
   GPU test with the same proxy/review diagnostics after downloading its
   checkpoint. Automatic masks still need overlap stitching and do not provide
   leaf hierarchy.
3. **HQ-SAM / HQ-SAM 2 with point or box prompts.** The
   [official project](https://github.com/SysCV/SAM-HQ) adds an HQ token for
   fine-structure boundaries while retaining promptability. It is promising
   for serrated/narrow visible blade edges, but not for deciding which
   overlapping blade is a parent/child. It requires a separate SAM/HQ
   checkpoint and environment; confirm the chosen checkpoint's license at
   download time before use. Test it only on independently reviewed blades,
   reporting an uncertain-edge-aware boundary diagnostic rather than proxy
   coverage alone.
4. **ZeroPlantSeg hierarchical grouping.**
   [ZeroPlantSeg](https://github.com/JunhaoXing/ZeroPlantSeg) is the most
   directly relevant hierarchy prior art: leaf candidates, keypoints and
   grouping rather than a foreground union. Its official code requires extra
   checkpoints and carries GPL-3.0; its published workflow is based on
   top-view datasets. Run only as an isolated research comparison after a
   dependency/license review, and do not infer its expected performance on
   this side-view photograph.
5. **Plant-specific trained instance networks (ReLeaf/GMT/Mask R-CNN family).**
   The [ReLeaf official repository](https://github.com/cropandweed/releaf)
   provides a multi-species leaf framework/data but is CC BY-NC-SA 4.0;
   [GMT](https://openaccess.thecvf.com/content/WACV2025/papers/Chen_GMT_Guided_Mask_Transformer_for_Leaf_Instance_Segmentation_WACV_2025_paper.pdf)
   trains on controlled leaf benchmarks. These are useful training-data and
   evaluation prior art, not zero-shot drop-ins for this image. A domain-tuned
   model becomes a credible candidate only with correctly licensed,
   target-like labeled images and a held-out protocol.

The current official SAM3 region-exemplar path is the smallest testable
alternative: it preserves full-image context and tests whether a visible
leaf/fan region is more coherent than text on overlapping tiles. It may still
merge leaflets, split a compound leaf, or transfer post-hoc region bias; review
images and per-seed proposal files retain those failures for inspection.
