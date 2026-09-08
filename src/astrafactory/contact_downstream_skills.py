"""Tiny learned privileged-state downstream policies with a fixed IK scaffold.

The checkpoint supplies every Cartesian motion correction. The scaffold only
bounds those corrections and converts a desired peg displacement through the
measured grasp transform into joint targets. It does not choose goal motion.
These are local feedback-controller distillations, not camera policies or RL.
"""
from pathlib import Path
import numpy as np
from astrafactory.yam_env import yaw_matrix, rotation_error


def exp_rotation(vector):
    theta=np.linalg.norm(vector)
    if theta<1e-12:return np.eye(3)
    a=vector/theta;k=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return np.eye(3)+np.sin(theta)*k+(1-np.cos(theta))*k@k


def observe(env,kind):
    e=env.unwrapped;t=e.task
    peg=e.data.site_xpos[t.pid].copy();pr=e.data.site_xmat[t.pid].reshape(3,3)
    goal=t.goal[:3].copy()
    if kind=='align':goal[2]=.065
    scale=.05 if kind=='align' else .01
    error=np.r_[(goal-peg)/scale,rotation_error(yaw_matrix(t.goal[3]),pr)/.1]
    va=int(e.model.jnt_dofadr[t.peg_joint]);velocity=e.data.qvel[va:va+6].copy()
    obs=np.r_[error,velocity[:3]/.1,velocity[3:]]
    if kind=='insert':obs=np.r_[obs,t.force/40.,np.linalg.norm(error[:2]),np.linalg.norm(error[3:])]
    return obs.astype(np.float64)


def expert_label(env,kind):
    """Training only: requested Cartesian correction, prior to common bounds."""
    x=observe(env,kind);out=x[:6].copy()
    if kind=='insert':
        # Analytic demonstration teacher preserves lateral/angular alignment.
        if np.linalg.norm(x[:2])>.04 or np.linalg.norm(x[3:])>.08:out[2]=0
        if env.task.force>32:out[2]=.4
    return out


def scaffold(env,kind,correction):
    e=env.unwrapped;t=e.task
    a=np.asarray(correction,dtype=float)
    if a.shape!=(6,) or not np.isfinite(a).all():raise ValueError('Expected six finite learned Cartesian outputs')
    pos=e.data.site_xpos[t.sid].copy();rot=e.data.site_xmat[t.sid].reshape(3,3).copy();peg=e.data.site_xpos[t.pid].copy()
    delta=a[:3]*(.05 if kind=='align' else .01)
    limit=.0025 if kind=='align' else (.0006 if peg[2]<.047 else .0012)
    delta=np.clip(delta,-limit,limit)
    angular=a[3:]*.1;angular*=min(1,.012/max(np.linalg.norm(angular),1e-12))
    desired_rot=exp_rotation(angular)@rot
    local_offset=rot.T@(pos-peg)
    target=peg+delta+desired_rot@local_offset
    q=e.ik(target,desired_rot,initial=e.target[:6])
    return np.r_[np.clip((q-e.target[:6])/e.scales[:6],-.4,.4),np.clip((-.0045-e.target[6])/e.scales[6],-.5,.5)].astype(np.float32)


class DownstreamSkill:
    def __init__(self,checkpoint,kind):
        if kind not in ('align','insert'):raise ValueError(kind)
        self.kind=kind;self.checkpoint=str(Path(checkpoint));self.count=0
        with np.load(checkpoint,allow_pickle=False) as d:
            if str(d['kind'])!=kind:raise ValueError('Checkpoint skill mismatch')
            self.weight=d['weight'].copy()
        self.observation_size=12 if kind=='align' else 15
        if self.weight.shape!=(self.observation_size,6):raise ValueError('Checkpoint shape mismatch')
    def start(self,env):self.count=0
    def act(self,env):return scaffold(env,self.kind,observe(env,self.kind)@self.weight)
    def handoff(self,env,info):
        if self.kind=='insert':return bool(info['is_success'])
        x=observe(env,self.kind)
        valid=np.linalg.norm(x[:2])*.05<.0005 and abs(x[2])*.05<.001 and np.linalg.norm(x[3:6])*.1<.01 and np.linalg.norm(x[6:9])*.1<.015 and bool(info['grasp_contacts'])
        self.count=self.count+1 if valid else 0
        return self.count>=10
