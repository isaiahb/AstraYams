"""Small learned six-joint positioning specialist in the full strawberry plant."""
from pathlib import Path
import gymnasium as gym
from gymnasium import spaces
import mujoco,numpy as np

TASK=Path(__file__).resolve().parents[2]/'tasks/yam_catcher_positioning'

class CatcherPositioningEnv(gym.Env):
 def __init__(self,variation=1.,task_dir=TASK):
  self.task_dir=Path(task_dir)
  self.model=mujoco.MjModel.from_xml_path(str(self.task_dir/'scene.xml'));self.data=mujoco.MjData(self.model);m=self.model
  self.initial=np.load(self.task_dir/'initial.npz')['qpos'];self.variation=variation
  self.qids=np.array([m.joint(f'joint{i}').qposadr[0] for i in range(1,7)]);self.vids=np.array([m.joint(f'joint{i}').dofadr[0] for i in range(1,7)]);self.aids=np.array([m.actuator(f'motor{i}').id for i in range(1,7)])
  self.limits=np.array([m.joint(f'joint{i}').range for i in range(1,7)]);self.kp=np.array([180,180,180,80,70,60.]);self.kd=np.array([18,18,16,8,7,6.])
  self.tool=m.body('catcher').id;self.wrist=m.body('gripper').id;self.handle=m.geom('catcher_handle').id;self.site=m.site('catcher_center').id
  self.fruit=m.body('fruit_secondary_b').id;self.fruitgeom=m.geom('berry_secondary_b').id;k=m.geom_dataid[self.fruitgeom]
  self.fruit_vertices=m.mesh_vert[m.mesh_vertadr[k]:m.mesh_vertadr[k]+m.mesh_vertnum[k]].copy()
  self.frame=m.body('plant_frame').id;self.pos=m.body_pos.copy();self.quat=m.body_quat.copy();self.stiff=m.jnt_stiffness.copy()
  self.fingers={side:{i for i in range(m.ngeom) if (m.geom(i).name or '').startswith('finger_'+side+'_')} for side in ['left','right']}
  # Stock pads extend onto the handle-to-spine blend. Both are the designated
  # grasp surface; contacts there are expected, not obstacle strikes.
  self.grasp_geoms={self.handle,m.geom('catcher_spine_0').id}
  self.robotgeoms={i for i in range(m.ngeom) if m.geom_contype[i]&6};self.permitted={tuple(sorted((g,i))) for g in self.grasp_geoms for ids in self.fingers.values() for i in ids}
  self.skip=round(.02/m.opt.timestep);self.action_space=spaces.Box(-1,1,(6,),np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(35,),np.float32)
 def geometry(self):
  d=self.data;g=self.fruitgeom;v=self.fruit_vertices@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g]
  goal=np.r_[d.xipos[self.fruit][:2],v[:,2].min()-.018]
  return goal,d.site_xpos[self.site],d.xmat[self.tool].reshape(3,3)[:,0]
 def grasp(self):
  m,d=self.model,self.data;forces={side:0. for side in self.fingers};wrong=0.;penetration=0.
  for i in range(d.ncon):
   c=d.contact[i];g1,g2=int(c.geom1),int(c.geom2)
   if g1 not in self.robotgeoms and g2 not in self.robotgeoms:continue
   f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f);pair=tuple(sorted((g1,g2)))
   if pair in self.permitted:
    other=g2 if g1 in self.grasp_geoms else g1
    for side,ids in self.fingers.items():
     if other in ids:forces[side]+=max(0.,float(f[0]))
   else:wrong=max(wrong,float(np.linalg.norm(f[:3])));penetration=max(penetration,float(-c.dist))
  R=d.xmat[self.wrist].reshape(3,3);rel=R.T@(d.xpos[self.tool]-d.xpos[self.wrist]);rot=R.T@d.xmat[self.tool].reshape(3,3)
  return dict(left_jaw_N=forces['left'],right_jaw_N=forces['right'],tool_slip_m=float(np.linalg.norm(rel)),tool_rotation_rad=float(np.arccos(np.clip((np.trace(rot)-1)/2,-1,1))),wrong_contact_N=wrong,penetration_m=penetration)
 def servo(self):
  m,d=self.model,self.data
  d.ctrl[self.aids]=np.clip(self.kp*(self.target-d.qpos[self.qids])-self.kd*d.qvel[self.vids]+d.qfrc_bias[self.vids],-10,10)
  j=m.joint('joint7');d.ctrl[m.actuator('grip').id]=np.clip(1200*(0.-d.qpos[j.qposadr[0]])-10*d.qvel[j.dofadr[0]],-12,12)
 def observe(self):
  d=self.data;goal,p,normal=self.geometry();quality=np.clip(min(self.grip['left_jaw_N'],self.grip['right_jaw_N'])/5,0,1)
  return np.r_[d.qpos[self.qids]-self.initial[self.qids],d.qvel[self.vids],(self.target-d.qpos[self.qids])*10,(goal-p)*20,normal,self.goal_velocity*10,self.last,quality,self.hold/20].astype(np.float32)
 def reset(self,*,seed=None,options=None):
  super().reset(seed=seed);m,d=self.model,self.data;mujoco.mj_resetData(m,d);d.qpos[:]=self.initial;m.body_pos[:]=self.pos;m.body_quat[:]=self.quat;m.jnt_stiffness[:]=self.stiff
  v=self.variation;offset=self.np_random.uniform([- .02,-.02,-.012],[.02,.02,.012])*v;yaw=float(self.np_random.uniform(-.20,.20)*v);stiff=float(self.np_random.uniform(1-.15*v,1+.15*v))
  m.body_pos[self.frame]+=offset;m.body_quat[self.frame]=[np.cos(yaw/2),0,0,np.sin(yaw/2)];m.jnt_stiffness[:]*=stiff
  self.target=d.qpos[self.qids].copy();self.last=np.zeros(6);self.goal_velocity=np.zeros(3);self.hold=0;self.steps=0;self.episode_return=0.;self.peakwrong=0.
  mujoco.mj_forward(m,d)
  for _ in range(round(.3/m.opt.timestep)):self.servo();mujoco.mj_step(m,d)
  mujoco.mj_forward(m,d);self.grip=self.grasp();self.previous_goal=self.geometry()[0].copy();self.previous_distance=float(np.linalg.norm(self.geometry()[0]-self.geometry()[1]));self.dr=dict(offset_m=offset.tolist(),yaw_rad=yaw,stiffness_scale=stiff)
  return self.observe(),dict(domain_randomization=self.dr,grasp=self.grip)
 def step(self,action):
  a=np.asarray(action,dtype=float)
  if a.shape!=(6,) or not np.isfinite(a).all():raise ValueError('Six finite joint commands required')
  a=np.clip(a,-1,1);self.target=np.clip(self.target+a*.015,self.limits[:,0]+.001,self.limits[:,1]-.001)
  wrong=0.;depth=0.
  for _ in range(self.skip):
   self.servo();mujoco.mj_step(self.model,self.data);self.grip=self.grasp();wrong=max(wrong,self.grip['wrong_contact_N']);depth=max(depth,self.grip['penetration_m'])
  mujoco.mj_forward(self.model,self.data);goal,p,n=self.geometry();self.goal_velocity=(goal-self.previous_goal)/.02;self.previous_goal=goal.copy()
  distance=float(np.linalg.norm(goal-p));speed=float(np.linalg.norm(self.data.qvel[self.vids]));self.steps+=1;self.peakwrong=max(self.peakwrong,wrong)
  validgrasp=min(self.grip['left_jaw_N'],self.grip['right_jaw_N'])>.2 and self.grip['tool_slip_m']<.005 and self.grip['tool_rotation_rad']<.15
  invalid=bool(wrong>.8 or depth>.0008 or self.grip['tool_slip_m']>.025 or self.grip['tool_rotation_rad']>.5 or any(w.number for w in self.data.warning) or not np.isfinite(self.data.qpos).all())
  valid=distance<.005 and n[2]>.96 and speed<.35 and validgrasp and not invalid
  self.hold=self.hold+1 if valid else 0;success=self.hold>=20
  reward=80*(self.previous_distance-distance)+1.2*np.exp(-distance/.025)+.15*n[2]-.003*(a@a)-.006*np.square(a-self.last).sum()
  if valid:reward+=1
  if invalid:reward-=8
  if success:reward+=12
  self.previous_distance=distance;self.last=a.copy();self.episode_return+=float(reward)
  info=dict(is_success=bool(success),invalid=invalid,distance_m=distance,normal_z=float(n[2]),joint_speed_norm=speed,hold_steps=self.hold,return_sum=self.episode_return,sim_s=self.steps*.02,peak_wrong_contact_N=self.peakwrong,domain_randomization=self.dr,**self.grip)
  return self.observe(),float(reward),bool(success or invalid),self.steps>=200,info
 def close(self):pass
