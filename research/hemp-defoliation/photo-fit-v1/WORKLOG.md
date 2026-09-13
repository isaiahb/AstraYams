# Photo-constrained plant iteration

## Resource constraint — latest user direction

Never run SAM, Depth Anything, ML inference/training or heavy batches on the
user's Mac. They are actively working there. Use RunPod for model computation;
local work is lightweight source editing and finished-artifact inspection only.
See `../remote-perception-v1/README.md` for the prepared, unexecuted pilot.
Do not resume the earlier local parameter fitting/render batch automatically.

## Pass complete; next pass ready — 2026-09-13

Initial reconstruction and visual/geometry checks are complete. The recurring
task can now continue from the next ranked mismatch below. Mark a new pass active
before changing files; do not run a second simultaneous build.

User request: adapt CityFarmers SIM's tomato methodology, keep iterating until
stopped, and show real-photo versus actual-model spot-the-difference evidence.
Desktop app changes remain out of scope. The 15-minute heartbeat is
`iterate-hemp-plant-realism`.

## Method adopted from CityFarmers SIM

Read its task and `research/synthetic-plants/leaf-organ-model/README.md` on
2026-09-13. Useful principles: persistent organ identity; explicit connected
geometry; matched cameras; measured variation versus transferred priors versus
synthetic stress tests; fitting data is not a holdout; static growth stages are
not physics replay. Its current tomato leaf generator is not fully calibrated,
and no mechanics values or cultivar rules are transferred here.

## Initial evidence correction

Anderson Figure 1's Cherry Blossom crop truncates the canopy at top and bottom.
The prior research viewer also used object-fit:cover, further hiding that fact.
Cherry Wine's 50 ppm image has a more complete visible canopy and stem base and
is selected for the first projected reconstruction. This is a geometric
observability decision, not a recommendation for cultivation. The original
Cherry Blossom dataset and other cultivar profiles remain intact.

Use the published photo only as a 2D observation. Its actual specimen ID,
perspective, metric scale and hidden branch origins are unresolved. Cohort
height and stem diameter provide a working scale prior, not photogrammetric
measurements of this photographed individual. Dry biomass must never be used
as fresh mass without conversion evidence.

## Planned acceptance evidence

- Source image with overlaid approximate traced axes and uncertain connections.
- Initial and fitted 3D models rendered at the same camera and scale.
- Reference/model mask overlap and horizontal occupancy errors, explicitly
  fitting diagnostics, with sensitivity to segmentation thresholds.
- Side and top views of alternative hidden-depth hypotheses.
- Stable organ IDs and exact parent attachments.
- Mechanics remain uncalibrated and must be tested independently.

## Next ranked mismatches

1. Compare three local source patches (apex, middle, lower terminal clusters)
   against the corresponding actual mesh projections. Record missing organ
   types and projected directions before adding geometry. Source is low-res;
   explicitly distinguish visible evidence from latent fine-structure guesses.
2. Fit narrow leaflet outlines/posture locally, rather than widening all leaves
   to improve global coverage. Current narrower default is a visual hypothesis,
   not a cultivar-specific measurement. Preserve masks and failed attempts.
3. Check hidden-depth hypotheses and nonadjacent stem/leaf intersections. The
   top view remains flattened because only one source view exists; do not
   pretend independent 3D validation is available.
4. Only after geometry improves, connect a bounded mechanical probe to the same
   graph; report assumptions,
   numerical convergence and unresolved biological calibration separately.

## Completed comparison passes

1. Built 15 manually projected axes and 37 visible leaf-junction/direction
   landmarks. Initial fit enlarged blades to cover missing structures, reaching
   width multiplier 1.6. Visual review rejected its maple-like form. Preserved
   metrics and residual in `evidence/rejected/wide-leaf-*`.
2. Added 28 connected latent secondary shoots and bounded width. This improved
   coverage but retained broad repeated fans. Preserved pre-midrib image and
   manifest under `evidence/rejected/`.
3. Found a mesh bug: asymmetric outline profiles sometimes have both margins
   on one side of the nominal straight axis. The straight center strip folded
   outside the outline. Replaced it with the extracted medial curve and removed
   degenerate tip triangles after export rounding. Inspected corrected WebGL.
4. Added a narrower-leaf hypothesis (width .65, cup .06). It looks closer in
   blade proportions but scores lower; it is the default, with optimized and
   alternate-depth models retained for honest comparison.
5. Standardized fitting/reporting at native 381x444 resolution, closing3 pixels.
   Earlier half-resolution histories have different effective closing radii and
   must not be compared directly. Native raw IoU: initial28.5%, fitted37.6%,
   narrower34.2%. Coarse:36.9%,47.2%,45.2%. No independent holdout.
6. Threshold sensitivity30/42/60: narrower rawIoU35.2%/34.2%/32.9%.
   The source mask is a heuristic, not semantic ground truth.
7. All five exported variants pass finite vertices, index validity, unique IDs,
   parent resolution, nondegenerate triangles and exactly connected branch/leaf
   origins. These checks do not validate biology or prevent self-collision.

## Visible remaining difference

Source has denser fine structures at terminal clusters, less repetitive leaf
posture and brighter illumination. Current mesh is sparse there and the apex
still resembles a generic fan. Preserve this criticism in subsequent passes;
do not declare success merely because the viewer renders or a score improves.
There is no whole-plant growth/contact solver or PPO training in this pass.
