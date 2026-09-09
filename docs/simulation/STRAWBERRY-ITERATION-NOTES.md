# Manual strawberry simulation notes

## Working agreement — 2026-09-09

Work directly with the user on the plant and its physical interactions. Do not edit the desktop app or package a skill/plugin during this phase. Keep the original specimen inspectable; make separate candidates. Show actual rendered images and recordings after changes. Record unsuccessful work as well as useful changes. This is a notebook of the work, not a finished universal methodology.

## Leaflet trial, paused

Observation: the leaflet still resembles joined stiff panels, with visible gaps under bending. An isolated shared-vertex shell was attempted in `tools/study_strawberry_leaf.py`. It reported an acceleration warning at 0.00025 s, before contact. Its result is retained under `assets/workcells/strawberry-specimen/leaf-study/shell/contact/result.json`. It was not applied to the plant and is not a successful deformable-leaf model. The user redirected the next iteration to the stalks near the crown.

Lesson: trying a richer physical representation is not evidence that it works. Preserve the failed numerical result and leave the stable specimen unchanged.

## Crown-adjacent stalk support

User observation: stalks in the reference look substantially stronger near the crown than in the simulation.

Reference: [Gerald Holmes / Cal Poly, crown and root anatomy](https://strawberrycenterblog.com/2026/02/19/__trashed/). The bare-root image shows broad petiole bases around the crown. It shows trimmed stalks; it does not measure mature emergence angles, tissue modulus or load response. Metric radii and unloaded curves below are explicit modeling hypotheses.

### Baseline

Saved the source, input graph, model, validation and relevant rollouts to `assets/workcells/strawberry-specimen/checkpoints/v4-before-leaf-study/`. The original standalone viewer still points to that original whole-plant result. No desktop app files were edited.

The earlier leaf-stalk model used a 1.65 mm nominal radius with modest taper. A larger sleeve was visible at the base, but the spring calculation did not include a stronger basal section. Worse, the moving sleeve extended into the rigid substrate collider.

### Separate hypotheses

1. **Cross section:** use a 2.8 mm leaf-stalk basal radius and 3.3 mm flower-stalk basal radius, tapering to the existing nominal shaft over 35 mm. Keep the material modulus values. Integrate rotational compliance along the tapered cross section; the same section generates the visible and contact mesh. Rounded segment ends keep coverage under bending; mass comes from the material span instead of summing overlapping cap volumes.
2. **Unloaded posture:** let the leaf stalk rise near the crown before curving outward. Preserve its nominal endpoint. Do not increase stiffness to compensate for a wrongly specified unloaded growth direction. The flower stalk keeps its previous unloaded curve and still sags under fruit weight.
3. **Attachment boundary:** the embedded basal sleeve belongs to the fixed crown. The flexible exposed stalk begins at the top of that foundation. Keep the exposed stalk's collision enabled. Do not turn off its soil or probe contact to obtain a favorable animation.

### What exposed the attachment bug

The thicker-base candidate increased one basal spring from roughly 0.0204 to 0.1637 N·m/rad, yet its resting rotation was still about 13.5°. A diagnostic disabling only the embedded sleeve collisions reduced that rotation to about 1.1°. This implicated a boundary-condition artifact, rather than inadequate stiffness alone.

The implemented fix shortened the embedded sleeve to the flexible-stalk origin and attached it to the fixed crown. Static embedded crown tissue no longer generates spurious moving-body/rigid-substrate reaction forces. The stiffer candidate with that corrected foundation again settled at about 1.1° for the left leaf stalk. These are joint rotations relative to the modeled unloaded shape, not absolute growth angles or real-plant measurements.

### Contact test caught a second problem

The first corrected-foundation candidate (`basal-study/v6`) completed all four scripted probe trials and matched no-contact controls without solver warnings. However, the basal push penetrated the stalk by **2.123 mm**. That result is retained and is not an acceptable contact-fidelity pass. Leaf, distal-stalk and neighboring-fruit contact penetrations were much smaller.

The next candidate refined the numerical contact time constant on the stiffer basal sections to 1 ms. This is contact discretization work, not a change to the assumed tissue modulus. At the old 0.5 ms timestep it reduced penetration but still produced a timestep-dependent force spike. Solver warnings alone were insufficient to detect the bad result.

### Numerical check and selected candidate

Compared the same initial state and the same physical probe trajectory with only timestep changed. Before the two smaller-step runs, recorded the criterion: probe penetration below 1 mm, no solver warnings, and less than 10% change in impulse and maximum target displacement between the two finest timesteps.

| Timestep | Probe penetration | Peak normal force | Contact impulse | Maximum target displacement |
| --- | ---: | ---: | ---: | ---: |
| 0.5 ms | 0.567 mm | 4.513 N | 1.61460 N·s | 9.803 mm |
| 0.25 ms | 0.102 mm | 1.600 N | 1.56056 N·s | 8.843 mm |
| 0.125 ms | 0.080 mm | 1.600 N | 1.56081 N·s | 8.846 mm |

The two finest steps differ by 0.016% in impulse and 0.035% in target displacement. Selected **0.25 ms** for candidate v7. This establishes convergence for this push, not for all loads or biological accuracy. Keep the rejected coarse result; do not average it away.

Rebuilt v7 and ran a **fresh 10-second gravity settle**, followed by four contact trials and their matching no-contact controls. All reached their intended contact target, had no initial probe overlap, completed without warnings, and had matching initial states and commanded strokes. All controls produced zero probe contacts. Maximum probe penetration was 0.102 mm at the base, 0.231 mm on the leaf, 0.057 mm on the distal stalk and 0.160 mm in the neighboring-fruit test. Maximum geometry coordinate span in the final second of settling was 0.128 mm.

The final left and front leaf-stalk root rotations were 1.10° and 0.71° relative to their unloaded orientations. The fruit-bearing peduncle still rotated 11.86° under load. Existing spring damping remains a heuristic proportional to stiffness, not a measured damping coefficient.

**Remaining failures/limits:** initial gravity settling still contains up to 1.43 mm of berry/stalk penetration and 1.10 mm at the trough. These are reported, not covered by the four probe-contact passes. Leaflet wedge gaps and polygonal stalk bends remain visually evident. The material modulus, circular cross sections, taper dimensions, unloaded growth curve, damping and fixed-root assumption are uncalibrated.

### Inspectable evidence

- Separate model and existing orbitable viewer: `assets/workcells/strawberry-specimen/basal-study/v7/index.html`.
- Camera-matched actual-state still and video: `basal-study/crown-before-after.png` and `.mp4`.
- Video has an explicitly labeled settled-state lead-in, a physical-time contact recording, and a hold on the actual final state. It does not animate a reset back to the initial plant.
- Before/after strokes have the same timing, direction and relative distance; each is centered on its own settled target. This comparison includes geometry and boundary changes, not just material stiffness.
- Detailed results: `basal-study/v7/validation.json`, `basal-study/comparison-results.json`, and `basal-study/timestep-check/results.json`.
- The standalone candidate reuses the existing viewer with an additional basal-test selector. No desktop product files changed.

Rebuild with `tools/build_strawberry_specimen.py --output assets/workcells/strawberry-specimen/basal-study/v7`. Test with `tools/test_strawberry_specimen.py --model-dir assets/workcells/strawberry-specimen/basal-study/v7 --kind rest`, then `--kind basal`, `leaf`, `stalk`, `neighbor`, each with and without `--control`. Render with the analogous `tools/render_strawberry_specimen.py --model-dir ... --kind ... --video`; export recorded 3D replays using `--export`. Use the environment containing MuJoCo 3.12.0. Raw rollouts and intermediate checkpoints stay local.

## What to carry into the next iteration

- Check attachment constraints and initial overlaps before tuning material stiffness. A bad boundary can imitate a weak material.
- Record unloaded geometry separately from the gravity-settled shape.
- Make changes to structural dimensions affect mass, contact geometry and bending stiffness consistently.
- Use a localized push and a matched collision-disabled control; log all contacted objects and penetration.
- Compare the same camera, saved states, and honest test labels. Both models here use the same relative probe stroke centered on their own settled stalk; absolute probe positions differ.
- Keep numerical validity, anatomical plausibility, material calibration and eventual robot-task success separate.

Physical modeling reference: [MuJoCo joints and contact modeling](https://mujoco.readthedocs.io/en/stable/modeling.html). The abandoned leaflet shell used the documented [2D flex elasticity](https://mujoco.readthedocs.io/en/stable/XMLreference.html#flex-elasticity) capability; its existence did not establish stability for our chosen mesh and parameters.
