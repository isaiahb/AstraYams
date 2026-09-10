# Recovery study v1 — baseline rejected

The six contact trials and their exact-command, no-contact controls share the
same initial loaded state. Contact forces, penetration, force balance and the
half-timestep test meet the predeclared numerical limits, but **all six controls
fail the 0.10 mm drift limit**: fruit-origin drift is 0.106–0.228 mm. The original
initial state was still slowly settling. This revision is preserved as a failed
baseline, not accepted material evidence. The limit has not been relaxed.

The relaxing hypothesis's long hold shows a roughly 14% force decline, versus
less than 0.3% for the fixed-spring hypotheses. This is a preliminary simulated
prediction, not a measured strawberry response. It must be repeated from a
better-equilibrated shared starting state before acceptance.

See [protocol](protocol.json), [complete comparisons](comparison.json),
[research and assumptions](research.md), [replay](index.html), and
[force/recovery curves](recovery-comparison.png). Case directories contain
numerical reports; large trajectory files and recordings are local artifacts.

The three hypotheses are original elastic springs plus damping, those springs
plus an assumed passive Maxwell component, and a different fixed rest curvature
paired with twice the stiffness. The third model does not simulate growth or
plastic deformation. All trials use actual contact-driven motion of an intact
cluster. Recorded replays reuse the same visible geometry.

The next revision will continue gravity settling with unchanged masses,
stiffness, damping and constraints, then repeat every comparison from that
shared state. No velocity reset or preferred plant pose will be imposed.
