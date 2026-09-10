# Catcher + jaw-driven stem shear — mechanism study B

Confirmed user direction, 2026-09-10: one YAM holds a soft cup/net below a berry;
the second YAM uses its existing jaw motion to sever the selected peduncle with
a precision cutting attachment. No fruit grasp, scooping or independently powered
scissor actuator is intended.

## What this revision establishes

This is a parametric solid-CAD mechanism study with actual YAM finger meshes for
scale and fit review. It is not a learned rollout or a production release.

- Catcher: a complete oval rim, separate bolted retaining ring, replaceable net
  pouch, and a flat grip handle. The textile surface is shown separately from
  rigid CAD; the rendered sag is an assumed rest shape, not a solved drop test.
- Cutter: opposed, replaceable bypass blades on two finger-mounted carriers.
  The stock parallel jaws provide the entire cutting stroke. Each blade follows
  its own finger; no new actuator or animated independent blade motion.
- Proposed clamping shoes surround the distal finger envelope. Their dimensions
  come from the supplied mesh, while liner compression, preload, tolerances,
  blade alignment and allowable jaw force remain engineering assumptions.
- Show the stem between the blade tips and the catcher beneath the fruit at one
  scale. Open/closed CAD states explain the mechanism; they do not simulate
  stem fracture or demonstrate successful harvesting.

## Evidence and limits

The earlier fixed-wrist support PPO scored 11/12 on its holdout. Its crude,
gripper-held successor scored 0/3 development trials. Neither result applies to
these tools or the new cut-and-catch task. No new PPO was trained for this revision.

Rajendran et al., *Peduncle Gripping and Cutting Force for Strawberry Harvesting
Robotic End-effector Design* (2022 preprint), separates stem gripping and cutting
and measures blade/stem interactions: https://arxiv.org/html/2207.12552 . Its
specific cultivars, blade and slow test motion do not establish our required
cutting force or a bruise threshold. Nominal aperture dimensions here are design
choices, not experimentally fitted agricultural specifications.

## Next acceptance evidence, before training

1. Verify mounting and blade clearance throughout the actual jaw stroke. Include
   tolerances, fastener access, blade stiffness, finger loads and camera sightline.
2. Bench model: drive only the YAM gripper actuator; measure transmitted blade
   displacement/force. Do not remove a stem on a timer or distance test alone.
3. Net drop tests: fruit mass/shape, drop height, net tension, stretch and damping;
   compare peak force, rebound and retention across timestep refinements. No
   bruise-safety claim without a measured damage criterion.
4. Then train coordinated joint-level PPO skills for catcher placement/holding
   and cutter approach/alignment, followed by cutting and transfer. Evaluate
   unseen stem poses and neighboring fruit. Preserve failures and exact models.

## Checks completed in this revision

- 26 valid rigid component solids, each exported to STEP and re-imported with
  volume error below 0.01 mm³. Combined STEP re-import: valid, 26 solids.
- Opposing cartridges checked at nine positions from 7 to 3 mm per-jaw offset:
  zero cross-cartridge volume intersections. The first version failed because
  inward-facing screw heads collided. Screws now enter from the outside.
- Carrier versus blade and carrier versus clamp-cover intersections are zero
  on both sides. Blade seats were recessed so the blades rest on the carrier.
- Actual source YAM meshes inspected in assembled, isolated, top and closed
  views. The two clamp plates are tapped aluminium concepts. Nominal blade
  separation is 0.04 mm; this is NOT a demonstrated achievable tolerance under load.
- Net fibers extend into the ring flange. Its rest surface, 2.5 mm mesh pitch,
  strand thickness and material response are design assumptions.

These are nominal geometric checks, not grasp, structural, cutting or damage
validation. The opposing blades are parallel bypass shears, not pivoting scissors.

## Reproduce

Dependencies: Python 3.12, CadQuery 2.8.0, trimesh 5.1.0, numpy; rendering also uses
MuJoCo 3.12.0 and Pillow. Run `python build.py`, then `python render.py` from this
directory. Serve the repository root to use `index.html`; its viewer uses the
existing local Three.js installation in `apps/skill-studio/node_modules`.

Official YAM STL files and their local translations are read directly from this
repository; upstream attribution is in `assets/robots/yam/SOURCE.json` and LICENSE.
`reference/berry.stl` preserves the earlier isolated coarse reference. The live
viewer now reads `specimen-source.json`, which points to the shared full plant's
settled meshes and physical pose. The plant is translated as one assembly; the
fruit is not positioned independently of its stalk. The current profile family,
shape assumptions, rebuilt COM/inertia and new contact recordings are linked
from that manifest. Only the nominal CAD tool layout is repositioned.

The earlier standalone assembly images preserve the original design study;
the live full-plant viewer is the current context review. The STEP assembly
contains the rigid new tools; textile and imported robot/plant meshes are
separate preview geometry. No prior training run is needed to rebuild the tools.
