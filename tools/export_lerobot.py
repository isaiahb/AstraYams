"""Export one synchronized NPZ split to a local LeRobot image dataset; no upload."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_episode(path, record, fps):
    if sha256(path) != record['sha256']:
        raise ValueError(f'Checksum mismatch: {path.name}')
    with np.load(path, allow_pickle=False) as data:
        count = int(record['steps'])
        for key, shape in {'image': (count, 240, 320, 3),
                           'proprioception': (count, 28), 'teacher_action': (count, 7)}.items():
            if data[key].shape != shape:
                raise ValueError(f'{path.name}: {key} shape mismatch')
        if data['image'].dtype != np.uint8:
            raise ValueError('RGB must be uint8')
        for key in ('proprioception', 'teacher_action'):
            if data[key].dtype != np.float32 or not np.isfinite(data[key]).all():
                raise ValueError(f'{key} must be finite float32')
        if np.max(np.abs(data['teacher_action'])) > 1.00001:
            raise ValueError('Actions exceed normalized bounds')
        if count > 1 and not np.allclose(np.diff(data['sim_time']), 1 / fps, atol=1e-5):
            raise ValueError('Simulation timestamps disagree with fps')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--repo-id', default='astrafactory/yam-contact-train')
    p.add_argument('--split', choices=['train', 'development'], default='train')
    p.add_argument('--expected-episodes', type=int, required=True)
    p.add_argument('--fps', type=int, default=50)
    p.add_argument('--task-text', default='Pick up the keyed peg and insert it into the matching socket.')
    args = p.parse_args()
    if args.out.exists():
        p.error('Output must not exist; refusing mixed datasets or overwrite')
    manifest_bytes = (args.source / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    if not manifest.get('camera'):
        raise ValueError('Source lacks synchronized camera data')
    records = [r for r in manifest['episodes'] if r['split'] == args.split]
    if len(records) != args.expected_episodes or not records:
        raise ValueError(f'Expected {args.expected_episodes} episodes, found {len(records)}')
    selected = {r['seed'] for r in records}
    others = {r['seed'] for r in manifest['episodes'] if r['split'] != args.split}
    if selected & others or len(selected) != len(records):
        raise ValueError('Duplicate or overlapping seeds')
    for r in records:
        path = (args.source / r['file']).resolve()
        if not path.is_relative_to(args.source.resolve()):
            raise ValueError('Episode path escapes source')
        validate_episode(path, r, args.fps)

    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from torch.utils.data import DataLoader
    import torch
    features = {
        'observation.images.overview': {'dtype': 'image', 'shape': (240, 320, 3),
                                        'names': ['height', 'width', 'channels']},
        'observation.state': {'dtype': 'float32', 'shape': (28,),
            'names': [f'{k}_{i + 1}' for k in ('q', 'qvel', 'target', 'previous_action') for i in range(7)]},
        'action': {'dtype': 'float32', 'shape': (7,),
                   'names': [f'joint{i + 1}_target_increment' for i in range(7)]},
    }
    ds = LeRobotDataset.create(repo_id=args.repo_id, root=args.out, fps=args.fps,
        features=features, robot_type='yam_contact_simulation', use_videos=False,
        image_writer_threads=4)
    mapping = []
    for index, r in enumerate(records):
        with np.load(args.source / r['file'], allow_pickle=False) as data:
            for image, state, action in zip(data['image'], data['proprioception'], data['teacher_action'], strict=True):
                ds.add_frame({'observation.images.overview': image, 'observation.state': state,
                              'action': action, 'task': args.task_text})
        ds.save_episode()
        mapping.append({'lerobot_episode_index': index, **r})
        print(f'Exported {args.split} {index + 1}/{len(records)} seed={r["seed"]}', flush=True)
    ds.finalize()
    batch = next(iter(DataLoader(ds, batch_size=2, num_workers=0)))
    assert batch['observation.state'].shape[1:] == (28,)
    assert batch['action'].shape[1:] == (7,)
    assert batch['observation.images.overview'].shape[1:] == (3, 240, 320)
    assert torch.isfinite(batch['observation.state']).all()
    assert batch['observation.images.overview'].min() >= 0
    assert batch['observation.images.overview'].max() <= 1
    with np.load(args.source / records[0]['file'], allow_pickle=False) as first:
        assert np.allclose(batch['observation.state'][0].numpy(), first['proprioception'][0])
        assert np.allclose(batch['action'][0].numpy(), first['teacher_action'][0])
        assert np.allclose(batch['observation.images.overview'][0].numpy(),
                           first['image'][0].transpose(2, 0, 1) / 255.0, atol=1e-7)
    audit = {'source_manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
             'source_manifest_snapshot': manifest, 'split': args.split, 'episode_mapping': mapping,
             'label': 'teacher_action', 'policy_features': list(features), 'task_text': args.task_text,
             'fps': args.fps, 'frames': sum(r['steps'] for r in records),
             'smoke_batch_shapes': {k: list(v.shape) for k, v in batch.items() if isinstance(v, torch.Tensor)},
             'pixel_state_action_roundtrip': True, 'hub_upload': False}
    (args.out / 'meta' / 'source_provenance.json').write_text(json.dumps(audit, indent=2))
    files = [f for f in args.out.rglob('*') if f.is_file()]
    (args.out / 'meta' / 'export_checksums.json').write_text(json.dumps({
        str(f.relative_to(args.out)): sha256(f) for f in sorted(files)}, indent=2))
    print(json.dumps({'root': str(args.out), 'episodes': len(records),
                      'frames': audit['frames'], 'batch': audit['smoke_batch_shapes']}), flush=True)


if __name__ == '__main__':
    main()
