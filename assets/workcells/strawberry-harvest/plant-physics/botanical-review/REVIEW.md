# Strawberry morphology and shape retention revision

Status: contact-only candidate. Original harvest baseline preserved. This revision does not implement fruit detachment; it must not be described as a working harvest environment.

## Why the previous version was wrong
Long, straight stalks radiated from a high junction, foliage lay near the soil, and oscillation persisted. Merely increasing a damping number would not fix the anatomy or the natural resting geometry.

## Botanical changes
Crown-rooted upright petioles carry broad trifoliate foliage. Curved trusses emerge separately, with a primary terminal fruit and a secondary fork carrying shorter pedicels. One smaller green fruit provides a different development stage, with mass and collision geometry scaled consistently. The resting centerlines are curved, with tapered radii; they no longer start as a straight hanging frame. Botanical layout follows the crown/petiole/compound-cyme distinction in NC State's production guide, but remains a procedural approximation, not a measured cultivar model. Canopy shape and variation still need improvement.

Reference: https://content.ces.ncsu.edu/southern-regional-strawberry-plasticulture-production-guide (Strawberry biology / Morphology)
Reference: https://strawberrycenterblog.com/2025/12/15/strawberry-anatomy-part-3-leaves-and-stems/

## Mechanical changes
Natural shape is encoded by curved rest geometry. Equivalent rotational stiffness derives from EI/L. The final candidate uses spherical joints with approximate isotropic rotational stiffness, stronger restoring stiffness and damping than the rejected version. Tissue values remain uncalibrated. This is not a validated Cosserat/FEM model.

Internal collisions between connected tissue at crowns/forks/fruit attachments are excluded; external robot, tool, berry and plant contacts remain. Free fruit bodies plus stiff attachment constraints proved problematic in the stiffer trials. For this diagnostic, berries are directly attached to the flexible stalk hierarchy, preserving their mass and inertia without attachment-constraint stretch. This removes detachment capability from this candidate; explicit topology change/contact restoration is required before cutting tests. No robot, gripper, tool or camera geometry changed.

## Validation
A matching untouched control tests whether the plant settles under gravity. The contact test drives a force-limited dynamic probe against a berry and withdraws. There are five seconds of settling before the contact test. The video starts after that settling period; the interactive replay and raw trace include it. No fruit is teleported or animated by keyframes.

Both final trials ran for 14 simulated seconds at a 0.5 ms timestep without warnings. The largest control span during the one-second window before contact was 0.0246 mm. Peak probe contact force was 0.195 N; maximum probe penetration was 0.434 mm. Maximum final difference from the untouched control was 0.0146 mm. These are simulator checks, not measurements of a real strawberry plant.

## Rejected trials retained
The initial botanical build and revisions v2, v5, v6 and v7 reported numerical instability and were rejected. Version v4 was finite but failed the quiet-rest intent, with roughly 11 mm motion on one coordinate of the immature fruit in the final second. The final v8 changes the attachment representation rather than hiding that failure with scripted trajectories.

## What is still unproven
Real-plant load–deflection curves, recovery time, damping, turgor effects, fruit deformation/bruising and cutting forces have not been calibrated. The quiet-rest gate is an engineering sanity check, not a biological tolerance. Stable contact response does not establish sim-to-real accuracy. Training throughput and solver/discretization convergence must be assessed after the final attachment/cutting model is chosen.
