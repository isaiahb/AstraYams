# Partial specimen reconstruction

First manually traced scaffold from preserved published image: panel (a), L specimen. This is a treated dated research plant, not a verified representative pre-removal crop. Source DOI, crop, attribution and explicit limitations in specimen.json. Figure pixels unchanged; SVG clips the chosen panel in the browser.

Three approximate axis paths follow publisher main/side guide annotations. Their basal attachment is a hypothesis, not observed ground truth. Four partial blade regions have null parents, so they are not physically connected organs. All depth zero/unresolved; no arbitrary depth, material or growth parameters introduced. Large amounts of foliage and all floral structures remain unmodeled.

Inspected matching/front, side and top views. Side/top intentionally collapse because no depth is known. Corrected source SVG overflow and normalized camera alignment. Coordinate round-trip and declared axis-attachment checks pass; these check transfer only, not annotation accuracy, biology or mechanics. Manual traces have approximation error and do not cover serration detail.

Run node research/hemp-defoliation/specimen-reconstruction-v1/check.mjs and python3 research/hemp-defoliation/specimen-reconstruction-v1/publish.py. Existing server path /runs/hemp-specimen-reconstruction-v1/index.html.

Next: improve visible-organ annotation and resolve parent hypotheses; obtain multi-view specimen evidence for depth. This is not yet a complete plant or a robot training environment. No ML, inference, render batches or GPU jobs used.
