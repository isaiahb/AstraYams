# Harvest bay — specification and industrial design study 01

2026-09-10. Proposal for discussion; image exploration precedes CAD. This work is isolated from the continuing harvest-policy task.

## Purpose

Represent one useful portion of Ian's intended Freya-based strawberry farm well enough to design and subsequently test two-arm harvesting: identify a ripe fruit, bring a soft catcher beneath it, isolate and cut its own stalk, withdraw without harming neighbors, and transfer it into a receiving tray gently. The farm is the constraint; the robot layout is a candidate to test against it.

Source hierarchy and unknowns are recorded in [the reference brief](../2026-09-10-reference-brief.md). City Farmers calls its renderings concepts. Neither those renderings nor this generated study are measured geometry or proof of feasibility.

## First unit of work

One section of an inclined growing face, its A-frame structure, the opposite aisle boundary, a local harvest carriage and a receiving tray. Retain plants above, below and beside the target so reach and neighboring contact remain meaningful. Do not design a whole greenhouse or alter the existing desktop app.

| Assembly | Design intent | Evidence / status |
|---|---|---|
| Growing rack | Repeated inclined white panels on a structural A-frame; real planting openings; roots inside, crowns at the openings, canopy outside | Supplier photographic architecture; dimensions and interfaces unresolved |
| Crop | Irregular overlapping trifoliate foliage; branching fruit stalks; mixed maturity and berry sizes at several heights | Use the existing anatomical model later, re-established for panel mounting and gravity |
| Thin crop lines | Horizontal lines at reference-observed locations; explicit obstacles | Observed; purpose, material and tension unresolved |
| Aisle | Include opposing growing face, rack feet, floor and robot travel corridor | Supplier photo plus customer layout intent; width unresolved |
| Row travel | A low guided carriage travels parallel to the crop row | Our interpretation of the customer's concept, not a confirmed Freya harvesting product |
| Lift and standoff | Common vertical carriage with a crop-facing cross-slide or equivalent standoff adjustment | Proposed. A vertical lift alone does not follow an inclined panel; required stroke depends on inclination, height and reachable tool poses |
| Two arms | Reuse two existing YAM models; distinct bolted mounts, longitudinal separation and modest height offset to separate elbows and approach paths | Our evaluation hardware. Image-generated arms are layout placeholders; exact link lengths, joints, limits and mounting orientation must come from the URDF |
| Cutter | Small targeted shears with a slender approach; clear mechanical connection to the gripper | Tool concept/interface; blade actuation, stalk isolation and clearance require engineering |
| Catcher | Open soft mesh pocket held on a small rounded rim, presented below the selected fruit | User's selected functional direction. No hard enclosing cup or fruit-grasping claw |
| Receiving tray | Removable shallow lined tray beside the arms, carried by the same moving assembly | Proposed to reduce transport and drop height. Must not obstruct the net path, lower crop rows or cross-slide motion |
| Cables and sensing | Rear cable carriers; overview camera on the carriage and small wrist-camera allowances | Proposed; mounting, wet-environment protection and visibility need review |

## Operating sequence and physical requirements

1. Position row travel, lift and standoff for a local cluster; stop that carrier during fine manipulation in the initial concept.
2. Observe and select an accessible ripe fruit. Fruit maturity must not imply that its stalk is automatically accessible.
3. Place the catcher below the fruit, then approach its stalk with the cutter. Both tools and whole arms must have clearance from crop lines, foliage, fruit, panels and each other.
4. Cut only after the catcher is positioned. Detached fruit falls and contacts the mesh under simulation physics; it is never attached to the catcher by script.
5. Retreat the cutter into a verified free corridor before the catcher transports the fruit. Avoid neighbor contact during withdrawal as well as approach.
6. Bring the mesh pocket close to the tray and transfer at low relative speed with minimal free fall. Net lip, tray edge, previously collected fruit and basket occupancy are part of the task.

Later evaluation should record cut correctness, retained fruit, placement completion, impact speed/impulse, contact forces, non-target contacts and time. These are mechanical proxies, not a calibrated claim of bruise safety. Mesh compliance, stem failure and fruit damage remain separate calibration problems.

## Industrial design direction

Readable, serviceable machinery: anodized structural members, compact light-colored covers, dark joints, restrained teal tool accents, exposed fasteners only where they explain assembly, removable contact parts. Keep crop presentation botanical rather than a uniform decorative green wall. The visual language can use the project's subtle cel outlines while retaining believable materials and geometry.

The first image shows the architecture and paths. It is not an advertisement asserting a completed robot. A following detail should make the two independent tool attachments and cut/catch relationship legible. Image generation may approximate the YAM morphology; CAD must use the actual source assets without copying those approximations.

## Parameters to establish before CAD is called a match

- Rack height, width, bay length, panel angle, planting pitch and holder shape.
- Aisle width measured between canopy envelopes, not merely frame edges.
- Low and high fruit envelopes, panel setback with height, neighbor and crop-line positions.
- Arm mount separation, orientation and offset; tool and camera envelopes.
- Longitudinal travel, vertical stroke, cross-slide stroke and retracted corridor.
- Receiving-tray size, loaded mass, position and transfer clearance.
- Carriage support, center of mass, overturning loads, drive/brake arrangement and cable bend radii.

No dimension in an image is a supplier specification. Do not copy 60-degree panel or width figures from Freya's cut-greens product into its strawberry model.

## Review gates

**Now, image review:** architecture resembles the references; two arms have distinct mounts and roles; the receiver is reachable; support structure and crop-facing standoff adjustment can be understood; plants are not repeated clones. Preserve visible failures and write the next edit explicitly.

**After direction review, CAD:** front/side/plan layout with explicit sourced or assumed dimensions; exact YAM kinematics; low/middle/high crop reach and tray return; opposing rack and full-arm clearance; carrier load-path and wet-environment design review. Reject an attractive layout if it fails these checks.

**After geometric feasibility, simulation:** matching visible/collision surfaces, stable gravity settling on inclined mounting, blade/neighbor contact, cut/recoil, mesh capture and loaded-tray transfer. Reuse and re-evaluate plant mechanics. Do not port successful policies and imply they were validated in this farm without new tests.

## Ownership

Source checkpoint: `2458ece`; research checkpoint: `43f9c14`. This study changes only documents and concept-image assets in `AstraFactory-IanResearch`. Existing policy training, source checkout, servers and generated runs are not managed from this fork.
