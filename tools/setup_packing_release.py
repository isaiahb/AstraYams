"""Initialize a separate near-container release test, not a transport success."""
from pathlib import Path
import json
import numpy as np
import mujoco as mj
from scipy.optimize import least_squares
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/tower-lift-v9';B=R/'gate-bench'
plan=json.loads((B/'commission-plan.json').read_text());hover=plan['waypoints'][6];low=plan['waypoints'][7];deep=plan['waypoints'][8]
# Select explicit target times to avoid depending on list order.
at=lambda t:next(p for p in plan['waypoints'] if p['time_s']==t)
hover=at(13);low=at(15);deep=at(17)
m=mj.MjModel.from_xml_path(str(R/'so101/scene.xml'));d=mj.MjData(m);d.qpos[:]=np.load(R/'so101/initial.npz')['qpos']
names=['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll']
ids=[m.joint('right_'+n).qposadr[0] for n in names]
lo=[m.joint('right_'+n).range[0]+.04 for n in names];hi=[m.joint('right_'+n).range[1]-.04 for n in names]
sid=m.site('packing_net_center').id
# A separate high approach keeps the closed lever above the roller initially.
def objective(q):
    d.qpos[ids]=q;mj.mj_kinematics(m,d)
    return np.r_[100*(d.site_xpos[sid]-[-.195,.171,.635]),d.site_xmat[sid].reshape(3,3)[:,2]-[0,0,1]]
r=least_squares(objective,np.clip(hover['right'],lo,hi),bounds=(lo,hi));hover['right']=r.x.tolist()
for side in ['left','right']:
 for n,q in zip(names,hover[side]):d.qpos[m.joint(side+'_'+n).qposadr[0]]=q
mj.mj_forward(m,d);netpose=np.r_[d.xpos[m.body('right_packing_net').id],d.xquat[m.body('right_packing_net').id]]
a=mj.MjModel.from_xml_path(str(B/'scene.xml'));b=mj.MjData(a);initial=np.load(B/'initial.npz');b.qpos[:]=initial['qpos'];b.ctrl[:]=initial['ctrl']
for side in ['left','right']:
 for n,q in zip(names,hover[side]):b.qpos[a.joint(side+'_'+n).qposadr[0]]=q;b.ctrl[a.actuator(side+'_'+n).id]=q
j=a.joint('right_net_free').qposadr[0];b.qpos[j:j+7]=netpose
j=a.joint('packing_berry_free').qposadr[0];b.qpos[j:j+7]=np.r_[netpose[:3]+[0,0,.055],[1,0,0,0]]
mj.mj_forward(a,b);np.savez_compressed(B/'release-initial.npz',qpos=b.qpos,ctrl=b.ctrl)
way=[]
for t,p in [(0,hover),(1,hover),(3,low),(5,deep),(6,deep),(8,hover),(9,hover)]:way.append(dict(time_s=t,left=p['left'],right=p['right']))
(B/'release-plan.json').write_text(json.dumps(dict(scope=__doc__,waypoints=way),indent=2)+'\n')
print('Separate initialization:',netpose[:3])
