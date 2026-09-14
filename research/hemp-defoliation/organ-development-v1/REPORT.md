# Hemp organ development for anatomical simulation

## Findings

A useful developmental model needs separate representations of organ identity, appearance, expansion, maturation and loss. The existing growth-history-v2 model preserves some connectivity but couples many events to one arbitrary clock. Its numerical settings do not constitute a measured hemp growth history.

The available evidence supports a stronger anatomical model now, but not a universal table of days and growth rates for every organ. Quantitative observations come from different populations, including field fibre hemp, controlled-environment seedlings and mixed Cannabis accessions. They must remain separate cohorts. A dense indoor plant cannot be constructed credibly by combining every published maximum.

The recommended target is a **cohort-conditioned organ graph**: a seed-origin or cutting-origin starting structure, with each axis carrying nodes, attached leaves and buds, plus independently tracked organ ages. High-foliage examples should be a labeled challenge subset of this model. They are not established as the preference of every grower.

## Anatomical inventory and developmental order

The hemp BBCH description distinguishes germination, leaf development, lateral shoot formation, elongation, reproductive development and senescence. These stages overlap: leaf development is not completed before elongation begins. Its early leaf sequence distinguishes the simple first true-leaf pair from later compound pairs. Its lateral-shoot stage overlaps the seven-to-nine-or-more leaf-pair stages in that description; this is a stage association, not a universal bud-delay rule.[^1]

| Structure | Developmental identity | Representation needed | Quantitative gap |
|---|---|---|---|
| Seed and embryo | Starting structure for a seed-derived plant | Optional initialization record; never insert a seedling stage into a mature cutting history | Germination/emergence duration for the target cohort |
| Primary and lateral roots | Below-ground branching system | Parent-connected root graph, or an explicit reduced anchorage boundary for an above-ground study | Target root growth and anchorage stiffness |
| Adventitious roots | Roots formed on cutting-derived material | Separate origin metadata and initialization | Target clone root architecture over time |
| Hypocotyl | Seedling axis below cotyledons | Independent length and diameter history | Cohort-specific dimensions and tissue properties |
| Cotyledons | Seed leaves, separate from true leaves | Persistent identity and explicit aging state | Unfolding and retention duration |
| Shoot apex | Site of ongoing axis development | Explicit apex state per active shoot | Primordium initiation intervals |
| Nodes and internodes | Repeated axis units | Node identity, rank, parent axis, adjacent segment length | Rank-dependent extension curves |
| Petiole | Connection between axis and leaf blade | Its own geometry, local frame and mechanical link | Elongation, diameter and bending response |
| Compound leaf and leaflets | A leaf contains several blades | One leaf ID with child leaflet IDs; leaflet number is not leaf count | Cohort-specific expansion and lifespan |
| Axillary buds | Potential lateral growth at nodes | Bud existence separate from bud activation | Dormancy/outgrowth probability and delay |
| Lateral shoots | Higher-order axes | Each has its own apex and organ history | Branch-order-specific development |
| Stipules | Small appendages requiring correct node-level identification | Explicit small-organ category pending reference annotation | Size, persistence and stage-specific geometry |
| Reproductive structures | Distinct organs, not enlarged vegetative buds | Separate bract, flower and inflorescence identities | Target-cohort chronology and geometry |
| Surface tissues and veins | Sub-organ anatomy | Visual or mechanical detail only at useful resolution | Thickness, friction and stiffness data |
| Senescent and lost organs | Historical organs with changed state | Retain identity and attachment history after visibility changes | Cohort-specific aging and detachment evidence |

This table is a proposed simulator inventory, not a claim that all these structures have been measured. Unresolved categories remain explicitly unparameterized.

Seed-grown hemp generally has a branched taproot. UC Davis notes a more fibrous form in cutting/transplant contexts but explicitly describes limited evidence for that generalization. Its page also contains an apparent error calling hemp a monocot; that sentence must not propagate into model assumptions. Root-origin distinctions are useful, but this extension page does not supply a validated root-growth model.[^2]

## Leaf form and organ age

Balant and colleagues analyzed 341 leaves from 24 seed-grown individuals representing nine accessions. Their material supports changes in leaf form with accession and developmental position. The paper describes increasing leaflet complexity followed by reduction toward inflorescence-associated leaves; it does not support a universal fixed progression terminating at seven leaflets. Its data and code include leaf outlines and landmarks, useful for geometry but not time-resolved expansion of individual attached leaves.[^3]

**Model implication:** distinguish a newly initiated leaf's age from the axis's developmental identity. A new leaf on a mature lateral axis should not automatically replay the first leaf of a seedling. Likewise, a leaf with five leaflets is one organ, not five independent node attachments. Leaflet shape, relative size and count should be conditioned together on the relevant accession and node position. Reusing one outline at every rank misses that structure.

The current model assigns three leaflets to every new lateral shoot's first leaf and five thereafter. This is a scenario rule without a demonstrated cohort fit. Replace it with a profile lookup that can explicitly return “unknown” until suitable records exist. Do not invent a distribution merely to fill every field.

## Timing and numerical evidence

The following quantities have different meanings. They cannot be pooled into one minimum-to-maximum growth-rate slider.

| Quantity | Evidence | Interpretation and use |
|---|---|---|
| Leaf appearance | Indexed thesis chapter reports 0.152 leaf pairs/day on average, approximately one pair per 6.6 days | Field fibre-hemp observation, not indoor clone timing |
| Thermal leaf appearance | Same chapter reports 0.0149 pairs/degree-day and 33.5 degree-days per single leaf, using a 1°C base | A single leaf is not a paired-node event; full extraction remains necessary before implementation |
| Variation at a fixed age | Same chapter reports four to ten pairs at 40 days after emergence | Observed developmental spread, not a confidence interval or universal cultivar range |
| Hypocotyl maturation | Santhica 27 sections at 6, 9, 12, 15, 17 and 20 days after sowing | Discrete histological observations, not a complete elongation curve |
| Leaf shape | 341 leaves, 24 plants, nine accessions | Cross-sectional morphometry; not days between new leaves |
| Petiole length | Indexed hybrid-hemp study table reports 1.2–8.0 cm, mean 3.86 cm | Endpoint morphology lead; full table/population verification required before sampling |
| Leaf expansion, retention, bud delay | No transferable target-cohort range established in this review | Keep separate unknown parameters |

The leaf-appearance figures above come from the indexed text of van der Werf's 1994 thesis, chapter 4, page 54; direct PDF retrieval failed. The university record verifies the thesis's identity and year, and a related 1995 journal paper is indexed. These numbers are **provisional extraction evidence**, not newly validated defaults. Their thermal-time units and leaf-pair convention require particular care.[^4][^5]

In Santhica 27 hypocotyls, Behr et al. report elongation having stopped by the nine-day observation while secondary growth proceeds; later sections show developing secondary xylem and bast fibres. This establishes why length and girth need separate developmental states. It does not establish a nine-day rule for every stem segment or cultivar, nor give petiole stiffness. The discussion also refers to cessation at the later H20 observation; the explicit results at H9 are the clearer event statement, not a reason to fabricate a 9–20-day cessation distribution.[^6]

The petiole range is retained only as a discovery lead because full PMC access returned a verification page. A pooled range from hybrids would not, by itself, describe variation within one commercial clone cohort.[^7]

## Branches and continued growth

Microscopy in the 2019 architecture study distinguishes main and axillary meristems and changing vegetative/reproductive phytomers. It shows that reproductive architecture involves continued production and altered organ combinations, not simply stopping the entire plant. The study's medical Cannabis material is not a numerical calibration for the target hemp population. Its useful contribution here is organ topology and differentiation, not production scheduling.[^8]

**Implementation consequence:** separate three questions:

1. Does a bud exist at this node?
2. Has that bud begun visible outgrowth?
3. Is its resulting axis still producing or expanding organs?

The present generator creates buds only for selected node ranks, then activates all of those after nearly the same delay. That conflates absence, dormancy and activation. Lower foliage can consequently appear according to the script rather than a tested developmental history. Store all modeled eligible buds, but permit dormant, active and terminated states. Activation rules must remain hypotheses until compared with observations.

Continued simulation must also allow organs to mature or be lost. Unlimited addition with no senescence creates increasing density by construction. Conversely, fixed axis caps create an artificial final height. Neither is a biological explanation. An explicit finite study horizon is acceptable; it should remain visibly distinct from biological termination.

## Dense-canopy variation

“Grows a lot” needs a measurable definition. Height, projected coverage, total leaf area, number of active lateral axes and number of leaves are separate variables. A tall plant need not present a densely occluded manipulation scene. A large count of small leaves need not equal the leaf area of fewer broad leaves.

For the simulation, use a reference cohort and retain correlated records where possible: node spacing, branch lengths, leaf dimensions and developmental stage from the same individual. A dense challenge case can be selected using projected leaf coverage and gap size from a fixed set of views. Keep this selection label attached to results so it does not silently become the assumed prevalence of real plants.

Do not independently maximize leaf size, branch number, petiole length and growth rate. That produces a composite for which no plant has been observed. If joint data are unavailable, expose alternative scenarios and uncertainty rather than labeling them cultivar replicas. A selected scenario is useful for testing occlusion but is not biological validation.

## Mechanics boundary

This research supports structural organization more strongly than physical coefficients. A rendering of secondary tissue is not a measured elastic modulus. The initial mechanics model should distinguish unloaded growth geometry from deformation under current gravity and contact. Retained organ mass, attachment location and local thickness need to travel with each organ's identity.

For a beam approximation, bending resistance depends on both material and cross-section. Thus changing radius to improve a silhouette also changes the mechanical hypothesis. Record those changes separately; do not silently adjust stiffness to obtain attractive motion. Thin leaf surfaces may need a reduced vein-and-blade representation, but the selected representation must be tested against displacement and recovery observations.

No new force, damage or separation thresholds are established by this report. Root anchorage can initially be an explicit boundary assumption. It should not be presented as simulated roots if it is actually a fixed base.

## Model revisions supported now

| Existing shortcut | Proposed replacement | Acceptance evidence |
|---|---|---|
| One expansion clock for leaves and internodes | Separate appearance, leaf expansion, petiole extension and segment extension fields | Exported histories show independent states and retain units/provenance |
| Leaf buds only at hard-coded ranks | Explicit bud identity and state | Every modeled bud has a parent node; dormancy is not deletion |
| Juvenile sequence reset on every branch | Axis identity and cohort/rank-conditioned morphology | Matched organ comparison, with unsupported stages marked unknown |
| Fixed 1/3/5/7 main-axis sequence | Empirical leaf-profile records where available | Source-linked outline and leaflet metadata, not just visual variety |
| Permanent mature leaves | Explicit mature/senescent/lost states | Counts distinguish initiated, retained and visible organs |
| Arbitrary final height | Explicit study horizon and growth termination status | No claim that the last frame predicts mature height |
| One dense specimen | Correlated cohort samples plus labeled challenge cases | Multi-view coverage, leaf-area and topology comparisons |

These are engineering proposals derived from the evidence audit. They are not fitted biological laws. The next implementation should make these states explicit before changing numerical rates. That allows subsequent calibration to improve one organ process without corrupting unrelated timing.

## Reference figures and data to inspect

- BBCH paper, table and stage descriptions: developmental ordering, not a timed photo series.[^1]
- Balant et al., Figures 1, 2 and 6: accession/node-associated leaves, real scans and modeled shapes. Detached leaf scans are valid outline evidence, not whole-plant posture.[^3]
- Behr et al., Figure 1 and supplementary elongation image: age-indexed cross-sections and hypocotyl development. Microscopic scale is not whole-plant scale.[^6]
- Spitzer-Rimon et al., Figure 2: axis and phytomer organization. Different study material; transfer only the explicitly justified anatomical concepts.[^8]

No reference image has been generatively enhanced or passed off as a measurement. Source links are retained; reproduction and dataset licenses need verification before incorporating assets into a distributable simulator.

## Sources

[^1]: Mishchenko et al. (2017). [Phenological growth stages of hemp (Cannabis sativa L.): codification and description according to the BBCH scale](https://www.lmaleidykla.lt/ojs/index.php/zemesukiomokslai/article/download/3496/2295). Žemės ūkio mokslai 24(2), 31–36. Full six-page PDF accessible.
[^2]: Hotz, M., UC Davis (2023). [Vegetative Plant Parts of Hemp](https://hemp.ucdavis.edu/guidelines/vegetative-plant-parts-hemp). Extension overview; root caveat and textual taxonomy error noted above.
[^3]: Balant et al. (2024). [Intra-leaf modeling of Cannabis leaflet shape produces leaf models that predict genetic and developmental identities](https://doi.org/10.1111/nph.19817). New Phytologist 243, 781–796. [Accessible author-institution PDF](https://diposit.ub.edu/bitstreams/83769daf-d56f-4955-9260-98153873590c/download). [Author data/code repository](https://github.com/BalantM/Cannabis_leaf_morpho_updated), identified in the paper; repository contents not newly audited.
[^4]: van der Werf, H. (1994). [Crop physiology of fibre hemp](https://doi.org/10.18174/202103). Wageningen doctoral thesis. [University bibliographic record](https://research.wur.nl/en/publications/crop-physiology-of-fibre-hemp-cannabis-sativa-l/). Numerical passage available through indexed chapter text; direct PDF access unsuccessful this pass.
[^5]: van der Werf, Brouwer, Wijlhuizen and Withagen (1995). [The effect of temperature on leaf appearance and canopy establishment in fibre hemp](https://doi.org/10.1111/j.1744-7348.1995.tb05389.x). Annals of Applied Biology 126, 551–561. Bibliographic identity verified; not an independent replication of the thesis figures.
[^6]: Behr et al. (2016). [Studying Secondary Growth and Bast Fiber Development: The Hemp Hypocotyl Peeks behind the Wall](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2016.01733/full). Frontiers in Plant Science 7:1733. Results, Figure 1 and discussion examined.
[^7]: [Morphometric relationships and their contribution to biomass and cannabinoid yield in hybrids of hemp](https://pmc.ncbi.nlm.nih.gov/articles/PMC8643699/) (2021). Petiole values are indexed-table leads; full text unavailable on this pass. Do not treat them as approved parameters.
[^8]: Spitzer-Rimon et al. (2019). [Architecture and Florogenesis in Female Cannabis sativa Plants](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.00350/full). Frontiers in Plant Science 10:350. Anatomy transfer only; target population differs.
