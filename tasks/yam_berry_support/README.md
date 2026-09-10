# Learned berry support with YAM

The experiment prioritizes a demonstrable learned motor skill over further motor
component research. A small PPO actor directly commands all six arm joints. A
finite-torque PD controller executes those targets. No inverse kinematics,
behavior-cloning teacher, or Cartesian path controller chooses execution motion.
One IK calculation builds a fixed initial posture; it is not recomputed for each
randomized berry. The cup is a fixed wrist-mounted tool, not an object falsely
claimed to be held by friction.

The task is to approach an attached fruit, support part of its weight, and hold.
It is a subskill for harvesting, not a complete harvest. Geometry is reused from
the researched v14 strawberry specimen and the pinned official YAM assets.
Fruit-bearing branches retain their joints, mass and springs. Foliage is fixed
in its settled pose, with collision surfaces retained. No cutting occurs.

Actor inputs are 34 simulated state values: joint displacement from the fixed
start, joint velocity, target tracking error, relative fruit/cup position, cup
normal, true contact force, previous actions and hold progress. This is privileged
state training, not camera-based transfer. The true contact-force input would
require sensing or estimation on physical hardware. Motor dynamics and the plant
are uncalibrated; arm self-collision remains disabled in this local experiment.

The frozen success condition is 0.4 continuous seconds carrying 60–110% of fruit
body weight, XY error below 5 mm, cup-normal vertical component above 0.94, and
joint-velocity norm below 0.3 rad/s. Abort limits are 0.65 N target contact,
0.8 N other robot contact, or 0.8 mm target penetration. These limits are
engineering acceptance criteria, not biological bruising thresholds.

Training gradually expands berry position, stalk stiffness, and fixed-leaf
orientation variation. Development seeds are separate from final holdout seeds.
A holdout with varied leaves does not alone prove the robot learned leaf avoidance;
causal obstacle interaction needs its own test. Report that limitation explicitly.

Rebuild and train:

```sh
PYTHONPATH=src python tools/build_yam_berry_support.py
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python tools/train_berry_support_ppo.py
```

Generated scene, initial state, policy checkpoints and recordings are local
artifacts; source and compact experiment results should be committed. Always pin
the source/scene hashes with each run. Replay saved actions through dynamics and
compare the resulting states before publishing video or an orbitable recording.

Rejected setup: v1 had a support rod protruding into the cup. Its first 32,768-step
PPO learned an approach but scored 0/3 on the full support criterion. The cup mount
was lowered and a floor added. v2 fine-tunes that PPO checkpoint; it must not be
reported as a fresh scratch run or as success on the rejected geometry. The v1
checkpoint and report remain in runs/yam-berry-support-ppo-v1.
