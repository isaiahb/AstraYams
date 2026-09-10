# Harvest speed: objective and measured baseline — 2026-09-10

The user wants human-competitive speed while protecting fruit, plant, basket and
the other arm. Optimize the throughput of accepted fruit, with physical
acceptance checks retained. Speed is not yet improved or retrained in this audit.

## Human comparison

- [Development of a General-Purpose AI-Powered Robotic Platform for Strawberry
  Harvesting (2026)](https://www.mdpi.com/2077-0472/16/7/769) reports an estimate of
  1–3 seconds per fruit for trained human workers. This is a rough picking
  reference, not a measured human baseline for our clip/catch/net/basket workflow;
  the passage does not establish equivalent start/end conditions.
- [Bhattarai et al., published study, arXiv v3
  (2026)](https://arxiv.org/abs/2503.22809v3) reports 6.85 minutes average tray-fill
  time and 75.07% average picker efficiency from season-long commercial strawberry
  field data. These values differ from the earlier preprint's 6.22 minutes and
  73.56%; use v3. This is a stronger reminder to include non-picking time. Do not
  convert trays into berries using an assumed fruit count.

For an eventual human comparison, time the same start/end states, target
accessibility, container distance, quality inspection and recovery requirements.
Report both individual cycle latency and whole-cell accepted fruit/hour. Two arms
cooperating on one fruit do not independently double throughput. Human-relative
speed cannot yet be computed from this simulation.

## Recorded simulation baseline

| Recording | Phase | Seconds |
| --- | --- | ---: |
| Five-PPO partial-chain-v6 | Both arms position concurrently | 5.86 |
| Same continuous episode | Fine alignment | 3.46 |
| Same continuous episode | Clip | 0.18 |
| Same continuous episode | Release/retreat until timeout | 10.02 |
| Scripted basket-commission-v8, separate reset | Carry already-caught fruit | 3.54 |
| Same commissioning episode | Lower | 0.76 |
| Same commissioning episode | Unload and settle | 11.38 |

The learned fruit cut occurs at 9.48725 s; sustained retention is confirmed at
12.52 s. Retreat times out at 19.52 s, so no learned basket placement follows.
Scripted placement completes at 15.68 s from an already-caught reset. These times
must **not** be added into a claimed completed full cycle.

Recorded peak actual joint speeds (50 Hz samples, not substep maxima): learned
catcher 0.238 rad/s, learned cutter 0.103 rad/s; scripted catcher 0.231 rad/s.
The scripted joint-target slew cap is 0.006 rad / 0.02 s = 0.3 rad/s. Existing PPO
action caps are 0.75 rad/s of catcher target slew and 0.4 rad/s cutter target slew;
clipping scales the latter by 0.25. These are distinct from actual velocities,
torque limits, tool speed and hardware ratings. Policies are often commanding
less than their caps, so simply increasing a cap does not address all hesitation.

Reproduce the immutable-recording audit:

```sh
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/audit_harvest_speed.py \
  --runs runs/harvest-skill-suite/partial-chain-v6 runs/harvest-skill-suite/basket-commission-v8 \
  --out runs/harvest-skill-suite/speed-audit-2026-09-10
```

The JSON records source hashes, separate actual-velocity and target-slew statistics,
phase durations and missing full-cycle results. Timing is also attached to new
composed and scripted commissioning evaluations. Existing recordings stay intact.

## Next training protocol

1. Finish the retreat-to-carry handoff and learned placement under the existing
   checks. A fast partial success does not constitute productive harvesting.
2. Fine-tune on real predecessor-policy terminal states; retain the second arm
   during training where its reaction matters. Reduce approach/alignment delays
   and unnecessary pauses before chasing the already-short cutting action.
3. Express time cost as `lambda_time * elapsed_sim_seconds`. The present joint
   skill already pays 0.03 each 20 ms step (1.5 reward units/second), in addition
   to pose/action costs. The support reward still has dense positive dwell
   rewards; audit that incentive before increasing speed pressure. This document
   proposes a new reward experiment; it does not claim those changes are trained.
4. Reward earlier valid completion and penalize wasted travel/oscillation.
   Do not reward velocity itself. End unsafe episodes as failures, and include
   their elapsed/recovery time in throughput so quick failures cannot win.
5. Run faster through verified clear space and decelerate before contact. Bound
   velocity, acceleration, torque and payload motion. Clearance must account for
   stopping distance, latency, model uncertainty and the complete swept geometry.
   Retrain with the changed command dynamics; do not multiply saved policy actions
   at demo time and imply the old validation still applies.
6. Compare fixed development sets at several speed-pressure settings, then freeze
   selection and evaluate unseen anatomy, positions, stiffness, payload mass,
   friction and latency. Report success fraction, p50/p95 completion time, all
   failures, peak contacts, impact energy/impulse and placement-score distributions.
   Preserve original contact/hold criteria. Fast-and-rough candidates remain rejected.
7. Add repeated fruit selection, already-collected fruit, basket occupancy and
   ready-for-next evidence before reporting operational berries/hour. Keep playback
   at 1× for speed comparisons, including the full interval through settled release.

The current model has unresolved same-arm collision coverage and uncalibrated
tissue/actuator dynamics. Its passes cannot establish a human-safe operating speed
or bruise-free handling. [I2RT's actual control
interface](https://doc.i2rt.com/products/yam) exposes joint position/velocity and
motor torque commands; our finite-PD model and rate caps are not a validated
hardware operating envelope.
