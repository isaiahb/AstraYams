# Machine-tending CAD reference

Build with `/tmp/clonebench-cad-env/bin/python tools/build_machine_fixture_cad.py`. CadQuery constructs dimensioned solids in millimetres. STEP is a named, coloured assembly in millimetres at the original reset configuration. Each STL is exported in metres in its original MuJoCo body frame; read `manifest.json` for attachment, bounds and hashes. World-attached table and tray coordinates are already baked. Stock meshes retain exact 18 × 14 × 70 mm dimensions with the body origin at the bottom.

The moving rod and jaw assembly attach to `vise_slider`, so recorded slider motion is visible without invented animation. The powered actuator housing is a visual design reference, not a calibrated pneumatic or electric mechanism. Chamfers, counterbores, hex sockets, guide bearings and formed tray rims are CAD geometry.

The unchanged `tasks/yam_machine_tending/scene.xml` remains the contact and dynamics authority. These visual assets must never replace collision geometry implicitly. Cosmetic geometry may differ at fillets and around housings; no manufacturing tolerances, strength, seals, cutting loads or collision clearances are validated.
