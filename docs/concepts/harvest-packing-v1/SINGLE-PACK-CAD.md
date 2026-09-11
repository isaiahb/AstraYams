# Concept A: one supported clamshell

The user selected one-container development after rejecting arm transport of a
filled clamshell. V8 adds a side shelf to the lower carriage, a removable carrier,
an approximate clear clamshell, upright lid retention, and a small catching net.
The accepted V7 direct robot mounts and 200 mm vertical separation are preserved.
No earlier YAM or tower-lift scene is replaced.

## Load path and operation

The clamshell rests on a liner and a carrier floor. The carrier rests on the shelf
deck. Two side webs join the deck to a plate using four existing photo-model
carriage hole positions. Thus fruit and container weight is carried by the lift,
not the robot wrist. The net is the lower arm's only added tool.

The proposed sequence is catch a berry, bring the net into the supported open
container, and release it gently. This revision only checks discrete geometric
poses; it does not yet implement berry release. In particular, a fixed net has no
opening bottom: tipping, rolling release or a release mechanism must be designed
and tested before claiming a complete packing cycle.

The carrier has side guides, a rear stop and an engagement handle at its open
transfer end. A front latch envelope indicates where retention is needed. A
future bottom station could pull the carrier onto a supported surface. It is not
built or animated here. The latch, lid clip and net dock are preliminary geometry,
not commissioned mechanisms. Manual container exchange is sufficient for this
first one-container concept.

## Dimensions and evidence

All generated STEP parts use millimetres. These are design parameters, not new
measurements of the user's rig.

| Item | Current CAD choice |
|---|---|
| Shelf deck | 163 × 246 × 4 mm |
| Removable carrier | 139 × 208 × 11 mm, plus front handle |
| Carrier side clearance | 1 mm each side |
| Container reference | Approximately 123 × 186 × 81.8 mm closed envelope |
| Container CAD | Tapered 76 mm body, thin vented walls, separate approximate lid |
| Lid angle | 95° from closed, along outboard long edge |
| Net | 86 mm outside diameter, 76 mm clear opening, shallow textile rest shape |
| Net handle | 44 × 16 × 17.8 mm, raised 50 mm above net rim datum |
| Added mass | Approximately 1.27 kg before fruit, from assumed material densities |

Container envelope reference:
[Pactiv Evergreen YYY9772](https://pactivevergreen.com/products/yyy9772).
The generated container is an envelope interpretation, not supplier CAD. Its
actual hinge, vents, ribbing, wall stiffness and fit require the chosen sample.
The thin reference container and the rigid carrier are separate parts.

The initial flat net handle crossed the container wall; raising it lets the net
bowl enter the cavity while the handle remains above the rim. The complete stock
jaw also crossed the wall in the initial deep-access pose. The final access pose
keeps the net rim above the container lip. The handle width and
jaw angle were adjusted using sections through the upstream SO-101 meshes.
The net is still attached rigidly for CAD review, not retained by simulated jaw
friction. Textile strands extend into the retaining ring, but their contact and
clamping preload are not simulated.

## Static review evidence

The review offers three discrete poses: catch approach, container access, and
the preserved V7 parked joint configuration. Offline numerical IK chooses these
poses within the original SO-101 joint limits. No PPO, trained policy or motion
controller is used in this review.

- Net position error: about 0.02 mm at catch approach and 0.19 mm at container
  access. The rim tilts about 0.7° and 7.9° respectively. The latter is an access
  pose, not proof of stable berry retention or release.
- Exact STEP checks find no rigid net/fixture intersection or carrier/guide
  obstruction in the three poses.
- Separate explicit distance checks include the visible cutter and net. The
  catch pose has only about 7 mm between the two arm/tool convex envelopes.
- The fixture has only 3.5 mm nominal clearance to the left frame member's inner
  plane. This is too small to treat as established hardware clearance given the
  estimated frame dimensions and unmodeled deflection.
- The container-access pose approaches the wrist-flex limit, with approximately
  0.03 rad margin. Static reach does not establish a collision-free approach or
  a feasible tipping/release motion.
- The upper cutter pose constrains tip position only. Its blade direction and
  target-stem engagement are not commissioned by this shelf study.

New fixture/tool geometry has explicit mass estimates but its MuJoCo collision
contacts are disabled during this CAD review. Hollow CAD intersections are
checked separately, rather than replacing the clamshell cavity with a filled
convex hull. There is no claim of contact dynamics, net compliance, bruise safety,
lift load capacity or structural validation.

## Reproduce and inspect

Requires the preserved local V7 build, upstream SO-101 assets, supplied AEROBERRY
CAD, and the existing CAD/MuJoCo environment. Generated assets remain under
ignored `runs/`; source builders and this evidence description are versioned.

```sh
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/build_single_pack.py
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/review_single_pack.py
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/audit_single_pack.py
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python -m unittest discover -s tests -p test_single_pack.py
```

Review: `http://127.0.0.1:8793/runs/tower-lift-v8/index.html`.
It includes fixture/net cameras, three static arm poses, exploded fixture view,
individual STEP parts, complete support STEP, and machine-readable checks.

## Next engineering gate

First resolve the berry release method and demonstrate a continuous collision-
checked path between catch and release with adequate wrist margin. Then validate
the net/jaw contact and flexible textile, shelf/latch hardware, and lift load.
Acquire the exact clamshell sample and frame measurements before tightening fit
tolerances or adding automatic full-container exchange. Keep the one-container
load path throughout those tests.
