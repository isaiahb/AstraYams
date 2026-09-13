# Whole-plant development study v1

An inspectable **developmental architecture hypothesis** for non-psychoactive hemp. This checkpoint replaces resampled static plant geometry with persistent organ identities and a reproducible history. It is not a validated growth simulator, harvest policy, or whole-plant contact simulation.

Open [the timeline](http://127.0.0.1:8793/runs/hemp-development-v1/index.html), scrub from Early to Later, then compare the same specimen with its recorded leaf-removal event. Front, Side, Top and Branch bases expose attachment geometry. A separate [beam diagnostic](http://127.0.0.1:8793/runs/hemp-development-v1/mechanics.html) tests numerical mechanics without claiming measured plant behavior.

## What changed

- A short main axis and multiple persistent upper shoots replace the previous uniformly tiered tree silhouette. Prior apex arrest is an assumed starting architecture, not a simulated horticultural intervention.
- Each axis and compound leaf has a stable ID, parent node, birth step, age and mature dimensions. Internodes and leaves expand with age; new snapshots do not generate a new random plant.
- Three specimens have coupled specimen/shoot vigor and different branch membership. This is a procedural prior, not a calibrated population distribution.
- Existing Futura 75 outline coordinates supply individual leaflets. They remain attached to petioles and parent nodes throughout the timeline.
- A constructed event removes a fixed set of leaf IDs at step 82. Retained branch coordinates, thickness and age remain identical at that instant. The event does not solve unloading, wound response or regrowth.
- Planar leaflet area, estimated leaf mass, tapered-frustum stem mass and illustrative age-indexed beam rigidity are exported for eventual mechanics coupling.

The 0–100 timeline is a **dimensionless development index, not days**. Smoothstep expansion is a convenient hypothesis. Nothing in this version establishes a growth rate, production recipe or optimal removal schedule.

## Evidence and assumptions

See [sources.json](sources.json) and [parameter-ledger.json](parameter-ledger.json). The previous photo review remains intact at `../indoor-photo-review/`.

Measured input: attributed two-dimensional Futura 75 leaflet outline coordinates from Balant et al. (2024), DOI 10.1111/nph.19817. Physical size, pose, age response, petiole properties and material properties are not measured by that source. Coordinate provenance remains at `../reference-data/provenance.json`.

Visual input: indoor photographs suggest a mismatch with the old sparse, evenly tiered model, but do not determine hidden branch connections, cultivar, cultivation history, exact scale, force response or growth rates. Our new plant is not a reconstruction of a photographed specimen.

New research lead: Rocamora-Osorio et al. (2025), Mendeley Data V1, DOI 10.17632/3md2tbx74c.1, describes hourly photographs of five industrial hemp plants through 20 days after transplanting. The metadata and C1 file listing were inspected. The image preview failed and the archive endpoint returned HTTP 403 in this session. **No images from that dataset were imported, measured or fitted.** It concerns greenhouse plants and does not establish the partner's flowering indoor morphology. The first candidate frame and publisher checksum are recorded in `sources.json`.

The Figshare numeric and image collections have different licenses: numeric data article 29097107 is CC BY 4.0; the linked APPF image collections 23211779/23211776 are CC BY-NC 4.0. None were imported. Do not silently treat those image licenses as the numeric-data license.

## Mechanics: verified equations, unvalidated material

`mechanics.py` solves a clamped, uniform Euler–Bernoulli beam with consistent mass, Rayleigh damping and Newmark integration. The assumed coupon is 160 mm long with a 2.6 mm radius, E=80 MPa, density=850 kg/m³ and a 3 mN peak incremental tip load. A shallow prescribed rest curve is added to the small elastic displacement. There is no gravity, cutting, fracture or tool contact.

Checks compare the static solution with FL³/(3EI), account for work and dissipated energy, and refine 12 elements/2 ms to 24 elements/1 ms. The maximum tip difference is approximately 0.136 µm. These checks verify this equation solver, **not the plant's stiffness or safety**. Rest-shape preservation is by construction. Large rotations, shear deformation, viscoelastic growth, tissue anisotropy and branching junction behavior require a more appropriate model and measured response data.

## Numerical and visual review

`evidence/audit.json` checks all 51 snapshots of all three specimens: unique organ IDs, valid parent birth order, finite coordinates, zero-length unborn internodes, exact attachments and retained scaffold identity across the event. These are bookkeeping checks, not independent biological validation.

`evidence/mechanics-audit.json` records the separate analytical and refinement checks. Actual browser-rendered views are stored under `evidence/`; the earlier open-triangle flower display is retained as `first-pass-flower-envelope.png` for comparison. Flower envelopes remain a coarse optional geometric proxy with no detailed reproductive anatomy or mass model.

Visual review found unresolved regularity in branch curves, repeated leaflet templates, simplistic branch junctions and no contact-induced canopy rearrangement. A denser silhouette alone does not close these gaps. There are no real hardware or trained-policy results in this checkpoint.

## Next experiment

Use the schema in `observation-schema.json` to record a **same-specimen** time series, including a visible scale and camera pose. Fit architecture against visible branch nodes, internode lengths, leaflet outlines and silhouettes; mark hidden organs as unknown. Reserve entire plants and later time points for validation rather than randomly mixing neighboring video frames into train/test.

Fit growth and mechanics separately: first match unloaded geometry through time, then use measured gentle load–hold–release traces to estimate stiffness, damping and persistent deformation. Couple them only after both tests pass. A static image cannot determine E, tissue strength or growth memory. Include uncertainty ranges and reject a model when multiple views cannot be explained by the same topology.

Next acceptance evidence should be a real/model comparison at matched scale and view, temporal errors on held-out observations, and measured-versus-simulated force/displacement recovery. Until then, material parameters and biological claims remain explicitly uncalibrated.

## Reproduce

From the AstraFactory repository, with Python 3.12 and NumPy 2.x:

```sh
python3 research/hemp-defoliation/development-v1/build.py
python3 research/hemp-defoliation/development-v1/mechanics.py
python3 -m http.server 8793 --bind 127.0.0.1
```

The viewer uses the repository's existing Three.js installation under `apps/skill-studio/node_modules/`. Runtime JSON is regenerated under `runs/hemp-development-v1/`; source, compact audits and review images are checkpointed separately. The previous indoor and whole-plant checkpoints are unchanged.
