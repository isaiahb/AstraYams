# Indoor hemp anatomy and work context

User direction, 2026-09-12: represent whole CBD hemp plants as encountered in an indoor commercial facility. This is the current visual study. The original [whole-plant candidate](../whole-plant/ANATOMY.md) remains preserved.

## What changed

Three independently generated whole-plant candidates share a supported bench, individual containers, irrigation routes and suspended light fixtures. The original organ geometry and attachment graph are reused. Each plant has a namespace (`A/`, `B/`, `C/`), its own geometry, configuration and geometry hash. The isolated specimen view extracts B from the same exported mesh; it does not substitute a different plant.

Height, node count, lower paired-node count, branch length, leaf length, azimuth and the procedural seed differ between candidates. This is an explicit geometry sensitivity example, not a fitted biological distribution, a growth model, or evidence of policy generalization. There is no claim that these parameter combinations correspond to specific cultivars.

An optional trellis layer is hidden by default. Its presence, geometry and tension are unconfirmed for the partner. Switching it on only exposes a possible obstruction layout; neither cord deformation nor plant contact is simulated.

## References personally inspected

1. **Islam et al. (2022), Fig. 9.** The photographed indoor hemp groups show neighboring canopies, suspended fixtures and differences in plant height and posture. This supports including the shared indoor context and avoiding one universal indoor silhouette. It does not establish commercial dimensions, flower-stage architecture or mechanical properties. No lighting, nutrition or production recipe is inferred. [Original paper](https://doi.org/10.3389/fpls.2022.984410), [figure](https://www.frontiersin.org/files/Articles/984410/xml-images/fpls-13-984410-g009.webp). CC BY; remotely embedded with attribution.
2. **Cornell CALS (2020), photographs by Justin James Muir.** The hero photograph shows individual hemp containers grouped on research benches, with adjacent foliage and an access aisle. This is greenhouse reference evidence, not an indoor factory reconstruction. The model's tray, rack, pot dimensions and water routing are assumptions. [Source and photograph](https://cals.cornell.edu/news/2020/02/genetics-not-field-conditions-makes-hemp-go-hot). Linked, not copied into the repository.
3. **Existing botanical evidence.** The [whole-plant study](../whole-plant/ANATOMY.md) documents the anatomy and leaflet-outline sources. They establish structural relationships, not this facility's crop architecture.

## Parameter and claim ledger

| Item | Status |
|---|---|
| Indoor commercial CBD hemp context | User specified |
| Whole-plant organ hierarchy | Botanical references; simplified implementation |
| Three plant poses and dimensions | Assumed candidates in `config.json` |
| Bench, aisle, container and fixture dimensions | Assumed scene layout |
| Continuous main shoot | Preserved hypothesis; partner pruning history unknown |
| Optional net | Unconfirmed hardware/layout hypothesis |
| Growth, gravity-settled posture, contact and root anchorage | Not simulated |
| Materials, damage, cutting and recovery | Unmeasured; no calibrated values assigned |
| Robot, tool, sensor poses and operational reachability | Not established by this scene |
| Visual illumination | Presentation lighting; not radiometric calibration or a growth model |

The scene is a single bench module rather than an invented complete factory floor. It deliberately leaves the relevant working space visible. There is no room HVAC model, supply reservoir, electrical installation, fluid flow, greenhouse reconstruction, or production scheduling model.

## Review and checks

The builder verifies resolving unique organ IDs, acyclic parent graphs, finite vertices, valid face indices and nondegenerate triangles. `audit.py` additionally checks node/parent centerline continuity, petiole and branch attachments to nodes, root containment within the assumed pots, distinct specimen geometry, pot-bottom contact with the tray, and nominal overhead fixture clearance. These are geometric checks only. They do not establish collisions between all leaves, compliance, root fixation or safe robot access.

The scene is reviewed from the bench, aisle, isolated plant, branch structure, node, roots and overhead views. An initial inspection exposed hanging-wire endpoints without crossmembers; crossmembers were added before the final evidence was saved. Source/render hashes distinguish the final artifact from that initial preview.

## Next consequential gaps

1. Match the partner's actual whole plants and working layout: calibrated front/side photographs, container size, branching/training history, neighboring clearance and any net/support contacts. The current figure is a context example, not a matched reference comparison.
2. Resolve branch and leaflet pose/occlusion errors before increasing the plant count. The canopy remains more procedurally regular than photographed plants, and floral regions are simplified. Current height/node choices have no fitted biological distribution.
3. Add a supported whole-plant mechanics experiment: root boundary → main shoot → branch → petiole → separate leaflet surfaces, with controlled contact and recovery measurements. A trellis, if present, must transmit force and create real snagging constraints rather than merely intersecting the drawing.

The earlier isolated-leaf elastic candidate failed and is not silently reintroduced. No PPO or contact manipulation was run for this layout revision.

## Reproduce

```sh
/tmp/clonebench-cad-env/bin/python research/hemp-defoliation/indoor/build.py
/tmp/clonebench-cad-env/bin/python research/hemp-defoliation/indoor/audit.py
/tmp/clonebench-cad-env/bin/python research/hemp-defoliation/indoor/render.py
```

Serve the repository root on localhost:8793. Open `/runs/hemp-indoor-v1/index.html`. Rendering uses the exported geometry with fixed, visual-only MuJoCo meshes and no dynamics steps. The interactive viewer uses the same geometry from `plant.glb`.
