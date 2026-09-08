"""YAM free-object manipulation. No attachment equality or pose assignment in step."""
import numpy as np
import mujoco
from astrafactory.env import FactoryEnv
from astrafactory.yam_env import rotation_error,yaw_matrix


class ContactEnv(FactoryEnv):
    def ik(self,position,rotation,initial=None,restarts=1):
        scratch=mujoco.MjData(self.model);scratch.qpos[:]=self.data.qpos
        sid=self.model.site('tool_tip').id
        jp=np.zeros((3,self.model.nv));jr=jp.copy();rng=np.random.default_rng(2026)
        best=None;score=np.inf
        for attempt in range(restarts):
            q=np.asarray(initial if attempt==0 and initial is not None else rng.uniform(self.limits[:6,0]+.05,self.limits[:6,1]-.05)).copy()
            for _ in range(250):
                scratch.qpos[self.qadr[:6]]=q;mujoco.mj_forward(self.model,scratch)
                er=np.r_[position-scratch.site_xpos[sid],.15*rotation_error(rotation,scratch.site_xmat[sid].reshape(3,3))]
                loss=np.linalg.norm(er)
                if loss<score:score=loss;best=q.copy()
                if loss<1e-7:return q
                mujoco.mj_jacSite(self.model,scratch,jp,jr,sid);jac=np.r_[jp[:,self.vadr[:6]],.15*jr[:,self.vadr[:6]]]
                dq=jac.T@np.linalg.solve(jac@jac.T+np.eye(6)*1e-5,er)
                q=np.clip(q+np.clip(dq,-.15,.15),self.limits[:6,0]+1e-5,self.limits[:6,1]-1e-5)
        if score>.0003:raise ValueError(f'Contact task IK unreachable {score}')
        return best


class ContactTask:
    def __init__(self,env):
        self.env=env;self.sid=env.model.site('tool_tip').id;self.pid=env.model.site('peg_tip').id
        self.peg_joint=env.model.joint('peg_free').id;self.pa=env.model.jnt_qposadr[self.peg_joint]
        self.peg_body=env.model.body('free_peg').id;self.socket_id=env.model.body('socket').id
        self.goal=np.zeros(4);self.stage=0;self.hold=0;self.force=0;self.was_lifted=False;self.counter=0
    def error(self):
        e=self.env
        return np.r_[self.goal[:3]-e.data.site_xpos[self.pid],rotation_error(yaw_matrix(self.goal[3]),e.data.site_xmat[self.pid].reshape(3,3))]
    def distance(self):return float(np.linalg.norm(self.error()[:3])+.02*np.linalg.norm(self.error()[3:]))
    def reset(self,rng,options):
        if options:raise ValueError('Scored contact task does not allow reset pose overrides')
        e=self.env;self.goal=np.array([.32,0,.009,np.pi]);self.pick=np.array([.26,-.08,.001])
        e.data.qpos[self.pa:self.pa+7]=np.r_[self.pick,[0,0,0,1]]
        e.model.body_pos[self.socket_id]=[.32,0,0];e.model.body_quat[self.socket_id]=[0,0,0,1]
        e.data.qpos[e.qadr[6]]=-.02;e.data.qpos[e.model.joint('joint8').qposadr]=-.02
        pose=self.pick+np.array([0,0,.115])
        e.data.qpos[e.qadr[:6]]=e.ik(pose,yaw_matrix(np.pi),initial=np.array([0,1.4,1.4,0,0,0]),restarts=12)
        self.stage=0;self.hold=0;self.force=0;self.was_lifted=False;self.counter=0;self.desired=pose.copy()
    def observe(self):
        e=self.env
        return np.r_[e.data.qpos[e.qadr],e.data.qvel[e.vadr],e.target,self.error(),e.previous_action,e.data.qpos[self.pa:self.pa+7],self.force]
    def evaluate(self,force):
        e=self.env;names=[]
        for c in e.data.contact:
            if c.dist>.0001:continue
            gs=[e.model.geom(int(x)).name for x in c.geom]
            if any('peg' in n for n in gs):names.extend(gs)
        left=any('left' in n for n in names);right=any('right' in n for n in names)
        z=float(e.data.site_xpos[self.pid,2]);self.was_lifted=self.was_lifted or (z>.035 and left and right)
        er=self.error();pv=e.model.jnt_dofadr[self.peg_joint];speed=float(np.linalg.norm(e.data.qvel[pv:pv+3]))
        valid=self.was_lifted and np.linalg.norm(er[:2])<.001 and np.linalg.norm(er[3:])<.06 and .0075<=z<=.012 and speed<.015 and force<45
        self.hold=self.hold+1 if valid else 0;self.force=force
        return {'is_success':self.hold>=15,'peg_z_m':z,'tip_z_m':z,'xy_error_m':float(np.linalg.norm(er[:2])),'orientation_error_rad':float(np.linalg.norm(er[3:])),'yaw_error_rad':float(abs(er[5])),'left_contact':left,'right_contact':right,'grasp_contacts':bool(left and right),'was_lifted':self.was_lifted,'stage':self.stage,'hold_steps':self.hold,'peg_speed_m_s':speed}


def teacher(env,stop_after_lift=False):
    e=env.unwrapped;t=e.task;pos=e.data.site_xpos[t.sid]
    target=t.pick+np.array([0,0,.054]);grip=-.02
    if t.stage==0:
        if np.linalg.norm(pos-target)<.001 and np.max(np.abs(e.data.qvel[e.vadr[:6]]))<.03:t.stage=1;t.counter=0
    if t.stage==1:
        grip=-.0045;t.counter+=1
        if t.counter>45:t.stage=2
    if t.stage==2:
        grip=-.0045;target=t.pick+np.array([0,0,.145])
        if np.linalg.norm(pos-target)<.001:t.stage=3;t.counter=0
    if t.stage==3:
        grip=-.0045;target=t.pick+np.array([0,0,.145]);t.counter+=1
        if not stop_after_lift and t.counter>30:t.stage=4
    if t.stage==4:
        grip=-.0045;target=np.array([.32,0,.146])
        if np.linalg.norm(pos-target)<.0005:t.stage=5
    if t.stage==5:
        grip=-.0045;target=np.array([.32,0,.063])
    # Cartesian waypoint keeps low-level joint-space interpolation short.
    delta=target-pos;norm=np.linalg.norm(delta)
    waypoint=pos+delta*min(1,.001/max(norm,1e-9))
    q=e.ik(waypoint,yaw_matrix(np.pi),initial=e.target[:6])
    return np.r_[np.clip((q-e.target[:6])/e.scales[:6],-.2,.2),np.clip((grip-e.target[6])/e.scales[6],-.5,.5)].astype(np.float32)
