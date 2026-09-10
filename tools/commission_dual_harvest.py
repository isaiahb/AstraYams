"""Explicit commissioning diagnostic: learned catcher, scripted cutter motion.
No end-to-end PPO claim. Used to verify tools, interactions and task geometry.
"""
import argparse,json,time,shutil
from pathlib import Path
import numpy as np,mujoco
from astrafactory.dual_harvest import DualHarvestEnv,TASK
from export_catcher_demonstrations import predict

def run(seed=61001,variation=0.,out=Path('runs/dual-harvest-commission-v1'),allow_cut=True):
 out.mkdir(exist_ok=True,parents=True);shutil.copytree(TASK,out/'task',dirs_exist_ok=True);scene=out/'task/scene.xml';scene.write_text(scene.read_text().replace(str(TASK),str((out/'task').resolve())));e=DualHarvestEnv(variation,task_dir=out/'task');o,_=e.reset(seed=seed);m,d=e.model,e.data;weights=np.load('runs/catcher-specialist-v3/synthetic-demonstrations/actor.npz');qs=[d.qpos.copy()];vs=[d.qvel.copy()];trace=[];flex=[d.flexvert_xpos.copy()];eq=[d.eq_active.copy()];stage=0;Rdesired=d.site_xmat[e.cutsite].reshape(3,3).copy();start=time.time()
 from astrafactory.yam_env import rotation_error
 for step in range(650):
  if stage==0:
   a=predict(weights,e.observe());e.phase='PPO / position catcher';info=e.advance(catch_action=a,allow_cut=allow_cut)
   if info['catcher_ready']:stage=1
  else:
   p=d.site_xpos[e.cutsite];goal=d.xpos[e.branch].copy();err=goal-p
   if stage==1:
    e.phase='Commissioning / align cutter';jp=np.zeros((3,m.nv));jr=jp.copy();mujoco.mj_jacSite(m,d,jp,jr,e.cutsite);error=np.r_[err,rotation_error(Rdesired,d.site_xmat[e.cutsite].reshape(3,3))*.1];J=np.r_[jp[:,e.cv],jr[:,e.cv]*.1];dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-5,error);e.cut_target=np.clip(e.cut_target+np.clip(d.qpos[e.cq]+dq*.7-e.cut_target,-.006,.006),e.climits[:,0]+.01,e.climits[:,1]-.01)
    if np.linalg.norm(err)<.0009 and np.linalg.norm(d.qvel[e.cv])<.15:stage=2
   elif stage==2:
    e.phase='Commissioning / close stock jaws';e.jaw_target=min(-.0028,e.jaw_target+.00003)
    if e.severed:stage=3
   else:e.phase='Physics / receive and retain berry'
   info=e.advance(allow_cut=allow_cut)
  qs.append(d.qpos.copy());vs.append(d.qvel.copy());flex.append(d.flexvert_xpos.copy());eq.append(d.eq_active.copy());trace.append(info)
  if step%50==0:print(step,info['phase'],'cut error',round(info['cut_distance_m']*1000,2),'work',round(info['cut_work_J'],6),'net',round(info['net_contact_N'],3),'wrong',round(info['wrong_contact_N'],2),flush=True)
  if info['invalid'] or info['is_success']:break
 np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,qvel=vs,flex_vertices=flex,eq_active=eq,t=np.arange(len(qs))*.02)
 result=dict(seed=seed,wall_s=time.time()-start,controller='Frozen PPO catcher; scripted Jacobian cutter commissioning; finite-torque motors; event-driven fracture surrogate.',**info)
 (out/f'episode-{seed}.json').write_text(json.dumps(dict(result=result,trace=trace),indent=2)+'\n');print('RESULT',json.dumps(result),flush=True)
 # Contact diagnostics make every invalid result inspectable.
 cs=[]
 for i in range(d.ncon):
  c=d.contact[i];f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f)
  if f[0]>.05:cs.append(dict(geoms=[m.geom(int(g)).name if g>=0 else 'flex' for g in c.geom],flex=c.flex.tolist(),force=float(f[0]),depth=float(-c.dist)))
 (out/'terminal-contacts.json').write_text(json.dumps(cs,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=61001);p.add_argument('--variation',type=float,default=0.);p.add_argument('--out',type=Path,default=Path('runs/dual-harvest-commission-v1'));p.add_argument('--no-cut',action='store_true');a=p.parse_args();run(a.seed,a.variation,a.out,not a.no_cut)
