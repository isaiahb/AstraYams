# Visual student and sim-to-real boundary

The objective is now a policy that controls the YAM from sensor data available on a physical setup. The earlier privileged state-policy chain is preserved as a simulation reference and demonstration teacher. Its success rates do not establish deployable visual-policy performance.

## Chosen input/output contract

The first visual student consumes two fixed external RGB camera views plus 28 proprioceptive/controller-history channels. The cameras are a proposed physical mounting arrangement, not a claim that cameras ship with the arm. No camera follows the peg using simulator coordinates. Calibration, exposure, camera latency and real mounting still require measurement.

The 28 channels are: six arm joint positions and normalized gripper opening; their seven velocities; the seven last commanded target values; and the seven previous normalized actions. Targets and previous actions are known software history, not inferred object state. Normalized gripper opening is 0 closed / 1 open. Current sim slider conversion uses opening=-q7/0.04695, with the corresponding velocity conversion; this is an explicit calibration assumption, not a measured real-gripper map.

The official [YAM interface](https://doc.i2rt.com/products/yam) documents joint position/velocity and gripper position/velocity observations, and joint-position commands with normalized linear-gripper values. Joint effort is also exposed, but this experiment excludes it because simulated contact-force sums are not equivalent to hardware motor effort or calibrated fingertip/wrist sensing.

The student emits seven bounded joint-target increments, including gripper motion. A task-independent control adapter integrates and bounds commands. The student does not call IK, read the socket/peg pose, use task phase, receive simulator contact measurements, or invoke the privileged skill chain during execution. The low-level PD model remains a simulation approximation of hardware tracking.

## Reset protocol matters

The old curriculum positioned the arm above the actual randomized peg via IK. This leaks object location into initial joint feedback and assumes an unavailable perception step before the task. The visual-reset-v1 variant fixes initial robot joint configuration, velocity, target and action history across seeds, while object layout and appearance vary. All such initialization occurs before simulation execution; physical contacts and the insertion evaluator remain unchanged. The new reset variant must be recorded distinctly from earlier scored reset distributions.

## Training information versus execution information

Privileged geometry/contact state may generate demonstrations or evaluate success. It must never enter student observations, control-side handoff decisions, camera tracking, or reset initialization conditioned on randomized object poses. A pure act(observation) API supports that boundary. Static and poisoned-oracle checks help catch unintended access; camera blanking/shuffling is a separate test of whether the model actually uses vision.

A teacher can use exact simulator information to create examples for a sensor-limited student. This does not make the student state-privileged if runtime inputs and helpers are isolated. Conversely, a camera in the observation dictionary alone does not prove vision is used.

## What remains unverified

Simulated images differ from real textures, lighting, lens distortion, motion blur, occlusion and exposure. Encoder noise, calibration error, communication delay, compliance, backlash, contact friction and motor response also need real measurements. Randomization can train robustness over declared assumptions but cannot verify real-robot transfer without hardware tests. Collision geometry, mass and actuation parameters should ultimately be identified against the actual YAM variant and gripper.

The visual experiment uses explicit seed namespaces: training 10000–10031; offline development 20000–20007; rollout development 21000–21004; reserved visual final 8000–8099. These are disjoint within this new experiment; do not infer split membership from a blanket numeric cutoff inherited from earlier experiments. Model architecture, dataset hashes, actual used seeds and results are recorded separately.

## First milestone

The first candidate learns pickup and sustained physical grasp only. This is not the full insertion task. Its paired development evaluation compares initial, trained, and blank-camera versions using the same seeds and independently computed contact/hold measurements. Insertion remains a later skill.

## First measured result (8 demonstrations)

The first 201,672-parameter CNN/GRU student trained for 400 behavior-cloning updates on eight training demonstrations, with two separate offline development demonstrations. Training took 107.13 seconds on the M4 Pro GPU (MPS). An identical ten-update batch benchmark took 6.02 seconds on CPU and 2.52 seconds on MPS; this does not measure RunPod performance.

Paired independent rollout development on seeds 21000–21004 scored **trained RGB 0/5, blank RGB 0/5, untrained RGB 0/5**. None achieved the independently scored pickup/hold; all ended at the original force limit. The candidate is not promoted. Low offline action-prediction error did not translate into successful closed-loop manipulation. The blank-image result cannot establish useful visual dependence when both conditions fail.

The actual trained checkpoint passed the software information-boundary audit on 16 recorded observation packets, with identical actions under poisoned simulator references. That establishes the audited runtime boundary, not task competence or hardware transfer. Forty full offline teacher demonstrations are preserved for subsequent work. Visual final seeds 8000–8099 remain untouched.

Artifacts: `runs/visual-policy-v1-8episodes/report.json`, `leak-audit.json`, and `runs/visual-policy-v1-8episodes-evaluation/report.json`. The evaluation directory includes the student's actual two-camera video, sensor packets, actions and physical traces. No successful teacher footage is substituted for the failed student.

## Bounded second candidate

A second candidate uses all 32 training and eight offline-development demonstrations, 1,000 updates, and fresh rollout-development seeds 21010–21014. It keeps the same network, sensor/action interface, physics and pickup metric. Sampling emphasizes initial approach windows (25% initial frame, 25% first 64 steps, 50% all pickup steps). Previous-action normalization uses known action bounds rather than tiny empirical variance; encoder/target and velocity scales have explicit floors. These changes are bundled, so any improvement cannot be attributed to one factor without a separate ablation. It trained in 257.31 seconds on MPS. The final paired development result was trained RGB **1/5**, blank RGB **2/5**, and untrained **0/5**. These five-trial results do not demonstrate useful visual contribution; the checkpoint is not promoted. One successful physical pickup does not establish robust perception, insertion, or sim-to-real transfer. See `runs/visual-policy-v2-32episodes-evaluation/report.json` for every outcome.
