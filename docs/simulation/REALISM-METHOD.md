# Task-to-simulation realism loop

A reusable procedure for AstraFactory. Started 2026-09-09 from the strawberry environment review. Visual plausibility, numerical stability, physical accuracy and policy success are separate claims; each requires separate evidence.

## 1. Define the interaction before building the scene
Write the task, embodiment, tool, available sensors, required contacts, forbidden contacts, success conditions and failure conditions. Separate full-task requirements from the current diagnostic. Strawberry example: approach through foliage, support fruit, cut its pedicel, retain fruit, place it. The current botanical candidate supports contact diagnostics only: it has no detachment mechanism and is not a completed harvest task.

## 2. Establish references and a parameter ledger
Use primary anatomy/engineering references, real photos from multiple angles, dimensions and available response measurements. Record source, units, uncertainty and whether each parameter is measured, sourced, estimated or assumed. Images can support structure and appearance; they cannot establish stiffness, friction or cutting force. Generated concept images express intent, not ground truth.

For strawberries, the [NC State production guide](https://content.ces.ncsu.edu/southern-regional-strawberry-plasticulture-production-guide), morphology section, supports crown-rooted petioles with three leaflets and independently branching fruit inflorescences. It does not calibrate our simulated tissue properties.

## 3. Build one coherent specimen
Create a structural graph before multiplying objects. For plants: crown → petiole → three leaflets, and crown → peduncle → branches → pedicels → fruit. For manufactured tasks: assembly hierarchy, joints, tolerances and cable routes. Build from attachments, not from desired robot target locations. Distinguish unloaded geometry from the shape under gravity; avoid encoding sag twice.

## 4. Make rendered and physical geometry agree
Inspect collision overlays and cross sections. Record approximations: convex hulls, rigid fruit, segmented leaves, jointed beams. Thin concave geometry often requires decomposition. Check mass/inertia, contact masks, attachment exclusions and clearances. Exclude only physically joined regions, not inconvenient external contacts. Keep robot/tool/camera assets versioned and verify they did not change accidentally.

## 5. Freeze a baseline and isolate interactions
Save source and asset hashes, simulator version, timestep, solver settings, seed and parameter ledger. For every contact type run an untouched/control trajectory and a matching physical-contact trajectory. For strawberries: leaf brush, stalk push, neighboring fruit contact, then cutting and retention when implemented.

Log every contacted geometry, not just the intended class. Require evidence that the intended target was actually touched. Report unintended contacts. Record force, impulse, penetration, target deflection, settling, recovery and warnings. Identify resets explicitly; never present object teleports or attachment switches as physical behavior. A probe test is not a learned robot manipulation result.

## 6. Review motion and numerical sensitivity
Replay from useful camera views with scrub/orbit and collision inspection. Watch approach, contact, release and recovery. Compare smaller timesteps and finer discretization using predeclared tolerances; stability alone is not convergence. Reject unstable trials and retain their reports. A passing synthetic test only establishes simulator behavior, not biological or hardware accuracy.

## 7. Calibrate before claiming transfer
Compare force–deflection and recovery curves against real measurements. Fit on calibration specimens, assess on held-out specimens. Keep uncertainty visible when hardware is unavailable. Do not tune solely to make an animation attractive. Missing physical data becomes an explicit experiment request.

## 8. Randomize coherent causes, then train
Randomize bounded, plausible variables jointly: geometry, mass, tissue stiffness, maturation, pose, illumination, camera errors and control latency. Preserve structural dependencies (e.g. mass changes with size). Keep training and held-out seeds/configurations separate; include hard occlusions and adverse contacts. Do not use privileged simulator state at deployment without labeling the gap.

## 9. Promote with evidence
Each revision contains: hypothesis, minimal change, source/checkpoint hashes, parameter changes, tests, positive/negative controls, videos/replays, rejected trials, acceptance decision and remaining gaps. Promote only the claims supported by the results. Carry the same protocol across new tasks; change the interaction-specific tests and calibration data.

## Current strawberry evidence and limits
The existing v8 checkpoint added flexible segmented stalks, hinged leaf panels and physical fruit contacts, and passed its recorded quiet-rest and berry-probe sanity checks. Its canopy still looks overly flat and repetitive. Stiffness/damping/friction are assumed; berries are rigid; attachment topology currently prevents detachment. The next audit extends contact accounting to leaves and stalks before those interactions are described as tested. Shape refinement and measured calibration remain separate work.

## Reference-first specimen pass (2026-09-09)
The follow-up implementation is `tasks/strawberry_specimen/reference-graph.json` and `tools/build_strawberry_specimen.py`. It records visible image landmarks separately from hidden connectivity assumptions; consumes a manually estimated leaflet width profile; builds fruit from branch tips; places a compact crown at substrate level; and lets the truss settle onto a physical trough rim. The anatomical atlas includes crown/root photos, a crown section, leaf surfaces, branching trusses, fruit/calyx details and flower development. Camera matching and real physical calibration remain incomplete.

Review media are mandatory for this workflow: one whole-specimen view, a close-up for each altered organ, an orbitable mesh replay, and contact recordings with the probe visibly in frame. Check screenshots from the contact phase, not just a final resting image. Record occluded views as presentation failures and choose a clear camera without changing the physics.

## Loaded configuration, material frames and history

A visible pose does not uniquely determine rest shape, stiffness or stored
strain. Check attachment/material frames, actual COM and inertia before adding
new deformation models. Verify one isolated mechanics calculation independently
(for example gravity moment and rotational inertia about an attachment).

Use matched loaded-state hypotheses to expose non-identifiability. If rest shape
and stiffness both change to preserve that state, say so; do not attribute a
response difference solely to growth. Separate fast recoverable strain, delayed
recovery and persistent/growth-related shape. Identify each from observations
at the relevant timescale, rather than inferring them from appearance alone.

A diagnostic load-release experiment can disable a known connection to study
unloading. Label the imposed boundary event; it is not evidence of tool-driven
cutting or fracture. Preserve mass, inertia, instantaneous pose and velocity;
verify the temporary attachment transmits moments before release. Repeat with
an uncut control and a refined timestep. A failed attachment approximation must
be repaired and rerun, not counted as biological compliance. Keep the actual
tool/contact/fracture gate open until those interactions are implemented and
validated.

## Autonomous critique and next-goal selection

User request, 2026-09-09: derive subsequent goals from the values expressed in
their feedback. The agent owns routine diagnosis, prioritization and execution;
the user provides direction and corrections rather than serving as the only
reviewer who notices the next defect.

1. Re-read the active outcome and constraints. Preserve accepted design choices;
   keep product/UI work paused. Ask what a successful robot interaction needs
   from this model, not just what the last patch changed.
2. Inspect the delivered artifacts personally: whole object and altered parts,
   multiple useful views, resting behavior, contact, release and recovery. Look
   for the next likely objection: wrong form/attachment, missing support, false
   motion, mismatch between rendered and collision surfaces, or an untested
   assumption. Verify the issue rather than assuming the user would dislike it.
3. Convert each discrepancy into an observation, candidate cause and test that
   could distinguish causes. A list of caveats is unfinished work, not a way to
   dispose of the issue. Real-data gaps become measurement/research requirements.
4. Pick the next bounded milestone by consequence for the intended task, strength
   of evidence that the model is wrong, information gained by testing, and cost.
   Resolve dependencies first. A large error after an irrelevant ground drop may
   be lower priority than a smaller contact error at the intended grasp/cut site.
5. State the observable outcome and acceptance evidence before changing things.
   Continue the authorized experiment/fix; preserve comparisons and failures.
   Avoid a broad expansion into more organs, more fidelity or a new app merely
   because those tasks are available.
6. Review against the whole outcome again. Show the evidence and selected next
   goal during work. Local numerical success is a checkpoint, not automatic
   completion of the user's broader objective. If the next decision needs user
   knowledge or changes a material commitment, present that specific tradeoff.

The values behind this loop are causal realism, useful robot capability,
coherence of the complete object, visible evidence, durable/reusable progress,
and independent judgment. They are a working project brief, not a claim about
the user's preferences in every context. Update them when the user steers.
