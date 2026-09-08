# Machine-tending learning experiment

The task is to unload a finished rectangular stock from a powered vise, release it into an output tray, pick fresh stock, load it into the vise, clamp it, and withdraw the gripper. The final independent evaluator applies a 1 N sideways force for 0.3 s and requires stable seating and clamping afterward. This represents the loading portion of an established machine-tending application, not a simulated cutting process or a hardware-ready CNC cell.

Use the skill library in `apps/skill-studio` to view current and historical runs. Its live data source is `runs/skill-studio/skills.json`; generated artifacts remain outside Git.

## Reproduce

From the repository root with the simulation Python environment:

```sh
PYTHONPATH=src:tools python tools/train_machine_tending.py --episodes 8 --out runs/machine-tending-bc-v1
PYTHONPATH=src:tools python tools/refine_machine_servo.py
```

The second command expects the first run's two demonstration datasets. It writes `runs/machine-tending-structured-v2` and refuses to overwrite it. Run directories contain proposals, checkpoints, action/qpos logs, per-seed traces, reports, and labeled videos. The raw stock XY position varies by ±10 mm. Shape, mass, friction, orientation, fixture position, and cameras do not vary; this is narrow position generalization.

## Learning boundary

The first candidate fits two 13→48→48→7 MLPs to analytic local-motion labels along physical teacher trajectories. Both initial and trained candidates scored 0/5 development trials: the trained candidate stalled at the first approach. Its near-zero input still produced cross-axis and jaw motion, so the failed candidate is preserved rather than promoted.

The second candidate tests a much narrower family: two axis-separated seven-gain feedback controllers fitted by gradient descent, with explicit vector-norm motion limits. This is 14 fitted parameters, not a neural VLA, learned planning, or evidence of a novel manipulation strategy. It tests whether a restricted controller can execute the complete physical cycle without the MLP's drift. The target construction, phase sequence, grasp transform, IK, robot motor control, and vise commands remain engineered in both candidates.

Six of eight scripted teacher collection episodes passed; two aborted at the force limit while seating. Demonstration datasets contain teacher-labeled prefixes from all eight episodes, including the unsuccessful ones. Training seeds 56000–56007 and development seeds 57000–57004 are separate. Reserved seeds 58000–58019 must remain unused until a candidate is frozen; development performance must not be called final held-out proof.

The physical objects have free joints, contact-driven grasping, and a force-driven vise. The controller asserts that it does not change live qpos. MuJoCo parameters and simplified geometry are not calibrated to hardware. See the task README for exact evaluator criteria and limitations.

## Second candidate results

The restricted controllers improved from 0/5 initial to 2/5 fitted development trials. Seeds 57000 and 57001 passed; 57002 timed out with 39 of the required 50 final stable-hold steps; 57003 and 57004 exceeded the force limit during seating. The candidate is not promoted. Fitting took 4.27 seconds on CPU, excluding demonstration generation and physical evaluation. No final reserved seeds were run. Watch `runs/machine-tending-structured-v2/trained-57000.mp4` for a successful development trial and inspect the report for all failures.
