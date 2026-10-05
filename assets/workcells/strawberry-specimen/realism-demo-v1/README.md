# Updated specimen demo

This isolated review refreshes the original photograph/physics demo using the
complete surface-study V4 plant. The source studies, training environments,
desktop app, and original demo are unchanged.

## What is shown

- The updated crown, ascending tapered petioles, articulated leaves and loaded
  fruit truss from the shared plant model.
- Photograph-derived asymmetric fruit shapes, corresponding rigid collision
  envelopes, centers of mass and inertias, with V4 achene/calyx appearance.
- Four fresh force-limited probe trials: stem base, leaflet, fruit stalk and
  berry. Each has a matched trial with only probe contact disabled.
- Recorded body transforms, in physical seconds, with orbit/pan/zoom and a
  cel/material shading toggle. No procedural plant-motion animation.
- Same-camera comparison against the original model's settled pose. This is
  a visual comparison, not a controlled material experiment: both morphology
  and mechanical parameters changed between those models.
- Contact-induced target displacement is measured against the matched control
  at each recorded time. Force and penetration values are trial peaks, not
  instantaneous values inferred from the pictures.

The reused 20-second settling trajectory comes from V3. V4's exact compiled
physics-equivalence audit permits reuse; it changes visual details only.
`provenance.json` records scene and trajectory hashes. The eight contact/control
trials are freshly simulated with that V4 scene.

## Limits

This is a diagnostic demonstration, not PPO or a harvesting success. Material
parameters are uncalibrated. Fruit is rigid; bruising and flesh indentation are
not established. Detailed calyx visuals still have simplified collision shapes.
The crown is anchored; roots are reference imagery, not simulated root mechanics.
The separate elastic/relaxing/retained-curvature recovery experiments remain
hypotheses and are linked separately, not silently substituted into this model.

No-contact controls intentionally allow the probe to pass through the plant;
their sole purpose is to distinguish contact-induced response from natural drift.

## Reproduce

From the repository root, use the installed MuJoCo environment:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/clonebench-cad-env/bin/python assets/workcells/strawberry-specimen/realism-demo-v1/build.py
```

This writes only this revision directory. Existing completed contact trials are
reused on rerun. Raw outputs are local artifacts and are not committed here.
Photo credits and source links remain visible in the review and original studies.
