# Keyed insertion physics review

Reviewed 2026-09-08 against the source hashes recorded in `runs/review/reset-probes.json`, using Python 3.12.14 and MuJoCo 3.12.0 through `/tmp/clonebench-cad-env/bin/python`. This review changed no task, controller, geometry, reward, or acceptance criteria.

The current task supports a reproducible demonstration of physically stepped, clearance-fit insertion with a four-DoF held-tool fixture. No false success was found through the tested normal-reset action trajectories. It does not establish full-arm feasibility, grasp acquisition, learned contact control, or hardware performance.

## Executed evidence

Full episode outcomes are in `runs/review/physics-probes.json` and `runs/review/reset-probes.json` (generated local evidence, excluded from git).

| Probe | Result | Interpretation |
| --- | --- | --- |
| Existing alignment-first teacher, fresh review seeds 100–149 | 50/50 success | Broader feasibility check; these seeds are now development evidence, not untouched final tests. |
| Uniform random actions in [-1, 1], seeds 100–109, at most 400 steps | 0/10 success | No accidental success in this bounded sample. |
| Maximum-speed blind descent `[0, 0, -1, 0]`, same 10 seeds | 0/10 success | Physics blocks unaligned descent. Maximum episode contact metric was 21.47 N. |
| Alignment-first offset targets, seeds 100–102: +0.75 mm X, +0.75 mm Y, or +0.5/+0.5 mm XY with +0.04 rad yaw | 0/9 success | Even poses within the evaluator's loose XY/yaw bounds are blocked when the actual profiles overlap; final tip height was approximately 40 mm. |
| Alignment-first targets +3 mm X or +0.4 rad yaw, same three seeds | 0/6 success | Gross misalignment is blocked near the socket top. |
| Alignment-first target +0.049 rad yaw, same three seeds | 3/3 success | Transformed peg profiles fit inside the actual opening; this accepted yaw offset was not a collision shortcut. |

The offset policy used the existing teacher's target-increment construction, with half-scale actions. It first aligned to the modified XY/yaw target at Z=58 mm, using 0.1 mm XY and 0.005 rad gates, then commanded Z=9 mm. All runs ended on termination or the 400-step horizon. Profile checks transformed the design polygon into the socket frame and measured `peg.difference(opening).area` using Shapely, with the opening constructed by the generator's 0.6 mm mitred buffer.

All 50 teacher successes had zero measured contact load throughout their episodes and zero peg cross-sectional area outside the opening at acceptance. This is a useful positioning baseline with collision constraints. Its success alone is not evidence that contact feedback, compliant search, or tactile behavior has been learned.

## Actionable findings

1. **Keep reset overrides out of scored evaluation.** `Task.reset` accepts `options['initial_pose']` with joint-limit/finite checks only. At seed 123, resetting at the goal then holding succeeds in 15 steps without an insertion trajectory. Starting at Z=6 mm, below the 8 mm floor, settles and succeeds in 16 steps. Starting 3 mm into a wall at Z=9 mm also settles and succeeds in 16 steps. These are explicit reset overrides, not a normal policy-action exploit. A benchmark runner should own the reset distribution, disallow such overrides for scored episodes, and record any curriculum overrides separately. The evaluator measures a final held state; it does not prove a preceding insertion path.
2. **State speed units explicitly.** `task.py` computes one maximum across three linear velocities and yaw rate, comparing it with `speed_max=0.015`. The present behavior means every translation component is below 0.015 m/s and yaw rate is below 0.015 rad/s. This is operationally consistent but the reported `speed` scalar has mixed units. Document those component bounds now; use separate named linear/angular thresholds in a versioned future task. Do not silently change the frozen criterion during policy comparisons.
3. **Validate controller assumptions before accepting another task package.** The core assumes each configured joint has one position and velocity coordinate, finite meaningful limits, and a correspondingly ordered, unit-gear torque/force motor. It does not check joint type, transmission/gear, actuator dynamics, vector lengths, or whether limits are enabled. A position actuator, non-unit gear, unlimited hinge, or ball/free joint can load but invalidate PD semantics. Current keyed-insertion motors and joints satisfy these assumptions. Supporting another controller requires explicit validation or an adapter.
4. **Treat nonfinite termination as incomplete error plumbing.** The core detects nonfinite state after task evaluation and reward calculation, then calls `_observation()`, which raises on nonfinite values. Thus a numerical failure can raise rather than return the advertised terminal transition. No instability was observed in these probes; this is a source-level robustness issue for future task packages.

## Mechanics and acceptance assessment

The CAD coordinates are metres. The 38 mm convex peg and nine convex wall prisms preserve the keyed opening; the triangulation area check covers the socket ring. The socket floor occupies Z=0–8 mm and walls end at 40 mm. The model uses actual bounded motor forces during stepping; joint positions are assigned only on reset. A 2 ms physics step and ten substeps give 50 Hz actions. Translation action increments are 1.5 mm and yaw increments are 0.025 rad before policy scaling. Translation force bounds are ±20 N and yaw torque is ±0.6 N·m.

The controller's specified 150 g body mass and translational gains imply an overdamped free-space response (approximately 1.30 damping ratio); yaw is moderately damped (approximately 10.1 Hz natural frequency and 0.79 damping ratio). These estimates concern the specified lumped fixture inertia, not any robot arm. The bounded rollouts showed stable settling and physical blocking without visible numerical failure in returned states; they are not an exhaustive stability proof.

Success requires alignment, a tip height of 7.5–12 mm, the component speed bound, load below 15 N, and 15 consecutive control-step checks (0.3 s). Its 9 mm goal is above the 8 mm floor. It consequently proves held insertion depth/alignment, not bottom contact or retention. Its XY tolerance (0.8 mm) is larger than nominal clearance (0.6 mm); the tested interfering offset paths were still physically rejected, but success should not be relabelled a strict geometric nonpenetration test. MuJoCo contact is compliant, and the reset-overlap example settles with micrometre-scale wall penetration.

The contact metric sums the magnitudes of all contact force vectors and takes the maximum over ten substeps. It includes every scene contact, not only tool/socket contacts. That is acceptable for this simple fixture's conservative simulation metric, but unrelated contacts in a future task would contaminate it. It is not a wrist wrench. The 45 N abort check occurs after the control step; it does not stop at the first offending substep. Provisional mass, friction, soft-contact parameters, fixed roll/pitch, exact privileged pose observations, and rigid attachment limit transfer claims.

## Reproduction notes

Use the existing `tools/check_task.py` teacher for positive runs. For reset probes: reset seed 123, copy `env.task.goal`, optionally set Z to 0.006 or add 0.003 to X, reset again with the same seed and `options={'initial_pose': pose}`, then apply zero actions until termination. The reset-probe JSON records initial poses, final outcomes, MuJoCo warning counters, interpreter/library versions, and source SHA-256 hashes. All three reset probes had zero MuJoCo warnings.

Before claiming learned improvement, keep the task/evaluator fixed, retain blind-descent and no-op controls, and score policy execution on a runner-owned fresh reset set. Report scripted feasibility and learned policy performance separately.
