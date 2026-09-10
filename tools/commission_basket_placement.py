"""Offline path feasibility plus finite-motor commissioning, not learned movement."""
from pathlib import Path
import argparse,json,shutil,time
import numpy as np,mujoco
from scipy.optimize import least_squares
from astrafactory.harvest_basket import HarvestBasketEnv


def run(out,task):
 out.mkdir(parents=True,exist_ok=True);source=Path('runs/dual-harvest-commission-v13');shutil.copytree(task,out/'task',dirs_exist_ok=True)
 e=HarvestBasketEnv(task_dir=out/'task');e.reset(seed=61001);m,d=e.model,e.data;z=np.load(source/'episode-61001.npz');mapping=np.load(task/'source-qpos-map.npy');d.qpos[mapping]=z['qpos'][-1];d.qvel[:len(z['qvel'][-1])]=z['qvel'][-1];d.eq_active[:]=z['eq_active'][-1]
 e.target=z['catch_targets'][-1].copy();e.cut_target=z['cut_targets'][-1].copy();e.jaw_target=-.0028;e.severed=True;e.work=e.threshold;e.cut_time=0.
 a,b=sorted([m.body('secondary_b_5').id,e.branch]);m.exclude_signature[m.exclude_signature==(a<<16)+b]=0;m.exclude_signature[:]=np.sort(m.exclude_signature);mujoco.mj_forward(m,d)
 e.grip=e.grasp();e.previous_goal=e.geometry()[0].copy();e.basket_start=d.xpos[e.basket].copy();e.basket_quat=d.xquat[e.basket].copy()
 initial=d.qpos.copy();sid=m.site('initial_catcher_center').id;R0=d.site_xmat[sid].reshape(3,3).copy();p0=d.site_xpos[sid].copy();q0=d.qpos[e.qids].copy();lo=e.limits[:,0]+.05;hi=e.limits[:,1]-.05
 # Free yaw while retaining the actual upright support normal avoids a wrist limit.
 center=d.xpos[e.basket].copy();high=center+[.04,0,.09];low=center+[.04,0,.065]
 plan=[];prev=q0.copy()
 for stage,positions in [('carry',np.linspace(p0,high,60)[1:]),('lower',np.linspace(high,low,20)[1:])]:
  for position in positions:
   def residual(q):
    d.qpos[e.qids]=q;mujoco.mj_kinematics(m,d);R=d.site_xmat[sid].reshape(3,3)
    return np.r_[30*(d.site_xpos[sid]-position),3*(R[:,0]-R0[:,0]),.004*(q-prev)]
   fit=least_squares(residual,prev,bounds=(lo,hi),max_nfev=80);residual(fit.x)
   assert np.linalg.norm(d.site_xpos[sid]-position)<.0005,'Unreachable basket path'
   assert np.linalg.norm(d.site_xmat[sid].reshape(3,3)[:,0]-R0[:,0])<.005,'Unreachable support normal'
   prev=fit.x.copy();plan.append((stage,prev.copy(),position.copy(),d.site_xmat[sid].reshape(3,3).copy()))
 unload_start=prev.copy()
 for angle in np.linspace(0,1.85,160)[1:]:
  q=unload_start.copy();q[-1]-=angle;assert np.all(q>lo) and np.all(q<hi)
  d.qpos[e.qids]=q;mujoco.mj_kinematics(m,d);plan.append(('unload',q,d.site_xpos[sid].copy(),d.site_xmat[sid].reshape(3,3).copy()))
 d.qpos[:]=initial;mujoco.mj_forward(m,d)
 rows=[];qs=[d.qpos.copy()];vs=[d.qvel.copy()];ctrl=[d.ctrl.copy()];targets=[e.target.copy()];cuts=[e.cut_target.copy()];flex=[d.flexvert_xpos.copy()];eqs=[d.eq_active.copy()];start=time.time();index=0
 for step in range(1600):
  stage,qgoal,goal,R=plan[index];delta=qgoal-e.target
  # Uniform scaling retains the direction and bounds the joint target speed.
  scale=min(1.,.004/max(1e-9,float(np.max(abs(delta)))));e.target+=delta*scale
  if np.max(abs(d.qpos[e.qids]-qgoal))<.004 and np.max(abs(delta))<.002:index=min(index+1,len(plan)-1)
  e.phase='Scripted commissioning / '+stage;info=e.advance();info.update(goal_position=goal.tolist(),goal_rotation=R.ravel().tolist(),stage=stage,path_index=index)
  rows.append(info);qs.append(d.qpos.copy());vs.append(d.qvel.copy());ctrl.append(d.ctrl.copy());targets.append(e.target.copy());cuts.append(e.cut_target.copy());flex.append(d.flexvert_xpos.copy());eqs.append(d.eq_active.copy())
  if step%100==0:print(step,stage,index,'pos',d.site_xpos[e.site],'score',info['gentleness_score'],'contact',info['peak_unexpected_contact'],flush=True)
  if info['invalid'] or info['placement_success']:break
 np.savez_compressed(out/'episode-61001.npz',qpos=qs,qvel=vs,controls=ctrl,catch_targets=targets,cut_targets=cuts,eq_active=eqs,flex_vertices=flex,t=np.arange(len(qs))*.02)
 result=dict(**info,seed=61001,wall_s=time.time()-start,controller='Scripted basket commissioning from recorded cut-and-caught state; offline IK path, finite motor forces. No learned carry/unload claim.')
 (out/'episode-61001.json').write_text(json.dumps(dict(result=result,trace=rows),indent=2)+'\n');print('RESULT',json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('runs/harvest-skill-suite/basket-commission-v3'));p.add_argument('--task',type=Path,default=Path('runs/harvest-skill-suite/basket-task-v3'));a=p.parse_args();run(a.out,a.task)
