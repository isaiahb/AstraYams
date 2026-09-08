# Camera-based SmolVLA experiment

## Runtime and budget

The experiment uses one RunPod Secure Cloud A100 80 GB at $1.59/hour.
Pod `dzvyvey4mpynmd` has a native stop deadline plus the local watchdog in
`tools/probe_runpod.py`: September 8, 2026, 21:11:45 UTC. The attempt cap is $4.
The pre-existing user Pod was not modified. A final status must verify shutdown;
an internal training timeout alone does not stop GPU billing.

Verified runtime: Python 3.12.11, PyTorch 2.11.0+cu128, MuJoCo 3.12.0 and LeRobot
commit `2774d9bddcbbda50e697e162e89e7eaada8d7105`.
SmolVLA base revision: `c83c3163b8ca9b7e67c509fffd9121e66cb96205`.
The actual 450,046,176-parameter checkpoint loaded on CUDA; 99,880,992 parameters
are trainable under the expert-focused configuration.

RunPod authentication uses the existing environment key with an explicit
User-Agent. No key replacement was required and no credentials belong in Git.

## Dataset and control contract

Sixteen successful scripted contact-manipulation episodes (11,571 frames) form
the training split; two successful episodes (1,450 frames) are separate.
The teacher uses simulator ground truth to generate labels. The learned VLA
receives only:

- `observation.images.overview`: pre-action RGB, 240×320, converted from HWC
  uint8 to CHW float32 in [0,1].
- `observation.state`: 28 values, ordered joint positions7, velocities7,
  commanded targets7, previous action7.
- One fixed instruction: “Pick up the keyed peg and insert it into the matching socket.”

The seven actions are normalized target increments: 0.01 rad per arm joint and
0.0006 m for the gripper at action magnitude1. Negative gripper action opens.
Internal model padding stays32. The pretrained embodiment's feature declarations
are replaced; its original camera/state/action shape is incompatible.

Dataset export verifies source SHA256, episode boundaries, time alignment and an
exact first-batch image/state/action roundtrip. State42, object pose, socket pose,
teacher phase and contact load are excluded from VLA inputs. No dataset or model
was publicly uploaded.

Training and evaluation use chunk50, execute5 actions per inference and10 diffusion
steps. The simulator control rate is50 Hz; inference is not claimed to run at
real-time50 Hz. Checkpoint evaluation loads saved processors and refuses mismatched
normalization statistics.

## Measured results

| Model | Development seeds | Actual success |
|---|---|---:|
| Pretrained weights, adapted task features/statistics | 2000–2002 | 0/3 |
| First fine-tune, 1,000 updates | 2000–2002 | 0/3 |
| Intermediate checkpoint, 500 updates | 2000 | 0/1 |

Base adaptation is not training: it changes input/output declarations and uses
training-dataset normalization with unchanged pretrained weights. The 1,000-step
fine-tune reduced reported training loss from1.099 to0.154, but failed all three
closed-loop trials. Loss reduction does not establish a robot skill.

Deterministic replay identifies premature lifting before gripper closure: the
model approaches the peg, but at step201 the gripper joint remains approximately
-12.7 mm; contact needs approximately -6.9 mm in this geometry. The arm lifts while
the fingers are still open. The peg remains on the bench. This is a measured
coordination failure, not a claim of successful grasp.

A longer 4,000-update phase starts from the 1,000-update checkpoint with a fresh
optimizer. It is a separate phase, not an exact optimizer resume. Any subsequent
closing-window weighted phase must be compared against equal ordinary training
from the same checkpoint before attributing improvement to weighting.

The frozen v0 JSON/evaluator threshold discrepancy is documented in
`CONTACT-VALIDATION.md`. Reports retain actual evaluator outcomes and a separate
stricter posthoc audit. Physics and acceptance are not changed between candidates.
Final evaluation seeds5000+ remain reserved until a working candidate is frozen.

## Running and preservation

`tools/train_smolvla.py` launches ordinary fine-tuning.
`tools/train_closing_weighted.py` launches the explicit weighted-loss experiment.
`tools/evaluate_smolvla.py` performs actual camera/proprioception inference,
records actions and videos, and never calls the teacher.
`tools/render_policy_diagnosis.py` replays saved actions through physics for
an explicitly separate close-up diagnosis.

The worker's current /workspace is on its disposable container disk, so it must
be exported before shutdown. `tools/preserve_runpod.py` streams archives directly
from SSH into the private repository's draft release and checks remote/stream/
GitHub SHA256 agreement. GitHub credentials remain on the laptop. This avoids
large local downloads while storage is constrained.

The [private draft checkpoint release](https://github.com/isaiahb/AstraFactory/releases/tag/untagged-a53d9f9d3a211f200ea9)
contains the RGB data/provenance, frozen state-policy experiments, first VLA model,
optimizer state and logs. Later results must be preserved before stopping the Pod.

Sources: [official SmolVLA training documentation](https://huggingface.co/docs/lerobot/main/smolvla)
and [RunPod storage persistence](https://docs.runpod.io/pods/storage/types).
