# First measured-outline diagnostic — rejected physics candidate

The user requested three tasks: standing-plant leaf removal, large-leaf removal on harvested branches, and fine trimming around harvested flowers. This experiment is an early anatomy component, not any of those completed tasks.

## View

[Local orbitable geometry review](http://127.0.0.1:8793/runs/hemp-leaf-contact-v1/index.html)

The review is explicitly static. It shows a measured 2D leaf outline, candidate triangulation, and the source's individual leaflet landmarks. No recorded motion is presented as accepted physics.

## Source and assumptions

The coordinate measurements come from specimen `FUT75_2_12_4a_7` in the dataset accompanying Balant et al. (2024). See [provenance](../reference-data/provenance.json). No author code or original photograph is copied. This Futura 75 sample is not evidence for the partner's CBD cultivar.

The central leaflet is assigned a 110 mm diagnostic length. Physical scale, planar starting pose, stem/petiole geometry, mass, and material properties are assumptions. The 484-vertex, 570-triangle mesh has about 5.2% less area than the source outline at that assumed scale. Agreement in projected area is not anatomical or mechanical validation.

## Rejections retained

1. An initial coarse triangulation lost 9.6% of the outline area, failing the predeclared 8% geometry check. Increased boundary resolution reduced this error, but did not establish a suitable mechanical mesh.
2. The first mechanics trial included contact within attached tissue and internal shell contact at very small elements. The attachment contact filtering was narrowed to exclude the fixed stem/first petiole segment and the distal bonded leaf region. External probe contact remained enabled. Internal anti-inversion contacts were disabled while flex self-collision remained enabled, following the simulator's distinction between those mechanisms.
3. Even with zero initial contacts, the revised elastic-shell candidate became unstable during settling at a 0.5 ms timestep. Short probes at smaller timesteps also failed. No recovery curve, contact success, or biological fidelity is claimed.
4. Visual anatomy review identified a more fundamental error: a projected union outline is insufficient evidence for connecting overlapping leaflets into one continuous sheet. The seven leaflet landmarks must inform separate surfaces and their attachments. Hidden basal geometry needs explicit assumptions.

The stem/petiole remains schematic; veins, local tissue reinforcement, turgor, growth, separation, and flowers are not modeled.

## Next bounded experiment

Reconstruct separate leaflet topology first. Then create a conditioned mechanical mesh and isolate one leaflet with a clearly specified attachment boundary. Assess bending-force stability and discretization sensitivity before reintroducing petiole compliance and whole-leaf contact. Keep the failure record and original outline for comparison.

## Reproduce

```sh
/tmp/clonebench-cad-env/bin/python research/hemp-defoliation/diagnostics/leaf_contact.py --geometry-only
/tmp/clonebench-cad-env/bin/python research/hemp-defoliation/diagnostics/render_review.py
```

Omitting `--geometry-only` reproduces the rejected contact attempt and writes `failure.json`; it is expected to fail with the current candidate. The prototype uses the existing MuJoCo 3.12.0 environment, NumPy, SciPy, and Matplotlib. No training job was started.

Simulator reference: [MuJoCo flex contact and elasticity](https://mujoco.readthedocs.io/en/latest/XMLreference.html#flex-contact). Numerical settings and code are experimental, not recommended biological properties.

The small `evidence/` snapshot retains the failure and geometry reports, candidate model, and static images. `manifest.json` records their hashes. The candidate remains anatomically rejected even if a later numerical setting makes it stable; passing numerical checks cannot override that rejection.
