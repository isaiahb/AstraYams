# What the current YAM simulator does and does not establish

2026-09-09. User correction: a one-channel jaw PPO is below the intended
dexterity milestone. The goal is learned coordinated manipulation across arm
joints, followed by useful skill composition. The squeeze pilot is retained as
an instrument/control experiment, not the main demonstration.

## Current execution model

The exact active task is `tasks/yam_contact_curriculum`. It inherits
`FactoryEnv.step` through `CurriculumEnv`/`ContactEnv`. The older rigidly attached
peg environment is not used by the new squeeze tests.

1. A 50 Hz action adds bounded increments to joint position targets.
2. Every 2 ms, custom PD code computes `kp*(target-q) - kd*qvel + qfrc_bias`.
3. The computed effort is clipped and passed to MuJoCo's ideal joint actuators.
4. MuJoCo integrates the coupled rigid-body dynamics, gravity, inertia, damping,
   joint constraints and enabled contacts.

`qfrc_bias` uses the simulator's own gravity/Coriolis/centrifugal model. This is
an idealized feedforward term. Neither its accuracy nor the timing matches a
specific physical unit by evidence yet.

IK only computes desired joint values on scratch `MjData`. It does not assign
execution qpos. Ordinary episode initialization assigns poses; isolated training
can restore physically reached states. Continuous skill handoffs do neither.
The rendered recordings re-simulate actions and verify the resulting states.

## Data provenance and approximation ledger

| Aspect | What is implemented | Evidence / missing validation |
|---|---|---|
| Geometry, axes and travel | Official YAM URDF/STL data | Pinned upstream commit and hashes in `assets/robots/yam/SOURCE.json` |
| Link mass, COM and inertia | Imported URDF values | Vendor model data, not measurements of a borrowed unit |
| Robot/object contact | Rigid bodies and friction; 24 convex pieces per finger | Derived collision shapes; no measured contact calibration |
| Free manipulated object | 40 g free body with declared inertia | Our designed rigid part; no weld or kinematic attachment |
| Arm actuators | Ideal torque actuators, ±10 Nm each | Uniform bounds follow old upstream MJCF modeling values, not a verified per-motor torque-speed envelope |
| Jaw actuator | Ideal linear actuator, ±30 N, coupled fingers | Provisional cap and equality coupling; no detailed rotary transmission |
| Position controller | Custom PD at 500 Hz | Gains are our simulation settings, not demonstrated firmware parity |
| Damping / reflected motor inertia | Constant per-joint damping and armature | Provisional, no identified friction/backlash/elastic transmission model |
| Voltage / current / winding dynamics | Not modeled | No electrical motor plant or current-control loop |
| Speed-dependent torque / back EMF | Not modeled | Constant effort clipping is not a torque-speed envelope |
| Delay / packet loss / quantization | Not modeled | Observation and command timing are idealized |
| Temperature / derating | Not modeled | No sustained-duty or thermal validation |
| Arm self-contact | **Disabled** by current collision masks | Must be addressed before unstructured six-axis exploration |
| Real tracking and contact error | Unknown | No measured YAM trajectories, blocked-load curves or contact-force reference data |

The URDF has effort/velocity values of 1 throughout; the source MJCF differs.
That inconsistency was already noted in `assets/robots/yam/INTEGRATION.md`.
Do not treat either number as a verified motor specification.

## Blocked-motion experiment performed in this audit

From one physically acquired held-object state, command jaw position zero
(fully closed) using the normal bounded position-target increments:

| Actuator cap | Requested jaw coordinate | Actual jaw coordinate | Actual motor effort | Net axial squeeze |
|---|---:|---:|---:|---:|
| 30 N | 0 mm | −6.870 mm | 5.502 N | 5.396 N |
| 1 N | 0 mm | −6.948 mm | 1.000 N | 0.995 N |

The obstruction prevents reaching the target and a lower effort limit changes
the reaction load. This establishes that these movements are dynamically
constrained in the simulator. It does not calibrate the response to real hardware.
Raw measurements are in `docs/evidence/yam-grip-policies/blocked-jaw-diagnostic.json`.

MuJoCo contacts are compliant numerical constraints, so small penetration is
possible; a blocked-motion result is not an assertion of infinitely rigid contact
or exact surface agreement. Contact-mesh accuracy and timestep sensitivity remain
part of the validation work.

## Public data available to improve this

The vendor documents actual joint-position/velocity/effort observations, gripper
effort and optional temperature telemetry. It exposes joint position/state
commands and per-arm gains, gravity compensation and friction settings. These
are useful starting data for a matched actuator interface, not measurements
of the task's particular hardware.

- [Official SDK and models](https://github.com/i2rt-robotics/i2rt)
- [YAM API, controller and hardware-variant documentation](https://doc.i2rt.com/products/yam)
- [Motor command interface](https://doc.i2rt.com/products/motors)
- [mjlab's YAM actuator model](https://github.com/mujocolab/mjlab/blob/main/src/mjlab/asset_zoo/robots/i2rt_yam/yam_constants.py)

The mjlab implementation distinguishes motor types and reflected inertias and
documents an approximate gripper transmission. It also makes simplifying choices,
including a deliberately limited gripper force and a gripper-only default collision
configuration. It is prior art to inspect, not a drop-in certificate of fidelity.
Its crank gripper must not be silently substituted for our current linear-jaw
geometry. The vendor's current motor catalogue also includes GF-series modules;
do not equate their ratings to the DM motor configuration without confirming the
specific arm revision.

No percentage such as “95% realistic” is justified. A useful next fidelity target
is measurable prediction error in joint tracking, saturation, disturbance
response and gripping over the operating envelope of the next learned skill.
Electrical detail should be added when it changes those responses, rather than
assuming every transistor must be simulated to learn manipulation.

Follow-up component research is recorded in
[A calibratable actuator model for YAM manipulation](../research/yam-actuator-model/REPORT.md).
It identifies the pinned SDK's DM4340/DM4310 families, compares manufacturer
manual revisions, distinguishes protocol limits from physical ratings, and
defines a hardware-calibration protocol. Its 39-entry parameter ledger retains
unknown values explicitly. Nine isolated MuJoCo 3.12 capability checks passed;
they do not constitute a calibrated motor or an integrated arm simulation.
The execution-model limitations above remain applicable.

## Revised dexterity milestone

Train a small policy to align, rotate and seat the custom keyed part from varied
offsets and orientations. During that skill, PPO must command the six arm joints
(and either own the jaw or compose explicitly with the frozen grip controller).
It must not call IK or a BC motion planner to solve alignment during execution.
Retaining a hardware-matched servo below the policy is legitimate: that servo
tracks commands but does not decide how to solve the manipulation task.

Use a physically acquired pregrasp/held state only to initialize an isolated
skill. Score both that skill and a continuous composition separately. Define
exactly which policy inputs are ideal simulated measurements and which have
a real sensor counterpart; do not call perfect pose input a camera policy.

Before broad six-axis training: verify joint/channel mapping and gripper variant,
replace untraceable drive assumptions with a documented motor/controller envelope,
validate relevant self-collision handling, and test that blocked commands and
reduced torque cannot be bypassed. Then compare learned coordinated manipulation
against a fixed conventional baseline on unseen offsets, rotations and contact
conditions. This stronger skill has not been trained by the squeeze experiment.
