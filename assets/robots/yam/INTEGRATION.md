# Official YAM source assets

`v1/` is copied without modification from I2RT Robotics' official repository at commit `5b72c47239bd056d0fa6c1a39edeb0537c89443c`. See `SOURCE.json` for original paths and SHA256 hashes and `LICENSE` for the upstream MIT license. `v1/README.md` contains detailed official kinematic, inertial, joint-limit and home-frame tables.

## Files and import checks

- `v1/yam.urdf`: complete arm with gripper and both fingers, eight joints, nine visual meshes. All mesh paths are relative `assets/*.stl`.
- `v1/yam.xml`: official arm-only MJCF, six hinges, six arm meshes, no actuators; end-effector `gripper` is intentionally a mount with placeholder mass, awaiting a separate gripper attachment.
- `v1/assets/`: every upstream STL in this arm directory, including alternate `crank_4310` gripper meshes.

Verified with the prepared Python/MuJoCo environment on 2026-09-08:

1. Unmodified MJCF loads: nq=6, nv=6, nbody=8, ngeom=6, nu=0.
2. URDF import with in-memory compiler `discardvisual=false` and absolute `meshdir` pointing to `v1/` loads: nq=8, nv=8, nbody=9, ngeom=9, nu=0. Do not point meshdir to `v1/assets/`, which would duplicate `assets/` in paths.
3. Imported URDF has zero collision-enabled geoms. Collision proxies/treatment are required for a physical integration; simply rendering imported visuals does not establish collision validation. No actuators are included in either source.

Source assets were not altered to perform the import probe. Any generated simulator adapter should be a separate derived file, preserve source attribution, and record actuator/contact changes.

## Kinematics

Six revolute arm joints: `joint1` through `joint6`. Chain: `base -> link1 -> link2 -> link3 -> link4 -> link5 -> gripper`. End-effector attachment frame: `gripper`, the child of `joint6`; there is no named tool-center-point site. Define a derived TCP explicitly for the peg.

| Joint | Lower (rad) | Upper (rad) |
|---|---:|---:|
| joint1 | -2.61799 | 3.14159 |
| joint2 | approximately 0 | 3.66519 |
| joint3 | 0 | 3.14159 |
| joint4 | -1.69297 | 1.5708 |
| joint5 | -1.5708 | 1.5708 |
| joint6 | -2.0944 | 2.0944 |

URDF fingers: `joint7` is prismatic `gripper -> tip_left` with local +Y axis; `joint8` is prismatic `gripper -> tip_right` with local -Y axis. Both have travel [-0.04695, 0] metres. There is no mimic coupling in this URDF. For a rigidly preheld peg, lock jaw coordinates explicitly and label grasp as prepared rather than acquired.

At all-zero arm coordinates, the official MJCF gripper position is approximately `(0.110597, 0.000001, 0.173502)` metres and rotation matrix is approximately `[[0,0,-1],[0,-1,0],[-1,0,0]]`. Thus gripper local -Z points toward world +X in the home pose. Do not assume a downward-pointing tool from the mount frame. Use numerical FK/IK and joint-limit checks when orienting the peg vertically.

Upstream URDF uses effort/velocity limits of 1 throughout while arm MJCF declares actuator force ranges ±10. These are source modeling values, not independently verified hardware capability. URDF gripper mass is 0.553219kg; arm-only MJCF's gripper mass1e-6kg is an explicit placeholder, not a real gripper. Use actual URDF inertial data when including gripper visuals/geometry, and disclose any simulator gain/torque choices.
