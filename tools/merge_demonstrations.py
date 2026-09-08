"""Combine compatible demonstration manifests without duplicating episode arrays."""
from pathlib import Path
import argparse
import hashlib
import json
import os


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        p.error('Output directory must be empty')
    result, seen = None, set()
    for directory in args.data:
        path = directory / 'manifest.json'
        source = json.loads(path.read_text())
        if result is None:
            result = {k:v for k,v in source.items() if k not in ['episodes', 'learner_checkpoint', 'learner_checkpoint_sha256', 'action_noise_std', 'teacher_execution_probability']}
            result.update(episodes=[], sources=[])
        for key in ['task_hashes', 'env_class', 'env_source_sha256']:
            if source[key] != result[key]:
                raise ValueError(f'Incompatible {key}: {directory}')
        for row in source['episodes']:
            if row['seed'] in seen:
                raise ValueError(f'Duplicate seed across merged episodes: {row["seed"]}; use separate collection seed ranges')
            seen.add(row['seed'])
            result['episodes'].append({**row, 'file': os.path.relpath((directory / row['file']).resolve(), args.out.resolve())})
        result['sources'].append({'directory': str(directory.resolve()), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'teacher': source.get('teacher'), 'learner_checkpoint': source.get('learner_checkpoint'),
                                  'teacher_execution_probability': source.get('teacher_execution_probability'), 'action_noise_std': source.get('action_noise_std')})
    result['unique_initial_states'] = len({r['initial_state_sha256'] for r in result['episodes']})
    result['unique_state_action_trajectories'] = len({r['trajectory_sha256'] for r in result['episodes']})
    (args.out / 'manifest.json').write_text(json.dumps(result, indent=2))
    print('Merged episodes:', len(result['episodes']), flush=True)


if __name__ == '__main__':
    main()
