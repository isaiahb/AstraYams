"""Coordinated seven-action cutter retreat and release after a learned cut."""
import numpy as np
from gymnasium import spaces
from astrafactory.harvest_joint_skill import HarvestJointSkill

class ReleaseWithdrawSkill(HarvestJointSkill):
 def __init__(self,source='runs/harvest-skill-suite/cut-release-source-v1',curriculum=None,variation=1.,support_policy=None):
  super().__init__('withdraw',source=source,curriculum=curriculum,difficulty=1.,variation=variation)
  self.action_space=spaces.Box(-1,1,(7,),np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(71,),np.float32)
  jaw=-.007
  for a in self.z['actions'][:self.begin]:jaw=float(np.clip(jaw+a[-1]*.00025,-.009,-.0028))
  self.entry_jaw=jaw
  self.support_path=support_policy;self.partner=None
  if support_policy:
   from stable_baselines3 import PPO
   self.partner=PPO.load(support_policy,device='cpu')
  self.support_reference=self.e.initial[self.e.qids].copy()
 def observe(self):
  e=self.e;j=e.model.joint('cut_joint7');return np.r_[super().observe(),(e.data.qpos[j.qposadr[0]]+.007)*200,(e.jaw_target+.007)*200,self.info.get('net_contact_N',0.),min(e.net_hold,25)/25].astype(np.float32)
 def reset(self,*,seed=None,options=None):
  _,info=super().reset(seed=seed,options=options);self.e.jaw_target=self.entry_jaw;self.previous_jaw=float(self.e.data.qpos[self.e.model.joint('cut_joint7').qposadr[0]])
  return self.observe(),info
 def step(self,action):
  a=np.clip(np.asarray(action,float),-1,1)
  if a.shape!=(7,) or not np.isfinite(a).all():raise ValueError('Six joint and one jaw action required')
  ca=self.partner_action();info=self.e.advance(cut_action=a,catch_action=ca);return self.after_step(a,info)
 def partner_action(self):
  # Track the still-gripped fruit with the existing learned support specialist.
  # Once released or received, retain the current motor targets so the net does
  # not chase a falling payload. This gate chooses a skill, not an arm path.
  if self.partner is None or self.e.jaw_target<-.0065 or self.info.get('net_contact_N',0)>.005:return None
  o=self.e.observe();o[:6]=self.e.data.qpos[self.e.qids]-self.support_reference
  return self.partner.predict(o,deterministic=True)[0]
 def after_step(self,a,info):
  _,reward,_,trunc,row=super().after_step(a[:6],info);e=self.e;jaw=float(e.data.qpos[e.model.joint('cut_joint7').qposadr[0]])
  # A pose-only completion is insufficient: the payload must leave the cutter
  # and settle in the other arm's contact-held flexible net.
  if row['is_success']:reward-=150
  reward+=2*(getattr(self,'previous_jaw',jaw)-jaw)/.0042
  success=bool(self.hold>=10 and e.net_hold>=25 and jaw<-.0065 and not row['invalid'])
  if success:reward+=180
  row.update(is_success=success,skill='release_withdraw',jaw_position_m=jaw);self.info=row;self.previous_jaw=jaw
  return self.observe(),reward,bool(success or row['invalid']),trunc,row
