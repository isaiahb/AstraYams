# Product-informed tower correction

The user rejected V1's tower dimensions and plastic holder form, supplied a
product dimension diagram, and linked ASIN B0FSCQMMT7. The frame dimensions are
also disputed; updated photos are pending. V1 remains at its original review URL.

## Evidence and uncertainty

- [Amazon listing](https://www.amazon.com/dp/B0FSCQMMT7?th=1), reviewed 2026-09-10:
  12 tiers, 60 sites. This implies five holders per tier, not V1's three.
- Supplied dimension image: 184 cm overall, 40 cm × 40 cm reservoir footprint,
  and a 20 cm dimension across the reservoir body. Whether that last dimension
  includes the wheels is ambiguous. We currently model a 20 cm body plus 4 cm
  caster clearance and a 1 cm lid. These are **not measured hardware dimensions**.
- Overall stack constrains the tier pitch: (1840 − 250 − 40) / 12 = 129.167 mm.
  The 250 mm reservoir/lid/caster stack and 40 mm top collar are assumptions.
- Photos show flared pockets joined to the center, circular basket rims and
  staggered tiers. V2 uses five hollow flares merged into one shell per tier,
  with five separate slotted baskets. Pocket radius, 24° axis angle, wall
  thickness, collar fit and net-rib details remain estimates.
- The linked listing is black/grey. The user's physical tower photographs are
  white. Color remains white; we do not assert their variants have identical
  details merely because their silhouettes are similar.
- Rear X frame, arm spacing and lift properties remain provisional, inherited
  from V1. We have not guessed replacement frame measurements.

Source image is kept locally at
`runs/tower-lift-v2/references/product-dimensions.png`, unmodified and uncommitted.
Marketing illustrations and listing text are reference material, not scientific
plant-growth or safety evidence.

## Implementation

`tools/tower_product.py` generates real CadQuery solids for a connected tier,
net basket, hollow tapered square reservoir, removable lid, caster envelopes and
top collar. The existing support builder selects this geometry using
`configs/tower_lift_v2.json`. V1's config still selects its original shape.

The tier is a reconstruction, not manufacturer CAD or a manufacturing-ready copy.
Exact fasteners, retaining tabs, irrigation distributor, pump/tubing and roots
are outside this correction. Water flow and wheel/structural dynamics are not
simulated; reservoir and frame are anchored.

Collision geometry keeps holder mouths open using narrow convex wall/shoulder
sectors and discrete basket ribs. It is a contact approximation. Hub/pocket
interior union seams are not exact Boolean collision solids; reservoir contact
uses a conservative external box. Neither should be used to claim calibrated
contact accuracy for insertion inside the plumbing. The relevant access test
checks entry through each of 60 basket mouths and physical rim contact.

One V4 plant is seated at a basket mouth and retains its original articulated
physics parameters. No new plant-growth realism, damage safety or domain
randomization is established here. Both SO-101 and YAM layouts remain available.
No harvesting policy is trained or transferred in this revision.

## Review and acceptance evidence

The review puts the supplied dimension image beside the model. Tower-only and
holder-detail views isolate the corrected geometry; whole-cell views retain the
provisional frame and two alternative robot embodiments. STEP files are linked.

Automated checks validate single-solid CAD, the actual 400 mm lid envelope, the
constrained total height and 60 plant sites. Contact probes must pass through all
60 mouth centers without hitting a filled hull and must contact their rims.
The lift recording separately reports finite-force dynamics and all contacts;
new plant/robot contacts must be disclosed, not counted as a collision-free pass.

Next uncertainty to resolve: compare the individual holder close-up and assembled
stack with the user's updated photos, then update the frame dimensions and
holder/pot seating measurements. These determine reach, cut/catch access and
contact placement before new policies are trained.

## Reproduce

```sh
PYTHONPATH=src python tools/build_tower_lift.py --config configs/tower_lift_v2.json --out runs/tower-lift-v2
PYTHONPATH=src python tools/review_tower_lift.py --root runs/tower-lift-v2 --template tools/templates/tower-product-review.html
PYTHONPATH=src python -m unittest discover -s tests -p 'test_tower_product.py' -v
```

## Recorded outcome

Two product checks passed (including transformed scene extent 0.400 × 0.400 ×
1.840 m and 180 contact-probe cases across all 60 mouths). Three V1 regression
checks also passed. Both 5.5-second lift clips completed without simulator
warnings. SO-101 registered 0.01453 N peak robot-associated contact and 0.3203 mm
peak overlap; this is disclosed, not called safe or collision-free. YAM registered
no robot contact during that short parked-arm lift test. See
`tower-lift-v2-evidence.json` for source hashes and full results.

Visual inspection covered the product/model comparison, isolated holder, complete
cell and both robot variants. Holder-only normals use crease-aware smoothing;
applying it to every high-detail robot mesh was too slow and was rejected. The
remaining cel-shading edges are a display limitation, not extra CAD surface ribs.
