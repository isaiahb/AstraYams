# SmolVLA and compute readiness

Inspected 2026-09-08. No billable resources were provisioned or started by this investigation.

## Verified local status

`/tmp/clonebench-cad-env/bin/python` has PyTorch 2.14.0, MPS built and available, and no CUDA. A float32 MPS tensor forward/backward completed with finite gradients (0.565 seconds including first-use overhead). This establishes basic Torch operation only, not SmolVLA compatibility or training throughput. `lerobot`, `transformers`, `huggingface_hub`, and Python `runpod` were absent at inspection. Avoid disrupting the existing training environment: install VLA dependencies in a separate environment.

`runpodctl` 2.1.9 is installed at `/opt/homebrew/bin/runpodctl`. The `RUNPOD_API_KEY` environment variable exists; its value was neither printed nor written. No RunPod connector tool is available. Official REST `GET https://rest.runpod.io/v1/pods` and an official GraphQL read-only query both returned HTTP 403. Authentication/permissions or network access therefore need resolving before provisioning. This does not prove the key itself is invalid, and account balance/pod inventory could not be verified. The stated $35 credit remains user-reported.

## Exact custom embodiment adapter

The current checkpoint [config.json](https://huggingface.co/lerobot/smolvla_base/blob/main/config.json) declares six state values, six actions and three camera inputs. Loading that configuration unchanged is wrong for this environment.

- Replace input features with `observation.state: STATE (16,)` and `observation.images.camera1: VISUAL (3,240,320)`; replace output features with `action: ACTION (4,)`. Remove the unused camera2/camera3 feature declarations. Keep one real camera and no invented views.
- Convert wrapper `image` uint8 HWC to float32 CHW in [0,1]. Use the model's configured aspect-preserving padded resize (512×512); preserve the same camera and preprocessing for collection/evaluation.
- Map wrapper `proprioception` directly in its declared order: q(4), qvel(4), controller targets(4), previous action(4). Do not include privileged state21, relative socket pose, success info, or teacher internals during execution.
- Action order is X/Y/Z/yaw, with each component in [-1,1] representing increments of commanded targets, scaled by `[0.0015,0.0015,0.0015,0.025]` metres/radians per 50Hz step. Train on those normalized environment actions. Unnormalize the predicted action using this dataset's action statistics and clip to the environment bounds; do not scale twice or interpret outputs as SO100 joint angles.
- Keep internal `max_state_dim=32` and `max_action_dim=32`; the implementation pads shorter vectors. Both 16-state and 4-action fit without resizing network weights. This preserves checkpoint tensor compatibility, not pretrained control semantics.
- Recompute state/action mean/std from training episodes only; never reuse the base embodiment's six-value normalization. Use LeRobot policy processor pipelines for task newline/tokenization, device transfer, normalization and output unnormalization.
- Add task text such as `Insert the keyed peg into the matching socket.` to every episode. A single constant instruction does not establish language-conditioned task selection or general language understanding.
- Dataset frames must pair pre-action RGB/proprioception with that same step's teacher action; store episode boundaries, timestamps, 50fps metadata and explicit feature names. Future chunks must stay within episode padding conventions. Existing post-step video alone is not an aligned dataset.
- Base chunk size is 50 (one simulated second). Start with `n_action_steps=1` or 5 while keeping `chunk_size=50` for checkpoint compatibility, and measure inference latency. Fifty open-loop increments are a poor default near contact. Reset the policy action queue on every environment reset. Real-time 50Hz execution has not been established.

Source: current [SmolVLA configuration](https://github.com/huggingface/lerobot/blob/main/src/lerobot/policies/smolvla/configuration_smolvla.py) and [processor implementation](https://github.com/huggingface/lerobot/blob/main/src/lerobot/policies/smolvla/processor_smolvla.py). Pin the LeRobot commit and checkpoint revision in an actual run; main is mutable.

## Fastest credible path

The official [fine-tuning recipe](https://huggingface.co/docs/lerobot/main/smolvla) uses the pretrained 450M model and reports approximately four hours for 20,000 steps on one A100. It is a reference workload, not a prediction for this dataset or proof of task success. A complete one-hour VLA convergence claim is unsupported.

For the one-hour evidence window, use synchronized demonstrations and a compact camera-plus-proprioception behavior-cloning policy in the working local environment, then evaluate fresh fixed resets against the teacher and an untrained baseline. Label it a learned visual policy, not a VLA. If only state features train successfully, label that privileged-state policy explicitly. Measure physical evaluator success, contact peaks and failures rather than training loss alone.

In parallel with that deliverable, prepare a separate Linux CUDA LeRobot environment, load `lerobot/smolvla_base` with the custom features/stats, and run one forward, one backward and one bounded rollout before committing to long training. Preserve frozen vision encoder / expert-only fine-tuning defaults initially. A VLA smoke pass establishes integration only; a held-out success comparison is required to claim learning. No pretrained checkpoint or large dependency stack was downloaded in this probe.

## GPU choice and budget proposal

Public [RunPod dedicated Pod prices](https://www.runpod.io/pricing) inspected on 2026-09-08: A40 48GB $0.49/hour, RTX A6000 48GB $0.53/hour, RTX 4090 24GB $0.74/hour. These are advertised rates, not authenticated availability or a deployment quote. The [official current rental guide](https://www.runpod.io/articles/guides/ai-server-cost) lists A100 80GB at $1.59/hour. Recheck the actual offered rate before starting.

Prefer one A100 80GB if available at no more than $2/hour for turnaround and memory headroom. Cap the first attempt at two hours ($4 compute maximum), with a 15-minute installation/forward-pass checkpoint and a 30-minute first-training-checkpoint requirement. Abort a stalled setup rather than leave it billed. Alternatively use one A40/A6000 48GB at no more than $0.75/hour for a cheaper run, beginning with batch size 8 and measuring peak CUDA memory before increasing. A 4090 24GB is a plausible smaller-batch candidate, not a verified fit for batch64. None of these configurations has been memory-tested here.

Keep $25 as the maximum main campaign spend and $10 untouched reserve. Within the main cap, budget at most $20 compute and $5 storage/setup contingency; do not automatically spend the whole allocation. Stop after two hours to evaluate progress before extending. A price/time cap requires an external watchdog and verified stop/termination; a shell timeout inside a pod does not stop GPU billing. Download checkpoints/logs before deleting disposable resources, and account for storage that may persist after stopping. Do not create recurring resources or savings commitments for this experiment.

Provisioning prerequisites: resolve 403 responses, verify balance and live quote, prepare pinned environment/dataset, test headless MuJoCo EGL, and install a stop watchdog. The compact local policy path does not depend on these blockers.
