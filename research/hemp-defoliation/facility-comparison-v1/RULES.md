# V4: evidence boundaries

The revision separates supported anatomy from assumed numerical behavior. It does not establish a validated growth or contact simulator.

| Behavior | Evidence / population | Implemented scope | Unresolved |
|---|---|---|---|
| Node-dependent compound leaf form | Balant et al. 2024, DOI 10.1111/nph.19817; Futura 75 individual 2, nodes 4a, 6a, 12b | Direct outline coordinates and 7/9/7 leaflet counts at matching main-axis node ranks | Other nodes, lateral leaves, physical size, expansion, 3D curvature; not a cultivar distribution |
| Distinguish bud identity from outgrowth | Phytomer anatomy, Spitzer-Rimon et al. 2019, DOI 10.3389/fpls.2019.00350; different population | Stable node/leaf-linked bud records. Default outgrowth state unresolved | Bud presence at every generated axil is an anatomical abstraction. Exact initiation time, eligibility and dormancy duration uncalibrated |
| Elongation and thickening are separate processes | Behr et al. 2016, DOI 10.3389/fpls.2016.01733; Santhica 27 hypocotyl study | Independent software curves for axial length and radius | Study does not calibrate these virtual main/lateral stems. Smoothstep curves and durations are assumptions |
| Separate blade and petiole expansion | Distinct anatomical organs; no paired quantitative time series obtained | Separate sensitivity controls, retaining former durations | No empirical organ-specific rates inferred |
| Opposite-to-alternate arrangement | USDA hemp descriptors, seed-grown architecture | Preserved schematic arrangement | Transition node 6 and 145-degree rotation are not calibrated |

## Remaining scenario rules — not claims of biology

All initiation intervals, initial emergence time, hypocotyl height, internode lengths, leaf lengths, petiole proportions, unfolding angle, leaflet bending, radii, smoothstep curves, cotyledon disappearance, branch headings and upward reorientation are assumptions. True-leaf senescence, roots, floral development, environmental response, force dynamics and contact are absent. Node caps and the 34-unit playback window are computational limits, not biological stopping points. Development units cannot be interpreted as days.

The legacy preset retains node 3–12 activation and fixed delays solely for comparison. The default does **not** substitute a new activation rule: it leaves outgrowth unresolved. Consequently its lack of branches is not a predicted plant form.

The outline source contains leaves from different nodes at collection, not images of a leaf changing through time. Scaling an outline through playback is a geometric interpolation, not observed ontogeny. Applying a sampled outline to both virtual leaves at a paired node is a reference transfer, not evidence that the pair is identical.

## Validation and next evidence needed

`checks.json` checks software consistency and parameter isolation. The source-coordinate panel and 3D blades share data: this tests transfer, not independent agreement with biology. Need repeated photographs of identifiable organs on the same plant, with scale and timestamps, before fitting developmental rates or forecasting branch outgrowth. Mechanical validation requires force/displacement measurements separately.

Coordinates are attributed in leaf-observations.json with hashes and pinned source revision. No explicit repository license found; no rights to source photos or source code are asserted. Only numerical outline and landmark observations retained.
