# V6 — stacked SO-101 bases mounted directly to carriage plates

User correction: each robot base attaches directly to its carriage bracket; the second bracket is beneath the first. There is no added platform. V5 remains a preserved checkpoint.

## Implemented geometry

- Two vertical 245 × 115 × 6 mm carriage plates. These plate dimensions remain photo estimates from the earlier reconstruction.
- Upper and lower SO-101 bases sit directly against the outward plate faces. No shelf, bridge, L supports, gussets or base adapter plates are generated for this variant.
- Each plate has its own four guide blocks and a clamp onto the front belt run.
- Upper plate center starts at 0.840 m; lower starts at 0.540 m. The 300 mm separation is an editable layout choice, not a user measurement.
- Stock base +Z points outward (+world Y), base +X upward (+world Z), and base +Y to world +X. The base's original −2.4 mm mounting plane meets the 3 mm half-thickness plate face exactly.
- The stock base footprint is centered vertically using a −21.9 mm root offset. This centers the actual mesh sole inside the existing plate rather than centering the link origin arbitrarily.
- Upper arm uses the AEROBERRY cutter; lower retains the stock SO-101 jaw. Internal left/right names are retained for compatibility, meaning upper/lower respectively in this model.

Base fastening patterns and hardware are still unverified. The model represents a fixed mounting interface, not a manufactured bolt connection or a structural load assessment.

## Connected motion

The lower bracket is an independent passive slide, not a floating decoration or part of an invisible rigid shelf. Both front clamps attach to the same ideal belt strand:

- `q_lower = q_upper − 0.300 m`
- `q_rear = 1.680 m − q_upper`

Only the upper lift coordinate is actuated. Constraint forces transmit the lower bracket/arm loads to that same drive. The rear counterweight remains independent and travels oppositely. The additional lower carriage mass is a 0.60 kg prior; original upper carriage, counterweight and servo priors remain uncalibrated.

Upper travel is restricted to 0.50–1.48 m, giving lower travel 0.20–1.18 m. These limits prevent the new lower bracket from passing below the modeled lower safe travel region. They are geometric model limits, not verified hardware limit-switch settings.

## Verification

`tests/test_stacked_carriage.py` passed three checks against the generated model:

1. Actual stock-base mesh soles coincide with both vertical plate faces, lie within the plates and are parented directly to them.
2. There are two carriage plates and two belt clamps, with no platform/bridge/adapter bodies or CAD parts.
3. A finite-actuator motion test moves both front sliders together while the rear moves oppositely. The relative-travel residual stays below the test tolerance of 20 μm, with no simulator warnings. This checks the ideal solver constraint; it is not a physical belt-accuracy claim.

The review uses static 14°, 7° and 0° cutter poses and labels them as CAD articulation, not a learned harvest or cutting simulation. AEROBERRY tool contact and flexure dynamics remain unimplemented. V4's earlier recorded lift commissioning and YAM models are linked/preserved separately.

Build:

```
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/build_tower_lift.py --config configs/tower_lift_v6.json --out runs/tower-lift-v6
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/review_aeroberry_mount.py --root runs/tower-lift-v6 --template tools/templates/stacked-carriage-review.html
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python -m unittest discover -s tests -p test_stacked_carriage.py -v
```
