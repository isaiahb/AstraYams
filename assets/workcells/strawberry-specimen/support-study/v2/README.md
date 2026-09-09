# Intact fruit support and recovery

Standalone simulation evidence, 2026-09-09. Desktop product development remains paused.

- [Orbitable recorded poses](index.html#view)
- [Full motion, two cameras and measured loads](support-review.mp4)
- [Force and control-relative response](support-response.png)
- [Predeclared protocol](protocol.json)
- [Support/control checks and timestep comparison](comparison.json)
- [Orientation and stage motion audit](motion-audit.json)

## What causes the motion

An ideal three-axis prismatic test stage drives a small concave support cup under
an intact strawberry. The force-limited position actuators move the stage;
contact forces move the fruit and its connected stalks. The controller uses
measured tool/fruit contact force, with a target of 80% of the fruit's weight.
It then lowers and withdraws. The fruit is never attached to the tool, and no
plant positions, velocities, spring references, masses or inertias are reset
during the episode. The calyx stays connected throughout.

This is a **virtual laboratory instrument**, not a complete physical stage
design, YAM arm, learned policy or harvesting end effector. Ideal prismatic
constraints represent the internal guide interfaces. Their internal contacts
are excluded; all external instrument/plant contacts remain active. Initial
alignment uses the known simulated fruit pose. It is not a vision solution.

The cup comprises an explicit convex floor and 20 convex wall sectors. Those
same surfaces are rendered and used for collision. Its outer diameter is 16 mm.
The inner/outer wall radii and floor geometry are chosen for clearance, not
fitted to fruit deformation. The fruit remains a rigid finite-mass body.

## Findings on the central approach

- Fruit mass: 18.05 g, weight 0.17707 N. Before contact the calyx load sensor
  measures 0.17707 N upward, independently checking the load path and sign.
- During the hold the cup carries 76.56% of the weight; the stalk carries 23.46%.
  The closed-loop response has not fully reached the 80% target in this short
  trial. It is not labeled as exactly 80% support.
- Peak contact force over **every integration step**: 0.2163 N. Maximum
  cup/fruit overlap: 0.0063 mm. No unintended instrument/plant contacts.
- Mean stalk-tip rise versus control: 8.81 mm. The other berries move by up to
  10.74 mm through their shared branch. The cup does not touch them.
- Primary fruit orientation changes by up to 11.11 degrees. No orientation
  corrections are applied during simulation or rendering.
- During the final 0.5 s the fruit is within 0.568 mm of the control trajectory,
  with no tool contact. This is a finite observation interval, not proof of
  complete asymptotic recovery.
- Newton-law residual during the smooth hold: at most 0.000111 N, comparing
  independently logged contact/stalk forces with differentiated COM velocity.
- Timestep 0.125 → 0.0625 ms: maximum fruit-path difference 0.0154 mm and
  mean hold support-force difference 0.00000285 N. Both runs have zero warnings.

The matched negative control starts from **identical positions and velocities**
and replays **identical recorded motor commands** with instrument contacts
disabled. The stalk keeps carrying the full fruit weight. Any tool/fruit
intersection shown in that explicitly labeled control is intentional; it is
not presented as successful physical handling.

Two additional approaches shift the entire initial cup path by ±2 mm in X,
with the same controller, plant, target load and acceptance criteria. Each has
its own identical-command no-contact control. All declared checks pass:

| Approach offset | Mean weight supported | Peak contact force | Final deviation from control |
|---|---:|---:|---:|
| −2 mm | 76.56% | 0.1935 N | 0.561 mm |
| 0 mm | 76.56% | 0.2163 N | 0.568 mm |
| +2 mm | 76.65% | 0.2655 N | 0.639 mm |

All three approach recordings are available in the orbitable viewer. This is
limited controller tolerance evidence on one simulated plant, not policy
learning, a morphology holdout or established real-world generalization.

## Failed first trial retained

v1 touched a neighboring berry during approach. It also reported a single-step
22.87 N, 4.22 mm-deep cylinder-floor/fruit contact during withdrawal, missed by
the 5 ms saved force samples. Exact-command replay reproduced it at 8.99925 s;
recomputing contact at the post-step state returned no floor/fruit contact.
See [the failure report](../v1/support/result.json) and
[event diagnostic](../v1/peak-diagnostic.json).

v2 narrows the cup, connects its visible support shaft, and replaces the
analytic cylinder floor with an explicit convex prism. The controller and
predeclared force/penetration/recovery limits remain unchanged. The spike did
not recur in the central or refined run. These combined geometry changes do
not isolate a simulator root cause; no engine bug is claimed as proven.

## What remains uncertain

Passing these checks establishes a coherent simulated interaction. It does
not validate real strawberry mechanics or safe fruit handling. In particular:

- The force budget is a predeclared **numerical diagnostic limit**, not a
  measured bruising threshold. A rigid berry contacting a rigid small cup cannot
  predict contact area, flesh strain or damage.
- Truss stiffness, rest curvature, damping and torsional response remain
  uncalibrated. A settled photograph cannot identify their unloading behavior.
- The crown is fixed, roots/soil compliance absent, and leaf-panel limitations
  persist. Larger overlaps during original gravity initialization and dropped
  fruit/ground impact remain separate failures; this trial starts after settling.
- No cutting, fracture, stem remnant, growth law or learned robot control.

## Research and reusable method

[Rajendran et al., 2022](https://arxiv.org/html/2207.12552) distinguish attachment,
detachment and transport and investigate peduncle gripping/cutting. That work
motivates separating these tests. Its peduncle forces are **not** imported as
fruit-body support or damage constants. Local anatomy references and source
credits remain in the specimen's [fruit study](../../fruit-study/README.md).

For a real matched experiment: record a scaled stereo view of an intact truss,
measure fruit mass, approach with an instrumented support at known speed, log
support force and several stalk/fruit landmarks, then withdraw and observe fast
and delayed recovery. Repeat partial load levels and approach offsets. Fit
stiffness/history/damping using one group of plants and test on another.

Method learned here: audit the settled contact state; isolate one load path;
verify sensor conventions against gravity; declare bounds; record every-step
contact extrema in addition to replay samples; inspect the full instrument and
neighboring objects; retain a same-command no-contact control; check timestep
sensitivity and unretuned approach perturbations; show actual poses and the
limits of what the evidence establishes.

## Reproduce

Requires the v14 scene and settled rollout; rebuild them using the first three
commands in the [fruit-study instructions](../../fruit-study/README.md).

```sh
python tools/study_strawberry_support.py prepare
python tools/study_strawberry_support.py run
python tools/study_strawberry_support.py run --control
python tools/study_strawberry_support.py run --fine
python tools/study_strawberry_support.py compare
python tools/render_strawberry_support.py
python tools/render_strawberry_support.py --export
```

Offset cases use the same geometry/controller/criteria:

```sh
python tools/study_strawberry_support.py prepare --output assets/workcells/strawberry-specimen/support-study/offset-plus2 --offset-x-mm 2
python tools/study_strawberry_support.py run --output assets/workcells/strawberry-specimen/support-study/offset-plus2
python tools/study_strawberry_support.py run --output assets/workcells/strawberry-specimen/support-study/offset-plus2 --control
python tools/study_strawberry_support.py compare --output assets/workcells/strawberry-specimen/support-study/offset-plus2
```

For the opposite offset use `offset-minus2` and `--offset-x-mm -2`.
Large XML, rollouts, meshes, GLB, replays and movies stay local. Source, protocols,
compact results and selected review images are versioned. v1 is reproducible
from commit `dbff206`; v2 and the earlier v13/v14 scenes are separate checkpoints.
