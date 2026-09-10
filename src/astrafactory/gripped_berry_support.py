"""Joint-level support with a removable tool held by actual jaw contact."""
from pathlib import Path
import mujoco,numpy as np
from .berry_support import BerrySupportEnv
TASK=Path(__file__).resolve().parents[2]/'tasks/yam_gripped_berry_support'
class GrippedBerrySupportEnv(BerrySupportEnv):
 def __init__(self,variation=1.,render_mode=None):
  super().__init__(variation,render_mode,task_dir=TASK);m=self.model
  self.tool=m.body('grasped_cradle').id;self.wrist=m.body('gripper').id;self.handle=m.geom('support_handle').id
  self.fingers={side:{i for i in range(m.ngeom) if (m.geom(i).name or '').startswith('finger_'+side+'_')} for side in ['left','right']}
  self.allowed_contact_pairs={tuple(sorted((self.handle,i))) for values in self.fingers.values() for i in values}
  self.jaw_target=0.
 def servo(self):
  super().servo();m,d=self.model,self.data;j=m.joint('joint7')
  d.ctrl[m.actuator('grip').id]=np.clip(1200*(self.jaw_target-d.qpos[j.qposadr[0]])-10*d.qvel[j.dofadr[0]],-12,12)
 def grasp(self):
  m,d=self.model,self.data;forces={side:0. for side in self.fingers}
  for i in range(d.ncon):
   c=d.contact[i];pair={int(c.geom1),int(c.geom2)}
   if self.handle not in pair:continue
   other=next(iter(pair-{self.handle}),-1)
   for side,ids in self.fingers.items():
    if other in ids:
     f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f);forces[side]+=max(0.,float(f[0]))
  R=d.xmat[self.wrist].reshape(3,3);rel=R.T@(d.xpos[self.tool]-d.xpos[self.wrist]);rot=R.T@d.xmat[self.tool].reshape(3,3);angle=float(np.arccos(np.clip((np.trace(rot)-1)/2,-1,1)))
  return dict(left_jaw_N=forces['left'],right_jaw_N=forces['right'],tool_slip_m=float(np.linalg.norm(rel)),tool_rotation_rad=angle)
 def additional_validity(self):
  g=self.grasp();return min(g['left_jaw_N'],g['right_jaw_N'])>.2 and g['tool_slip_m']<.005 and g['tool_rotation_rad']<.15
 def step(self,action):
  o,r,done,trunc,info=super().step(action);g=self.grasp();info.update(g);info['grasp_valid']=self.additional_validity()
  if g['tool_slip_m']>.025 or g['tool_rotation_rad']>.5:
   info['invalid']=True;info['is_success']=False;done=True;r-=8
  return o,r,done,trunc,info
