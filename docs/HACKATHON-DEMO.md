# Three-minute learning demo

Start with the learning evidence panel in AstraFactory. Keep the separate bench-arm CAD workflow to an optional 15-second supporting example; the insertion policies do not assemble that arm.

## Rehearsal script

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Learning headline and task view | “AstraFactory is an AI that creates the robotics skills it is missing. Our prototype builds a simulation task, trains small specialist policies, tests them, and composes them.” |
| 0:20–0:40 | Successful task preview, pause before insertion | “The task is to grip a custom keyed part, lift it, align it and insert it. This is the YAM robot model with physical gripper contact. For this prototype, policies receive simulator state.” |
| 0:40–1:00 | Earlier failure clip, skip to late stall if needed | “The early composed system could grasp but stalled during insertion. It passed only two of ten development trials. We inspected the failure and found an error in the insertion teacher's gating logic.” |
| 1:00–1:30 | Skill cards and paired pickup metric | “We generated demonstrations and trained small specialists. The paired pickup test improved from zero of five to five of five on the same seeds, with the control scaffold held fixed. Those two pickup models trained in about five seconds; that excludes data collection and testing. The full chain has 3,242 learned parameters, alongside conventional control.” |
| 1:30–2:00 | Full successful final trial (~14s) | “After correcting the insertion teacher and retraining the correction, we froze the chain. It passed twenty nominal and twenty randomized final trials. The gripper physically holds the part throughout; there is no attachment weld or reset between skills.” |
| 2:00–2:25 | Four-layout grid (~17s) | “These are four recorded physical simulations with different part locations and key rotations. All six named layout cases passed. This is the same geometry, not generalization to arbitrary products.” |
| 2:25–2:45 | Experiment status / visual result | “The system also records when a change does not earn promotion. Our camera-and-joint-feedback path has not demonstrated useful visual control yet. We preserve its failures instead of presenting it as deployment-ready.” |
| 2:45–3:00 | Headline / next step | “The goal is a repeatable loop: design a task, create training experience, learn a skill, test it, and add it to a library. This demo proves that loop in simulation; real-robot transfer is the next validation step.” |

## Exact claim boundaries

- Prepared recordings are audited saved-action replays, not live training or fresh policy inference during playback.
- The successful state-based runtime uses exact object state, target construction, phase guards, IK, angular stabilization and gripper hold logic. Neural models do not replace every controller.
- Pickup 0/5→5/5 is paired. Earlier full-chain 2/10 and final 20/20 are different seed sets, so they are not a paired improvement estimate.
- The approximately five-second number is two pickup specialists' training only. It is not end-to-end environment creation, data generation, all-skill training or evaluation time.
- Success is insertion and hold; no release/retention or complete arm assembly is claimed.
- Image-policy v2: RGB1/5, blankRGB2/5, untrained0/5. No demonstrated visual advantage; not promoted.
- This demonstrated training route is imitation learning. A separate PPO residual candidate failed to improve and was rejected.

## Playback and recovery

- App integration reads `runs/hackathon-demo/final-demo.json`.
- Individual self-contained videos: `runs/hackathon-demo/videos/{failure,success,generalization}.mp4`.
- Fallback montage: `runs/hackathon-demo/astra-learning-demo.mp4`. Failure runs at2x, other clips at1x; labels are visible. It is a presentation montage, not one rollout.
- Existing full evidence page: `http://127.0.0.1:8769/runs/skill-observatory/index.html`.
- If the app fails, open the fallback MP4 locally. Explain the paired metrics verbally; the montage's failure clip is the earlier full-chain failure, not the untrained pickup trial.
- Freeze source, checkpoints and evaluation criteria. No last-minute training, camera relocation or dynamics edits are necessary for this presentation.

## Rebuild

From repository root: `python3 tools/build_hackathon_demo.py`, then `/tmp/clonebench-cad-env/bin/python tools/build_demo_reel.py`. The first verifies checkpoint hashes and copies measured reports/videos; the second only edits presentation framing/playback rate. The generated bundle stays out of Git; code and this runbook are tracked.
