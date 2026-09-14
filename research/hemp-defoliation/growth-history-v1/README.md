# Growth history 01

User direction: generate the plant through development, rather than adding
foliage onto a photograph-derived flat scaffold. This is the first executable
organ-scale **developmental geometry** model of that replacement.

## Run / review

```sh
node research/hemp-defoliation/growth-history-v1/check.mjs
python3 research/hemp-defoliation/growth-history-v1/publish.py
```

Open `/runs/hemp-growth-history-v1/index.html` on the existing repository server.
Requires the existing Three.js installation and prior leaf outline profiles.
No inference/training process or GPU job is started. The browser computes the
small deterministic history and builds merged meshes when a stage changes.
Playback pauses when the page becomes hidden; the renderer is idle otherwise.

## What is implemented

- A seed marker and schematic above-ground emergence, cotyledon expansion,
  sequential main-axis node births and true-leaf expansion.
- Node-local leaf arrangements: early paired organs, followed by an assumed
  alternate arrangement. Local frames vary continuously, without camera-facing
  directions or sudden reference-axis switches.
- Axillary bud activation connected to a specific subtending leaf and node.
  Child axes add their own nodes over time. Persistent identifiers allow
  tracking the same organ through the history.
- Separate age functions for internode length, radius and leaf expansion.
- An explicitly heuristic direction-response term acts while a segment grows.
  Mature intrinsic directions stop updating; they are not reoriented at every
  later snapshot. Disable this response to inspect its effect on architecture.
- Juvenile simple leaves, later compound leaves and an unfolding rest pose.
  The outline profiles reuse prior Futura75 work; this is a cross-cultivar
  transfer, not newly measured shapes for the partner's plant.
- A stage slider, fixed-camera playback, fit-stage control, four views, organ
  age coloring, skeleton inspection, previous-structure comparison and export.

## Evidence and assumptions

See `sources.json`. USDA architecture descriptions inform node-arrangement
states. Balant et al. (2024) support developmental variation in leaf form;
Spitzer-Rimon et al. (2019) support the phytomer hierarchy. Bastien et al. (2015)
motivate separating active posture changes from passive mechanics.

Numerical birth intervals, expansion durations, transition node, azimuth,
branch caps, final dimensions and direction-response coefficient are scenario
assumptions. They are not fitted biological measurements. Development units
are not days. Neither growth-rate accuracy nor commercial-cultivar resemblance
has been established. A historical architecture model for a mature cutting
would require a different initial state from this seed-origin scenario.

## Implementation checks

The final default history has 121 nodes, 24 shoots and 171 visible true leaves.
Checks cover parent attachment, chronology, stable IDs, finite coordinates,
monotone segment extension, deterministic replay, a non-planar test scenario
and a direction-response ablation. Halving the integration timestep preserves
final organ counts; dimensional deviation is recorded in `checks.json`.
These are implementation checks, not evidence of biological realism.

## Next discrepancies to resolve

The default remains an upright, regular, single-axis vegetative scenario. Its
repeated timing and bud rules need measured developmental variation and a
matched specimen history. No acceptance claim is made from leaf count or a
roughly circular top view. The target may have an asymmetric canopy.

There is no root physiology, photosynthesis/resource model, self-shading,
flowering, elastic loading, self-collision, live-tissue calibration or damage
model. Leaf droop is rest-pose geometry, not solved weight response. The upward
term is not a force and is not the full AC tropism model from the literature.
Do not reuse the render as validated contact geometry for robot training.

The useful next mechanical increment is a single branch/petiole loading test
that separates intrinsic growth curvature from load-induced displacement,
followed by a multi-view specimen fit. Preserve this developmental history
and the rejected flat reconstruction while improving those components.

## Browser review completed

Inspected the developed three-quarter view, the young-plant stage with stage
framing, and a top-view comparison against the old photo-fit geometry. Played
from emergence (0.5 units observed) to the final state (34 units, automatic
stop observed). Development controls remain visible beside the viewport.
The final shape is still regular and narrow; its simple schedules and missing
self-shading are limitations, not evidence of a particular commercial phenotype.
