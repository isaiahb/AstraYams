# City Farmers / Freya strawberry simulation — reference brief

Research only, 2026-09-10. No CAD, simulation code, policies or desktop UI changed.

## Checkpoint and ownership

This research branch starts at **2458ece — Document continuous five-PPO physical cut and catch**. Its independent checkout is `/Users/isaiah/Documents/BallahTech/AstraFactory-IanResearch`, branch `codex/ian-city-farmers-research`. The original checkout and its training, servers and compute resources belong to the continuing task and must not be managed from this research task.

At this checkpoint, five PPO specialists coordinate a continuous physical cut-and-catch on the original designated-fruit scene. The net retains the fruit, but the final cutter pose contract times out; learned basket delivery is incomplete. Separately, support positioning passed four tests on two held-out anatomical plants. Neither result establishes a complete generalized harvesting system. See [the frozen evidence ledger](../../evidence/harvest-skill-suite/README.md) and [result summary](../../evidence/harvest-skill-suite/results-2026-09-10.json). Generated runs and policy files remain in the original checkout; the Git checkpoint preserves source and evidence summaries, not every generated artifact.

## What the supplied references establish

1. **Customer direction.** In his linked reply, Ian explicitly identifies Freya as what the production system will look like. This establishes the intended growing-system family, not an exact farm layout or a confirmed robot bill of materials. [Ian's post](https://x.com/ihwylie/status/2098173969891508720?s=20).
2. **Supplier architecture.** Freya describes inclined A-frame cultivation and aeroponic strawberry production, with a stated density of 20–25 plants per square metre of floor area. Use that density as a supplier-stated cross-check, not a measured plant-spacing specification. [Strawberry system](https://freyacultivation.com/strawberry-system/).
3. **Customer system context.** City Farmers identifies Freya as the growing-system partner and describes cultivation and robotics as parts of its intended operation. Its site explicitly labels renderings as concepts and its facilities/robotics capabilities as plans rather than operating results. The supplied robot-and-rack image is therefore layout intent, not an as-built engineering drawing. [City Farmers](https://www.cityfarmers.xyz/).
4. **Photographic geometry reference.** Freya's rack image shows facing inclined cultivation surfaces, repeated planting openings, overlapping leaves, fruit at several levels, horizontal lines along the crop rows, lower structural supports and an aisle. The line material, tension and purpose are not confirmed by the image. [Rack reference](https://freyacultivation.com/media/strawberry-aeroframe.webp).
5. **Root-side reference.** The interior image shows suspended roots, structural cross-members and longitudinal guides/cable routing. Freya separately describes mobile irrigation equipment. Do not treat this interior arrangement as evidence of an external harvesting-robot rail. Crop identity and exact assembly variant in this generic root illustration are unconfirmed. [Root-zone reference](https://freyacultivation.com/media/air-suspended-roots.webp), [supplier equipment description](https://freyacultivation.com/about/).

Website imagery was inspected directly. Marketing yield, quality and economic claims have not been independently validated and will not serve as physics calibration data. A dimension stated on Freya's **cut-greens** page must not silently become a strawberry-system specification.

## Consequences for the simulation

The useful initial unit is **one representative harvest bay and its aisle**, including the opposing crop face and a receiving location. Repeat the bay only after its geometry and manipulation constraints make sense.

| Element | Representation to prepare | Why it affects the task |
|---|---|---|
| Rack and growing faces | Parameterized frame, panels, openings, edges, cross-members and feet | Reach, approach clearance and accidental tool contact |
| Plant installation | Crown/holder interface at actual planting sites; roots behind the panel | Establishes the correct support boundary and growth orientation |
| Crop canopy | Anatomical plant instances with correlated variation across rows and crop stages | Occlusion, reachable stalks, neighboring fruit and leaves |
| Horizontal crop lines | Explicit geometry; classify purpose before choosing rigid or tensile physics | A thin line can obstruct or be cut by shears even when barely visible |
| Aisle and adjacent rack | Actual available workspace, floor/support obstacles and clearances | Determines whether two arms can reposition and cooperate |
| Robot positioning | Separate candidate mounting/vertical-travel/row-travel assemblies | The concept depicts a mast and rail, but their engineering details are unknown |
| Receiving workflow | Basket or tray location, entry clearance and growing occupancy | Determines transport distance and gentle placement constraints |
| Greenhouse light | Translucent enclosure, sunlight, shadows and plant reflectance | Relevant to eventual camera policies and perception tests |

Reuse the developed plant mechanics and YAM assets where applicable. Re-establish crown anchoring and settled growth shape for panel planting: rotating an entire hanging-trough plant would rotate gravity-shaped stalks and leaf arrangements incorrectly. The two YAMs remain our candidate evaluation hardware; the concept image does not establish that Ian selected YAM or a two-arm arrangement.

For harvest training, detailed root growth and atomized mist do not initially need full fluid/biological simulation. Their layout and interfaces matter; additional dynamics should be added when they can change the task outcome.

## Dimensions and assumptions to resolve before claiming a match

- Strawberry module height, width, length and growing-face inclination.
- Plant-site pitch, row layout, holder geometry, and actual crown mounting orientation.
- Crop-line locations and mechanical properties; other hoses or supports near the fruit.
- Aisle width, rack-to-rack spacing, floor obstructions and whether racks move.
- Harvesting carriage concept, available vertical travel, payload and arm mounting interfaces.
- Fruit/cultivar size range, maturity pattern, typical stalk accessibility and canopy density.
- Camera placement and harvest destination: mobile basket, fixed tray, conveyor or packout interface.

Evidence priority: applicable supplier drawings/dimensions, then scale-referenced photographs and walk-through footage, then explicit bounded estimates. Multiple views are needed to avoid reading perspective as a dimension. No outreach has been sent; these are the targeted gaps to close after extracting what existing references can support.

## Proposed first design-review milestone — not implemented

Prepare front, side and plan views of one bay, plus a view matching the supplier rack photograph. Every important dimension should identify its source or be marked an assumption. Include low, middle and high fruit targets, dense and sparse local foliage, an adjacent growing face and the receiving location.

The review should answer:

1. Do planting sites, crown angles, foliage and fruit presentation resemble the applicable references from matching views?
2. Can both tools reach the targets without crossing panels, crop lines, neighboring plants or the other arm?
3. Can a caught fruit travel to its destination without requiring an invented aisle or mounting clearance?
4. Do visible and collision surfaces agree where tools can touch? Do plant settling and contact tests remain credible after changing the mounting geometry?

Only then port policies or start new training. Keep architectural assumptions separate from measured plant mechanics, simulation results and hardware validation. This brief does not approve an exact farm layout or claim a calibrated digital twin.
