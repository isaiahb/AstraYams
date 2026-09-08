# Reproducible state-policy learning loop

Current free-peg/curriculum results and the bounded DAgger experiment are documented in [STATE-LEARNING.md](STATE-LEARNING.md). The tested free-contact learned candidates remain unsuccessful; historical rigid-attachment results below do not transfer to them.

This pipeline trains a compact learned state policy for the articulated six-axis YAM arm, with the earlier Cartesian fixture retained as historical pipeline evidence. The policy is a two-hidden-layer, 128-unit tanh MLP trained by behavioral cloning. YAM observations contain 31 values, including privileged simulator goal errors; the historical fixture has 21. This is **not a VLA**, camera policy, learned grasp, or physical validation. The scripted teacher is used only when collecting demonstrations; learned rollout inference consumes the observation tensor alone.

## Articulated YAM adapter

The same collector and MLP trainer accept an environment-class adapter. The YAM task uses joint-delta actions on the articulated arm and a task-specific scripted IK teacher:

```sh
PY=/tmp/clonebench-cad-env/bin/python
$PY tools/check_yam_task.py
$PY tools/record_yam_task.py --out runs/yam-teacher-recording
$PY tools/collect_demonstrations.py --task tasks/yam_keyed_insertion \
  --env-class astrafactory.yam_env:YamEnv --teacher astrafactory.yam_env:teacher \
  --out runs/yam-demonstrations
$PY tools/finetune_skill.py --task tasks/yam_keyed_insertion \
  --env-class astrafactory.yam_env:YamEnv --data runs/yam-demonstrations \
  --out runs/yam-state-bc --epochs 150
$PY tools/record_yam_task.py --mode learned \
  --checkpoint runs/yam-state-bc/policy.pt --out runs/yam-learned-recording
```

Finish scene generation and styling before collecting data: task-file changes invalidate dataset/checkpoint hash matching. `check_yam_task.py` explicitly checks that the teacher does not assign the physical joint state and that successful teacher rollouts move the arm. The recorder saves the actual MuJoCo joint trajectories and actuator controls alongside its video. The video frames are post-step; the transition file contains pre-action state, action, and next state. Camera training data still requires the collector's `--camera` mode.

The final frozen YAM task uses six joint-delta actions and a 31-value state. Its corrected held-tool transform places the peg tip 170 mm from the gripper frame. The separately saved physical check reported teacher 10/10 and hold 0/10 on seeds 0–9. The data collector retained 64/64 successful training episodes (100–163) and 16/16 successful development demonstration episodes (1000–1015).

| YAM learned run | Epochs | Independent development rollouts, seeds 2000–2019 | Failure outcomes |
|---|---|---|---|
| Initial behavioral cloning | 150 | 3/20 successful | 13 force-limit aborts, 4 timeouts |
| Resumed supervised fine-tuning | 300 total, continuation learning rate 0.0002 | 5/20 successful | 15 force-limit aborts |

These paired development results establish a working training/resume loop and some genuine learned insertion executions, **not a reliable YAM skill or a final held-out improvement claim**. Resume used the same demonstration dataset and preserved normalization, optimizer state, task hashes and environment source hash. Lower imitation MSE (4.07e-5 to 3.39e-5 on development demonstrations) did not remove drift during learned rollouts. The arm policy still frequently develops orientation/action errors and triggers contact aborts. All episodes remain in each report.

The checkpoints and reports are `runs/yam-state-bc` and `runs/yam-state-finetuned`; the dataset is `runs/yam-demonstrations`. No seeds 5000+ were used in this development work. Freeze a candidate before a separate final evaluation; do not tune against that final report.

The actual teacher video is `runs/yam-teacher-recording/teacher.mp4` (seed 0, 539 actions, 10.78 simulated seconds, success with zero contact). The initial learned policy has both a successful video at `runs/yam-learned-recording/learned.mp4` (selected development seed 2000) and a failed video at `runs/yam-learned-failure-recording/learned.mp4` (seed 2001, force abort). These individual examples must be presented alongside the aggregate score, not as evidence of consistent success.

The fixture instructions/results below are historical development evidence for the reusable pipeline; their 20/20 score does not transfer to the articulated YAM arm.

## Historical fixture: collect demonstrations

```sh
PY=/tmp/clonebench-cad-env/bin/python
$PY tools/collect_demonstrations.py --out runs/bc-demo \
  --train-episodes 64 --development-episodes 16
```

Default training seeds are 100–163, and development demonstration seeds are 1000–1015. Splits are entire episodes, never shuffled transitions from the same trajectory. Every rollout is retained, including failures; collection does not filter on success. The dataset manifest records seeds, termination reasons, physical metrics, task-file and referenced external mesh hashes, environment source hash, teacher identity and source hash, and per-episode file hashes. Seed ranges must be disjoint, and seeds 5000+ are reserved for final evaluation.

The default `check_task:teacher` is explicitly a privileged, keyed-insertion-specific scripted teacher. For another task, supply an importable `--teacher module:function`; the callable receives `FactoryEnv` and returns one bounded action. This is a reusable dataset/training interface, not an automatic teacher generator for arbitrary CAD.

Each compressed NPZ contains `state`, `action`, `next_state`, `reward`, `terminated`, `truncated`, and pre-action `sim_time`. With `--camera`, it also contains pre-action `image` (RGB uint8, 240×320) and `proprioception` (16 values for this fixture). At index `t`, the image, state, proprioception, and timestamp all describe the simulator before `action[t]`; `next_state[t]` describes its result. Camera recording is optional and can substantially increase disk usage. No language conditioning or model-specific camera adapter is implemented. The state trainer ignores camera arrays.

## Train and independently evaluate

```sh
$PY tools/finetune_skill.py --data runs/bc-demo \
  --out runs/bc-baseline --epochs 150 --eval-episodes 20
```

Normalization uses training transitions only. The development demonstration split supplies an MSE diagnostic; it does not provide gradient updates. The independent rollout evaluation defaults to seeds 2000–2019, absent from both demonstration splits. It counts all episodes using the unchanged environment success/abort/horizon rules. Development MSE and success rate are different quantities; imitation loss alone cannot establish insertion success.

`policy.pt` stores model weights, Adam optimizer state, observation normalization, architecture, task hashes, accumulated training/development seeds, RNG state, epoch count and dataset provenance. `report.json` records the actual per-episode outcomes and training loss history. Checkpoints are trusted local pickle-based PyTorch artifacts; only load ones you trust. Generated artifacts remain under ignored `runs/` directories. Each command requires a fresh output directory to prevent mixing or overwriting runs.

## Resume supervised fine-tuning

```sh
$PY tools/collect_demonstrations.py --out runs/bc-finetune-demo \
  --train-episodes 32 --development-episodes 8 \
  --train-seed-start 200 --development-seed-start 1100
$PY tools/finetune_skill.py --data runs/bc-finetune-demo \
  --resume runs/bc-baseline/policy.pt --out runs/bc-finetuned \
  --epochs 25 --eval-seed-start 2020 --eval-episodes 20
```

Resume restores normalization and optimizer state, resumes the torch RNG, and trains on the supplied dataset. `--learning-rate` sets the resumed learning rate. Previous datasets are not automatically replayed; include them in a deliberately assembled dataset if retention requires that. Training/development seed separation is checked across the full checkpoint lineage. Task hashes and observation/action dimensions must match the checkpoint and dataset; incompatible task revisions fail instead of silently changing the experiment.

This is supervised fine-tuning on demonstrations, not reinforcement learning or autonomous reward optimization. The generic PPO entry point remains available separately in `tools/train.py`.

## Frozen final evaluation

After selecting and freezing a checkpoint using development data, run once on untouched seeds:

```sh
$PY tools/finetune_skill.py --resume runs/bc-baseline/policy.pt \
  --eval-only --eval-seed-start 5000 --eval-episodes 50 \
  --out runs/bc-final
```

Final seeds are accepted only with `--eval-only`, which performs no optimization or checkpoint save. The report labels the evaluation as final. The scripts cannot prevent a human from repeatedly inspecting final reports; do not use those outcomes to tune the model. Compare policies on the same frozen task and paired seeds when making an improvement claim. Geometry/evaluator changes require a new experiment and reevaluation of all compared policies.

## Verified development run (2026-09-08)

With the prepared local interpreter and the task hashes stored in the run reports:

| Run | Training | Development rollout seeds | Successes |
|---|---|---|---|
| Scripted teacher dataset | 64 train + 16 development episodes | 100–163, 1000–1015 | 80/80 collected |
| Learned BC baseline | 150 epochs, 64 teacher episodes | 2000–2019 | 20/20 |
| Resumed learned policy | 25 additional epochs, 32 new teacher episodes | 2020–2039 | 20/20 |

The baseline development imitation MSE was 0.000920; resumed development MSE on a different demonstration split was 0.001014. These are different splits, not a loss-improvement comparison. Both learned rollout sets had a peak contact metric of 0 N: these executions aligned and descended through the nominal clearance without contact. They do not demonstrate force-guided correction, recovery from jamming, or robustness outside the configured reset distribution.

Resume verification confirmed unchanged normalization, changed weights, 175 accumulated epochs and 96 accumulated training seeds. A camera episode had 96 synchronized pre-action frames; every saved transition exactly matched a seeded replay. A separate checkpoint-only reload reproduced development execution. These are development feasibility results, not a before/after improvement claim or a final held-out score. Checkpoints and full reports are local ignored artifacts at `runs/bc-baseline`, `runs/bc-finetuned`, and `runs/bc-camera-check`.
