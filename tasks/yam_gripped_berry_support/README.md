# Gripper-held support tool experiment — rejected industrial design

This intermediate simulation fixed the false attachment assumption: the tool has a
free joint, geometry-derived mass/inertia and jaw contacts. It has no weld,
kinematic parenting or tool-to-arm equality. At reset it is prepositioned in the
jaws; acquisition from a tool rack is not claimed. The grip servo closes with
bounded effort. The six arm-joint targets remain PPO outputs.

The user rejected its industrial design. Training stopped after a saved 65,536-step
finetuning round, with 0/3 development successes. Neither the 11/12 fixed-mount
result nor the scripted grasp test is evidence for a learned complete harvest.
The actual solid CAD replacement is in cad/berry-cradle/rev-a. That design has
not yet replaced these collision meshes or undergone PPO training.

Measured engineering test in this simulation: 5.10 N minimum normal force per jaw,
1.80 mm maximum tool displacement relative to the wrist during 3.5 seconds of
scripted joint motion. Opening the jaws releases the tool; its relative displacement
reaches 294 mm. Friction, contact compliance and motor calibration remain assumptions.

Rebuild the earlier fixed experiment first with tools/build_yam_berry_support.py,
then tools/build_gripped_berry_tool.py. tools/audit_gripped_berry_tool.py runs the
scripted test. Training entry is tools/train_berry_support_ppo.py --gripped.
Do not resume training on this rejected shape without an explicit reason.
