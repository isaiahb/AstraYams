# Height and developmental appearance evidence

Research checkpoint responding to the user's concern that the current indoor CBD-hemp model is not credible. Open `index.html` through the repository server. No plant geometry, material values, cultivation controls, robot policies or desktop application code were changed.

The board compares actual dated research photographs with an unchanged screenshot of our model and gives measured height results with their pooling/treatment context. These studies do not establish a commercial indoor standard or the partner's crop height. We have not reconstructed the paper plants, fitted a growth function, or validated our existing geometry.

## Sources

- Crispim Massuela et al. (2022), DOI 10.3390/plants11010140. Figure 1 on p5 contains a same-age architecture comparison at 65 DAP (rooted-clone planting), with an 80 cm ruler. The separate 93 DAP image is a flower closeup, not a whole-plant time point. CC BY 4.0.
- Burgel et al. (2020), DOI 10.3390/plants9060725. Figure 1 on p6 contains measured height histories. No-PGR control is pooled over genotypes; genotype curves are pooled over treatments. All plants were topped before treatments. The methods' transition date should be reconciled before translating the graph into a flowering calendar. CC BY 4.0.
- Schober et al. (2023), DOI 10.1016/j.indcrop.2023.117172. Publisher results text reports a fitted height asymptote of 80.3 ± 2.9 cm in a CBD-type greenhouse experiment. The full figure/raw data were not accessed. Do not present this fitted parameter as a commercial plant-height average.
- Anderson et al. (2021), DOI 10.1371/journal.pone.0252985. Article text describes repeated medium-to-apex height observations at 31/36/52/67/77/99/114 DAS, plus near-harvest images and growth curves from the same greenhouse experiment. Image endpoint display failed; no local images, numeric supplementary files or curve fit imported.

## Reproduce the figure crops

Run `python3 research/hemp-defoliation/height-evidence-v1/build_figures.py` from the repository with Pillow and Poppler installed. The local PDFs are open-access paper copies obtained from Semantic Scholar mirrors; original publisher DOI links are retained above and in `sources.json`. Crops retain all figure panels, axes and scale markings. The board paraphrases captions and links full source PDFs. `figure-provenance.json` records page, crop coordinates and source hashes.

## Modeling decision

Do not adjust final height alone or relabel the dimensionless 0–100 index as days. First select a consistent cohort; fit both height and visible topology; retain stage, scale, genotype and history; then compare held-out dates/plants. Whole-plant mechanics remains separately unvalidated. The next visual deliverable should show a documented real specimen and reconstruction from matched views, with explicit geometric errors and unresolved hidden organs.
