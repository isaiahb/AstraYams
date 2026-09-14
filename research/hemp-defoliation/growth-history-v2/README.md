# Growth history v2 — continuous stem geometry

Preserves v1 and changes one bounded issue: adjacent stem segments now share a boundary radius. The hypocotyl grows in radius with the main stem instead of remaining a fixed thin neck beneath it.

Evidence: inspection of v1 source revealed independent per-segment taper and fixed hypocotyl radii. This is an implementation correction, not a measured biological thickening law. Existing botanical sources and their limitations remain in sources.json and the review page.

Run `node research/hemp-defoliation/growth-history-v2/check.mjs`, then `python3 research/hemp-defoliation/growth-history-v2/publish.py` from the repository root.

Reviewed the mature skeleton from the side in the browser. Shared radii remove the basal pinch; the skeleton remains regular and narrow. Segment frames and branch junctions are not welded physical tissue meshes. Growth time, dimensions and basal thickening remain uncalibrated. No elastic mechanics, contact, light competition or physiology is validated.

Next evidence gap: compare node spacing and branch-order silhouettes across matched views and developmental stages before adding more foliage. No training or heavy compute was performed for this revision.
