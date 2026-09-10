"""Explicit commissioning diagnostic: learned catcher, scripted cutter motion.
No end-to-end PPO claim. Used to verify tools, interactions and task geometry.
"""
import argparse,json,time,shutil,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,mujoco
from astrafactory.dual_harvest import DualHarvestEnv,TASK
from export_catcher_demonstrations import predict

def run(seed=61001,variation=0.,out=Path('runs/dual-harvest-commission-v1'),allow_cut=True,drop_test=False,timestep=None,postcut_seconds=2.):
 out.mkdir(exist_ok=True,parents=True);shutil.copytree(TASK,out/'task',dirs_exist_ok=True);scene=out/'task/scene.xml';scene.write_text(scene.read_text().replace(str(TASK),str((out/'task').resolve())))
 if timestep is not None:
  tree=ET.parse(scene);tree.getroot().find('option').set('timestep',str(timestep));tree.write(scene,encoding='unicode')
 sources=out/'sources';sources.mkdir(exist_ok=True)
 for path in [Path(__file__),Path('src/astrafactory/dual_harvest.py'),Path('src/astrafactory/catcher_positioning.py')]:shutil.copy2(path,sources/path.name)
 e=DualHarvestEnv(variation,task_dir=out/'task');o,_=e.reset(seed=seed);m,d=e.model,e.data;weights=np.load('runs/catcher-specialist-v3/synthetic-demonstrations/actor.npz');qs=[d.qpos.copy()];vs=[d.qvel.copy()];targets=[e.target.copy()];cut_targets=[e.cut_target.copy()];controls=[d.ctrl.copy()];trace=[];flex=[d.flexvert_xpos.copy()];eq=[d.eq_active.copy()];stage=0;Rdesired=d.site_xmat[e.cutsite].reshape(3,3).copy();start=time.time();withdraw_goal=None
 from astrafactory.yam_env import rotation_error
 for step in range(650):
  if stage==0:
   a=predict(weights,e.observe());e.phase='PPO / position catcher';info=e.advance(catch_action=a,allow_cut=allow_cut)
   if info['catcher_ready']:
    stage=1
    if drop_test:
     d.eq_active[e.eq]=0;e.severed=True;e.cut_time=float(d.time-.3);stage=3;e.cut_event=dict(kind='Externally released attachment: net bench test, no cutter claim',time_s=e.cut_time)
     a,b=sorted([m.body('secondary_b_5').id,e.branch]);m.exclude_signature[m.exclude_signature==(a<<16)+b]=0;m.exclude_signature[:]=np.sort(m.exclude_signature)
  else:
   p=d.site_xpos[e.cutsite];goal=d.xpos[e.branch].copy();err=goal-p
   if stage==2 and e.severed:stage=3
   if stage==1:
    e.phase='Commissioning / align cutter';jp=np.zeros((3,m.nv));jr=jp.copy();mujoco.mj_jacSite(m,d,jp,jr,e.cutsite);error=np.r_[err,rotation_error(Rdesired,d.site_xmat[e.cutsite].reshape(3,3))*.1];J=np.r_[jp[:,e.cv],jr[:,e.cv]*.1];dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-5,error);e.cut_target=np.clip(e.cut_target+np.clip(d.qpos[e.cq]+dq*.7-e.cut_target,-.006,.006),e.climits[:,0]+.01,e.climits[:,1]-.01)
    if np.linalg.norm(err)<.0009 and np.linalg.norm(d.qvel[e.cv])<.15:stage=2
   elif stage==2:
    e.phase='Commissioning / close stock jaws';e.jaw_target=min(-.0028,e.jaw_target+.00003)
    if e.severed:stage=3
   else:
    e.phase='Physics / receive and retain berry'
    if not drop_test:
     # Joint interpolation dipped the blade into the recoiling neighbor.
     # Withdraw upward and back in Cartesian space through finite motor torques.
     if withdraw_goal is None:withdraw_goal=p.copy()+Rdesired[:,2]*.035+np.array([0,0,.02])
     jp=np.zeros((3,m.nv));jr=jp.copy();mujoco.mj_jacSite(m,d,jp,jr,e.cutsite)
     error=np.r_[withdraw_goal-p,rotation_error(Rdesired,d.site_xmat[e.cutsite].reshape(3,3))*.1];J=np.r_[jp[:,e.cv],jr[:,e.cv]*.1]
     dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-5,error)
     e.cut_target=np.clip(e.cut_target+np.clip(d.qpos[e.cq]+.7*dq-e.cut_target,-.008,.008),e.climits[:,0]+.01,e.climits[:,1]-.01)
   info=e.advance(allow_cut=allow_cut)
  qs.append(d.qpos.copy());vs.append(d.qvel.copy());targets.append(e.target.copy());cut_targets.append(e.cut_target.copy());controls.append(d.ctrl.copy());flex.append(d.flexvert_xpos.copy());eq.append(d.eq_active.copy());trace.append(info)
  if step%50==0:print(step,info['phase'],'cut error',round(info['cut_distance_m']*1000,2),'work',round(info['cut_work_J'],6),'net',round(info['net_contact_N'],3),'wrong',round(info['wrong_contact_N'],2),flush=True)
  if info['invalid'] or (info['is_success'] and e.cut_time is not None and info['sim_s']-e.cut_time>=postcut_seconds):break
 np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,qvel=vs,catch_targets=targets,cut_targets=cut_targets,controls=controls,flex_vertices=flex,eq_active=eq,t=np.arange(len(qs))*.02)
 result=dict(seed=seed,physics_timestep_s=float(m.opt.timestep),postcut_observation_s=None if e.cut_time is None else info['sim_s']-e.cut_time,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources.iterdir()},wall_s=time.time()-start,controller=('Net bench test: PPO places catcher, external attachment release tests passive catch. No cutting claim.' if drop_test else 'Frozen PPO catcher; scripted Jacobian cutter commissioning; finite-torque motors; event-driven fracture surrogate.'),**info)
 (out/f'episode-{seed}.json').write_text(json.dumps(dict(result=result,trace=trace),indent=2)+'\n');print('RESULT',json.dumps(result),flush=True)
 # Contact diagnostics make every invalid result inspectable.
 cs=[]
 for i in range(d.ncon):
  c=d.contact[i];f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f)
  if f[0]>.05:cs.append(dict(geoms=[m.geom(int(g)).name if g>=0 else 'flex' for g in c.geom],flex=c.flex.tolist(),force=float(f[0]),depth=float(-c.dist)))
 (out/'terminal-contacts.json').write_text(json.dumps(cs,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=61001);p.add_argument('--variation',type=float,default=0.);p.add_argument('--out',type=Path,default=Path('runs/dual-harvest-commission-v1'));p.add_argument('--no-cut',action='store_true');p.add_argument('--drop-test',action='store_true');p.add_argument('--timestep',type=float);p.add_argument('--postcut-seconds',type=float,default=2.);a=p.parse_args();run(a.seed,a.variation,a.out,not a.no_cut,a.drop_test,a.timestep,a.postcut_seconds)
