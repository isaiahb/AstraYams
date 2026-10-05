"""Refresh the specimen demo in isolation; never mutate source study/training assets."""
from pathlib import Path
import sys, shutil, json, hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import test_strawberry_specimen as probe
import render_strawberry_specimen as render
import numpy as np
import mujoco

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    base=HERE.parent/'surface-study/v4'; old=HERE.parent/'surface-study/v3'
    for name in ['scene.xml','reference-graph.json','physics-equivalence.json']:
        shutil.copy2(base/name,HERE/name)
    provenance={'scene_source':str(base.relative_to(ROOT)/'scene.xml'),
        'scene_sha256':sha(HERE/'scene.xml'),'prior_page':str(HERE.parent.relative_to(ROOT)/'index.html'),
        'scope':'Same complete V4 specimen; fresh diagnostic contacts, reused physically equivalent V3 settling. No PPO or biological calibration.',
        'recordings':{}}
    (HERE/'rest').mkdir(exist_ok=True)
    for name in ['rollout.npz','result.json']:shutil.copy2(old/'rest'/name,HERE/'rest'/name)
    provenance['recordings']['rest']={'origin':'reused','source':str((old/'rest/rollout.npz').relative_to(ROOT)),
        'sha256':sha(old/'rest/rollout.npz'),'equivalence':'physics-equivalence.json'}
    probe.P=HERE
    for kind in ['leaf','basal','stalk','neighbor']:
        for control in [False,True]:
            name=kind+('-control' if control else '')
            if not (HERE/name/'result.json').exists():probe.run(kind,control)
            provenance['recordings'][name]={'origin':'fresh','sha256':sha(HERE/name/'rollout.npz')}
    kinds=['rest']+[k+s for k in ['leaf','basal','stalk','neighbor'] for s in ['', '-control']]
    render.P=HERE;render.export(kinds)
    manifest={}
    for kind in kinds:
        report=json.loads((HERE/kind/'result.json').read_text())
        manifest[kind]={'report':report,'source':provenance['recordings'][kind]}
    model=mujoco.MjModel.from_xml_path(str(HERE/'scene.xml'))
    for kind in ['leaf','basal','stalk','neighbor']:
        a=np.load(HERE/kind/'rollout.npz');b=np.load(HERE/(kind+'-control')/'rollout.npz')
        assert np.array_equal(a['t'],b['t'])
        gid=model.geom(manifest[kind]['report']['target']).id
        delta=np.linalg.norm(a['geom_positions'][:,gid]-b['geom_positions'][:,gid],axis=1)*1000
        sample_times=np.linspace(0,4,101)
        manifest[kind]['comparison']={'peak_mm':float(delta.max()),
            'samples':np.c_[sample_times,np.interp(sample_times,a['t'],delta)].tolist(),
            'method':'Euclidean target-geom displacement relative to the matched contact-disabled trajectory. Not a force/deflection calibration.'}
    (HERE/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (HERE/'experiments.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Ready:',HERE/'index.html',flush=True)

if __name__=='__main__':main()
