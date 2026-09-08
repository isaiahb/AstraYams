# Free-peg contact validation

The contact task replaces the earlier prepared rigid attachment with a genuinely free MuJoCo body. The six-axis YAM arm closes its actuated gripper around a separate peg resting on the bench. Contact and friction must support the peg's weight. No grasp result is inferred from the earlier rigid-attachment task or its learned-policy score.

`tools/check_yam_contact.py` checks four conditions independently of the task's insertion-success flag:

1. The peg has a free joint, a world-body parent, downward gravity, no mocap assignment, and no connecting/welding equality to the robot.
2. The scripted controller raises the peg tip at least 20 mm above its reset height and reaches the scripted lift-hold phase and sustains that elevation for at least 0.5 seconds with contact forces from both actual finger bodies and no contact force from a supporting surface.
3. From that suspended grasp, negative gripper joint commands open the fingers. The peg must fall at least 20 mm within two seconds, finger joint opening travel must exceed 2 mm, and both finger contacts must release.
4. A fresh, identically seeded simulation replays the successful lift's exact joint/gripper action sequence with every geom and explicit contact-pair friction coefficient set to zero. The arm must attempt at least 20 mm of upward travel, while the peg must not rise 20 mm. Replaying commands avoids an adaptive teacher refusing to attempt a lift in the negative test.

Contact forces are computed directly from MuJoCo contacts against the `free_peg` body's geometry and descendants of `tip_left`/`tip_right`. The checker does not trust the controller's contact labels to establish support. It records actual positions, velocities, actuator controls and actions. It also verifies that calling the scripted teacher does not change execution joint positions. Initial reset placement and the arm's numerical IK are separate from physics stepping; the teacher must not teleport the peg.

```sh
PY=/tmp/clonebench-cad-env/bin/python
$PY tools/check_yam_contact.py --out runs/yam-contact-checks
$PY tools/record_yam_contact.py --camera insertion --out runs/yam-contact-recording
```

The recorder generates separate lift, release/drop and zero-friction videos, plus complete transition traces and a report. Video frames describe post-step physics; trace entries preserve the pre-action observation, action and next observation. These are scripted physical experiments, not learned-policy demonstrations.

```sh
$PY tools/record_yam_contact.py --insertion --camera insertion --out runs/yam-contact-insertion-recording
```

`--insertion` attempts and records insertion only after all contact validations pass. The resulting insertion attempt is labelled separately and uses the unchanged task success flag. A failed insertion is retained as a failed attempt. A passing grasp check alone does not establish insertion, mating, retention after release, or hardware performance.

These tests can expose geometric caging or an unintended ledge: if the zero-friction peg still lifts, the negative control fails even if the normal-friction lift looks convincing. A failed check must be investigated rather than replaced with a weld, a position override, or a relaxed acceptance threshold.

## Measured outcome, 2026-09-08

The actual free-body grasp checks passed for the fixed pickup/fixture arrangement at seed 0. This task currently uses a fixed reset, so repeated seed labels do not establish randomized robustness.

| Check | Actual result |
|---|---|
| Free object | Separate 40 g body, free joint, world parent, no mocap or attachment equality |
| Closed-gripper lift | Maximum tip rise 89.4 mm; stage-3 unsupported bilateral-contact hold 0.50 s |
| Suspended contact forces | At the end of the hold: left 1.10 N, right 2.06 N, other support 0 N |
| Open/release | First verified drop 23.5 mm in 0.22 s; downward velocity 0.215 m/s and both finger forces 0 N |
| Zero-friction replay | Same 755 commands raised the tool 91.0 mm; peg tip's maximum excursion was 13.25 mm, below the 20 mm lift criterion; peg ended supported on the bench |
| Full insertion attempt | Failed with a force-limit abort: tip Z 40.01 mm, XY error 2.78 mm, orientation error 0.1166 rad, peak summed contact-force metric 85.57 N |

The zero-friction result does **not** mean the peg never moves: its tip has a 13.25 mm transient excursion. It does show failure to achieve the specified lift while the same arm commands raise the tool, followed by support on the bench rather than suspension by the fingers. The open-release video continues through two simulated seconds to show the actual fall and settling, while the report retains the first verified release time.

This establishes an acquired, contact-supported simulated grasp and gravity-driven release in the measured arrangement. The original insertion attempt failed. The failure is preserved rather than replaced with an attachment or a passing animation. The earlier rigid-attachment learning scores do not apply.

The complete closeup evidence is in `runs/yam-contact-evidence`: `lift.mp4`, `drop.mp4`, `zero-friction.mp4`, `insertion-attempt.mp4`, per-step traces and `report.json`. `runs/yam-contact-overview` records the same experiments with the full-arm camera. The reports include task/referenced-asset hashes and environment source hashes; generated recordings remain ignored artifacts. The earlier independent static/physics report is `runs/yam-contact-full-lift-checks/report.json`.

These are simulator measurements, not physical gripper calibration or hardware safety limits. Finger collision meshes, inertias, friction, actuator gains and contact solver settings remain model assumptions.


## Feedback correction and narrow curriculum

The new `astrafactory.contact_teacher:feedbackteacher` corrects the gripper pose from the measured free-peg pose after pickup. It aligns above the rim and retracts under excessive force. It writes commands only, uses scratch state for IK, and preserves the free body and original insertion acceptance thresholds.

The fixed-reset run succeeds in 724 steps (14.48 simulated seconds), with tip height 9.210 mm, XY error 0.165 mm and peak summed contact-force metric 9.715 N. Independent grasp, release and zero-friction checks pass again.

The separate `yam_contact_curriculum` task randomizes peg and socket XY independently within ±2 mm and varies their shared yaw within ±0.02 radians. Seeds 0–4 all succeed with this scripted controller. This is narrow reset variation, not broad robustness or independent angular misalignment coverage.

The synchronized overview/closeup video is `runs/contact-teacher-video/scripted-contact-insertion.mp4`, explicitly labelled scripted feedback controller. Initial learned state-policy candidates fail. Camera-based VLA fine-tuning is a separate experiment; controller success does not establish learned performance.
