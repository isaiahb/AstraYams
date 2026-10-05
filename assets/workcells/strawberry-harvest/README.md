# Three-strawberry harvest with official YAM wrist cameras

This isolated study uses two YAM v1 arms with linear-4310 grippers. Three separate simulated strawberries are cut, caught, and deposited into one basket in a continuous episode. Completed fruit bodies remain in the physics simulation; there are no between-fruit resets or teleports. The controller is scripted state feedback, not a learned or camera-driven policy. The cel-shaded video replays the saved actions at real time.

## Hardware provenance

Official I2RT camera assembly, mount mesh, and gripper-to-optical-frame transforms:
https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/robot_models/station/yam_station_linear_4310_d405/README.md

Pinned source files and MIT license are in references/. Both wrist cameras use the published transforms and mesh; ROS optical axes are converted to MuJoCo camera axes. The harvesting cell uses its own opposing-arm base arrangement, not the official station base layout.

YAM product specifications: 95 mm gripper throw, 2 kg nominal payload, 750 mm maximum workspace, and 5.02 kg arm weight including gripper:
https://i2rt.com/products/yam-6-dof-arm

D405 manufacturer specifications: 42 x 42 x 23 mm, 60 g, nominal 87 x 58 degree field of view, ideal operating range 7–50 cm:
https://www.realsenseai.com/products/stereo-depth-camera-d405/

The camera projection uses nominal 87 x 58 degrees at 1280 x 720. These are not intrinsics calibrated from a physical camera. Manufacturer documentation has a horizontal-FOV discrepancy (84 degrees in the August 2025 datasheet versus 87 on the product page); this study uses the product page. Distortion and calibrated RealSense depth noise are not modeled. Camera mass is 60 g plus an estimated 30 g bracket; the official CAD inertia distribution is scaled to that assumed assembly mass.

## Results and limitations

Seed 1: 3/3 retained in basket in 34.12 s. Video replay has zero maximum qpos discrepancy and zero maximum camera optical-origin discrepancy against the configured mount transforms. See replay-audit.json and hardware-applied.json.

Seed 2: 2/3 collected by 60 s, lost finger contact with tool; peak catch force 20.81 N.
Seed 3: 3/3 retained in 34.72 s, peak catch force 4.59 N.

Thus two of three tested runs complete; grasp retention across repeated cycles needs improvement. This is not a validated sim-to-real system. Stem cutting is a simplified fracture model, tool mechanisms are concept geometry, and friction, bracket mass, actuator limits and sensor calibration need hardware measurement. The basket's slatted rendering uses a continuous collision liner approximation.

## Artifacts

- three-strawberries-wrist-cameras.mp4: continuous successful episode, overview and two wrist views.
- rollout.npz / trace.json / events.json: saved episode and measurements.
- validation.json: additional seeds, including failure.
- scene.xml: generated physics scene.
- env_multi.py / run.py / render_multi.py: environment, controller and rendering.

## Crop placement correction

Background strawberries now hang at y=0.145 m in front of the trough's y=0.195 m wall, with stems routed above its rim before descending outside. The clearance audit measures approximately 29.7 mm between each background fruit mesh and the trough, and at least 44.5 mm between the three harvested fruit collision shapes and the trough over all 1,706 saved poses. This correction changes static decorative geometry, not the controller, task fruit poses, or evaluation criteria. Background fruit and foliage remain non-contact scenery.
