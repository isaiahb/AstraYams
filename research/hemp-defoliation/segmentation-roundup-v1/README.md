# Segmentation experiment coordination

Three user-requested agents worked in parallel:

- Sol: matched residual-segmentation comparison on the isolated RunPod worker.
- Terra: living upright potted-plant image sources and resolution/provenance audit.
- Terra: segmentation prior art and bounded alternative prompting techniques.

The root agent froze review criteria before outputs, reviewed worker scoring
for consistent ROI denominators, checked source images and their limitations,
and inspected returned comparison artifacts. See REVIEW-PROTOCOL.md.

## Artifacts

- [Residual comparison](../../../runs/hemp-residual-segmentation-v1/index.html)
- [Reference photographs](../living-reference-search-v2/index.html)
- [Alternative prompting methods](../segmentation-alternatives-v1/evidence/index.html)

## Scope of evidence

The residual A/B uses the frozen historical 381 × 444 photograph. This keeps
the comparison interpretable; it does not establish performance on the newly
recovered APPF native image. That source requires a separate comparison with
an appropriate foreground annotation, including yellow/brown and dark tissue
while excluding pot, cage and support hardware.

The visual-region and point-refinement conditions use the same SAM3 checkpoint.
They are actual alternative techniques, not an independent-model benchmark.
SAM3.1, HQ-SAM and plant-specific systems in the research shortlist are not
silently counted as tested methods. Post-hoc reviewed points supply information
to the interactive method; its result is not autonomous whole-plant labeling.

Coverage is a color-based foreground proxy. It cannot establish correct organ
classes, boundaries, counts, hidden connections or physical behavior. No plant
geometry, physics, cultivation procedure or robot policy is changed by this run.
