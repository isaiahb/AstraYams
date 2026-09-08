# AstraFactory

**An AI that creates the robot skills it’s missing.**

Give a robot a task. Astra analyzes its failures, creates targeted simulation and training experience, trains a skill, and evaluates whether it improved.

## First experiment

A YAM robot grasps a free custom keyed peg through finger contact, lifts it and attempts insertion into a matching socket. A shared MuJoCo/Gym core loads task-specific CAD, reset rules, reward code and acceptance checks. The peg is a separate dynamic body, with no attachment to the gripper.

## Repository

- `assets/robots/yam/`: official I2RT YAM URDF, meshes, upstream license and pinned source manifest.
- `docs/ENVIRONMENT.md`: task-package contract, running instructions and limitations.
- `tasks/keyed_insertion/`: generated CAD meshes, physics scene, reward and evaluator.
- `tasks/yam_keyed_insertion/`: articulated YAM task, physical joint control and insertion acceptance contract.
- `tasks/yam_contact_insertion/`: active task with moving fingers, free peg and contact-only manipulation.
- `src/astrafactory/`: reusable Gym core and camera observations.
- `tools/`: CAD generation, environment checks, rollout recording and PPO training.

## Status

The active contact task passes physical grasp diagnostics at one fixed reset:89.4mm lift with bilateral unsupported finger contact, release/drop on jaw opening, and failed sustained lift when friction is removed. Insertion is currently unsuccessful: transport error causes a socket-rim collision and force abort. These are scripted physics checks, not trained-policy results. See [contact validation](docs/CONTACT-VALIDATION.md). Earlier rigid-tool checkpoints are incompatible with this task and do not establish contact manipulation performance.

Active robot assets: [I2RT YAM](https://github.com/i2rt-robotics/i2rt), MIT license retained in `assets/robots/yam/LICENSE`. Importing a URDF does not establish calibrated simulation dynamics or hardware readiness. Additional inactive robot assets retain their own source manifests and licenses.
