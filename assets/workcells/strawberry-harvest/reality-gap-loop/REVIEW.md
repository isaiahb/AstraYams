# CAD and physics review — candidate revision

The baseline demo is preserved. These trials use a scripted controller, not a trained policy. Success still requires the fruit to physically remain in the basket.

## CAD
Lowered the camera-facing catcher walls from 46 mm to 26 mm, reducing their mass proportionally. In the same initial camera view, visible cup-floor pixels increased from 4,572 to 5,834 (+27.6%); visible active-fruit pixels increased from 12,076 to 13,314. This is a visibility result, not proof of improved retention. CAD STEP solids pass geometric validity checks; they are concept parts, not manufacturing-ready assemblies.

## Physics and control
Made the basket containment wall colliders visible. Broadened stem contact filters to include interactions previously ignored. Cutting work threshold and success criteria were unchanged. A subsequent release candidate checks the actual outlet corners against the basket opening, rim clearance and cup orientation, replacing a precise center-height gate. No per-step object teleporting or tool-to-hand weld was added.

## Trials

| Trial | Collected | Time (s) |
|---|---:|---:|
| Baseline seed 1 | 3/3 | 34.12 |
| CAD only seed 1 | 3/3 | 33.88 |
| Broader contacts seed 1 | 2/3 | 50.0 |
| Combined seed 1 | 3/3 | 36.58 |
| Combined seed 2 | 3/3 | 34.0 |
| Combined seed 3 | 2/3 | 50.0 |

Combined revision completed 2/3 runs; the third seed timed out with the last berry still in the cup. The previous baseline also completed 2/3 runs, so this is not evidence of higher overall reliability. Single-seed comparisons are exploratory, and trial time limits differed from the earlier baseline suite.

## What reality still demands
1. Solve approach feasibility before training varied layouts. A stalled cutter was approximately 60 mm from its target with joints near limits; reset-pose IK did not establish a feasible trajectory. Tested yaw/IK branches did not resolve the entire path.
2. Inspect retained-fruit failure and tool slip/deflection. Refine tool seating and outlet geometry before relaxing release checks further.
3. Measure grasp friction, jaw force, actuator limits, stem fracture work and fruit damage in hardware. These remain assumed, uncalibrated parameters. A simulated cut is a simplified constraint fracture, not validated tissue mechanics.
4. Test time-step/contact sensitivity and held-out layouts. Camera mounts are based on the official YAM assembly, but depth/noise/intrinsics still need hardware calibration.

The immediate next candidate should address repeatable tool seating and release clearance; retain the lowered rim only if multi-seed retention tests support it.
