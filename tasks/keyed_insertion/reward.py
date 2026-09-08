"""Training reward can evolve independently of the task's success evaluator."""
import numpy as np


class Reward:
    def __init__(self, env):
        self.env = env
        self.last_distance = 0.

    def reset(self):
        self.last_distance = self.env.task.distance()

    def __call__(self, action, info):
        distance = self.env.task.distance()
        progress = self.last_distance - distance
        self.last_distance = distance
        return 80 * progress - distance - .0005 * np.sum(action ** 2) - .002 * min(self.env.task.force, 50) + (10 if info["is_success"] else 0)
