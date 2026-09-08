# YAM machine-tending simulation v0

The robot unloads one stock from a powered vise, deposits it in an output tray, picks up raw stock, seats and clamps it, then releases and retracts. Both stocks are independent free rigid bodies, each 18 × 14 × 70 mm and 40 g. Original articulated YAM finger meshes and their convex contact pieces are retained. There are no object welds, attachment equalities or runtime object-pose assignments.

## Interface and locations

`MachineTendingEnv` takes seven normalized robot joint-target increments. `command_vise(gap_m)` separately commands a physical sliding jaw; this scripted machine interface is not a learned robot output. Its permitted target gap is 12–40 mm, with 39 mm recommended for opening and 12.5 mm for clamping. A bounded ±20 N motor uses 3000 N/m position gain and 30 N·s/m damping. These are simulation assumptions, not calibrated industrial-vise parameters.

| Location | Position in metres |
| --- | --- |
| Vise seat, stock bottom | (0.32, 0, 0.020) |
| Output tray floor centre | (0.24, 0.10, 0.004) |
| Raw tray floor centre | (0.25, −0.10, 0.004) |

The stock grasp centre is 54 mm above its bottom site. Vise jaw tops are 40 mm above the bench. End stops leave a 22 mm opening for the stock's 18 mm width. Tray floors are 4 mm high; deposition commands must respect this floor.

`task.select_part('finished'|'raw')` changes references only. Compatibility fields include `sid`, `pid`, `peg_joint`, `pa`, `peg_body`, `pick`, `goal` and `desired_rotation`. `active_contacts(env)` returns selected-stock force magnitudes from the left finger, right finger and other supports. The older MicroGrasp helper hardcodes the raw body and is unsuitable for the finished stock.

## Reset variation

Only raw-stock X and Y are randomized: independent uniform offsets of ±10 mm around its tray centre. Its initial bottom is 0.1 mm above the floor. Finished stock starts 0.1 mm above the fixed vise seat. Both stocks have the same fixed vertical orientation and 180° world-Z rotation. Robot joints start at one fixed pose above the finished stock, independent of raw-stock position. Vise position starts at a 14 mm gap and its controller targets 12.5 mm; closure settles through physics.

No mass, friction, lighting, camera, stock geometry, vise pose or orientation randomization is enabled. Five reset seeds were checked: initial robot joints were identical while raw positions differed, and no reset passed success. These checks do not establish generalization beyond this limited reset distribution.

## Independent acceptance

The evaluator uses actual stock geometry, motion and contact forces, independently of the workflow's selected part or phase:

1. The vise must have opened beyond 30 mm. Finished stock must have risen above 40 mm with bilateral finger contact, then been released entirely inside the output region. All eight corners must be within ±36 mm XY of the output centre, between 2 and 100 mm in Z, with linear speed below 20 mm/s and finger contact below 0.05 N.
2. After that deposit, raw stock must have risen above 25 mm with bilateral finger contact. Its final bottom must be within 1.5 mm XY and Z of the seat, with full rotation error below 3° and linear speed below 10 mm/s.
3. Raw stock must contact each vise jaw above 1 N, have less than 0.05 N total finger contact, and the fingers must be open beyond joint position −15 mm. Tool height must exceed 130 mm.
4. Once these conditions hold, a fixed 1 N world-X force acts at raw stock's centre of mass for 15 controls (0.3 s). After the pulse, 50 consecutive valid control states are required. Recovery from a temporary deviation during the pulse is allowed; the rubric does not require uninterrupted validity during the pulse. The first post-pulse state counts toward the 50 states.

The finished stock must remain in its output region throughout the final hold. Any aggregate contact-load peak above 80 N aborts; this sum includes all scene contact-force magnitudes and is not a wrist force sensor. All controllers share a 4000-control horizon (80 simulated seconds). The task reward is terminal success only.

## Scope and limitations

This models contact-based unloading, loading and clamping, not cutting or material removal. Raw and finished stocks have identical geometry with different appearance. Vise back-body overlaps are excluded from machine self-contact; original arm self-collision limitations remain. Contact sums do not establish individual normal forces or hardware safety. The retention pulse is a fixed lateral disturbance, not a cutting-load model.

The 42-dimensional observation contains privileged simulator state. This task does not by itself establish sensor-only deployment, real-hardware performance, generalization to new part geometry, or an autonomously learned workflow. Robot motion, machine commands, reward and evaluator evidence should be reported separately.
