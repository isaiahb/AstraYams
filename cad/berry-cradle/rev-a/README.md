# Cradle 01 — solid CAD, revision A

A real B-rep prototype replaces the earlier assembly of simulation primitives.
`build.py` creates a single valid solid with CadQuery/Open Cascade and exports STEP,
B-rep, STL and orthographic SVGs. All modelling dimensions are millimetres. The STL
is a tessellation of the solid; it is not the source design.

The gripping envelope is derived from the official YAM jaw mesh: opposed inner
pad planes, about 34 mm distal axial span and 40 mm lateral span. The part uses a
34 × 26 × 16 mm grip envelope with R3 corners, leaving flat contact faces. An
elliptical loft and R2 shoulder blend join the grip to the curved cradle. The bowl
uses concentric 17/15 mm spheres for a nominal 2 mm radial wall; its lip and side
opening have R0.65 edge rounds. CAD volume and an assumed solid PA12 density of
1.01 g/cm³ give an approximate 18.4 g mass. These are design assumptions, not
measurements of a fabricated tool.

The side opening is provisional. A full crude cup contacted an adjacent berry in
the earlier simulation, but that does not justify this particular opening's size.
Next compare the closed bowl and rounded relief alternatives along collision-
checked approaches, including berry/support coverage. Do not train around an
arbitrary missing slice and then label the geometry validated.

`render.py` re-imports STEP and checks validity, solid count and volume. Its jaw
images are static CAD fit studies, not a dynamics or learned-grasp claim. The HTML
review offers orbiting, section clipping, STEP download and parametric source.
Manufacturing method, print orientation, finishing, contact pressure, stiffness,
friction and bruise limits still need validation. The model is a concept prototype,
not production-ready or validated for harvesting.

PPO training was paused when this CAD work began. No previous policy success rate
applies to this new geometry. Before resuming: derive collision pieces from this
solid, include its mass/inertia, test free-tool retention/release, then evaluate the
frozen policy and finetune only against unchanged acceptance criteria.
