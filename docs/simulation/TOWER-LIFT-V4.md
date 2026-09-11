# Counterweighted lift correction

The user clarified that the round rear weight and the front bracket move in
opposite directions. V3 incorrectly rigidly joined them with a shaft. V4 removes
that connection and gives the counterweight an independent rear carrier. The
prior V3 checkpoint and reference photos are preserved.

## Confirmed and inferred

**Confirmed by the user:** the rear component is a counterweight; when the front
bracket rises the weight descends, and vice versa.

**Still inferred:** a 1:1 closed, taut belt transmission, 20 mm pitch radius,
2.8 kg rear assembly mass, rear guide shoes and the weight's attachment to its
own carrier. Actual weight, ratio, pulley size, bearing design, friction, belt
preload, compliance, slip and motor capacity are not measured. The frame scale
remains the editable photo estimate from V3.

The default rig model and both proposed dual-arm models retain the rear weight.
The robot bridge belongs to the front carrier; adding robot arms does not remove
the counterweight or automatically rebalance its mass.

## Mechanical and simulation changes

- Front and rear carriers are independent world-root bodies, each with a
  vertical slide joint. The rear assembly has explicit mass and inertia and no
  actuator. Its collision envelopes interact with the front carrier, frame,
  plant and robots; its carrier does not rigidly follow the front body.
- An ideal belt constraint holds `front_height + rear_height = 1.68 m`, the sum
  of the two configured initial heights. A force-limited drive acts on the
  front slider; constraint forces transmit the rear assembly's weight/inertia.
  This is a reduced transmission model, not a second mirrored motor command.
- Top and bottom pulleys have hinge joints and rotational inertia. Their angles
  follow the belt travel through additional solver constraints. Visible marks
  rotate from recorded joint states. Belt spans and wraps show the inferred
  routing, while tooth engagement and elastic belt deformation are unmodeled.
- The front guide shoe is open at its rear. Separate rear shoes occupy the back
  side of the extrusion and can pass the front shoes. The guide mechanism is
  still an ideal slide constraint; supplier bearing details are not established.
- The counterweight shaft now terminates at its own rear plate. There is no
  cross-shaft tying its height to the front carriage.
- The stroke is bounded to 0.20–1.48 m for both carriers. Using V3's 1.63 m front
  maximum with this initial height sum would put the counterweight too low.

MuJoCo's joint equality supports a polynomial relationship between scalar joint
coordinates and transfers constraint forces. The linear coefficient is -1 for
opposed sliders; pulley coefficients use the reciprocal pitch radius. See the
[MuJoCo joint equality reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#equality-joint).
The solver permits small residuals, which are measured rather than hidden.

## Discriminating validation

`tests/test_lift_counterweight.py` checks:

1. The rear assembly has a separate joint and no actuator in rig, SO-101 and
   YAM configurations. The former shared shaft is absent.
2. The actual front and rear guide CAD solids do not intersect when passing.
3. With the motor disabled, a lighter rear weight lets the front descend, while
   a heavier rear weight lifts the front. This distinguishes counterbalance
   physics from two independently animated parts.
4. Equal masses balance with the motor off. Disabling the belt constraint makes
   both sliders fall independently despite an upward actuator setpoint.
5. Balancing the rear mass reduces the holding force required from the motor.
6. All recorded lifts have opposite front/rear travel, finite bounded actuator
   forces, small belt-constraint residuals and no counterweight contact.

A reduced diagnostic fixture omits the unrelated plant for mass/load tests but
retains the rig's geometry, masses, timestep, constraints and actuators. Full
commissioning uses the tower, plant and chosen robot configuration.

The displayed motion is a recorded scripted lift test, not learned harvesting.
State observations now include rear height and velocity. Replay overlays report
both displacements; the browser never derives or overwrites the rear pose from
the front pose. Detailed results and hashes are in `tower-lift-v4-evidence.json`.

## Remaining limitations

No calibration of load rating, belt slack/slip, electrical or thermal drive
behavior, emergency braking, guide friction or frame tipping is established.
The ideal bilateral belt relation assumes a taut, engaged drive. Hidden guide
and mounting geometry are explicit hypotheses awaiting hardware inspection.
The light SO-101/leaf brush from the layout remains recorded; successful lift
commissioning does not establish collision-free harvesting or fruit safety.

## Reproduce

```sh
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/build_tower_lift.py --config configs/tower_lift_v4.json --out runs/tower-lift-v4
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python tools/review_tower_lift.py --root runs/tower-lift-v4 --template tools/templates/counterweight-review.html
PYTHONPATH=src /tmp/clonebench-cad-env/bin/python -m unittest discover -s tests -p 'test_lift_counterweight.py' -v
```

Review: `http://127.0.0.1:8793/runs/tower-lift-v4/index.html`.
