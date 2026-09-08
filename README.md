# AstraFactory

**An AI that creates the robot skills it’s missing.**

Give a robot a task. Astra analyzes its failures, creates targeted simulation and training experience, trains a skill, and evaluates whether it improved.

## First experiment

A YAM robot inserts a custom keyed peg into a matching socket despite position and orientation errors. A shared MuJoCo/Gym core loads task-specific CAD, reset rules, reward code and acceptance checks. The peg starts attached to the gripper; grasp acquisition is outside this experiment.

## Repository

- `assets/robots/yam/`: official I2RT YAM URDF, meshes, upstream license and pinned source manifest.
- `docs/ENVIRONMENT.md`: task-package contract, running instructions and limitations.
- `tasks/keyed_insertion/`: generated CAD meshes, physics scene, reward and evaluator.
- `tasks/yam_keyed_insertion/`: articulated YAM task, physical joint control and insertion acceptance contract.
- `src/astrafactory/`: reusable Gym core and camera observations.
- `tools/`: CAD generation, environment checks, rollout recording and PPO training.

## Status

The articulated YAM environment runs with contact dynamics and separate training/evaluation logic. Scripted teacher10/10; hold0/10; deliberately misaligned descent0/3 physically blocked at the socket rim. Learned state-policy baseline3/20 and resumed candidate5/20 on paired development seeds; this is not robust insertion or a VLA result. See [YAM task](tasks/yam_keyed_insertion/README.md) and [learning evidence](docs/LEARNING.md).

Active robot assets: [I2RT YAM](https://github.com/i2rt-robotics/i2rt), MIT license retained in `assets/robots/yam/LICENSE`. Importing a URDF does not establish calibrated simulation dynamics or hardware readiness. Additional inactive robot assets retain their own source manifests and licenses.
