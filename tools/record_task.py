"""Record actual physics controls, observations and video for task inspection."""
from pathlib import Path
import argparse
import json
import numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageDraw
from astrafactory.env import FactoryEnv
from check_task import teacher

P = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--task", default=str(P / "tasks/keyed_insertion"))
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--out", default=str(P / "runs/inspection"))
args = parser.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
env = FactoryEnv(args.task, render_mode="rgb_array")
results = []
for mode in ["blind_descent", "teacher"]:
    obs, info = env.reset(seed=args.seed)
    states, observations, actions = [], [], []
    with imageio.get_writer(out / f"{mode}.mp4", fps=25, codec="libx264", quality=8) as writer:
        for step in range(env.horizon):
            action = teacher(env) if mode == "teacher" else np.array([0, 0, -.5, 0])
            observations.append(obs.copy())
            actions.append(action.copy())
            obs, reward, terminated, truncated, info = env.step(action)
            states.append({"qpos": env.data.qpos.tolist(), "qvel": env.data.qvel.tolist(), "ctrl": env.data.ctrl.tolist(), **info})
            if step % 2 == 0 or terminated or truncated:
                image = Image.fromarray(env.render())
                draw = ImageDraw.Draw(image)
                draw.rectangle((0, 0, 960, 70), fill=(18, 27, 37))
                draw.text((20, 12), f"AstraFactory | Custom keyed insertion | {mode} (scripted, not learned)", fill="white", font_size=20)
                draw.text((20, 42), f"Held-tool fixture | t={info['sim_time']:.2f}s | XY error {1000*info['xy_error_m']:.1f} mm | peak force {info['episode_peak_force_n']:.1f} N", fill="white", font_size=18)
                writer.append_data(np.asarray(image))
                if step == 0:
                    image.save(out / f"{mode}-start.png")
                if terminated or truncated:
                    image.save(out / f"{mode}-end.png")
            if terminated or truncated:
                break
    np.savez_compressed(out / f"{mode}-transitions.npz", observations=observations, actions=actions, final_observation=obs)
    (out / f"{mode}-states.json").write_text(json.dumps(states))
    results.append({"mode": mode, "seed": args.seed, **info})
    print(results[-1], flush=True)
(out / "results.json").write_text(json.dumps(results, indent=2))
env.close()
