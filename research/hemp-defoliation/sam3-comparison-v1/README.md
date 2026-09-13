# Segmentation model selection — 2026-09-13

## Decision

Use the official full SAM3 image model as the next primary candidate. SAM2.1 is
retained as a baseline only, not a limitation on model quality. No general claim
that SAM3 is the best for every leaf shape or imaging domain is warranted.

Correction: the previous pilot checked environment variables but overlooked the
existing Hugging Face token cache. An authenticated HEAD request now confirms
access to the official facebook/sam3 checkpoint. No new terms accepted; no mirror
used. Only an expiring checkpoint download URL is sent to the isolated worker;
the Hugging Face account token stays local and never appears in logs.

## Primary-source comparison

- **SAM3** supports text and exemplar concept prompts and interactive visual
  prompts. It is the strongest immediately available general candidate we found
  for this sparse-label image annotation task. Official code:
  https://github.com/facebookresearch/sam3
- **SAM3.1** improves multi-object video tracking/multiplexing. The current
  official still-image builder loads SAM3 weights; 3.1 is not a demonstrated
  still-image leaf-accuracy upgrade. For future multi-view/video work, evaluate
  it separately: https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md
- **ReLeaf** evaluates leaf-specialized YOLO26/Detectron2 variants. Its selected
  model achieves 83.9% mean AP50–95 across corresponding test datasets but 40.2%
  on a new cross-species benchmark. These are not comparisons with SAM3 and do
  not establish superiority on our low-resolution side-view canopy. Specialist
  training is a candidate if reviewed annotations justify it. Framework license
  is CC BY-NC-SA 4.0, so it is not a drop-in commercial component.
  https://arxiv.org/abs/2605.03784
  https://github.com/cropandweed/releaf
- A September 7 preprint combines **SAM3 + semantic NeRF** across multiple views,
  reporting promising plant-part semantic segmentation. It merges instances
  within a class; its mIoU is not a count of individual leaves. Our single
  low-resolution photo does not satisfy its multi-view setup.
  https://arxiv.org/abs/2609.07724

## Frozen comparison

Same three input images, checksums, 381×444 native comparison resolution and
synthetic visible-ID buffers as the first pilot. Same four predeclared prompts:
leaf, leaflet, plant stem, flower cluster. Confidence 0.5, bfloat16 autocast. Record all
masks and failures, without green/size filtering of SAM3 output. Keep compound
leaf and leaflet evaluations separate. Use exact synthetic masks for known
geometry; real-photo masks remain predictions awaiting review. Prompt selection,
precision and task interface differ from SAM2 automatic proposals; this is a
pipeline usefulness comparison, not an architecture-only ablation.

No inference or weight download on the Mac. RunPod A40 worker has a 90-minute
billing deadline and bounded commands. Retrieve results before verified stop.

## Diagnostic follow-up

The baseline returned zero reference masks for leaf/leaflet at confidence 0.5.
Keep it intact. `prompt_probe.py` tests five alternate noun phrases on all three
images, a separately labeled 0.1-confidence diagnostic, a manually selected
compound-leaf example box, and three native-pixel reference crops. These are
exploratory interventions, not a new acceptance threshold or held-out result.

Execution notes: the initial no-autocast attempt failed on an internal bfloat16
activation / float32 layer mismatch. Using bfloat16 autocast followed the model's
numerical path; saved confidence tensors are explicitly converted to float32
before NumPy serialization. Earlier failed attempts emitted no scored masks.

## Outcome

The official SAM3 image model actually ran on RunPod. Four baseline prompts per
image took about 0.7–1.1 seconds including postprocessing/saving, excluding model
load; timing is not a standardized throughput benchmark. Plain leaf/leaflet
prompts at 0.5 returned zero masks for the reference photo. Leaf masks numbered
29 for the broad render and 13 for the narrow render. Against unchanged synthetic
coverage criteria, leaf matches were 27/134 and 10/139; this does not outperform
the denser SAM2 proposal pipeline's 62/134 and 34/139 coverage.

Exploration found 119 reference candidates at confidence 0.1, but visual review
shows masks bridging gaps and swallowing large canopy regions. Those candidates
are not a validated improvement in real organ segmentation. On synthetic whole
leaves, the low-confidence diagnostic covers 66/134 broad and 35/139 narrow,
slightly above SAM2 recall coverage but without verified precision. Refiltering
that diagnostic's scores at 0.5 yields 15 narrow proposals versus 13 in the
separate baseline run; do not claim exact deterministic repeatability.

Example-box-only returned one reference mask; leaf plus example returned two.
Upper/middle/lower native crops returned 1/0/1. More specific botanical phrases
also returned zero reference masks at 0.5. All outcomes are preserved.

**Decision:** SAM3 is now available and integrated as the current primary model
candidate, but this test does not justify declaring it the best organ segmenter
for these images. No automatic plant geometry update is accepted from these
predictions. Next useful work is a small fixed set of reviewed visible boundaries
and genuinely higher-resolution reference material, then prompt/threshold
calibration evaluated separately from final test images. More model names alone
will not establish accuracy. No local inference is permitted.

[Actual interactive comparison](http://127.0.0.1:8793/runs/hemp-sam3-comparison-v1/index.html).
