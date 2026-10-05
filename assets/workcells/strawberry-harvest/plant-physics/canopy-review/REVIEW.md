# Canopy iteration after approved botanical v8 checkpoint

The prior checkpoint remains at ../botanical-review/ with its video, replay and source. An additional local checkpoint with SHA-256 file hashes is saved in the study at checkpoints/2026-09-09-botanical-v8/. The YAM hardware, tools, fruit truss geometry and stiffness baseline are unchanged.

Changes: deterministic per-crown variation in petiole lengths, heights and directions; varied leaflet pitch and roll; contiguous cupped/serrated lamina panels; lower older leaves near the fruit; subtle leaf color variation. Removed the thin artificial midrib geometry and reduced the dark contour thickness specifically on leaf surfaces. Physics still uses physical hinged panels with convex-hull contacts; leaf tissue is not FEM and the concave visual cup is approximated by a hull for contact.

Both 14-second control/contact runs completed without MuJoCo warnings. The unchanged 2 mm engineering quiet-rest gate passed. The largest control motion span in the final second was 0.498 mm; the final maximum contact-vs-control positional difference was 0.945 mm. This is a simulated sanity check, not a real-plant validation. It is less quiet than the previous checkpoint, with additional foliage interaction, and does not demonstrate improved transfer performance.

A single-pose rendering check found that leaf surfaces hide about 6.4% of berry-mesh pixels in the cutting wrist view, 1.3% in the overview, and 0% in the catching wrist view. This is modest added occlusion, not a dense-canopy benchmark. RGB images, counts and the counterfactual definition are in canopy-v1/visibility.json. No camera mount was moved.

The leaves are physical and can contact objects. The orange sphere is a force-driven diagnostic probe, not a learned robot action. Fruit detachment is still unavailable in this contact-only candidate. Real leaf geometry, stiffness/damping measurements, cutting/topology change and fruit deformation remain outstanding.
