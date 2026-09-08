# Manual screw-vise variant

Separate design reference: the powered-vise checkpoint is unchanged. A 40 mm pedestal lifts the entire vise and finished stock; raw stock remains in its original tray. Change this with `--pedestal-height-mm` when regenerating. Build with `/tmp/clonebench-cad-env/bin/python tools/build_manual_vise_cad.py`. STEP uses millimetres; each STL uses metres in its declared body frame. The complete assembly contains a genuine helical CAD ridge at 2 mm pitch, drilled bearing supports, guide bearings, a translating nut bridge and a radial robot-graspable crank.

The grip sleeve is a separate `manual_grip_sleeve` body with origin (0.035, 0.022, 0) m in the crank frame and a proposed passive Y-axis bearing; the robot need not rotate its wrist with the crank. Low bearing damping/friction are explicit provisional mechanical assumptions. The manual table spans world X −0.130 to 0.800 m and Y −0.200 to 0.650 m, with its top at Z=0.

Screw rotation is axially fixed; the anti-rotation nut and moving jaw translate along Y. Handle centre is world (0.320, 0.135, 0.095) m, radius 35 mm. At zero angle the cylindrical 8 mm × 24 mm grasp pin is centred at (0.355, 0.157, 0.095) m. A 20 to 14 mm closing stroke needs three turns; a declared 16 to 14 mm near-clamp stroke needs one. Full 39 to 14 mm closing needs 12.5 turns.

`mechanical_spec.json` defines proposed coupling, finite torque, friction and force bounds. None is calibrated hardware evidence. New handle/bridge collision geometry, both arms, all crank angles and nut travel require a separately audited simulation task. No powered actuator or implicit infinite-force drive is included. The original jaw/stock faces remain the reference contact geometry; this CAD is not manufacturing validated.
