# Parametric strawberry study — local research artifacts

Current whole-plant candidate: **v13**. Preserved baseline: `../basal-study/v7`. Intermediate rejected candidates remain on disk. The desktop product is unchanged.

Review:
- `whole-plant-progress.png`: credited real photo and matched simulation views; local reference composite, excluded from git.
- `crown-progress.png`: same-camera model stages.
- `v13/index.html`: orbit/pan/zoom recorded rigid-body physics.
- `variation-leaf-probes.mp4`: three actual probe recordings with 0 / -25 / +25 degree approaches. This is model testing, not policy generalization.
- `../leaf-study/rib-surface-v2/contact-and-control.mp4`: independent continuous-surface prototype; not integrated into the whole plant.
- `batch-results.json`, `v12-timestep/results.json`, `throughput-v13.json`, `throughput-leaf.json`: numerical and cost evidence. Real-plant calibration remains absent.

Use the repository Python environment with numpy, MuJoCo 3.12.0, trimesh, Pillow, matplotlib and imageio. The accepted whole-plant and rib-surface generators do not use Triangle.

From the repo root, rebuild into a NEW output directory:

```sh
python tools/parameterize_strawberry.py --config tasks/strawberry_specimen/parametric/canopy-v13.json --output /absolute/new-directory/reference-input.json
python tools/build_strawberry_specimen.py --spec /absolute/new-directory/reference-input.json --output /absolute/new-directory
python tools/test_strawberry_specimen.py --model-dir /absolute/new-directory --kind rest
python tools/test_strawberry_specimen.py --model-dir /absolute/new-directory --kind leaf
python tools/test_strawberry_specimen.py --model-dir /absolute/new-directory --kind leaf --control
```

Repeat `basal`, `stalk`, `neighbor` with and without control; then run `tools/audit_parametric_strawberry.py /absolute/new-directory`. Seeds 41/73 go on the parameter compiler; angles -25/+25 go on paired leaf/basal tests. The full iteration notes and open-work ledger under `docs/simulation` explain criteria, failures and remaining physical mechanisms. Keep raw rollouts/media local and do not overwrite checkpoints.
