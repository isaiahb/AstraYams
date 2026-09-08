# Isolated seating PPO experiment

The machine-tending chain is split into pickup, transport, seating, and clamp/release verification. This experiment changes only seating. Pickup and transport reuse the two fitted feedback controllers; workflow targets, phase guards, inverse kinematics, and machine commands remain programmed.

PPO learns a three-dimensional tool-target correction bounded to ±2 mm during `seat_raw`. Its 13-dimensional observation contains simulator pose error, stock velocity, contact loads, and gripper target. This is privileged-state residual RL, not visual learning or learning the entire task from scratch.

Training episodes reset to complete MuJoCo integration states that were reached by physical prefix rollouts at seeds 56000–56003. There are no object attachments or pose writes during a rollout. Development evaluation starts the complete cycle at seeds 59000–59004 and never restores a snapshot between skills. Reserved final seeds 58000–58019 remain untouched.

Astra's reward combines distance progress, penalties for contact load above 10 N, action effort, elapsed steps, +20 for actual task success, and −20 for force abort. These are training preferences. The unchanged task evaluator separately requires unloading, raw-stock seating, bilateral clamping, gripper release and clearance, a 1 N retention pulse, and a stable hold. The 80 N force abort and 4,000-step horizon remain unchanged.

Run:

```sh
PYTHONPATH=src:tools python tools/train_machine_seating_ppo.py --steps 8192 --out runs/machine-seating-ppo-v1
```

The proposal, progress, training episodes, policy checkpoints, paired full-cycle traces, action/qpos records, and report are saved in the run directory. Report PPO optimization/rollout time separately from prefix generation and full-cycle evaluation. A short training run is possible because the policy only adjusts a small part of an already engineered controller. It does not imply that arbitrary manufacturing skills can be learned in seconds.

For historical comparison, `runs/residual-insert-ppo-v2/report.json` records the earlier insertion PPO experiment: 8,192 training steps in 17.97 seconds, with baseline 6/10 and PPO candidate 5/10. It was not retained as an improvement. The successful prior imitation-learning experiments should not be labeled PPO.
