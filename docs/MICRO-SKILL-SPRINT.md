# Small composable skills: measured sprint

The chosen chain has four learned controllers: acquisition (1,540 parameters), lift (1,540), alignment (72), and insertion (90). It passed20/20 reserved nominal starts5000–5019 and20/20 separate reserved stress starts5100–5119 after all weights were frozen. No reset or state restoration occurs between skills during scored composition. These counts describe two narrow simulated distributions, not guaranteed success or sim-to-real transfer.

## What Astra did

Astra used subagents to build skill candidates, inspect physical rollout failures, diagnose training guidance, run comparisons, and preserve decisions. The runtime executor itself is a deterministic guarded skill graph; no autonomous background LLM researcher or general task planner is claimed. The append-only ledger exposes proposed hypotheses, evidence, training changes, randomization, seeds, thresholds, model hashes and acceptance/rejection summaries. It does not expose hidden chain-of-thought or invent live agent status.

1. The earlier5,252-parameter grasp model passed1/5 starts. A new two-specialist model learns Cartesian and jaw commands with explicit physical reach/close/lift guards. The new model passed5/5 versus0/5 untrained under the same scaffold, then15/15 additional nominal and10/10 stress starts. Training took4.987seconds on CPU; collection, training and initial comparisons together took19.74seconds. This changes architecture, observations, labels and scaffold versus the earlier model; it is not an isolated decomposition ablation.
2. Alignment/insertion trained after teacher pickup worked in isolation, but composition with the new learned grasp passed only2/10 development starts2500–2509. Audited video shows retention succeeded while descent stalled.
3. Review found an insertion label bug: an angular guard used x[3:] and accidentally included velocity/load features. A new version uses only angular coordinates x[3:6]. It trains on24 physically reached learned-grasp/learned-alignment starts with mild training randomization. Corrected demonstration continuations passed24/24; fitted linear and nonlinear candidates both passed10/10 development. The90-parameter linear candidate was selected because the nonlinear model showed no measured gain. Collection, fitting both candidates and20 development evaluations took56.9seconds; this is not pure training time.
4. A genuine PPO vertical residual experiment ran8,192steps with a545-parameter actor in17.97CPUseconds. On paired full-chain seeds2400–2409 it regressed from6/10 to5/10 and was rejected. Its reward included absolute insertion-distance progress, alignment/load/effort penalties and actual success/force-abort terms. It is not in the chosen chain.
5. The corrected chain passed20/20 new nominal development and20/20 new stress starts. Only then were reserved final seeds evaluated, without fitting or selection afterward.

## Learning and control boundaries

Acquisition/lift models learn four commanded components (XYZ displacement and jaw increment). Target construction, pose estimation from the simulator, angular grasp stabilization, scratch inverse kinematics, bounded PD actuation and physical handoff guards are scripted. Downstream models learn six Cartesian corrections in engineered goal-error coordinates; jaw hold and IK are scripted. Their almost exact linear fit is essentially distilling local analytic feedback control. This is useful evidence for fast composable controller training, not a difficult visual manipulation breakthrough.

The peg remains a40g free body supported through contact with articulated YAM fingers. No weld, mocap or physical pose assignment is used during rollout. Arm self-collision remains disabled and contact parameters uncalibrated. Insertion is insert-and-hold, not release/retention or manufacturing quality validation. Videos replay saved actions and match every recorded telemetry value exactly; original rollout qpos arrays were not recorded, so no original-qpos comparison is claimed.

## Randomization and frozen evaluation

Training-mild-v1 independently varies peg mass/inertia scale and shared peg/finger sliding friction scale within0.9–1.1, peg/socket XY within±3mm, and shared yaw within±0.025rad. Stress-v1 uses0.8–1.2,±4mm and±0.04rad. These are declared engineering sensitivity assumptions, not calibrated hardware uncertainty. Changes happen at episode reset, never mid-composition. Grasp training used controller-state augmentation rather than dynamics DR; downstream training used mild dynamics DR. Nominal evaluation uses the original environment directly. A regression test verifies the nominal wrapper reproduces the original reset.

The actual frozen evaluator requires previous lift, XY<1mm, full rotation error<0.06rad, tip7.5–12mm, speed<15mm/s and load<45N for15consecutive steps; abort is80N and episode horizon1500steps. task.json contains stale stricter descriptive values (0.8mm/yaw0.05rad/15N). The implementation was never changed. Early ledger proposals that copied stale metadata are explicitly blocked from promotion; later confirmation/final proposals use the actual criteria. Both descriptions remain auditable.

## Run and inspect

```sh
PYTHONPATH=src python tools/run_micro_composition.py --grasp runs/micro-grasp-v1/policy.pt --downstream runs/downstream-v2-dr --insert-v3 runs/downstream-v3-corrected/linear.npz --out runs/my-new-development-check --seed 2800 --episodes 10
PYTHONPATH=src python tools/build_skill_observatory.py
python -m http.server 8769 --bind 127.0.0.1
```

Open http://127.0.0.1:8769/runs/skill-observatory/index.html. It contains final videos plus the unsuccessful chain and rejected experiments. The desktop app can also index the JSON, Markdown and MP4 artifacts under runs. The report is a snapshot of recorded evidence, not a live trainer dashboard.

Training entry points: tools/train_micro_grasp.py, tools/train_downstream_skills.py (preserved old-label experiment), tools/train_corrected_insert.py (corrected candidate), and tools/train_insert_residual.py (rejected PPO experiment). Output directories must be new. Generated data and weights remain ignored by Git and are preserved separately in the private checkpoint release. No GPU was provisioned for this sprint.
