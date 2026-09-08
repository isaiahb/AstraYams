# Prepared bench-arm demo evidence

Project: `cc24adc4-3f2b-410a-b4ae-45989045f793`, locally preserved under `apps/desktop/workspaces/` (ignored generated data).

Actual app sessions produced a brief, a mechanical revision, an independent failing re-test, a separate corrected revision and a second independent report. This is a prepared design/check/revision example, not a three-minute live CAD build or a robot-learning demonstration.

- ME01: shaft intersects base by 678.584013 mm³; tool screws lack nominal backing.
- ME02: independent CAD query confirms zero base/shaft overlap and 3 mm radial clearance. Four screws have full material backing and 8 mm nominal engagement; thread strength is unverified.
- Independent tester regenerated all 40 parts, verified 118 file hashes, reran submitted and regenerated geometry over 855 poses each, independently computed FK at 703 poses, and compared all five rendered images.
- Overall FAIL remains: retainer/collar and flange/wiring hardware overlaps, cable bends below the 30 mm requirement. Component capacities, continuous clearance, electrical design and physical behavior remain unverified.

Evidence: `ME02/manifest.json`, `ME02/details/base_before_after.png`, `verification_me02/REPORT.md`, `verification_me02/results.json` within the project directory.

ME02 manifest SHA-256: `b802c6aa50c51c96ace8e6a7948aad76344576b46a8cd1250f2a8e036c6459dd`.

Independent report SHA-256 at review: `b857e53e04cc977cdf37730ae1dc4784c74536c6fe173f934722c054403fa241`.

Show the whole assembly first, then the base section and the short finding. Do not imply that this isolated improvement passes the entire arm, establishes manufacturability or demonstrates a trained assembly policy.
