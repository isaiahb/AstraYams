"""Task-independent MuJoCo/Gym execution core.

Task plugins are trusted local Python, not a sandbox for arbitrary code.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import gymnasium as gym
from gymnasium import spaces
import mujoco
import numpy as np


class FactoryEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 25}

    def __init__(self, task_dir, render_mode=None):
        self.task_dir = Path(task_dir).resolve()
        self.specification = json.loads((self.task_dir / "task.json").read_text())
        if self.specification["schema_version"] != 1:
            raise ValueError("Unsupported task schema")
        self.model = mujoco.MjModel.from_xml_path(str(self.task_dir / self.specification["scene"]))
        self.data = mujoco.MjData(self.model)
        self.render_mode = render_mode
        self.renderer = None
        self.frame_skip = self.specification["frame_skip"]
        self.horizon = self.specification["horizon"]
        config = self.specification["controller"]
        self.jids = np.array([self.model.joint(n).id for n in config["joints"]])
        self.qadr = self.model.jnt_qposadr[self.jids]
        self.vadr = self.model.jnt_dofadr[self.jids]
        self.aids = np.array([self.model.actuator(n).id for n in config["actuators"]])
        self.limits = self.model.jnt_range[self.jids].copy()
        self.scales = np.asarray(config["action_scale"])
        self.kp = np.asarray(config["kp"])
        self.kd = np.asarray(config["kd"])
        self.action_space = spaces.Box(-1, 1, (len(self.jids),), dtype=np.float32)
        plugin_path = self.task_dir / self.specification["plugin"]
        spec = importlib.util.spec_from_file_location("task_" + hashlib.sha256(str(plugin_path).encode()).hexdigest()[:12], plugin_path)
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)
        self.task = plugin.Task(self)
        reward_path = self.task_dir / self.specification["reward_plugin"]
        reward_spec = importlib.util.spec_from_file_location("reward_" + hashlib.sha256(str(reward_path).encode()).hexdigest()[:12], reward_path)
        reward_module = importlib.util.module_from_spec(reward_spec)
        reward_spec.loader.exec_module(reward_module)
        self.reward_function = reward_module.Reward(self)
        self.observation_space = spaces.Box(-np.inf, np.inf, (self.specification["observation_size"],), dtype=np.float32)
        self.initial_body_pos = self.model.body_pos.copy()
        self.initial_body_quat = self.model.body_quat.copy()
        self.target = np.zeros(len(self.jids))
        self.previous_action = np.zeros(len(self.jids))
        self.steps = 0
        self.episode_peak_force = 0.

    def _observation(self):
        observation = np.asarray(self.task.observe(), dtype=np.float32)
        if observation.shape != self.observation_space.shape or not np.isfinite(observation).all():
            raise ValueError("Task returned invalid observation")
        return observation

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.model.body_pos[:] = self.initial_body_pos
        self.model.body_quat[:] = self.initial_body_quat
        self.previous_action[:] = 0
        self.steps = 0
        self.episode_peak_force = 0.
        self.task.reset(self.np_random, options or {})
        self.target = self.data.qpos[self.qadr].copy()
        mujoco.mj_forward(self.model, self.data)
        self.reward_function.reset()
        return self._observation(), {"task_id": self.specification["id"], "is_success": False}

    def step(self, action):
        action = np.asarray(action, dtype=float)
        if action.shape != self.action_space.shape or not np.isfinite(action).all():
            raise ValueError("Action must be finite and match the action space")
        action = np.clip(action, -1, 1)
        self.target = np.clip(self.target + action * self.scales, self.limits[:, 0], self.limits[:, 1])
        peak_force = 0.
        for _ in range(self.frame_skip):
            control = self.kp * (self.target - self.data.qpos[self.qadr]) - self.kd * self.data.qvel[self.vadr] + self.data.qfrc_bias[self.vadr]
            bounds = self.model.actuator_ctrlrange[self.aids]
            self.data.ctrl[self.aids] = np.clip(control, bounds[:, 0], bounds[:, 1])
            mujoco.mj_step(self.model, self.data)
            contact_load = 0.
            for contact_id in range(self.data.ncon):
                force = np.zeros(6)
                mujoco.mj_contactForce(self.model, self.data, contact_id, force)
                contact_load += float(np.linalg.norm(force[:3]))
            # Conservative sum of contact-force magnitudes, not a hardware wrench sensor.
            peak_force = max(peak_force, contact_load)
        self.episode_peak_force = max(self.episode_peak_force, peak_force)
        self.steps += 1
        info = self.task.evaluate(peak_force)
        reward = float(self.reward_function(action, info))
        self.previous_action = action.copy()
        finite = bool(np.isfinite(self.data.qpos).all() and np.isfinite(self.data.qvel).all())
        unsafe = peak_force > self.specification["abort_contact_force_n"]
        terminated = bool(info["is_success"] or unsafe or not finite)
        truncated = bool(self.steps >= self.horizon and not terminated)
        info.update(task_id=self.specification["id"], sim_time=float(self.data.time),
                    peak_contact_force_n=peak_force, episode_peak_force_n=self.episode_peak_force,
                    reason="success" if info["is_success"] else "force_limit" if unsafe else "nonfinite" if not finite else "timeout" if truncated else None)
        return self._observation(), reward, terminated, truncated, info

    def render(self):
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=720, width=960)
        self.renderer.update_scene(self.data, camera=self.specification.get("camera", "overview"))
        return self.renderer.render()

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
            self.renderer = None
