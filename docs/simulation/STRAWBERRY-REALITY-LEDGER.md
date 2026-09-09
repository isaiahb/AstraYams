# Strawberry reality ledger — 2026-09-09

## Baseline and changes
The v8 source checkpoint remains at `AstraFactory-harvest-study-20260908/bimanual/plant-physics/checkpoints/2026-09-09-botanical-v8/`. SHA-256 fingerprints are in `strawberry-audit-checkpoint.json`.

Existing work: crown/petiole/fruit-branch hierarchy; curved, tapered segmented stalks; three hinged panels per leaflet; mesh-based berry collision; attachment collision exclusions; gravity settling and a force-limited berry probe; untouched control and recovery comparison. Robot, tool and camera geometry were preserved. This replaces decorative/static plant parts with articulated contact geometry, but does not validate real plant response.

New work: full probe-contact accounting plus independent leaf, stalk and berry attempts, each with a no-contact control. Exact target names and every incidental contact are recorded. A failed approach remains a failed approach, even when another leaf visibly moves.

## Parameter status
| Item | Current representation | Evidence status |
|---|---|---|
| Botanical topology | Crown, trifoliate leaves, branching fruit trusses | Primary anatomy reference; procedural specimen |
| Stalk mechanics | Tapered capsule chain, rotational stiffness EI/L | Beam approximation, not measured tissue |
| Elastic modulus | Approximately 80–120 MPa by stalk type | Assumed prior |
| Damping | Stalk damping proportional to stiffness | Assumed, requires recovery calibration |
| Leaf mechanics | Three rigid mesh panels with hinge springs per leaflet | Coarse approximation; not membrane deformation |
| Leaf angles | Baseline nearly horizontal; new rest-angle candidate | Visual hypothesis, not measured cultivar variation |
| Fruit | Rigid mesh collision and attached mass/inertia | No bruising/deformation model |
| Detachment | Fruit attached in articulated hierarchy | Cutting unavailable in this candidate |
| Probe | 12 mm sphere, position servo, ±2 N per axis | Diagnostic fixture, not robot gripper |
| Contacts | Simulator soft contact, recorded penetration | Numerical model; no real contact calibration |

## Explicit next promotion gates
1. Review canopy candidate at rest from multiple views; check overlap and visible/collision agreement.
2. Compare quiet-rest motion with baseline; no warnings is necessary but insufficient.
3. Confirm each intended leaf/stalk/fruit target receives contact. Incidental contact must be reported and approach design revised before claiming isolated validation.
4. Compare deflection and recovery against matched controls; test timestep and segment sensitivity before physical-accuracy claims.
5. Gather real force–deflection/recovery measurements. Preserve uncertainty until available.
6. Implement and independently test cutting/retention before training or presenting a complete harvest skill.

## Reproduction
Use the existing study assets and MuJoCo environment:

```sh
python tools/audit_strawberry_contacts.py --plant-dir /absolute/path/to/AstraFactory-harvest-study-20260908/bimanual/plant-physics
```

This command depends on the existing `multi-harvest` assets and `env_multi.py`, plus v8 scene and control rollout. It initializes each short diagnostic from the saved five-second resting position with zero velocities. That is an experiment reset, not physical robot motion. Trials then run four seconds at 0.5 ms steps. Generated rollouts remain local; reports and source are versioned.
