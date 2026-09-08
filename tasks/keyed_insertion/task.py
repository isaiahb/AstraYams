"""Task-owned reset, observation, reward and frozen physical success contract."""
import numpy as np


def angle(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class Task:
    def __init__(self, env):
        self.env = env
        self.socket_id = env.model.body("socket").id
        self.goal = np.zeros(4)
        self.hold = 0
        self.force = 0.
        self.last_distance = 0.

    def error(self):
        error = self.goal - self.env.data.qpos[self.env.qadr]
        error[3] = angle(error[3])
        return error

    def reset(self, rng, options):
        e = self.env
        c = e.specification["reset"]
        xy = rng.uniform(-c["socket_xy_range_m"], c["socket_xy_range_m"], 2)
        yaw = rng.uniform(-c["socket_yaw_range_rad"], c["socket_yaw_range_rad"])
        self.goal = np.r_[xy, .009, yaw]
        e.model.body_pos[self.socket_id] = [*xy, 0]
        e.model.body_quat[self.socket_id] = [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
        pose = np.r_[xy + rng.uniform(-c["tool_xy_error_m"], c["tool_xy_error_m"], 2), .062, yaw + rng.uniform(-c["tool_yaw_error_rad"], c["tool_yaw_error_rad"])]
        if "initial_pose" in options:
            pose = np.asarray(options["initial_pose"], dtype=float)
            if pose.shape != (4,) or not np.isfinite(pose).all() or np.any(pose < e.limits[:, 0]) or np.any(pose > e.limits[:, 1]):
                raise ValueError("initial_pose must fit the four joint limits")
        e.data.qpos[e.qadr] = pose
        self.hold = 0
        self.force = 0.
        self.last_distance = self.distance()

    def distance(self):
        err = self.error()
        return float(np.linalg.norm(err[:2]) + abs(err[2]) + .02 * abs(err[3]))

    def observe(self):
        e = self.env
        return np.r_[e.data.qpos[e.qadr], e.data.qvel[e.vadr], e.target, self.error(), e.previous_action, self.force]

    def evaluate(self, force):
        e = self.env
        c = e.specification["success"]
        err = self.error()
        z = float(e.data.qpos[e.qadr[2]])
        speed = float(np.max(np.abs(e.data.qvel[e.vadr])))
        aligned = np.linalg.norm(err[:2]) < c["xy_tolerance_m"] and abs(err[3]) < c["yaw_tolerance_rad"]
        seated = c["tip_z_min_m"] <= z <= c["tip_z_max_m"]
        valid = aligned and seated and speed < c["speed_max"] and force < c["contact_force_max_n"]
        self.hold = self.hold + 1 if valid else 0
        self.force = force
        return {"is_success": self.hold >= c["hold_steps"], "xy_error_m": float(np.linalg.norm(err[:2])), "yaw_error_rad": float(abs(err[3])), "tip_z_m": z, "hold_steps": self.hold, "speed": speed}
