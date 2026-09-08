# Reusable task packages

**Current contact-manipulation task:** `ContactEnv('tasks/yam_contact_insertion')` from `astrafactory.contact_env`. The peg is a free body, fingers are articulated, and grasp retention comes only from contact/friction. Run `python tools/check_yam_contact.py` and `python tools/record_yam_contact.py --insertion`. Seven actions,42 state observations. [Physical evidence and limitations](CONTACT-VALIDATION.md). The prepared rigid-tool task below is a separate diagnostic and its policies are not valid for the contact task.

**Active demonstration:** the official articulated [YAM task](../tasks/yam_keyed_insertion/README.md), using `astrafactory.yam_env.YamEnv`. Run `python tools/check_yam_task.py --episodes 10` and `python tools/record_yam_task.py --mode teacher`. Its six actions and31 observations replace the Cartesian fixture interface described below. [Learning commands and actual results](LEARNING.md). The fixture remains a focused contact test.

The shared `FactoryEnv` owns physics stepping, bounded PD control, Gym API, deterministic resets, rendering and termination plumbing. A task directory owns its CAD meshes, MJCF scene, reset distribution, observation contract, reward and success logic. New rigid-part tasks should be new directories, not forks of the Gym core.

## Run locally or on a Linux worker

```sh
python -m pip install -e '.[design,train,video]'
python tools/build_keyed_parts.py
python tools/check_task.py
python tools/record_task.py
python tools/train.py --steps 10000 --out runs/first-policy
python tools/train.py --steps 10000 --resume runs/first-policy/policy.zip --out runs/continued-policy
```

The prepared Mac interpreter is `/tmp/clonebench-cad-env/bin/python`. On a headless GPU worker, rendering may require `MUJOCO_GL=egl`; it has not been verified on RunPod yet. The current tiny state-policy trainer explicitly uses CPU; no GPU instance has been provisioned by these scripts.

```python
from astrafactory.env import FactoryEnv
from astrafactory.observations import CameraObservation

env = FactoryEnv('tasks/keyed_insertion')
observation, info = env.reset(seed=123)
observation, reward, terminated, truncated, info = env.step(env.action_space.sample())
# For image-based policies, use CameraObservation(FactoryEnv(...)).
env.close()
```

## Task-package contract

| File | Ownership |
|---|---|
| `task.json` | Scene/plugin paths, control joints and actuators, gains, action units/scales, observation size, horizon, reset distribution and acceptance thresholds. |
| `scene.xml` + `assets/` | Robot/tool, custom parts, fixtures, cameras and physics. Parts must use collision geometry that preserves critical holes and concavities. |
| `task.py` | `Task(env)` with `reset(rng, options)`, `observe()` and `evaluate(contact_load)`. The evaluator returns at least `is_success`. |
| `reward.py` | `Reward(env)` with `reset()` and `__call__(action, info)`. Training rewards can be revised separately from acceptance checks. |
| `design.json` | Parametric part dimensions, units and collision-construction notes. |

Plugins are trusted Python code, not a security sandbox. The controller currently supports one-DoF slide/hinge joints with torque/force motors, not arbitrary actuator types. New controllers and deformable/contact models require additional implementation. This is an extensible core, not a claim that arbitrary CAD is automatically a valid simulator.

## First task: custom keyed insertion

Parametric CAD generator: `tools/build_keyed_parts.py`. A five-sided peg is 18 × 14 mm in footprint, with a clipped corner and 38 mm length. Socket walls are 32 mm deep, with nominal 0.6 mm clearance per side. The generator exports watertight STL meshes; this is parametric mesh CAD, not a manufacturing drawing/STEP release.

Nine convex triangular prisms cover the socket walls. The generator checks their combined area exactly against the ring polygon. MuJoCo can therefore retain the opening rather than convex-hulling the whole socket shut. The peg is a convex mesh. Floor, holder, gravity, contact friction and bounded actuation are present.

**Embodiment:** four-DoF Cartesian tool fixture (X/Y/Z/yaw), peg rigidly attached from reset. It is not the full robot-arm model. The attachment is an explicitly prepared initial condition; no grasp is acquired by this task. The imported robot URDF remains available for a subsequent arm adapter and reachability/torque validation. There is no claim of full-arm or sim-to-real validation.

**Control:** 500 Hz MuJoCo, 50 Hz Gym actions. Actions increment tool position targets by at most 1.5 mm and yaw by 0.025 rad per step. PD forces and torque are capped. `step()` never assigns joint positions; only reset does. Roll/pitch are constrained by the fixture.

**Randomization:** socket X/Y ±8 mm, socket yaw ±0.18 rad; initial tool error X/Y ±12 mm and yaw ±0.3 rad. Initial peg tip Z=62 mm. Mass, friction and dynamics are provisional, not calibrated or randomized yet.

**State observation (21):** tool position/yaw, velocities, commanded targets, relative goal, previous action and contact-load scalar. These include privileged simulator coordinates. They are appropriate for a labelled state-based experiment, not evidence of visual generalization.

**Camera wrapper:** RGB 320 × 240 plus 16 proprioceptive/controller values. It excludes goal/socket state from the observation. Evaluation `info` still contains ground truth; policy adapters must not consume that during execution. This is a camera interface, not yet a SmolVLA/LeRobot adapter or fine-tuned VLA. Language instructions and model-specific normalization/action chunking still need integration.

**Success:** XY error <0.8 mm, yaw error <0.05 rad, peg tip Z between 7.5 and 12 mm, low velocity, contact load <15 N, held for 15 control steps. The goal tip Z is 9 mm, 1 mm above the floor: success establishes insertion depth and alignment, not bottom contact, electrical mating, latching or press-fit retention. Peg remains held.

**Force metric:** peak over each control step of the sum of contact-force magnitudes. It is conservative and is not a calibrated wrist wrench. Abort above 45 N is a simulation setting, not a hardware safety rating.

## Checks and evidence

`tools/check_task.py` validates Gym behavior, seeded resets, invalid actions and physical positive/negative controls. The alignment-first scripted teacher is a feasibility baseline and possible demonstration source, not a learned policy. Blind descent tests whether walls physically block misaligned insertion. Hold-position tests for false success.

`tools/record_task.py` records actual simulator execution as MP4, states, actions and observations. Its policy modes are specific to keyed insertion. Video frames are post-step and transition observations are pre-step; use a dedicated synchronized camera dataset collector before VLA training.

`tools/train.py` accepts any compatible task package and saves PPO checkpoints, Monitor traces, task-file hashes and evaluation results. `--resume` continues compatible checkpoints. Smoke training only establishes execution; it does not establish learning. Saved evaluation seeds are a development smoke set; allocate fresh untouched final tests for a real improvement claim.

Freeze the task/evaluator and held-out reset distribution before comparing policies. If geometry or acceptance criteria change, rerun both policies. Allow Astra to revise training rewards and development curricula while preserving the final test. No reward improvement can substitute for the physical success check.

## Next extension

Collect synchronized RGB/state/action demonstrations, validate a model-specific VLA adapter, then fine-tune against a fixed test. Add the full robot adapter afterward without changing task acceptance semantics. Grasping, deformable cables, thread engagement and actuator system identification are separate capabilities.
