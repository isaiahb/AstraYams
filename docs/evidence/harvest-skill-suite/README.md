# Two-arm specialist PPO work ledger — 2026-09-10

Objective: compose joint-level learned support, cutter approach, clipping, withdrawal, transport and gentle release. Two official YAM models, finite motor torques, contact-held catcher, jaw-driven CAD shears, dynamic plant and textile. The full composed objective is **not yet achieved**.

## Evidence and failures retained locally

- `runs/dual-harvest-commission-v13`: prior contact repair. Learned catcher; scripted cutter. Not a learned full harvest.
- `runs/harvest-skill-suite/population`: six seeded anatomical variants built through the existing V4 plant mechanics and photograph-derived outline families. Fruit count, maturity, branch dimensions, leaf number, height, mass and outline change. Fixed-camera render for comparison. Engineering distributions, not measured population statistics. Seed 72002 failed settling and is excluded.
- `population-cells`: compilation of those same physical plants into both YAMs; startup/contact audits. A valid stationary workcell is not a policy success.
- `clip-v2`: local open-jaw clipping PPO development passed 3/3. A disk-full error interrupted the next save. Last valid checkpoint is round 2. No full-approach claim.
- `clip-v3`: broader approach-plus-clip failed 0/8 full-scene local holdouts. Split approach from clipping instead of counting a scripted approach as learned.
- `withdraw-v2`: 1/4 local full-scene holdouts. Reduced curriculum incorrectly froze the net at its unloaded shape despite initializing a caught fruit. Large artificial net forces invalidate that curriculum for post-contact skills. `dynamic-net-curriculum` retains all textile DOFs; `withdraw-v3` retries it.
- `basket-commission-v1`: rejected; Jacobian incorrectly used the independent free tool instead of the gripper-mounted proxy. `basket-commission-v2`: rejected basket-wall contact; fixed wrist orientation near a joint limit and per-joint clipping distorted the path. `basket-commission-v3`: testing an offline feasible upright path and gradual wrist rotation with finite motors. All three are scripted mechanical tests, not PPO demonstrations.

## Contracts and scoring

- Approach: coordinate six cutter joints, jaws open, align with target and settle before clipping.
- Clip: seven learned joint/jaw actions, actual blade contacts and accumulated cut work; ends at stem separation. No pose/velocity edits on release.
- Withdraw: six cutter joints, clear stalk while catcher remains held under finite motor forces.
- Carry: six catcher joints, retain fruit, arrive above receiving basket upright.
- Unload: six catcher joints, release and settle fruit into basket without unintended scene contact.
- Coordinator must require physical entry/exit conditions, preserve simulator state across handoffs and stop on invalid contact. No hidden IK fallback.

Placement rubric awards a 0–100 score only on successful settling. Provisional quality is `100 exp(-E/0.001 - Fpeak/2 - Jexcess/0.02)`: preimpact relative kinetic energy in J, peak normal force in N, excess impulse over static weight for the first 150 ms in Ns. The receiving basket has finite mass and rests on a shelf. A passive vertical liner spring represents cushioning. These are **uncalibrated engineering proxies**, not bruise, crushing, vine tearing, basket buckling or hardware validation.

Known limits: privileged simulator-state policies, no cameras; same-arm self-collision still unresolved; one designated cuttable fruit per episode; no morphology generalization or complete learned basket placement established yet. Final validation must restore full canopy and dynamic net; frozen geometry curricula never count as full-physics evidence.
