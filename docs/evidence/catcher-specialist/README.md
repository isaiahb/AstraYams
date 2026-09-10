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

## Reward audit and V3

V2's later development checkpoints approach the target but frequently break the
continuous hold before completion. Their episode returns exceed the earlier
passing checkpoints. The reward pays a proximity/upright/valid-hold annuity of
up to 2.35 per step while completing pays only 12 and ends the episode. At gamma
0.98, the persistent annuity can be worth 117.5. This creates a reason to linger
without finishing. See `reward-audit.json` for a same-seed discounted comparison.

V3 raises the completion bonus to 200, keeps every acceptance threshold and the
physical scene unchanged, and trains from scratch with fresh holdout seeds
44001–44024. This is a reward correction, not a relaxed evaluation. The original
source/checkpoint/results remain preserved. V3 budget: three rounds of 16,384
steps, four CPU environments, learning rate 0.0003, ten PPO optimization epochs.

```sh
python tools/train_catcher_specialist.py --out runs/catcher-specialist-v3 --task-dir tasks/yam_catcher_positioning_v2 --steps 16384 --rounds 3 --envs 4 --lr .0003 --epochs 10 --dev-count 6 --holdout-start 44001 --holdout-count 24 --completion-bonus 200
```

The presentation script captures the same recorded-state viewer with headless
Chrome via `puppeteer-core` and encodes it with FFmpeg. It changes replay time,
camera and captions only. Source paths remain local; no social post is sent.

## Final packaged result

V3 selected round 3: **23/24** fresh held-out positioning trials passed, versus
0/24 for a controller that holds the starting pose. Training took 345.46 seconds
inside the three learning calls (49,152 transitions); setup, auditing, rendering
and evaluation took additional time. The failed test, seed 44019, remains in the
interactive replay and the 31-second film.

The frozen actor generated **63 accepted demonstrations from 64 new attempts**,
with **4,813** accepted state/action pairs. These are separate from the evaluation
split. The portable NumPy actor has 2,406 parameters and occupies 10,175 compressed
bytes; its outputs match the training actor within 1.2e-7 normalized action units.
No student model or multi-skill composition is claimed.

Two successful final holdout trajectories still passed at 0.25 and 0.125 ms
physics steps, with maximum rim deviation below 0.04 mm from the 0.5 ms run.
A separate nonadjacent robot collision-proxy screen flagged convex overlaps.
Boolean intersections of the corresponding **visible meshes at one terminal
pose** were empty for both flagged pairs. This does not clear every trajectory
or validate the collision approximations. Self-collision dynamics remain off;
refine and validate those proxies before enabling them or claiming transfer-ready
robot dynamics. Both audit outputs are retained.

The final film is `runs/catcher-specialist-v3/presentation/astra-catcher-ppo.mp4`:
H.264, 1280x720, 25 fps, 31 seconds. Its captions distinguish recorded motion from
paused terminal frames and show the disabled self-collision limitation. The
replay uses every terminal sample, including odd-indexed final steps, so its
visible pass/hold state matches the recorded evaluation.

Final review: http://127.0.0.1:8793/runs/catcher-specialist-v3/review/index.html
See `DEMO-NOTES.md` for the three-minute presentation and `X-POST.txt` for the
276-character draft. Nothing has been published or sent externally.
