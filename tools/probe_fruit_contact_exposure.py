"""Re-simulate recorded motor targets with substep fruit-contact instrumentation.

No state resets after initialization. This is command replay, not a new policy
evaluation. Record trajectory drift; old display-rate traces cannot recover peaks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from astrafactory.harvest_basket import HarvestBasketEnv
from astrafactory.fruit_contact_audit import FruitContactAudit


def run(source, out, seconds=None, dt=None, start_s=0.):
    out.mkdir(parents=True, exist_ok=False)
    path = sorted(source.glob('episode-*.json'))[0]
    payload = json.loads(path.read_text())
    z = np.load(path.with_suffix('.npz'))
    begin = round(start_s / .02)
    if begin < 0 or begin >= len(z['t']) - 1 or not np.isclose(begin * .02, start_s):
        raise ValueError('Start must be an available recorded 20 ms frame')
    shutil.copytree(source / 'task', out / 'task')
    if dt is not None:
        if dt <= 0 or not np.isclose(round(.02 / dt) * dt, .02):
            raise ValueError('Timestep must divide the 20 ms action period')
        scene = out / 'task/scene.xml'; root = ET.parse(scene)
        root.getroot().find('option').set('timestep', str(dt)); root.write(scene, encoding='unicode')
    e = HarvestBasketEnv(task_dir=out / 'task')
    e.reset(seed=payload['result']['seed']); m, d = e.model, e.data
    d.qpos[:] = z['qpos'][begin]; d.qvel[:] = z['qvel'][begin]; d.eq_active[:] = z['eq_active'][begin]
    d.time = .3 + start_s; e.steps = begin; e.elapsed = start_s
    e.target = z['catch_targets'][begin].copy(); e.cut_target = z['cut_targets'][begin].copy()
    e.severed = not bool(d.eq_active[e.eq])
    e.work = payload['trace'][begin - 1]['cut_work_J'] if begin else e.threshold if e.severed else 0.
    e.jaw_target = float(z['jaw_targets'][begin]) if 'jaw_targets' in z else -.0028
    if e.severed:
        a, b = sorted([m.body('secondary_b_5').id, e.branch])
        m.exclude_signature[m.exclude_signature == (a << 16) + b] = 0
        m.exclude_signature[:] = np.sort(m.exclude_signature)
    mujoco.mj_forward(m, d)
    e.grip = e.grasp(); e.previous_goal = e.geometry()[0].copy()
    e.jaw_previous = sum(d.qpos[m.joint(n).qposadr[0]] for n in ['cut_joint7', 'cut_joint8'])
    e.basket_start = d.xpos[e.basket].copy(); e.basket_quat = d.xquat[e.basket].copy()
    # Paired window tests need the same numerical restart state as well as poses.
    # Historical recordings did not save the iterative solver warm start.
    if begin: d.qacc_warmstart[:] = 0.
    initial_hash = hashlib.sha256(d.qpos.tobytes() + d.qvel.tobytes() +
                                 d.eq_active.tobytes() + d.qacc_warmstart.tobytes()).hexdigest()
    observer = FruitContactAudit(m); original = e.after_physics_step; origin = .3
    def observe():
        original(); observer.sample(d, float(d.time - origin), float(m.opt.timestep))
    e.after_physics_step = observe
    count = len(z['t']) - 1
    if seconds is not None: count = min(count, round(seconds / .02))
    rows = []; qpos = [d.qpos.copy()]; qvel = [d.qvel.copy()]; eq = [d.eq_active.copy()]
    flex = [d.flexvert_xpos.copy()]; reference = mujoco.MjData(m); drift = 0.; start = time.time()
    if count <= begin: raise ValueError('End time must follow the start')
    for i in range(begin, count):
        e.target = z['catch_targets'][i + 1].copy(); e.cut_target = z['cut_targets'][i + 1].copy()
        if 'jaw_targets' in z: e.jaw_target = float(z['jaw_targets'][i + 1])
        e.phase = 'Recorded motor targets / ' + payload['trace'][i].get('phase', '')
        info = e.advance(); rows.append(info)
        reference.qpos[:] = z['qpos'][i + 1]; mujoco.mj_kinematics(m, reference)
        drift = max(drift, float(np.linalg.norm(d.xpos[e.fruit] - reference.xpos[e.fruit])))
        qpos.append(d.qpos.copy()); qvel.append(d.qvel.copy()); eq.append(d.eq_active.copy())
        flex.append(d.flexvert_xpos.copy())
        if i % 100 == 0:
            print(json.dumps(dict(step=i, sim_s=e.elapsed, wall_s=time.time() - start,
                                  invalid=info['invalid'], peak_fruit_drift_m=drift)), flush=True)
        if info['invalid']: break
    report = observer.report()
    report.update(source=str(source), source_episode_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  source_physics_sha256=hashlib.sha256(path.with_suffix('.npz').read_bytes()).hexdigest(),
                  timestep_s=float(m.opt.timestep), source_start_s=start_s, wall_s=time.time() - start,
                  initial_state_sha256=initial_hash,
                  solver_warmstart='zeroed for controlled window restart' if begin else 'retained from original reset sequence',
                  peak_target_origin_drift_from_source_m=drift, source_result=payload['result'],
                  replay_result=info, replay_scope='Finite-motor target replay in full plant/net physics. '
                  'No repeated pose injection; not a new closed-loop PPO evaluation. No damage model fit.')
    (out / 'contact-exposure.json').write_text(json.dumps(report, indent=2) + '\n')
    np.savez_compressed(out / 'contact-samples.npz', samples=np.asarray(observer.samples))
    result = dict(info, seed=payload['result']['seed'], controller='Recorded motor-target replay with '
                  'physics-rate contact audit; no new PPO evaluation and no biological damage validation.')
    (out / path.name).write_text(json.dumps(dict(result=result, trace=rows), indent=2))
    np.savez_compressed(out / path.with_suffix('.npz').name, qpos=qpos, qvel=qvel, eq_active=eq,
                        flex_vertices=flex, t=start_s + np.arange(len(qpos)) * .02,
                        catch_targets=z['catch_targets'][begin:begin+len(qpos)],
                        cut_targets=z['cut_targets'][begin:begin+len(qpos)])
    print(json.dumps(dict(report=str(out / 'contact-exposure.json'), pair_count=len(report['pairs']),
                          peak_target_origin_drift_m=drift, sim_s=e.elapsed)), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--seconds', type=float)
    p.add_argument('--dt', type=float); p.add_argument('--start-s', type=float, default=0.)
    a = p.parse_args(); run(a.source, a.out, a.seconds, a.dt, a.start_s)
