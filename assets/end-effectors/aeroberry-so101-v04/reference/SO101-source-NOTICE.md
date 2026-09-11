# Upstream CAD attribution

The retained wrist/servo cradle in P01 is derived from TheRobotStudio's SO-101
assembly in the SO-ARM100 repository, distributed under Apache License 2.0.
The original license is included as `SO101-Apache-2.0-LICENSE.txt`.

Source: https://github.com/TheRobotStudio/SO-ARM100/blob/main/STEP/SO101/SO101%20Assembly.step

Downloaded 2026-09-02. STEP header: SO101 Assembly v4, 2025-04-15.
Original complete STEP SHA-256:
`f754be35708382b05ce65768ae33c612f91dca11ad19d14807dc637eb944ba3d`.

Changes: extracted fixed cradle; transformed into a gripper-drive coordinate
frame; cropped away the original working finger; added a bridge, fresh fixed
jaw, blade receiver, bench attachment holes, an integral V guide and a printed stop post. v0.3 replaces the separate guide fasteners used in v0.2. The complete
aligned reference part is retained in `SO101-fixed-cradle-aligned.brep`.
The final part is a modified derivative, not the original manufacturer's file.

The transformed, otherwise unmodified servo reference is included in `Servo-aligned.brep` for clearance checks.

The servo family model was used to read the nominal 14 mm horn pitch circle
and 37.25 mm front/rear horn separation. No 25-tooth spline is printed.
The other printable shapes were constructed for this study. SROI was studied
for the harvesting concept; no SROI part geometry is included in these STLs.
