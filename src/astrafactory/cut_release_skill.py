"""Learn to release a physically severed stalk into the other arm's net."""
from pathlib import Path
import json,numpy as np,mujoco,gymnasium as gym
from gymnasium import spaces
from astrafactory.dual_harvest import DualHarvestEnv

class CutReleaseSkill(gym.Env):
 def __init__(self,source='runs/harvest-skill-suite/partial-chain-v5',curriculum=None,variation=1.):
  self.source=Path(source);task=Path(curriculum) if curriculum else self.source/'task';self.e=DualHarvestEnv(task_dir=task);self.e.reset(seed=0);episode=sorted(self.source.glob('episode-*.npz'))[0];self.z=np.load(episode);self.trace=json.loads(episode.with_suffix('.json').read_text())['trace'];self.index=next(i for i,r in enumerate(self.trace) if r['severed'])+1
  self.qmap=np.load(task/'qpos-map.npy') if curriculum else np.arange(self.e.model.nq);self.vmap=np.load(task/'qvel-map.npy') if curriculum else np.arange(self.e.model.nv);self.variation=variation;self.action_space=spaces.Box(-1,1,(1,),np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(15,),np.float32)
  jaw=-.007
  for a in self.z['actions'][:self.index]:jaw=float(np.clip(jaw+float(a[-1])*.00025,-.009,-.0028))
  self.entry_jaw=jaw;self.info={};self.last=0.
 def observe(self):
  e=self.e;m,d=e.model,e.data;j=m.joint('cut_joint7');v=np.zeros(6);mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,e.fruit,v,0)
  return np.r_[(d.qpos[j.qposadr[0]]+.007)*200,(e.jaw_target+.007)*200,d.qvel[j.dofadr[0]]*10,20*(d.xipos[e.fruit]-d.site_xpos[e.site]),v[3:]*5,np.array(self.info.get('blade_forces_N',[0,0]))/5,self.info.get('net_contact_N',0),min(e.net_hold,25)/25,min(e.grip['left_jaw_N'],e.grip['right_jaw_N'])/10,self.last].astype(np.float32)
 def reset(self,*,seed=None,options=None):
  super().reset(seed=seed);e=self.e;e.reset(seed=seed);m,d=e.model,e.data;d.qpos[:]=self.z['qpos'][self.index,self.qmap];d.qvel[:]=self.z['qvel'][self.index,self.vmap];d.eq_active[:]=self.z['eq_active'][self.index];e.target=self.z['catch_targets'][self.index].copy();e.cut_target=self.z['cut_targets'][self.index].copy();e.jaw_target=self.entry_jaw;e.severed=True;e.work=float(self.trace[self.index-1]['cut_work_J']);e.cut_time=0.;e.cut_event=None
  a,b=sorted([m.body('secondary_b_5').id,e.branch]);m.exclude_signature[m.exclude_signature==(a<<16)+b]=0;m.exclude_signature[:]=np.sort(m.exclude_signature)
  # Small encoder-entry uncertainty; no object pose edits after the episode starts.
  jitter=self.np_random.uniform(-.001,.001,6)*self.variation;d.qpos[e.cq]+=jitter;e.dr.update(cutter_joint_offset_rad=jitter.tolist(),reset_frame=self.index,source=str(self.source))
  mujoco.mj_forward(m,d);e.grip=e.grasp();e.previous_goal=e.geometry()[0].copy();e.jaw_previous=sum(d.qpos[m.joint(n).qposadr[0]] for n in ['cut_joint7','cut_joint8']);self.bind(e);return self.observe(),dict(domain_randomization=e.dr)
 def bind(self,e):
  self.e=e;self.last=0.;self.info={};self.steps=0;self.previous_jaw=float(e.data.qpos[e.model.joint('cut_joint7').qposadr[0]])
 def step(self,action):
  a=np.clip(np.asarray(action,float),-1,1)
  if a.shape!=(1,) or not np.isfinite(a).all():raise ValueError('One finite learned jaw command required')
  info=self.e.advance(cut_action=np.r_[np.zeros(6),a]);return self.after_step(a,info)
 def after_step(self,a,info):
  e=self.e;self.info=dict(info);self.steps+=1;jaw=float(e.data.qpos[e.model.joint('cut_joint7').qposadr[0]]);success=bool(e.net_hold>=25 and jaw<-.0065 and not info['invalid']);reward=3*(self.previous_jaw-jaw)/.0042-.02-.002*float(a[0]**2)
  if success:reward+=100
  if info['invalid']:reward-=100
  self.last=float(a[0]);self.previous_jaw=jaw;self.info.update(is_success=success,skill='release_cut',jaw_position_m=jaw)
  return self.observe(),float(reward),bool(success or info['invalid']),self.steps>=180,self.info
 def close(self):self.e.close()
