# Visual student information boundary

The new student is a separate experiment from the successful privileged-state skill chain. The earlier chain's outcomes remain valid within their recorded scope; they are not camera-policy or hardware results.

The student runtime is `astrafactory.vision_policy.VisualPolicy(checkpoint, device).reset()` and `act(observation) -> seven normalized joint/gripper deltas`. Its source imports NumPy and PyTorch, not MuJoCo, Gym, task plugins, teachers or privileged skills. The runtime reads only `rgb` and `proprio`; it does not accept an environment. Its history stores copies of those values. Teacher actions and simulator ground truth are permitted for offline labels and independent evaluation, never as student observations.

## Sensor and command contract

| Channel | Student-facing values | Physical counterpart and unresolved issue |
|---|---|---|
| RGB | Two uint8 160×160 RGB images | Two rigid workcell camera mounts; simulated intrinsics/extrinsics are engineering assumptions, not measured calibration. |
| Measured position | Six arm encoder angles and normalized gripper opening | SDK feedback mapping must be validated against actual hardware and chosen gripper. |
| Measured velocity | Six arm joint velocities and normalized opening velocity | Real timing, filtering and feedback latency must be measured. |
| Controller memory | Seven commanded targets and seven previous normalized actions | Known commands, not object/contact estimates. Mapping must account for real controller limits and tracking error. |
| Time metadata | Sensor and image timestamps outside the network's current input | Camera cache is nominally 25 Hz, action loop 50 Hz; real exposure, synchronization, transport delay and dropped frames remain unmeasured. |

No object/socket pose, grasp contact force, success flag, teacher phase, reward, task stage or task-conditioned IK is supplied to the student. No torque/contact-force input is chosen. Simulator contact force is an evaluator quantity, not a supported hardware sensor claim. The simulated finger stroke→SDK normalized opening mapping in `sensor_contract.py` is explicitly uncalibrated. There is no connected hardware or physical deployment validation in this experiment.

## Camera inspection

`deployable_observations.py` constructs two fixed workcell transforms. Front-left uses constant look-at `[.29, -.04, .045]`, distance `.38 m`, azimuth `45°`, elevation `−35°`; front-oblique uses the same look-at, distance `.34 m`, azimuth `135°`, elevation `−35°`. Both use `45°` FOV. These look-at points are constants, not current object coordinates. Training augmentation perturbs a camera once at construction and leaves that sampled transform fixed during the episode. Actual mounting clearance, occlusion, lens model and calibration still require hardware work.

The independent `--reset-audit` passed on seeds 99000–99003: all 28 initial proprioceptive channels were identical (maximum difference 0), while all four initial image hashes and object placements differed. Camera transform and rendered-eye maximum differences were both 0. Image timestamps confirmed one cached frame across two 50 Hz control calls, followed by a new frame. Results and source hashes are recorded in `runs/visual-reset-audit/report.json`. These are software checks on the current simulator adapter, not physical calibration.

The renderer and sensor adapter necessarily access simulator geometry to produce pixels, and robot q/qdot to produce encoder values. They remain outside the student boundary; the rig/environment object is never a valid student observation. The dynamic reset/camera checks described above independently verify this source-level inspection.

## Reset-channel issue found before data collection

The existing `CurriculumEnv` initializes robot IK relative to each randomized peg. Even without explicit peg coordinates, its initial q/command targets therefore encode the randomized object position. This is inappropriate evidence of camera-dependent acquisition.

The new `visual-reset-v1` variant must set a fixed canonical robot q, zero/constant qdot and fixed target/history independent of randomized peg/socket pose before the first physics step. The privileged offline teacher may subsequently approach the object while generating demonstrations. The student evaluation may not receive a teacher pre-approach. Independent validation now confirms identical initial proprioception across four randomized scenes while pixels/object poses vary. Contact physics and actual acceptance criteria remain unchanged, but this reset distribution is a distinct recorded experiment variant.

## Independent tests and limits

`tools/check_visual_leaks.py` inspects student imports/attributes, checks held references for simulator environments, and compares action sequences for identical fixed sensor packets with module-level oracle contexts poisoned to raise on access. It checks finite bounded seven-dimensional actions. Tests include a deliberately leaky policy using hidden `env.task.goal`; that negative control is detected. An untrained actual student-network fixture passes the same invariance check. The actual trained checkpoint also passed on 16 recorded offline-development sensor packets: a real audit environment had task/data/model replaced with poisoned objects; action differences were exactly zero, with no oracle accesses or held simulator references. The checkpoint and recorded data SHA256 are in `runs/visual-policy-v1-8episodes/leak-audit.json`. Independent evaluator/trainer wiring review is in `wiring-audit.json` beside it. These checks establish the implemented software boundary, not successful learning.

```sh
python -m unittest discover -s tests -p 'test_visual_leak_audit.py'
python tools/check_visual_leaks.py --reset-audit --out runs/visual-reset-audit/report.json
python tools/check_visual_leaks.py --checkpoint runs/<candidate>/policy.pt \
  --observations runs/<dataset>/episode.npz --out runs/<candidate>/leak-audit.json
```

The checker is not a proof against arbitrary malicious native code or dynamic hidden imports. Review source, collector/evaluation wiring and reset/camera behavior together. A policy can still ignore its camera and exploit timing or proprioceptive patterns while passing an information-boundary test. Closed-loop blank-image and shuffled-image controls on fixed evaluation seeds are therefore useful separate measurements; action sensitivity alone is not proof of visual generalization.

Run records must report failures and baseline results as measured. Final seeds 8000–8099 are reserved until the student checkpoint and complete evaluation protocol are frozen; do not use them for training, checkpoint selection or debugging.


## First trained candidate outcome

The 201,672-parameter student trained on eight demonstrations plus two offline-development episodes in 107.13 seconds (120.68 seconds for the trainer run). On the five registered rollout-development seeds, trained RGB, blank RGB and initial untrained weights each scored 0/5 on the final-retention pickup criterion. All 15 episodes ended on the original simulator force limit, with no ever-validated pickup. Offline action MSE is not task success. The candidate is rejected; the successful privileged-state chain remains a separate result. No final seeds were used. Source reports, sensor video and audit snapshots are in `docs/evidence/skill-observatory/visual-student-v1/`.
