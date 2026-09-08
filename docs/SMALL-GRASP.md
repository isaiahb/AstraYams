# Compact grasp skill v1

This is a 5,252-parameter state policy with privileged simulator pose and contact inputs. It is not a camera policy or VLA. It predicts four absolute Cartesian/jaw command targets; a scripted scratch-IK adapter, upright yaw stabilization, and joint command limits execute those targets through the existing bounded PD controller. This changes the action abstraction from the VLA experiment, so their results are not an apples-to-apples comparison.

The frozen yam-contact-curriculum-v0 environment, physical contacts, and insertion evaluator were not changed. The skill never resets the environment or assigns execution qpos. Only the caller starts a new episode.

## Compact contract

The 12 inputs are handle-to-tool XYZ, peg/tool rotation error XYZ, tool and peg heights, jaw joint position, tool vertical speed, and separate left/right contact-force magnitudes. Pose is privileged ground truth; forces are simulated contact measurements, not calibrated hardware sensors. No teacher stage or elapsed-time feature is fed to the network.

The four outputs are commanded tool XY offsets relative to the peg, commanded tool world Z, and commanded jaw joint position. Training labels are obtained by forward kinematics of the next commanded joint targets in the demonstrations. Output values are bounded to the training command range. The nonlearned adapter bounds Cartesian travel to 2.5 mm per control call, arm deltas to ±0.4, and jaw deltas to ±0.5.

`GraspSkill(checkpoint).start(env)` records initial peg height. `act(env)` returns the seven environment actions. After stepping, `handoff(env)` checks at least 20 mm rise, both finger forces above 1e-5 N, nonfinger support below 1e-5 N continuously for at least 0.5 seconds at control samples, and current tip clearance of at least 65 mm. Duration is last timestamp minus first timestamp. No teacher stage or timer alone triggers handoff. The skill has no internal reset; transport and insertion can continue in the same physical state.

## One bounded experiment

Linux teacher episodes 100–107 trained the model; episodes 1000–1001 provided offline development error. Replaying their saved actions reconstructed contact inputs and command labels; maximum replay state discrepancy was below 5e-7. Segments cover approach, closing, lift to 83 mm, and 0.4 seconds afterward. Training used 400 epochs, Adam at 0.001, two 64-unit tanh hidden layers, training seed 31, and CPU only. Normalization uses training samples only.

All five rollout evaluations used new development reset seeds 2000–2004 with no teacher calls. No final seeds 5000+ were used. The one frozen candidate achieved **1/5 physical grasp handoffs**:

| Seed | Handoff | Maximum peg rise | Longest qualified support |
|---|---|---|---|
| 2000 | Fail | 20.72 mm | 0.06 s |
| 2001 | Fail | 16.74 mm | 0 s |
| 2002 | Fail | 0 mm | 0 s |
| 2003 | Fail | 26.38 mm | 0.22 s |
| 2004 | Pass | 64.01 mm | 2.40 s |

Seed 2004 reached tip Z 65.013 mm at step 731. It is evidence of a learned grasp under the explicit controller scaffold, not successful insertion. Failed rollouts demonstrate that low offline command MSE (0.000695 normalized development MSE) does not establish reliable closed-loop grasping. This candidate is not ready to replace the existing pickup policy. Further learning needs to address grasp acquisition and retention; this experiment does not isolate whether observation ambiguity, label conditioning, or feedback extrapolation dominates.

Generated artifacts are ignored under `runs/small-grasp-v1/`: checkpoint, report with task/source/data hashes and seeds, and every evaluation action/contact trace. Run:

```sh
PYTHONPATH=src python tools/train_small_grasp.py --data /workspace/contact-rgb-v1 --out runs/small-grasp-v1
```

This prototype implements the grasp module only. Transport/alignment and insertion are separate skills; composition and any scripted stages must be identified explicitly. The hybrid executor supports either VLA pickup or this tiny policy. A selected successful development start (seed 2004) completed learned pickup followed by scripted transport and insertion, continuously without resetting the world. This single selected composition is not a reliability estimate; grasp remains 1/5. See SKILL-COMPOSITION.md.
