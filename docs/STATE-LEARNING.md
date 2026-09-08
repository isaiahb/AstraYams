# Free-contact state-policy learning results

The feedback teacher solves the free-peg task, but the tested learned state policies do not yet solve it. These are privileged-state behavioral-cloning/DAgger experiments, not a VLA or camera-policy result. No final seeds 5000+ were used.

## Data and policy contracts

The policy consumes 42 physical/controller observation values and emits seven actions (six arm joints and gripper). A configurable 64-observation history supplies temporal context; teacher stage and teacher actions are never policy inputs. Training/inference window alignment and reset padding were checked directly.

The collector retains every episode and records the command actually executed in `action`, the expert supervision in `teacher_action`, and the source selection in `executed_teacher`. Optional executed-action noise and DAgger mixtures are explicitly recorded. DAgger maintains the learner's observation history on every step, including steps controlled by the expert. Camera/proprioception/action interfaces were not changed.

The fixed-reset data has one unique initial state and trajectory despite different seed labels. Its initial MLP (300 epochs) and noisy-data resume (700 total epochs) each failed the one fixed-setup rollout. Those runs do not measure generalization.

The separately versioned `yam_contact_curriculum` varies peg/socket XY by ±2 mm and common yaw by ±0.02 rad. Initial collection used eight training and two development episodes; all succeeded and had distinct starts. DAgger1 added eight training/two development episodes with 80% expert execution; DAgger2 added twelve training/two development episodes with 50% expert execution. Those mixed-controller episodes succeeded, but must not be counted as learned-policy successes.

`tools/merge_demonstrations.py` combines compatible manifests without duplicating arrays. The final aggregate has 28 training and six demonstration-development episodes. It preserves source manifests and forbids duplicate/cross-split seed reuse. All training uses expert labels, including on states reached by learner actions.

## Actual learned rollout outcomes

| Candidate | Total epochs | Development seeds | Success |
|---|---:|---|---:|
| History-window BC | 200 | 2000–2004 | 0/5 |
| DAgger1 resume | 400 | 2000–2004 | 0/5 |
| DAgger2 resume | 600 | 2000–2004 | 0/5 |
| DAgger2, unchanged | 600 | 2200–2204 | 0/5 |
| DAgger2, explicit output clipping | 600 | 2200–2204 | 0/5 |
| Bounded tanh-output resume | 900 | 2200–2204 | 0/5 |

The clipped baseline and bounded retraining use arm output limits ±0.4 and gripper ±0.5, matching the demonstrator's command envelope. These are explicit model/evaluation configuration changes; environment physics and acceptance were unchanged. The bounded candidate adds `tanh` scaling inside the model and received one 300-epoch continuation. No further fitting followed that attempt.

## Failure diagnosis

`tools/diagnose_state_policy.py` queries the teacher for diagnostic action labels only and asserts that this cannot change policy observations, physical joint positions or targets. On the bounded candidate's seed 2200, action error exceeded RMS 0.05 by step 27, during approach. Bilateral finger contact occurred at step 143, but no bilateral unsupported 20 mm lift occurred. Maximum peg-tip rise was only 2.14 mm; the rollout aborted at step 180 with a 103.82 N peak contact metric.

Earlier unconstrained models extrapolated to the environment's ±1 action limits outside demonstrated states. One DAgger1 diagnostic lifted the peg far beyond the intended height and then force-aborted; this is a failure, not an improvement claim. Output bounding removed that unconstrained model parameterization but did not establish a working grasp/insertion policy.

## Reproduction and storage

Use `--env-class astrafactory.contact_curriculum:CurriculumEnv`, `--teacher astrafactory.contact_teacher:teacher` and `--task tasks/yam_contact_curriculum`. Training options include `--history-steps 64 --width 128 --activation relu`. DAgger collection adds `--learner-checkpoint ... --teacher-execution-probability 0.8` (or 0.5 for the second round). Bounded continuation adds `--output-scales 0.4 0.4 0.4 0.4 0.4 0.4 0.5`; the clipped baseline uses `--eval-only --action-clip-scales ...`.

Local disk exhaustion interrupted one checkpoint save. That failed-save run produced no candidate; it was rerun on remote CPU, with the GPU reserved for separate VLA work. Frozen state artifacts reside under `/workspace/astrafactory-state/runs/`, including `contact-bounded-policy`, `contact-dagger2-dev2200`, `contact-dagger2-clipped-dev2200`, aggregate manifests, source datasets, earlier checkpoints and `diagnose-*` traces. Preservation of this directory was requested before pod shutdown. Reports/checkpoints contain actual task hashes, source information, model configuration, normalization, optimizer/RNG state and seed lists.

The scripted teacher's contact-grasp/insertion evidence and the separate VLA experiment must be assessed independently of these failed state-policy candidates.
