# Strawberry work ledger

User direction: finish the deferred scientific-modeling work on this specimen, show the evidence, and record a reusable process. Desktop product work remains paused. A model can pass a numerical test while remaining biologically wrong.

## Dependencies and acceptance evidence

| Work previously discussed | Status at start of this iteration | Required next evidence |
|---|---|---|
| Multiple primary-source references, crown/root and whole-plant comparisons | Done; nine photos and three review plates | Continue comparing separate stages/conditions; never infer natural posture from a specimen held apart |
| Preserve sources, parameters, failed trials and checkpoints | v4 and basal v7 saved | Version every new input and store simulator/source/scene hashes |
| Fix crown attachment, tapered basal stiffness and numerical contact | v7 four probe/control pairs complete; basal timestep study complete | Recheck after anatomical changes; retain remaining truss/fruit penetration failures |
| Explicit parametric graph and evidence/assumption ledger | Previously proposed only | Compile editable anatomical/mechanical parameters into connected geometry, mass and contacts |
| Correct whole-stalk growth and leaf orientation | Review found early arching and downward tips | Gravity-settled comparison against v7 and real photos; unloaded vs loaded angle audit |
| Layered crown attachments and central growth | Simplified hub only | Stagger attached bases, add developing trifoliate growth, inspect self-contact and crown close-up |
| Continuous leaf mechanics | Isolated shell failed at first step | Stable shared-surface model, matched clamp/probe/control, strain and timestep tests; then integrate/export actual deforming vertices |
| Coherent variants and held-out interactions | Not done | Seeded linked changes, independent variant configs, target/control pairs at new approach angles; these establish simulated coverage only |
| Roots and compliant anchorage | Missing | Anatomy graph plus measured crown motion/soil support; fixed boundary must remain labeled until replaced/tested |
| Optical/camera match and quantitative morphology fitting | Approximate viewing directions only | Scaled multi-view specimen capture, camera calibration, annotations with uncertainty, held-out views |
| Force–deflection, recovery and contact calibration | No real observations | Execute the calibration protocol on real plants; separate fitting/test specimens; record uncertainty |
| Cutting, fracture, fruit retention and damage | Missing | Tool contact and physical separation tests; no timer-based detachment; force/displacement observations |
| Discretization, sensitivity and simulation cost | One basal timestep study only | Fresh-model throughput, segment/timestep response convergence, identify which uncertain parameters affect task outcomes |
| Reduced or learned mechanics | Research direction only | A trusted detailed/calibrated teacher, held-out errors and speedups, explicit validity range and fallback |
| Harvest policy on revised specimen | Not started | All task contacts represented, accessible observations, separate training/test distributions and task success/damage criteria |
| Turn methodology into app/skill/plugin | Deliberately paused by user | Demonstrate this manual loop first, then obtain user direction to resume productization |

## Current batch

Implement the parametric graph and canopy/crown hypothesis; preserve the rejected first candidate; settle the corrected candidate; run controlled contact trials; create reproducible morphology holdouts; save actual renders/replays and response/cost reports. Prepare a concrete physical-measurement protocol. Continuous surfaces, anchorage, cutting and real calibration remain separate work until their gates pass.

Do not mark the whole roadmap complete when this batch completes. Cellular/atomic simulations are an optional future escalation if task-relevant error cannot be resolved at organ/tissue scale. More detail and faster computation are not physical validation.

## Progress after this batch

- Implemented editable anatomy/material configuration, source/assumption records, graph checks and reproducible correlated variants.
- Improved canopy through explicit unloaded paths, corrected leaf frames, staggered crown attachments and age-dependent literature priors; v13 preserved separately.
- Completed eight probe/control pairs across three configurations; repeated basal timestep checks after changing stiffness. Full-scene settling penetration remains a failure to resolve.
- Built and tested an isolated continuous contact surface using articulated ribs and constrained shared vertices. Whole-plant integration remains pending; the original FEM shell remains rejected.
- Added actual-state review images, videos, standalone orbitable replay, control-relative response audits and a local simulation-cost measurement.
- Prepared the real calibration/held-out observation protocol. No real measurements have been executed.

The earlier table records the starting audit. This update and the chronological iteration notes record the actual work completed; the longer roadmap remains open.

## Fruit orientation / unloading follow-up

- v14 fixes a material-frame error at the calyx. COM and finite inertia already
  existed; an independent gravity/parallel-axis check now verifies them.
- Four release/control pairs (two rest-shape/stiffness hypotheses, two timesteps)
  record actual fruit fall and stalk/neighbor recoil with no pose/velocity reset.
- This is a labeled unloading diagnostic. The **cutting/harvest gate remains
  open**: no blade contact, fracture criterion or distal stalk remnant. Timed
  diagnostic release must not be reused as successful robot cutting.
- No growth evolution or calibrated viscoelastic recovery is implemented. The
  second hypothesis sets rest orientations and stiffness before the experiment;
  real unloading and longitudinal observations remain necessary.
- Contact penetration and fixed-root limitations persist. Reproducible visuals
  and assumptions: `assets/workcells/strawberry-specimen/fruit-study/README.md`.

## Selected next milestone — 2026-09-09

Derived from the user's request that the agent own critique and goal selection:
**make one fruit cluster credible under contact, support and unloading**, with
inspectable evidence of how load transfers to the tool and away from the stalk.
This is the next diagnostic toward robot harvesting, not a claim that the
current specimen or a complete harvest policy is ready.

First audit completed: recomputed contacts at recorded poses. The largest
release overlap (~2.27 mm) is the detached fruit hitting the ground at 1.175 s.
In gravity initialization, fruit/fruit overlap reaches ~1.08 mm and fruit versus
a neighboring stalk ~0.88 mm; leaf/leaf overlap is already ~0.45 mm in the first
saved frame. These are sampled maxima at 5 ms, not every integration step, and
the initialization transients must not be described as persistent settled
overlap. Evidence: `fruit-study/next-goal-contact-audit.json`.

Execution order and evidence:

1. Inspect those specific interfaces with visible collision surfaces and local
   dimensions; distinguish initial geometry errors from contact-compliance and
   initialization artifacts. Declare scale-aware numerical acceptance limits
   before tuning, without mistaking them for measured tissue compliance.
2. Build a controlled, contact-driven support/unweighting trial from the settled
   v14 candidate. The tool must visibly contact the fruit, transfer load and
   withdraw; preserve the full neighboring cluster and a matching no-contact
   control. This fills a missing interaction rather than adding another pose.
3. Log tool contact force, load transfer, fruit angle, stalk/neighbor movement,
   penetration, residual motion and energy where applicable. Inspect the entire
   trajectory from useful views; repair failures and verify timestep sensitivity.
4. Use evidence to constrain rest curvature, compliance and recovery assumptions.
   Seek relevant strawberry observations; keep unknown ranges explicit if real
   measurements remain unavailable. Do not invent calibration or quiet motion
   by changing spring references during unloading.
5. Show the recorded contact/support/recovery and compare with references. Choose
   the next experiment from the largest remaining task-relevant discrepancy.

Actual pedicel cutting, fruit retention, whole-plant leaf/anchorage refinement,
and learned robot execution remain on the broader roadmap. Do not prematurely
expand into the desktop app or claim all realism work is finished when this
diagnostic passes. User feedback can reprioritize the milestone without losing
the preserved v13/v14 work.

## Support milestone evidence — 2026-09-09

Completed the selected diagnostic with an intact truss, force-driven three-axis
test stage, visible/collision-matched concave cup, calyx load cell, matched
no-contact commands, actual-pose video and orbitable replay. v1 is retained as
a failure (neighbor contact and one-step floor/fruit penetration spike). v2
uses a narrower cup, connected shaft and explicit mesh floor without relaxing
the controller's predeclared acceptance limits.

The central case passes all 12 declared comparisons: about 76.56% of weight
transfers to the tool, peak target contact is 0.2163 N, overlap 0.0063 mm, and
final target displacement from control is 0.568 mm. All other berries remain
untouched by the tool but move through the common branch. A half-timestep repeat
changes the fruit path by at most 0.0154 mm. Two unchanged-controller ±2 mm
approaches and their matched controls also pass. These are tests on one model,
not learned-policy generalization or tissue validation.

### Next goal selected from the remaining uncertainty

The largest new consequence is now material identification, not the existence
of a contact load path. The rigid fruit cannot predict indentation or bruising;
the truss's scalar spring/damper model cannot establish real slow recovery or
growth-induced rest curvature. Prioritize a controlled load–hold–unload material
study, with partial support levels and several hold durations, before cutting
or training a harvest policy on this instrument. Compare alternative stiffness,
rest-curvature and relaxation hypotheses using identical intervention histories;
identify which observations distinguish them and which remain ambiguous.

Acceptance evidence for that next study: published/observed parameter ranges
with specimen and loading conditions, separated assumptions, time/force traces,
held-out intervention histories, convergence checks, and visible contact-area
and recovery differences. Actual real-plant calibration still requires the
prepared measurement protocol; simulation-generated curves cannot supply it.
Fruit contact compliance and stalk recovery are separate mechanisms and should
be tested separately before coupling. No such calibrated material model is
claimed complete by this support milestone.


## Recovery milestone evidence — 2026-09-09

Completed the uncalibrated material-hypothesis experiment, including six
contact/control pairs, independent constitutive checks and a half-timestep
repeat. v1's initial state failed the control-drift limit and is preserved.
v2 repaired the baseline through unchanged physical settling and passes the
original limits. Long-hold force relaxation remains about 14.2% in the assumed
Maxwell case versus less than 0.3% in the two fixed-spring alternatives. Actual
recordings, curves, numerical reports and a real measurement plan are at
`assets/workcells/strawberry-specimen/recovery-study/v2/README.md`.

This closes implementation/testing of a discrimination experiment, not material
identification from real data. A matching accessible strawberry fruit-stalk
recovery curve was not found or fitted. No biological parameter bounds, growth
law, tissue damage threshold or full-plant accuracy are established. Multiple
support amplitudes, held-out plants and measured intervention histories remain
required for validation; the two simulated holds do not supply that evidence.

### Next prioritized outcome

A physically deforming berry/tool contact with inspectable indentation and
contact-area change, first as an isolated nondestructive loading/unloading test.
Maintain this rigid-fruit baseline and the unchanged truss while checking the
new component separately. Use available strawberry tissue measurements only
within their specimen and loading scope. Compare contact force, displacement,
recovery and mesh/time refinement; add damage only with separate evidence.
Then couple the accepted contact component into the support trial.

Do not substitute more spring damping or contact penetration for modeled flesh
deformation, and do not describe a numerically stable grasp as bruise-safe.
The broader crown/root/leaf, multiple-specimen, cutter and learned-robot roadmap
remains open. Product UI work remains paused.

## Fruit outline correction — 2026-09-10

User rejected the long taper, then rejected the shorter version because every
fruit still repeated a perfect profile. V2's passed contact test did not establish
visual morphology. It is preserved at commit 956dc05.

V3 replaces the symmetric profile assumption with 18 digitized photographic
outlines from six cultivars (Nagamatsu et al., 2021, Fig. 1). Separate boundary
curves preserve unequal shoulders, taper and slice-centerline drift. Six 3D
examples show distinct observed contours with explicitly unobserved depth,
flattening and out-of-plane bending. The plant example interpolates within one
cultivar's outline family, rather than independently randomizing unrelated traits.

Method improvement: inspect source photographs, overlay the digitized curves,
project the actual generated mesh back onto its source view, inspect a quarter
turn, distinguish fitted evidence from latent assumptions, and compile the same
macroscopic surface into contact/mass geometry. Re-settle and run contact/control
experiments after physical changes. Appearance-only changes can reuse recordings
only after verifying unchanged compiled physical arrays.

Artifacts and uncertainty: `surface-study/v3/README.md`, `outline-analysis.png`,
`projection-fit.json`, `shape-audit.json`, `collision-fit.json`, and the fresh
neighbor/control results. The fitted-view score is not held-out evidence.
Single views do not determine hidden geometry; the terminal outline pixels and
calyx-end depression remain less reliable. Parameter slider edits are labeled
geometry previews and never alter the linked recorded physics.

Next acceptance evidence is paired/turntable views of the same fruit and a scale
reference, held-out-view shape error, and a correlated within-cultivar population.
Calibrated tissue response, maturity-dependent shape, calyx detail, net contact,
stem fracture, and PPO with the new tools remain open. No product-app changes.
