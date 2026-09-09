# Crown support candidate v7

Separate manual simulation study. The desktop app and original specimen are unchanged.

Changes: broader structural bases taper over 35 mm; leaf-stalk growth curves emerge more upright; the embedded sheath is fixed to the crown and ends where the flexible stalk begins. Exposed stalk surfaces remain collidable. A 0.25 ms timestep and 1 ms contact time constant resolve the stronger base in the controlled push diagnostic.

The short videos and orbitable replays show saved MuJoCo states at physical time. The gold probe is driven by position servos limited to ±1.5 N on each world axis. Contact normal force is measured separately and is not that actuator limit. These are scripted physical diagnostics, not learned actions.

Basal dimensions, circular sections, material modulus, damping and unloaded shape are hypotheses, not fitted plant measurements. Leaflets still use articulated wedges. Crown/root anchoring is fixed. Fruit is rigid. No cutting or detachment is modeled. Numerical convergence of one push does not validate biological accuracy.

Evidence and iteration notebook: `/docs/simulation/STRAWBERRY-ITERATION-NOTES.md`. Before/after video and numerical trials are one directory above this candidate.

Photo credits and context remain in the copied specimen review. Reference images guide anatomy, not stiffness measurements.

Reference publications:
- [Cal Poly crown and roots](https://strawberrycenterblog.com/2026/02/19/__trashed/)
- [Cal Poly leaves and stems](https://strawberrycenterblog.com/2025/12/15/strawberry-anatomy-part-3-leaves-and-stems/)
- [Ohio State protected strawberry structures](https://u.osu.edu/indoorberry/structures/)
