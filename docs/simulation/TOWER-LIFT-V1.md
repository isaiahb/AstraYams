# Tower and shared lift workcell

2026-09-10. New workcell branch `codex/tower-lift-so101`; previous YAM harvesting
assets, environments, recordings and policy weights are preserved.

## User observations and supplied dimensions

The user supplied three photographs: an empty planting tower, a tall central
lift in an extrusion frame, and a bench with two small arms beside a planted
tower. The user subsequently specified **6 ft high × 4 ft wide** for the outer
frame and triangular cross supports in the middle for the lift. We use exactly
1.8288 m × 1.2192 m. We interpret the bracing as rear-plane crossing diagonals and
carriage shelf gussets. Brace endpoints, extrusion size and bearing details remain
unmeasured. Both arms are placed on one shared moving carriage as the stated
working assumption; the user has not separately confirmed that arrangement.

The source photos remain local under `runs/tower-lift-v1/references/` and are not
committed. They are layout references, not biological calibration data.

## What is implemented

- `configs/tower_lift_v1.json` separates user-supplied dimensions from estimates.
- `tools/build_tower_lift.py` builds valid parametric CAD solids and individual
  STEP files for extrusions, carriage, shelf, gussets, adapter blanks, open tapered
  planting pockets, central tube, reservoir envelope and pulleys. The support STEP
  assembly also includes the rear braces, motor envelope and belt envelope.
- A shared finite-force slide moves both robot bases and the shelf. Two separate
  MJCF scenes use either two SO-101 arms or two YAMs. The frame/tower are anchored;
  this does not evaluate tipping or structural compliance.
- SO-101 assets are unmodified upstream imports pinned at
  `eecbe3e0a9ebb23e25ad7b2759b03884c6660903`, from
  [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100/tree/eecbe3e0a9ebb23e25ad7b2759b03884c6660903/Simulation/SO101).
  Apache-2.0 license, attribution and individual source hashes are preserved.
  Workcell-generated copies change visual plastic to white, namespace each arm
  and restore base collision meshes. Convex collision meshes are conservative;
  they are not a validated precision-grasp model. The upstream motor parameters
  are modeling priors, not identification measurements from the photographed arms.
- YAM models come from the existing official-asset environment. Their joint limits,
  masses and finite 10 Nm / 30 N motor limits are retained. The new commissioning
  controller adds finite-force PD position servos with explicitly chosen gains.
  SO-101 has five arm hinges plus its hinged gripper; YAM has six arm joints and
  its coupled linear jaws. Action spaces are therefore 13 and 15 respectively,
  including the shared lift. No cross-embodiment policy-weight transfer occurs.
- The V4 strawberry specimen retains its articulated leaf/stalk joints, masses,
  inertia and elastic/damping priors. It is re-anchored to a tilted pocket and
  evolves under gravity/contact. Existing trough/substrate/probe are omitted.
  One specimen is present; empty pockets do not represent domain randomization.
- Pocket wall and bottom collision sectors retain a real open mouth and bottom
  drain hole. A whole-cup convex hull would wrongly close those openings.
- `TowerLiftEnv` is a Gymnasium control/clearance environment. It applies rate-limited
  actuator setpoints, never sets robot poses during `step`, and checks non-finite
  state, warnings and simulator-clock resets. Its reward is zero and
  `harvest_success` is null because a new harvesting task is not implemented yet.
- The standalone cel-shaded review switches robot embodiments, orbits/pans/zooms,
  scrubs recorded physics and provides individual CAD downloads. The desktop
  product application was not edited.

## Commissioning and inspection

Both arms hold a parking posture while the shared lift rises approximately 0.12 m
and returns. This is a scripted motor test, not PPO or harvesting. Five and a half
seconds are simulated at a 0.125 ms integration timestep. Per-embodiment reports
record actual lift position and force, robot contact/overlap and simulator warnings.
See the tracked `tower-lift-v1-commission.json` beside this document.

Initial import checks caught a YAM visual finger mesh inadvertently made collidable;
the importer now respects visual-only geometry. An overlapping closed-finger start
was replaced by an open parking posture, retaining opposing-jaw contacts and all
other collision checks. No collision-force threshold was relaxed to obtain a pass.

Three tests cover distinct control dimensions, finite force limits, rejection of
non-finite commands, passive falling when the lift actuator is disabled despite
an upward command, and the recorded commissioning results. Visual review includes
the whole frame, arms/plant, side views and both robot variants. A short lift test
does not validate the entire travel range, reachability or any harvesting action.

## Scope of the next mechanical iteration

The new arms carry stock jaws. The previous YAM cutter/catcher tools and trained
harvest remain available in their original workcell. Adapter blanks in the new
support assembly do not constitute verified bolt patterns, fastening or payload
design. SO-101's hinged jaw needs an actual cutter/catcher interface design;
attaching the existing YAM tool by an invisible weld would not establish a fit.

All dimensions other than outer height/width are estimates: 1.56 m tower height,
8 tiers, 0.17 m tier pitch, 28° pocket-axis inclination, 20 mm extrusion, frame
depth, crown seating and arm spacing. The 350 N lift force limit and 0.08 m/s
command limit are unmeasured commissioning priors, not the real lift's ratings.
The belt graphic does not simulate belt stretch, slip, backlash, voltage/current
or gearbox behavior. The holder/crown connection is fixed with an explicit
holder-to-crown contact exclusion; holder compliance/root restraint needs data.

The rotated mature specimen is a transplantation hypothesis. It is **not** a
plant generated by calibrated growth at that angle, and it does not resolve fruit
tissue damage. The earlier fruit-contact convergence failure remains unresolved.

Next concrete outcome: verify carriage/guide arrangement and crown-holder geometry
against measurements; then evaluate each arm's reach and collision-free approach
to several tier targets. After that, design and mechanically verify stock-jaw tool
adapters, define a task/reward, and train new embodiment-specific skills. Keep the
plant growth and damage calibration work tracked separately from this layout.

## Reproduction

```sh
python tools/fetch_so101.py
PYTHONPATH=src python tools/build_tower_lift.py
PYTHONPATH=src python tools/review_tower_lift.py
PYTHONPATH=src python -m unittest discover -s tests -p 'test_tower_lift.py' -v
```

Review: `http://127.0.0.1:8793/runs/tower-lift-v1/index.html`.
Generated models, STEP, recordings and photos live in ignored `runs/` directories.
