"""Composable PPO joint skills with explicit physical entry/exit contracts."""
from pathlib import Path
import json,numpy as np,mujoco,gymnasium as gym
from gymnasium import spaces
from scipy.spatial.transform import Rotation
from astrafactory.dual_harvest import DualHarvestEnv
from astrafactory.harvest_basket import HarvestBasketEnv
from astrafactory.yam_env import rotation_error

class HarvestJointSkill(gym.Env):
 def __init__(self,skill='withdraw',source='runs/dual-harvest-commission-v13',curriculum=None,difficulty=0.,variation=1.):
  self.skill=skill;self.source=Path(source);task=Path(curriculum) if curriculum else self.source/'task';self.e=(HarvestBasketEnv if skill in ['carry','unload'] else DualHarvestEnv)(task_dir=task);self.e.reset(seed=0);self.z=np.load(self.source/'episode-61001.npz');self.trace=json.loads((self.source/'episode-61001.json').read_text())['trace'];self.difficulty=difficulty;self.variation=variation
  self.qmap=np.load(task/'qpos-map.npy') if (task/'qpos-map.npy').exists() else np.arange(self.e.model.nq);self.vmap=np.load(task/'qvel-map.npy') if (task/'qvel-map.npy').exists() else np.arange(self.e.model.nv)
  e=self.e;m,d=e.model,e.data;self.cutter=skill in ['approach','withdraw'];self.qids=e.cq if self.cutter else e.qids;self.vids=e.cv if self.cutter else e.vids;self.site=e.cutsite if self.cutter else e.site;self.body=m.site_bodyid[self.site]
  if skill=='withdraw':
   self.begin=next(i for i,r in enumerate(self.trace) if r['severed'])+1;self.end=min(len(self.trace)-1,self.begin+60)
  elif skill=='approach':
   self.begin=next(i for i,r in enumerate(self.trace) if r['catcher_ready'])+1;self.end=next(i for i,r in enumerate(self.trace) if r['phase']=='Commissioning / close stock jaws')
  elif skill=='carry':
   self.begin=0;self.end=next(i for i,r in enumerate(self.trace) if r.get('stage')=='unload')
  else:
   self.begin=next(i for i,r in enumerate(self.trace) if r.get('stage')=='unload');self.end=max(self.begin,next((i for i,r in enumerate(self.trace) if r.get('placement_contact',False) or r.get('placement_peak_N',0)>.01),len(self.trace)-1)-8)
  d.qpos[:]=self.z['qpos'][self.begin,self.qmap];mujoco.mj_forward(m,d);self.reference_R=d.xmat[self.body].reshape(3,3).copy()
  if skill=='approach':
   d.qpos[:]=self.z['qpos'][self.end,self.qmap];mujoco.mj_forward(m,d);self.goal_base=d.site_xpos[self.site].copy();self.goal_R=d.xmat[self.body].reshape(3,3).copy()
  elif skill=='withdraw':self.goal_base=d.site_xpos[self.site]+self.reference_R[:,2]*.035+[0,0,.020];self.goal_R=self.reference_R.copy()
  else:
   goal_row=self.trace[self.end if skill=='carry' else -1]
   self.goal_base=np.array(goal_row['goal_position']);self.goal_R=np.array(goal_row['goal_rotation']).reshape(3,3)
  self.reference_q=e.initial[self.qids].copy()
  self.action_space=spaces.Box(-1,1,(6,),np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(87 if skill in ['carry','unload'] else 67,),np.float32);self.info={};self.last=np.zeros(6)
 def geometry(self):
  e=self.e;return self.goal-e.data.site_xpos[self.site],rotation_error(self.goal_R,e.data.xmat[self.body].reshape(3,3))
 def obstacles(self):
  e=self.e;m,d=e.model,e.data;p=d.site_xpos[self.site];result=[]
  for category in ['berry_','_surface']:
   ids=[g for g in range(m.ngeom) if (m.geom(g).name.startswith(category) if category=='berry_' else m.geom(g).name.endswith(category) and m.geom_contype[g]==1) and g not in e.cutstems and g!=e.fruitgeom]
   ids=sorted(ids,key=lambda g:float(np.linalg.norm(d.geom_xpos[g]-p)))[:4]
   for g in ids:result.extend([*(10*(d.geom_xpos[g]-p)),float(m.geom_rbound[g]*10)])
   result.extend([0.]*(4-len(ids))*4)
  return result
 def observe(self):
  e=self.e;d=e.data;delta,rot=self.geometry();targets=e.cut_target if self.cutter else e.target;quality=np.clip(min(e.grip['left_jaw_N'],e.grip['right_jaw_N'])/5,0,1)
  base=np.r_[d.qpos[self.qids]-self.reference_q,d.qvel[self.vids],(targets-d.qpos[self.qids])*10,delta*20,np.array([0,0,1])+rot,np.zeros(3),self.last,quality,min(self.hold,10)/10,self.obstacles()]
  if self.skill in ['carry','unload']:
   # Observe the payload and receiving contacts, not just an end-effector pose.
   v=np.zeros(6);mujoco.mj_objectVelocity(e.model,d,mujoco.mjtObj.mjOBJ_BODY,e.fruit,v,0)
   base=np.r_[base,20*(d.xipos[e.fruit]-d.site_xpos[e.site]),v,
    self.info.get('net_contact_N',0.),e.current_basket_force,float(e.placement_contact),
    min(e.placement_hold,25)/25,e.impact_energy_J*1000,e.placement_impulse_Ns*50,e.placement_peak_N,
    10*(d.xipos[e.fruit]-d.xpos[e.basket]),min(e.net_hold,25)/25]
  return base.astype(np.float32)
 def reset(self,*,seed=None,options=None):
  super().reset(seed=seed);e=self.e;m,d=e.model,e.data;mujoco.mj_resetData(m,d);d.time=.3;m.exclude_signature[:]=e.excludes;m.body_pos[:]=e.pos;m.body_quat[:]=e.quat;m.jnt_stiffness[:]=e.stiff
  index=round(self.end*(1-self.difficulty)+self.begin*self.difficulty);d.qpos[:]=self.z['qpos'][index,self.qmap];d.qvel[:]=self.z['qvel'][index,self.vmap];d.eq_active[:]=self.z['eq_active'][index]
  e.target=self.z['catch_targets'][index].copy();e.cut_target=self.z['cut_targets'][index].copy();e.jaw_target=-.007 if self.skill=='approach' else -.0028;e.severed=not bool(d.eq_active[e.eq]);e.work=e.threshold if e.severed else 0.;e.cut_time=0.;e.cut_event=None
  if e.severed:
   a,b=sorted([m.body('secondary_b_5').id,e.branch]);m.exclude_signature[m.exclude_signature==(a<<16)+b]=0;m.exclude_signature[:]=np.sort(m.exclude_signature)
  jitter=self.np_random.uniform(-.002,.002,6)*self.variation;d.qpos[self.qids]+=jitter;self.goal=self.goal_base+self.np_random.uniform(-.002,.002,3)*self.variation
  e.last=np.zeros(6);e.goal_velocity=np.zeros(3);e.hold=0;e.steps=0;e.episode_return=0.;e.peakwrong=0.;e.peak_net=0.;e.net_hold=0;e.peak_blade=0.;e.peak_interarm=0.;e.phase='PPO / '+self.skill;e.elapsed=0.;e.peak_depth=0.;e.last_cut=np.zeros(7);e.receive_peak=0.;e.contact_peak=dict(force_N=0.,geoms=[],time_s=0.);e.neighbor_peak=e.contact_peak.copy();e.dr=dict(offset_m=[0,0,0],yaw_rad=0.,stiffness_scale=1.,joint_entry_offset_rad=jitter.tolist(),goal_offset_m=(self.goal-self.goal_base).tolist(),reset_frame=index)
  mujoco.mj_forward(m,d);e.grip=e.grasp();e.previous_goal=e.geometry()[0].copy();e.jaw_previous=sum(d.qpos[m.joint(n).qposadr[0]] for n in ['cut_joint7','cut_joint8'])
  if self.skill in ['carry','unload']:e.clear_metrics();e.basket_start=d.xpos[e.basket].copy();e.basket_quat=d.xquat[e.basket].copy()
  self.steps=0;self.hold=0;self.last=np.zeros(6);self.info={};self.previous_impact_cost=0.;delta,rot=self.geometry();self.previous_cost=np.linalg.norm(delta)+.025*np.linalg.norm(rot)
  return self.observe(),dict(domain_randomization=e.dr)
 def step(self,action):
  a=np.clip(np.asarray(action,dtype=float),-1,1);e=self.e
  if a.shape!=(6,) or not np.isfinite(a).all():raise ValueError('Six finite joint actions required')
  info=e.advance(cut_action=np.r_[a,0.] if self.cutter else None,catch_action=a if not self.cutter else None)
  return self.after_step(a,info)
 def after_step(self,a,info):
  e=self.e;self.info=dict(info);delta,rot=self.geometry();cost=float(np.linalg.norm(delta)+.025*np.linalg.norm(rot));self.steps+=1
  if self.skill=='approach' and e.severed:self.info.update(invalid=True,unexpected_separation=True)
  good=np.linalg.norm(delta)<.004 and np.linalg.norm(rot)<.06 and np.linalg.norm(e.data.qvel[self.vids])<.15 and not self.info['invalid'];self.hold=self.hold+1 if good else 0
  success=bool(self.info.get('placement_success',False)) if self.skill=='unload' else self.hold>=10
  if self.skill=='carry':success=success and e.net_hold>=10
  reward=250*(self.previous_cost-cost)-8*cost-.03-.002*float(a@a)+(.2 if good else 0.)
  if success:reward+=150
  if self.skill=='unload':
   impact_cost=10*self.info['impact_energy_J']/.001+self.info['placement_peak_N']+20*self.info['placement_impulse_Ns']
   reward-=max(0.,impact_cost-self.previous_impact_cost);self.previous_impact_cost=impact_cost
   if success:reward+=.5*self.info['gentleness_score']
  if self.info['invalid']:reward-=100
  self.info.update(is_success=success,skill=self.skill,goal_error_m=float(np.linalg.norm(delta)),orientation_error_rad=float(np.linalg.norm(rot)),skill_hold_steps=self.hold);self.previous_cost=cost;self.last=a.copy()
  return self.observe(),float(reward),bool(success or self.info['invalid']),self.steps>=250,self.info
 def close(self):self.e.close()
