"""Joint-and-jaw PPO for a local approach/clip skill. No runtime IK or BC.

A recorded physical reset curriculum initializes the task. Optional frozen
canopy/net curriculum is explicitly approximate; full-scene evaluation is separate.
"""
from pathlib import Path
import json,numpy as np,mujoco,gymnasium as gym
from gymnasium import spaces
from astrafactory.dual_harvest import DualHarvestEnv
from astrafactory.yam_env import rotation_error

class CutterSkillEnv(gym.Env):
 def __init__(self,source='runs/dual-harvest-commission-v13',difficulty=0.,variation=1.,curriculum=None,joint_scale=1.):
  self.joint_scale=float(joint_scale)
  self.source=Path(source);task=Path(curriculum) if curriculum else self.source/'task';self.e=DualHarvestEnv(task_dir=task);self.e.reset(seed=0)
  self.z=np.load(self.source/'episode-61001.npz');self.trace=json.loads((self.source/'episode-61001.json').read_text())['trace'];self.difficulty=difficulty;self.variation=variation
  self.qmap=np.load(task/'qpos-map.npy') if curriculum else np.arange(self.e.model.nq);self.vmap=np.load(task/'qvel-map.npy') if curriculum else np.arange(self.e.model.nv)
  self.start=next(i for i,x in enumerate(self.trace) if x['catcher_ready'])+1;self.aligned=next(i for i,x in enumerate(self.trace) if x['phase']=='Commissioning / close stock jaws')
  self.near_cut=next(i for i,x in enumerate(self.trace) if x['severed'])-3
  self.action_space=spaces.Box(-1,1,(7,),np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(38,),np.float32);self.info={};self.last=np.zeros(7)
  d=self.e.data;d.qpos[:]=self.z['qpos'][self.aligned,self.qmap];mujoco.mj_forward(self.e.model,d);self.R=d.site_xmat[self.e.cutsite].reshape(3,3).copy()
 def geometry(self):
  e=self.e;d=e.data;return d.xpos[e.branch]-d.site_xpos[e.cutsite],rotation_error(self.R,d.site_xmat[e.cutsite].reshape(3,3))
 def observe(self):
  e=self.e;d=e.data;error,rot=self.geometry();j=e.model.joint('cut_joint7')
  return np.r_[d.qpos[e.cq]-e.initial[e.cq],d.qvel[e.cv],(e.cut_target-d.qpos[e.cq])*20,error*50,rot,(d.qpos[j.qposadr[0]]+.007)*200,(e.jaw_target+.007)*200,self.last,np.array(self.info.get('blade_forces_N',[0,0]))/5,min(e.work/e.threshold,1),float(e.severed),0.].astype(np.float32)
 def reset(self,*,seed=None,options=None):
  super().reset(seed=seed);e=self.e;m,d=e.model,e.data;mujoco.mj_resetData(m,d);m.exclude_signature[:]=e.excludes;m.body_pos[:]=e.pos;m.body_quat[:]=e.quat;m.jnt_stiffness[:]=e.stiff
  index=round(self.near_cut*(1-2*self.difficulty)+self.aligned*(2*self.difficulty)) if self.difficulty<=.5 else round(self.aligned*(2-2*self.difficulty)+self.start*(2*self.difficulty-1));d.qpos[:]=self.z['qpos'][index,self.qmap];d.qvel[:]=self.z['qvel'][index,self.vmap];d.time=.3
  e.target=self.z['catch_targets'][index].copy();e.cut_target=self.z['cut_targets'][index].copy();e.jaw_target=float(np.clip(d.qpos[m.joint('cut_joint7').qposadr[0]],-.007,-.0028))
  jitter=self.np_random.uniform(-.003,.003,6)*self.variation;d.qpos[e.cq]+=jitter;e.cut_target=d.qpos[e.cq].copy();stiff=float(self.np_random.uniform(.85,1.15));m.jnt_stiffness[:]*=stiff
  e.dr=dict(offset_m=[0,0,0],yaw_rad=0.,stiffness_scale=stiff,cutter_joint_offset_rad=jitter.tolist(),reset_frame=int(index));e.last=np.zeros(6);e.goal_velocity=np.zeros(3);e.hold=0;e.steps=0;e.episode_return=0.;e.peakwrong=0.;e.severed=False;e.work=float(self.trace[max(0,index-1)]['cut_work_J']);e.peak_net=0.;e.net_hold=0;e.cut_event=None;e.cut_time=None;e.peak_blade=0.;e.peak_interarm=0.;e.phase='PPO / cutter approach and jaw control';e.elapsed=0.;e.peak_depth=0.;e.last_cut=np.zeros(7);e.receive_peak=0.
  e.contact_peak=dict(force_N=0.,geoms=[],time_s=0.);e.neighbor_peak=e.contact_peak.copy()
  mujoco.mj_forward(m,d);e.grip=e.grasp();e.previous_goal=e.geometry()[0].copy();e.jaw_previous=sum(d.qpos[m.joint(n).qposadr[0]] for n in ['cut_joint7','cut_joint8']);self.last=np.zeros(7);self.info={};self.steps=0;self.previous_distance=float(np.linalg.norm(self.geometry()[0]));self.previous_work=e.work;self.previous_jaw=float(d.qpos[m.joint('cut_joint7').qposadr[0]])
  return self.observe(),dict(domain_randomization=e.dr)
 def step(self,action):
  a=np.asarray(action,dtype=float)
  if a.shape!=(7,) or not np.isfinite(a).all():raise ValueError('Seven finite joint/jaw commands required')
  a=np.clip(a,-1,1);e=self.e;command=a.copy();command[:6]*=self.joint_scale;info=e.advance(cut_action=command)
  return self.after_step(a,info)
 def after_step(self,a,info):
  e=self.e;self.info=dict(info);error,rot=self.geometry();distance=float(np.linalg.norm(error));self.steps+=1;jaw=float(e.data.qpos[e.model.joint('cut_joint7').qposadr[0]])
  reward=250*(self.previous_distance-distance)+.1*np.exp(-distance/.006)-8*distance-.08-.2*np.linalg.norm(rot)-.002*np.square(a).sum()
  if distance<.004:reward+=8*(jaw-self.previous_jaw)/.0042
  elif jaw>-.006:reward-=.4
  reward+=10*(e.work-self.previous_work)/e.threshold
  success=bool(e.severed and not self.info['invalid'])
  if success:reward+=100
  if self.info['invalid']:reward-=100
  self.previous_distance=distance;self.previous_work=e.work;self.previous_jaw=jaw;self.last=a.copy();self.info.update(is_success=success,cutter_goal_error_m=distance,rotation_error_rad=float(np.linalg.norm(rot)))
  return self.observe(),float(reward),bool(success or self.info['invalid']),self.steps>=180,self.info
 def close(self):self.e.close()
