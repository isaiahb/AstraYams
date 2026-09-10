# Strawberry morphology — observed curves and parametric variation

## Why the preceding shape failed

V2 varied length, width and one depth scale but repeated a symmetric loft. It
therefore retained equal shoulders, a centered apex and a straight centerline.
Changing its aspect ratio did not address those structural restrictions.

## Anatomical and morphological evidence

The fleshy body is an enlarged receptacle. Achene development and pollination
affect its uneven growth; cultivar and flower order also matter. Li et al.
(2020) measure multiple azimuths, horizontal sections, section circularity and
center-axis straightness. Their work shows why a single front view is not a
complete shape description. This model does not simulate those growth processes.
It represents the resulting geometry. [Li et al.](https://www.nature.com/articles/s41438-020-0337-x)

Nagamatsu et al. (2021), Fig. 1, provides typical and atypical photographs from
six cultivars. We segment all 18 photographs, keeping the two sides separately
instead of imposing symmetry. The source photographs have their calyces removed.
The normalized width and midpoint curves retain the observed shoulder position,
asymmetric taper and tip shift. The six 3D library examples use panel A directly.
These examples are a selected research figure, not a representative distribution
of supermarket or greenhouse fruit. [Nagamatsu et al.](https://www.jstage.jst.go.jp/article/jsbbs/71/2/71_19106/_html/-char/en)

UPOV TG/22/11 (2023), pp. 25–27, separately describes overall shape, maximum-width
position, apex form, calyx-end form, achene-free band, achene depth and calyx
attachment. These are useful independently inspectable traits; they are not
instructions to add arbitrary surface noise. [UPOV](https://www.upov.int/edocs/tgdocs/en/tg022.pdf)

## Representation and uncertainty

- Observed: 41 samples of half-width and midpoint versus longitudinal position,
  aspect ratio and widest-point location. Color segmentation and smoothing are
  approximate to 1–2 image pixels. Inspect `outline-analysis.png` and the masks;
  terminal slice midpoints are especially sensitive to pixel quantization.
- Assumed: depth/width, depth taper, out-of-plane bending and small angular
  lobes. One view cannot determine these. The browser controls demonstrate their
  effect; slider ranges are exploratory, not measured biological bounds.
- Coupled: skin, achenes and rigid envelope receive the same macroscopic mapping.
  Size is set by a 1000 kg/m³ density prior with the existing fruit masses. The
  calyx geometry/mass remain a simplified separate component.
- Plant example: interpolations within the three Fukuoka S6 outlines. These do
  not reconstruct a particular real plant. The small green fruit uses a scaled
  ripe-outline proxy; maturity-dependent shape still needs separate observations.

The original complete plant remains: leaf dynamics, truss topology, attachment
frames, stiffness and damping. Fruit collision, COM and inertia are rebuilt,
followed by new gravity settling and a contact/control pair. These use the
existing elastic/damped baseline; alternative material laws remain available
in recovery-study/v2. No training or biological calibration is claimed here.

## Reproduction

```sh
python tools/strawberry_morphology.py
python tools/study_strawberry_morphology.py library build settle
python tools/test_strawberry_specimen.py --model-dir assets/workcells/strawberry-specimen/surface-study/v3 --kind neighbor
python tools/test_strawberry_specimen.py --model-dir assets/workcells/strawberry-specimen/surface-study/v3 --kind neighbor --control
python tools/study_strawberry_morphology.py export render audit fit_review
```

All paths are relative to the repository root. Preserve V1 and V2. Generated
meshes, XML and full rollouts are excluded from Git; inputs, sources, reports
and visual reviews are retained. `reference/` contains source figure copies for
analysis and identified crop/overlay derivatives. Li et al. figures are CC BY
4.0; attribution remains with the cited authors. No claim of owning the source
photographs is made.

## Next evidence

Get paired orthogonal or turntable views of the *same* fruit with a scale marker,
measure the hidden cross-sections, and test held-out views. Fit a correlated
within-cultivar distribution before randomizing plants for policy training.
Check collision approximation at each likely contact patch, and replace rigid
fruit with a separately validated deformation component when the task requires
indentation. Texture, calyx refinement, net mechanics and cutting remain open.
