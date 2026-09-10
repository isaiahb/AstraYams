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

Known limits: privileged simulator-state policies, no cameras; same-arm self-collision still unresolved; one designated cuttable fruit per episode; support-only held-out morphology evidence is described below; no complete learned basket placement established yet. Final validation must restore full canopy and dynamic net; frozen geometry curricula never count as full-physics evidence.

## Subsequent evidence

- Withdrawal v3: 3/4 local full-scene holdouts (73001–73004), 0/1 zero-command baseline. Retraining retained the dynamic net. This is still one cluster, not morphology generalization.
- Clipping v2 local full-scene check: 2/4 (63001–63004); approach-plus-clip remains rejected.
- Basket v4: fruit reached receiving basket but did not meet the settling-speed/hold contract; score remains zero.
- Linux net replay: same recorded commands at 0.25 ms timestep produced a transient 2.69 mm berry/fiber penetration at 0.16225 s with an active 0.393 N normal contact. At 0.125 ms the first 0.18 s had no penetration. Full release and further convergence remain to test. Thresholds were not relaxed.
- Real plant workcells: five passed a 1 s stationary contact test. These are validated startup states, not learned task successes.
- State-preserving handoff check: binding a skill preserves qpos, qvel and equality state byte-for-byte. PPO memory/goal changes only. Full composed rollout is still pending.

## Contact-preserving basket commissioning and current PPO work

- Basket v8 (Mac, 0.125 ms): physical release and settling passed at 15.68 s; no unintended, neighbor or inter-arm contact; maximum penetration 0.0083 mm; peak basket force 0.355 N, impact energy 8.75 microjoules, rubric 82.0/100. Remote v7 uses the same geometry/control and passed at 17.0 s with 0.494 N and 75.8/100. Both are **scripted commissioning**, not learned placement. Their differences also preclude claiming calibrated contact-force accuracy.
- The validated path offsets the receiving location toward the basket edge so stock fingers clear its wall, lowers the net before rolling the berry out, and preserves finite motor/contact dynamics. Failed v5/v6 numerical penetration and finger-wall contact remain retained.
- Carry/unload PPOs now observe 87 simulator-state features: the original joint/goal/nearby-geometry features plus payload position/velocity, net and basket contact, settling progress and impact measures. Six joint actions each, no runtime IK. Training uses actual recorded reset states with the dynamic net retained. No learned success yet.
- Clip v5: **7/8 full-dynamics local holdouts**, zero-action baseline 0/3. Selected checkpoint round 2, 2,535 actor parameters. These are aligned open-jaw starts with local encoder/stiffness variation; not a global approach or morphology-generalization result. An intermediate commentary incorrectly said 8/8 before the full report was read; the report and this ledger use 7/8.
- Partial-chain v1: support PPO reaches its condition; cutter approach stalls roughly 6 mm from the stalk. The coordinator times out, preserves the failed rollout and does not substitute a scripted motion. No full-chain pass.
- Population support uses a fixed encoder reference across different compiled plants. Subtracting each plant's different initial pose had removed configuration information. Carry/clip/withdraw binding likewise preserves its training encoder reference.

- Release-reset audit: v1 easiest state was already airborne before first basket contact. Stopped that run before any completed PPO checkpoint. v2 starts at recorded frame 404 (normal_z crosses 0.65) with a supported berry. A 4 s zero-action test retains it in the net and never places it.
- Loaded-net rigid curriculum: source is the already caught, loaded state (basket v8 frame 0), unlike the rejected unloaded-net curriculum. Carry zero-command resets at difficulties 0, 0.5 and 1 passed initial contact checks. Unload resets failed with 3.7–4.2 mm geometric penetrations, so this approximation is **rejected for unloading**. Unload retains all textile DOFs.
- Same-arm geometry audit (both geom and body collision masks enabled): neighboring mating base/link1 surfaces, both finger pairs, and the catcher wrist/gripper convex envelopes overlap. This is a remaining collision-model limitation. Do not assert complete self-collision coverage or hardware safety from current passes. Documentation: https://mujoco.readthedocs.io/en/3.4.0/computation/index.html explains convex mesh collision and body filtering.

- Composition entry probe: the existing clipping PPO fails from the actual approach terminal state (~5.6 mm from the stalk). `clip-handoff-v1` now fine-tunes on that recorded upstream PPO state with joint/stiffness jitter and fresh evaluation seeds 65001–65008. No full-chain pass claimed.
- Contact accounting audit found two issues: only the berry geom's textile contacts were audited, and a detached target pedicel hitting the receiving rim was incorrectly classified as an outside-plant collision. The physics engine was already responding. Accounting now audits **every** net contact (including neighboring fruit, stems and cutter), and groups the cut branch's descendants as the received payload. All forces and penetration remain recorded; non-target contact thresholds are unchanged. New trials are required; previous failed reports remain intact.


## Learned alignment, physical cut and held-out morphology

- `align-v1`: a new six-joint fine-alignment PPO starts from the real coarse-approach terminal state. Full-dynamics final checkpoint passed 4/4 local tests (73001–73004); zero-action baseline failed. The composed chain uses round 1 selected on development (about 2.2 mm alignment), while the 4/4 report evaluates round 3 (about 2.7 mm). Do not conflate these checkpoints.
- `partial-chain-v5`: four moving specialists—support and coarse approach concurrently, then fine alignment and clipping—produce a physical cut at 9.4675 s. Both blade contacts about 2.77 N; work 1.502 mJ; qpos/qvel jump zero. No recorded unwanted, neighboring-plant or inter-arm contact. The fifth specialist, withdrawal, fails: closed blades retain the severed stalk and net contact stays zero. Complete episode retained and marked failed, not a whole-harvest demo.
- `remote/support-v3`: development counts progressed 5/6, 2/6, 6/6. Final round 3 passed **4/4** full-dynamics tests across two held-out anatomical plants, seeds 72001 (3 fruit, 7 leaves) and 72003 (2 fruit, 5 leaves). A fixed encoder reference is shared across plants. This is a small support-only generalization test, not evidence for clipping/carrying/unloading on those plants. Separate fixed-view replays show the actual morphology.
- `cut-release-v1`: one-jaw PPO on the actual learned cut state passed **0/4** full-physics tests. A constant maximum-opening diagnostic also fails on neighboring calyx contact (~2.13 N). Retrying more jaw-only training would not address the action-space limitation.
- `release-withdraw-v1`: transfer six-joint withdrawal policy weights into a seven-action joint/jaw PPO. New jaw output and four additional observation weights start at zero; training is PPO, no scripted jaw trajectory. `release-withdraw-v2` adds the frozen learned support PPO as a concurrent partner while the cutter retains the fruit. The partner holds its current motor targets after jaw opening or receiving contact; this is a skill-selection gate, not an IK path.
- `carry-v3`: near-end loaded-net curriculum improved position error but never passed development. Final full-net held-out tests failed. The frozen loaded-net approximation and limited start-distance curriculum are not adequate evidence of learned transport.
- `remote/wrist-release-v1`: two learned wrist commands, other four joints hold finite motor targets. Dynamic net retained. No success established yet. This restriction is explicit in the action space and must not be described as a six-joint policy.
- The review now labels support completion as SUPPORT POSITIONED, not RETAINED. Captures preserve failures and include controller provenance; a failed physical episode is not discarded or presented as a pass.


## Methodology learned from these experiments

1. Change anatomical parameters upstream of physics compilation; verify resting state and keep the camera fixed for comparison. Vary plant topology and payload physics, not just rendering.
2. Define skill success by physical outcomes and explicitly distinguish support positioning, cutting, retention, clearing and settled placement. Preserve reset states and failed trajectories.
3. Train on the **actual preceding policy's terminal states**. Passing isolated experts from scripted ideal starts did not establish composability.
4. Split coarse approach from millimeter alignment, but merge release with retreat when jaw opening alone strikes a neighbor. Decomposition follows the contact coupling; the smallest action space is not always sufficient.
5. Include the other learned arm policy during training when its response changes the transition dynamics. Freeze its weights and record its checkpoint identity.
6. Compare reduced training physics against full plant/textile dynamics. Reject a frozen unloaded net for loaded states, airborne release starts, or ignored contact categories. Full-physics failures remain failures.
7. Preserve checkpoints, controller provenance, state-preserving handoff assertions, untouched acceptance thresholds, report hashes and inspectable replay. A score is a proxy until material/robot experiments calibrate it.
