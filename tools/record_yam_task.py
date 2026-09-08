"""Record an actual physics-driven YAM teacher or learned-state-policy rollout."""
from pathlib import Path
import argparse
import json
import numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    from astrafactory.yam_env import YamEnv, teacher
    try:
        from .collect_demonstrations import task_hashes, environment_source_hash
        from .finetune_skill import StatePolicy, predict
    except ImportError:
        from collect_demonstrations import task_hashes, environment_source_hash
        from finetune_skill import StatePolicy, predict
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', default=str(ROOT / 'tasks/yam_keyed_insertion'))
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--mode', choices=['teacher', 'hold', 'learned'], default='teacher')
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--out', type=Path, default=ROOT / 'runs/yam-recording')
    p.add_argument('--every', type=int, default=2, help='Control steps per video frame')
    args = p.parse_args()
    if args.every < 1:
        p.error('--every must be positive')
    if args.mode == 'learned' and args.checkpoint is None:
        p.error('Learned mode requires --checkpoint')
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        p.error('Output directory must be empty')
    env = YamEnv(args.task, render_mode='rgb_array')
    hashes = task_hashes(args.task)
    env_hash = environment_source_hash('astrafactory.yam_env:YamEnv')
    if args.mode == 'learned':
        import torch
        torch.set_num_threads(2)
        ckpt = torch.load(args.checkpoint, map_location='cpu', weights_only=False)
        if ckpt['task_hashes'] != hashes or ckpt.get('env_class') != 'astrafactory.yam_env:YamEnv' or ckpt.get('env_source_sha256', env_hash) != env_hash:
            raise ValueError('Checkpoint does not match current YAM task')
        model = StatePolicy(**ckpt['config'])
        model.load_state_dict(ckpt['model'])
        model.eval()
    label = {'teacher': 'Scripted IK teacher', 'hold': 'Hold control', 'learned': 'Learned privileged-state policy'}[args.mode]
    fps = 1 / (env.model.opt.timestep * env.frame_skip * args.every)
    transitions = {k: [] for k in ['state', 'action', 'next_state', 'reward', 'terminated', 'truncated']}
    frames = []
    try:
        obs, info = env.reset(seed=args.seed)
        with imageio.get_writer(args.out / f'{args.mode}.mp4', fps=fps, codec='libx264', quality=8) as writer:
            for step in range(env.horizon):
                if args.mode == 'teacher':
                    action = teacher(env)
                elif args.mode == 'learned':
                    action = predict(model, obs, ckpt['mean'], ckpt['std'])
                else:
                    action = np.zeros(env.action_space.shape)
                transitions['state'].append(obs.copy())
                transitions['action'].append(np.asarray(action).copy())
                obs, reward, terminated, truncated, info = env.step(action)
                for key, value in [('next_state', obs.copy()), ('reward', reward), ('terminated', terminated), ('truncated', truncated)]:
                    transitions[key].append(value)
                frames.append({'step': step+1, 'qpos': env.data.qpos.tolist(), 'qvel': env.data.qvel.tolist(),
                               'ctrl': env.data.ctrl.tolist(), **info})
                if step % args.every == 0 or terminated or truncated:
                    image = Image.fromarray(env.render())
                    draw = ImageDraw.Draw(image)
                    width = image.width
                    draw.rectangle((0, 0, width, 76), fill=(18, 27, 37))
                    draw.text((18, 10), f'ASTRAFACTORY  |  YAM ARM  |  {label}', fill='white', font_size=20)
                    draw.text((18, 42), f"Seed {args.seed}   t={info.get('sim_time', env.data.time):.2f}s   XY {1000*info.get('xy_error_m',0):.2f} mm   Peak contact {info.get('episode_peak_force_n',0):.2f} N", fill=(194,218,231), font_size=17)
                    writer.append_data(np.asarray(image))
                    if step == 0:
                        image.save(args.out / 'start.png')
                    if terminated or truncated:
                        image.save(args.out / 'end.png')
                if terminated or truncated:
                    break
        np.savez_compressed(args.out / 'transitions.npz', **{k: np.asarray(v) for k,v in transitions.items()})
        (args.out / 'states.json').write_text(json.dumps(frames))
        report = {'embodiment': 'articulated_yam', 'policy': label, 'seed': args.seed, 'steps': step+1,
                  'checkpoint': str(args.checkpoint) if args.checkpoint else None, 'task_hashes': hashes, 'env_source_sha256': env_hash,
                  'video_alignment': 'post-step frames; transitions state is pre-action', **info}
        (args.out / 'result.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()
