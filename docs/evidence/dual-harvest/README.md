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
