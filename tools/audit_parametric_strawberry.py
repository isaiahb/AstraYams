"""Measure saved states; never edit rollouts or hide incidental contacts."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import mujoco


def audit(path):
    path=Path(path);model=mujoco.MjModel.from_xml_path(str(path/'scene.xml'))
    spec=json.loads((path/'reference-graph.json').read_text())
    data=mujoco.MjData(model);angles={}
    rest=np.load(path/'rest/rollout.npz')
    for state in ['unloaded','settled']:
        mujoco.mj_resetData(model,data)
        if state=='settled':data.qpos[:]=rest['qpos'][-1]
        mujoco.mj_forward(model,data);items={}
        for leaf in spec['leaves']:
            name='petiole_'+leaf['id'];n=next(b['segments'] for b in json.loads((path/'model.json').read_text())['beam_parameters'] if b['id']==name)
            xyz=np.array([data.xpos[model.body(f'{name}_{i}').id] for i in range(n)]+[data.xpos[model.body(name+'_tip').id]])
            delta=np.diff(xyz,axis=0)
            incl=np.degrees(np.arccos(np.clip(delta[:,2]/np.linalg.norm(delta,axis=1),-1,1)))
            normals=[data.xmat[model.body(f"leaf_{leaf['id']}_{i}_panel0").id].reshape(3,3)[:,2] for i in range(3)]
            items[leaf['id']]={'segment_inclination_from_vertical_deg':incl.tolist(),
                              'leaflet_base_normal_from_up_deg':[float(np.degrees(np.arccos(np.clip(n[2],-1,1)))) for n in normals],
                              'tip_m':xyz[-1].tolist()}
        angles[state]=items
    pairs={}
    for result in path.glob('*/result.json'):
        if result.parent.name=='rest' or result.parent.name.endswith('-control'):continue
        control=result.parent.with_name(result.parent.name+'-control')
        if not (control/'result.json').exists():continue
        trial=json.loads(result.read_text());ctrl=json.loads((control/'result.json').read_text())
        a=np.load(result.parent/'rollout.npz');b=np.load(control/'rollout.npz')
        same_shape=a['qpos'].shape==b['qpos'].shape
        match=bool(same_shape and np.allclose(a['qpos'][0],b['qpos'][0],atol=1e-9) and np.allclose(a['t'],b['t'],atol=1e-9) and np.allclose(trial['probe_start_m'],ctrl['probe_start_m']) and np.allclose(trial['probe_end_m'],ctrl['probe_end_m']))
        gid=model.geom(trial['target']).id
        disp=np.linalg.norm(a['geom_positions'][:,gid]-b['geom_positions'][:,gid],axis=1)*1000 if same_shape else np.array([float('nan')])
        pen=max([s['max_penetration_mm'] for s in trial['probe_contacts'].values()],default=0.)
        passed=bool(match and trial['valid_run'] and ctrl['valid_run'] and trial['target_touched'] and not trial['initial_probe_contacts'] and not ctrl['probe_contacts'] and pen<1.)
        family={'basal':'petiole_left_','leaf':'leaf_left_1_','stalk':'peduncle_','neighbor':'berry_secondary_a'}[trial['kind']]
        incidental=[name for name in trial['probe_contacts'] if not name.startswith(family)]
        pairs[result.parent.name]={'numerical_probe_gate_pass':passed,'matching_initial_state_and_stroke':match,
            'isolated_intended_organ':not incidental,'incidental_other_organs':incidental,
            'target_touched':trial['target_touched'],'control_contact_count':len(ctrl['probe_contacts']),
            'max_probe_penetration_mm':pen,'max_target_displacement_relative_control_mm':float(disp.max()),
            'final_target_displacement_relative_control_mm':float(disp[-1]),
            'summed_contact_impulse_ns':sum(s['impulse_ns'] for s in trial['probe_contacts'].values()),
            'contacted_surfaces':list(trial['probe_contacts']), 'all_scene_penetrations_over_1mm':trial['penetrations_over_1mm']}
    report={'scene_sha256':hashlib.sha256((path/'scene.xml').read_bytes()).hexdigest(),
            'mujoco_version':mujoco.__version__,'anatomy':angles,'probe_pairs':pairs,
            'rest':json.loads((path/'rest/result.json').read_text()),
            'scope':'Synthetic geometry/contact checks only. No calibration, real transfer, root movement, cutting or policy result.'}
    (path/'audit.json').write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('model_dir',type=Path);args=parser.parse_args()
    result=audit(args.model_dir);print(json.dumps({'pairs':result['probe_pairs'],'audit':str(args.model_dir/'audit.json')},indent=2))
