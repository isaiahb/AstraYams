"""Privileged state behavioral cloning; resume supervised fine-tuning, independent rollouts."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import numpy as np
import torch
from torch import nn
try:
    from .collect_demonstrations import task_hashes, ROOT, load_callable, environment_source_hash
except ImportError:  # Direct execution as python tools/finetune_skill.py.
    from collect_demonstrations import task_hashes, ROOT, load_callable, environment_source_hash


class StatePolicy(nn.Module):
    def __init__(self, observation_size, action_size, width=128, activation='tanh', history_steps=1, output_scales=None, action_clip_scales=None):
        super().__init__()
        self.history_steps = history_steps
        self.output_scales = output_scales
        self.action_clip_scales = action_clip_scales
        self.reset_history()
        nonlinearity = {'tanh': nn.Tanh, 'relu': nn.ReLU}[activation]
        self.network = nn.Sequential(nn.Linear(observation_size * history_steps, width), nonlinearity(),
                                     nn.Linear(width, width), nonlinearity(), nn.Linear(width, action_size))

    def reset_history(self):
        self.observation_history = []

    def forward(self, x):
        output = self.network(x)
        return torch.tanh(output) * output.new_tensor(self.output_scales) if self.output_scales is not None else output


def predict(model, observation, mean, std):
    normalized = np.asarray((observation - mean) / std, dtype=np.float32)
    if not model.observation_history:
        model.observation_history = [normalized.copy() for _ in range(model.history_steps)]
    else:
        model.observation_history.append(normalized.copy())
        model.observation_history = model.observation_history[-model.history_steps:]
    with torch.no_grad():
        output = model(torch.as_tensor(np.asarray(model.observation_history).reshape(-1), dtype=torch.float32)).numpy()
        bounds = np.asarray(model.action_clip_scales) if model.action_clip_scales is not None else 1.
        return np.clip(output, -bounds, bounds)


def load_split(directory, manifest, split, history_steps=1):
    states, actions = [], []
    for episode in manifest['episodes']:
        if episode['split'] == split:
            path = directory / episode['file']
            if episode.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest() != episode['sha256']:
                raise ValueError(f'Dataset checksum mismatch: {path}')
            with np.load(path) as data:
                state = data['state']
                padded = np.concatenate([np.repeat(state[:1], history_steps-1, axis=0), state])
                windows = np.lib.stride_tricks.sliding_window_view(padded, history_steps, axis=0).transpose(0,2,1)
                states.append(windows)
                actions.append(data['teacher_action'] if 'teacher_action' in data else data['action'])
    if not states:
        raise ValueError(f'No {split} episodes')
    return np.concatenate(states), np.concatenate(actions)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', default=str(ROOT / 'tasks/keyed_insertion'))
    p.add_argument('--env-class', default='astrafactory.env:FactoryEnv', help='Importable module:class accepting a task path')
    p.add_argument('--data', type=Path)
    p.add_argument('--out', type=Path, default=ROOT / 'runs/state-bc')
    p.add_argument('--resume', type=Path)
    p.add_argument('--epochs', type=int, default=150)
    p.add_argument('--batch-size', type=int, default=256)
    p.add_argument('--learning-rate', type=float, default=0.001)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--output-scales', type=float, nargs='+', help='Explicit tanh output scales, one per action; may initialize a bounded resume')
    p.add_argument('--action-clip-scales', type=float, nargs='+', help='Explicit post-model clipping for a baseline comparison')
    p.add_argument('--history-steps', type=int, default=1, help='Number of past/current observations; never includes teacher phase')
    p.add_argument('--width', type=int, default=128, help='Hidden width for a new model; resume restores saved architecture')
    p.add_argument('--activation', choices=['tanh', 'relu'], default='tanh')
    p.add_argument('--eval-only', action='store_true')
    p.add_argument('--eval-seed-start', type=int, default=2000)
    p.add_argument('--eval-episodes', type=int, default=20)
    args = p.parse_args()
    if args.eval_episodes < 1 or args.batch_size < 1 or args.epochs < 0 or args.history_steps < 1 or args.width < 1:
        p.error('Invalid counts')
    if args.eval_only and not args.resume:
        p.error('--eval-only requires --resume')
    if not args.eval_only and not args.data:
        p.error('Training requires --data')
    if not args.eval_only and args.eval_seed_start + args.eval_episodes > 5000:
        p.error('Final seeds 5000+ may only be used with --eval-only')
    torch.set_num_threads(2)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        p.error('Output directory must be empty; use a new run directory')
    if args.eval_seed_start < 0 or args.eval_seed_start < 5000 < args.eval_seed_start + args.eval_episodes:
        p.error('Evaluation seed range must be nonnegative and cannot mix development and final seeds')
    hashes = task_hashes(args.task)
    env_hash = environment_source_hash(args.env_class)
    env = load_callable(args.env_class)(args.task)
    config = {'observation_size': env.observation_space.shape[0], 'action_size': env.action_space.shape[0], 'width': args.width, 'activation': args.activation, 'history_steps': args.history_steps}
    checkpoint = torch.load(args.resume, map_location='cpu', weights_only=False) if args.resume else None
    if checkpoint:
        if any(checkpoint['config'][key] != config[key] for key in ['observation_size', 'action_size']):
            raise ValueError('Checkpoint observation/action dimensions differ')
        config = dict(checkpoint['config'])
    for key in ['output_scales', 'action_clip_scales']:
        values = getattr(args, key)
        if values is not None:
            if len(values) != config['action_size'] or any(not np.isfinite(v) or v <= 0 or v > 1 for v in values):
                p.error('Output bounds must contain one finite positive scale <=1 per action')
            config[key] = values
    if checkpoint and (checkpoint['task_hashes'] != hashes or checkpoint.get('env_class', 'astrafactory.env:FactoryEnv') != args.env_class or checkpoint.get('env_source_sha256', env_hash) != env_hash):
        raise ValueError('Checkpoint task or observation/action contract differs')
    model = StatePolicy(**config)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    seen_seeds = set(checkpoint['training_seeds']) if checkpoint else set()
    development_seeds = set(checkpoint['development_seeds']) if checkpoint else set()
    history, epoch_start = [], 0
    data_history = list(checkpoint.get('data_history', [])) if checkpoint else []
    evaluation_seeds = list(range(args.eval_seed_start, args.eval_seed_start + args.eval_episodes))
    if checkpoint:
        model.load_state_dict(checkpoint['model'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        mean, std = checkpoint['mean'], checkpoint['std']
        epoch_start = checkpoint['epochs']
        torch.set_rng_state(checkpoint['torch_rng_state'])
        for group in optimizer.param_groups:
            group['lr'] = args.learning_rate
    if not args.eval_only:
        manifest = json.loads((args.data / 'manifest.json').read_text())
        if manifest['task_hashes'] != hashes or manifest.get('env_class', 'astrafactory.env:FactoryEnv') != args.env_class or manifest.get('env_source_sha256', env_hash) != env_hash:
            raise ValueError('Dataset task hashes differ from current task')
        new_train = {r['seed'] for r in manifest['episodes'] if r['split'] == 'train'}
        new_dev = {r['seed'] for r in manifest['episodes'] if r['split'] == 'development'}
        if (new_train | seen_seeds) & (new_dev | development_seeds):
            raise ValueError('Training/development episode leakage')
        seen_seeds |= new_train
        development_seeds |= new_dev
        if any(s < 0 or s >= 5000 for s in seen_seeds | development_seeds):
            raise ValueError('Demonstrations must not contain reserved final evaluation seeds')
        if set(evaluation_seeds) & (seen_seeds | development_seeds):
            raise ValueError('Rollout evaluation seeds overlap demonstration seeds')
        data_history.append({'directory': str(args.data.resolve()), 'manifest_sha256': hashlib.sha256((args.data / 'manifest.json').read_bytes()).hexdigest(), 'epochs': args.epochs,
                             'unique_initial_states': manifest.get('unique_initial_states'),
                             'unique_state_action_trajectories': manifest.get('unique_state_action_trajectories'),
                             'action_noise_std': manifest.get('action_noise_std', 0.),
                             'teacher': manifest.get('teacher')})
        x, y = load_split(args.data, manifest, 'train', config.get('history_steps', 1))
        dx, dy = load_split(args.data, manifest, 'development', config.get('history_steps', 1))
        if checkpoint is None:
            mean, std = x.mean(axis=(0,1)), np.maximum(x.std(axis=(0,1)), 1e-4)
        x, y = torch.tensor(((x-mean)/std).reshape(len(x), -1), dtype=torch.float32), torch.tensor(y, dtype=torch.float32)
        dx, dy = torch.tensor(((dx-mean)/std).reshape(len(dx), -1), dtype=torch.float32), torch.tensor(dy, dtype=torch.float32)
        for epoch in range(args.epochs):
            model.train()
            order = torch.randperm(len(x))
            losses = []
            for indices in order.split(args.batch_size):
                loss = nn.functional.mse_loss(model(x[indices]), y[indices])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(loss.item())
            model.eval()
            with torch.no_grad():
                dev_loss = nn.functional.mse_loss(model(dx), dy).item()
            history.append({'epoch': epoch_start + epoch + 1, 'train_mse': float(np.mean(losses)), 'development_mse': dev_loss})
            if (epoch+1) % 25 == 0:
                print(history[-1], flush=True)
        torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'config': config,
                    'mean': mean, 'std': std, 'epochs': epoch_start + args.epochs,
                    'task_hashes': hashes, 'env_class': args.env_class, 'env_source_sha256': env_hash, 'training_seeds': sorted(seen_seeds),
                    'development_seeds': sorted(development_seeds), 'torch_rng_state': torch.get_rng_state(),
                    'policy_kind': 'privileged_state_behavioral_cloning', 'seed': args.seed, 'data_history': data_history}, args.out / 'policy.pt')
    evaluation_seeds = list(range(args.eval_seed_start, args.eval_seed_start + args.eval_episodes))
    if set(evaluation_seeds) & (seen_seeds | development_seeds):
        raise ValueError('Rollout evaluation must use independent seeds, absent from demonstration splits')
    rows = []
    model.eval()
    try:
        for seed in evaluation_seeds:
            obs, info = env.reset(seed=seed)
            model.reset_history()
            initial_hash = hashlib.sha256(np.asarray(obs).tobytes()).hexdigest()
            total_reward = 0.
            for step in range(env.horizon):
                action = predict(model, obs, mean, std)
                obs, reward, terminated, truncated, info = env.step(action)
                total_reward += reward
                if terminated or truncated:
                    break
            rows.append({'seed': seed, 'initial_state_sha256': initial_hash, 'steps': step+1, 'return': total_reward, **info})
    finally:
        env.close()
    report = {'policy_kind': 'privileged_state_behavioral_cloning', 'task_hashes': hashes, 'env_class': args.env_class, 'env_source_sha256': env_hash,
              'resume': str(args.resume) if args.resume else None, 'epochs': epoch_start + (0 if args.eval_only else args.epochs),
              'training_seed': args.seed, 'model_config': config, 'batch_size': args.batch_size, 'learning_rate': args.learning_rate,
              'data_history': data_history, 'torch_version': torch.__version__, 'numpy_version': np.__version__,
              'training_seeds': sorted(seen_seeds), 'development_seeds': sorted(development_seeds),
              'evaluation_role': 'final' if min(evaluation_seeds) >= 5000 else 'development',
              'reset_configuration': env.specification.get('reset'), 'curriculum_configuration': env.specification.get('curriculum'),
              'evaluation_scope': 'fixed_setup_repeatability_not_heldout_generalization' if env.specification.get('reset', {}).get('type') == 'fixed_pregrasp' and not env.specification.get('curriculum') else 'seed_disjoint_reset_rollouts',
              'unique_evaluation_initial_states': len({r['initial_state_sha256'] for r in rows}),
              'history': history, 'evaluation': rows, 'successes': sum(r['is_success'] for r in rows), 'episodes': len(rows)}
    (args.out / 'report.json').write_text(json.dumps(report, indent=2))
    print('Learned policy:', report['successes'], '/', len(rows), flush=True)


if __name__ == '__main__':
    main()
