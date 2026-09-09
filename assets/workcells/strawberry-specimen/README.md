# Single strawberry specimen — reference and contact review

This is a reference-informed reconstruction, not a measured digital twin or a trained harvesting policy. The tabletop photograph supplies approximate visible landmarks; hidden crown connections and every depth/metric coordinate are inferred. The model does not reproduce an entire row or establish that all visible stalks belong to one plant.

## What now comes from references
- Cal Poly upper-surface leaflet photograph: manually estimated width stations, broad obovate silhouette, serrated margins, central crease and short petiolules. The mesh builder consumes the stored width profile.
- Cal Poly bare-root photograph and crown section: compressed crown at the substrate line, overlapping basal sheaths/stipules, separately distributed stalk origins. The smooth exposed ellipsoid was removed.
- Cal Poly truss photograph: a peduncle branches into pedicels. Fruit bodies attach to branch tips; their settled world positions come from dynamics.
- Ohio State tabletop photograph: uneven foliage, mixed fruit maturity and trough-supported hanging trusses. The camera comparison is approximate; no calibrated reprojection fit is claimed.

## Physics and tests
Stem rest geometry has a slight upward growth bias, not pre-sculpted hanging sag. Gravity, fruit mass and contact with the trough determine the resting shape. Leaf silhouettes are built from small convex wedges used for both rendering and collision. Four hinges per leaflet approximate bending. Capsule chains approximate stalk elasticity. Stalk bases bonded within sheaths exclude their internal attachment contacts only.

Ten seconds of settling precede separate leaf brushing, stalk bending and neighboring-fruit probe trials. Controls use the same plant state and the same collision-aware approach selection; only probe collision is disabled after selecting the trajectory. Test records include initialization overlaps, all probe contacts, penetrations, and trough/fruit contact durations. Rejected earlier trials remain under `checkpoints/`.

Fruit pairs may already touch at rest: the neighboring-fruit trial tests response in an existing cluster, not first-contact onset. Root/substrate mechanics, fruit deformation/bruising, cutting/detachment and real-plant calibration are not implemented. Tiny seed/calyx details are visual only and should not be used to claim tool-contact precision. Crown cross sections in the atlas are references, not simulated internal anatomy.

## Inspect
Open `index.html` through a local HTTP server rooted at the repository. Drag/scroll the 3D view, use the four recordings, inspect the crown close-up, or download `specimen-settled.glb`. The orbitable mesh follows recorded MuJoCo body transforms. The surface mesh toggle shows the tessellation; it does not visualize solver contact forces.

## Reproduce
```
python tools/build_strawberry_specimen.py
python tools/test_strawberry_specimen.py --kind rest
python tools/test_strawberry_specimen.py --kind leaf
python tools/test_strawberry_specimen.py --kind stalk
python tools/test_strawberry_specimen.py --kind neighbor
```
Repeat each contact command with `--control`, then render with `tools/render_strawberry_specimen.py --kind KIND --video` and export replays with `--export`. Requires MuJoCo, NumPy, trimesh, Pillow and imageio/ffmpeg. The photo-based design input is `tasks/strawberry_specimen/reference-graph.json`.

## Primary sources and image credits
Images remain attributed to their original owners; no open redistribution license is claimed. Local reference copies are for this study.
- Ohio State Kubota Lab, [production structures](https://u.osu.edu/indoorberry/structures/). Tabletop photo credited in-image to Meteor Systems; raised trough photo hosted by OSU.
- Gerald Holmes / Cal Poly Strawberry Center, [leaves and stems](https://strawberrycenterblog.com/2025/12/15/strawberry-anatomy-part-3-leaves-and-stems/): leaf upper/lower surfaces, petiolules, truss, trichomes.
- Gerald Holmes / Cal Poly, [roots and crowns](https://strawberrycenterblog.com/2026/02/19/__trashed/): bare-root photograph. Whole-plant and crown-section illustrations are from Strand 2008 / UC IPM, reproduced by Cal Poly with permission.
- Gerald Holmes / Cal Poly, [fruit](https://strawberrycenterblog.com/2025/11/25/strawberry-anatomy-part-2-the-fruit/): calyx variation, achene surface, fruit cross section.
- Gerald Holmes / Cal Poly, [flower](https://strawberrycenterblog.com/2025/11/04/strawberry-anatomy-part-1-the-flower/): buds and open flower.
- UMN Extension, [planting depth](https://extension.umn.edu/agriculture/specialty-crops/commercial-fruit-production/strawberry-farming/planting-a-new-strawberry-field): middle of crown at soil surface.

## Next morphology work
Fit a consistent camera and record projected landmark errors; improve the maturity-specific fruit outline and calyx; add branching-depth measurements from multi-view imagery; validate leaf crease and petiole taper against a single measured specimen. Parameter fitting needs real force–deflection/recovery data. Do not increase specimen count before reviewing these remaining gaps.
