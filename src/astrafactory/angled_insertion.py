"""Versioned angled socket task; full 3D orientation and socket-frame acceptance."""
import numpy as np
import mujoco
from astrafactory.contact_curriculum import CurriculumTask
from astrafactory.yam_env import yaw_matrix,rotation_error
from astrafactory.contact_downstream_skills import exp_rotation

class AngledTask(CurriculumTask):
 def reset(self,rng,options):
  super().reset(rng,options);e=self.env;c=e.specification['angled_insertion']
  self.tilt_degrees=float(rng.uniform(*c['tilt_degrees']))
  self.pick[:2]+=rng.uniform(-c['peg_xy_m'],c['peg_xy_m'],2);e.data.qpos[self.pa:self.pa+3]=self.pick
  self.origin=np.r_[np.array([.32,0])+rng.uniform(-c['socket_xy_m'],c['socket_xy_m'],2),c['socket_origin_z_m']]
  self.relative_yaw=float(rng.uniform(-c['relative_key_yaw_rad'],c['relative_key_yaw_rad']))
  self.rotation=exp_rotation(np.array([0,np.deg2rad(self.tilt_degrees),0]))@yaw_matrix(self.goal[3]+self.relative_yaw)
  quat=np.zeros(4);mujoco.mju_mat2Quat(quat,self.rotation.reshape(-1));e.model.body_pos[self.socket_id]=self.origin;e.model.body_quat[self.socket_id]=quat
  support=e.model.body('fixture_support').id;e.model.body_pos[support]=self.origin-np.array([0,0,.03])
  self.goal[:3]=self.origin+self.rotation@np.array([0,0,.009]);self.was_lifted=False
 def error(self):
  e=self.env;return np.r_[self.goal[:3]-e.data.site_xpos[self.pid],rotation_error(self.rotation,e.data.site_xmat[self.pid].reshape(3,3))]
 def evaluate(self,force):
  # Inherit contact diagnostics, then apply this version's registered local-frame criteria.
  info=super().evaluate(force);e=self.env;local=self.rotation.T@(e.data.site_xpos[self.pid]-self.origin)
  er=self.error();c=e.specification['success']
  valid=(self.was_lifted and np.linalg.norm(local[:2])<c['lateral_tolerance_m'] and np.linalg.norm(er[3:])<c['orientation_tolerance_rad'] and c['axial_tip_min_m']<=local[2]<=c['axial_tip_max_m'] and info['peg_speed_m_s']<c['speed_max_m_s'] and force<c['contact_force_max_n'])
  self.angled_hold=getattr(self,'angled_hold',0)+1 if valid else 0
  info.update(is_success=self.angled_hold>=c['hold_steps'],hold_steps=self.angled_hold,lateral_error_m=float(np.linalg.norm(local[:2])),axial_tip_m=float(local[2]),socket_tilt_degrees=self.tilt_degrees,relative_key_yaw_rad=self.relative_yaw)
  return info

def observation(env,phase):
 t=env.task;pos=env.data.site_xpos[t.pid];rot=env.data.site_xmat[t.pid].reshape(3,3)
 goal=t.origin+t.rotation@np.array([0,0,.078 if phase=='orient' else .009])
 local=t.rotation.T@(goal-pos);angle=t.rotation.T@rotation_error(t.rotation,rot)
 va=int(env.model.jnt_dofadr[t.peg_joint]);vel=env.data.qvel[va:va+6]
 return np.r_[local/.05,angle/.5,t.rotation.T@vel[:3]/.1,vel[3:],t.force/40.,float(phase=='insert')].astype(np.float32)

def teacher_label(x):
 y=np.r_[np.clip(x[:3]*.05/.0015,-1,1),np.clip(x[3:6]*.5/.009,-1,1)]
 if x[-1]>.5 and (np.linalg.norm(x[:2])*.05>.0006 or np.linalg.norm(x[3:6])*.5>.025):y[2]=max(0,y[2])
 if x[-1]>.5 and x[-2]*40>32:y[2]=.5
 return y.astype(np.float32)

def apply_correction(env,phase,action):
 t=env.task;a=np.clip(np.asarray(action),-1,1);d=env.data
 pos=d.site_xpos[t.sid].copy();rot=d.site_xmat[t.sid].reshape(3,3).copy();peg=d.site_xpos[t.pid].copy()
 delta=t.rotation@(a[:3]*(.0015 if phase=='orient' else .0006));angular=t.rotation@(a[3:]*.009)
 desired=exp_rotation(angular)@rot;offset=rot.T@(pos-peg);target=peg+delta+desired@offset
 q=env.ik(target,desired,initial=env.target[:6]);return np.r_[np.clip((q-env.target[:6])/env.scales[:6],-.4,.4),np.clip((-.0045-env.target[6])/env.scales[6],-.5,.5)].astype(np.float32)

def ready_to_insert(env):
 x=observation(env,'orient');return np.linalg.norm(x[:3])*.05<.001 and np.linalg.norm(x[3:6])*.5<.015 and np.linalg.norm(x[6:9])*.1<.02
