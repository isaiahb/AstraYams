# Articulated YAM keyed insertion

This task imports the official `assets/robots/yam/v1/yam.urdf`, preserving all six revolute-joint transforms, ranges, link inertias, gripper inertia, and visual meshes. It is a separate task from the four-axis Cartesian fixture.

Run `python tools/build_yam_task.py`, then `python tools/check_yam_task.py --episodes 10`. Construct with `YamEnv('tasks/yam_keyed_insertion')` from `astrafactory.yam_env`. The builder applies the root-owned presentation styler after building physics.

## Physical setup

The arm base is at world origin on the Z=0 bench. Socket nominal position is (0.32, 0, 0) m, with the original ±8 mm XY randomization; its nominal yaw is π rad plus ±0.18 rad to remain within the YAM wrist joint range. The prepared peg tip is rigidly attached to the real gripper frame at local (0, 0, -0.17) m with identity orientation. The 38 mm peg extends toward the gripper along local +Z. An explicit adapter stem joins it to the prepared fingers. Both finger prismatic joints are fixed at -0.030 m; grasp acquisition, finger contact-based retention and release are outside this task.

The imported visual meshes serve as convex collision hulls against the bench and exact decomposed socket. Arm self-collision is disabled by collision masks: official URDF supplies no validated collision meshes. The held tool also cannot collide with its own gripper. These approximations require replacement before planning arbitrary arm motions or claiming self-collision clearance. Peg/socket collision geometry is reused from the original task.

All six arm joints advance through MuJoCo dynamics and bounded torque motors. Joint positions are assigned only at reset. The IK teacher calculates kinematics on separate scratch data, then sends ordinary bounded target-increment actions; it does not write execution qpos or teleport the tool. Translation-waypoint descent preserves alignment; naive interpolation between joint configurations was observed to arc into the socket rim and is not the teacher used here.

Torque caps ±10 N·m follow the official upstream MJCF rather than the URDF's 1 N·m placeholder. PD gains, 0.15 N·m·s/rad passive damping, 0.015 kg·m² rotor armature, 25 g held peg/adapter mass and contact settings are provisional simulation parameters. URDF velocity metadata is not enforced as a separate hard velocity limiter. No motor calibration or hardware validation is implied.

## API and acceptance

Six actions in [-1,1] increment the six joint targets by at most 0.01 rad per 20 ms control step. The 31-dimensional privileged state observation is q(6), qvel(6), targets(6), Cartesian position error(3), rotation-vector error(3), previous action(6), contact metric(1). Policy observation includes simulator goal coordinates. This is a state-policy interface, not a visual-language-action integration.

Default reset uses IK to prepare a peg tip at Z=75 mm, with XY/yaw errors drawn from the original reset ranges. This is an already-held reachable initial state, not an executed home-to-workpiece or grasp trajectory. This task does not accept custom reset poses. Reset is seeded and deterministic.

The original acceptance thresholds remain in task.json: XY <0.8 mm, tip Z in [7.5,12] mm, speed bound0.015, load<15 N, held15 steps. Because the arm adds roll/pitch freedom, the orientation test bounds the full rotation-vector norm by0.05 rad, which also constrains tilt; this is a new task ID rather than pretending equivalence to the four-axis task. Linear Cartesian velocity components are checked in m/s and angular components in rad/s, each under the numeric0.015 limit. Success still means held depth/alignment, not bottom contact, latching, electrical mating, or retention after release. The goal tip Z is 9 mm, which is 1 mm above the 8 mm floor.

`teacher(env)` first aligns above the opening, then advances a Cartesian Z waypoint using scratch IK. Contacts, full arm dynamics and capped actuation remain active. The episode horizon is600 control steps (12 seconds). Fresh final policy comparisons must use untouched seeds and the exact frozen task and adapter hashes.
