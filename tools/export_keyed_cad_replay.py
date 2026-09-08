"""Export audited saved-action replay states, with the exact task mesh geometry."""
import json
from pathlib import Path
import mujoco
import numpy as np
import trimesh
from astrafactory.contact_curriculum import CurriculumEnv
from export_machine_cad_replay import sha

run = Path('runs/full-micro-composition-v3-final-render')
source = run / 'seed-5000-replay-state.npz'
audit_path = run / 'seed-5000-audit.json'
audit = json.loads(audit_path.read_text())
assert audit['exact_telemetry_within_1e_minus8'] and audit['replay_success']
env = CurriculumEnv('tasks/yam_contact_curriculum')
env.reset(seed=5000)
m, d = env.model, env.data
states = np.load(source)['qpos']
trace = json.loads(Path('runs/full-micro-composition-v3-final-nominal/seed-5000-trace.json').read_text())
assert len(states) == len(trace)
out = Path('assets/workcells/keyed_insertion_cad')
out.mkdir(parents=True, exist_ok=True)
objects = []
for i in range(m.ngeom):
    body = m.body(int(m.geom_bodyid[i])).name
    if body not in ['socket', 'free_peg']:
        continue
    name = m.geom(i).name
    kind = m.geom_type[i]
    if kind == mujoco.mjtGeom.mjGEOM_MESH:
        mid = m.geom_dataid[i]
        va, vn = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        fa, fn = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        mesh = trimesh.Trimesh(m.mesh_vert[va:va+vn].copy(), m.mesh_face[fa:fa+fn].copy(), process=False)
    elif kind == mujoco.mjtGeom.mjGEOM_BOX:
        mesh = trimesh.creation.box(extents=m.geom_size[i]*2)
    else:
        raise ValueError(f'Unsupported task geometry: {name}')
    path = out / f'{name}.stl'
    mesh.export(path)
    q = m.geom_quat[i]
    objects.append({'name':name, 'body':body, 'mesh_path':str(path),
                    'color':0xD79D58 if body=='free_peg' else 0x518F91,
                    'local_position':m.geom_pos[i].tolist(),
                    'local_quaternion':q[[1,2,3,0]].tolist(), 'scale':[1,1,1]})
frames = []
for k, state in enumerate(states):
    d.qpos[:] = state
    mujoco.mj_forward(m,d)
    bodies = {m.body(i).name:{'position':d.xpos[i].tolist(), 'quaternion':d.xquat[i][[1,2,3,0]].tolist()} for i in range(m.nbody) if m.body(i).name}
    frames.append({'time':(k+1)*m.opt.timestep*env.frame_skip, 'phase':trace[k]['phase'], 'bodies':bodies})
result = {'schema_version':1,'coordinate_system':'right-handed Z-up','units':'metres',
          'label':'recorded_physics','source_sha256':sha(source),'audit_sha256':sha(audit_path),
          'scene_sha256':sha('tasks/yam_contact_curriculum/scene.xml'),
          'fps':1/(m.opt.timestep*env.frame_skip),'frames':frames,'objects':objects,
          'camera':{'target':[.25,0,.16],'position':[.85,-.72,.57]},
          'scope':'Audited saved-action physics replay; original actions reproduced telemetry within 1e-8. Four learned imitation specialists plus scripted targets, guards and IK. Simulator-state observations; no hardware validation. Task meshes copied from compiled collision geometry.'}
target = run / 'seed-5000-cad-replay.json'
target.write_text(json.dumps(result,separators=(',',':')))
print(json.dumps({'path':str(target),'frames':len(frames),'objects':len(objects),'duration':frames[-1]['time']}))
env.close()
