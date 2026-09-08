# YAM gripper contact geometry audit

This audit uses the official YAM URDF and STL geometry pinned in `assets/robots/yam/SOURCE.json`. It concerns actual articulated finger contacts with a free peg, not a rigid attachment or acquired-grasp claim based on a weld.

## Joint motion and jaw spacing

`joint7` moves `tip_left` along local +Y; `joint8` moves `tip_right` along local -Y. Their common travel is [-0.04695,0]m. Equality `q8=q7` produces symmetric opening. **Negative motion opens; positive motion closes.** The names left/right do not imply which side of gripper Y their distal contact faces occupy: at q=0 the left distal face is negative Y and right is positive Y.

Gripper-frame joint offsets at zero:

- tip_left: `[-0.0239931, +0.0445119, -0.0566829]`m.
- tip_right: `[+0.0239931, -0.0445119, -0.0566829]`m.

The original STL coordinates are transformed by each URDF visual origin, then the joint offset. Both fingers span approximately Z[-0.1468425,-0.0529999] in the gripper frame at zero. Distal inner faces are near Y=0; the large overall finger bounding boxes are not a valid measure of jaw opening because the proximal structure extends to both sides.

Mesh plane sections give the following unloaded gap, before adding joint displacement:

| Gripper local Z | Left inner Y at q=0 | Right inner Y at q=0 | Gap |
|---|---:|---:|---:|
| -0.140m | -0.00003108m | +0.00003110m | 0.0622mm |
| -0.135m | -0.00003108m | +0.00003110m | 0.0622mm |
| -0.130m | -0.00006036m | +0.00006038m | 0.1207mm |
| -0.125m | -0.00035435m | +0.00035437m | 0.7087mm |
| -0.120m | -0.00065690m | +0.00065691m | 1.3138mm |

For symmetric q, gap(z,q)=gap(z,0)-2q. At Z=-0.130, a centered 14mm width in Y contacts near q=-0.00694; a 24mm opening is near q=-0.01194. Exact onset varies with the contact patch and convex approximation. Closure must be force-controlled against the free peg; a position setpoint is not proof of normal contact.

## Peg pose and access

A sensible grip center is gripper-frame `[0,0,-0.130]`m, with peg width18mm along X,14mm along Y and its long axis along local Z. This places its narrower dimension between the fingers. At Z=-0.140 the finger width already spans ±9.66mm, enough for the 18mm peg cross-section.

A 38mm peg alone leaves little protrusion beyond the 94mm-long finger structure for deep socket insertion. An explicitly modeled extended handle can provide access: for a65mm-long object, distal tip Z=-0.184 and proximal endZ=-0.119 put the grip near its proximal end and leave37.16mm beyond the distal finger extent. This yields roughly8mm finger-to-socket-top separation at29mm insertion depth, before rotation/contact tolerances. If the actual handle is70mm overall, keep the chosen distal tip and update the upper end accordingly. The added handle is a new CAD design choice, not an original YAM part.

Keep the peg freejoint throughout execution, without peg weld/equality/kinematic repositioning. Finger coupling equality is appropriate because it couples the jaws, not the object. Test opening after lifting: the peg must fall or move independently. Test a friction-free ablation: holding behavior should degrade rather than remain attached. Distinguish object support on a table/fixture from genuine bilateral jaw support.

## Collision representation

Each source finger STL splits into three connected shells. The largest shell is watertight and concave (~30k faces). The two tiny negative-volume shells are screw-hole interiors; they are not valid standalone convex collision solids. A convex hull of the entire finger can fill concavities and invent contacts. Raw `split()` does not solve this.

The geometry task generates real-mesh CoACD convex pieces in `assets/robots/yam/collision/`, retaining original STL coordinates. Use `DECOMPOSITION.json` for piece names, hashes, volumes and provenance. Each piece must be its own MuJoCo mesh+geom under the corresponding tip body, using the original visual mesh transform:

- tip_left visual origin `[0.00999321,-0.0914614,0.129783]`.
- tip_right visual origin `[-0.0379932,-0.00133753,0.129783]`.

Set original finger meshes visual-only (`contype=0`, `conaffinity=0`), and enable contact on convex pieces. Preserve URDF body inertias; use density0 on additional geoms to avoid counting mass repeatedly. Pieces are an approximation of real mesh shape, so inspect local jaw gap and grasp contact before relying on them. A successful file conversion alone is not a validated grasp.

## Force expectation

For the current proposed0.04kg peg, gravity is0.3924N. Two symmetric jaw contacts with friction coefficientμ require normal force per jaw at least `N >= mg/(2μ)` for a quasi-static vertical hold:0.164N atμ1.2,0.245N atμ0.8,0.392N atμ0.5. These are ideal lower bounds; include acceleration, offsets, torque and slip margin. Friction1.2 and any motor cap are provisional simulator parameters, not calibrated hardware ratings.

With one motor driving a symmetric equality-coupled jaw coordinate, the actuator's generalized force is shared through the constraint. Do not assume the motor command equals each jaw's measured normal force. In the ideal symmetric static case, a closure forceF maps approximately toF/2 normal force per finger. Log actual MuJoCo contact normal/tangential forces, object slip and jaw separation. A30N generalized-force cap is much larger than the ideal gravitational requirement and can cause contact impulses if approached with excessive speed.

## Completed decomposition check

Generated24 convex pieces per finger (48 total), all convex. CoACD reached the hull-count limit before the requested global concavity threshold; summed hull volumes exceed source outer-shell volume by7.58% left and4.23% right. Distal inner jaw faces at five Z sections from -0.140 to -0.120m matched original surfaces within0.7 micrometre over the central±9mm band. This supports using these real-geometry pieces for the grasp contact region while retaining the caveat about proximal concavities. Dynamic grasp and release remain integration checks. Exact parameters and file hashes are in `assets/robots/yam/collision/DECOMPOSITION.json`.
