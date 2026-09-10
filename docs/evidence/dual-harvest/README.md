# Two YAMs: cut and catch

The user’s deliverable is one coordinated harvest: one YAM carries the net
catcher, the second YAM closes its stock parallel jaws to drive the Rev-B bypass
blades. Positioning the catcher is a component skill, not the deliverable.

## Mechanical task contract

1. The free catcher is retained by physical finger contacts, with its rim under
   the target fruit. Its flexible fibers are collision geometry, not an image.
2. The cutter approaches the selected stalk without hitting neighboring fruit,
   the growing trough, the catcher or the other arm.
3. Closing the stock gripper drives the two bolted cartridges. No independent
   scissor motor, timed release or pose change is permitted.
4. A declared blade/stem fracture surrogate severs the stalk; the distal stalk,
   calyx and finite-mass berry remain in the simulated world.
5. Gravity and contact bring the berry into the net. Success requires physical
   contact and retained fruit for 0.5 seconds, with the catcher still gripped.

The arm receives bounded joint commands and finite-torque PD control. Same-arm
collision proxies remain unresolved; collisions between arms and with the plant
are enabled. Simulation evidence cannot certify bruise safety or hardware transfer.

## What is already learned

The frozen 2,406-parameter catcher PPO from `catcher-specialist-v3` is reused,
with its original observations and six joint commands. Its previous 23/24 score
is a positioning result in the old task, not a dual-arm harvest score.

`commission_dual_harvest.py` explicitly uses scripted Jacobian control to debug
the cutter. Commissioning is not PPO, behavioral cloning or a learned harvest.

## Research and approximations

- The Rev-B CAD includes actual finger-carrier masses, replaceable blades,
  clamping plates, screws and a free catcher frame.
- The full V4 specimen remains dynamic. A stalk capsule is split at a flat
  section; an integrity weld holds the two pieces until fracture. It introduces
  compliance and must be compared against the intact source.
- The net is a 97-node, 264-fiber 1D MuJoCo flex. The 1.5 g mass, 60 N/m edge
  stiffness, 0.015 Ns/m edge damping and coarse weave are explicit modeling
  assumptions. There is no hidden filled collision cup.
- MuJoCo flexes distribute element contact forces to their connected bodies:
  https://mujoco.readthedocs.io/en/stable/XMLreference.html#deformable-flex
- Peduncle experiments distinguish cutting force from gripping/crushing force:
  https://arxiv.org/html/2207.12552 . Table II reports mean cutting peaks roughly
  4–7 N for its cultivars/blade/test speeds. Those are context, not calibration
  of this tool, and are not fruit-bruising thresholds.

## Failed commissioning checkpoints

- v1: straight cutter approach contacted the trough; rejected.
- v2: a 25-degree approach cleared the trough but contacted a neighboring berry.
- v3: higher stalk cut position; cutter command accumulation produced an
  oscillatory approach and neighboring-berry contact; rejected.
- v4: resolved-rate commissioning command now targets the current joint pose
  plus a bounded correction, rather than accumulating full pose error.

Each run preserves its trace and failure. New runs snapshot the scene and tools.
Evaluation criteria must not be relaxed to obtain a passing demonstration.

## Contact correction, 2026-09-10

The user identified the cutter overlapping a neighboring strawberry in v6.
This was a genuine modeling defect, not something to fix only in the renderer.
The old carrier envelopes selected vertices in slices and omitted long faces
between CAD tessellation rings. Calyx leaves also had no collision geometry.

- `tools/cad_collision.py` clips triangle edges at slab boundaries, then creates
  conservative convex envelopes. It accepts STL seam discontinuities without
  relying on a solid boolean that can silently return empty geometry.
- The six carrier/cover/liner surfaces have 135,336 audited vertex/triangle-center
  samples. Previously 5,696 were uncovered; now zero are outside the envelope
  union at the 2 micrometre numerical tolerance. These are coverage checks,
  not tolerances of a manufactured tool.
- Each calyx component now has a rigid contact envelope on its original dynamic
  fruit body. It can transmit forces and torques through the plant. Sepal
  flexibility and material parameters remain uncalibrated.
- Replaying the old movement with corrected contacts failed at 3.798 s: a blade
  struck the neighboring calyx at 1.063 N. The run was rejected, not relabeled.
- Interpolating to the initial joint configuration dipped the cutter downward
  into the recoiling neighbor. Withdrawal now lifts 20 mm and retreats 35 mm
  in tool approach coordinates, through bounded joint targets and finite motor
  torques. It starts on the next control tick after the physical cut event.
- Contact records name the offending geometry. Target fruit/calyx-to-catcher-rim
  contact is classified as receiving contact; it still records force and overlap.
  It is not a collision with a neighboring fruit. The 0.8 N unexpected-contact
  and 0.8 mm monitored-penetration rejection limits were not relaxed.

### Evidence

`contact-fix/collision-audit.json` preserves the coverage and dynamic ablation.
Both ablation runs start from the **same already-cut physical state at 3.74 s**,
with the same motor commands and stem separation. Only cutter/plant collision
masks change in the explicitly labeled diagnostic counterfactual. With contact,
the neighboring calyx exerts a 1.512 N peak on the blade and deflects the plant;
without it the force is zero. Final neighboring fruit positions differ by
10.74 mm after 0.2 s. Neither run reports solver warnings. This comparison tests
contact causality, not measured botanical accuracy or harvest success.

`contact-fix/commissioning-results.json` preserves the failed approach and two
corrected full sequences:

| Check | 0.25 ms step | 0.125 ms step |
|---|---:|---:|
| Cut and retained, no rejection | yes | yes |
| Time observed after cut | 2.016 s | 2.018 s |
| Cutter contact with neighboring fruit/calyx | 0 N | 0 N |
| Inter-arm contact | 0 N | 0 N |
| Maximum monitored penetration | 0.138 mm | 0 mm |
| Net peak summed contact magnitude | 9.10 N | 11.11 N |
| Target calyx/rim peak | 4.52 N | 0 N |
| Catcher slip | 0.240 mm | 0.182 mm |
| Pose/velocity jumps at fracture | zero | zero |

The two steps agree on the task outcome and clearance, **not on detailed impact
forces or the exact catch trajectory**. Those remain timestep-sensitive and
uncalibrated; this is not evidence of bruise safety. Maximum penetration here
covers monitored tool/net contacts, not every leaf-leaf contact in the plant.
Same-arm self-collision is still unresolved.

The corrected orbitable replay is `runs/dual-harvest-commission-v13/review/`.
`tools/capture_dual_contact_review.cjs` captures its recorded poses from three
cameras, with a visible controller label. v6/v8 reviews are marked rejected.
The catcher remains a frozen PPO; the cutter is scripted commissioning. No new
PPO cutter training occurred during this physics repair.

Reproduce from the repository with the CAD/MuJoCo environment:

```sh
PYTHONPATH=src python tools/build_dual_harvest.py
PYTHONPATH=src python tools/commission_dual_harvest.py --out runs/dual-harvest-contact-check
PYTHONPATH=src python tools/commission_dual_harvest.py --out runs/dual-harvest-contact-halfstep --timestep 0.000125
PYTHONPATH=src python tools/audit_dual_contacts.py
```

The audit intentionally depends on preserved v6/v10 run fixtures. Commissioning
snapshots the task XML, meshes, trajectory, controls and controller source hashes.
The sparse-face regression in `tests/test_cad_collision.py` also runs without
those historical fixtures.
