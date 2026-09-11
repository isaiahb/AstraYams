# V16: detachable net and useful container fingers

The user rejected V15's elaborate gate/roller assembly. This revision uses one
fixed net ring, an integrated keyed lug, replacement printed SO101 finger tips,
and one horseshoe parking seat. It preserves the earlier rigs and trials.
The design goal is to park the net deliberately, then use the fingers for an
empty clamshell or supported carrier. A filled pack remains carriage-supported.

The original SO101 STEP files are pinned at
`eecbe3e0a9ebb23e25ad7b2759b03884c6660903` under
`assets/end-effectors/dockable-net/reference`; hashes and Apache-2.0 license are
included. The source is https://github.com/TheRobotStudio/SO-ARM100.
Servo/pivot mounting geometry is retained; the printed tips are modified.
This is not a retrofit bolted onto unspecified finger holes.

## Design and fit

- 86 mm net outside diameter, 76 mm opening, 16 mm textile rest depth.
- Raised neck clears the real lower finger before descending to the ring.
- Opposed 14 x 10 x 3 mm keys seat in pockets with 0.15 mm nominal side clearance.
  This tolerance is a design assumption; printing, wear and hardware fit are unmeasured.
- The moving finger follows the actual SO101 rotary joint, not a parallel-jaw model.
- Open the jaw, lower the wrist 4 mm nominally to clear the lower key, and retreat.
- A horseshoe seat supports the rear-heavy tool while leaving its neck accessible.
- Extended carrier loop reaches past the shelf edge so a finger can get underneath.
  The original loop was above the deck and could not be pinched from below.
- One side bracket supports the parking seat; the full-arm location remains a fit concept.
- No moving net gate, release rollers, long shaft, extra motor or automatic tool changer.
  Wrist tipping is the proposed berry-unloading action; it is not yet validated.

36 sampled BRep interference checks report zero overlap, including rotary opening,
release/retreat, net/dock, mesh/dock, and the supported-carrier approach. Four
attempted 1 mm lateral shifts are blocked geometrically by the opposed keys.
These are sampled configurations, not a continuous swept-volume proof.

## Contact evidence

These are **scripted local fixtures, not PPO and not full-arm commissioning**.
The net is a free MuJoCo body: no weld or pose writes after initialization.
Contact proxies represent the flat socket walls, keys, neck and rim. They omit
fillets and the rest of the arm; this is not a surface-accurate contact model of
every STEP component. Net textile is not deformable in these interface tests.
The tool's 18.55 g mass and inertia use CAD plus an assumed 1100 kg/m³ density;
fastener mass and real printed/material properties remain to be measured.

Retention applies ±1 N along horizontal axes and +1 N vertically at the tool CoM,
with gravity and a 0.35 Nm jaw torque limit. Low friction μ=0.05 is a test choice.
At 0.25 / 0.125 ms timesteps, maximum key shift was 0.310 / 0.312 mm and tool
rotation 1.88 / 1.92 degrees. Both meet the inherited <1 mm / <2 degree nominal
retention targets. Peak contact force was 13.85 / 11.66 N; force is not claimed
converged. No simulator warnings occurred.

A frictionless normal-contact challenge also retained the tool: 0.321 mm shift,
2.25 degrees rotation. It exceeds the 2-degree precision target. Opening the jaw
in the no-dock control lets the tool detach. That test stops once key displacement
exceeds 50 mm; it does not apply continuing forces to an escaped tool.

The docking fixture drives X/Z translation with force-limited stage actuators and
opens the rotary jaw. In both timesteps the stage withdraws 68 mm, final net
contacts are with the dock only, and no finger contact remains. Maximum net-origin
movement is 1.01 / 1.03 mm. Commanded 4 mm descent becomes about 4.96 mm under
stage gravity/load; the replay records the actual position, not the command.

A zero-friction run with 3D friction-cone contacts was numerically invalid. The
frictionless case uses MuJoCo normal-only contact (condim=1), not a zero-coefficient
friction cone. Unstable or geometrically invalid intermediate trials are not
counted as successful evidence.

## What the tests changed

1. First neck layout intersected the lower finger by 469 mm³. Routed the neck
   forward past the fingertip before it slopes down.
2. First 0.3 mm-clearance keys retained the net but allowed nearly 4 degrees of
   angular play. Wider keys and 0.15 mm clearance reduce nominal play below 2 degrees.
3. Two narrow parking rails let the handle-heavy net tip backward and remain
   engaged with the lower pocket during withdrawal. The CAD-derived CoM is at
   x=-31.8 mm. A horseshoe seat extends the support region behind that CoM and
   lets the tool stay in its dock.
4. The old carrier handle was inaccessible underneath because of the deck.
   Extended it beyond the deck and checked the approach against both solids.

## Reproduce / inspect

Use the project CadQuery/MuJoCo Python environment:

```sh
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/build_dockable_net.py
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/check_dockable_net_physics.py
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/check_net_docking.py
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python -m unittest discover -s tests -p test_dockable_net.py
```

Review: `runs/tower-lift-v16/tool-study/index.html`, served from repo root.
The contact-test selector contains recorded docking, refined-timestep docking,
retention and opening-jaw control. Orbit, pan, zoom and scrub actual recorded poses.
Separate CAD views show tool capture, release, free fingers and carrier approach.
Individual STEP files and the assembled STEP are linked in the review.
The desktop product app is unchanged. Source hashes bind test evidence to the CAD.

## Next mechanical acceptance gates

Automatic re-acquisition needs entry chamfers/alignment tolerance tests; current
release success does not establish re-grasp success. Transfer the fixture poses to
the mounted SO101 and test full-arm reach and contact with neighboring hardware.
Commission carrier grip/translation and empty clamshell rim contact. Characterize
lid closing force and container flex before claiming automatic closing. Test
wrist tipping with the deformable net and real plant/berry simulation, including
impact/damage uncertainty. No learned harvest performance or hardware readiness
is claimed from this redesign.
