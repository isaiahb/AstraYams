# V7 — reversed SO-101 mounting and reduced bracket spacing

User correction: the SO-101 arms look upside down, and the two direct-mounted
brackets should be vertically closer. V6 remains an unchanged review checkpoint.

## Change

Both complete robot bases rotate 180 degrees about the outward plate normal.
Their mounting soles still sit directly on the front plate faces. Base-local +X
now points downward; +Z still points outward. The base-centering offset reverses
from −21.9 to +21.9 mm so the actual mounting footprint stays centered within the
plate. Joint zeroes and parked joint angles are unchanged.

Bracket centers are 200 mm apart, reduced from 300 mm. This is an adjustable
layout choice, not a hardware measurement. The 115 mm tall plates have an 85 mm
vertical edge gap. The upper plate starts at 840 mm and the lower at 640 mm.
Both front brackets travel together; the rear weight travels oppositely. With
the existing 0.50–1.48 m upper stroke, the lower stroke is 0.30–1.28 m.

There is no platform. The upper arm retains the supplied AEROBERRY cutter and
the lower retains its stock jaw. Tool/contact commissioning is still separate.

## Evidence and scope

Four artifact checks pass in `tests/test_stacked_carriage.py`:

- Actual base mesh soles touch and fit within the plate faces.
- The complete bases have the corrected orientation and the plate spacing is
  200 mm. Explicit geometry-distance queries include the visual-only cutter
  solids, rather than relying only on enabled collision contacts. At the
  displayed 14-degree opening, the minimum inter-arm convex-envelope clearance
  is 39.14 mm (upper utility carrier to lower arm link). All three displayed
  14/7/0-degree jaw poses exceed 30 mm. No enabled robot contact penetrates
  more than 0.1 mm in those static poses.
- No platform, bridge or adapter parts are generated.
- Finite actuator motion preserves equal front travel and opposite rear
  travel, with no simulator warnings and ideal-constraint residual below the
  20 micrometre test tolerance. This is not a hardware accuracy claim.

The clearance result applies to the shown parked arm poses, not the full joint
workspace or a learned harvest. Visual-only AEROBERRY solids are queried for
geometric separation but do not yet exert contact forces. Mounting fasteners,
load capacity, cable routing and safe motion envelopes remain unverified.

## Reproduce

```sh
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/build_tower_lift.py --config configs/tower_lift_v7.json --out runs/tower-lift-v7
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/review_aeroberry_mount.py --root runs/tower-lift-v7 --template tools/templates/compact-carriage-review.html
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python -m unittest discover -s tests -p test_stacked_carriage.py -v
TOWER_LIFT_RUN=tower-lift-v6 PYTHONPATH=src /tmp/clonebench-cad-env/bin/python -m unittest discover -s tests -p test_stacked_carriage.py -v
```
