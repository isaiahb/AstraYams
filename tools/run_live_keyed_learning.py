"""Fresh, bounded behavioral-cloning loop with continuous physical chain evaluation.

Prepared teacher data is reused; results and trained weights are always new.
This is privileged-state imitation with explicit target/guard/IK scaffolding.
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import mujoco
import numpy as np
import torch
import trimesh
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_downstream_skills import DownstreamSkill
from astrafactory.contact_downstream_skills_v3 import CorrectedInsertSkill
from check_yam_contact import physical_state, model_checks
from collect_demonstrations import task_hashes

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ('Fresh privileged-state behavioral cloning of acquisition/lift XYZ and jaw; '
         'frozen learned alignment/insertion, scripted targets, angular stabilization, guards and IK. '
         'Continuous free-body contact simulation; no hardware validation.')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def save_policy(skill, path):
    torch.save({'models': {k: v.state_dict() for k, v in skill.models.items()},
                'scope': SCOPE, 'initialization_seed': 31}, path)


def geometry(env, out):
    objects = []
    mesh_dir = out / 'meshes'
    mesh_dir.mkdir()
    m = env.model
    for i in range(m.ngeom):
        body = m.body(int(m.geom_bodyid[i])).name
        if body not in ('socket', 'free_peg'):
            continue
        if m.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH:
            mid = m.geom_dataid[i]
            va, vn = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
            fa, fn = m.mesh_faceadr[mid], m.mesh_facenum[mid]
            mesh = trimesh.Trimesh(m.mesh_vert[va:va+vn].copy(), m.mesh_face[fa:fa+fn].copy(), process=False)
        elif m.geom_type[i] == mujoco.mjtGeom.mjGEOM_BOX:
            mesh = trimesh.creation.box(extents=m.geom_size[i]*2)
        else:
            raise ValueError('Unsupported task geometry')
        path = mesh_dir / f'{m.geom(i).name}.stl'
        mesh.export(path)
        objects.append({'name': m.geom(i).name, 'body': body, 'mesh_path': str(path),
                        'color': 0xD79D58 if body == 'free_peg' else 0x518F91,
                        'local_position': m.geom_pos[i].tolist(),
                        'local_quaternion': m.geom_quat[i][[1, 2, 3, 0]].tolist(), 'scale': [1, 1, 1]})
    return objects


def evaluate(a, checkpoint, mode, emit, objects):
    trials = []
    for split, seeds in [('development', a.dev_seeds), ('holdout', a.holdout_seeds)]:
        for seed in seeds:
            started = time.monotonic()
            env = CurriculumEnv(a.task)
            env.reset(seed=seed)
            checks = model_checks(env)
            if not checks['passed']:
                raise RuntimeError('Physical model checks failed')
            skills = {'grasp': MicroGrasp(checkpoint), 'align': DownstreamSkill(a.align, 'align'),
                      'insert': CorrectedInsertSkill(a.insert)}
            phase = 'grasp'
            skills[phase].start(env)
            rows, actions, states, frames, handoffs = [], [], [], [], []
            error = None
            info = {}
            try:
                for step in range(env.horizon):
                    before = env.data.qpos.copy()
                    action = skills[phase].act(env)
                    if not np.array_equal(before, env.data.qpos):
                        raise RuntimeError('Policy changed physical state outside env.step')
                    _, _, done, truncated, info = env.step(action)
                    state = physical_state(env)
                    rows.append({'step': step+1, 'phase': phase, **info, **state})
                    actions.append(action.copy())
                    states.append(env.data.qpos.copy())
                    bodies = {env.model.body(i).name: {'position': env.data.xpos[i].tolist(),
                              'quaternion': env.data.xquat[i][[1, 2, 3, 0]].tolist()}
                              for i in range(env.model.nbody) if env.model.body(i).name}
                    frames.append({'time': float(env.data.time), 'phase': phase, 'bodies': bodies,
                                   'is_success': bool(info.get('is_success', False))})
                    ready = skills[phase].handoff(env) if phase == 'grasp' else skills[phase].handoff(env, info)
                    if ready and phase != 'insert':
                        old = phase
                        phase = 'align' if phase == 'grasp' else 'insert'
                        skills[phase].start(env)
                        handoffs.append({'from': old, 'to': phase, 'step': step+1})
                    if done or truncated:
                        break
            except Exception as exc:
                error = repr(exc)
            prefix = a.out / f'{mode}-{seed}'
            np.savez_compressed(str(prefix)+'.npz', actions=np.asarray(actions), qpos=np.asarray(states), seed=seed)
            write(Path(str(prefix)+'-trace.json'), rows)
            result = {'seed': seed, 'split': split, 'success': bool(info.get('is_success', False)) and error is None,
                      'steps': len(rows), 'sim_seconds': float(env.data.time), 'wall_seconds': time.monotonic()-started,
                      'final_phase': phase, 'final': info, 'error': error, 'handoffs': handoffs,
                      'state_path': str(prefix)+'.npz', 'model_checks': checks}
            replay = {'schema_version': 1, 'coordinate_system': 'right-handed Z-up', 'units': 'metres',
                      'label': 'recorded_physics', 'frames': frames, 'objects': objects, 'fps': 50,
                      'source_sha256': sha(str(prefix)+'.npz'), 'trace_sha256': sha(str(prefix)+'-trace.json'),
                      'scene_sha256': sha(a.task/'scene.xml'), 'seed': seed, 'mode': mode, 'outcome': result,
                      'camera': {'target': [.25, 0, .16], 'position': [.85, -.72, .57]}, 'scope': SCOPE,
                      'state_provenance': 'Body transforms and qpos sampled directly after each executed env.step; no pose synthesis or playback speed change.'}
            replay_path = Path(str(prefix)+'-cad-replay.json')
            replay_path.write_text(json.dumps(replay, separators=(',', ':')))
            result['replay_path'] = str(replay_path)
            trials.append(result)
            env.close()
            emit('evaluating', mode=mode, **{k: result[k] for k in ('seed', 'split', 'success', 'steps', 'final_phase')})
    return trials


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--task', type=Path, default=ROOT/'tasks/yam_contact_curriculum')
    p.add_argument('--data', type=Path, default=ROOT/'runs/micro-grasp-v1')
    p.add_argument('--align', type=Path, default=ROOT/'runs/downstream-v2-dr/align.npz')
    p.add_argument('--insert', type=Path, default=ROOT/'runs/downstream-v3-corrected/linear.npz')
    p.add_argument('--dev-seeds', type=int, nargs=3, default=[4600, 4601, 4602])
    p.add_argument('--holdout-seeds', type=int, nargs=3, default=[4900, 4901, 4902])
    p.add_argument('--epochs', type=int, default=300)
    a = p.parse_args()
    if len(set(a.dev_seeds+a.holdout_seeds)) != 6 or a.epochs < 1:
        p.error('Six distinct seeds and positive epochs are required')
    for name in ('out', 'task', 'data', 'align', 'insert'):
        absolute = getattr(a, name).resolve()
        setattr(a, name, absolute.relative_to(ROOT) if absolute.is_relative_to(ROOT) else absolute)
    os.chdir(ROOT)
    a.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    started = time.monotonic()
    def emit(stage, **data):
        message = data.get('decision') or (f"{data.get('mode', '')} seed {data['seed']}: {'success' if data.get('success') else 'failure'}" if 'seed' in data else f"{stage.title()}: {data.get('skill', 'live learning loop')}")
        event = {'stage': stage, 'message': message, 'elapsed_seconds': time.monotonic()-started, **data}
        write(a.out/'progress.json', event)
        with (a.out/'events.jsonl').open('a') as f:
            f.write(json.dumps(event)+'\n')
        print(json.dumps(event), flush=True)
    try:
        data_paths = {k: a.data/f'{k}-data.npz' for k in ('acquire', 'lift')}
        manifest = {'scope': SCOPE, 'development_seeds': a.dev_seeds, 'holdout_seeds': a.holdout_seeds,
                    'task_hashes': task_hashes(a.task), 'source_hashes': {},
                    'data_hashes': {str(v): sha(v) for v in data_paths.values()},
                    'prepared_teacher_report': {'path': str(a.data/'report.json'), 'sha256': sha(a.data/'report.json')},
                    'downstream_hashes': {str(v): sha(v) for v in (a.align, a.insert)},
                    'training': {'method': 'behavioral cloning', 'epochs': a.epochs, 'batch': 512, 'lr': .002,
                                 'optimizer': 'Adam', 'shuffle_seed': 42, 'initialization_seed': 31, 'device': 'cpu', 'threads': 2},
                    'acceptance': 'Development full-insertion success count strictly improves and holdout success count does not regress. No claim of statistical robustness from three holdout trials.',
                    'task_contract': ['acquire contact grasp', 'stable unsupported lift', 'align keyed geometry', 'insert using unchanged physical evaluator'],
                    'data_provenance': 'Prepared nominal teacher episodes300–309 plus fourfold controller-state augmentation and analytic relabeling; no fresh demonstration collection or reward shaping.'}
        for path in [Path(__file__), ROOT/'tools/train_micro_grasp.py', ROOT/'tools/run_micro_composition.py',
                     *sorted((ROOT/'src/astrafactory').glob('contact*.py')), ROOT/'src/astrafactory/env.py']:
            manifest['source_hashes'][str(path.relative_to(ROOT))] = sha(path)
        write(a.out/'manifest.json', manifest)
        emit('prepared', decision='Freeze seeds, data, physics and downstream policies before comparison.', manifest=str(a.out/'manifest.json'))
        env = CurriculumEnv(a.task)
        objects = geometry(env, a.out)
        env.close()
        skill = MicroGrasp()
        baseline = a.out/'initial-untrained.pt'
        save_policy(skill, baseline)
        before = evaluate(a, baseline, 'baseline', emit, objects)
        emit('training', decision='Train acquisition/lift only; downstream models remain frozen to isolate the changed component.',
             evidence={'baseline_successes': sum(r['success'] for r in before), 'episodes': len(before)})
        rng = np.random.default_rng(42)
        losses = {}
        train_started = time.monotonic()
        for key, path in data_paths.items():
            with np.load(path) as dataset:
                x = torch.tensor(dataset['training_x'], dtype=torch.float32)
                y = torch.tensor(dataset['training_y'], dtype=torch.float32)
                physical_count = len(dataset['physical_x'])
            model = skill.models[key]
            model.train()
            with torch.no_grad(): initial_loss = float(((model(x)-y)**2).mean())
            opt = torch.optim.Adam(model.parameters(), lr=.002)
            for epoch in range(a.epochs):
                order = rng.permutation(len(x))
                for j in range(0, len(x), 512):
                    ids = order[j:j+512]
                    loss = ((model(x[ids])-y[ids])**2).mean()
                    opt.zero_grad(); loss.backward(); opt.step()
            with torch.no_grad(): final_loss = float(((model(x)-y)**2).mean())
            model.eval()
            losses[key] = {'before_mse': initial_loss, 'after_mse': final_loss,
                           'physical_samples': physical_count, 'training_samples': len(x)}
            emit('training', skill=key, **losses[key])
        training_seconds = time.monotonic()-train_started
        checkpoint = a.out/'trained.pt'
        save_policy(skill, checkpoint)
        after = evaluate(a, checkpoint, 'trained', emit, objects)
        metrics = {mode: {split: {'successes': sum(r['success'] for r in rows if r['split'] == split),
                                'episodes': sum(r['split'] == split for r in rows)}
                         for split in ('development', 'holdout')}
                   for mode, rows in [('baseline', before), ('trained', after)]}
        accepted = (metrics['trained']['development']['successes'] > metrics['baseline']['development']['successes'] and
                    metrics['trained']['holdout']['successes'] >= metrics['baseline']['holdout']['successes'])
        report = {**manifest, 'metrics': metrics, 'losses': losses, 'training_seconds': training_seconds,
                  'parameters': sum(p.numel() for model in skill.models.values() for p in model.parameters()),
                  'baseline_sha256': sha(baseline), 'trained_sha256': sha(checkpoint), 'accepted': accepted,
                  'regression': any(metrics['trained'][s]['successes'] < metrics['baseline'][s]['successes'] for s in ('development', 'holdout')),
                  'baseline': before, 'trained': after, 'total_seconds': time.monotonic()-started}
        write(a.out/'report.json', report)
        videos = []
        for mode, rows in [('baseline', before), ('trained', after)]:
            selected = rows[0]
            videos.append({'id': mode, 'title': mode.title()+' grasp · full chain', 'kind': 'cad',
                           'replay_path': selected['replay_path'],
                           'caption': f"Paired development seed {selected['seed']}; {'success' if selected['success'] else 'failure'}. Fresh physical execution."})
        demo_metrics = [{'label': f'{mode.title()} {split}', 'value': f"{count['successes']}/{count['episodes']}", 'detail': 'Fresh full physical insertion rollouts'}
                        for mode, splits in metrics.items() for split, count in splits.items()]
        demo_metrics.append({'label': 'BC training', 'value': f'{training_seconds:.2f}s', 'detail': '3080 parameters, CPU, two threads'})
        write(a.out/'demo.json', {'videos': videos, 'metrics': demo_metrics, 'losses': losses,
                                 'scope_label': SCOPE, 'accepted': accepted, 'report_path': str(a.out/'report.json'),
                                 'limitations': ['Privileged simulator state; not camera control or hardware validation.',
                                     'Prepared teacher data reused; new optimization and all evaluation trajectories are fresh.',
                                     'Three holdout seeds are a small sample; no reset or teleport between skills.',
                                     'Behavioral cloning from random initialization, not reward-based learning or pretrained finetuning.']})
        emit('complete', accepted=accepted, metrics=metrics, demo=str(a.out/'demo.json'))
    except Exception as exc:
        emit('failed', error=repr(exc))
        raise


if __name__ == '__main__':
    main()
