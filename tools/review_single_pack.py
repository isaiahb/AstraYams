"""Export explicitly static CAD poses for the single-container reach study."""
import json,shutil
from pathlib import Path
import numpy as np
import mujoco as mj
from scipy.optimize import least_squares
import render_strawberry_specimen as exporter

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runs/tower-lift-v8';P=OUT/'so101'

def main():
    m=mj.MjModel.from_xml_path(str(P/'scene.xml'));d=mj.MjData(m)
    initial=np.load(P/'initial.npz');d.qpos[:]=initial['qpos'];d.ctrl[:]=initial['ctrl']
    # Warm starts from the numerical pair-layout search, recomputed below.
    # No motion controller or policy uses these static review seeds.
    for side,values in [('left',[-.576589,-1.152215,-.901981,1.383667,-.078044]),
                        ('right',[-.054919,-1.559672,-1.288482,1.266990,.103719])]:
        for name,value in zip(['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll'],values):
            d.qpos[m.joint(side+'_'+name).qposadr[0]]=value
    rng=np.random.default_rng(28);audit=[]
    def solve(side,site,goal,axis=2):
        joints=[m.joint(side+'_'+j) for j in ['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll']]
        ids=np.array([j.qposadr[0] for j in joints]);lo=np.array([j.range[0]+.03 for j in joints]);hi=np.array([j.range[1]-.03 for j in joints]);start=d.qpos[ids].copy();sid=m.site(site).id
        best=None
        def fun(q):
            d.qpos[ids]=q;mj.mj_kinematics(m,d)
            normal=d.site_xmat[sid].reshape(3,3)[:,axis] if axis is not None else np.array([0,0,1])
            return np.r_[100*(d.site_xpos[sid]-goal),2*(normal-[0,0,1]),.002*(q-start)]
        for k in range(16):
            q=start if k==0 else rng.uniform(lo,hi)
            r=least_squares(fun,np.clip(q,lo,hi),bounds=(lo,hi),max_nfev=120)
            fun(r.x);err=float(np.linalg.norm(d.site_xpos[sid]-goal));normal=d.site_xmat[sid].reshape(3,3)[:,axis].copy() if axis is not None else np.array([0,0,1])
            mj.mj_forward(m,d)
            bad=[]
            for c in d.contact:
                names=[m.body(m.geom_bodyid[g]).name or '' for g in [c.geom1,c.geom2]]
                if c.dist<-.0002 and any(n.startswith(side+'_') for n in names):bad.append(float(c.dist))
            score=err*100+np.linalg.norm(normal-[0,0,1])+sum(abs(x) for x in bad)*1000
            if best is None or score<best[0]:best=(score,r.x.copy(),err,normal,bad)
            if err<.0005 and normal[2]>.998 and not bad:break
        _,q,err,normal,bad=best;d.qpos[ids]=q;mj.mj_forward(m,d)
        record=dict(arm=side,site=site,goal_m=np.asarray(goal).tolist(),position_error_m=err,normal_z=float(normal[2]) if axis is not None else None,orientation_constraint='upward net normal' if axis is not None else 'tip position only; cutter orientation not commissioned',joint_positions=q.tolist(),enabled_contact_penetrations_m=bad)
        audit.append(record);print(record,flush=True)
        return err<.003 and normal[2]>.97 and not bad
    # The cutter tip is placed near the target. Cutting orientation and the
    # stem/blade interaction are explicitly outside this fixture layout test.
    assert solve('left','left_gripperframe',np.array([.012,.451,.875]),None)
    assert solve('right','packing_net_center',np.array([.012,.451,.789]),2)
    catch=d.qpos.copy()
    # Rim just above the container lip, with the net bowl dipping inside.
    # The complete stock jaw must clear the wall as well as the net frame.
    assert solve('right','packing_net_center',np.array([-.205,.171,.620]),2)
    deposit=d.qpos.copy()
    poses=[catch,deposit,initial['qpos'].copy()]
    layout=P/'layout';layout.mkdir(exist_ok=True)
    np.savez_compressed(layout/'rollout.npz',qpos=np.repeat(poses,2,axis=0),t=np.repeat(np.arange(len(poses)),2))
    exporter.P=P;exporter.export(['layout'])
    payload=json.loads((layout/'replay.json').read_text())
    labels=['Catch approach — offline joint pose','Container access — offline joint pose','V7 parked joints — layout comparison']
    payload.update(label='static_CAD_fit_review',scope='Single clamshell on carriage-supported shelf · net fixed for CAD fit only · no learned or physics-validated packing',training_ready=False,audit={},pose_labels=labels)
    for frame,label in zip(payload['frames'],labels):frame['phase']=label
    for o in payload['objects']:
        if o['body'] in ['pack_clamshell','pack_lid'] or o['body'].startswith('pack_hinge'):o['opacity']=.25
    for dest in [layout/'replay.json',P/'replay.json']:dest.write_text(json.dumps(payload,separators=(',',':')))
    (OUT/'reach-checks.json').write_text(json.dumps(dict(method='Offline numerical IK using original SO101 joints and limits; no policy or motion replay',poses=audit,scope='Position/orientation and enabled original-model contact checks only; new CAD interfaces need explicit interference/contact commissioning'),indent=2)+'\n')
    shutil.copy2(ROOT/'tools/templates/single-pack-review.html',OUT/'index.html')

if __name__=='__main__':main()
