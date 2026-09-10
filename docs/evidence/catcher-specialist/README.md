# A small PPO specialist produces checked synthetic demonstrations

The intended demo is a complete measured loop: define a skill and its criteria,
construct its physics environment, shape rewards, train a small specialist with
PPO, evaluate unseen cases, and accept successful state/action trajectories as
synthetic demonstrations. Astra authors and revises this workflow; this is not
yet a generic prompt-to-training product or a camera-trained robot.

## Current task boundary

The official YAM moves the current revision-B catcher beneath the outer berry
of the shared V4 strawberry plant. All plant joints are retained. The catcher
is a free body gripped through contact, with CAD-derived mass and rigid contact
approximations. It starts between the jaws: no pickup, cut or falling-fruit catch
is demonstrated. The textile is a visual unloaded shape, not a deformable net.

PPO emits six joint-target increments at 50 Hz. The actor has 2,406 parameters.
Finite-torque PD, gravity compensation and a fixed jaw controller remain
engineered. Observations are 35 privileged simulator-state values, not images.
There is no IK or behavior-cloning controller in PPO execution. IK establishes
one constant reset posture and separately checks workspace feasibility.

Success requires rim-center position within 5 mm of the goal, upright normal
Z > 0.96, joint-speed norm < 0.35, both jaw forces > 0.2 N, tool slip < 5 mm
and relative rotation < 0.15 rad, continuously for 0.4 s. Unexpected contact,
penetration, lost grasp and numerical warnings fail an episode. These are
engineering acceptance criteria, not fruit-damage or real-world safety limits.

## Iteration record

1. **V1 failed: 0/12 holdout.** Development accuracy improved, but the initial
   posture put the wrist near a joint limit and required approximately 9.68
   N m at the shoulder against a 10 N m simulated torque cap. Three held-out
   policy trials collapsed into the floor. Preserve the report; it cannot
   support a successful-learning claim.
2. **V2 repairs the workspace.** Move the anchored growing trough closer to the
   arm; choose a starting posture with 0.15 rad joint-limit margins and lower
   static torque. A separately labeled IK feasibility diagnostic passes 3/3
   development cases with peak commanded torque below 6.7 N m. That diagnostic
   is not PPO data, not a learned result, and not supplied to the learner.
3. **V2 PPO is a fresh run.** Lower learning rate, more optimization epochs,
   unchanged success criteria and reward formula. Development seeds 41001–41006
   select a checkpoint. New holdout seeds 43001–43024 are reserved until
   selection. V1's now-exposed holdout is not reused as fresh evidence.

Training varies plant XYZ position (+/-20/20/12 mm), yaw (+/-0.2 rad) and plant
joint stiffness (+/-15%). These ranges are provisional priors, not fitted real
population distributions. They do not test unseen plant topology, lighting,
cameras, species, robot calibration or all possible fruit positions.

## Physics limitations

The training scene uses a 0.5 ms physics step (the original botanical study used
0.125 ms); step-refinement results must be inspected separately. Robot
self-collision is disabled. Torque limits, PD gains, gripper friction and plant
material behavior are uncalibrated. The detailed electrical/thermal motor model
researched elsewhere is not integrated into this trial. The trough is an
anchored fixture. Visible net threads have no collision response in this
pre-contact positioning task.

## Reproduce locally

Use the project Python dependencies, with `PYTHONPATH=src`. Generate the V4
specimen and revision-B tools using their recorded build scripts first.

```sh
python tools/build_catcher_positioning.py --out tasks/yam_catcher_positioning_v2 --comfortable
python tools/train_catcher_specialist.py --out runs/catcher-specialist-v2 --task-dir tasks/yam_catcher_positioning_v2 --steps 32768 --rounds 6 --envs 8 --lr .0003 --epochs 10 --dev-count 6 --holdout-start 43001 --holdout-count 24
python tools/review_catcher_specialist.py --run runs/catcher-specialist-v2
```

Do not reuse holdout seeds as untouched evidence after inspecting and tuning
against their results. The trainer writes its proposal and source hashes before
training. Checkpoints, raw trajectories and generated meshes stay under local
run/task folders; compact reports are retained here. The viewer plays recorded
body poses and supports orbiting and cel/material shading. It does not animate
a scripted successful trajectory.

The initial numerical check replays two untrained development trajectories at
0.5, 0.25 and 0.125 ms steps, including a fresh grip-settling phase each time.
Maximum catcher-rim deviation from the 0.5 ms run is below 0.07 mm over those
trials. This is a narrow numerical consistency check, not calibration or a
substitute for checking successful learned trajectories and plant contacts.
