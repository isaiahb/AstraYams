# Compact strawberry shape — surface study 2

The preceding surface pass still had a narrow body and drawn-out tip. This
revision uses fuller shoulders, a shorter body and a rounded tip. The primary
fruit is approximately 34 mm long by 35 mm wide; the three other fruit have
slightly different aspect ratios and flattening. These are design hypotheses,
not measured cultivar fits. A homogeneous density prior of 1000 kg/m³ determines
size while retaining the previous fruit masses.

## One shared geometry and a fresh physical response

`tools/strawberry_surface.py` defines the macroscopic profile for both the skin
and convex rigid collision envelope. Sub-millimetre pits/seeds are visual detail,
not contact roughness or tissue deformation. COM and inertia are recomputed from
the changed envelope and existing calyx mass distribution. All other plant
mass/inertia, attachments, beam joints, stiffness and damping remain unchanged.
`shape-audit.json` records the comparisons and assumptions.

The full v14 plant is used, including dynamic leaves and all neighboring fruit.
This study uses the existing elastic/damped baseline. The alternative Maxwell
relaxation and retained-rest hypotheses remain in recovery-study/v2; no one of
them has been identified from real strawberry recovery measurements.

After changing the collision geometry, the plant is integrated under gravity
until quiet. `rest/result.json` reports 20 simulated seconds, less than 0.01 mm
fruit coordinate span over the final five seconds, and no simulation warnings.
The previous shape's physics recording is not used to animate the new shape.

The neighboring-fruit probe experiment and matched contact-disabled control
then start from this new state. They are force-limited diagnostics, not PPO or
robot harvesting. Inspect both result files: numerical completion alone does
not establish fidelity or damage safety.

The tool CAD page loads `cad-context.json`: the complete settled plant translated
as one assembly. Only tool placement is adjusted. It is static CAD context;
neither net contact nor cutting is simulated there.

## Reproduce

From the repository root, with the existing full specimen/recovery assets and
Python dependencies (MuJoCo, trimesh, numpy, scipy, Pillow):

```sh
python tools/review_strawberry_surface.py
python tools/reshape_strawberry.py build settle
python tools/test_strawberry_specimen.py --model-dir assets/workcells/strawberry-specimen/surface-study/v2 --kind neighbor
python tools/test_strawberry_specimen.py --model-dir assets/workcells/strawberry-specimen/surface-study/v2 --kind neighbor --control
python tools/reshape_strawberry.py export render
```

For a newly generated plant, the shared native builder also accepts
`--compact-fruit`; it includes detailed surfaces and updated collision geometry.
Always generate fresh settling/contact records after changing the shape.
Generated mesh/replay/XML files are excluded from Git; sources, reports and
review images are retained. Serve the repo root over HTTP and open this index.

## References and remaining uncertainty

- [Ishikawa et al., fruit shape analysis](https://www.jstage.jst.go.jp/article/jsbbs/71/2/71_19106/_html/-char/en): morphology varies; a single long cone is insufficient.
- [Cal Poly Strawberry Center fruit anatomy](https://strawberrycenterblog.com/2025/11/25/strawberry-anatomy-part-2-the-fruit/): surface and calyx anatomy reference.

The next shape evidence should be measured multi-view outlines from one real
fruit, including shoulder asymmetry, cross-section and volume. Current regular
seed rows, simplified calyx and smooth uniform material remain visible model
limitations. Net deformation, stem fracture, flesh deformation, bruising, and a
PPO using the new tools remain separate unfinished work.
