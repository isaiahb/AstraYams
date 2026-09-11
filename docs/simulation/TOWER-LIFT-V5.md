# SO-101 / AEROBERRY mounting study — V5

This checkpoint responds to the user's supplied AEROBERRY design package and request to use SO-101 arms. V4's counterweighted rig and the YAM scenes remain intact. V5 is **CAD integration and a provisional carriage layout**, not a corrected, validated harvesting simulator.

## What was imported

The selected starting candidate is `01_SO101_v0.4`, the documented utility-blade prototype. The miniaturized scalpel v0.2 in the supplied package is a separate layout study with unresolved spring and blade details. No choice response had arrived while this candidate was prepared.

The copied source FCStd, STEP parts, assembly STEP, notices, verification reports and preview are retained unchanged under `assets/end-effectors/aeroberry-so101-v04/`. `source.json` hashes every copied file. These are user-supplied CAD, not newly designed AstraFactory geometry.

`tools/aeroberry_tool.py` extracts ten saved BREP solids. A FreeCAD BREP already contains its saved Placement: remove that pose exactly once to obtain the closed CAD coordinates. Keep the fixed jaw/pad rigid to the wrist; attach carrier, brace, flexure, cover, blade, moving pad and screws to the hinge. The original servo remains, and the original fixed jaw housing and moving finger are removed.

Mapping from package millimetres to the upstream SO-101 gripper link:

- CAD pivot: (0, 9, 0) mm.
- Upstream servo pivot: (0.0202, 0.0188, −0.0234) m.
- Axis mapping: CAD X → SO −Z, CAD Y → SO −X, CAD Z → SO +Y.
- Translation: (29.2, 18.8, −23.4) mm.
- Positive opening is opposite the stock finger's sign convention, with range 0–14°.

This is a datum-based fit interpretation. It does not validate horn screws, splines or servo clearance. The package documents a source servo-envelope overlap of approximately 38 mm³; its reference envelope also differs slightly from the upstream robot servo mesh. Do not claim exact measured hardware compatibility.

## Carriage candidate

The former generic 560 × 190 mm shelf is replaced for this SO-101 candidate with a 360 × 130 × 6 mm deck, 240 mm base spacing, two small L brackets and triangular support webs. The reconstructed faceplate, guide shoes and independent rear counterweight are retained.

The SO-101 base's source mesh bottom is 2.4 mm below its link origin. V5 compensates this offset; both feet meet the deck top at 0.907 m in the initial pose. The 111 mm wide stock base footprints fit within the proposed deck. Mounting slots are provisional, **not** an asserted stock SO-101 bolt pattern. Base clamp/fastener hardware remains unresolved. Horizontal versus vertical base mounting was asked in chat; this is a reversible horizontal-layout candidate pending that preference.

The rig dimensions remain estimates inherited from V4. New bracket sizes are design choices, not dimensions measured from the user's photographs. No plate stiffness, tipping, fastener strength or bearing-load validation has been performed.

## Scope and limitations

- Left arm: user's AEROBERRY v0.4 grip-cut tool.
- Right arm: stock SO-101 gripper; there is no compatible catcher design in this package. Do not silently reinterpret the Maker Arm tool as an SO-101 catcher.
- Tool geometry is visible-only in MuJoCo. Tool collisions, stem cutting and compliant gripping are not implemented here. `training_ready: false` in import/build/replay metadata.
- The flexure is the source's prescribed rest CAD shape, not a force or deformation law.
- Tool mass/inertia uses actual mesh geometry, nominal 1100 kg/m³ polymer and 7800 kg/m³ steel, plus a 55 g servo prior. These are not weighed hardware values.
- Browser poses are 14°, 7°, and 0° static forward-kinematic CAD states. They are explicitly labelled as such, never as learned or physics rollouts.
- V4's separately linked lift replay remains the evidence for the previously commissioned opposed counterweight motion. No V5 harvest result is claimed.

## Checks

Four tests in `tests/test_aeroberry_mount.py` verify source solid volume preservation, pivot mapping, independent fixed/moving jaw behavior over 14°, and honest readiness metadata. The generated model retains six actuators per SO-101 plus one lift drive. Original jaw geometry is replaced, not stacked under the retrofit. Browser review includes cutter, underside wrist interface, carriage, bracket, side and complete-workcell cameras.

## Next engineering gate

Confirm which supplied tool and carriage arrangement correspond to the intended hardware. Then specify and model actual base fastening, check the wrist envelope against a measured assembly, derive non-sealing collision geometry and a calibrated flexure/pad force law, and perform independent grasp/cut/retention tests. Only after those checks should this tool enter harvesting PPO training.
