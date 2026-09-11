# Supported pack: paired passive release experiment

The revised net deposits one test berry into the carriage-supported clamshell
and withdraws empty. It does this at both 0.25 ms and 0.125 ms physics steps.
**This is a partial mechanical result, not a qualified packing system.** The
tool still moves in the jaws, and the landing is not validated as gentle.

V7 stacked, direct SO-101 mounts and V8 remain preserved. No arm lifts a filled
clamshell. The shelf takes that load. This is an isolated packing bench with a
frozen lift and no growing tower, so it does not demonstrate harvesting,
collision-free transport from the plant, or filled-container exchange.

## Why the mechanism changed

| Trial | Observation | Decision |
|---|---|---|
| V9, single vertical cam | Gate hits the container floor; berry returns with the net. Tool shift 13.44 mm. | Provide room for the entire floor sweep. |
| V10, side actuation | Lever contacts the shelf web before the roller. | Reject this path; preserve the failed trial. |
| V11, outboard cam and lower pack | Clearance improves but the single lever twists the tool in the jaws. | Use opposing levers/rollers to balance lateral moments. |
| V12, paired rollers | Berry deposits; tool shift falls to about 3.18 mm. CAD support feet intersect the carrier. | Move feet underneath the deck. |
| V13, underside feet | Opposite column still intersects the carrier wall. | Step that column around the wall. |
| V14, offset column | Fixed fixture CAD clears, but the moving lever brushes the support. | Put the fork crossbar and column behind the lever's approach lane. |
| V15, rear-clearance fork | Deposition repeats at two timesteps; no unintended tool/fixture contact appears in the 50 Hz trace. | Preserve this partial result; address retention and landing next. |

The shelf is 10 mm inboard and 60 mm lower than V8. These offsets are design
choices, not new measurements of the photographed rig. The net floor is driven
through a transverse hex shaft by two levers at ±90 mm. Fixed rollers open it
as the arm lowers; a spring closes it as the arm withdraws. No runtime tool weld,
gate-angle assignment, berry teleportation or learned-policy claim is used.

CAD now includes the stepped column, rear-clearance roller forks, axles,
underside mounting plates, matching deck holes, countersunk M4 screw envelopes
and nuts. The roller supports clear 52 tested support/fixture solid pairs.
There is no volumetric interference in 48 floor/lever versus frame/ear checks
at eight sampled angles. These are fit checks, not strength certification.

## What was measured in V15

| Metric | 0.25 ms step | 0.125 ms step |
|---|---:|---:|
| Berry remains in clamshell after net withdrawal | Yes | Yes |
| Maximum floor opening | 88.04° | 88.03° |
| Maximum tool translation relative to jaws | 3.181 mm | 3.180 mm |
| Maximum tool rotation relative to jaws | 2.301° | 2.303° |
| Peak berry/container contact, every solver step | 10.02 N | 8.53 N |
| Berry speed at first container contact | 0.821 m/s | 0.755 m/s |
| Solver warnings | 0 | 0 |

The pre-existing grip criterion is below 1 mm and 2°. Both runs **fail** it.
The final berry surface, rather than just its centre, is checked against the
container's tapered inner envelope with a disclosed 0.5 mm contact tolerance.
The final skin penetrations are below 0.001 mm in this geometric check.

The two landing locations differ by about 57 mm. Similar deposition outcomes
do not establish convergence of bounce trajectories, robustness across plant
layouts or sim-to-real accuracy. Both runs share one initialized berry and one
scripted trajectory; changing timestep is not domain randomization.

Logging only at 50 Hz hid brief impacts: in the 0.25 ms run, the sampled
berry/container peak was about 0.67 N while the solver-step peak was 10.02 N.
Fruit forces are now measured at 4 kHz / 8 kHz. Other contact categories remain
50 Hz measurements and can miss short events. Neither set is a calibrated bruise
threshold. The rigid fruit/contact-compliance model needs physical calibration.

## Remaining design limits and the next useful work

1. **Retain the tool geometrically.** Use a compact keyed jaw adapter or a dock
   that takes opening torque. Raising friction until a preferred animation
   appears is not an acceptable substitute.
2. **Support the berry through handoff.** The hinged floor needs enough clearance
   to swing, which leaves a substantial drop. Compare a peeling/rolling net or
   another supported handoff before assuming a softer contact parameter fixes it.
3. **Recover a compact harvesting envelope.** The wide lever/shaft arrangement
   and front column are acceptable for this bench experiment, but have not been
   checked among leaves or against carrier exchange. Do not integrate them into
   a harvesting policy as if those checks had passed.
4. **Finish actual hardware details.** Gate spring, positive travel stops, shaft
   axial retention, axle retention and final thread/fastener selection remain
   engineering work. The current spring and hinge are idealized abstractions.
5. **Calibrate materials and fruit damage.** Friction, textile stiffness/damping,
   berry/contact response and container compliance remain assumed. Measure them
   and compare real bruise outcomes before claiming gentle handling.

The jaw and net-frame collision decomposition retains the disclosed 48-hull
limit from V9; it did not meet the requested 0.5 mm concavity target. Forks and
the stepped column use separate collision pieces so their open regions are
not filled by a convex hull. Rounded edges, holes and thread details remain
simplified in those collision proxies.

## Inspect and reproduce

The cel-shaded orbitable replay is `/runs/tower-lift-v15/gate-bench/index.html`.
It exposes both timesteps, measured tool motion, solver-step fruit contact peaks,
STEP assembly and individual part files. Recorded simulation states drive the
replay; camera controls do not change the experiment.

Using the project CadQuery/MuJoCo Python environment with `PYTHONPATH=src`:

```sh
python tools/build_single_pack.py --out runs/tower-lift-v15 --inboard-mm 10 --drop-mm 60
python tools/build_packing_gate_bench.py --run runs/tower-lift-v15 --opening-deg 75 --lever-offset-mm 90 --paired-rollers --underslung-feet --offset-second-column
python tools/setup_paired_packing_release.py --bench runs/tower-lift-v15/gate-bench
python tools/commission_packing_gate.py --bench runs/tower-lift-v15/gate-bench --name release-contact-audit --seconds 9 --grip-torque .7 --initial runs/tower-lift-v15/gate-bench/release-initial.npz --plan runs/tower-lift-v15/gate-bench/release-plan.json
python tools/commission_packing_gate.py --bench runs/tower-lift-v15/gate-bench --name release-refined-step --seconds 9 --dt .000125 --grip-torque .7 --initial runs/tower-lift-v15/gate-bench/release-initial.npz --plan runs/tower-lift-v15/gate-bench/release-plan.json
python tools/audit_packing_fixture.py --run runs/tower-lift-v15
python tools/export_packing_gate_cad.py --run runs/tower-lift-v15
python tools/audit_packing_gate_cad.py --run runs/tower-lift-v15
python tools/summarize_paired_packing.py --run runs/tower-lift-v15 release-contact-audit release-refined-step
python tools/review_packing_gate.py --bench runs/tower-lift-v15/gate-bench release-contact-audit release-refined-step
```

Initialization deliberately reuses the preserved V9 isolated release start by
joint name. V8 robot/collision assets and V9 initialization must exist first.
Each test records its full initial state, plan, timestep, torque cap and scene
SHA-256. Earlier local scene/STEP snapshots remain available. Compact historical
evidence is in `paired-gate-development-evidence.json`; final evidence is in
`v15-release-evidence.json` and `v15-gate-sweep.json`.
