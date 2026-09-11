# V9: supported single-pack shelf and passive net-floor prototype

The shelf remains a useful direction. The passive gate is **not release-ready**.
A free tool can hold a falling test berry in the net, but the release experiment
opens the floor only about 55.5 degrees, shifts the tool in its jaws, and brings
the berry back up. This is a mechanical commissioning result, not a PPO result.

## Preserved and changed

V7 direct, stacked SO-101 mounts and V8 remain preserved. No robot lifts a filled
clamshell. The carriage carries the container through the shelf and carrier.
The V9 shelf moves 10 mm inward and 40 mm down. These are design changes, not new
measurements of the photographed rig. The container remains the approximate
123 × 186 × 81.8 mm catalog envelope from the V8 study, not supplier CAD.

A new hinged floor carries a woven net. A transverse hex shaft connects the
floor to a lever outside the container. A shelf-mounted roller pushes the lever;
a torsion spring returns the floor. The revised axis is 5 mm below the rim datum,
and the lever extends about 46 mm behind the shaft. The STEP files contain the
frame, ears, moving ring, shaft, bearings, lever, roller, post and foot.
Spring hardware, travel-stop hardware, shaft retention and roller axle details
remain unfinished. The simulated hinge and spring are engineering abstractions.

## What the experiments established

- The fixed CAD attachment was replaced with a **free tool** in jaw contact.
  There is no tool weld and no runtime assignment of its pose.
- The textile uses connected flexible strands with shared crossing nodes,
  gravity, finite mass and elastic/damping forces. It is not an invisible bowl.
- The berry reuses the specimen's skin/achene/calyx assets. It has 18 g mass and
  inertia from the skin's convex hull. It is loaded by gravity in an isolated
  test; this is not a recorded clipping/harvesting episode.
- The corrected stationary hold at 0.25 ms steps has about **0.089 mm** maximum
  sampled grip translation error. At 0.125 ms it is **0.086 mm**. Both retain the
  berry. This checks numerical consistency, not calibration against hardware.
- The initial gate had about 109–111 mm³ rigid interference at its hinge.
  Lowering the axis removed intersections between the floor/lever and the
  frame/ears at all **8 sampled angles from 0 to 105 degrees**. This is a sampled
  exact-solid check, not a continuous-motion or structural certification.
- The corrected release test has **13.44 mm tool shift**, **11.14° tool rotation**,
  a maximum floor angle of **55.51°**, and does **not** leave the berry in the pack.
  Its sampled net/fixture contact peak is 12.23 N. The container lip, floor and
  net geometry must be evaluated together; pushing deeper is not a solution.
- Increasing jaw torque from 0.35 to 0.7 or 1.2 Nm did not cure the original
  release failure. A 3 mm torsional-contact-length sensitivity test did not cure
  it either. Do not tune friction until an intended animation appears to work.

All force maxima currently come from 50 Hz logging. They can miss short peaks
and cannot establish bruise safety. No contact-force threshold has been relabeled
as a validated fruit-damage threshold.

## Setup defects discovered and corrected

1. A duplicate drop-test berry initially overlapped a frozen neighboring berry.
   The packing bench now removes the crop/tower assembly explicitly. The original
   growing environment is preserved elsewhere.
2. The imported fixed robot base and shoulder collision envelopes overlapped at
   their intended mechanical interface. An explicit adjacent-body exclusion was
   added for each base/shoulder pair; arm-to-arm collision stays enabled.
3. The first cutter retreat physically hit the net. That failed transport is
   preserved. The isolated release bench starts the cutter in a separately
   searched pose clear of the lower arm's sampled test positions. This is not
   proof that the cutter can retreat there safely after a cut.
4. A single convex carrier collision mesh filled its hollow recess. It was
   replaced with a base and four wall pieces. The clamshell also has separate
   tapered wall and floor contacts. Covered base slots, vents and small rounded
   corners remain approximations.
5. The inherited ground mask omitted the new berry/tool/textile groups. It now
   admits them, and a separate gravity-drop test checks ground contact.

## Collision and material limits

The jaw and fixed net-frame meshes use CoACD decomposition. The 48-hull cap did
not meet the requested 0.5 mm concavity target for all meshes. That number is a
request, **not a measured collision-surface accuracy**. Grip pressure distribution
and torsional resistance remain especially uncertain. Official references:
[CoACD](https://github.com/SarahWeiii/CoACD) and
[MuJoCo contact parameters](https://mujoco.readthedocs.io/en/stable/modeling.html#contact-parameters).

Current priors: 1.5 g textile, 60 N/m edge stiffness, 0.015 Ns/m edge damping;
gate 0.006 Nm/rad with 0.016 Nm closing preload; 0.35 Nm hold clamp and 0.7 Nm
release clamp. These are disclosed simulation choices, not measured SO-101 or
food-contact material properties. Arm servos retain finite actuator limits.
Lift/counterweight coordinates are frozen only for this isolated packing test.

## Reproduce from the preserved project assets

Use the project CadQuery/MuJoCo environment with `PYTHONPATH=src`:

1. `tools/build_single_pack.py --out runs/tower-lift-v9 --inboard-mm 10 --drop-mm 40`
2. `tools/packing_collision_parts.py` (requires CoACD; preserves the manifest)
3. `tools/build_packing_gate_bench.py`
4. `tools/plan_packing_commission.py` (diagnostic offline IK, not a learned policy)
5. `tools/setup_packing_release.py`, then `tools/park_packing_cutter.py`
6. Run `tools/commission_packing_gate.py` with the chosen initial state/plan,
   grip cap and timestep; each new run saves its inputs and scene hash.
7. `tools/export_packing_gate_cad.py`, `tools/audit_packing_gate_cad.py`,
   `tools/summarize_packing_commission.py`, `tools/review_packing_gate.py CASE...`

The orbitable review is `/runs/tower-lift-v9/gate-bench/index.html`.
Earlier geometry/test snapshots are `gate-bench-v1` / `cad-v1` and `gate-bench-v2`.
Generated runs are local artifacts; source and compact evidence are committed.

## Next mechanical decision

Keep the carriage-supported pack. Redesign the tool interface to resist rotation
geometrically, or let a dedicated docking fixture take the gate actuation loads.
Evaluate side actuation or a controlled release/reset latch so opening does not
require lowering the moving floor into the bottom of the container. Re-test a
single complete release before spending tokens on training. Then commission the
cutter retreat and lower-arm transport together, including inter-arm clearance.
