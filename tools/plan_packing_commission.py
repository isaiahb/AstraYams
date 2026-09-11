"""Offline IK commissioning path, never presented as a learned policy."""
from pathlib import Path
import json
import mujoco as mj
import numpy as np
from packing_workspace_study import solve
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'runs/tower-lift-v9'
m=mj.MjModel.from_xml_path(str(RUN/'so101/scene.xml'));d=mj.MjData(m)
d.qpos[:]=np.load(ROOT/'runs/tower-lift-v8/so101/layout/rollout.npz')['qpos'][0];mj.mj_forward(m,d)
names=['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll']
idx=lambda side:[m.joint(side+'_'+n).qposadr[0] for n in names]
start=d.qpos[idx('right')].copy();left=d.qpos[idx('left')].copy();park=np.load(RUN/'so101/initial.npz')['qpos'][idx('left')]
way=[dict(time_s=0,left=left.tolist(),right=start.tolist()),dict(time_s=1,left=left.tolist(),right=start.tolist()),dict(time_s=3,left=park.tolist(),right=start.tolist())];evidence=[]
for t,goal in [(5,[.012,.46,.79]),(8,[-.17,.40,.75]),(11,[-.195,.22,.65]),(13,[-.195,.171,.62]),(15,[-.195,.171,.58]),(17,[-.195,.171,.56]),(19,[-.195,.171,.62])]:
    r=solve(m,d,np.array(goal),np.array([0,0,1]),start,margin=.06,trials=7);start=np.array(r['q']);evidence.append(dict(time_s=t,goal=goal,**r));way.append(dict(time_s=t,left=park.tolist(),right=start.tolist()));print(t,goal,r['position_error_mm'],r['normal_error_deg'],flush=True)
(RUN/'gate-bench/commission-plan.json').write_text(json.dumps(dict(method=__doc__,waypoints=way,pose_checks=evidence),indent=2)+'\n')
