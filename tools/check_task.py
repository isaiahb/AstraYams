"""Check Gym contracts and physical positive/negative controls."""
from pathlib import Path
import argparse
import json
import numpy as np
from gymnasium.utils.env_checker import check_env
from astrafactory.env import FactoryEnv

P = Path(__file__).resolve().parents[1]


def teacher(env):
    q = env.data.qpos[env.qadr]
    goal = env.task.goal.copy()
    if np.linalg.norm(q[:2] - goal[:2]) > .00035 or abs(q[3] - goal[3]) > .025:
        goal[2] = .058
    return np.clip((goal - env.target) / env.scales, -.5, .5)


def rollout(env, seed, mode):
    obs, info = env.reset(seed=seed)
    for step in range(env.horizon):
        action = teacher(env) if mode == "teacher" else np.array([0, 0, -.5, 0]) if mode == "blind_descent" else np.zeros(4)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break
    return {"seed": seed, "mode": mode, "steps": step + 1, **info}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=str(P / "tasks/keyed_insertion"))
    parser.add_argument("--output", default=str(P / "runs/checks.json"))
    args = parser.parse_args()
    env = FactoryEnv(args.task)
    check_env(env, skip_render_check=True)
    a, _ = env.reset(seed=42)
    b, _ = env.reset(seed=42)
    assert np.array_equal(a, b)
    old = env.data.qpos.copy()
    try:
        env.step([float("nan")] * 4)
        raise AssertionError("Nonfinite action accepted")
    except ValueError:
        assert np.array_equal(old, env.data.qpos)
    results = [rollout(env, seed, mode) for mode in ["teacher", "hold", "blind_descent"] for seed in range(10)]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"gym_checker": "pass", "deterministic_reset": "pass", "invalid_action": "pass", "rollouts": results}, indent=2))
    for mode in ["teacher", "hold", "blind_descent"]:
        rows = [r for r in results if r["mode"] == mode]
        print(mode, sum(r["is_success"] for r in rows), "/", len(rows), "peak force", max(r["episode_peak_force_n"] for r in rows))
    assert all(r["is_success"] for r in results if r["mode"] == "teacher"), "Teacher did not establish feasibility"
    assert not any(r["is_success"] for r in results if r["mode"] == "hold"), "No-op falsely passed"
    env.close()
