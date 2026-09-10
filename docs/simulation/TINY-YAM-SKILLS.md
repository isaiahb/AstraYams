# Tiny, composable YAM policies — 2026-09-09

The current experiment trains **one new jaw specialist with PPO** and composes
it with the existing learned approach/lift controllers. A language model is not
yet choosing the transitions: deterministic guards still do that. The desktop
product and strawberry geometry/physics were not changed.

## Measured result

| Controller | Isolated holdout grip cases | Complete stress chains |
|---|---:|---:|
| Fixed jaw position | 6/12 | 8/12 |
| Engineered motor-effort feedback | 11/12 | 12/12 |
| New PPO jaw policy | 12/12 | 12/12 |

The PPO also passed 3/3 nominal continuous approach–grip–lift chains. This is
a small feasibility result, **not evidence that PPO beats well-designed feedback
control**, nor a demonstration of general dexterity or real-arm transfer.

- Actor: 6 → 16 → 16 → 1, tanh hidden layers, **401 parameters**. The critic and
  exploration variance are used during training but excluded from this count.
- Mean NumPy actor inference: **3.71 μs** over 20,000 calls after warmup. This
  excludes observation acquisition, communication and robot control latency.
- Actual policy rate: **50 Hz**, over the existing **500 Hz** simulated motor loop.
- Training: PPO from scratch, three retained 32,768-step passes taking **23.84,
  29.90 and 30.59 seconds**. No BC update or demonstration action labels were used
  for this new actor. A small positive action-mean bias and an engineered
  requested-load-minus-effort feature helped exploration and representation.
- The second pass initially failed to save because disk space ran out. That
  unsaved work was lost; training resumed from round 1 with a reseeded sampler.
  **84.33 s is the sum of retained training passes, not total elapsed work**.
  Lost-pass duration was not recorded; `total_seconds` in the report describes
  only the resumed invocation. Cache cleanup and rendering are additional.
- Same actor handles requested loads between **2.5 and 4.5 N**. Test goals were
  2.75, 3.5 and 4.25 N. Do not create a separate model for every force or pose.

## What the actor can see and do

Inputs are jaw encoder position, jaw velocity, commanded jaw position, simulated
motor effort, requested axial squeeze, and requested squeeze minus motor effort.
It does not read object pose, contact forces, images or the arm's phase. Motor
effort has not been calibrated against squeeze on a real YAM; its availability,
units, noise and delay must be verified before hardware use.

The output changes the existing jaw position target by at most 0.3 mm per 20 ms.
That is a **command rate limit**, not a guarantee about measured finger speed.
The existing PD controller applies bounded forces. We retained its modeled
torque/force limits; they are not newly verified physical YAM specifications.

`SqueezeSkill(checkpoint, goal_n).act(env)` exposes a seven-channel action with
only the jaw channel active. It rejects goals outside the trained range. A caller
can combine that jaw channel with a separate arm policy's six channels. This
adapter supplies no hardware safety guarantee and does not replace handoff guards.

## Composition contract

The demonstrated chain is:

1. Existing BC approach, using scripted targets, pose information and IK.
2. Start the new PPO jaw controller when the approach guard qualifies.
3. Start the existing lift controller after bilateral contact and settling.
4. **Keep the PPO jaw controller running during the lift.** It owns the jaw;
   the lift controller owns the arm. These skills overlap instead of competing
   over the same action channel.
5. Confirm unsupported bilateral contact and physical object clearance before
   handing off to a later task.

There is no reset, weld, attachment or object-pose write at a transition. Isolated
training episodes do reset, but to saved states reached by a physically executed
approach or lift. The predecessor policy and guards use privileged simulator
state. This is not an end-to-end camera policy.

A future small planner should choose a bounded command such as
`{skill: "yam.regulate_axial_squeeze.v2", goal_n: 3.5}` and receive concise status
and failure codes. A deterministic dispatcher must check preconditions and action
ownership. The planner runs at decision points; the learned controllers close
the fast feedback loops. Do not put an LLM in charge of each servo tick.

Each next skill needs: input/actuator ownership, parameter range, entry-state
distribution, completion and abort conditions, predecessor/successor tests,
frozen baselines, held-out cases and checkpoint provenance. If a successor cannot
recover from its predecessor's real outputs, train that transition explicitly.

## Why the first attempt was rejected

`yam-grip-ppo-v1` trained a 481-parameter PPO for 28.14 seconds. It passed only
1/12 isolated holdout trials, equal to its fixed-jaw baseline, and was not promoted.
It mostly continued closing rather than regulating load.

That attempt targeted the **sum of contact-force magnitudes**, which includes
friction and does not equal axial squeeze. At approximately 3 N steady motor
effort, a held-object diagnostic showed that sum oscillating roughly 3.6–5.4 N.
Projecting each finger's net force along its closing axis produced approximately
3 N combined squeeze with much smaller fluctuations. Halving the timestep did
not repair the original metric. The finest-step diagnostic also had an open-grip
failure, so it is not evidence of numerical convergence.

V2 defines a separate mechanical quantity: vector-sum object-on-finger forces,
then project each finger's net force opposite its closing axis and sum the two
projections. V1's rejected criterion and scores remain preserved. We did not
relabel it as a success. V2 also changed the goal range and observation features;
it is not an ablation that attributes improvement solely to the force metric.

MuJoCo's [contact-frame documentation](https://mujoco.readthedocs.io/en/latest/computation.html#contact)
and [net-force reduction documentation](https://mujoco.readthedocs.io/en/latest/XMLreference.html#sensor-contact)
describe the underlying conventions. Force on geom2 is transformed into world
coordinates; the opposite sign is used for geom1 before summing.

## Evaluation and limits

Training seeds 84000–84007, development 84100–84102, isolated holdout 84200–84205.
Every seed supplies physically generated open-pregrasp and held-object states.
The actor was selected once using development results; holdout and stress results
did not change checkpoint selection.

Training uses original task pose variations of ±2 mm XY and ±0.02 rad yaw, plus
open/held conditions and continuous requested-load variation. Mass and friction
were not randomized during these PPO passes.

The frozen complete-chain stress test uses 84300–84311, ±4 mm XY, ±0.04 rad yaw,
and independently sampled 0.8–1.2x object mass and sliding friction. These are
engineering sensitivity ranges, not measured distributions. Part shape, camera
input, delays, occlusion, actuator dynamics error and real fingertip material
variation are **not covered**.

Success: last 0.3 s inside ±20% of the requested axial load, bilateral contact,
no held-object drop above 10 mm, and no sampled axial squeeze above 8 N. Full-chain
tests additionally require the existing physical lift handoff and final force in
band. The primary score samples at 50 Hz. A separate independent integration
audit checked every **500 Hz physics step** on all 15 PPO continuous chains:
maximum axial squeeze **4.405 N**, modeled actuator bounds respected, and exactly
matching recorded qpos at every control boundary. This is a simulation audit,
not real-world safety validation or a tissue-damage model.

All three nominal videos replay the saved actions through the physics engine;
the qpos and axial force match their source recordings exactly. They show every
nominal continuous trial, including the actual handoff times, at 1x speed.

## What the older fast results actually were

The 3,080-parameter micro-grasp pair fitted in **4.99 s using behavior cloning**;
the full collection/training/evaluation run took 19.74 s. The old complete BC skill
composition reached 20/20 nominal and 20/20 stress cases, with scripted targets,
IK and guards. That was not four policies learning from scratch with PPO.

A previous genuine 545-parameter residual PPO trained in 17.97 s but changed
continuous-task success from 6/10 to 5/10. Another 1.39 s PPO smoke test achieved
0/10 and used a simplified fixture. Training duration alone is not evidence of
skill acquisition.

[PPO](https://arxiv.org/abs/1707.06347) is the training algorithm, not a model type
or a VLA. The resulting controller can be a tiny MLP. The importance of training
handoffs between specialists also has prior art in
[Composing Complex Skills by Learning Transition Policies](https://youngwoon.github.io/transition/).

## Artifacts and reproduction

Local review: `http://127.0.0.1:8793/runs/yam-squeeze-ppo-v2/review/index.html`.
Compact reports, audits and one preview are tracked in
`docs/evidence/yam-grip-policies/`. Checkpoints, action/state recordings and videos
remain under ignored `runs/`, in accordance with the repository policy.

From the repository root, using its MuJoCo/SB3 Python environment:

```sh
python tools/train_yam_squeeze_ppo.py --out runs/yam-squeeze-new
python tools/evaluate_yam_squeeze_stress.py --run runs/yam-squeeze-new
python tools/audit_yam_squeeze_mechanics.py --run runs/yam-squeeze-new
python tools/render_yam_squeeze_review.py --run runs/yam-squeeze-new
```

Use `--resume` only for an interrupted training directory with at least one
complete `round-N.json` and checkpoint. A fresh run follows the original seed
schedule; it will not reproduce the interruption-induced reseeding exactly.

## Next useful experiment

The next specialist should solve a task where feedback alone lacks a good
hand-designed solution: contact-guided alignment or recovery from a misgrasp,
with an explicit sensing contract. First measure which failure is actually
observable with the available encoders/effort or add a realistically modeled
camera/tactile input. Do not claim that encoders alone reveal vertical object slip.

Use this same loop: isolate a meaningful skill, define a measurable physical
target, establish conventional and untrained baselines, train, freeze, evaluate
on unseen conditions, then test actual predecessor/successor transitions. Keep
the simple controller when the learned one offers no demonstrated advantage.
