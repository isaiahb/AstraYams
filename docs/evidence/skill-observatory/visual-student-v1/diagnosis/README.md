# Visual student v1: bounded independent diagnosis

The failed first candidate has two concrete problems. This review changed no policy, dataset, physics, or evaluation code.

1. Low-variance feedback normalization amplifies prediction error. Previous-action joint5 has a training normalization standard deviation floored at0.001. The first predicted joint5 command+0.012596 becomes+12.574 normalizedinput atstep2. By step12 the channel is−23.722; later it reaches about184 standard deviations. State/action histories then depart strongly from demonstration support. This is a plausible closed-loop instability mechanism, not a proven sole cause.
2. Initial actions barely respond to different scene images. Across five rollout-development layouts with exactly identical initial proprioception, student first-action standard deviations are only about1–3.6e−5 perchannel. The offline same-state privileged comparison controller varies joint1 by0.1435 andjoint6 by0.3919. In seed21000 the student initially commands joint6+0.056 while the comparison requires−0.4; other layouts require+0.4. This supports insufficient initial visual localization, independent of the later normalization feedback.

The sampled seed21000 replay starts62mm from the grasp-handle target and is73mm away bystep101; the diagnostic comparison controller still considers this an approach state. Comparison commands were calculated only after the scored rollout for diagnosis and were never executed. The replay used original saved student actions; its encoder discrepancy is recorded and includes float32 sensor serialization precision.

RGB layout/transpose and [0,1] scaling match between training and runtime. Action limits match the demonstration controller (.4 arm,.5 gripper), and the SDK-compatible jaw opening codec is used identically in collection and evaluation. No unit/sign/shape mismatch was found.

V2 changes normalization, training coverage, and early-state sampling together. Any subsequent improvement cannot isolate a causal effect of just one change. Offline regression quality alone is not physical pickup success.
