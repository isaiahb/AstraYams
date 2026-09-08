"""Camera/proprioception wrapper without privileged object-goal coordinates."""
import gymnasium as gym
from gymnasium import spaces
import mujoco
import numpy as np


class CameraObservation(gym.ObservationWrapper):
    def __init__(self, env, width=320, height=240):
        super().__init__(env)
        n = env.action_space.shape[0]
        self.width, self.height = width, height
        self.camera_renderer = None
        self.observation_space = spaces.Dict({
            "image": spaces.Box(0, 255, (height, width, 3), dtype=np.uint8),
            "proprioception": spaces.Box(-np.inf, np.inf, (4 * n,), dtype=np.float32),
        })

    def observation(self, observation):
        e = self.env.unwrapped
        if self.camera_renderer is None:
            self.camera_renderer = mujoco.Renderer(e.model, height=self.height, width=self.width)
        self.camera_renderer.update_scene(e.data, camera=e.specification.get("camera", "overview"))
        return {"image": self.camera_renderer.render().copy(), "proprioception": np.r_[e.data.qpos[e.qadr], e.data.qvel[e.vadr], e.target, e.previous_action].astype(np.float32)}

    def close(self):
        if self.camera_renderer is not None:
            self.camera_renderer.close()
            self.camera_renderer = None
        super().close()
