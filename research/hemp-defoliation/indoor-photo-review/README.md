# Indoor plant photo review — 2026-09-12

Open `http://127.0.0.1:8793/research/hemp-defoliation/indoor-photo-review/index.html` with the repository HTTP server running. The page embeds publisher-hosted photographs; no remote photographs are bundled or republished as local assets. `references.json` records URLs, source attribution, context and uncertainty.

## Evidence collected

- Three published photographs from Buckeye Relief's commercial indoor medical-cannabis facility: vegetative canopy, a flowering work area, and defoliation in progress. These are not confirmed CBD-hemp plants and are not a same-plant paired comparison.
- Three Royal Queen Seeds comparison images: lollipopping, vegetative defoliation, flowering defoliation. Indoor examples, not verified factory evidence; no verified CBD identity. The lollipopping photo explicitly carries Before/After labels. These labels do not establish absence of earlier pruning or training. Camera framing differs.
- Islam et al. (2022), Figure 9: confirmed Alpine Star CBD-hemp indoor research reference. The four panels are experimental groups, not before/after pruning.
- Existing indoor-v1 render for direct qualitative comparison. Model and references differ in viewpoint and stage; no metric fit is claimed.

## Visual findings from inspection

The current model has three separate, open, roughly conical plants with evenly tiered lateral branches. The commercial room photographs show substantial foliage overlap and many upper shoots with a visibly exposed lower framework. The paired photographs further show that an upper canopy can coexist with long bare lower branches. Simply reducing the model's leaf count would not capture all of this architecture.

This is evidence of a mismatch to these particular examples, not proof that every indoor hemp plant has one universal shape. Cultivar, developmental stage, prior interventions, spacing and viewpoint remain confounders. Exact branch connectivity behind foliage cannot be recovered from these photographs alone.

## Next justified work

1. Select a documented architecture and compare it from matching views, with uncertain hidden connections marked.
2. Represent branch topology, canopy overlap and removal history explicitly; retain the current checkpoint.
3. Use a paired removal example to assess whether the retained scaffold still looks plausible after visible foliage is removed.
4. Obtain a commercial CBD-hemp same-plant reference sequence before claiming partner-specific fidelity. This review did not find a verified one.

Photos do not calibrate bending stiffness, damping, friction, cutting force or damage thresholds. Those need separate observations or measurements.

## Verification

All eight gallery images loaded in the local browser. The commercial images, all three before/after images, CBD research figure and model render were visually inspected. Enlargement and filter interactions were checked. No geometry, physics or policy was changed in this review.
