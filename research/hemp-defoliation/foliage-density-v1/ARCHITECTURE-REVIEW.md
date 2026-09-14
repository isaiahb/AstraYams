# Architecture and mechanics review — 2026-09-13

## Disposition: density revision is not an accepted plant model

User review correctly rejected the plant from other angles. Reviewed top and
side views, including the bare branch structure, in the live comparison.
Adding connected organs improved density but preserved the wrong architectural
assumption. Do not iterate by adding another batch of leaves.

The photo-fit generator maps annotated image coordinates into X/Z, then gives
branches a sinusoidal Y displacement. Many observed leaf directions also come
from that image plane. This is a projected reconstruction hypothesis, not a
developmental model. A successful frontal fit cannot establish a plausible 3D
plant. The additions inherit that bias.

Exported mesh bounds, not real measurements:

| Variant | Width (m) | Depth (m) | Height (m) |
|---|---:|---:|---:|
| Photo-fit baseline | 0.9432 | 0.3327 | 1.3117 |
| Foliage revision | 0.9458 | 0.4950 | 1.3117 |

These bounds diagnose the reconstruction; they do not imply that real plants
must have equal width and depth. Adding depth by scaling Y would also fail to
establish correct branching, attachment or leaf orientation.

## Evidence that changes the model design

1. **Developmental state and origin matter.** USDA's hemp descriptor handbook,
   architecture section, distinguishes the opposite-to-alternate transition of
   seed-grown plants from the generally alternate pattern in cuttings. Thus a
   clone cannot simply be replayed as a seedling with a different random seed.
   Use its initial branch/node state as an input. The handbook's canopy and
   stem descriptors provide observables, not a complete simulator.
   [USDA handbook, pp. 11–12](https://www.ars.usda.gov/ARSUSERFILES/80600500/HDM_DATA/HDMV3.PDF)

2. **Use repeated anatomical units.** The 2019 architecture study describes
   phytomers: connected internodes, nodes, leaves and axillary shoots. Leaf
   form changes with branch order and developmental state. Use it as evidence
   for connections and organ hierarchy, not as measured dimensions for the
   partner's hemp cultivar; its three study cultivars were different material.
   [Spitzer-Rimon et al., 2019](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.00350/full)

3. **Posture is actively developed.** Bastien et al. model slow curvature
   changes from gravity sensing and curvature sensing, extended to directional
   light. This supports separating developmental curvature from instantaneous
   deflection. Their 2015 quantitative comparison uses oat coleoptiles and a
   planar model, neglecting self-weight; it is not a calibrated 3D hemp contact
   solver. Transfer of its parameters would be unjustified.
   [Bastien et al., 2013](https://pubmed.ncbi.nlm.nih.gov/23236182/)
   [Bastien et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4332863/)

4. **Mechanical data must match tissue and test conditions.** A hemp stalk
   compression study tested air-dried sections from two varieties, not living
   petioles bending on a plant. Its compression results cannot supply live
   branch bending stiffness or leaf-contact damage thresholds. Keep those
   quantities unknown until supported by suitable measurements.
   [Khan et al., 2010](https://doi.org/10.1016/j.biosystemseng.2010.04.004)

## Proposed replacement: organ-scale development plus mechanics

This is an engineering proposal informed by the above evidence, not a claim
that these papers validate the combined model.

- **Topology:** each node stores parent, branch order, age/stage, local frame,
  leaf attachment and axillary shoot state. Branching is defined around its
  parent axis, independent of any review camera. Do not assume a universal
  golden angle or equal radial spacing without cultivar evidence.
- **Development:** organ initiation, internode elongation, leaf expansion and
  stem thickening use separate trajectories. Preserve mature basal geometry
  while younger regions develop. Initial clone structure and existing supports
  are explicit inputs. Sparse evidence means uncertain trajectories, not a
  fictitious day-accurate growth prediction.
- **Rest geometry:** store rest lengths and intrinsic curvature separately
  from the current deformed configuration. Slow posture adaptation updates
  rest geometry; it does not overwrite the outcome of a contact timestep.
- **Mechanics:** propose tapered beam/rod branches and petioles carrying leaf
  mass and inertia, coupled at nodes. Solve gravity and later contact relative
  to the stored rest geometry. Leaf orientation has its own local frame and
  compliant support. A proposed rod moment relation is M = B(κ − κ₀), with
  B the bending/torsional stiffness matrix. B, damping and tissue response
  remain calibration parameters; this relation alone is not a full solver.
- **Variation:** vary developmental state and coupled organ traits within a
  declared phenotype family. Avoid independently shuffling branch endpoints,
  leaflet sizes and stiffnesses to fill image-space gaps.

The required first artifact is a bare 3D skeleton at several development
stages, followed by leaves attached in local frames. Review matching front,
side and top views before adding surface detail. Do not require a circular
canopy; require a defensible architecture independent of the camera.

## Tests that distinguish the missing mechanisms

| Question | Inspectable experiment | What it establishes |
|---|---|---|
| Is this a volume or a photograph with depth? | Rotate a leaf-free skeleton; inspect branch azimuths and node attachments | Geometry/topology only |
| Is growth just global scaling? | Track the same node IDs through several stages | Development implementation, not biological calibration |
| Is droop encoded twice? | Compare rest shape, gravity-settled shape and unloaded shape | Separation of rest curvature from load deflection |
| Are branches appropriately compliant? | Apply and release a known load on one branch; record force, displacement and recovery | Simulation consistency first; material accuracy requires living-plant data |
| Does the full model agree with observations? | Compare several views of the same specimen, branch-order lengths and leaf orientations | Fit to those observations; hidden structure remains uncertain |

No new growth or contact solver was implemented in this research pass. No
heavy local inference or remote compute was started. The existing revision
and its rejection remain preserved so the same mistake is not repeated.
