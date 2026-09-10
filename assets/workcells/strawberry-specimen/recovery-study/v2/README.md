# Stalk recovery: controlled material-hypothesis comparison

This experiment asks which measurements could distinguish different mechanical
explanations of the same loaded strawberry plant. It does **not** fit real
strawberry recovery data, infer growth from a photograph, or train a robot.

## Inspect the evidence

- [Orbit, pan and replay the six contact trials](index.html).
- [Short hold, three hypotheses at once](1s-hold.mp4).
- [Long hold, three hypotheses at once](12s-hold.mp4).
- [Force and recovery curves](recovery-comparison.png).
- [Why the observation window matters](observation-window.png).
- [All numerical comparisons](comparison.json), [protocol](protocol.json),
  [constitutive checks](constitutive-checks.json) and [settling](settling.json).
- [Research, applicability and missing measurements](research.md).
- [Proposed real measurement and validation plan](measurement-plan.json).

Videos show actual simulated poses at normal speed. The interactive viewer
replays recorded body transforms using unchanged body-local meshes. It does not
run the material solver in the browser. The scene geometry alone does not
encode the relaxing component; the Python source and saved states reproduce it.
The downloadable GLB uses this revision's shared initial pose. The unrelated
legacy push-test probe, collision-disabled in every trial, is omitted from the
exported review geometry; the active cup and connected stage remain visible.

## Competing hypotheses

| Case | Mechanical change | Interpretation |
|---|---|---|
| A | Original equilibrium springs and existing damping | Fixed rest shape, elastic response with damped dynamics |
| B | A plus a passive rotational Maxwell arm at 42 truss joints | One assumed delayed-recovery mechanism |
| C | Half the loaded joint rotation assigned as rest curvature, with twice the stiffness | A different pre-existing rest shape **and** stiffness, with the same initial restoring moments |

For B, the added spring equals the original spring, and its stress-relaxation
time is an illustrative 3 seconds. At a fixed joint rotation, its strain and
stored energy decay exponentially; the lost energy is nonnegative dissipation.
Its internal rest rotation evolves continuously by that constitutive law,
including in an untouched control. Solver callbacks only compute forces;
internal state advances once per integration step. Independent checks cover
noncommuting quaternion energy gradients, fixed-strain decay and scalar
standard-solid creep/recovery. These checks validate the mathematics implemented,
not the suitability of those constants for living tissue.

The inherited 45 MPa equilibrium truss modulus, Maxwell ratio/time and C's rest
fraction are uncalibrated assumptions. No spring rest references are adjusted
to produce a desired fruit pose during a trial. C does not grow or plastically
deform during the experiment. A and C also recover dynamically; their existing
damping should not be confused with B's additional time-dependent material law.

## Intervention and controls

The intact fruit remains attached. A visible concave cup physically contacts
it, transfers part of its weight to an actuated bench stage, holds, lowers and
withdraws. Every model receives the identical 100 Hz commanded stage path for
each hold duration. The command is frozen for 1 or 12 seconds, followed by the
same translated withdrawal and 15 seconds of further observation. Actual stage
position is dynamic because its actuators have finite stiffness. Force relaxation
therefore belongs to the coupled instrument–plant response, not an ideal fixed-
strain material test.

Each trial has an exact-command no-contact control. Recovery plots subtract
that model's control and align time to its final cup contact. Force plots use
20 ms samples; extrema and unintended contacts are audited every integration
step, so a brief peak need not appear in the plot. The relaxing short trial is
repeated at half the timestep. Residual recovery is an outcome, not something
adjusted to pass a preferred visual appearance.

## Why there is a v2

[v1](../v1/README.md) failed its predeclared 0.10 mm control-drift limit: its
starting plant was still settling slowly. That failed baseline is preserved in
commit `05d0147`. This revision continues actual gravity integration until a
quiet 20-second window, with at least 60 additional simulated seconds. Geometry,
masses, stiffness and damping are unchanged; no velocity or pose reset is used.
The resulting shared loaded state starts every material hypothesis. The original
control-drift, contact and convergence limits remain unchanged.

## Repeated-trial results

| Hypothesis | Hold | Cup force near hold start → end | Decline | Tip height 1 s after contact ends, relative to control |
|---|---:|---:|---:|---:|
| A: elastic + damping | 1 s | 0.1315 → 0.1315 N | 0.02% | -0.019 mm |
| B: added relaxing component | 1 s | 0.1540 → 0.1501 N | 2.55% | +0.436 mm |
| C: alternate rest + 2× stiffness | 1 s | 0.1761 → 0.1760 N | 0.03% | -0.043 mm |
| A: elastic + damping | 12 s | 0.1315 → 0.1314 N | 0.11% | -0.019 mm |
| B: added relaxing component | 12 s | 0.1540 → 0.1321 N | 14.21% | +0.649 mm |
| C: alternate rest + 2× stiffness | 12 s | 0.1761 → 0.1757 N | 0.23% | -0.046 mm |

These simulated response differences survive the improved initial equilibrium.
All six coarse trial/control pairs pass their declared comparisons. Their largest
control drift is 0.000103 mm, maximum target contact is 0.203 N, and maximum
tool overlap is 0.0068 mm. The largest hold-stage drift is 0.092 mm. Those are
numerical instrument/contact checks, not measured tissue tolerances. See the
full comparison report for every check. The half-timestep repeat also passes;
its maximum fruit-path difference is 0.0048 mm, maximum contact 0.204 N and
maximum tool overlap 0.0072 mm.

B's roughly 14.2% long-hold force decline and delayed tip recovery suggest
force-plus-motion measurements could distinguish it from A or C. This does
not establish that B describes a real strawberry or that one relaxation time
is sufficient. The instrument's finite compliance is part of these predictions.

## What remains unidentified

No accessible matching strawberry fruit-stalk load–hold–unload curve was found
in this search. A slow response within a finite window does not establish
permanent set; the analytical sensitivity figure illustrates that ambiguity.
The study compares two holds at one support-command amplitude on one plant.
It is not validation across plants, forces or unseen biological measurements.
The fruit is rigid, the crown is fixed, and flesh indentation, bruising, blade
cutting, root motion and long-term growth are not modeled here.

Next measurements should record intact-truss geometry, fruit masses, actual
support displacement/force, multiple holds and long recovery in two calibrated
views. Record organ dimensions, cultivar, maturity, hydration and temperature.
Reserve other plants, amplitudes and hold durations for validation. Separately
characterize fruit-body indentation and contact area before making claims about
gripper pressure or safe handling. Tissue properties from other organs or
failure tests cannot fill those gaps automatically.

## Reproduce

From the repository root, using Python with MuJoCo, NumPy, SciPy, Pillow,
Matplotlib and imageio/FFmpeg:

```sh
python tools/study_strawberry_recovery.py prepare
```

For each material `elastic`, `relaxing`, `retained` and hold `1`, `12`, run:

```sh
python tools/study_strawberry_recovery.py run --material elastic --hold 1
python tools/study_strawberry_recovery.py run --material elastic --hold 1 --control
```

Then:

```sh
python tools/study_strawberry_recovery.py run --material relaxing --hold 1 --fine
python tools/study_strawberry_recovery.py compare
python tools/render_strawberry_recovery.py plots
python tools/render_strawberry_recovery.py render --hold 1
python tools/render_strawberry_recovery.py render --hold 12
python tools/render_strawberry_recovery.py export
```

Source, compact reports and selected figures are committed. Large trajectory
arrays, generated meshes, browser pose recordings and videos remain local.
