# Whole-plant anatomy study

The user redirected the work on 2026-09-12: build and study the entire plant, not an isolated leaf. The current deliverable is an inspectable female flowering hemp anatomy candidate. The original failed single-leaf experiment is preserved, not promoted into this model's physics.

## Research that changed the model

- **Branch architecture and flower sites.** Spitzer-Rimon, Duchin, Bernstein and Kamenetsky (2019) describe a hierarchy of repeating nodes and internodes, with leaf-axil shoots and condensed flowering branchlets. Their figures show whole-plant differences, node connections, reduced foliage and small floral structures. This informed the parent graph and placement of protected flower structures beside leaf bases. These medicinal accessions are not the partner's hemp cultivar. [Paper and Figs. 2, 5, 7](https://doi.org/10.3389/fpls.2019.00350). Figure URLs are linked directly with attribution; the article is CC BY. No cultivation protocols or chemistry models are used.
- **Blade anatomy.** UF/IFAS identifies compound leaves, distinct serrated leaflets, prominent midribs and veins, and compact female floral structures. The model gives each leaflet its own surface and adds veins rather than treating the leaf as a single lobed membrane. [Botanical identification](https://ask.ifas.ufl.edu/publication/AG476).
- **Whole-plant context.** NC A&T's hemp biology chapter describes differences in branching, lower/upper leaf arrangement, stems and roots across plant contexts. It motivated separating stem architecture from a rooted-cutting root hypothesis. The root system here is illustrative; no propagation method has been confirmed for the partner. [Hemp biology, printed pp. 3–5](https://www.ncat.edu/caes/cooperative-extension/files/all-about-hemp.pdf).
- **Measured projected edges.** The existing Futura 75 coordinates accompanying Balant et al. (2024) supply visible edges of seven separate leaflets. We extract each tip-containing contour between its two basal landmarks, resample edges, and infer the unseen basal connections. The measured scan does not establish physical scale or 3D pose. [Paper](https://doi.org/10.1111/nph.19817), [coordinate provenance](../reference-data/provenance.json).

The architecture photographs and node/flower close-ups were personally inspected. This is a synthesis of anatomical references, not a quantitative fit to a photographed whole specimen.

## What is represented

Root collar → main stem → nodes → axillary branches and leaf stalks. Leaf stalks → independent leaflets → blade and vein geometry. Flowering axes → shortened branchlets → simplified enclosing bracts and paired stigmas. Larger leaves, reduced leaves, stipules, roots, container and substrate have separate identities.

All geometry uses metres. Each organ has an ID, parent and attachment location; supported axes additionally retain their centerlines. Those identities can later support collision, damage and task labels. The rendered model and downloadable GLB come from the same generated geometry.

The default has a continuous main shoot and lower paired/higher alternate leaves. It is one architectural hypothesis, not a universal progression or a fitted growth law. It does not model seedling cotyledons on a mature plant. No detached seeds, male organs, full flower interiors, trichome microstructure, microscopic stem tissue or root hairs are represented.

## Evidence and assumptions

| Quantity | Status |
|---|---|
| Visible 2D leaflet edges | Published coordinate measurements from one Futura 75 leaf |
| Repeating nodes, branching connections, separate leaflets | Literature-informed topology |
| Basal leaflet tissue hidden by overlap | Inferred geometry |
| Height, node counts, branch lengths, all organ dimensions | Assumed in `specimen.json` and the builder |
| Branch and leaf curvature, orientation, asymmetry | Assumed static poses, not gravity-equilibrated shapes |
| Root architecture | Rooted-cutting hypothesis, unconfirmed |
| Compact floral units | Simplified external envelopes; no tissue-scale model |
| Stiffness, density, damping, friction, cutting force, damage | Unknown; not assigned in this anatomy study |

## Review and acceptance

The viewer supports whole plant, foliage-hidden branches, a stem node, an inflorescence, roots and top view. Anatomical colors separate the classes. Clicking visible geometry exposes an organ's parent. Root view hides the container/substrate explicitly; it is a visibility change, not a removal event.

The builder checks finite geometry, nonzero triangle areas, valid indices, unique IDs, resolving parents and an acyclic graph. These are geometry checks, not anatomical or physical validation. A connected graph does not prove physically correct attachment areas or collision clearance.

Initial review found roots protruding beyond the assumed pot and flower structures appearing as sparse rows. Root extent was constrained to the container context, a below-ground collar was included, and the floral envelopes were regrouped around their short supporting axes. These are geometry revisions, not measured calibration.

Remaining mismatches: foliage is still based on one source leaf; branching is more regular than a measured specimen; flower interiors and local node swellings remain simplified; root branching is coarse. A seed only reproduces this candidate—it does not establish a realistic domain-randomization distribution. Future architecture and organ-shape random streams should be separated so changing flower detail cannot alter unrelated branches.

Next: compare complete plants from the partner with whole-model front/side views, measure branch and node positions, then correct the highest-impact attachment and occlusion errors. Mechanics tests should be attached to this complete graph, with force–deflection and recovery calibration by organ. Do not return to an isolated leaf as the sole visible deliverable.

## Reproduce

```sh
/tmp/clonebench-cad-env/bin/python research/hemp-defoliation/whole-plant/build.py
/tmp/clonebench-cad-env/bin/python research/hemp-defoliation/whole-plant/render.py
```

Outputs are in `runs/hemp-whole-plant-v1/`: `index.html`, `plant.json`, `plant.glb`, `anatomy-graph.json`, and `report.json`. Serve the repository root on localhost port 8793 to load its existing Three.js dependency. This does not edit the desktop application or launch training.
