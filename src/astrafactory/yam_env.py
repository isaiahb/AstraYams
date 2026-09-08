"""Articulated official-YAM adapter: joint torque dynamics with a prepared held peg."""
import numpy as np
import mujoco
from astrafactory.env import FactoryEnv


def rotation_error(target, current):
    a=np.zeros(4);b=np.zeros(4);q=np.zeros(4)
    mujoco.mju_mat2Quat(a,np.asarray(target).reshape(-1));mujoco.mju_mat2Quat(b,np.asarray(current).reshape(-1))
    b[1:]*=-1;mujoco.mju_mulQuat(q,a,b)
    if q[0]<0:q*=-1
    n=np.linalg.norm(q[1:])
    return q[1:]*(2*np.arctan2(n,q[0])/n) if n>1e-10 else q[1:]*2


def yaw_matrix(yaw):
    c,s=np.cos(yaw),np.sin(yaw)
    return np.array([[c,-s,0],[s,c,0],[0,0,1.]])


class YamEnv(FactoryEnv):
    def ik(self, position, rotation, initial=None, restarts=1):
        """Kinematics runs on separate scratch data; never assigns execution state."""
        scratch=mujoco.MjData(self.model)
        sid=self.model.site('peg_tip').id
        jp=np.zeros((3,self.model.nv));jr=jp.copy()
        rng=np.random.default_rng(2026)
        best=None;score=np.inf
        for attempt in range(restarts):
            q=np.asarray(initial if attempt==0 and initial is not None else rng.uniform(self.limits[:,0]+.05,self.limits[:,1]-.05),float).copy()
            for _ in range(180):
                scratch.qpos[self.qadr]=q;mujoco.mj_forward(self.model,scratch)
                error=np.r_[position-scratch.site_xpos[sid],.15*rotation_error(rotation,scratch.site_xmat[sid].reshape(3,3))]
                loss=np.linalg.norm(error)
                if loss<score:best=q.copy();score=loss
                if loss<1e-7:return q
                mujoco.mj_jacSite(self.model,scratch,jp,jr,sid)
                jac=np.r_[jp[:,self.vadr],.15*jr[:,self.vadr]]
                dq=jac.T@np.linalg.solve(jac@jac.T+np.eye(6)*1e-5,error)
                q=np.clip(q+np.clip(dq,-.18,.18),self.limits[:,0]+1e-5,self.limits[:,1]-1e-5)
        if score>.00015:raise ValueError(f'YAM IK unreachable: weighted residual {score:.6f}')
        return best


class YamTask:
    def __init__(self,env):
        self.env=env;self.socket_id=env.model.body('socket').id;self.sid=env.model.site('peg_tip').id
        self.goal=np.zeros(4);self.hold=0;self.force=0.;self.teacher_stage=0
    def error(self):
        e=self.env
        return np.r_[self.goal[:3]-e.data.site_xpos[self.sid],rotation_error(yaw_matrix(self.goal[3]),e.data.site_xmat[self.sid].reshape(3,3))]
    def distance(self):
        er=self.error();return float(np.linalg.norm(er[:3])+.02*np.linalg.norm(er[3:]))
    def reset(self,rng,options):
        e=self.env;c=e.specification['reset']
        xy=np.array([.32,0])+rng.uniform(-c['socket_xy_range_m'],c['socket_xy_range_m'],2)
        yaw=np.pi+rng.uniform(-c['socket_yaw_range_rad'],c['socket_yaw_range_rad'])
        self.goal=np.r_[xy,.009,yaw];e.model.body_pos[self.socket_id]=[*xy,0];e.model.body_quat[self.socket_id]=[np.cos(yaw/2),0,0,np.sin(yaw/2)]
        start=np.r_[xy+rng.uniform(-c['tool_xy_error_m'],c['tool_xy_error_m'],2),.075]
        start_yaw=yaw+rng.uniform(-c['tool_yaw_error_rad'],c['tool_yaw_error_rad'])
        e.data.qpos[e.qadr]=e.ik(start,yaw_matrix(start_yaw),initial=np.array([0,1.4,1.4,0,0,0]),restarts=12)
        self.hold=0;self.force=0.;self.teacher_stage=0;self.teacher_z=.065
        self.teacher_q_above=e.ik(np.r_[xy,.065],yaw_matrix(yaw),initial=e.data.qpos[e.qadr],restarts=3)
        self.teacher_q_goal=e.ik(self.goal[:3],yaw_matrix(yaw),initial=self.teacher_q_above,restarts=3)
    def observe(self):
        e=self.env
        return np.r_[e.data.qpos[e.qadr],e.data.qvel[e.vadr],e.target,self.error(),e.previous_action,self.force]
    def evaluate(self,force):
        e=self.env;c=e.specification['success'];er=self.error();z=float(e.data.site_xpos[self.sid,2])
        jp=np.zeros((3,e.model.nv));jr=jp.copy();mujoco.mj_jacSite(e.model,e.data,jp,jr,self.sid)
        v=jp@e.data.qvel;w=jr@e.data.qvel
        speed=float(max(np.max(np.abs(v)),np.max(np.abs(w))))
        aligned=np.linalg.norm(er[:2])<c['xy_tolerance_m'] and np.linalg.norm(er[3:])<c['yaw_tolerance_rad']
        valid=aligned and c['tip_z_min_m']<=z<=c['tip_z_max_m'] and speed<c['speed_max'] and force<c['contact_force_max_n']
        self.hold=self.hold+1 if valid else 0;self.force=force
        return {'is_success':self.hold>=c['hold_steps'],'xy_error_m':float(np.linalg.norm(er[:2])),'yaw_error_rad':float(abs(er[5])),'orientation_error_rad':float(np.linalg.norm(er[3:])),'tip_z_m':z,'speed':speed,'hold_steps':self.hold}


def teacher(env):
    e=env.unwrapped;t=e.task
    if t.teacher_stage==0:
        goal=t.teacher_q_above
        if np.max(np.abs(e.data.qpos[e.qadr]-goal))<.001 and np.max(np.abs(e.data.qvel[e.vadr]))<.01:t.teacher_stage=1
    else:
        er=t.error()
        if abs(e.data.site_xpos[t.sid,2]-t.teacher_z)<.0004 and np.linalg.norm(er[:2])<.0004 and np.linalg.norm(er[3:])<.008:
            t.teacher_z=max(float(t.goal[2]),t.teacher_z-.00025)
        goal=e.ik(np.r_[t.goal[:2],t.teacher_z],yaw_matrix(t.goal[3]),initial=e.target)

    return np.clip((goal-e.target)/e.scales,-.25,.25).astype(np.float32)
