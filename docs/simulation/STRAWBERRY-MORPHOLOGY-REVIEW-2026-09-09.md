# Strawberry morphology review — 2026-09-09

The user requested more crown/root close-ups and a whole-plant "spot the difference" comparison across growing conditions. This is a manual evidence review, not an app change or a new geometry revision.

## What was done

- Collected seven additional source images and retained two existing references: nine image files from five institutions. Some contain multiple panels. The sample is deliberately varied but is not representative in a statistical sense.
- Recorded source URLs, credits, file hashes and specimen conditions in the study’s `sources.json`. Kept source photographs separate from simulation renders.
- Rendered seven views of the unchanged v7 model at its saved gravity-settled state. Camera direction is approximate; the photographs and model are not calibrated or metrically aligned.
- Built three annotated review plates: whole plant, crown/roots, and growing contexts. The cutaway hides container and distal plant parts for inspection; it is not a physical uprooting simulation.

## Actual model findings

- The five leaf-stalk first segments are about 11–23° from world vertical. The earlier 1.1° number was a joint rotation relative to its unloaded reference, not a stem’s absolute growth angle. These quantities must not be confused.
- Left, right and front stalks end at approximately 94°, 98° and 105° from vertical: their final modeled segments point below horizontal. Full profiles are in `model-angle-audit.json`. These are measurements of the simulation, not targets inferred from photographs.
- The rendered leaflets have large edge-on surfaces and visible articulated strips. Curvature along the stalk and leaflet orientation both need attention.
- Crown geometry is one fixed, simplified core with closely grouped attachments. Biological roots are not modeled. Names such as `leaf_left_0_root` refer to leaflet attachment bodies, not underground roots.

## Interpretation and next controlled changes

The multi-image comparison supports studying the attachment layout and organ shape before treating every pose mismatch as a material-stiffness error. It does not identify a unique stiffness, unloaded shape, cultivar or 3D reconstruction.

1. Keep the mature trough crop as the intended task context. Use isolated standing plants to study one crown; use exposed specimens for connectivity.
2. Review petiole curvature along its length, then the three leaflet orientations. Compare unloaded and settled shapes separately; change one cause at a time.
3. Replace the central attachment approximation with layered leaf bases and developing central growth. Add branch crowns only for a deliberately selected plant age/history.
4. Model the crown/root junction explicitly if roots are in scope. Root anchoring and pullout cannot be validated by decorating the fixed core with a root-looking mesh.
5. Show the same camera views after each change, then repeat the existing contact checks. Do not score crop-row density against a single isolated crown.

The strongest whole-plant reference still contains neighboring foliage; the foreground crop does not perfectly isolate one individual. Older and dug plants have disturbed or stage-specific poses. Two Oregon State figures are low resolution and are kept as context, not dimensional measurements.

## Reference register

- **osu-whole** — [Standing field plant: crown, leaves and fruit stalks](https://extension.oregonstate.edu/catalog/pub/ec-1307-growing-strawberries-your-home-garden). Bernadine Strik / Amanda Davis, Oregon State University. Condition: Standing field plant; foreground plant partly overlaps neighbors. Figure 1.
- **osu-containers** — [Container-grown plants, cultivar Albion in some panels](https://extension.oregonstate.edu/catalog/pub/ec-1307-growing-strawberries-your-home-garden). Bernadine Strik / Amanda Davis, Oregon State University. Condition: Four container panels A–D; differing plant counts/stages. Context only: low source resolution.
- **osu-crown** — [Older crown in winter / adding substrate](https://extension.oregonstate.edu/catalog/pub/ec-1307-growing-strawberries-your-home-garden). Bernadine Strik / Amanda Davis, Oregon State University. Condition: Two winter / soil-renewal panels. Older crown; low source resolution, not a stiffness reference.
- **unl-pot** — [Young Evie-2 plant with flowers in a nursery pot](https://agronomy.unl.edu/year-round-strawberry-production/). University of Nebraska–Lincoln, Agronomy and Horticulture. Condition: Young propagated Evie-2 plants in nursery pots; open flowers visible. Not a mature tabletop crop.
- **unl-large-crown** — [Large crown selected for cold storage](https://agronomy.unl.edu/year-round-strawberry-production/). University of Nebraska–Lincoln, Agronomy and Horticulture. Condition: Dug, soil-bearing large crown selected for storage; photographed outside its growing substrate.
- **arkansas-branch** — [Main crown and branch crowns, dug field plant](https://www.uaex.uada.edu/farm-ranch/crops-commercial-horticulture/horticulture/ar-fruit-veg-nut-update-blog/posts/HighGDDImpact.aspx). University of Arkansas Division of Agriculture. Condition: Dug field plant held apart by hands to expose main and branch crowns; disturbed pose.
- **calpoly-uprooted** — [Uprooted strawberry plant](https://strawberry.calpoly.edu/news/test-your-strawberry-anatomy-skills-part-2). Cal Poly Strawberry Center. Condition: Uprooted plant laid out on a dark surface; useful topology, not standing angles.
- **calpoly-trimmed** — [Trimmed bare-root crown](https://strawberrycenterblog.com/2026/02/19/__trashed/). Gerald Holmes / Cal Poly Strawberry Center. Condition: Trimmed bare-root specimen; clipped petioles and roots; useful bases, not mature canopy shape.
- **osu-tabletop** — [Mature tabletop trough crop](https://u.osu.edu/indoorberry/structures/). Meteor Systems via Ohio State Kubota Lab. Condition: Mature greenhouse trough row with overlapping plants; individual crown ownership obscured.

## Artifacts

Under `assets/workcells/strawberry-specimen/morphology-review-2026-09-09/`:

- `01-whole-plant.png`, `02-crown-roots.png`, `03-environments.png`: local annotated plates.
- `sources.json`: provenance, attribution and conditions.
- `renders/provenance.json`: cameras, saved-state/model hashes and cutaway disclosure.
- `model-angle-audit.json`: current stalk directions.

`tools/review_strawberry_morphology.py` recreates the plates from these locally retained source files and renders. The evidence figures contain credited external images; no redistribution license is assumed, and the composite plates and source photos remain local. The original v7 physics and desktop app were not edited.
