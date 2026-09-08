# YAM contact-only grasp and insertion

Instantiate `astrafactory.contact_env.ContactEnv` with this directory. The official YAM arm has six torque-controlled rotary joints and two articulated fingers coupled by their joint mimic relation. The peg has a world-parented free joint: no weld, mocap, adapter stem, or shared rigid body attaches it to the robot. Only reset places it; actions do not assign peg poses.

The 40 g custom part has a 38 mm keyed insertion section plus a graspable rectangular handle, for 70 mm total height. This is an explicit part redesign to put real finger contact above the socket. The inner finger contact geometry uses 48 convex pieces decomposed from the actual official finger meshes. Measured distal surface agreement and global approximation bounds are in `assets/robots/yam/collision/DECOMPOSITION.json` and `docs/GRIPPER-CONTACT.md`.

## Controls and state

Seven normalized actions: six arm-joint target increments (0.01rad maximum per20ms), plus the primary finger target increment (0.6mm maximum). Negative finger displacement opens; movement toward zero closes. The second jaw is coupled through joint equality; this equality does not involve the peg. Bounded PD applies forces/torques through MuJoCo. Gripper PD, friction, contact stiffness and arm dynamics are provisional; they have not been calibrated against a physical YAM.

42 privileged state values: joint positions7, velocities7, controller targets7, peg goal position/orientation error6, previous actions7, free-peg pose7, contact-load scalar1. This is not a trained VLA or camera-only policy. Reset currently uses one fixed pickup and socket pose; supplied seed is accepted by Gym but does not introduce pose variation yet. No pose overrides are accepted.

## Acceptance and test boundaries

The task tracks whether the peg was genuinely lifted with bilateral contact before allowing insertion success. Insertion also requires position/orientation/depth, low peg velocity and bounded contact force held over15steps. The check is not electrical mating, press fit, latching or release stability.

Independent checks verify absence of an attachment, sustained unsupported bilateral contact lift, release when opened, and failure to sustain lift on zero-friction replay. The default script attempts grasp→lift→transport→insert; insertion presently catches the rim and aborts. Do not report this as a successful assembly.

Robot self-collision is still disabled; arm link collision approximations and passive/actuator parameters remain provisional. Finger geometry is convex-decomposed, not an exact analytic surface; the collision material model is rigid Coulomb-style contact, not measured elastomer deformation. Passing simulated grasp checks establishes contact-based behavior, not real-world grasp reliability.

Full evidence: [contact validation](../../docs/CONTACT-VALIDATION.md).
