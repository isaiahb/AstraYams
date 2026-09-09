# Physical observation and calibration protocol — prepared, not executed

Purpose: determine which errors come from shape, attachment, constitutive law, or numerical approximation. Current photos cannot identify stiffness, damping, friction or fracture. No real measurements have been collected in this project.

## Specimens and records

Assign specimen IDs before experiments. Record cultivar if known, maturity, substrate/container, watering time, ambient conditions, dimensions, image calibration, tool geometry and all sensor uncertainties. Preserve raw time series/video. Split by specimen and capture session, not adjacent video frames. A preliminary pilot can use three calibration and three untouched evaluation plants; this is a feasibility study, not a population-level sample-size claim.

Capture a scale and camera calibration board, then front, side, top and crown close-ups without rearranging the plant. Track corresponding crown, attachment, branch, leaf-tip and fruit landmarks across views. Separately label uprooted, trimmed or manually spread specimens; do not use their growth angles as standing-plant ground truth. Hidden structure remains uncertain. Repeated annotators/views estimate reconstruction uncertainty.

## Isolate the responses

| Experiment | Record | Parameters/effects it can constrain | Confounds to control |
|---|---|---|---|
| Quiet plant under gravity | 3D landmark positions and drift | Loaded geometry and settling | Unknown unloaded shape, leaf/fruit mass |
| Small reversible push at two stalk heights in two directions | Calibrated probe force, tool/stalk displacement, base rotation, release video | Effective bending, cross-section anisotropy, crown support | Probe sliding, contact with adjacent organs, root/soil motion |
| Leaf brush near midrib and edge | Force, tool position, surface displacement and recovery | Bending/twisting/vein effects, contact geometry | Thickness, anisotropy, moisture, fixture constraint |
| Neighboring fruit interaction | Motion of both fruit, stalks and crown; contact force | Coupled load paths, friction and inertia | Unseen leaf/branch contact |
| Separate anchorage observation | Crown/soil displacement during nondestructive stalk loading | Fixed vs compliant root boundary | Soil moisture, pot wall support, root disturbance |
| Separate cutting/retention study | Tool pose, opening, force, displacement and separation event | Fracture/cutting law and retention | Tool sharpness, cut location, tissue condition; must not reuse damaged stems as intact controls |

Determine nondestructive force/displacement limits on separate pilot specimens, using instrument resolution and observed recovery. No invented biological force limit is prescribed here. Record aborted tests and permanent deformation. Run sensor/fixture-only negative controls to identify friction, backlash and camera drift.

## Fit, reject, and evaluate

1. Fix measured geometry/mass first where available. Do not hide geometric error by fitting tissue modulus.
2. Compare models with a fixed and a compliant crown; base motion can otherwise masquerade as flexible tissue.
3. Fit force–displacement and release transients jointly on calibration specimens. Estimate plausible parameter intervals and identify non-unique fits.
4. Check residual patterns. Direction-dependent errors suggest anisotropy; rate-dependent errors suggest viscoelasticity; irreversible events need a damage/fracture model, not just a new spring value.
5. Declare numerical and task tolerances using measurement uncertainty and harvest clearance/damage requirements before evaluating untouched specimens. Include both force and displacement errors, recovery times, contact location error and failure-event predictions.
6. Validate numerical resolution separately. A converged wrong constitutive model remains wrong.
7. Publish held-out errors and domain limits alongside cost in wall seconds per simulated second. Only then choose a cheaper surrogate or reduced representation and test it against both the detailed model and independent measurements.

## Machine-readable measurement columns

`specimen_id, session_id, split, experiment, trial_id, time_s, probe_x_m, probe_y_m, probe_z_m, force_x_n, force_y_n, force_z_n, crown_x_m, crown_y_m, crown_z_m, target_x_m, target_y_m, target_z_m, contact_label, event_label, uncertainty_note`

Keep missing observations empty, not zero. Save units, coordinate transforms, synchronization/calibration metadata and video references separately. Source research supplies priors; synthetic trajectories must never be stored in the real-observation dataset without an explicit synthetic label.
