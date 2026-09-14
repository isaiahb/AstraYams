# Return to foliage: revision 01

The user asked to leave the dataset/gallery detour and add foliage to the
existing model. This revision reuses `photo-fit-v1/shape-constrained` unchanged.
It adds 38 node-attached shoots bearing 114 compound leaves (148 → 262).
The earlier rejected wide-blade geometry is not used.

## Reproduce

From the repository root, with the existing Python environment:

```sh
/Users/isaiah/Documents/BallahTech/City-Farmers-Sim/.venv/bin/python research/hemp-defoliation/foliage-density-v1/build.py
```

Open `/runs/hemp-foliage-density-v1/index.html` on the existing local server.
The generator requires the preserved photo-fit export and its source research
files. No SAM, depth model, image fitting, training, or GPU job is launched.
It imports geometric functions from the original module; that module opens its
small reference image, but this build does not call its raster fitting routines.
Generated mesh data remains under ignored `runs/`; source and checks are versioned.

## Review / evidence

- Matched front, side, three-quarter and top camera presets; linked orbit/zoom.
- Before and after share the exact baseline buffers and lighting.
- Added organs can be highlighted, and foliage hidden to inspect support.
- All 38 new shoots begin on existing nodes; all 114 petioles begin on shoot nodes.
- Parent IDs, uniqueness, triangle index bounds, finite coordinates checked.
- `checks.json` records baseline hash and zero analytic attachment mismatch.
- Browser review inspected front, side, three-quarter and skeleton views.
- The viewer merges meshes and renders on interaction only to avoid idle load.

## What the comparison revealed

The revision increases canopy occupancy and side-view foliage depth. It does
not solve the flatter, photograph-derived primary branch arrangement. Much of
the lower canopy overlaps densely while the middle remains open. Those are
visible limitations, not a validated commercial plant shape.

The added geometry is a seeded hypothesis, not measured cultivar variation or
biological growth. No collision shapes, elastic parameters, damage limits or
policy results were changed. Contact physics and self-intersections have not
been validated for these additions. Do not feed the new render to training as
though the added leaves already had corresponding physical bodies.

## Methodology retained

Change one identifiable feature, preserve the accepted baseline, expose the
addition separately, inspect matching angles, and record the discrepancy still
visible. Do not substitute segmentation coverage or organ count for realism.
