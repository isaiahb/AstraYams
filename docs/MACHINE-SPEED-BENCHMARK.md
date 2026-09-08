# Machine-tending speed benchmark

The engineered transport-command scaling produced a modest real reduction in simulated cycle time. It is not faster playback or new policy training. Neither candidate is promoted because at least one paired case had a higher peak contact load.

| Transport factor | Seed59000 cycle | Seed59003 cycle | Successes | Peak contact loads, N |
|---|---:|---:|---:|---|
| 1.0 baseline | 78.66s | 78.22s | 2/2 | 22.329,22.960 |
| 1.5 | 76.60s | 76.28s | 2/2 | 23.005,22.370 |
| 2.0 | 75.70s | 75.30s | 2/2 | 22.998,22.982 |

At2.0, the cycles are3.76% and3.73% shorter. Peak contact load rises0.669N on59000 and0.022N on59003. These are two existing development cases, not a fresh holdout or evidence of broad reliability.

The benchmark uses the unchanged547-parameter PPO seating correction from `runs/machine-seating-ppo-v1/policy.zip` and frozen StructuredServo weights from `runs/machine-tending-structured-v2/policy.pt`. Only arm action components are multiplied during `move_output`, `move_vise`, and `travel_raw`; final actions remain within[-1,1]. Gripper commands, contact-phase commands, phase guards, seating correction, PD gains, torque bounds, task success, retention check, and80N force-abort threshold remain unchanged. Carrying requires bilateral grip, stock clearance above100mm, and no fixture support; other robot contact disables scaling. Transition steps are not scaled.

The unchanged IK target still advances through bounded Cartesian increments of at most1.5mm. Scaling the resulting joint command therefore does not double Cartesian trajectory speed. The guarded transport phases shrink from28.32/27.98s to25.34/25.04s at2.0; other phases remain governed by the original controller.

The largest baseline phases on seed 59000 are `travel_raw` (12.34 s), `move_output` (8.22 s), and `move_vise` (7.76 s): together 36% of the cycle. The next largest are `lift_raw` (7.20 s), `lower_output` (6.76 s), and `lift_finished` (6.34 s), which this experiment does not accelerate. Existing PPO training charges -0.002 per seating control step, but that reward does not control the engineered transport phases.

Across all runs, maximum sampled arm speed is0.1416rad/s and maximum sampled actuator torque is7.469Nm. Sampling occurs after each50Hz control step; this is not a substep velocity-maximum audit. Applied torque is read from MuJoCo's actuator generalized force, separately from control commands. Simulator motor commands remain within the existing±10Nm bounds.

The source URDF lists velocity=1 and effort=1 for all arm joints. These are placeholder values, not verified YAM ratings. Sampled velocities fall below the literal1rad/s values, while sampled torque exceeds the literal1Nm effort placeholders. Neither those fields nor the simulator±10Nm bounds establish a safe hardware speed or torque envelope. No hardware was operated.

Run `PYTHONPATH=src python tools/benchmark_machine_speed.py --out runs/machine-speed-v1`. The generated report contains source/checkpoint/URDF hashes, all per-joint speed and torque maxima, phase durations, actions, joint positions and step telemetry. The benchmark verified that all frozen source and checkpoint files stayed unchanged. Canonical evidence: `runs/machine-speed-v1/report.json`.
