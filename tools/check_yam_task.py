"""Check articulated YAM Gym behavior and actual teacher/hold physics rollouts."""
from pathlib import Path
import argparse
import json
import numpy as np
from gymnasium.utils.env_checker import check_env
try:
    from .collect_demonstrations import task_hashes, environment_source_hash
except ImportError:
    from collect_demonstrations import task_hashes, environment_source_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    from astrafactory.yam_env import YamEnv, teacher
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', default=str(ROOT / 'tasks/yam_keyed_insertion'))
    p.add_argument('--episodes', type=int, default=5)
    p.add_argument('--seed-start', type=int, default=0)
    p.add_argument('--out', type=Path, default=ROOT / 'runs/yam-checks.json')
    args = p.parse_args()
    if args.episodes < 1:
        p.error('Need at least one episode')
    env = YamEnv(args.task)
    rows = []
    try:
        check_env(env, skip_render_check=True)
        first, _ = env.reset(seed=42)
        second, _ = env.reset(seed=42)
        assert np.array_equal(first, second), 'Seeded resets differ'
        q = env.data.qpos.copy()
        try:
            env.step(np.full(env.action_space.shape, np.nan))
            raise AssertionError('Nonfinite action was accepted')
        except ValueError:
            assert np.array_equal(q, env.data.qpos), 'Invalid action mutated state'
        for mode in ['teacher', 'hold']:
            for seed in range(args.seed_start, args.seed_start + args.episodes):
                obs, info = env.reset(seed=seed)
                initial_q = env.data.qpos[env.qadr].copy()
                total_reward, max_motion = 0., 0.
                for step in range(env.horizon):
                    before_teacher = env.data.qpos.copy()
                    action = teacher(env) if mode == 'teacher' else np.zeros(env.action_space.shape)
                    assert np.array_equal(before_teacher, env.data.qpos), 'Teacher modified physical joint state'
                    obs, reward, terminated, truncated, info = env.step(action)
                    max_motion = max(max_motion, float(np.max(np.abs(env.data.qpos[env.qadr]-initial_q))))
                    total_reward += reward
                    if terminated or truncated:
                        break
                rows.append({'mode': mode, 'seed': seed, 'steps': step+1, 'return': total_reward,
                             'max_joint_displacement_rad': max_motion, **info})
            subset = [r for r in rows if r['mode'] == mode]
            print(mode, sum(r['is_success'] for r in subset), '/', len(subset), flush=True)
        result = {'embodiment': 'articulated_yam', 'gym_checker': 'pass', 'deterministic_reset': 'pass',
                  'invalid_action': 'pass', 'task_hashes': task_hashes(args.task),
                  'env_source_sha256': environment_source_hash('astrafactory.yam_env:YamEnv'), 'teacher_does_not_assign_qpos': 'pass', 'rollouts': rows}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2))
        assert all(r['is_success'] for r in rows if r['mode'] == 'teacher'), 'Teacher failed to establish articulated-arm feasibility; see saved results'
        assert not any(r['is_success'] for r in rows if r['mode'] == 'hold'), 'Hold control falsely succeeded'
        assert all(r['max_joint_displacement_rad'] > 1e-3 for r in rows if r['mode'] == 'teacher'), 'Arm did not move'
    finally:
        env.close()


if __name__ == '__main__':
    main()
