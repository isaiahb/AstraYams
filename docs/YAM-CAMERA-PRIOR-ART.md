# YAM camera placement: primary-source research

Checked September 8, 2026. Current visual experiments use two fixed oblique cameras chosen for visibility in our scene. They are engineering assumptions, not a reproduction of a measured YAM station. Preserve those frozen experiments when testing another camera layout.

## YAM-specific references

- [I2RT YAM-ABC camera configuration](https://github.com/i2rt-robotics/yam-abc-reproduce/blob/main/configs/cameras.yaml): the supplied pick-and-place roster uses overhead, left and right RealSense cameras, each RGB 640×480 at 30 FPS, with depth disabled. The file establishes roles and acquisition settings, but supplies no camera extrinsics. It is a useful manufacturer example, not evidence of optimal placement for our insertion task.
- [ARISE YAMLab robot calibration](https://github.com/ARISE-Initiative/yamlab/blob/main/yamlab/configs/robot/yam.yaml): provides one world-mounted top camera plus left/right wrist cameras attached under each arm's link_6. The repository describes these as measured workstation calibration and includes camera transforms, intrinsics, parent frames and 640×480 calibration resolution. Coordinates belong to that station and robot model; do not paste them into our MuJoCo scene without frame conversion and mount verification.
- [I2RT teleoperation station](https://i2rt.com/products/yam-teleoperation-stations): says cameras are not included and that printable camera-mount CAD is provided. Camera choice/mounting is therefore a real integration decision, not something determined by the YAM URDF alone.

## Relevant manipulation research

[Look Closer (RA-L 2022)](https://arxiv.org/abs/2201.07779) combines a static external camera and wrist camera using cross-view attention. It reports gains over its single/multiple-view baselines and real-robot experiments. It supports testing complementary global/local views; it neither establishes a best YAM camera pose nor guarantees our small CNN/GRU will learn the same behavior.

## Recommendation for the next camera comparison

For one arm, test one elevated overview plus one rigid wrist camera; for two arms, overview plus a wrist camera on each. This is an engineering recommendation based on the references, not a measured result from our experiment. The overview should retain object/workspace context while the wrist view resolves jaw alignment and the insertion opening. Check occlusion throughout reach, grasp, transport and insertion, including the part occluding the socket while held.

Compare the current two-fixed-camera baseline and the proposed layout on the same declared development distribution, with separate regenerated datasets/checkpoints. Keep camera mounts physical (fixed world or robot-link transform), never simulator-object tracking. Match aspect ratio, scaled intrinsics, lens distortion/crop and timing; randomize bounded mounting/calibration error. Wrist hardware and cable clearance/mass require verification before real use. Do not change the running v2 experiment's camera contract after training has begun.
