"""Exact-solid fit checks for roller supports versus the fixed packing fixture."""
from pathlib import Path
import argparse,json
import cadquery as cq
import mujoco as mj
import numpy as np
from scipy.spatial.transform import Rotation

def audit(run):
    bench=run/'gate-bench';m=mj.MjModel.from_xml_path(str(bench/'scene.xml'));d=mj.MjData(m)
    d.qpos[:]=np.load(bench/'initial.npz')['qpos'];mj.mj_forward(m,d)
    instances=json.loads((run/'so101/build.json').read_text())['instances']+json.loads((bench/'build.json').read_text())['new_cad_instances']
    shapes={}
    for body,part in instances:
        if not body.startswith('pack_'):continue
        i=mj.mj_name2id(m,mj.mjtObj.mjOBJ_BODY,body)
        if i<0:continue
        s=cq.importers.importStep(str(run/'cad'/(part+'.step'))).val()
        rv=Rotation.from_matrix(d.xmat[i].reshape(3,3)).as_rotvec();a=np.linalg.norm(rv)
        if a>1e-9:s=s.rotate((0,0,0),tuple(rv/a),np.rad2deg(a))
        shapes[body]=s.translate(tuple(d.xpos[i]*1000))
    supports=[n for n in shapes if n.startswith(('pack_gate_roller_foot','pack_gate_roller_post'))]
    fixture=[n for n in shapes if n.startswith(('pack_carrier','pack_clamshell','pack_lid','pack_guide','pack_web','pack_liner','pack_mount_plate','pack_rear_stop','pack_latch'))]
    checks=[]
    for a in supports:
        for b in fixture:
            vol=shapes[a].intersect(shapes[b]).Volume()
            checks.append(dict(support=a,fixture=b,intersection_mm3=vol))
    result=dict(scope=__doc__,checks=checks,maximum_intersection_mm3=max(c['intersection_mm3'] for c in checks),passed=all(c['intersection_mm3']<.01 for c in checks),
        minimum_static_pack_x_mm=min(s.BoundingBox().xmin for s in shapes.values()),
        exclusions='Intended fastener/thread engagement and post-to-foot joints are excluded. No strength or dynamic clearance certification.')
    (bench/'fixture-fit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();audit(a.run.resolve())
