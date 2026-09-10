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


## Multi-reference morphology review — 2026-09-09

The user asked to compare crown/root angles and whole-plant structure against more than one photograph. Added seven new primary-source image files, retained two previous references, rendered the unchanged v7 specimen from comparable directions, and made three local “spot the difference” plates. Full findings and source conditions are in `STRAWBERRY-MORPHOLOGY-REVIEW-2026-09-09.md`.

This revealed a distinction missed by the earlier base-only rotation metric: proximal leaf-stalk segments stand 11–23° from vertical, while several distal segments point below horizontal. The next geometry review should address curvature along the stalk and leaflet orientation, together with layered crown attachments. Roots are absent, so root angles cannot yet be assessed in the model. No new geometry or contact-accuracy claim was made in this review.


## Task-specific parametric physical models — thesis discussion

User direction: AI should research an object and construct a sufficiently useful parametric physical model for learning a specific robot task, beginning with strawberries. Generalize the methodology after demonstrating it here; do not resume desktop app development.

The current generator is already parametric, but many anatomical choices, attachment rules and material constants are embedded in code. The next representation should make explicit: the object’s connected parts; unloaded shape and dimensions; constitutive/contact/attachment behavior; the conditions under which parameters vary together; source evidence and uncertainty; and the task-specific tests that could reject the model. Visual geometry and mechanical discretization may differ in resolution, but their contact locations must agree to an explicit tolerance.

Model-family error must be separated from parameter error. An always-intact beam cannot represent cutting by stiffness tuning alone. A fixed crown can represent some above-ground brushing tasks, but not root movement or pullout. The task determines which effects must be represented. Research supplies priors; real observations and controlled interactions constrain parameters. Photographs alone do not identify material properties.

Proposed next bounded milestone: parameterize one coherent strawberry crown and its leaf-stalk/leaflet system, expose parameters currently hidden in the generator, and produce several anatomically plausible variants. Show each from the same review cameras, then apply the same contact probes. Keep research-derived, inferred and measured values distinct. This is a proposed next implementation, not completed functionality or demonstrated sim-to-real transfer.

Relevant existing foundations: [OpenAlea multiscale tree graphs](https://mtg.readthedocs.io/en/latest/user/intro.html) for plant architecture, [MuJoCo elasticity models](https://github.com/google-deepmind/mujoco/blob/main/plugin/elasticity/README.md) for available deformable primitives, and [MuJoCo system identification](https://github.com/google-deepmind/mujoco/blob/main/python/mujoco/sysid/README.md) for fitting simulation parameters to recorded sensor data. These establish prior art and possible building blocks, not a selected dependency stack or a validated strawberry model.


## Scientific model refinement and simulation efficiency — thesis discussion

User extends the goal to an AI-led scientific loop: observe, propose models, design experiments, measure disagreement, revise, and discover more accurate or cheaper calculations. The representation may span physical scales when the task requires it.

Distinguish errors in anatomy/topology, assumed parameters, missing mechanical effects, and numerical approximation from evidence against fundamental physical laws. Our strawberry results currently demonstrate the former categories. A hierarchy can use detailed calculations or experiments offline to identify a cheaper runtime model, with refinement when a task leaves the validated range. Finer spatial detail alone does not establish accuracy.

Success should be assessed against independent observations and held-out interactions, together with simulation throughput and stability. A surrogate trained only on an imperfect simulator can inherit its errors. The proposed process generalizes to model/constitutive-law discovery and numerical-method improvement; it does not establish that this project has discovered new physics or mathematics.

Prior work to examine when implementation reaches this stage: [equation-free multiscale computation](https://arxiv.org/abs/physics/0209043) and [MeshGraphNets](https://arxiv.org/abs/2010.03409). No new dependencies, plant geometry, solver or desktop UI were introduced in this discussion.

## Executing the deferred work: parametric canopy and a continuous-surface experiment

The request to execute the outstanding work is tracked in `STRAWBERRY-OPEN-WORK.md`. Desktop product files remain untouched. Candidate outputs live in `assets/workcells/strawberry-specimen/parametric-study/`; v7 and all rejected candidates remain available.

### Representation and morphology

Added an explicit configuration/compiler for crown-relative attachment positions, unloaded Bezier centerlines, leaflet frames, size-dependent leaf mass, material priors and correlated morphology seeds. The configuration records sources, assumptions, missing mechanisms and units. The source graph is compiled into the existing physical model, not applied as a render deformation. Each output records input/generator/scene hashes and MuJoCo version.

The first new short stalk collided with its own 18 mm stipule. Candidate v8 is retained as rejected; scaling the attached stipule to the stalk removed that overlap in v9. Radial leaf orientations had also been mixed with intrinsic xyz Euler rotations. Applying the azimuth before the leaf elevation fixed that frame convention. It exposed overlap between broad adjacent leaflets in v10; an explicit wider trifoliate fan removed the initial overlap in v11. This fan angle is an anatomical hypothesis, not a dimension measured from a photo.

Geometry alone did not solve the loaded droop. We then found [Tsubota et al. (2022)](https://doi.org/10.11357/jsamfe.84.4_229): reported effective petiole moduli were 89, 194 and 297 MPa for new, second, and third-and-older leaves. The study used Tochiotome plants and inferred modulus from buckling with specified supports. Candidate v12 uses these as age-dependent priors; mapping our leaf ages to those ranks is assumed. This is not a direct calibration of our tapered circular beam model. The prior stiffness-proportional damping rule remains, so the change affects damping as well as stiffness. Leaf mass, blade mechanics, fruit-truss mechanics and root support remain uncalibrated.

The final candidate v13 has the same geometry/material configuration with a refined timestep. Its four mature distal stalk inclinations are 47.2°, 30.8°, 55.8° and 57.1° from vertical, compared with 94.0°, 70.3°, 97.6° and 105.4° in v7. These are model measurements, not errors against reconstructed reference angles. The actual-state comparison shows the canopy improvement and the remaining coarse leaf surfaces.

### Numerical recheck after material changes

The stronger bases produced a 4.019 N transient normal-force peak at 0.25 ms. Although penetration was below 1 mm, that peak was timestep-sensitive. At the same frozen initial state and probe stroke, 0.125 and 0.0625 ms produced peaks of 1.571160 and 1.571127 N, impulses of 1.607187 and 1.607223 N·s, and maximum control-relative target displacements of 6.008963 and 6.009000 mm. Selected 0.125 ms and reran a fresh settle and all contact trials as v13. Force-limited actuator commands do not clamp the contact normal force.

All four representative contact/control pairs and four pairs on two untuned morphology variants passed the numerical probe gate: intended target touched, identical initial state/stroke for each pair, no initial probe contact, no runtime warnings, zero control contacts, and probe penetration below 1 mm. Holdouts use seeds 41 and 73 and approach offsets −25°/+25°. The variation links leaf dimensions to mass and fruit dimensions to volume/mass. It is not an empirically fitted plant distribution or a learned-policy generalization result. All incidental surfaces are retained in the reports; isolation from other organs is a separate field.

The full-scene gate remains open: v13 gravity settling still reaches 1.12 mm fruit/trough and 1.36 mm fruit/stalk penetration. Seed 41 shows 0.687 mm final-second geometry drift, versus 0.126 mm in the representative plant. Neither is hidden by the successful probe tests. See `batch-results.json`, per-candidate `audit.json`, and `v12-timestep/results.json`.

### Continuous leaf surface: separate reduced-model prototype

The earlier 2D elastic shell remains rejected. Its narrow end triangles produced initial self-contacts and large passive forces; improving triangulation alone did not yield a valid model at the chosen step. A temporary offline Triangle meshing experiment was exploratory and is not a runtime dependency of the accepted model. No FEM calibration or fully elastic tissue-shell result is claimed.

Implemented a different reduced representation: one shared-vertex MuJoCo flex surface supported by articulated transverse ribs, with hinge bending and near-inextensible edge constraints. Rendered and contact surfaces are the same flex. The first unconstrained rib surface changed edge lengths by 20.6%; a first soft constraint attempt still reached 2.02%, over the 2% criterion. Both are retained, not promoted. The stronger numerical edge constraint in `rib-surface-v2` gives 0.529% maximum edge change, 0.903 mm maximum probe penetration, target contact and no initial contacts/runtime warnings. Its no-contact control produces zero contacts. At half the timestep, peak force differs by 0.64% and maximum control-relative vertex displacement by less than 0.001%.

This is still a reduced bending model: ribs constrain transverse deformation, and there is no calibrated membrane law, torsion, explicit veins, turgor or fracture. First-quarter vertices are pinned; the first dynamic rib is one axial cell beyond the pinned region. The isolated boundary is not the crown attachment. The continuous surface is **not integrated into the whole plant** or the old rigid-mesh exporter. Its own video replays actual qpos through MuJoCo and checks recorded/reconstructed flex vertices within 0.1 mm. Whole-plant v13 still uses four panels per leaflet.

### Inspectable outputs and remaining dependencies

- `parametric-study/whole-plant-progress.png`: credited real reference, preserved v7, candidate v13.
- `parametric-study/crown-progress.png`: matched crown views with geometry-only and literature-prior stages.
- `parametric-study/v13/index.html`: copied standalone review viewer with saved physical rollouts; leaf camera recentered on the actual probe trajectory. Product app unchanged.
- `leaf-study/rib-surface-v2/contact-and-control.mp4`: continuous-surface contact and negative control at physical playback speed.
- `STRAWBERRY-CALIBRATION-PROTOCOL.md`: concrete observation, fitting and held-out experiment protocol; prepared but not executed on real plants.

Next dependencies: integrate and retest the continuous surface in the plant; resolve remaining truss contact penetration; represent and constrain crown/root anchorage; measure real responses; test sensitivity to discretization and uncertain geometry/materials; add physically triggered cutting/retention and damage; then train the harvest policy. A faster surrogate requires a validated teacher and independent observations. None of these remaining steps is marked complete by the current batch.


## 2026-09-09 — Finite fruit orientation and unloading

User noticed unrealistic fruit angles and challenged the assumption that a
stalk growing under fruit weight should recover to a never-loaded shape.
Inspected real truss anatomy, inferred body COM/inertia and current rotations.
The mass was finite; the erroneous local-down fruit attachment caused a 42–64°
angle to its terminal stalk. Optional terminal-tangent material frames fix that
without world-space pose overrides. v13 preserved; new v14 checkpoint.

Independent finite-body gravity acceleration agrees with the parallel-axis
inertia calculation. Four paired release/control experiments cover two distinct
rest-curvature/stiffness hypotheses and two timesteps. Identical initial loaded
poses and restoring moments lead to 19.71 vs 11.39 mm tip rise by 3 s after load
release. Material changes occur before each experiment, never at release; this
is an identifiability counterexample, not measured growth or plasticity.

Every release preserves qpos/qvel exactly. Refined timestep changes the response
curve by at most 0.061 mm. The event only disables a calyx attachment weld, so
blade contact, cutting work, fracture and a distal stalk remnant remain absent.
Contact penetrations up to ~2.3 mm still prevent a physical-accuracy claim.

Rendered before/after fruit closeups, recorded release video and recoil curves;
inspected pre-release, falling and late-response frames. Research distinguishes
fast elastic, delayed recoverable and irreversible plant bending, but no real
strawberry recoil/growth constants were found or measured in this iteration.
Prepared matching-plant unloading and longitudinal observations in the study
README. Desktop app unchanged; root/leaf/harvest roadmap remains open.

Method: check hidden frame/inertia assumptions before adding complexity; verify
analytical mechanics independently; branch same-state experiments; preserve
pose/velocity across topology events; use paired controls and timestep studies;
expose non-identifiability instead of claiming a single fitted biological truth.

Final attachment audit rejected the first temporary weld for 0.1996° rotational
error against a predeclared 0.1° numerical tolerance. Preserved it under
`release-soft-weld`, increased only its constraint torque scale (0.03 -> 0.1),
and repeated all eight trajectories. Angular error is now <0.0185° and total
mass is unchanged. Final rise remains ~19.71 / 11.39 mm; timestep response
curve change <0.059 mm. Exported an orbitable standalone replay using existing
viewer code; checked matching body-local geometry across the topology change.
Desktop product files remain untouched.


## 2026-09-09 — Own the next-goal decision

User explicitly asked the agent to infer values from the repeated feedback and
derive the next goals instead of requiring the user to identify each defect.
Recorded a working project brief in AGENTS.md and an autonomous critique loop
in REALISM-METHOD.md. Updated the stale keyed-insertion focus to the current
strawberry/modeling work; product UI remains paused.

Before selecting the next fix, classified recorded contact failures by object
and phase. The largest release penetration is a ground impact, whereas the
plant's initialization contains fruit/stalk and leaf/leaf overlaps. The next
selected outcome is a credible contact/support/unweighting test of the intact
fruit cluster, with load transfer and recovery evidence. This avoids picking
work merely because its numerical error is largest. The audit and standing
workflow are completed; the new physical support trial is not yet implemented.


## 2026-09-09 — Contact support, failure diagnosis and tolerance checks

Followed the selected goal through implementation, rejection, repair and
verification. The intact v14 fruit cluster is supported by an ideal actuated
bench stage with a contact-matched concave cup. A calyx force/torque sensor
checks the load path. The stage uses contact-force feedback; the fruit has no
tool attachment or state overrides. Product UI was not edited.

v1 failed: neighboring-berry contact on approach; an every-step 22.87 N /
4.22 mm floor/fruit event during withdrawal that was invisible in the 5 ms
saved force trace. Exact-command replay located the event at 8.99925 s. The
recomputed next-state contact was zero. Retained source and failed reports in
commit dbff206. No isolated engine root-cause claim.

v2 narrows the cup (22 → 16 mm outer diameter), joins its shaft to the floor,
and uses an explicit convex-prism floor. Controller and acceptance bounds are
unchanged. Central support/control, a half-timestep support repeat, and ±2 mm
approach/control pairs completed without warnings or unintended tool contacts.
Central hold: 76.56% weight on cup, 23.46% on stalk, 0.2163 N peak contact,
0.0063 mm maximum penetration, 8.81 mm mean stalk-tip rise, 0.568 mm final
control-relative fruit deviation. Newton hold residual <0.000111 N. Refinement
changes the fruit path <0.0154 mm. Both approach offsets pass the same checks.

Personally reviewed the instrument connection and contact from front/side/
oblique cameras, complete approach/hold/lowering/retreat snapshots, load traces
and browser replay. Reframed the whole-plant camera when its upper canopy was
clipped. The cup never touches neighboring berries; their approximately 11 mm
response propagates through the shared branch. Exported actual MuJoCo poses,
no animation overrides, plus matched control and offset selectors.

The numerical support milestone is complete; biological calibration is not.
The next prioritized study is load–hold–unload material identification, testing
fruit contact compliance and stalk history/recovery separately. No real safe
force, flesh-damage model, growth law, cutter or trained policy is claimed.
Reproducible sources, evidence, assumptions and commands live in
assets/workcells/strawberry-specimen/support-study/v2/README.md.


## 2026-09-09 — Stalk recovery hypotheses and baseline repair

Researched strawberry mechanical measurements with organ, species and loading-
mode applicability. No accessible matching fruit-stalk load–hold–unload curve
was found or fitted. Petiole stiffness, peduncle cutting and woody-branch creep
remain distinct evidence. Recorded the search limitations and a real measurement
plan with paired baselines, actual stage position/force, multiple hold durations,
long recovery and held-out plants/interventions.

Implemented a passive rotational Maxwell component in parallel with the existing
42 truss springs. Its internal rotation advances once per integration step;
the force callback never advances state. Noncommuting rotation energy-gradient,
fixed-strain relaxation/dissipation and analytical scalar creep/recovery checks
pass. The 3 s relaxation time and equal added stiffness are explicit illustrative
choices. Compared this with original elastic/damped mechanics and half loaded
rest curvature plus doubled stiffness, preserving initial restoring moments.
The latter is a combined pre-existing rest-shape/stiffness hypothesis, not growth
or plasticity evolving during the trial.

All receive identical 100 Hz stage command histories: the prior approach/support,
a frozen command held for 1 or 12 seconds, continuous withdrawal and 15 further
seconds. The fruit stays attached and interacts through real cup contact. Actual
position is logged because command position and physical position differ under
finite stage stiffness. Each of six trials has an exact-command no-contact
control; a relaxing short trial is repeated at half the timestep.

Rejected v1 despite its plausible curves: untouched fruit drifted 0.106–0.228 mm
against a predeclared 0.10 mm limit. Preserved in commit 05d0147. v2 continues
gravity settling for 103 simulated seconds without pose/velocity resets or
material changes. The final 20-second settling window moves only 0.000045 mm.
Every repeated trial/control pair passes the unchanged limits; the largest
control drift is 0.000103 mm. Main-trial contact peaks stay below 0.203 N and
penetration below 0.0068 mm. The fine repeat peaks at 0.204 N / 0.0072 mm, has
no unintended contact, and differs in fruit path by at most 0.0048 mm.

With the improved baseline, long-hold cup force declines 14.21% for the relaxing
hypothesis, 0.11% for the original fixed springs and 0.23% for alternate rest
curvature plus stiffness. At one second after final contact, control-relative
stalk-tip height is +0.649 mm, -0.019 mm and -0.046 mm respectively. These are
model predictions that distinguish candidate laws, not observed plant properties.
Maximum actual stage drift during hold is 0.092 mm; instrument compliance must
remain part of identification. Short analytical observation-window examples
expose delayed-recovery/permanent-set ambiguity without asserting growth.

The first relaxing short rerun was interrupted solely to dispatch independent
cases concurrently; no completed data were discarded as unfavorable. The final
reports come from completed repeats. Exported two three-panel actual-pose videos,
six orbitable recordings, an initial-scene GLB, unclipped force/recovery plots,
compact results and reproducible source. Reviewed saved hold/recovery frames,
plots and browser loading/playback/view controls. Desktop product files were
not edited. Source, assumptions, failure history and evidence live in
assets/workcells/strawberry-specimen/recovery-study/v2/README.md.

The next priority remains one fruit/tool contact deformation experiment before
cutting or harvest-policy training: indentation, contact area, unloading and
rate dependence. Added relevant fruit-tissue compression leads without applying
excised-tissue or failure numbers as whole-berry parameters. Real calibration,
whole-plant morphology/anchorage and actual cutter interaction remain open.
