"""Explicit reset-only domain randomization for contact skill experiments.

These are engineering sensitivity ranges, not calibrated real-world distributions.
A fresh unwrapped CurriculumEnv is the frozen nominal evaluator.
"""
from copy import deepcopy
import hashlib
import json
import mujoco
import numpy as np

PROFILES = {
    "nominal": {"mass_scale": [1., 1.], "friction_scale": [1., 1.],
                "peg_xy_m": .002, "socket_xy_m": .002, "yaw_rad": .02},
    "training-mild-v1": {"mass_scale": [.9, 1.1], "friction_scale": [.9, 1.1],
                         "peg_xy_m": .003, "socket_xy_m": .003, "yaw_rad": .025},
    "stress-v1": {"mass_scale": [.8, 1.2], "friction_scale": [.8, 1.2],
                  "peg_xy_m": .004, "socket_xy_m": .004, "yaw_rad": .04},
}

class SkillRandomization:
    """Use reset(seed=..., domain_seed=...) before a rollout; never between skills."""
    def __init__(self, env, profile="training-mild-v1", role="training"):
        if profile not in PROFILES or role not in ("training", "stress", "nominal"):
            raise ValueError("Unknown profile or role")
        expected = {"training": "training-mild-v1", "stress": "stress-v1", "nominal": "nominal"}
        if expected[role] != profile:
            raise ValueError("Randomization role/profile mismatch")
        self.env, self.profile, self.role = env, profile, role
        self.base_mass = env.model.body_mass.copy()
        self.base_inertia = env.model.body_inertia.copy()
        self.base_friction = env.model.geom_friction.copy()
        self.base_curriculum = deepcopy(env.specification["curriculum"])
        self.peg_id = env.model.body("free_peg").id
        self.geoms = [i for i in range(env.model.ngeom)
                      if any(s in (env.model.geom(i).name or "")
                             for s in ("peg", "finger_left", "finger_right"))]
        self.last_sample = None

    def reset(self, *, seed, domain_seed=None):
        if domain_seed is None: domain_seed = seed + 100000
        rng = np.random.default_rng(domain_seed)
        profile = PROFILES[self.profile]
        mass = float(rng.uniform(*profile["mass_scale"]))
        friction = float(rng.uniform(*profile["friction_scale"]))
        e = self.env
        e.model.body_mass[:] = self.base_mass
        e.model.body_inertia[:] = self.base_inertia
        e.model.geom_friction[:] = self.base_friction
        e.model.body_mass[self.peg_id] *= mass
        e.model.body_inertia[self.peg_id] *= mass
        # One shared sliding-friction scale avoids claiming independent contact
        # parameters when MuJoCo's pair combination can select the larger one.
        e.model.geom_friction[self.geoms, 0] *= friction
        e.specification["curriculum"] = {k: profile[k] for k in self.base_curriculum}
        # Recompute mass-dependent constants with scratch data, then normal reset.
        mujoco.mj_setConst(e.model, mujoco.MjData(e.model))
        obs, info = e.reset(seed=seed)
        self.last_sample = {"role": self.role, "profile": self.profile,
            "reset_seed": seed, "domain_seed": domain_seed,
            "mass_scale": mass, "sliding_friction_scale": friction,
            "peg_mass_kg": float(e.model.body_mass[self.peg_id]),
            "curriculum": deepcopy(e.specification["curriculum"]),
            "range_provenance": "uncalibrated engineering sensitivity assumption",
            "profile_sha256": hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()}
        return obs, {**info, "domain_randomization": deepcopy(self.last_sample)}
