# Environment design review and synthetic observation pilot

Three sequential image reviews informed changes to crop geometry. The original successful harvesting checkpoint remains unchanged.

1. Narrow gutter: a 560 mm-wide, 85 mm-deep open channel replaces the bulky trough. Initial image review: exposed fruit, but sparse canopy and overly regular straight hanging branches. Next change: individual growing pockets and curved botanical branches.
2. Modular pockets: separate polygonal containers and fuller foliage. Initial image review: clearer plant identity, but all pockets still line up; catcher wall still blocks part of the wrist view. Next change: stagger height/depth and introduce near-fruit foliage.
3. Staggered bays: six-sided pockets at different heights/depths, curved branches and leaves near the fruit. Review: a better candidate for varying approach and visual occlusion; still stylized, sparse and not botanically calibrated. The unchanged catcher still obscures its receiving area. This is a preferred design direction, not a validated harvesting improvement.

## Measured trials

Each design was reset with seed 11 and evaluated with the existing scripted state-feedback controller for 50 simulated seconds. All three collected 0/3 fruits and stalled before cutting. Initial reset IK residuals were small; that does not establish feasible dynamic execution. These complete failure traces and actions are retained. No policy was trained or improved in this experiment.

## Diversity review

An initial nine-sample random batch accidentally clustered gutter widths. Eight samples passed the narrow clearance/reset gate; seed 7104 was rejected for an IK residual above the unchanged 0.001 threshold. This batch remains in batch/.

The reviewed batch in batch-stratified/ deliberately spans approximately 460, 590 and 720 mm widths; depths approximately 85–145 mm; top heights 445–490 mm; three layouts; different fruit positions/heights; and canopy density/placement. These are design-exploration bounds, not measured agricultural distributions. All nine stratified samples passed the same initial fruit-to-planter clearance (>10 mm), reset residual (<0.001) and finite-state 25-step checks. This limited gate is not a full collision, force, motion or safety verification.

## Synthetic observations

For each stratified sample: a fresh 25-step/0.5 s simulation smoke episode; qpos/actions; synchronized 512 x 288 RGB, ideal depth in metres, and object-ID segmentation for both official D405 wrist mounts; camera world transforms, nominal intrinsics, scene hash, geometry label map, and qpos/qvel/timestamp. The review previews depict the initial state; the sensor dataset is captured at 0.5 s. Images are simulator renders, not image-generated substitutes.

This is 18 synchronized wrist RGB observations across nine configurations, not a large demonstration dataset. No calibrated depth noise, distortion or motion blur is applied. Connecting botanical branches and foliage are visual-only approximations. Collection-tool occlusion remains visible. The non-contact canopy should not be used to claim collision-aware leaf manipulation or reliable sim-to-real transfer.

## Next rubric

Before increasing dataset scale: diagnose the cutter/controller stall on varied targets; measure tool retention and target visibility through the entire approach; reject fruit/planter and tool/fixture intersections; record outcomes under fixed criteria. Add constrained scene yaw, fruit-size variation and calibrated camera/actuator uncertainty only with explicit ranges and checks. Keep training and held-out configurations separate. Do not relabel smoke checks as successful task execution.
