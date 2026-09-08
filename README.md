# AstraFactory

**An AI that creates the robot skills it’s missing.**

Give a robot a task. Astra analyzes its failures, creates targeted simulation and training experience, trains a skill, and evaluates whether it improved.

## First experiment

One arm pushes a small part into a marked target on a workbench. The part must remain in the target after the arm withdraws. Compare a baseline and a fine-tuned policy on identical held-out starting conditions.

## Repository

- `assets/robots/rebot_dm/`: robot URDF and its complete visual/collision mesh dependencies, with upstream license and pinned source manifest.
- `docs/POC.md`: task, learning loop and acceptance criteria.
- `src/astrafactory/`: simulation and learning implementation.

## Status

Repository initialized; robot assets imported and mesh references verified. The pushing environment and training experiment are not implemented yet.

Robot assets: [Seeed reBot-DevArm](https://github.com/Seeed-Projects/reBot-DevArm). Asset terms are retained in `assets/robots/rebot_dm/LICENSE`. Importing a URDF does not establish calibrated simulation dynamics or hardware readiness.
