# Photo-constrained plant iteration

## Resource constraint — latest user direction

Never run SAM, Depth Anything, ML inference/training or heavy batches on the
user's Mac. They are actively working there. Use RunPod for model computation;
local work is lightweight source editing and finished-artifact inspection only.
See `../remote-perception-v1/README.md` for the remote pilot. User has now
authorized RunPod spending and reasonable overruns without asking again.
Pilot is COMPLETE. Task worker astra-plant-perception-20260913 was verified
stopped after artifact retrieval. SAM2.1 and DA3-Small ran sequentially remotely.
See remote-perception-v1/evidence/execution.json for shutdown/rate, not an exact invoice.
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

## Remote perception pass complete — 2026-09-13

Actual comparison: /runs/hemp-perception-pilot-v1/index.html. Source/scripts and
compact evidence: ../remote-perception-v1/. Mac performed no ML inference.
Denser SAM2 recovered region proposals but missed/merged fine foliage. Exact
synthetic audits found only 19/402 visible narrow leaflets with best IoU >=0.5.
DA3 depth rank correlation with known narrow mesh depth was 0.012. Neither
backend provides validated organ census, contact geometry or physical parameters.
SAM3 was not run in that pilot because access was mistakenly thought unavailable;
the later SAM3 comparison below corrects this credential-discovery error.

Next pass: freeze a small reviewed sample of clear and overlapping visible
organs before further automated scoring. Inspect source resolution and metadata;
prefer genuinely higher-resolution originals to upsampling. Any prompted
inference or new rendering/raycast batch must run on one isolated RunPod worker,
with deadline and verified shutdown. Do not automatically optimize the plant
against unreviewed masks or start duplicate workers. No new fitting accepted.

## SAM3 comparison COMPLETE — 2026-09-13

User requests the strongest current model. Cached Hugging Face authentication
was found and official SAM3 access verified: earlier access-blocked conclusion
was incomplete. Task worker astra-sam3-comparison-20260913 was verified stopped after retrieval.
SAM3 same-image text, example boxes, native crops and alternate concept prompts
were executed remotely; results retained with synthetic coverage audits.
SAM3.1 is a video multiplexing release; image factory still uses SAM3 weights.

Actual review: /runs/hemp-sam3-comparison-v1/index.html. SAM3 is integrated but
not validated as the best segmenter for this domain. Plain 0.5 leaf prompt found
no reference masks. A 0.1 diagnostic found 119 regions but some swallow canopy
and background gaps. Text+example found two masks; native crops 1/0/1. Do not
promote these numbers to a true organ census. The immediate next step remains
reviewed boundaries and better-resolution original sources; keep automated
fit decisions paused until the observation model is validated. Do not revert to
SAM2 solely because it is easier to run. Document which model/prompt/threshold
is used and why. No new terms or mirror downloads were needed for SAM3.

## Source-resolution audit COMPLETE — 2026-09-13

Publisher PNG (large) and TIFF (original) both report 2250 x 2300 pixels for
the complete 30-plant grid. Metadata read through bounded 262144-byte HTTP
Range requests; no raster decoding, inference, weights or rendering on Mac.
Local grid JPEG is 1761 x 1800, so original offers about 1.28x linear resolution
relative to that overview. Existing single-plant input is 381 x 444; its exact
crop/resampling lineage remains unresolved. Do not call it verified native sensor
resolution. Original-grid dimensions alone do not demonstrate better detail than
that existing crop. No claim that the source resolution caused SAM3 failure.

Evidence: source-resolution-audit.json. Next discriminating step: trace crop
provenance and compare a remote extraction from the original against the frozen
input, then annotate a small fixed sample of clearly visible leaves and difficult
overlaps. Keep calibration separate from held-out evaluation; score precision,
recall and boundary agreement, not proposal count. No automatic geometry updates
from unreviewed segmentation, and no extra GPU spend in this metadata pass.


## Overlapping SAM3 tiles COMPLETE — 2026-09-13

User proposes cropping and stitching. Prior three broad crops were not a tiled
comparison. New pass freezes 1x1, 2x2, 3x3 grids with 30% overlap, leaf prompt,
0.5 primary and 0.1 diagnostic thresholds. Record raw masks and edge flags;
suppress duplicates without merging distinct leaves. Exact synthetic whole-leaf
IDs provide one-to-one precision/recall; real-photo predictions require review.
RunPod replacement worker dvayjyonatj1n6 (A40, $0.49/hour), 30-minute stop
watchdog. Old worker lacked free GPU capacity and remains stopped. No local ML.


Tiled result: /runs/hemp-sam3-tiles-v1/index.html. Reference proposals at 0.5
increase 0 -> 15 -> 51 after deduplication and crop-edge exclusion. Broad
synthetic whole-leaf matching improves 27 -> 58/134, but narrow 3x3 predictions
switch toward leaflets: 81/402 leaflet matches versus only 3/139 whole-leaf
matches. Leaf and leaflet identities must stay separate in any future fusion.
Real-photo masks remain unvalidated; visible dense regions are still missed.
No automatic geometry fitting accepted. Raw predictions preserved, scores and
source checked; replacement GPU verified EXITED after checksum-verified retrieval.
Next bounded outcome: reviewed real-photo organ labels at both anatomical levels,
then explicit multiscale fusion with no parent/child double counting.


## Organ identity review COMPLETE — 2026-09-13, heartbeat 20:35 UTC

Created /runs/hemp-organ-review-v1/index.html from saved source pixels and SAM3
outputs: three enlarged regions with six candidate leaflet anchors, unresolved
parent groups and excluded dense regions. These are assistant visual annotations,
not expert-reviewed masks or held-out test data. No new ML, rendering batch,
GPU allocation or fitting; static SVG overlays only.

Visual inspection caught and corrected two initial anchors on the stem and in
a gap. Rejected proposals are preserved. The central shared-leaf hypothesis was
removed instead of forcing adjacent blades into one parent. Old approximate
central downward leaf geometry remains suspect and must not be treated as a
validated landmark. Whole-leaf boundaries are untraced; no IoU or count accuracy
claim is permitted from these points/ROIs.

Inspected existing connection, side and top panels: the thin depth/rear geometry
is unverified from one photo. No plant geometry or mechanics changed. Next:
trace one clearly visible upper-left blade with an uncertainty band, then remote
mask correspondence scoring; retain independence/annotation limitations.

## 2026-09-13 — completed grid search, resolution ablation and organ-conflict audit

User requested denser crop grids, near-total visible-plant coverage and organ labels. They then corrected the search direction: after 50×50 regressed, turn toward smaller grids. I had unnecessarily completed a 100×100 check; preserve its evidence but do not repeat that expansion pattern. Bracket the winning region and refine there.

- Isolated A40 pod jly533nd5mlwnl, verified EXITED after checksum-verified retrieval. No Mac inference, training, image processing or rendering jobs. No desktop-app edits.
- Original image: initial grids 1,3,5,10,20,25,50,100; refinement 7,8,9,11,12,15. Fixed 30% overlap, primary confidence 0.5; 0.25/0.1 diagnostic. Fixed green-foreground estimate, conservative core and uncertainty band. No manual organ ground truth.
- Primary foreground-proxy IoU winner: 11×11, 30.47% plant-area coverage, 30.30% IoU, 0.60% definite-background fraction of prediction. Neighbors 10×10 and 12×12 score lower. At confidence 0.1, 12×12 is the best tested IoU tradeoff: 91.75% coverage, 86.93% IoU, 3.14% background fraction.
- 50×50 and 100×100 collapse on the 381×444 input. 100×100 processed 4,330 nonempty crops out of 10,000 and took 683 seconds; this was a poor use of search budget once the regression was known.
- Multi-prompt leaf/leaflet, stem and flower audit at the initially selected 10/5 grids: lowering confidence to 0.1 covers 98.5% of estimated foreground but 89.5% of that foreground has conflicting organ labels. This does NOT establish correct organ segmentation. At 0.25, 21.4% remains unclassified and 8.7% has conflicts. Leaves/leaflets are combined only as tissue, never counted as independent biological leaves.
- Found primary CC BY 4.0 dataset DOI 10.5281/zenodo.17783092 (Morales, Griffiths, Topp). Checked archive MD5 and inspected six 4000×6000 shoot photographs. These are excised shoots on cloth, NOT living whole-plant shape or mechanical evidence. Compared a fixed 1950×4150 crop with its 381px-wide downsample. At 20×20 and confidence 0.5: native coverage 59.65% vs 40.5% downsized. The color-based proxy has visible background speckles and uncertain edges; do not treat it as exact annotation.
- Added inspectable raw crop-local masks, full score maps, foreground mask/cutout, organ-ID PNG/NPZ exports with distinct background/unclassified/conflict IDs, and a static comparison viewer. Visually inspected original and native overviews; tested confidence and image controls in browser.
- Artifacts: runs/hemp-sam3-grid-search-v1/index.html and results/. Reproducible sources and compact evidence: research/hemp-defoliation/sam3-grid-search-v1/. Initial source commit 86a1218, protocol/viewer commit b42687b.

Remaining priority: trustworthy organ boundaries and semantic labels, not more grid density. Before fitting model anatomy from masks, create a small explicitly reviewed set of clear leaf/leaflet/stem boundaries on native-resolution images; mark hidden connections and dense clusters unknown. Evaluate prompted exemplars or corrected masks against those annotations. Keep whole-plant foreground coverage separate from instance correctness and from biological/mechanical validity. Do not claim this experiment reached near-100% correctly labeled organs or validated a plant model.

## 2026-09-13 — reference suitability correction; residual masking proposal

User explicitly rejected detached-shoot photos for the living upright potted-plant task. Archived them in the review and relabeled dataset controls; retain metrics as diagnostics only. Do not use their posture or geometry to fit the target plant. Verified original PLOS Fig. 1 caption says one week before harvest; pot is not shown in our crop, so task-stage/context suitability remains unverified. Next reference selection must establish living rooted/potted plants, natural pose and intended facility/task-stage context before optimizing segmentation.

User proposed masking accepted plant pixels black then rerunning on residuals. Discussed as an untested hypothesis with artificial-boundary/context-loss/early-error risks. Prefer testing black-fill against residual-directed crops of original pixels under the same inference budget and reviewed acceptance mask. Experimental design recorded in sam3-grid-search-v1/README.md. No GPU or inference started in this discussion.

## 2026-09-13 — residual experiments and alternative prompting completed

Three user-requested Sol/Terra agents completed residual A/B, source discovery and method research. Each residual condition used 87 calls and a frozen 0.5 first pass. Proxy coverage: unchanged 30.47%, black-fill 30.77%, original-context crops 31.94%. Context crops produced 470 overlapping cross-crop pairs and 131 edge proposals. Root inspected whole overlays and all three calibration close-ups. At 0.1, the unchanged condition outperformed both residual methods on proxy coverage. The static residual-mass selector over-concentrates crops; do not generalize this result to every residual technique.

Broad visual-region exemplars missed tissue or flooded background. An initial point-test configuration bug was corrected (enable_inst_interactivity plus the official processor-state/predict_inst path). Six positive/negative point runs produced 18 candidates in 4.62 seconds; localized blade proposals are useful for assisted labeling, not evidence of autonomous discovery or boundary accuracy. Preserve setup failures and all candidates. Original worker 87q94u6g8kjyo3 and single replacement mi70bjvnphais8 verified EXITED after checksum-verified retrieval. No local inference or raster processing.

Recovered native APPF 2472×3296 image: upright plant, tip/main stem/pot opening visible; pot bottom cropped, cage and dark/senescent tissue remain. Different sample/view/time from inherited crop; no cultivar mapping verified. CC BY-NC 4.0. New source not yet tested; its foreground annotation must account for non-green tissue and supports. Source review committed 79abceb; frozen protocol a59836c. Combined inspection: runs/hemp-segmentation-roundup-v1/.

## 2026-09-13 — direct manual annotation, first pass completed

User asked Astra itself to label the original in a 5×5 grid. Root inspected all 25 cells in enlarged row viewports, entered explicit vector coordinates, and inspected each row and stitched whole view. No SAM mask or image-generation output supplied the polygon coordinates. Prior model outputs had already been seen, so this is not a blind benchmark.

Produced 84 candidate leaflet contours, 6 exposed stem spans, 2 supports and 23 ignore/review regions. Shared global IDs and coordinates persist across 25 clipped SVG tiles. Bounds, positive area and proper edge-crossing checks pass for all 115 records; geometry validity does not establish image-boundary accuracy. Approximate boundaries, missed serrations, overshoot/undershoot and unresolved dense tissue remain. Unannotated pixels are unknown, parent IDs null, all records trainable:false; ignore regions are not valid organ masks. Corrected a displaced review region and two overextended contours during inspection.

Deliverables: editable labels, COCO-style draft with uncertainty extensions, grid manifest, stitched SVGs, and original/overlay review at runs/hemp-manual-segmentation-v1/. Next useful comparison: manually corrected contours versus point-assisted masks on suitable native-resolution examples, with an independently reviewed subset before fitting anatomy or making accuracy claims.

### 2026-09-13 — point-and-correction loop with scale controls

Ran official SAM3 interactive inference on one isolated RunPod A40. No local ML or raster processing. Three reviewed targets; full image 1×/2× and native crop 1×/2×/4×, then corrective full/native/4× conditions. Cropping helped exposed-blade identity; upscaling alone did not establish a boundary benefit. Corrected one misplaced dense-region point transparently, rather than accepting the cluster. Three provisional native masks exported with seven final points; all other pixels unknown and labels not trainable without review. Preserved all 72 candidates, exact prompts, model revision, raw masks and visual decisions. Verified 141 transferred hashes. Static before/after review: runs/hemp-point-loop-v1/index.html. Next useful test would hold crop/point budget fixed on additional independently reviewed visible blades; whole-plant completeness and hidden structure remain unresolved.

## Growth history v2 — stem continuity

Continued the user-requested developmental model, preserving v1. Corrected independent segment tapers and a fixed skinny hypocotyl: shared boundary radii now join adjacent sections and the main-axis base. Added finite positive radius and base continuity assertions. Lightweight implementation checks pass; published `/runs/hemp-growth-history-v2/`. Visually inspected the mature side skeleton. Its regular narrow branching remains a limitation; this revision establishes geometric continuity, not validated tissue mechanics or biological growth. No ML, heavy render batch, remote compute, desktop changes or cultivation optimization. Next priority is evidence for node spacing and branch-order variation across developmental stages.

## 2026-09-13 — dated-growth evidence gate

Latest user asks for reference images, elapsed real time and continued growth. Added growth-history-v2/TIME-CALIBRATION.md separating candidate indexed studies from verified usable observations. Publisher retrieval blocked by 429/browser verification; no raw timeline verified and no numerical calibration performed. Defined specimen/time-origin/scale provenance and fitting-versus-holdout requirements. Preserved uncalibrated clock rather than relabeling it days. Evidence-only pass; geometry and saved views unchanged, no new visual validation claimed. Next bounded action: obtain an accessible primary dated series and verify its specimen provenance before fitting. No compute worker started.

## Organ development research — 2026-09-13

User explicitly requested deep research into organs, developmental stages and rates. Added organ-development-v1/REPORT.md, evidence.json and README. Read primary BBCH PDF, leaf morphometry paper and hypocotyl histology; identified field leaf-appearance numbers in indexed thesis text, retained as provisional not defaults. Full access remains unavailable for thesis and hybrid petiole table. Documented UC Davis taxonomy typo and root-evidence caveat, seed/clone distinctions, separate appearance/expansion/maturation clocks, and current hard-coded bud and leaf-profile shortcuts. All numerical records forbid automatic default use. No plant geometry changed, so existing views remain unchanged; no visual/physics validation claimed. No ML or remote worker. Next implementation: explicit bud states and developmental identity, then source-linked leaf-profile comparison rather than maximizing foliage parameters independently.

## Growth history v3 — explicit buds

Added persistent dormant/active bud states for all modeled true-leaf axils; preserved inherited activation eligibility and canopy geometry to isolate this representation change. Added optional enlarged amber/blue diagnostic markers and inspected branching-stage three-quarter skeleton in browser. Attachment, activation timing and one-child-axis correspondence checks pass. Final 171 buds, 23 active, 148 dormant are scenario outputs. No biological calibration claimed. Lateral leaf profile reset and regular canopy remain next issues. No ML/heavy compute or desktop product edits.

## Basal bud audit — 2026-09-13

Latest user explicitly asks not to add lower buds merely to match their suggestion. Audited model rather than adding geometry: lowest two main-axis node ranks are held inactive; ranks 3–12 activate under an inherited eligibility rule and fixed delay. Added reproducible audit-buds.mjs and compact main-axis timeline JSON. Chronology assertions pass. This is a model explanation, not biological evidence. Primary developmental article publisher retry returned 429; no new empirical rate established. Existing visual views unchanged; no new visual inspection or validation claimed. No remote worker or heavy local job. Next evidence must resolve the same basal nodes over time, not compare unrelated plants.

## Biological justification requirement

User now explicitly requires researched justification for every scripted biological behavior. Added repository-level rule-provenance requirement and growth-history-v3/RULE-AUDIT.md. Audit separates supported anatomy from unsupported numerical timing, node eligibility, angles, dimensions, senescence and kinematic posture. Current model is not compliant as a biological forecast. No geometry or empirical claims changed. Next revisions must resolve documented unsupported behaviors individually with evidence; preserve exploratory legacy models.

## 2026-09-14 — lower foliage inventory

Bounded diagnostic of v4, motivated by user's sparse-bottom critique. Added reproducible leaf-junction counts in five height bands and traced lateral leaves to their main-axis branch origin. Legacy scenario has 11 junctions in lowest fifth vs 61 in each next fifth. This is not projected coverage, area, measured density or a target for biology. Counts conserve all 171 leaves; unresolved preset conserves 23. No geometry changed or growth/energy assumptions added. Visual anatomy comparison remains needed; no new reference fit, physics validation, ML or worker execution. Next: choose suitable pre-removal reference and fit visible lower branches with hidden connections explicitly unknown.

## 2026-09-14 — actual facility-photo / live-model comparison

Created standalone facility-comparison-v1: source-framed commercial facility photographs and identified indoor CBD chamber photograph beside orbitable v4 geometry. Inspected both reference types in the browser; external images loaded successfully. Recorded visible multiple-plant overlap, supports and the mismatch with our isolated regular model. These references do not resolve a single plant's lower connections and are not an established before-removal target. No geometry fit or physics added, no inference or batch jobs. Corrected “imbalance” wording in v4 to explicitly say a within-model distribution does not establish biological error. Retained assumptions and reference restrictions. Next: individual pre-removal reference with visible basal connections; no arbitrary foliage increase.

## 2026-09-14 — dated individual reference added

Inspected the preserved Massuela 2022 Figure 1 crop. Added it to the live-model comparison so individual potted silhouettes, source scale ruler and treatment labels can be examined directly, rather than relying only on shared-canopy photos. Explicitly identify C control versus L/T histories and 65-DAP whole plants versus separate 93-DAP flower closeup. Key observed mismatch: substantial floral structures in the photograph are entirely absent from our vegetative model; this is a stage mismatch, not proof of missing leaf count. Lower connections remain occluded. No geometry, calibration, physics or new render batches. Existing front/side/top camera behavior unchanged; only reference selection and evidence text added. No compute worker started.

## 2026-09-14 — first source-traced specimen subset

Built specimen-reconstruction-v1 using preserved Massuela Figure 1 panel (a), L plant. Three axis paths and four partial blade regions transferred from manual source-pixel annotations into normalized 3D. Treated specimen is not a verified pre-removal target. Publisher guide lines aid but obscure traces; basal branch attachments are hypotheses. Blade region parents remain null, not fake physical attachments. All depth unresolved at zero. Inspected front/matching, side and top; corrected source panel clipping and projection scale/center. Transfer checks pass, not annotation/biological validation. No full plant, contact physics, ML or compute jobs. Next: reviewed visible organ coverage and second-view depth evidence.

## Specimen reconstruction v2 — direct overlay and acceptance gates

Preserved v1; added six coarse visible blade contours (ten patches total), retaining unknown attachments and zero depth. Added source-photo plane in orbit viewer, explicitly diagnostic only. Visually inspected native source, SVG outlines and front overlay: contours remain coarse, significant foliage and all floral volumes absent. No claim of accurate segmentation or complete anatomy. Coordinate-transfer checks pass. Added visible acceptance gates for independent anatomy review, second-view depth, measured mechanical response and contact readiness. No cultivation schedule, growth rates, physics, ML or heavy compute added. Next meaningful improvement requires attachment/depth evidence, not counting more disconnected patches.

## 2026-09-14 — native reference and stage provenance correction

Extracted the existing PDF embedded Figure 1 (1552x627) without resampling; earlier page crop is 1080x434. Added same-panel comparison using SVG clipping, preserved original bytes locally and source hashes. Gain is modest, not recovered hidden detail. Native inspection still shows leaf overlap and publisher guide occlusion; no new attachments inferred. Caption audit: 65 DAP explicitly describes panel (b), not independently panel (a). Corrected active v2 specimen stage to unverified; preserved v1. No geometry change or new physics validation, fitting, ML, compute worker or cultivation guidance. Next: register original figure coordinates before contour correction; retain unknown attachments.

Browser inspection: native/page-crop comparison displays correctly; existing v2 front aligns the partial traces, side and top collapse to lines as expected for unresolved depth. This confirms the limitation, not validation. Compact source/provenance committed; extracted raster copies remain reproducible generated outputs.

## 2026-09-14 — original figure coordinate registration

Preserved v2 and created v3 with original embedded figure in left overlay. Derived source-pixel mapping from actual nested PDF image placement and saved page-crop dimensions, rather than eyeballing a resize. Saved nativePoints for every trace, mapping provenance, and inverse transfer check (max 2.85e-14 px arithmetic error; not annotation accuracy). Original region/axis geometry unchanged. Browser front overlay displays aligned placement; coarse contours and hidden junction errors remain. Side/top still collapse because depth remains unresolved. No new connections, leaf area, biological rates, mechanics or remote jobs. Next bounded priority: refine one clearly exposed blade against native detail, retain old contour and explicitly separate visible boundary from occluded origin.

## 2026-09-14 — exposed blade correction

Created v4 preserving v3. Inspected native upper-right detail: prior five-point patch began inside floral region and ended before visible tip. Revised only that patch to a narrower curved visible blade; excludes downward neighbor, retains occluded origin as unresolved truncation. Old/native contours retained and displayed orange/cyan together. Source remains too coarse for fine serrations; improvement is visual interpretation, not mask accuracy or a connected leaf. Fixed stale data/module caching encountered during review. Transfer checks pass; inspected detail and front/side/top (depth still flat). No other geometry, inferred attachments, biological scripts, physics, ML or compute jobs. Next: prioritize visible petiole/axis evidence or a specimen with independent depth views over multiplying disconnected patches.

## 2026-09-14 — multi-view suitability audit

Inspected and verified hashes of the two existing 084847-W images (same ID/timestamp). Front exposes petiole junctions, elevated view changes occlusion but does not establish correspondence/calibrated depth. No camera calibration found in checked local portrait/gallery metadata, not a claim none exists elsewhere. Preserved CC BY-NC restriction. Rejected as a replacement for requested dense facility plant or a metric-depth solution; did not transfer anatomy between specimens or train on these files. Compact assessment retained. Current v4 geometry and previously inspected front/side/top/photo views unchanged; no new visual model validation claimed. This avoids restarting the previously rejected sparse-plant gallery detour. Next current-specimen work must target observed branch evidence rather than guessed depth.
