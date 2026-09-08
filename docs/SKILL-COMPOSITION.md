# Composing contact skills: measured prototype

Astra authored a grasp specialist and a guarded executor. This is a prototype of creating a missing skill and composing it with existing controllers, not an autonomous runtime LLM planner or an entirely learned assembly system.

## Results

The 5,252-parameter grasp policy achieved 1/5 handoffs on fresh development starts. Replay, CPU training and five evaluations took approximately 50 seconds (estimated from timestamps, not an isolated training benchmark). Its privileged simulator observations and scripted Cartesian/IK scaffold differ from the VLA experiment; this does not establish a speed advantage over VLA training.

Two selected continuous-world compositions succeeded:

| Pickup | Selected development seed | Steps | Simulated duration | Final XY error | Episode peak force |
|---|---:|---:|---:|---:|---:|
| SmolVLA v3 | 2000 | 692 | 13.84 s | 0.160 mm | 8.44 N |
| Tiny state policy | 2004 | 1138 | 22.76 s | 0.156 mm | 30.28 N |

Both use scripted pose-feedback transport and insertion after learned pickup. They demonstrate an interface, not representative composition success rates. Videos, actions, contact traces and reports live in runs/hybrid-composition-v1 and runs/small-hybrid-composition-v1 and are preserved in the private draft checkpoint release.

## Physical handoffs

The executor observes measured lift, bilateral finger contact and absence of nonfinger support for a sustained interval, plus clearance, before passing control to transport. Alignment gates insertion. It does not reset the world or reposition the peg between stages. The peg is a free body supported through contact with actuated YAM fingers. Ground-truth simulator sensing remains privileged; contact parameters are uncalibrated and arm self-collision is disabled.

Success is insert-and-hold under the frozen evaluator, not release or hardware validation. The evaluator uses XY 1 mm, orientation 0.06 rad and contact force 45 N with 15 consecutive qualifying steps; these differ from task.json's declared stricter limits. See CONTACT-VALIDATION.md. No thresholds were changed for these runs.

## Monolithic comparison context

Base SmolVLA and the 1,000-update checkpoint each scored 0/3 full-task development successes. The continued 4,000-update phase also scored 0/3, but one rollout physically held the lifted peg for 11.1 seconds. A further closing-weighted 2,000-update phase scored 0/3. These experiments motivated isolating acquisition from transport and insertion; they do not prove decomposition is universally superior. No reserved final seeds were evaluated.

## Next experiment

Train alignment and insertion separately on physically reachable states produced by the preceding skill, with different observations, rewards and action limits. Then evaluate the complete chain continuously on fresh starts, including grasp failures, slips and recovery. Do not train each skill on perfect resets and infer that their success rates compose.
