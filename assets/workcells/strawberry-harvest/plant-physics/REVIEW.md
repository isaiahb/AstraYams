# Plant physics iteration

YAM arms, cameras, grippers and both held tools are unchanged. The original successful harvest remains the baseline; this candidate is a separate physical-interaction test, not a newly trained harvest.

## Revisions
1. Replaced five decorative berries and single-link target stalks with eight physical berries, common flexible branch parents and segmented stalks. Equivalent bending spring stiffness is EI/L with radius-dependent second moment of area. This is a reduced beam approximation, not a Cosserat or FEM implementation. Bodies have mass, damping and contacts with robot surfaces, tools, fixtures and other plant elements.
2. Reviewed the first render: stem attachments stretched visibly and stacked leaf ellipsoids looked implausible. Tightened attachment constraints and replaced leaves with contiguous mesh panels in trifoliate groups. 81 leaf panels are physical, though each panel remains rigid between hinges.
3. Replaced ellipsoidal berry collision proxies with convex collision hulls derived from the visible berry mesh. Increased stalk discretization from five to eight segments and tested a half timestep.

## Evidence
A force-limited dynamic spherical probe moves through the cluster, then withdraws. Robot motors hold their reset pose. Probe position is initialized once, clear of the fruit, after three seconds of settling; during the interaction the probe is force-driven, never teleported. An otherwise matching no-contact run provides a control. Neighbouring fruit can respond through their common branch and fruit–fruit contact; these tests do not isolate those mechanisms individually.

Compared with the no-contact control, maximum positional differences for the three right-cluster berries were 54.5, 54.1, 40.9 mm. Peak probe force was 0.329 N. Maximum probe penetration was 0.576 mm; maximum right-cluster attachment error was 2.241 mm. These are simulated measurements.

Halving the timestep from 1 ms to 0.5 ms changed peak force by 6.9% and contact impulse by 1.0%. Both runs remained finite and reported no MuJoCo warnings. The earlier five-to-eight-segment comparison changed peak force by roughly 29%, so mesh/segment convergence is not established.

## Remaining reality gaps
- Young's modulus, damping, stem density and fruit contact properties are uncalibrated assumptions. Fit them to measured load–deflection, release/oscillation and contact experiments before asserting transfer accuracy.
- Rigid fruit cannot predict local deformation or bruising. Mesh contacts use convex hulls; fine seeds and calyx details are not independently compliant.
- Leaf panels approximate bending; vein structure, tissue anisotropy and full sheet deformation are absent. Branch shapes and fruit distribution need measured botanical geometry.
- Harvest controller has not been commissioned on the moving plant. A cut/recoil test, unintended stem damage, and physical fracture calibration remain outstanding. Existing simplified work threshold is not validated by this probe test.
- Need longer settling and a wider sweep of stiffness, damping, integration resolution and held-out cluster shapes. Contact response is sensitive to initial conditions.

## Research informing model choice
- Gazebo Plants, Cosserat rod plant interactions: https://arxiv.org/abs/2402.02570
- Strawberry segmented-beam digital replicas, reported deflection errors 32–40%: https://doi.org/10.1007/978-3-032-15375-3_9
- Experimental strawberry stalk cutting/gripping forces: https://arxiv.org/abs/2207.12552
- MuJoCo elasticity plugin: https://github.com/google-deepmind/mujoco/blob/main/plugin/elasticity/README.md

Next: calibrate branch compliance and recovery against real plant video/force measurements, then test actual blade engagement and post-cut recoil. A visually convincing response alone is insufficient validation.
