from pathlib import Path
import sys,numpy as np,mujoco,json
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'environment-lab'));from lab import *
c=copy.deepcopy(CONFIGS[3]);e,_=make(c,P/'diagnostic-scene',11);r=np.load(HERE/'iteration-3/episode.npz');e.data.qpos[:]=r['qpos'][-1];e.data.qvel[:]=0;mujoco.mj_forward(e.model,e.data)
print('targets',c['targets'][0]);print('cut_site',e.data.site_xpos[e.model.site('cut_site').id])
for side,name in [('cut','cutter'),('catch','catcher')]:
 desired=np.array(c['targets'][0])+([-0.045,0,0] if side=='cut' else [0,0,-.098])+r['actions'][:,:6][:,0:3 if side=='cut' else 6].sum(0)[:3]*0 if False else None
 j=0 if side=='cut' else 3;desired=np.array(c['targets'][0])+([-0.045,0,0] if side=='cut' else [0,0,-.098])+r['actions'][:,j:j+3].sum(0)*.002
 print(side, 'desired',desired,'wrist_site',e.data.site_xpos[e.arms[side]['site']],'tool_center',e.data.site_xpos[e.model.site(name+'_center').id])
for contact in e.data.contact:
 names=[e.model.geom(int(g)).name for g in contact.geom]
 if contact.dist<-.0001:print('PENETRATION',contact.dist,names)
print('gateactions',np.max(r['actions'][:,6:],axis=0))
for side in ['cut','catch']:
 arm=e.arms[side];j=0 if side=='cut' else 3;target=np.array(c['targets'][0])+([-0.045,0,0] if side=='cut' else [0,0,-.098])+r['actions'][:,j:j+3].sum(0)*.002
 q,err=e.ik(side,target,e.data.qpos[arm['q']],300);print('IK',side,err,'q',q,'near bound',np.min(np.stack([q-arm['limits'][:,0],arm['limits'][:,1]-q])))
