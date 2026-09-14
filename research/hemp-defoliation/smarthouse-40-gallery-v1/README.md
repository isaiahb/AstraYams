# All 40 Smarthouse plants: source-photo gallery

User request: inspect all 40 different plants, seeking leafier and more occluded subjects rather than more camera angles of one specimen.

## Contents

- 40 unique plant IDs, 084267-H through 084306-H, one unmodified 2472 x 3296 PNG each.
- Every image uses RGB_3D_3D_side_far_0 on 2021-02-18. The date was selected before the end of the experiment, when taller subjects increasingly exceeded the camera frame. It is not claimed to maximize each individual's foliage.
- Original source metadata matched 40/40 IDs: Han NE (20), Felina 32 (10), Ferimon 12 (10). Source genotype abbreviations retained in the manifest.
- Five pages of eight images, cultivar filter, jump to ID, source-PSA sorting, four-specimen comparison, fit/native-pixel view and original downloads.
- Photo files are cached locally and ignored by Git; manifests and download code preserve provenance and reproducibility.

## Metric caveat

Sorting uses the researchers' raw Projected Shoot Area (PSA) at DAP 29 from `data_code/Smarthouse/data/raw.dat.csv`. It is the sum of shoot areas across three views, measured in kilopixels. It is not leaf count, foliage density, overlap, biomass or task difficulty. Calendar-to-DAP alignment is inferred from the time-series endpoints and has not been independently verified. The photo date is explicit in each archive-member name. Do not interpret the source metric as computed from the displayed single photo.

## Visual caveat

Original photos include blue support cages, dark leaves and some yellow/brown tissue. Specimen 084293-H has a visually verified clipped shoot tip; the gallery flags it. Framing of the remaining 39 was not exhaustively audited at native resolution. Larger projected area alone does not ensure a dense leafy canopy. This is a vegetative research cohort, not a verified match for a mature commercial canopy. No plant anatomy was synthesized or altered.

## Sources and licenses

Images: Rachel Burton; APPF Plant Accelerator, University of Adelaide; UA (Gill). https://doi.org/10.25909/23211779.v1 — CC BY-NC 4.0.

Archive listing: https://projects.pawsey.org.au/appf-tpa-0541-ph-ua-gill-hemp-pia/index.html

Metadata: Alison Gill, Beth Loveys, Chris Brien, Nathaniel Jewell, Bettina Berger, Timothy Cavagnaro, Rachel Burton. https://figshare.com/articles/dataset/29097107 — CC BY 4.0. Original data archive https://ndownloader.figshare.com/files/55667573. Files copied without modification into metadata/.

Study: https://doi.org/10.1071/FP24266

## Reproduce

Install the small `remotezip` Python package, then run `python3 fetch_sources.py` and `python3 build_gallery.py` from this directory. The fetcher downloads only the selected archive member using HTTP ranges, not the full time-series ZIP. It caches successful downloads and retries missing records on a rerun. No image processing, ML inference, GPU or image generation is involved.

## Verification

All 40 source downloads completed without errors. Forty unique IDs matched source metadata, all native dimensions are 2472 x 3296, and every image uses the same date/camera. Browser pagination was checked across all five pages. Selected original portraits were visually inspected; the gallery is a browsing tool, not a completed organ annotation dataset.
