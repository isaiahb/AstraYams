# Surface study 1 — preserved narrow outline

Adds shallow achene pits, embedded achenes and pointed sepals to the full
existing strawberry specimen. This appearance-only revision preserved the
original collision meshes, masses, inertia, springs and damping exactly.
`physics-regression.json` records the paired contact continuation check.

The user rejected its long, narrow silhouette. See `../v2/index.html` for the
shorter and broader revision, including changed collision/COM/inertia and new
physics recordings. This version intentionally preserves the rejected outline.

Reproduce from the repository root with `python tools/review_strawberry_surface.py`.
Serve the repository root over HTTP; browser module/mesh requests require it.
