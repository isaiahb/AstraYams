# Whole-plant variation and development v3

The viewer compares eight procedurally distinct plant graphs at the same scale and reference age. Four architecture families prioritize greenhouse/indoor-oriented forms: compact multiple-leader, upright branched, tall open, and broad lateral canopy. The old photo-fitted v2 remains intact.

These are **morphology scenarios**, not eight scanned plants, not verified reconstructions of named cultivars, and not a fitted commercial population. Indoor/greenhouse bias is a user-directed sampling choice. The two short-main-axis forms include an assumed prior management history. There is no optimization or prescription for that history.

## New primary evidence

1. Anderson et al. 2021, DOI [10.1371/journal.pone.0252985](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0252985), S2 raw phenotype dataset, CC BY. We imported repeated greenhouse heights from five essential-oil hemp cultivars. `reference-data.json` gives median, interquartile bounds and n at each observed date. Values are pooled across all six experimental treatments; they do not isolate genotype or represent commercial standards. The geometry uses a nondecreasing envelope of the observed medians; the plot preserves small late declines. These are summary trajectories, not one tracked median plant. Units in the source height columns are centimetres, converted to metres. Source file retained byte-for-byte with SHA256.
2. Islam et al. 2022, DOI [10.3389/fpls.2022.984410](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2022.984410/full), Figures 2 and 9, CC BY. Indoor Alpine Star CBD research separates shoot length, branch count, leaf length and leaf width across observation times. Used to justify separate morphology descriptors; numerical treatment-response functions are not imported. The remote original image in the viewer is a treatment comparison, not a development film or factory average.
3. [Greenhouse hemp morphology study, 2026](https://pubmed.ncbi.nlm.nih.gov/41787587/). Abstract describes lower main height and longer side shoots following changes to apex history in two industrial-hemp cultivars. Used only as qualitative support for multiple architecture histories, not specific topology, dates, dimensions or an operational protocol.
4. Existing Balant et al. 2024, DOI 10.1111/nph.19817, Futura75 two-dimensional leaflet outline. Reused with the previous source attribution; not an exact CBD cultivar leaf reconstruction.

The general indoor Gelato lighting paper and field morphology papers were found but their production settings and dimensions were not used as CBD greenhouse defaults.

## Parametric representation

`plant.mjs` is the authoritative deterministic generator. Each family has joint priors for main-axis count/history, branch abundance, secondary branching, canopy spread, blade size and blade width. Four sliders modify height, spread, branch abundance and leaflet width. New individual changes a numeric seed; it changes actual axes and organs while retaining the selected family. Export parameters preserves every specimen input and current reference age.

Primary lateral origins select available main-axis nodes, at most two at a paired node and one at an alternating node. Their azimuth follows the associated main leaf with bounded offset. Node identities and parentage are stable through the replay. Branch/leaf count, phenotype proportions, 3D depth, tissue dimensions and angle distributions are priors. Correlation within a family is authored, not estimated from a population covariance matrix.

DAS is the source experiment's age after sowing, used as a reference clock between 31 and 114 only. There is no extrapolation beyond the measured window. The reference height trajectory drives a dimensionless growth fraction. Axes expand through a soft apical growth front; children depend on their supporting node. Existing internodes do not shrink as new ones expand. A one-time final vertical calibration sets scenario extent; there is no per-frame whole-mesh scaling. Generated whole-canopy height can differ from the reference dominant-apex height, especially while lateral shoots develop. The plot and source label remain distinct from modeled extent; these are growth-guided scenarios, not height-fitted reconstructions.

Leaves expand after their supporting internode, with independent pose, size and mild late-stage color change. The reproductive envelope has a separate assumed expansion window. This is **not** a carbon/water/light/hormone, senescence, regrowth, gravity or contact solver. Age colors and flower proxies are illustrations. No learned robot policy runs here.

## Visual review and corrections

The first close-up showed upper internodes extending too far and a crowded low canopy. That candidate is saved as `evidence/rejected-long-upper-internodes.png`. The revision compresses terminal internodes, includes terminal foliage, moves secondary branches higher, and reduces excessive leaf-size taper. These remain priors requiring reference matching. A separate audit found and constrained possible excess primary branches sharing a node. Controls were corrected to retain default parameter precision.

The gallery uses identical units and camera scale for every specimen. It is a comparison layout, not a simulated facility rack. Inspect one provides orbit, side and overhead views. The source curves plot observed medians; model heights are scaled and depend on scenario structure. The viewer labels that distinction.

## Reproduce

Use Python with NumPy and Node.js:

1. `python3 research/hemp-defoliation/development-v3/build.py`
2. `node research/hemp-defoliation/development-v3/audit.mjs`
3. Repeat step 1 to sync the new audit to `runs/hemp-development-v3/`.
4. Serve the repository and open `/runs/hemp-development-v3/index.html`.

The source CSV is attributed published research, not generated training data. Generated runtime files remain under ignored `runs/`. No model weights or generated rollout datasets are committed.

## Validation limits and next evidence

Audit covers deterministic regeneration, all 84 daily states for eight default specimens and eight parameter-boundary cases, unique organ IDs, attachment continuity, nonnegative radii, finite coordinates, nonshrinking internodes and distinct default graphs. This tests code invariants, not botanical realism.

The next priority is matching several individual indoor/greenhouse plants: node topology, leaf landmarks, height/width profiles and recorded management history. A second view is needed to constrain depth. Canopy occlusion and plant-to-plant contact then need separate tests. Current flower envelopes, leaf poses and actual phenotype sampling probabilities remain visibly uncalibrated.
