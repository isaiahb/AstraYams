"""Physical two-arm cut-and-catch task; controller choice is external.

The stem integrity law is an uncalibrated force/work fracture surrogate, not
measured tissue mechanics. No pose/velocity edits occur on release.
"""
from pathlib import Path
import numpy as np,mujoco
from astrafactory.catcher_positioning import CatcherPositioningEnv
TASK=Path(__file__).resolve().parents[2]/'tasks/yam_dual_harvest_v1'

class DualHarvestEnv(CatcherPositioningEnv):
 def __init__(self,variation=0.,task_dir=TASK,cut_work_J=.0015):
  super().__init__(variation,task_dir,200.);m=self.model
  self.cq=np.array([m.joint(f'cut_joint{i}').qposadr[0] for i in range(1,7)]);self.cv=np.array([m.joint(f'cut_joint{i}').dofadr[0] for i in range(1,7)]);self.ca=np.array([m.actuator(f'cut_motor{i}').id for i in range(1,7)])
  self.climits=np.array([m.joint(f'cut_joint{i}').range for i in range(1,7)]);self.cutsite=m.site('cut_center').id;self.branch=m.body('cut_branch').id;self.freeadr=m.joint('cut_branch_free').qposadr[0];self.eq=m.equality('stem_integrity').id
  self.blades=[{i for i in range(m.ngeom) if (m.geom(i).name or '').startswith(f'cut_{side}_blade_contact')} for side in ['left','right']]
  self.cutstems={m.geom(n).id for n in ['proximal_cut_stem','distal_cut_stem']};self.net=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_FLEX,'catcher_net')
  self.allowed=np.zeros((m.ngeom,m.ngeom),dtype=bool)
  for a,b in self.permitted:self.allowed[a,b]=self.allowed[b,a]=True
  self.threshold=cut_work_J;self.excludes=m.exclude_signature.copy();self.cut_target=self.initial[self.cq].copy();self.jaw_target=-.007
 def servo(self):
  super().servo();m,d=self.model,self.data
  d.ctrl[self.ca]=np.clip(self.kp*(self.cut_target-d.qpos[self.cq])-self.kd*d.qvel[self.cv]+d.qfrc_bias[self.cv],-10,10)
  j=m.joint('cut_joint7');d.ctrl[m.actuator('cut_grip').id]=np.clip(2400*(self.jaw_target-d.qpos[j.qposadr[0]])-12*d.qvel[j.dofadr[0]],-30,30)
 def reset(self,*,seed=None,options=None):
  import gymnasium as gym
  gym.Env.reset(self,seed=seed);m,d=self.model,self.data;mujoco.mj_resetData(m,d);d.qpos[:]=self.initial;m.body_pos[:]=self.pos;m.body_quat[:]=self.quat;m.jnt_stiffness[:]=self.stiff;m.exclude_signature[:]=self.excludes
  v=self.variation;offset=self.np_random.uniform([-.02,-.02,-.012],[.02,.02,.012])*v;yaw=float(self.np_random.uniform(-.2,.2)*v);stiff=float(self.np_random.uniform(1-.15*v,1+.15*v));m.body_pos[self.frame]+=offset;m.body_quat[self.frame]=[np.cos(yaw/2),0,0,np.sin(yaw/2)];m.jnt_stiffness[:]*=stiff
  R=np.array([[np.cos(yaw),-np.sin(yaw),0],[np.sin(yaw),np.cos(yaw),0],[0,0,1]]);q=self.freeadr;d.qpos[q:q+3]=self.pos[self.frame]+offset+R@(self.initial[q:q+3]-self.pos[self.frame]);quat=np.zeros(4);mujoco.mju_mulQuat(quat,m.body_quat[self.frame],self.initial[q+3:q+7]);d.qpos[q+3:q+7]=quat
  self.cut_target=d.qpos[self.cq].copy();self.jaw_target=-.007;self.target=d.qpos[self.qids].copy();self.last=np.zeros(6);self.goal_velocity=np.zeros(3);self.hold=0;self.steps=0;self.episode_return=0.;self.peakwrong=0.;self.severed=False;self.work=0.;self.peak_net=0.;self.net_hold=0;self.cut_event=None;self.cut_time=None;self.peak_blade=0.;self.peak_interarm=0.;self.phase='position catcher';self.elapsed=0.;self.peak_depth=0.
  mujoco.mj_forward(m,d)
  for _ in range(round(.3/m.opt.timestep)):self.servo();mujoco.mj_step(m,d)
  mujoco.mj_forward(m,d);self.grip=self.grasp();self.previous_goal=self.geometry()[0].copy();self.previous_distance=float(np.linalg.norm(self.geometry()[0]-self.geometry()[1]));self.dr=dict(offset_m=offset.tolist(),yaw_rad=yaw,stiffness_scale=stiff);self.jaw_previous=sum(d.qpos[m.joint(n).qposadr[0]] for n in ['cut_joint7','cut_joint8']);self.last_cut=np.zeros(7)
  return self.observe(),dict(domain_randomization=self.dr,grasp=self.grip)
 def contacts(self):
  m,d=self.model,self.data;forces=[0.,0.];netforce=wrong=depth=interarm=0.
  geoms=d.contact.geom;valid=np.all(geoms>=0,axis=1);safe=np.maximum(geoms,0);bits=m.geom_contype[safe]
  relevant=valid & np.any((bits&14)!=0,axis=1)
  # Avoid scanning the many legitimate pad/handle contacts at every substep.
  relevant &= ~self.allowed[safe[:,0],safe[:,1]]
  netpairs=np.any(d.contact.flex==self.net,axis=1)&np.any(geoms==self.fruitgeom,axis=1)
  relevant |= netpairs
  for i in np.flatnonzero(relevant):
   c=d.contact[i];ids=set(int(x) for x in c.geom if x>=0);f=np.zeros(6);mujoco.mj_contactForce(m,d,int(i),f);force=float(np.linalg.norm(f[:3]))
   if netpairs[i]:netforce+=force;depth=max(depth,-float(c.dist));continue
   b=bits[i]
   if (b[0]&8 and b[1]&2) or (b[1]&8 and b[0]&2):interarm=max(interarm,force)
   bladepair=False
   for j,blade in enumerate(self.blades):
    if ids&blade and ids&self.cutstems:forces[j]+=max(float(f[0]),0.);bladepair=True
   if bladepair:continue
   if self.severed and self.fruitgeom in ids and np.any(b&4):continue
   wrong=max(wrong,force);depth=max(depth,-float(c.dist))
  return forces,netforce,wrong,depth,interarm
 def advance(self,catch_action=None,cut_action=None,allow_cut=True):
  m,d=self.model,self.data
  if catch_action is not None:
   a=np.clip(np.asarray(catch_action),-1,1);self.target=np.clip(self.target+a*.015,self.limits[:,0]+.001,self.limits[:,1]-.001);self.last=a.copy()
  if cut_action is not None:
   a=np.clip(np.asarray(cut_action),-1,1);self.cut_target=np.clip(self.cut_target+a[:6]*.008,self.climits[:,0]+.001,self.climits[:,1]-.001);self.jaw_target=float(np.clip(self.jaw_target+a[6]*.00025,-.009,-.0028));self.last_cut=a.copy()
  nf=wrong=depth=interarm=0.;bf=[0.,0.]
  for _ in range(self.skip):
   self.servo();mujoco.mj_step(m,d);forces,net,w,dep,inter=self.contacts();nf=max(nf,net);wrong=max(wrong,w);depth=max(depth,dep);interarm=max(interarm,inter);bf=np.maximum(bf,forces)
   jaws=sum(float(d.qpos[m.joint(n).qposadr[0]]) for n in ['cut_joint7','cut_joint8']);closing=max(0.,jaws-self.jaw_previous);self.jaw_previous=jaws
   if not self.severed and min(forces)>.1 and closing>0:
    self.work+=min(forces)*closing
    if allow_cut and self.work>=self.threshold:
     before_q=d.qpos.copy();before_v=d.qvel.copy();d.eq_active[self.eq]=0;self.severed=True;self.cut_time=float(d.time-.3)
     # Restore collision between the newly separated faces without removing either piece.
     a,b=sorted([m.body('secondary_b_5').id,self.branch]);signature=(a<<16)+b;m.exclude_signature[m.exclude_signature==signature]=0;m.exclude_signature[:]=np.sort(m.exclude_signature)
     self.cut_event=dict(time_s=self.cut_time,blade_force_N=list(map(float,forces)),work_J=self.work,threshold_J=self.threshold,qpos_jump=float(np.max(abs(d.qpos-before_q))),qvel_jump=float(np.max(abs(d.qvel-before_v))))
  mujoco.mj_forward(m,d);self.grip=self.grasp();goal,rim,normal=self.geometry();self.goal_velocity=(goal-self.previous_goal)/.02;self.previous_goal=goal.copy();dist=float(np.linalg.norm(goal-rim));self.steps+=1;self.elapsed=self.steps*.02
  gripvalid=min(self.grip['left_jaw_N'],self.grip['right_jaw_N'])>.2 and self.grip['tool_slip_m']<.005 and self.grip['tool_rotation_rad']<.15
  ready=dist<.005 and normal[2]>.96 and np.linalg.norm(d.qvel[self.vids])<.35 and gripvalid and wrong<.8
  self.hold=self.hold+1 if ready and not self.severed else 0
  R=d.xmat[self.tool].reshape(3,3);relative=R.T@(d.xipos[self.fruit]-rim);fv=np.zeros(6);mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,self.fruit,fv,0)
  contained=bool(self.severed and abs(relative[1])<.023 and abs(relative[2])<.027 and -.065<relative[0]<.015 and np.linalg.norm(fv[3:])<.1 and nf>.005 and gripvalid)
  self.net_hold=self.net_hold+1 if contained else 0;self.peak_net=max(self.peak_net,nf);self.peakwrong=max(self.peakwrong,wrong);self.peak_interarm=max(self.peak_interarm,interarm);self.peak_blade=max(self.peak_blade,*bf);self.peak_depth=max(self.peak_depth,depth)
  bad=bool(any(w.number for w in d.warning) or not np.isfinite(d.qpos).all() or self.grip['tool_slip_m']>.025 or self.grip['tool_rotation_rad']>.5 or wrong>.8 or interarm>.8)
  return dict(**{k:v for k,v in self.grip.items() if k not in ['wrong_contact_N']},phase=self.phase,sim_s=self.elapsed,is_success=self.net_hold>=25,invalid=bad,catcher_ready=self.hold>=20,severed=self.severed,cut_event=self.cut_event,cut_work_J=self.work,blade_forces_N=list(map(float,bf)),net_contact_N=nf,peak_net_N=self.peak_net,net_hold_steps=self.net_hold,peak_wrong_contact_N=self.peakwrong,wrong_contact_N=wrong,peak_interarm_N=self.peak_interarm,peak_penetration_m=self.peak_depth,cut_distance_m=float(np.linalg.norm(d.site_xpos[self.cutsite]-d.xpos[self.branch])),distance_m=dist,normal_z=float(normal[2]),hold_steps=self.hold,domain_randomization=self.dr)
