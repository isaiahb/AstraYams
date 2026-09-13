# Photo-constrained nominal reconstruction

An observable first reconstruction of a published Cherry Wine specimen. The
work adopts the manual organ/evidence loop from **CityFarmers SIM**, without
copying its tomato anatomy or claiming either model is biologically calibrated.

Open `http://127.0.0.1:8793/runs/hemp-photo-fit-v1/index.html` after generation.
The viewer uses the repository's existing Three.js files. It offers aligned
photo/model views, traced observations, missing/excess foliage masks, orbiting,
and alternative depth hypotheses. No desktop product UI was modified.

## Reproduce

From the AstraFactory root, with Python containing numpy, scipy and Pillow:

```sh
python research/hemp-defoliation/photo-fit-v1/build.py
python research/hemp-defoliation/photo-fit-v1/validate.py
python research/hemp-defoliation/photo-fit-v1/render_review.py
```

The available sibling runtime is
`/Users/isaiah/Documents/BallahTech/City-Farmers-Sim/.venv/bin/python`.
This only borrows its interpreter; the tomato project is not modified.
`render_review.py` currently uses macOS Arial for figure captions.
Generated mesh JSON lives in ignored `runs/`; compact evidence is versioned here.
The checked-in observations and input source hash make reconstruction repeatable.

## Interpretation

- `observations.json`: manually interpreted image coordinates. Occluded
  connections are assumptions, not annotated 3D ground truth.
- 15 projected main/lateral axes plus 28 hypothetical secondary shoots.
- 148 leaf organs, of which 37 have observed junction/direction landmarks.
- Each leaf mesh and petiole retains parent identity. Extracted curved profiles
  use a medial vertex strip, avoiding the previous folded-triangle bug.
- Cherry Wine cohort median height supplies a working scale, not the known
  height of the photographed individual. Leaf margins are transferred from
  Futura75 and adjusted as hypotheses.
- `fitted` maximizes projected coverage. `shape-constrained` uses narrower
  blades selected by visual review, and deliberately accepts a lower score.
- Depth B reverses hidden depth. Its matching mask score demonstrates that
  one projection cannot establish depth correctness.

## Current results and limits

Native-resolution raw mask overlap: initial 28.5%, fitted 37.6%, narrower-leaf
hypothesis 34.2%. Corresponding coarse overlaps: 36.9%, 47.2%, 45.2%.
These are same-photo fitting diagnostics, not accuracy on unseen plants.
Changing the green threshold from 30 to 60 changes the narrower-leaf raw score
from 35.2% to 32.9%; the segmentation is not an independently labeled mask.

All five meshes passed finite-coordinate, unique-ID, resolved-parent,
nondegenerate-triangle and exact attachment checks. This is software validation.
Self-contact, stiffness, fresh mass, damage, growth and policy performance are
not validated or simulated in this experiment.

The model still lacks fine terminal structure and has imperfect foliage density,
leaf posture, colour and hidden branching. It is not a finished cultivar replica
or a fitted cultivar population distribution. The next iteration must improve
these differences without rewarding bigger leaves for filling missing organs.

## Source and evidence

Anderson et al. (2021), Figure 1, Cherry Wine column; CC BY:
https://doi.org/10.1371/journal.pone.0252985.g001
The source crop and provenance are preserved under
`../nominal-cultivars-v1/`; measured outline provenance is under
`../development-v3/reference-data.json` and `../reference-data/provenance.json`.
The experimental-condition label identifies a photograph, not cultivation advice.

See `evidence/spot-the-difference.png`, `evidence/geometry-review.png`,
`evidence/manifest.json`, `evidence/geometry-checks.json` and `WORKLOG.md`.
Rejected attempts are preserved in `evidence/rejected/`. Offline figures render
the exported mesh using depth-sorted triangles; the interactive viewer uses a
real WebGL depth buffer. Neither image path invents additional geometry.
