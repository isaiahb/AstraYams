"""Static IK design preview; never labels design poses as physics rollouts."""
import json
from pathlib import Path
import mujoco
import numpy as np
from export_machine_cad_replay import sha

run = Path('runs/bimanual-vise-design')
scene = run / 'scene.xml'
manifest = Path('assets/workcells/manual_vise_cad/manifest.json')
model = mujoco.MjModel.from_xml_path(str(scene))
data = mujoco.MjData(model)
data.qpos[:] = np.load(run / 'design-poses.npz')['qpos'][3]
mujoco.mj_forward(model, data)
bodies = {}
for i in range(model.nbody):
    name = model.body(i).name
    if name:
        bodies[name] = {'position': data.xpos[i].tolist(),
                        'quaternion': data.xquat[i][[1, 2, 3, 0]].tolist()}
assets = json.loads(manifest.read_text())
objects = []
for item in assets['objects']:
    obj = dict(item)
    rgb = obj['color']
    obj['color'] = sum(int(round(v * 255)) << s for v, s in zip(rgb, [16, 8, 0]))
    obj['local_position'] = obj.pop('position', [0, 0, 0])
    q = obj.pop('quaternion', [1, 0, 0, 0])
    obj['local_quaternion'] = [q[1], q[2], q[3], q[0]]
    obj['scale'] = [1, 1, 1]
    assert obj['body'] in bodies
    assert Path(obj['mesh_path']).is_file()
    objects.append(obj)
preview = {
    'schema_version': 1, 'coordinate_system': 'right-handed Z-up', 'units': 'metres',
    'label': 'untrained_design', 'title': 'Two YAMs: hold stock and turn a manual vise',
    'source_sha256': sha(run / 'design-poses.npz'), 'scene_sha256': sha(scene),
    'cad_manifest_sha256': sha(manifest), 'fps': 1, 'default_time': 0,
    'frames': [{'time': 0, 'bodies': bodies, 'phase': 'IK design pose — contact unvalidated'}],
    'objects': objects,
    'robot_instances': [{'id': 'holder', 'body_prefix': ''},
                        {'id': 'tightener', 'body_prefix': 'right_'}],
    'camera': {'target': [.26, .21, .20], 'position': [.95, -.65, .70]},
    'scope': 'Static CAD and independent IK screening only. No executed trajectory, learned policy, or validated grasp. Screw mechanically coupled to jaw; no screw/jaw motor. Six upper half-turn strokes with alternating passive grips proposed. Full swept collision and contact-force validation pending.',
    'screening': json.loads((run / 'report.json').read_text()),
}
out = run / 'design-cad-preview.json'
out.write_text(json.dumps(preview, separators=(',', ':')))
print(out)
