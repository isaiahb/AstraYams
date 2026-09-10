"""Six-joint PPO support skill. No IK or motion teacher during execution."""
from pathlib import Path
import gymnasium as gym
from gymnasium import spaces
import mujoco,numpy as np

TASK=Path(__file__).resolve().parents[2]/'tasks/yam_berry_support'
class BerrySupportEnv(gym.Env):
 metadata={'render_modes':['rgb_array'],'render_fps':25}
 def __init__(self,variation=1.,render_mode=None,task_dir=None):
  task=Path(task_dir) if task_dir else TASK
  self.model=mujoco.MjModel.from_xml_path(str(task/'scene.xml'));self.data=mujoco.MjData(self.model);self.initial=np.load(task/'initial.npz')['qpos'].copy();m=self.model
  self.allowed_contact_pairs=set()
  self.qids=np.array([m.joint(f'joint{i}').qposadr[0] for i in range(1,7)]);self.vids=np.array([m.joint(f'joint{i}').dofadr[0] for i in range(1,7)]);self.aids=np.array([m.actuator(f'motor{i}').id for i in range(1,7)])
  self.limits=np.array([m.joint(f'joint{i}').range for i in range(1,7)]);self.cup=m.site('support_center').id;self.fruit=m.body('fruit_primary').id;self.frame=m.body('plant_frame').id
  self.stiff=m.jnt_stiffness.copy();self.damping=m.dof_damping.copy();self.pos=m.body_pos.copy();self.quat=m.body_quat.copy();self.mass=m.body_mass[self.fruit];self.weight=self.mass*9.81
  self.cupids={g for g in range(m.ngeom) if (m.geom(g).name or '').startswith('support_cup_')};self.robotids={g for g in range(m.ngeom) if (m.geom(g).name or '').startswith(('yam_geom','finger_','support_'))}
  self.variation=variation;self.render_mode=render_mode;self.renderer=None;self.action_space=spaces.Box(-1,1,(6,),np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(34,),np.float32)
  self.kp=np.array([180,180,180,80,70,60.]);self.kd=np.array([18,18,16,8,7,6.]);self.skip=round(.02/m.opt.timestep)
 def geometry(self):
  d=self.data;R=d.xmat[self.fruit].reshape(3,3);bottom=d.xpos[self.fruit]+R@np.array([0,0,-.039]);target=np.r_[d.xipos[self.fruit][:2],bottom[2]]
  return target,d.site_xpos[self.cup],d.site_xmat[self.cup].reshape(3,3)[:,1]
 def observe(self):
  d=self.data;goal,p,n=self.geometry()
  return np.r_[d.qpos[self.qids]-self.initial[self.qids],d.qvel[self.vids],(self.target-d.qpos[self.qids])*10,(goal-p)*20,n,self.force*5,self.last,self.hold/20].astype(np.float32)
 def reset(self,*,seed=None,options=None):
  super().reset(seed=seed);m,d=self.model,self.data;mujoco.mj_resetData(m,d);d.qpos[:]=self.initial;m.body_pos[:]=self.pos;m.body_quat[:]=self.quat;m.jnt_stiffness[:]=self.stiff
  v=self.variation;offset=self.np_random.uniform([- .012,-.012,-.006],[.012,.012,.006])*v;scale=float(self.np_random.uniform(1-.2*v,1+.2*v));m.body_pos[self.frame]+=offset;m.jnt_stiffness[:]*=scale
  leaf_angles=[]
  for name in ['petiole_left_0','petiole_front_0','petiole_right_0']:
   b=m.body(name).id;a=float(self.np_random.uniform(-.10,.10)*v);q=np.array([np.cos(a/2),0,0,np.sin(a/2)]);mujoco.mju_mulQuat(m.body_quat[b],q,self.quat[b]);leaf_angles.append(a)
  self.target=d.qpos[self.qids].copy();self.last=np.zeros(6);self.force=np.zeros(3);self.steps=0;self.hold=0;self.peak=0.;self.wrong=0.;self.episode_return=0.;self.first_contact=None
  # Only reset initialization. All subsequent movements are integrated forces.
  mujoco.mj_forward(m,d)
  for _ in range(round(.4/m.opt.timestep)):
   self.servo();mujoco.mj_step(m,d)
  mujoco.mj_forward(m,d);self.t0=float(d.time);self.prev_dist=float(np.linalg.norm(self.geometry()[0]-self.geometry()[1]));self.dr=dict(offset_m=offset.tolist(),stiffness_scale=scale,leaf_yaw_rad=leaf_angles)
  return self.observe(),{'domain_randomization':self.dr}
 def servo(self):
  d,m=self.data,self.model;d.ctrl[self.aids]=np.clip(self.kp*(self.target-d.qpos[self.qids])-self.kd*d.qvel[self.vids]+d.qfrc_bias[self.vids],-10,10)
  j=m.joint('joint7');d.ctrl[m.actuator('grip').id]=np.clip(800*(-.015-d.qpos[j.qposadr[0]])-8*d.qvel[j.dofadr[0]],-30,30)
 def contacts(self):
  m,d=self.model,self.data;force=np.zeros(3);wrong=0.;depth=0.
  for i in range(d.ncon):
   c=d.contact[i];g1,g2=int(c.geom1),int(c.geom2)
   if g1 not in self.robotids and g2 not in self.robotids:continue
   if tuple(sorted((g1,g2))) in self.allowed_contact_pairs:continue
   f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f);world=c.frame.reshape(3,3).T@f[:3]
   if g1 in self.cupids and m.geom_bodyid[g2]==self.fruit:force+=world;depth=max(depth,-c.dist)
   elif g2 in self.cupids and m.geom_bodyid[g1]==self.fruit:force-=world;depth=max(depth,-c.dist)
   else:wrong+=np.linalg.norm(world)
  return force,wrong,depth
 def additional_validity(self):return True
 def step(self,action):
  a=np.clip(np.asarray(action,dtype=float),-1,1)
  if a.shape!=(6,) or not np.isfinite(a).all():raise ValueError('Invalid joint action')
  self.target=np.clip(self.target+a*.015,self.limits[:,0]+.001,self.limits[:,1]-.001)
  peak=0.;wrong=0.;depth=0.
  for _ in range(self.skip):
   self.servo();mujoco.mj_step(self.model,self.data);f,w,h=self.contacts();peak=max(peak,float(np.linalg.norm(f)));wrong=max(wrong,w);depth=max(depth,h)
  self.force=f;self.peak=max(self.peak,peak);self.wrong=max(self.wrong,wrong);self.steps+=1
  target,p,normal=self.geometry();dist=float(np.linalg.norm(target-p));xy=float(np.linalg.norm((target-p)[:2]));fraction=float(f[2]/self.weight);speed=float(np.linalg.norm(self.data.qvel[self.vids]));angle=float(normal[2])
  invalid=bool(peak>.65 or wrong>.8 or depth>.0008 or not np.isfinite(self.data.qpos).all() or any(w.number for w in self.data.warning))
  contact=fraction>.1
  if contact and self.first_contact is None:self.first_contact=self.steps*.02
  valid=bool(.6<=fraction<=1.1 and xy<.005 and angle>.94 and speed<.3 and not invalid and self.additional_validity())
  self.hold=self.hold+1 if valid else 0;success=self.hold>=20
  reward=100*(self.prev_dist-dist)+1.5*np.exp(-dist/.02)+.15*angle-.003*float(a@a)-.005*float(np.square(a-self.last).sum())
  if dist<.015:reward+=1.5*np.exp(-((fraction-.8)/.35)**2)
  if valid:reward+=1.
  if invalid:reward-=8
  if success:reward+=10
  self.prev_dist=dist;self.last=a.copy();self.episode_return+=float(reward)
  info=dict(is_success=success,invalid=invalid,distance_m=dist,xy_error_m=xy,support_fraction=fraction,normal_z=angle,joint_speed_norm=speed,force_N=f.tolist(),peak_contact_N=self.peak,wrong_contact_N=self.wrong,penetration_m=depth,hold_steps=self.hold,sim_s=self.steps*.02,first_contact_s=self.first_contact,return_sum=self.episode_return,domain_randomization=self.dr)
  return self.observe(),float(reward),bool(success or invalid),self.steps>=200,info
 def render(self,camera='overview'):
  if self.renderer is None:self.renderer=mujoco.Renderer(self.model,720,1080)
  self.renderer.update_scene(self.data,camera=camera);return self.renderer.render()
 def close(self):
  if self.renderer:self.renderer.close();self.renderer=None
