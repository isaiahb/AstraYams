# Live learning demo contract

The keyed-insertion prompt configures a fresh copy of the prepared environment,
then launches a new learning job. Earlier library examples remain separate.

The run first freezes development seeds 4600–4602 and holdout seeds 4900–4902.
It evaluates an initially untrained grasp controller, trains new acquisition and
lift models using the existing prepared teacher data, and evaluates the complete
chain again on the same cases. Alignment and insertion checkpoints stay fixed.
This is supervised imitation learning; it is not a new PPO or VLA experiment.

The job publishes checkpoints, data/source provenance, actual training and
evaluation durations, all trial outcomes, and fresh body-state recordings.
The viewer can replay those recordings from any camera angle. It must not show
the older 20/20 or 4/5 results as the score for the new job.

Acceptance requires development improvement without a holdout regression. Failed
or non-improving candidates remain visible and cannot be labelled successful.
No object attachment, teleportation or reset between composed skills is allowed.

For presentation: launch Build & learn, inspect the two existing examples while
the job runs, then return to its new Before/After result. State that the geometry,
teacher dataset and downstream skills were prepared; the new grasp training and
evaluation ran now. Treat runtime as measured, not a promised one-minute delay.

This closes the bounded prepared-task learning loop. Arbitrary prompt-to-CAD,
autonomous reward redesign, camera-only control and manual-vise training remain
separate capabilities to implement and validate.
