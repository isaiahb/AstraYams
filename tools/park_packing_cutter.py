"""Choose an isolated bench starting pose clear of the lower arm's test poses.

This is static setup search, not a collision-free retreat from harvesting.
"""
from pathlib import Path
import json
import numpy as np
import mujoco as mj
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'runs/tower-lift-v9/gate-bench'
m=mj.MjModel.from_xml_path(str(B/'scene.xml'));d=mj.MjData(m);d.qpos[:]=np.load(B/'release-initial.npz')['qpos'];plan=json.loads((B/'release-plan.json').read_text());rng=np.random.default_rng(303)
names=['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll'];idx=lambda side:[m.joint(side+'_'+n).qposadr[0] for n in names];left=idx('left');right=idx('right');lo=np.array([m.joint('left_'+n).range[0]+.1 for n in names]);hi=np.array([m.joint('left_'+n).range[1]-.1 for n in names]);targets=[p['right'] for p in plan['waypoints']];best=None
for k in range(300):
 q=rng.uniform(lo,hi);d.qpos[left]=q;minimum=0;bad=False
 for v in targets:
  d.qpos[right]=v;mj.mj_forward(m,d)
  for c in d.contact:
   ns=[m.body(m.geom_bodyid[g]).name if g>=0 else 'textile' for g in [c.geom1,c.geom2]]
   if any(n.startswith('left_') for n in ns) and any(not n.startswith('left_') for n in ns):minimum=min(minimum,c.dist)
  if minimum<-.0001:bad=True;break
 if bad:continue
 tip=d.site_xpos[m.site('left_gripperframe').id];score=np.linalg.norm(tip-[.20,.30,1.05])
 if best is None or score<best[0]:best=(score,q.copy(),tip.copy())
 if score<.07:break
if best is None:raise RuntimeError('No clear cutter bench pose found')
print('Isolated cutter pose',best[1],best[2]);(B/'clear-cutter-pose.json').write_text(json.dumps(dict(scope=__doc__,q=best[1].tolist(),tool_tip_m=best[2].tolist(),tested_right_poses=len(targets)),indent=2)+'\n')
initial=np.load(B/'release-initial.npz');qpos=initial['qpos'].copy();ctrl=initial['ctrl'].copy();qpos[left]=best[1]
for n,q in zip(names,best[1]):ctrl[m.actuator('left_'+n).id]=q
np.savez_compressed(B/'release-initial.npz',qpos=qpos,ctrl=ctrl)
for p in plan['waypoints']:p['left']=best[1].tolist()
(B/'release-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
