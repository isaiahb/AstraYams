# Frozen-policy variation and compute checks

The selected four-policy chain was frozen before these tests. None of the challenge outcomes was used for training or checkpoint selection. The part and socket geometry stay the same. The tests evaluate policy robustness given privileged simulator pose/contact information, not visual perception generalization.

## Randomized challenge audit

Each profile has10 independently seeded continuous episodes, preserving the original contact model, scoring thresholds and horizon. All resets occur before pickup, and no reset/attachment occurs between learned skills.

| Profile | Changes from reference | Result |
|---|---|---|
| Wider pose | Peg/socket XY independently up to±10mm; shared yaw±0.15rad | 10/10 |
| Dynamics | Mass0.7–1.3×; sliding friction0.65–1.35× | 10/10 |
| Independent socket yaw | Keyed socket rotated relative to peg by up to±0.15rad | 10/10 |
| Combined | All the above | 10/10 |

These ranges exceed the downstream training ranges (mass/friction0.9–1.1×,XY±3mm,sharedyaw±0.025rad). Realized values, failed-reset accounting, checkpoint hashes, actions and traces are retained in runs/skill-generalization-v1. There were no failures in this finite audit;10/10 gives a95% Wilson interval of approximately72.2–100% per profile, not a guarantee of universal success. The engineering randomization ranges are not calibrated hardware distributions.

Six named larger-layout trials also passed6/6, with peg offsets up to±30mm, socket offsets up to±40mm and relative key rotation±30°. Four contrasting trials are shown simultaneously in runs/skill-layout-cases-v1-grid/four-physical-generalization-trials.mp4. This video is an exact-action replay with independently checked telemetry. These named trials and their synchronized video are a separate demonstration. They must not be pooled into a statistical random-sample success rate. Vertical key rotation is not the same as a tilted insertion axis. New part geometry, tilted holes and camera-based sensing are not established by this audit.

## CPU versus GPU measurement

The local benchmark uses the actual saved augmented grasp-training data, identical initialized two-specialist models (3,080 parameters total), Adam settings, and batch-index sequences. There are200updates per specialist (400total),20warmup updates followed by resetting weights/optimizer, and3repeats. MPS work is explicitly synchronized. Allocation/transfer and warmup are recorded separately.

| Batch | CPU2threads median | Apple MPS GPU median | Resident-update result |
|---|---:|---:|---|
| 512 | 0.19868s | 0.35538s | CPU1.79× faster |
| 4096 | 0.61255s | 0.45583s | MPS1.34× faster |

Hardware: Apple M4 Pro. These are resident optimizer timings, not complete task learning or equal policy-quality comparisons across different batch sizes. The NVIDIA A100/RunPod combination was not benchmarked. No new RunPod resources were provisioned.

The initial19.737second experiment comprised4.987seconds of network training and14.673seconds of teacher/evaluation rollouts. A separate rollout profile attributed about54% of inner-loop time to controller/IK and44% to physics/evaluation; moving only the network optimizer would not accelerate those CPU stages.

GPU simulation is a separate backend and batching decision. MuJoCo's documentation notes that MJX-JAX is intended for large parallel scene batches and can be slower than CPU MuJoCo for a single scene. See [MuJoCo MJX](https://mujoco.readthedocs.io/en/latest/mjx.html). PyTorch also documents kernel-launch overhead at small workloads: [CUDA graphs explanation](https://pytorch.org/blog/accelerating-pytorch-with-cuda-graphs/). The measured crossover above supports choosing hardware from actual workload timings rather than assuming either CPU or GPU always wins.

Benchmark artifacts: runs/micro-grasp-device-benchmark/summary.json and corresponding raw reports, source and batch4096 run. These benchmarks never modified the frozen policy checkpoint.
