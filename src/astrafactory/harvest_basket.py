"""Contact-derived placement quality. Scores are proxies, not bruise calibration."""
import numpy as np
import mujoco
from astrafactory.dual_harvest import DualHarvestEnv


class HarvestBasketEnv(DualHarvestEnv):
 def __init__(self,task_dir='runs/harvest-skill-suite/basket-task',**kw):
  super().__init__(task_dir=task_dir,**kw)
  m=self.model;self.basket=m.body('receiving_basket').id;self.liner=m.body('basket_liner').id
  self.basket_geoms={g for g in range(m.ngeom) if m.geom_bodyid[g] in [self.basket,self.liner]}
  self.clear_metrics()
 def clear_metrics(self):
  self.placement_peak_N=0.;self.placement_impulse_Ns=0.;self.inbound_speed_m_s=0.
  self.placement_contact=False;self.placement_hold=0;self.max_basket_displacement=0.;self.max_basket_rotation=0.
  self.current_basket_force=0.;self.first_contact_time=None;self.preimpact_velocity=np.zeros(6);self.impact_energy_J=0.;self.failed=False
 def reset(self,**kw):
  o,i=super().reset(**kw);self.clear_metrics();self.basket_start=self.data.xpos[self.basket].copy();self.basket_quat=self.data.xquat[self.basket].copy();return o,i
 def before_physics_step(self):
  m,d=self.model,self.data;fruit=np.zeros(6);basket=np.zeros(6)
  mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,self.fruit,fruit,0)
  mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,self.basket,basket,0)
  self.preimpact_velocity=fruit-basket
 def after_physics_step(self):
  m,d=self.model,self.data;total=0.
  for i,c in enumerate(d.contact):
   ids={int(g) for g in c.geom if g>=0}
   if not ids&self.basket_geoms or not any(m.geom_bodyid[g]==self.fruit for g in ids):continue
   f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f);total+=float(max(f[0],0))
  if total>0:
   if not self.placement_contact:
    self.inbound_speed_m_s=float(np.linalg.norm(self.preimpact_velocity[3:]));self.placement_contact=True;self.first_contact_time=float(d.time)
    R=d.ximat[self.fruit].reshape(3,3);omega=R.T@self.preimpact_velocity[:3]
    self.impact_energy_J=.5*m.body_mass[self.fruit]*self.inbound_speed_m_s**2+.5*float(np.sum(m.body_inertia[self.fruit]*omega**2))
   self.placement_peak_N=max(self.placement_peak_N,total)
   # First 150 ms only, above static weight: resting longer cannot worsen score.
   if d.time-self.first_contact_time<=.15:
    self.placement_impulse_Ns+=max(0.,total-m.body_mass[self.fruit]*np.linalg.norm(m.opt.gravity))*m.opt.timestep
  self.current_basket_force=total
 def advance(self,*args,**kw):
  info=super().advance(*args,**kw);m,d=self.model,self.data
  R=d.xmat[self.basket].reshape(3,3);rel=R.T@(d.xipos[self.fruit]-d.xpos[self.basket]);vel=np.zeros(6)
  mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,self.fruit,vel,0)
  displacement=float(np.linalg.norm(d.xpos[self.basket]-self.basket_start));angle=float(2*np.arccos(np.clip(abs(np.dot(d.xquat[self.basket],self.basket_quat)),0,1)))
  self.max_basket_displacement=max(self.max_basket_displacement,displacement);self.max_basket_rotation=max(self.max_basket_rotation,angle)
  contained=bool(self.severed and abs(rel[0])<.085 and abs(rel[1])<.060 and -.005<rel[2]<.050 and np.linalg.norm(vel[3:])<.025 and self.current_basket_force>.01 and info['net_contact_N']<.001)
  self.placement_hold=self.placement_hold+1 if contained else 0
  quality=100*float(np.exp(-self.impact_energy_J/.001-self.placement_peak_N/2.-self.placement_impulse_Ns/.02)) if self.placement_contact else 0.
  self.failed=bool(self.failed or info['invalid'] or self.max_basket_displacement>.003 or self.max_basket_rotation>.05)
  success=self.placement_hold>=25 and not self.failed
  info.update(net_retained=info['is_success'],is_success=success,placement_success=success,placement_contact=self.placement_contact,placement_hold_steps=self.placement_hold,gentleness_score=quality if success else 0.,provisional_contact_quality=quality,placement_peak_N=self.placement_peak_N,placement_impulse_Ns=self.placement_impulse_Ns,inbound_speed_m_s=self.inbound_speed_m_s,impact_energy_J=self.impact_energy_J,basket_displacement_m=self.max_basket_displacement,basket_rotation_rad=self.max_basket_rotation,invalid=self.failed,scoring_scope='Uncalibrated impact proxies; score only awarded on settled release. Rigid fruit and basket cannot establish bruising, tearing or crushing safety.')
  return info
