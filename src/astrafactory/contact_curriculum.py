"""Versioned pose curriculum; preserves contact dynamics and acceptance rules."""
import numpy as np
from astrafactory.contact_env import ContactEnv,ContactTask
from astrafactory.yam_env import yaw_matrix


class CurriculumEnv(ContactEnv):
    pass


class CurriculumTask(ContactTask):
    def reset(self,rng,options):
        super().reset(rng,options)
        e=self.env;c=e.specification['curriculum']
        self.pick[:2]+=rng.uniform(-c['peg_xy_m'],c['peg_xy_m'],2)
        self.goal[:2]+=rng.uniform(-c['socket_xy_m'],c['socket_xy_m'],2)
        self.goal[3]+=rng.uniform(-c['yaw_rad'],c['yaw_rad'])
        # Shared yaw variation initially; translation offsets differ independently.
        q=[np.cos(self.goal[3]/2),0,0,np.sin(self.goal[3]/2)]
        e.data.qpos[self.pa:self.pa+7]=np.r_[self.pick,q]
        e.model.body_pos[self.socket_id]=[*self.goal[:2],0]
        e.model.body_quat[self.socket_id]=q
        pose=self.pick+np.array([0,0,.115])
        e.data.qpos[e.qadr[:6]]=e.ik(pose,yaw_matrix(self.goal[3]),initial=e.data.qpos[e.qadr[:6]],restarts=3)
        self.desired=pose.copy()
