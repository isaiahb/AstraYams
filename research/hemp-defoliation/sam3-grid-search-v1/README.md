# SAM3 scale search and foreground audit

User request: test denser overlapping crops and quantify whether the visible plant is covered and its organs labeled. All inference and image processing run on an isolated RunPod A40. No local ML or image-processing jobs.

## Frozen comparison

- Original 381×444 reference, SHA256 in `protocol.json`.
- Leaf prompt; 30% adjacent overlap; grids 1, 3, 5, 10, 20, 25, 50, 100.
- Confidence 0.5 primary; 0.25 and 0.1 diagnostics, reported together.
- A fixed color-based foreground estimate, conservative core, permissive edge band and excluded frame/support region. This is a measurable proxy, not manually annotated ground truth.
- Skip crops with zero permissive foreground pixels. Report skipped counts. Background-only false positives in skipped tiles are consequently not measured.
- Score raw unions before foreground clipping. Coverage alone rewards overly large masks, so also report IoU and definite-background leakage.
- Retain crop-edge masks for area coverage, report them separately from complete-instance masks. Raw proposal counts are not leaf counts. Tiny crops can cover tissue while losing whole-organ identity.
- Keep lossless packed crop-local masks, scores, boxes and edge flags on each tested tile.
- No binary-search assumption: image quality is not monotonic with grid density.

## Organ proposal audit

Use the two best completed grids ≤10 by primary-threshold foreground-proxy IoU. Test `stem`, `flower` and `leaflet` in addition to `leaf`. Combine leaf/leaflet only as semantic tissue. Display overlapping semantic proposals as conflicts and uncovered foreground as unclassified. These are unverified proposals, not validated organ labels; scores across prompts are not calibrated probabilities.

## Resolution test

Primary dataset: Elisa Morales, Marcus Griffiths, Christopher Topp, *Images and parameters for manuscript on Hemp root and shoot diversity*, DOI 10.5281/zenodo.17783092, CC BY 4.0. The shoot archive has publisher MD5 744e231722aa8b7197bcd2b912fa5fcc. Download and extraction occur remotely.

4000×6000 source photographs show excised shoots on dark cloth, not intact standing plants. Select a fixed crop from sample 0 before segmentation and compare native pixels against the same crop resized to width 381. This tests resolution on one specimen; it is not independent validation across plants or a replacement for live-plant geometry evidence.

## Reproduction

`run_search.py` refuses non-RunPod execution before importing ML. Environment overrides: SEARCH_INPUT, SEARCH_OUT, SEARCH_GRIDS, SEARCH_SECONDS. Default workspace `/workspace/sam3-comparison`. Pinned SAM3 revision and official checkpoint hash are recorded with retrieved evidence. `postprocess.py` runs remotely. `build_review.py` only assembles static HTML from retrieved metadata.

Acceptance requires visually checking missed pixels, leakage, false organ assignments, overlaps and crop boundaries. Near-100% foreground coverage does not establish near-100% correctly segmented organs. No cultivation, pruning, robotic control or biological-damage conclusions follow from this experiment.

After the coarse sweep, refine the original reference at grids 7, 8, 9, 11, 12 and 15 in a separate output folder. The viewer combines leaf-area results, preserving which pass each row came from. The original semantic audit retains its initial chosen grids rather than silently changing its selection rule after refinement.

## Search-direction correction

The user explicitly corrected the search after 50×50 regressed: turn toward smaller crops-per-axis/grid counts rather than trying 100×100. The already completed 100×100 pass is retained as evidence, not a recommended search step. Future coarse searches must bracket the best score and refine inside that bracket; expansion into a direction already shown worse requires new evidence. In this run 5×5 and 20×20 bracketed the initial 10×10 primary-IoU winner.

## Living-plant reference correction and proposed residual experiment

The user rejected the additional excised-shoot photographs. Their task concerns leaf removal on living, upright, rooted/potted plants in the intended facility context. Archive excised images as completed segmentation diagnostics; do not fit target morphology, pose, attachment geometry or mechanics from them. Required replacement evidence: pot and main stem visible, natural posture, target-relevant plant stage and existing leaf-removal history, preferably multiple views of the same plant. Original PLOS Fig. 1 is described as one week before harvest; the crop alone does not show the pot or confirm a match to the intended task stage. Source: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0252985

User proposed blacking out accepted masks and rerunning segmentation on what remains. This is a worthwhile experimental condition, not yet tested here. Compare under equal inference budget: (A) unchanged-image repeat baseline; (B) blacked-out accepted pixels; (C) residual-guided overlapping crops from the unchanged original with context margins. Apply the same initial accepted masks and fixed scoring rules. Never equate low-confidence or conflicting masks with accepted labels. Score genuine new coverage, leakage, organ fragmentation/merging, original-image boundary agreement and cross-pass duplicate consistency. Black fill may create artificial edges, split partially captured organs, remove identifying connections or freeze early mistakes. Stop when new accepted coverage stalls; retain unknown areas explicitly. Predicted next-step preference: use residuals to choose crops/prompts while keeping original pixels available for recognition and review. No new inference was launched for this discussion.
