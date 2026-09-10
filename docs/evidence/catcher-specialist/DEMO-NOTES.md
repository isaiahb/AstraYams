# AstraFactory: a robot skill learning loop

An AI that creates the robot skills it’s missing.

This demonstration uses the shared V4 plant, the official I2RT YAM and the
revision-B catcher. A 2,406-parameter actor trained with PPO issues six joint
commands at 50 Hz. Engineered finite-torque PD and jaw control execute them.
It positions and holds the catcher under a berry; it does not pick up the tool,
cut a stem or catch a falling berry. Its observations are simulator state.

## Measured result

- 23/24 held-out positioning trials passed. The fixed-pose baseline passed 0/24.
- Development selected the checkpoint before any final-test episode was run.
- 49,152 training transitions across three rounds; 5.76 minutes inside the training calls, excluding environment construction and evaluation.
- New demonstration split: 63/64 accepted episodes, 4,813 state/action samples. The failed attempt is retained but excluded from the accepted dataset.
- Actor: 10,175 compressed bytes. NumPy inference agrees with PyTorch within 1.2e-07 in normalized action units.
- Two successful holdout rollouts also pass at finer timesteps; maximum catcher-rim deviation is below 0.04 mm in that check.
- Failed holdout: seed 44019. Its final position error is 12.85 mm. The failure is in the replay and film.

Randomization: plant position +/-20/20/12 mm XYZ, yaw +/-0.2 rad and stiffness
+/-15%. These are local simulated variations, not proof of arbitrary plant or
real-world generalization. The 24-case sample does not establish 100% reliability.

## Three-minute live demo

1. **0:00–0:20:** State the thesis. A large AI constructs the learning problem;
   a tiny specialist executes the resulting skill.
2. **0:20–0:50:** Show the plant and tool research, geometry and retained plant
   dynamics. Orbit the current cel-shaded workcell and the jaw/tool contact.
3. **0:50–1:20:** Compare the untrained and PPO development replays. The policy
   chooses six joint commands; no IK or behavior-cloning controller selects
   its movements. The jaw and motor controllers remain engineered.
4. **1:20–1:50:** Explain the reward audit. The old reward paid 81.5 discounted
   return for a failed lingering trajectory versus 41.0 for a passing one.
   Astra raised the completion bonus while preserving the success thresholds,
   then trained afresh. Do not claim the two different holdout sets are a
   paired comparison of the rewards.
5. **1:50–2:25:** Show the new held-out cases, including the failure. The target
   requires <5 mm error, an upright tool, stable physical grasp and a 0.4 s hold.
6. **2:25–3:00:** Show the portable actor, skill contract and fresh demonstration
   dataset. The next step is student learning and additional specialist skills,
   followed by tested handoffs. Those are not implemented in this demonstration.

## Files

- Film: `astra-catcher-ppo.mp4` (recorded body states in cel shading).
- Interactive: http://127.0.0.1:8793/runs/catcher-specialist-v3/review/index.html
- Dataset: `../synthetic-demonstrations/accepted-state-action.npz`
- Actor and contract: `../synthetic-demonstrations/actor.npz`, `skill.json`
- Checkpoint SHA256: `72efdce7479f87c36a629cc307f7908c98ddd3c24eba8e3c030812b3568075c9`

## Limits to say plainly

This is an experimental simulated positioning skill, not a deployed harvesting
system. Robot self-collision dynamics are disabled, and a separate proxy-distance
screen found convex-proxy overlaps; the visible meshes did not intersect at one inspected terminal pose. This narrow check does not validate all trajectories or the contact proxies. Plant, gripper and actuator
parameters are not calibrated to hardware. The net is a visual rest shape;
fruit/net contact, cutting, damage prediction, perception and multi-skill
composition are not demonstrated. Exported episodes pass the specified simulator
criteria, not a real-robot safety or transfer test.

YAM geometry/model credit: I2RT Robotics, MIT license retained at
`assets/robots/yam/LICENSE`. The plant and catcher are the project’s shared assets.
