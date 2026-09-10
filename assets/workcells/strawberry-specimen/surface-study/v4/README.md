# Strawberry anatomy, revision 4

V3's digitized fruit outlines are retained. V4 changes surface anatomy on those
shapes and in the **complete shared plant**. It is not a new learned policy,
new material identification, or a new contact experiment.

Open `index.html` through the repository HTTP server for six examples, orbit,
front/side/top views, shape-only mode and a same-camera V3/V4 toggle. `plant.html`
replays the prior rest/contact/control trajectories with new visual geometry.
`anatomy-comparison.png` and `comparison.png` are actual MuJoCo renders.

## Observations, implementation and unknowns

- [Holmes / Cal Poly, fruit anatomy, Figures 1, 2 and 5](https://strawberrycenterblog.com/2025/11/25/strawberry-anatomy-part-2-the-fruit/)
  shows variation in cap size, overlapping leaflike parts, achenes and surrounding
  surface structure. Photographs are remotely linked with attribution; no new
  reproduction license is asserted. These are different fruit from the fitted
  outline specimens. They do not validate this model's hidden geometry.
- [Flora of China, cultivated strawberry](https://www.efloras.org/florataxon.aspx?flora_id=2&taxon_id=242322784)
  distinguishes ovate sepals, narrower epicalyx parts and ovoid achenes.
  [The genus account](https://efloras.org/florataxon.aspx?flora_id=2&taxon_id=112975)
  describes alternating five-part whorls. Counts remain configurable; they are
  not a universal cultivar invariant.
- The existing [Nagamatsu et al. outline study](https://www.jstage.jst.go.jp/article/jsbbs/71/2/71_19106/_html/-char/en)
  remains the macro-shape evidence. Its calyx-removed photographs cannot fit cap
  geometry. [Li et al.](https://www.nature.com/articles/s41438-020-0337-x) says
  its generated datasets are available from the corresponding author on request.
  We have not obtained a matching multi-view dataset or contacted anyone.

The old generator placed near-horizontal rows on an axisymmetric base and then
warped the seeds with the fruit. V4 samples the **finished** surface by area,
uses a distance-exclusion rule, and constructs seed dimensions in each local
surface frame. This removes row bands and deformation-induced seed stretching.
It is a geometric spacing hypothesis, not a measured phyllotaxis or growth law.

Current explicit priors: 2.7 mm nominal minimum site spacing with a smooth local
density variation; achene full axes 0.72 × 1.30 × 0.36 mm, scaled 0.82–1.14;
shallow 0.16 mm nominal pits with variation. There are 270–289 sites on the six
18 g examples. These values are **not** population estimates from the photos.
Missing pistil remnants and finer epidermal structure remain visible limitations.

The calyx uses two alternating whorls, curved creased laminae, narrower outer
parts, a basal connector and a short pedicel transition at the existing fruit
attachment. Span, count and tip curl are separate parameters. Curvature, thickness
and display color are uncalibrated. The new calyx is visual geometry; its contact
surface and compliance have not been identified. The older simplified calyx
collision geoms and all physical fruit/stalk properties remain as before.

## Checks and interpretation

- `physics-equivalence.json`: exact compiled physical arrays, every active
  collision geom including mesh vertices/faces, and identical qpos/qvel after
  100 steps from the same initial state. This permits reuse of V3 trajectories.
- `rest`, `neighbor`, `neighbor-control` contain trajectory source hashes.
  Exporting a new replay with new meshes is not new physics or training.
- `projection-regression.json`: projecting all six generated skin meshes into
  their source images changes fitted-view IoU by less than 0.0015. This is a
  regression check on an already fitted view, not held-out validation.
- `native-builder-check.json`: the canonical specimen builder also accepts this
  graph and reproduces the physical parameters. An initial raw inertia-quaternion
  check was too sensitive to near-zero eigensolver components; the physical
  body-frame inertia tensor is checked with stated tolerances instead. The
  separate V3/V4 appearance-only checks remain exact.
- Inspected front, side, top, whole-plant and probe-contact views. The cap and
  skin remain smoother and more stylized than the reference photographs.

## Reproduction

From the repository root, with the existing MuJoCo/trimesh/scipy environment:

```sh
/tmp/clonebench-cad-env/bin/python tools/study_strawberry_anatomy.py
```

This regenerates the six assets, full specimen, physical-equivalence audit,
replays, actual renders, projection check and canonical-builder check. V3 data
and source files must exist. Generated meshes/rollouts are excluded from git.
Legacy recipes stay unchanged; `surface_recipe: 4` explicitly opts into V4.

## Next discriminating outcome

Highest consequence: the calyx and skin need visible/contact agreement before
training a cutter near them. First test a tool brushing one sepal with an explicit
flexible contact model, while preserving this rigid-fruit baseline. Its stiffness
must stay a hypothesis until force/deflection data exist. In parallel as evidence
becomes available, same-fruit multi-view images with scale should test the hidden
depth and calyx attachment. More decorative detail alone cannot close these gaps.
Full tool grasping, flexible net contact, cutting and PPO with these assets remain
open; desktop product work remains paused.
