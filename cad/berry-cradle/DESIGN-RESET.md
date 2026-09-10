# Reject Cradle 01; resolve the manipulation mechanism first

User rejected revision A on 2026-09-09/10. Preserve it as a rejected experiment.
Do not resume PPO training with it merely because it is one valid STEP solid.

## Why the design is not accepted

The block, lofted neck and partially removed spherical bowl were assembled before
establishing a defensible working principle. Export validity, radii and nominal wall
thickness did not answer the important questions: how the fruit enters, which areas
carry its weight, how it stays retained during motion, and how the tool leaves a
cluster. The opening responded to one collision observed with a different crude
cup and was not sized from a verified clearance envelope. There is no damage model
supporting a claim that the hard bowl or rim safely contacts ripe fruit.

The static jaw-fit pictures only establish a geometric arrangement. They are not
proof of grasp stability with this CAD, manufacturability or useful harvesting.

## Focused primary research

- Xiong, From and Isler (2018), *Design and Evaluation of a Novel Cable-Driven
  Gripper with Perception Capabilities for Strawberry Picking Robots*:
  https://arxiv.org/html/1804.09771
  Their mechanism closes multiple fingers around the fruit, guides the stem to an
  enclosed cutter, and uses sensing to correct positioning. The paper explicitly
  treats fruit isolation and neighboring-plant interaction as design requirements.
  This is a mechanism reference, not validation of our geometry or an instruction
  to copy that complete device.
- Rajendran et al. (2022 preprint), *Peduncle Gripping and Cutting Force for
  Strawberry Harvesting Robotic End-effector Design*:
  https://arxiv.org/abs/2207.12552
  Separates stem gripping and cutting and experimentally studies the forces involved.
  Reported peduncle forces must not be used as fruit-body bruise thresholds.

## Proposed direction, not yet implemented

For the direct-joint PPO objective, investigate shaped compliant fingertip adapters
on the existing YAM parallel jaws. Opening, approaching, enclosing and maintaining
bounded contact would give all six arm joints plus the jaw a clear role. This would
replace passive underside support with a direct-grasp skill and therefore changes
the task; do not silently claim it is the previously evaluated experiment.

If passive support for a second-arm cutter remains the intended task, keep that
scope and first lay out the fruit entry path, support footprint and exit path. Do
not generate another bowl silhouette before demonstrating those three in context.

The next concept review must show fruit + actual jaws at common scale, open and
closed states or entry/support/exit states, contact areas, the neighboring-fruit
clearance envelope, proposed attachment and material/compliance assumptions.
Only then should another solid CAD revision and collision model be built.
