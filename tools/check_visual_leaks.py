"""Independent observation-only student boundary audit; never changes policy code."""
import argparse
import ast
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import random
import sys
import numpy as np

FORBIDDEN_IMPORTS = ('mujoco', 'gymnasium', 'astrafactory.contact_env',
    'astrafactory.contact_curriculum', 'astrafactory.contact_teacher',
    'astrafactory.contact_micro_grasp', 'astrafactory.contact_downstream_skills',
    'astrafactory.contact_grasp_skill')
FORBIDDEN_ATTRIBUTES = {'env', 'environment', 'task', 'geom_xpos', 'geom_xmat',
    'site_xpos', 'site_xmat', 'contact', 'sensordata', 'feedback_state'}

class OracleTrap:
    """Every attempted oracle access fails, including chained/indexed access."""
    accesses = []
    def __getattr__(self, name):
        self.accesses.append(name)
        raise AssertionError('Privileged oracle access: '+name)
    def __getitem__(self, key):
        self.accesses.append(str(key))
        raise AssertionError('Privileged oracle indexing')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_source(module):
    path = Path(inspect.getsourcefile(module)); tree = ast.parse(path.read_text())
    findings = []
    for node in ast.walk(tree):
        imports = []
        if isinstance(node, ast.Import): imports = [n.name for n in node.names]
        elif isinstance(node, ast.ImportFrom): imports = [node.module or '']
        for name in imports:
            if any(name == bad or name.startswith(bad+'.') for bad in FORBIDDEN_IMPORTS):
                findings.append({'line': node.lineno, 'kind': 'privileged_import', 'name': name})
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRIBUTES:
            findings.append({'line': node.lineno, 'kind': 'oracle_attribute_review', 'name': node.attr})
    return {'path': str(path), 'sha256': sha(path), 'findings': findings,
            'limits': 'Static review of student module; dynamic imports and arbitrary external native code are not proven safe by this check.'}


def environment_references(obj):
    found, visited = [], set()
    def walk(value, path, depth):
        if depth > 6 or id(value) in visited: return
        visited.add(id(value)); module = type(value).__module__
        if module.startswith(('mujoco', 'gymnasium', 'astrafactory.contact_env', 'astrafactory.contact_curriculum')):
            found.append(path+':'+module); return
        if value is None or isinstance(value, (str, bytes, int, float, bool, np.ndarray)): return
        if module.startswith('torch') and not hasattr(value, '_modules'): return
        if isinstance(value, dict): items = value.items()
        elif isinstance(value, (list, tuple)): items = enumerate(value)
        elif hasattr(value, '__dict__'): items = vars(value).items()
        else: return
        for key, child in items: walk(child, path+'.'+str(key), depth+1)
    walk(obj, 'policy', 0)
    return found


def seed_everything():
    random.seed(20260908); np.random.seed(20260908)
    import torch
    torch.manual_seed(20260908)


def compare_with_poison(factory, module, checkpoint, observations, device, poisoned_environment=None):
    """Fixed sensor replay, fresh identically seeded policy, poisoned globals.

    The student never receives an env argument. Injected oracle globals represent
    forbidden simulator context; all access would raise. Existing directly held
    simulator references are also reported separately. This is a boundary test,
    not proof against malicious/dynamic hidden channels.
    """
    seed_everything(); baseline = factory(checkpoint, device=device); baseline.reset()
    refs = environment_references(baseline)
    before = [np.asarray(baseline.act({k: v.copy() if hasattr(v, 'copy') else v for k,v in obs.items()})).copy() for obs in observations]
    seed_everything(); poisoned = factory(checkpoint, device=device); poisoned.reset()
    trap = OracleTrap(); OracleTrap.accesses = []
    names = ('env', 'environment', 'task', 'sim_data', 'oracle', 'geometry_state', 'contact_oracle')
    absent = object(); saved = {n: vars(module).get(n, absent) for n in names}
    try:
        for name in names: setattr(module, name, poisoned_environment if poisoned_environment is not None and name in ('env','environment') else trap)
        after = [np.asarray(poisoned.act({k: v.copy() if hasattr(v, 'copy') else v for k,v in obs.items()})).copy() for obs in observations]
    finally:
        for name, value in saved.items():
            if value is absent: delattr(module, name)
            else: setattr(module, name, value)
    for action in before+after:
        if action.shape != (7,) or not np.isfinite(action).all() or np.max(np.abs(action)) > 1.00001:
            raise AssertionError('Expected seven finite bounded normalized actions')
    error = max(float(np.max(np.abs(a-b))) for a,b in zip(before,after))
    identical = all(np.array_equal(a,b) for a,b in zip(before,after))
    return {'frames': len(observations), 'identical_actions': identical, 'max_absolute_action_difference': error,
            'oracle_accesses': OracleTrap.accesses, 'held_environment_references': refs, 'actual_environment_poisoned': poisoned_environment is not None,
            'passed': identical and not refs and not OracleTrap.accesses,
            'limits': 'Poisoned module oracle globals and audit environment plus object-reference inspection; no environment is passed in student observations. Review collector/camera and evaluation wiring independently.'}


def audit_reset_and_cameras(task, seeds=(99000,99001,99002,99003)):
    import mujoco
    from astrafactory.contact_curriculum import CurriculumEnv
    from astrafactory.deployable_observations import reset_visual_episode, FixedCameraRig, CAMERA_SPECS
    records=[]
    for seed in seeds:
        env=CurriculumEnv(task);rig=None
        try:
            metadata=reset_visual_episode(env,seed,'rollout_development')
            rig=FixedCameraRig(env.model,env.data,env.qadr,env.vadr,augment=False,seed=seed)
            packet=rig.read(env.target,env.previous_action)
            initial=packet.proprio.copy(); image_hash=hashlib.sha256(packet.rgb.tobytes()).hexdigest()
            eyes=[c['rendered_eye_world_m'] for c in rig.visual_sample['fixed_cameras']]
            def camera_vectors():return [np.r_[c.lookat,c.distance,c.azimuth,c.elevation].tolist() for c in rig.cameras]
            cameras=camera_vectors(); timestamps=[packet.image_time_s]
            for _ in range(2):
                env.step(np.zeros(7,dtype=np.float32));sample=rig.read(env.target,env.previous_action);timestamps.append(sample.image_time_s)
            assert camera_vectors()==cameras
            assert timestamps[0]==timestamps[1] and timestamps[2]>timestamps[1]
            records.append({'seed':seed,'proprio':initial.tolist(),'rgb_sha256':image_hash,'camera_vectors':cameras,'rendered_eyes_world_m':eyes,'image_times_first_three_controls':timestamps,'reset_metadata_audit_only':metadata})
        finally:
            if rig is not None:rig.close()
            env.close()
    reference=np.array(records[0]['proprio']);proprio_error=max(float(np.max(np.abs(np.array(r['proprio'])-reference))) for r in records)
    camera_error=max(float(np.max(np.abs(np.array(r['camera_vectors'])-np.array(records[0]['camera_vectors'])))) for r in records)
    eye_error=max(float(np.max(np.abs(np.array(r['rendered_eyes_world_m'])-np.array(records[0]['rendered_eyes_world_m'])))) for r in records)
    distinct_images=len({r['rgb_sha256'] for r in records})
    distinct_objects=len({tuple(r['reset_metadata_audit_only']['realized_peg_position_m']) for r in records})
    result={'scope':'Independent reset/camera audit; privileged fields below are evaluator-only and never student inputs.', 'seeds':list(seeds),'records':records,'camera_specs':CAMERA_SPECS,'initial_proprio_max_difference':proprio_error,'camera_transform_max_difference':camera_error,'rendered_eye_max_difference':eye_error,'distinct_initial_images':distinct_images,'distinct_object_positions':distinct_objects,'passed':proprio_error==0 and camera_error==0 and eye_error==0 and distinct_images>1 and distinct_objects>1,'source_sha256':{str(p):sha(p) for p in [Path('src/astrafactory/deployable_observations.py'),Path('src/astrafactory/sensor_contract.py')]}}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy', default='astrafactory.vision_policy:VisualPolicy')
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--reset-audit', action='store_true')
    p.add_argument('--task', default='tasks/yam_contact_curriculum')
    p.add_argument('--observations', type=Path)
    p.add_argument('--device', default='cpu')
    p.add_argument('--out', type=Path, default=Path('runs/visual-leak-audit/report.json'))
    a = p.parse_args()
    if a.reset_audit:
        report=audit_reset_and_cameras(a.task);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
        if not report['passed']:sys.exit(1)
        return
    if a.checkpoint is None:p.error('--checkpoint required unless --reset-audit is used')
    name, symbol = a.policy.split(':'); module = importlib.import_module(name); factory = getattr(module, symbol)
    if a.observations:
        with np.load(a.observations, allow_pickle=False) as d:
            images = d['rgb'][:16] if 'rgb' in d else d['images'][d['image_index'][:16]]
            states = d['proprio'][:16]
        origin = {'path': str(a.observations), 'sha256': sha(a.observations)}
    else:
        rng = np.random.default_rng(902); images = rng.integers(0, 256, (16,2,160,160,3), dtype=np.uint8); states = rng.normal(0,.1,(16,28)).astype(np.float32)
        origin = {'synthetic_fixed_sensor_replay': True, 'seed': 902}
    assert len(images) == len(states) and len(images) > 0
    observations = [{'rgb': rgb.copy(), 'proprio': state.copy(), 'sensor_time_s': i*.02, 'image_time_s': (i//2)*.04} for i,(rgb,state) in enumerate(zip(images,states))]
    source = inspect_source(module)
    from astrafactory.contact_curriculum import CurriculumEnv
    audit_env=CurriculumEnv(a.task)
    original_context={name:getattr(audit_env,name) for name in ('task','data','model')}
    for name in original_context:setattr(audit_env,name,OracleTrap())
    try:
        dynamic = compare_with_poison(factory, module, a.checkpoint, observations, a.device, audit_env)
        passed = dynamic['passed'] and not source['findings']
    except Exception as error:
        dynamic = {'passed': False, 'error_type': type(error).__name__, 'error': str(error)}; passed = False
    finally:
        for name,value in original_context.items():setattr(audit_env,name,value)
        audit_env.close()
    report = {'policy': a.policy, 'checkpoint_sha256': sha(a.checkpoint), 'source': source,
              'observation_contract': 'RGB plus measured q/qd and command/history only; no object/socket pose, contacts, force, task stage or teacher actions',
              'observation_source': origin, 'dynamic': dynamic, 'passed': passed,
              'scope': 'Software information-boundary audit, not sim-to-real validation or proof of camera calibration/hardware sensing.'}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report, indent=2))
    if not passed: sys.exit(1)

if __name__ == '__main__': main()
