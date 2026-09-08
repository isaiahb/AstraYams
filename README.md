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

Four small learned controllers (3,242 parameters total) now execute contact grasp → lift → alignment → insertion continuously on the official YAM assets. The frozen chain passed **20/20 reserved nominal tests and 20/20 reserved stress tests**. It uses privileged simulator state, hand-designed target coordinates, physical handoff guards and an IK/control scaffold; this is local controller distillation, not visual VLA learning or hardware validation.

The observable experiment loop preserves rejected candidates, including a PPO residual that regressed from6/10 to5/10. Astra's review identified an incorrect insertion demonstration gate; correcting training guidance and retraining produced the final chain without changing physics or acceptance checks. Additional frozen checks passed40/40 wider randomized trials and6/6 named layouts with centimetre-scale position changes and±30° key rotation; see [generalization and compute measurements](docs/GENERALIZATION-AND-COMPUTE.md). See [measured sprint results](docs/MICRO-SKILL-SPRINT.md), [experiment report](docs/evidence/skill-observatory/index.html) and [ledger contract](docs/SKILL-EXPERIMENTS.md).

Active robot assets: [I2RT YAM](https://github.com/i2rt-robotics/i2rt), MIT license retained in `assets/robots/yam/LICENSE`. Importing a URDF does not establish calibrated simulation dynamics or hardware readiness. Additional inactive robot assets retain their own source manifests and licenses.
