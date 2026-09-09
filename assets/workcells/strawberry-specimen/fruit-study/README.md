# Fruit orientation and unloading — 2026-09-09

Standalone simulation study; desktop product unchanged. v13 remains preserved.
v14 changes only the fruit attachment material frames.

## Evidence

- [Orbitable recorded physics](index.html#view)
- [Before / after orientation](fruit-orientation-comparison.png)
- [Actual release trajectories, real-time video](release-comparison.mp4)
- [Control-relative recoil curves](recoil-response.png)
- [Orientation, mass, COM and inertia](orientation-audit.json)
- [Independent finite-body gravity check](finite-body-check.json)
- [Release protocol](release/protocol.json)
- [Recoil and timestep comparison](release/comparison.json)

The movie disables a calyx attachment constraint at 1 s. It is an **unloading
diagnostic**, not a cutter, tissue-fracture or harvesting simulation. The event
changes no positions, velocities, masses, inertias, contact filters or material
parameters. Falling and subsequent interactions are solved by MuJoCo.

## Findings

The prior fruit already had mesh-derived COM/inertia. Its attachment frame was
the error: the calyx-to-apex axis initially pointed along local -Z regardless of
the terminal stalk tangent. The axes met at 42–64 degrees. v14 continues the
terminal stalk into the calyx in the unloaded material frame. Gravity, elasticity
and contact then determine orientation. No body is realigned while simulating
or rendering. A real nonzero gravity moment may be balanced by stem/contact
moments; vertical fruit orientation is not a universal acceptance criterion.

The primary fruit has mass 18.05 g and COM 15.54 mm below its attachment in its
own frame. Its settled angle from downward changes from 49.09 to about 4.8°.
An independent ball-joint model with this mesh/calyx matches an analytical
gravity-torque/parallel-axis angular acceleration to about 6e-14 rad/s². This
verifies mechanics wiring, not biological mass-distribution calibration.

## Same loaded pose, different unloading

Two **uncalibrated hypotheses** start in exactly the same pose and velocity:

- A keeps the original truss spring rest configuration and stiffness.
- B assigns half the initial truss-joint rotation to its spring rest orientation
  and doubles that joint's stiffness **before** the trial starts.

B preserves A's initial spring moments to <7e-18 in generalized-force units.
Changing **both rest curvature and stiffness** preserves the initial loaded pose
while changing unloading. This exposes non-identifiability; it does not isolate
growth alone. The fraction is not measured, and no growth law is integrated.
Both models keep their respective rest orientations fixed during each trial.
Time-dependent creep and slow recovery have not been implemented.

Relative to their matching uncut controls, mean stalk-tip rise in the last 0.5 s
is 19.71 mm (A) and 11.39 mm (B). Peak three-dimensional tip displacement is
37.92 and 28.41 mm. Vertical rise and total recoil are different quantities.
The run ends 3 s after release; final equilibrium is not asserted.

Four release/control pairs cover both hypotheses at timesteps 0.125 and 0.0625 ms.
No warnings occurred; paired histories match exactly before release. Refinement
changes final tip rise by 0.00245 / 0.00026 mm; maximum response-curve difference
is 0.0584 mm. Attached translational weld error stays below 0.00034 mm. Angular error is
0.0185° or less; the initial 0.03 torque-scale weld failed a 0.1° tolerance
(measured 0.1996°). Its recordings remain in `release-soft-weld`; only the
numerical weld torque scale was raised to 0.1 before repeating every pair.
Total model mass is identical before/after the topology representation change.

## Unresolved limits

- v14 settling still reaches 1.18 mm berry/trough and 1.09 mm berry/berry
  penetration. Sampled release-trial penetration reaches about 2.3 mm. Timestep
  agreement does not validate contact compliance or resolve these errors.
- Homogeneous fruit mesh plus calyx masses; no measured density heterogeneity,
  flesh deformation, bruising or maturity-dependent material law.
- Scalar stalk ball-joint stiffness does not distinguish bending from torsion.
  The calyx remains bonded; no loose bearing is added. Local compliance is unknown.
- Calyx release leaves no distal stalk remnant. Cutting above the calyx requires
  different separation topology, blade work/contact and calibrated fracture.
- Crown fixed; roots/soil compliance absent. Existing leaf-panel limitations persist.
- No real strawberry unloading observations or fitted growth/recovery parameters.

## Research and next measurements

[Cal Poly anatomy](https://strawberrycenterblog.com/2025/12/15/strawberry-anatomy-part-3-leaves-and-stems/)
guides checking the pedicel/calyx connection. Exact local curvature is assumed.

[Ray & Bret-Harte 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6370663/)
experimentally separate immediate elastic, delayed recoverable and irreversible
bending in woody branches. Those mechanisms motivate separate state variables;
their measurements are not transferable strawberry pedicel constants.

[MuJoCo weld documentation](https://mujoco.readthedocs.io/en/stable/XMLreference.html#equality-weld)
defines the switchable attachment. Stalk elasticity remains active after release.

Record the same truss from two directions with a scale reference; weigh removed
fruit; film controlled unloading/cutting at high frame rate and observe recovery
for minutes. Compare reversible support/unweighting with cutting, documenting
support/cutter forces and neighboring contacts. Growth-induced rest curvature
needs longitudinal or independent unloaded-shape/material observations. Fit one
group and test held-out plants; do not choose rebound by appearance alone.

## Reproduce

Tested with MuJoCo 3.12.0, NumPy, SciPy, trimesh, Pillow, Matplotlib and imageio.
From repository root:

```sh
python tools/parameterize_strawberry.py --config tasks/strawberry_specimen/parametric/canopy-v14-fruit-frame.json --output assets/workcells/strawberry-specimen/fruit-study/v14/reference-input.json
python tools/build_strawberry_specimen.py --spec assets/workcells/strawberry-specimen/fruit-study/v14/reference-input.json --output assets/workcells/strawberry-specimen/fruit-study/v14
python tools/test_strawberry_specimen.py --model-dir assets/workcells/strawberry-specimen/fruit-study/v14 --kind rest
python tools/study_strawberry_fruit.py audit
python tools/study_strawberry_fruit.py prepare
python tools/study_strawberry_fruit.py run
python tools/study_strawberry_fruit.py run --control
python tools/study_strawberry_fruit.py run --history 0.5
python tools/study_strawberry_fruit.py run --history 0.5 --control
python tools/study_strawberry_fruit.py run --fine
python tools/study_strawberry_fruit.py run --fine --control
python tools/study_strawberry_fruit.py run --history 0.5 --fine
python tools/study_strawberry_fruit.py run --history 0.5 --fine --control
python tools/study_strawberry_fruit.py compare
python tools/study_strawberry_fruit.py attachment-check
python tools/render_strawberry_fruit.py
python tools/export_strawberry_fruit.py
```

The audit and comparison renderer also need the preserved v13 scene/settle
rollout. Rebuild with `canopy-v13.json` using the same build/settle commands if
those local assets are absent. Large XML, rollout, replay, mesh and video files
stay local; source, configs, compact reports and selected stills are versioned.
