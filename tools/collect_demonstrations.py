"""Collect episode-separated, synchronized scripted-teacher demonstrations."""
from pathlib import Path
import argparse
import hashlib
import importlib
import inspect
import json
import os
import xml.etree.ElementTree as ET
import numpy as np
from astrafactory.observations import CameraObservation

ROOT = Path(__file__).resolve().parents[1]


def load_callable(reference):
    module, name = reference.split(":", 1)
    return getattr(importlib.import_module(module), name)


def environment_source_hash(reference):
    return hashlib.sha256(Path(inspect.getfile(load_callable(reference))).read_bytes()).hexdigest()


def task_hashes(task):
    """Hash package files and referenced MJCF assets, including external robot meshes."""
    task = Path(task).resolve()
    files = {p.resolve() for p in task.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    pending = [p for p in files if p.suffix == '.xml']
    parsed = set()
    while pending:
        xml = pending.pop()
        if xml in parsed:
            continue
        parsed.add(xml)
        root = ET.parse(xml).getroot()
        compiler = root.find('compiler')
        settings = compiler.attrib if compiler is not None else {}
        for node in root.iter():
            name = node.get('file')
            if not name:
                continue
            prefix = settings.get('meshdir', settings.get('assetdir', '')) if node.tag == 'mesh' else settings.get('texturedir', settings.get('assetdir', '')) if node.tag == 'texture' else ''
            asset = (xml.parent / prefix / name).resolve()
            if asset.is_file():
                files.add(asset)
                if asset.suffix == '.xml':
                    pending.append(asset)
    return {os.path.relpath(p, task): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', default=str(ROOT / 'tasks/keyed_insertion'))
    p.add_argument('--env-class', default='astrafactory.env:FactoryEnv', help='Importable module:class accepting a task path')
    p.add_argument('--teacher', default='check_task:teacher', help='Importable module:function(env); default is keyed-insertion-specific, privileged scripted teacher')
    p.add_argument('--out', default=str(ROOT / 'runs/demonstrations'))
    p.add_argument('--train-episodes', type=int, default=64)
    p.add_argument('--development-episodes', type=int, default=16)
    p.add_argument('--train-seed-start', type=int, default=100)
    p.add_argument('--development-seed-start', type=int, default=1000)
    p.add_argument('--camera', action='store_true', help='Save synchronized pre-action RGB and proprioception (large files)')
    args = p.parse_args()
    if min(args.train_episodes, args.development_episodes) < 1:
        p.error('Both episode counts must be positive')
    splits = {'train': list(range(args.train_seed_start, args.train_seed_start + args.train_episodes)),
              'development': list(range(args.development_seed_start, args.development_seed_start + args.development_episodes))}
    if set(splits['train']) & set(splits['development']):
        p.error('Training and development seeds must be disjoint')
    if any(s < 0 or s >= 5000 for seeds in splits.values() for s in seeds):
        p.error('Seeds must be nonnegative; 5000+ are reserved for final evaluation')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        p.error('Output directory must be empty to prevent accidental mixed datasets')
    teacher = load_callable(args.teacher)
    env = load_callable(args.env_class)(args.task)
    camera = CameraObservation(env) if args.camera else None
    manifest = {'schema_version': 1, 'env_class': args.env_class, 'teacher': args.teacher, 'policy_kind': 'scripted_privileged_teacher',
                'task': str(Path(args.task).resolve()), 'task_hashes': task_hashes(args.task),
                'env_source_sha256': environment_source_hash(args.env_class),
                'alignment': 'state[t], image[t], proprioception[t] precede action[t]; next_state[t] follows action[t]',
                'camera': args.camera, 'teacher_source_sha256': hashlib.sha256(inspect.getsource(teacher).encode()).hexdigest(), 'episodes': []}
    try:
        for split, seeds in splits.items():
            (out / split).mkdir()
            for seed in seeds:
                obs, info = env.reset(seed=seed)
                data = {k: [] for k in ['state', 'action', 'next_state', 'reward', 'terminated', 'truncated', 'sim_time']}
                if camera:
                    data.update(image=[], proprioception=[])
                for step in range(env.horizon):
                    data['state'].append(obs.copy())
                    data['sim_time'].append(float(env.data.time))
                    if camera:
                        frame = camera.observation(obs)
                        for key in ['image', 'proprioception']:
                            data[key].append(frame[key])
                    action = np.asarray(teacher(env), dtype=np.float32)
                    obs, reward, terminated, truncated, info = env.step(action)
                    for key, value in [('action', action), ('next_state', obs.copy()), ('reward', reward), ('terminated', terminated), ('truncated', truncated)]:
                        data[key].append(value)
                    if terminated or truncated:
                        break
                path = f'{split}/episode_{seed}.npz'
                np.savez_compressed(out / path, **{k: np.asarray(v) for k, v in data.items()})
                manifest['episodes'].append({'split': split, 'seed': seed, 'file': path, 'steps': step + 1, 'sha256': hashlib.sha256((out / path).read_bytes()).hexdigest(), **info})
                (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            rows = [r for r in manifest['episodes'] if r['split'] == split]
            print(split, sum(r['is_success'] for r in rows), '/', len(rows), flush=True)
    finally:
        (camera or env).close()


if __name__ == '__main__':
    main()
