"""Learned local servos in an explicit machine-tending workflow.

State observations, target construction, phase guards and IK are engineered.
Networks supply Cartesian/angular/jaw increments. Vise commands are a separate
simulated machine interface, not manipulation of the simulator's qpos.
"""
import numpy as np
import mujoco
import torch
from torch import nn
from astrafactory.yam_env import yaw_matrix,rotation_error
from astrafactory.contact_downstream_skills import exp_rotation

class Servo(nn.Module):
 def __init__(self):
  super().__init__();self.net=nn.Sequential(nn.Linear(13,48),nn.Tanh(),nn.Linear(48,48),nn.Tanh(),nn.Linear(48,7),nn.Tanh())
 def forward(self,x):return self.net(x)

def label(x):
 x=np.asarray(x);delta=x[:3]*.03;delta*=min(1,.0015/max(np.linalg.norm(delta),1e-9))
 angle=x[3:6]*.3;angle*=min(1,.01/max(np.linalg.norm(angle),1e-9))
 return np.r_[delta/.0015,angle/.01,np.clip(x[12]*.02/.0006,-.5,.5)/.5].astype(np.float32)

class Workflow:
 def __init__(self,models=None):self.models=models;self.phase='open_vise';self.since=None;self.phase_start=0.;self.history=[];self.done=False
 def transition(self,e,phase):
  self.history.append({'from':self.phase,'to':phase,'time':float(e.data.time)});self.phase=phase;self.phase_start=e.data.time;self.since=None
 def stable(self,e,condition,duration=.15):
  if not condition:self.since=None;return False
  if self.since is None:self.since=float(e.data.time)
  return e.data.time-self.since>=duration
 def target(self,e):
  from astrafactory.machine_tending import active_contacts
  t=e.task;d=e.data;pos=d.site_xpos[t.sid].copy();rot=d.site_xmat[t.sid].reshape(3,3).copy()
  finished='finished' if self.phase in ['open_vise','approach_finished','grip_finished','lift_finished','move_output','lower_output','release_finished','retract_output'] else 'raw'
  t.select_part(finished)
  peg=d.site_xpos[t.pid].copy();pr=d.site_xmat[t.pid].reshape(3,3).copy();f=active_contacts(e)
  upright=yaw_matrix(np.arctan2(pr[1,0],pr[0,0]));goal_rot=yaw_matrix(np.pi)
  output=np.array([.24,.10,.004]);seat=np.array([.32,0,.02]);grip=-.0045
  # A tracked grasp transform converts part goals to tool goals; no object pose writes.
  def carry(p,r):return np.asarray(p)+r@pr.T@(pos-peg),r@pr.T@rot
  target=pos.copy();desired=rot.copy();age=d.time-self.phase_start
  if self.phase=='open_vise':
   e.command_vise(.039);grip=-.02
   if age>.6:self.transition(e,'approach_finished')
  elif self.phase in ['approach_finished','approach_raw']:
   target=peg+np.array([0,0,.054]);desired=upright;grip=-.02
   if self.stable(e,np.linalg.norm(target-pos)<.0012 and np.linalg.norm(rotation_error(desired,rot))<.025,.1):self.transition(e,'grip_finished' if finished=='finished' else 'grip_raw')
  elif self.phase in ['grip_finished','grip_raw']:
   target=peg+np.array([0,0,.054]);desired=upright
   if self.stable(e,f[0]>.25 and f[1]>.25,.25):self.transition(e,'lift_finished' if finished=='finished' else 'lift_raw')
  elif self.phase in ['lift_finished','lift_raw']:
   target,desired=carry(np.r_[peg[:2],.14],upright)
   if self.stable(e,peg[2]>.12 and f[0]>.1 and f[1]>.1,.15):self.transition(e,'move_output' if finished=='finished' else 'move_vise')
  elif self.phase in ['move_output','move_vise']:
   center=output if self.phase=='move_output' else seat;target,desired=carry(np.r_[center[:2],.14],goal_rot)
   if self.stable(e,np.linalg.norm(peg[:2]-center[:2])<.001 and abs(peg[2]-.14)<.002 and np.linalg.norm(rotation_error(goal_rot,pr))<.025,.15):self.transition(e,'lower_output' if self.phase=='move_output' else 'seat_raw')
  elif self.phase in ['lower_output','seat_raw']:
   center=output if self.phase=='lower_output' else seat;target,desired=carry(center,goal_rot)
   if self.stable(e,np.linalg.norm(peg-center)<.0018 and np.linalg.norm(rotation_error(goal_rot,pr))<.04,.3):self.transition(e,'release_finished' if self.phase=='lower_output' else 'clamp')
  elif self.phase=='clamp':
   target,desired=carry(seat,goal_rot);e.command_vise(.0125)
   if age>.7:self.transition(e,'release_raw')
  elif self.phase in ['release_finished','release_raw']:
   grip=-.025
   if age>.6:self.transition(e,'retract_output' if self.phase=='release_finished' else 'retreat')
  elif self.phase in ['retract_output','retreat']:
   center=output if self.phase=='retract_output' else seat;target=np.r_[center[:2],.18];desired=goal_rot;grip=-.025
   if np.linalg.norm(pos-target)<.003:
    if self.phase=='retract_output':self.transition(e,'travel_raw')
    else:self.transition(e,'verify')
  elif self.phase=='travel_raw':
   target=peg+np.array([0,0,.15]);desired=upright;grip=-.025
   if np.linalg.norm(pos-target)<.004:self.transition(e,'approach_raw')
  elif self.phase=='verify':target=np.r_[seat[:2],.18];desired=goal_rot;grip=-.025
  return target,desired,grip
 def act(self,e,collect=None):
  pos=e.data.site_xpos[e.task.sid].copy();rot=e.data.site_xmat[e.task.sid].reshape(3,3).copy()
  target,desired,grip=self.target(e);vel=np.zeros(6);mujoco.mj_objectVelocity(e.model,e.data,mujoco.mjtObj.mjOBJ_SITE,e.task.sid,vel,0)
  x=np.r_[(target-pos)/.03,rotation_error(desired,rot)/.3,vel[3:]/.1,vel[:3]/.3,(grip-e.target[6])/.02].astype(np.float32)
  kind='precision' if self.phase in ['approach_finished','approach_raw','grip_finished','grip_raw','lower_output','seat_raw','clamp','release_finished','release_raw'] else 'transport'
  if self.models is None:y=label(x)
  else:
   with torch.inference_mode():y=self.models[kind](torch.tensor(x)).numpy()
  if collect is not None:collect[kind][0].append(x);collect[kind][1].append(label(x))
  delta=np.clip(y[:3],-1,1)*.0015;angular=np.clip(y[3:6],-1,1)*.01
  q=e.ik(pos+delta,exp_rotation(angular)@rot,initial=e.target[:6])
  return np.r_[np.clip((q-e.target[:6])/e.scales[:6],-.4,.4),np.clip(y[6],-1,1)*.5].astype(np.float32)

class StructuredServo(nn.Module):
 """Seven fitted feedback gains; explicit norm limits, no learned task planner.

This restricted controller family prevents the cross-axis drift observed in the
MLP candidate. Both its structure and the workflow remain engineered.
 """
 def __init__(self):
  super().__init__();self.gain=nn.Parameter(torch.zeros(7))
 def forward(self,x):
  z=torch.cat([x[...,:6],x[...,12:13]],dim=-1)*self.gain
  p=z[...,:3]/torch.linalg.vector_norm(z[...,:3],dim=-1,keepdim=True).clamp_min(1)
  r=z[...,3:6]/torch.linalg.vector_norm(z[...,3:6],dim=-1,keepdim=True).clamp_min(1)
  return torch.cat([p,r,z[...,6:7].clamp(-1,1)],dim=-1)
