# Cultivar-conditioned nominal plant models v1

This research slice replaces the broad “generic indoor plant” prior with five named, measured greenhouse hemp cultivar profiles. It does **not** claim that the scalar dataset is a complete 3D or mechanical plant model.

## Recommended first placeholder

Use **Cherry Blossom at 50 ppm N** as the first nominal flowering plant while the design partner's cultivar is unknown. The source study grew five feminized essential-oil hemp cultivars from seed through eight vegetative and eight flowering weeks. The paper reports that 50 and 150 ppm N produced the tallest, highly branched, healthy plants, and it identifies 50 ppm N as the optimal measured fertilizer rate. The 50 ppm group supplies five or six plant-level records for each cultivar.

The five available nominal profiles are Cherry Blossom, Cherry Blossom (Tuan), Berry Blossom, Cherry Blossom × Trump, and Cherry Wine. `nominal-models.json` retains every usable plant vector from the 50 ppm nominal group and the combined 50/150 ppm healthy envelope. Each vector keeps its height history, stem diameters, cola dimensions, and biomass measurements together.

## Domain randomization rule

Condition the generator on this hierarchy:

1. species;
2. named cultivar;
3. seed lot or clone line;
4. facility recipe and management history;
5. developmental stage;
6. individual plant.

For the current dataset, randomly select a **complete plant row** from the chosen cultivar and condition. Do not sample height, stem diameter, cola density, and biomass independently from separate marginal ranges. With only five or six records in the nominal group, empirical resampling is safer than fitting a high-dimensional Gaussian. The 50/150 ppm envelope is suitable for a broader healthy cohort; stressed fertilizer treatments must remain a separate condition.

Branch topology, leaf attachment pose, tissue stiffness, cutting force, detachment thresholds, damping, and collision geometry are not measured in this dataset. Those parameters remain unresolved and should not be described as cultivar-fitted.

## What the second dataset adds

Gill et al. provide daily side-view images and projected shoot area for Felina 32, Ferimon 12, and Han NE, with 10, 10, and 20 plants respectively. That is useful for early growth shape and within-genotype visual variation. It ends at day 36 and does not establish flowering architecture. The tabular dataset is CC BY 4.0; its related image archives are CC BY-NC 4.0 and are retained here only as attributed research thumbnails.

## Strawberry parallel

LAST-Straw provides 84 point clouds: six plants, three each of Driscoll's Katrina and Driscoll's Zara, scanned 14 times over 11 weeks. Twenty-eight scans include organ-level class and instance labels, and the dataset supplies skeletons for stem-like structures. That makes it a much stronger geometry source for a cultivar-conditioned strawberry model than any open whole-plant Cannabis dataset found in this search. Its project page does not state a reuse license, so verify terms before redistributing files or using them in a product.

## Terminology

**Cultivar** is the correct word; “cultifier” is not. A cultivar is a named cultivated plant group selected for stable distinguishing traits. It may be propagated by seed, cuttings, runners, grafting, or another method. A **clone** is a vegetatively propagated, genetically identical lineage from one donor or mother plant. A cultivar may be represented by one clone, several closely similar clones, a stable seed line, or a hybrid population, so the words are not synonyms.

For a production cohort, the precise description is: “cultivar X, clone line or mother Y, grown under recipe Z.” The same terminology applies to strawberries: “the Driscoll's Katrina cultivar,” followed by the nursery batch or clone lineage if that identity is known.

## Reproduce

Run:

```bash
python3 research/hemp-defoliation/nominal-cultivars-v1/build.py
```

Then serve the repository and open `/runs/hemp-cultivar-nominals-v1/index.html`.

All source URLs, licenses, derived-image notes, and local inputs are listed in `sources.json`.
