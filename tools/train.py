"""Task-independent PPO entry point; smoke runs are not learned-success claims."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from astrafactory.env import FactoryEnv

P = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--task", default=str(P / "tasks/keyed_insertion"))
parser.add_argument("--steps", type=int, default=10000)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--out", default=str(P / "runs/ppo"))
parser.add_argument("--resume", help="Existing PPO checkpoint to continue training")
args = parser.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
torch.set_num_threads(2)
env = Monitor(FactoryEnv(args.task), filename=str(out / "monitor"))
model = PPO.load(args.resume, env=env, device="cpu") if args.resume else PPO("MlpPolicy", env, n_steps=256, batch_size=64, n_epochs=5, policy_kwargs={"net_arch": [64, 64]}, seed=args.seed, verbose=1, device="cpu")
start = time.time()
model.learn(total_timesteps=args.steps, reset_num_timesteps=not bool(args.resume))
model.save(out / "policy")
rows = []
evaluation = FactoryEnv(args.task)
for seed in range(1000, 1010):
    obs, info = evaluation.reset(seed=seed)
    for _ in range(evaluation.horizon):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = evaluation.step(action)
        if terminated or truncated:
            break
    rows.append({"seed": seed, **info})
task = Path(args.task)
hashes = {str(f.relative_to(task)): hashlib.sha256(f.read_bytes()).hexdigest() for f in task.rglob("*") if f.is_file() and "__pycache__" not in f.parts}
(out / "report.json").write_text(json.dumps({"elapsed_seconds": time.time()-start, "timesteps": model.num_timesteps, "task_hashes": hashes, "evaluation": rows, "successes": sum(r["is_success"] for r in rows), "episodes": len(rows)}, indent=2))
evaluation.close()
env.close()
