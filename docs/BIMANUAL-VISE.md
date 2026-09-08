# Bimanual manual-vise design checkpoint

One YAM holds the stock; the second turns a manual lead screw. This is an
untrained design study, separate from the powered-fixture PPO checkpoint.

The parametric CAD has a 105 mm riser, 2 mm/revolution screw and two opposing
35 mm crank grips. Each grip has a passive sleeve. Six upper half-turn closing
strokes would close a 20 mm loading gap to the nominal 14 mm stock width.
The tightener releases and transfers to the opposite grip after each stroke.
This robot-adapted mechanism is a proposal, not a validated commercial vise.

Seven independent IK samples across the upper semicircle reached their targets.
The holder also reached the stock target. No greater-than-0.5 mm inter-arm
penetration was detected in those sampled configurations. This does not verify
continuous paths, self-collision, fixture clearance, gripper contact, torque,
retention or real hardware. The design scene has an ideal screw/jaw constraint
and no jaw or screw actuator. No manual-tightening policy has been trained.

Reproduce from the repository root:

```sh
PYTHONPATH=src:tools python tools/check_bimanual_vise_layout.py
python tools/export_bimanual_design.py
```

The static preview uses the actual YAM mesh assets and generated CAD. It must
remain labelled `untrained_design`, never recorded physics or learned success.
`assets/workcells/concepts/bimanual-vise-concept.png` is an AI-generated visual
direction reference; its mechanism and poses are not simulation evidence.

Next validation: check continuous approach/regrasp clearance, establish a
frictional handle grasp, drive the screw through arm contact, measure stock
retention, then train the bounded grip/turn/regrasp skills against those checks.
