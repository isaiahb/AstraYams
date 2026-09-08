"""Independent free-peg contact checks; never replace a failed grasp with a weld."""
from pathlib import Path
import argparse
import json
import numpy as np
import mujoco
try:
    from .collect_demonstrations import task_hashes, environment_source_hash, load_callable
except ImportError:
    from collect_demonstrations import task_hashes, environment_source_hash, load_callable

ROOT = Path(__file__).resolve().parents[1]


def descendant(model, body, ancestor):
    while body:
        if body == ancestor:
            return True
        body = int(model.body_parentid[body])
    return body == ancestor


def model_checks(env):
    m = env.model
    peg = m.body('free_peg').id
    joint = m.joint('peg_free').id
    attachments = []
    for i in range(m.neq):
        if m.eq_type[i] in [mujoco.mjtEq.mjEQ_CONNECT, mujoco.mjtEq.mjEQ_WELD] and peg in [m.eq_obj1id[i], m.eq_obj2id[i]]:
            attachments.append(i)
    result = {'peg_joint_is_free': bool(m.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE),
              'peg_parent_is_world': bool(m.body_parentid[peg] == 0),
              'peg_is_not_mocap': bool(m.body_mocapid[peg] == -1),
              'no_peg_attachment_equalities': not attachments,
              'gravity_points_down': bool(m.opt.gravity[2] < 0),
              'attachment_equality_ids': attachments, 'peg_mass_kg': float(m.body_mass[peg])}
    result['passed'] = all(result[k] for k in ['peg_joint_is_free', 'peg_parent_is_world', 'peg_is_not_mocap', 'no_peg_attachment_equalities', 'gravity_points_down'])
    return result


def physical_state(env):
    m, d = env.model, env.data
    peg = m.body('free_peg').id
    left, right = m.body('tip_left').id, m.body('tip_right').id
    forces = {'left': 0., 'right': 0., 'other_support': 0.}
    contacts = []
    for index in range(d.ncon):
        c = d.contact[index]
        g1, g2 = int(c.geom1), int(c.geom2)
        b1, b2 = int(m.geom_bodyid[g1]), int(m.geom_bodyid[g2])
        if descendant(m, b1, peg):
            other, other_geom = b2, g2
        elif descendant(m, b2, peg):
            other, other_geom = b1, g1
        else:
            continue
        force = np.zeros(6)
        mujoco.mj_contactForce(m, d, index, force)
        magnitude = float(np.linalg.norm(force[:3]))
        group = 'left' if descendant(m, other, left) else 'right' if descendant(m, other, right) else 'other_support'
        forces[group] += magnitude
        if magnitude > 1e-6:
            contacts.append({'group': group, 'other_geom': m.geom(other_geom).name, 'force_n': magnitude})
    free_dof = m.jnt_dofadr[m.joint('peg_free').id]
    return {'peg_z_m': float(d.site_xpos[m.site('peg_tip').id, 2]),
            'tool_z_m': float(d.site_xpos[m.site('tool_tip').id, 2]),
            'peg_vertical_velocity_m_s': float(d.qvel[free_dof + 2]),
            'left_force_n': forces['left'], 'right_force_n': forces['right'],
            'nonfinger_support_force_n': forces['other_support'], 'peg_contacts': contacts,
            'grip_joint_position_m': float(d.qpos[m.jnt_qposadr[m.joint('joint7').id]]),
            'sim_time': float(d.time)}


def emit_step(env, action, obs, capture, info):
    observation, reward, terminated, truncated, info = env.step(action)
    state = physical_state(env)
    row = {**info, **state, 'action': np.asarray(action).tolist(), 'pre_action_state': np.asarray(obs).tolist(),
           'next_state': np.asarray(observation).tolist(), 'qpos': env.data.qpos.tolist(),
           'qvel': env.data.qvel.tolist(), 'ctrl': env.data.ctrl.tolist(),
           'reward': float(reward), 'terminated': bool(terminated), 'truncated': bool(truncated)}
    if capture:
        capture(env, row)
    return observation, terminated or truncated, row


def lift(env, seed, capture=None, teacher_reference='astrafactory.contact_env:teacher'):
    teacher = load_callable(teacher_reference)
    obs, info = env.reset(seed=seed)
    initial = physical_state(env)
    duration = env.model.opt.timestep * env.frame_skip
    consecutive, longest = 0., 0.
    rows, actions = [], []
    teacher_no_teleport = True
    for _ in range(env.horizon):
        before = env.data.qpos.copy()
        action = np.asarray(teacher(env, stop_after_lift=True), dtype=np.float32)
        teacher_no_teleport &= np.array_equal(before, env.data.qpos)
        if not teacher_no_teleport:
            raise AssertionError('Teacher assigned physical qpos')
        obs, done, row = emit_step(env, action, obs, capture, info)
        rows.append(row)
        actions.append(action.copy())
        supported = row['left_force_n'] > 1e-5 and row['right_force_n'] > 1e-5 and row['nonfinger_support_force_n'] < 1e-5
        elevated = row['peg_z_m'] - initial['peg_z_m'] >= .020
        at_lift_hold = int(getattr(env.task, 'stage', -1)) >= 3
        consecutive = consecutive + duration if supported and elevated and at_lift_hold else 0.
        longest = max(longest, consecutive)
        if longest >= .5 or done:
            break
    passed = longest >= .5
    return {'passed': passed, 'seed': seed, 'steps': len(rows), 'initial_peg_z_m': initial['peg_z_m'],
            'max_peg_rise_m': max((r['peg_z_m']-initial['peg_z_m'] for r in rows), default=0.),
            'bilateral_unsupported_hold_seconds': longest, 'teacher_does_not_assign_qpos': teacher_no_teleport,
            'last': rows[-1] if rows else initial}, actions, rows, obs


def drop(env, obs, seed, capture=None):
    initial = physical_state(env)
    rows = []
    first_release = None
    step_duration = env.model.opt.timestep * env.frame_skip
    for _ in range(int(np.ceil(2. / step_duration))):
        action = np.zeros(env.action_space.shape, dtype=np.float32)
        action[6] = -1.  # Joint-delta gripper command: negative opens.
        obs, done, row = emit_step(env, action, obs, capture, {})
        rows.append(row)
        if first_release is None and initial['peg_z_m'] - row['peg_z_m'] >= .020 and row['left_force_n'] < 1e-5 and row['right_force_n'] < 1e-5:
            first_release = {'elapsed_seconds': row['sim_time']-initial['sim_time'], 'peg_drop_m': initial['peg_z_m']-row['peg_z_m'], 'peg_vertical_velocity_m_s': row['peg_vertical_velocity_m_s']}
        if done:
            break
    last = rows[-1]
    fell = initial['peg_z_m'] - last['peg_z_m']
    opened = initial['grip_joint_position_m'] - last['grip_joint_position_m']
    return {'passed': bool(fell >= .020 and opened > .002 and last['left_force_n'] < 1e-5 and last['right_force_n'] < 1e-5),
            'seed': seed, 'steps': len(rows), 'peg_drop_m': fell, 'opening_joint_travel_m': opened,
            'elapsed_seconds': last['sim_time']-initial['sim_time'], 'first_verified_release': first_release, 'last': last}, rows


def zero_friction(env, seed, actions, capture=None):
    obs, info = env.reset(seed=seed)
    env.model.geom_friction[:] = 0
    env.model.pair_friction[:] = 0
    initial = physical_state(env)
    rows = []
    min_tool, tool_rise = initial['tool_z_m'], 0.
    for action in actions:
        obs, done, row = emit_step(env, action, obs, capture, info)
        rows.append(row)
        min_tool = min(min_tool, row['tool_z_m'])
        tool_rise = max(tool_rise, row['tool_z_m'] - min_tool)
        if done:
            break
    rise = max((r['peg_z_m']-initial['peg_z_m'] for r in rows), default=0.)
    return {'passed': bool(tool_rise >= .020 and rise < .020), 'seed': seed,
            'steps': len(rows), 'replayed_baseline_actions': len(actions),
            'max_peg_rise_m': rise, 'tool_upward_travel_m': tool_rise,
            'all_geom_and_pair_friction_zero': True, 'last': rows[-1] if rows else initial}, rows


def validate(task, seed=0, captures=None, teacher_reference='astrafactory.contact_env:teacher'):
    from astrafactory.contact_env import ContactEnv
    captures = captures or {}
    env = ContactEnv(task)
    try:
        static = model_checks(env)
        baseline, actions, rows, obs = lift(env, seed, captures.get('lift'), teacher_reference)
        if baseline['passed']:
            released, drop_rows = drop(env, obs, seed, captures.get('drop'))
        else:
            released, drop_rows = {'passed': False, 'skipped': 'No validated suspended grasp to release'}, []
    finally:
        env.close()
    negative_env = ContactEnv(task)
    try:
        negative, negative_rows = zero_friction(negative_env, seed, actions, captures.get('zero-friction'))
    finally:
        negative_env.close()
    report = {'scope': 'simulated free-body contact grasp; no learned-policy claim', 'seed': seed,
              'task_hashes': task_hashes(task), 'teacher': teacher_reference, 'teacher_module_sha256': environment_source_hash(teacher_reference), 'environment_source_hashes': {name: environment_source_hash(name) for name in ['astrafactory.contact_env:ContactEnv', 'astrafactory.env:FactoryEnv', 'astrafactory.yam_env:YamEnv']},
              'static_model': static, 'closed_contact_lift': baseline, 'open_gripper_drop': released,
              'zero_friction_action_replay': negative}
    report['passed'] = all(v['passed'] for v in [static, baseline, released, negative])
    return report, {'lift': rows, 'drop': drop_rows, 'zero-friction': negative_rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', default=str(ROOT / 'tasks/yam_contact_insertion'))
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--teacher', default='astrafactory.contact_env:teacher')
    p.add_argument('--out', type=Path, default=ROOT / 'runs/yam-contact-checks')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report, traces = validate(args.task, args.seed, teacher_reference=args.teacher)
    (args.out / 'report.json').write_text(json.dumps(report, indent=2))
    for mode, rows in traces.items():
        (args.out / f'{mode}-trace.json').write_text(json.dumps(rows))
    print(json.dumps({k: report[k]['passed'] for k in ['static_model', 'closed_contact_lift', 'open_gripper_drop', 'zero_friction_action_replay']}), flush=True)
    if not report['passed']:
        raise SystemExit('Contact validation failed; inspect recorded measurements, do not claim a acquired grasp')


if __name__ == '__main__':
    main()
