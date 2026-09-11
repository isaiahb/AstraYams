"""Export the actual scene's fixture and gate solids as inspectable STEP."""
from pathlib import Path
import json,argparse
import cadquery as cq
import mujoco as mj
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'runs/tower-lift-v9';B=RUN/'gate-bench'
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,default=RUN);args=parser.parse_args();RUN=args.run.resolve();B=RUN/'gate-bench'
m=mj.MjModel.from_xml_path(str(B/'scene.xml'));d=mj.MjData(m);d.qpos[:]=np.load(B/'initial.npz')['qpos'];mj.mj_forward(m,d)
instances=json.loads((RUN/'so101/build.json').read_text())['instances']+json.loads((B/'build.json').read_text())['new_cad_instances']
assembly=cq.Assembly(name=RUN.name.replace('-','_')+'_passive_gate_packing');records=json.loads((RUN/'cad/parts.json').read_text());seen={r['name'] for r in records};manifest=[]
for name,part in instances:
    bi=mj.mj_name2id(m,mj.mjtObj.mjOBJ_BODY,name)
    if bi<0:continue
    source=cq.importers.importStep(str(RUN/'cad'/(part+'.step')));shape=source.val();rv=Rotation.from_matrix(d.xmat[bi].reshape(3,3)).as_rotvec();angle=np.linalg.norm(rv)
    if angle>1e-9:shape=shape.rotate((0,0,0),tuple(rv/angle),np.rad2deg(angle))
    shape=shape.translate(tuple(d.xpos[bi]*1000));assembly.add(shape,name=name)
    manifest.append(dict(body=name,part=part,world_position_m=d.xpos[bi].tolist(),valid=source.val().isValid(),volume_mm3=source.val().Volume()))
    existing=next((r for r in records if r['name']==part),None)
    if existing is not None:existing.update(valid=source.val().isValid(),solids=len(source.solids().vals()),volume_mm3=source.val().Volume())
    if part not in seen:
        records.append(dict(name=part,step=part+'.step',mesh=part+'.stl',valid=source.val().isValid(),solids=len(source.solids().vals()),volume_mm3=source.val().Volume()));seen.add(part)
assembly.save(str(RUN/'cad/packing-gated-assembly.step'))
(RUN/'cad/parts.json').write_text(json.dumps(records,indent=2)+'\n');(RUN/'cad/gate-assembly-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Exported',len(manifest),'instances')
