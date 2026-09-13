# Photo-constrained hemp architecture v2

This candidate replaces v1's short, arrested main stem and similarly tall shoots with a persistent main axis and unequal lateral branches. Its target is control C in Figure 1b of Crispim Massuela et al. (2022), photographed at 65 days after rooted-clone planting. It is **not** established as the design partner's crop, a complete botanical reconstruction, calibrated development, or contact physics.

Open `/runs/hemp-development-v2/index.html` through the existing repository server. Front is now orthographic, allowing inspection of the projected scaffold. Oblique, side, top and branch-base views expose depth assumptions. The selector can show v1's scaffold with the current renderer; that is not an exact replay of the old renderer. The old checkpoint and its original screenshots remain untouched.

## Research applied

- **Crispim Massuela et al. (2022), DOI 10.3390/plants11010140:** the dated control plant supplies approximate projected main-axis and lateral centerlines. Original figure at `../height-evidence-v1/`; figure CC BY 4.0. The crop preserves the control plant but some canopy is outside the photographic panel. No full silhouette/maximum-width measurement is claimed.
- **Carlson et al. (2021), DOI 10.1093/jxb/erab346:** morphological characterization uses height, maximum canopy diameter and its height, trunk length, and internode measurements. We adopt explicit descriptor bookkeeping, not field-grown dimensions as indoor defaults. This paper's methods distinguish architecture, foliar traits and temporal growth; one scalar height cannot determine all three.
- **Balant et al. (2024), DOI 10.1111/nph.19817:** reuses the existing attributed Futura75 two-dimensional leaflet outlines. Morphological identity and developmental position matter, but our rank-to-leaflet count mapping, leaf size, tilt, curl and width variation remain chosen priors, not fitted observations.

The broader full-life morphological study returned in this search concerns White Widow; its node thresholds and heights were not adopted as CBD-hemp calibration. The USDA descriptor page timed out. Another high-CBD trait paper returned a security challenge on follow-up; no additional measurements were imported from it. No access control was bypassed.

## What the trace establishes

`reference.json` records approximate pixel centerlines, attachments and confidence labels. Orange overlay lines mean at least partly visible structure, not perfectly resolved anatomy; some connections are occluded. Blue dashed paths are hypotheses within the hidden canopy. All depth offsets are assumptions.

The 0.80 m main-axis height is a working scale estimate. The source ruler is labeled 80 cm but its zero/perspective are unresolved. This is not an 80 cm plant measurement. The displayed projection follows an orthographic assumption; a true calibrated camera was not recovered. Numerical round-trip error tests only the conversion from annotation pixels into the model and back. It is not an independent fit/validation score.

A has 9 modeled axes and 45 compound leaves. The count is a modeling choice, not a measured biological count. B and C vary depth and leaf pose around the same traced scaffold; they are uncertainty alternatives, not independent observed plants or calibrated domain randomization.

## Geometry changes and review loop

1. Preserve main-stem continuity, node positions and unequal branch trajectories.
2. Tie each petiole and branch to explicit persistent nodes. Growth introduces organs according to stable birth records.
3. First render exposed edge-on foliage and isolated pod-like reproductive proxies. Revised the leaf renderer so all leaflets share a compound-leaf plane before individual bending, then added position-dependent inclination, petiole length and leaflet size. Reproductive geometry now groups small envelopes; it is still a placeholder.
4. A further side-view inspection showed excessive downward leaf inclination. Preserved that rejected pass and reduced uniform droop in favor of mixed inclination. Retain varying local blade width and asymmetry within the traced leaflet template. These are modest procedural priors, not new measured specimens.
5. Review front, side, oblique, early/later and scaffold-only states. Record remaining errors rather than claiming visual plausibility establishes physics.

Planar leaf area integrates the same outline width/asymmetry used by the display. Leaf mass assumes area density, and stem mass assumes fresh density. Neither is measured for this specimen. Thickness, stiffness and age-indexed material changes are uncalibrated. There is no gravity equilibrium, collision solver, cutting, bruising or learned robot execution in this viewer. The old recorded leaf-removal toggle is retained for organ-membership continuity only; it is not a recommended pruning action.

The 0–100 replay is **not calendar days**. Index 100 matches the traced final scaffold; earlier states are a developmental hypothesis. The source's 65 DAP annotation must not be used to assign dates to the intermediate states.

## Reproduce

Run `python3 research/hemp-defoliation/development-v2/build.py` with NumPy installed. Runtime output under `runs/` is regenerated. Local Three.js dependencies are reused. `evidence/audit.json` checks all 51 snapshots of three alternatives, attachments, finite values, birth ordering and invariance of retained scaffold during the membership event. Whole-plant biological/physical validity remains false.

## Next discrepancy to resolve

The visible major scaffold is now constrained more tightly than the leaves. Foliage attachment selection, leaf silhouettes, reproductive geometry and depth remain the largest mismatches. Next fit individual visible petiole/blade landmarks with confidence bounds, obtain a second view or a documented time sequence, and test the reconstruction against observations not used to author it. Do not compensate for missing depth by reporting a small front-projection error as accuracy.

## Saved visual evidence

`evidence/reference-comparison.jpg` aligns the photo crop and actual front-view canvas export using the assumed root/apex scale and orthographic camera. It shows substantial residual differences in floral envelopes and individual leaves. `front.png`, `side.png`, `oblique.png`, `early.png` and `previous-scaffold.png` are actual viewer exports; the provenance ledger records hashes. `first-pass-drooped-front.png` retains the rejected excessive-droop pass. The current front comparison is a fitting aid, not an independent accuracy result.

A later continuous upper-flower envelope was also tested and rejected: it filled the stem as a cone and erased the reference’s clustered structure. The rejected function and screenshot remain in `evidence/rejected-floral-envelope.js` and `evidence/rejected-continuous-flower.png`; the final viewer retains the earlier explicitly labeled cluster placeholders. More volume alone did not improve anatomical fidelity.
