"""Two learned Cartesian/jaw servo specialists with explicit physical skill guards.

Privileged target construction, angular stabilization, scratch IK and guards are
scripted. Both XYZ waypoint displacement and jaw motor increment are learned.
No physical state writes or resets occur here. Frozen contact physics is reused.
"""
from pathlib import Path
import numpy as np
import mujoco
import torch
from torch import nn
from astrafactory.contact_grasp_skill import contacts
from astrafactory.contact_teacher import _exp
from astrafactory.yam_env import yaw_matrix, rotation_error


class Servo(nn.Module):
    def __init__(self, size):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(size,32),nn.Tanh(),nn.Linear(32,32),nn.Tanh(),nn.Linear(32,4),nn.Tanh())
    def forward(self,x):return self.net(x)


def oracle(x):
    """Distillation labels in normalized physical units; never used by learned act."""
    error=x[:3]*.03
    delta=error*min(1.,.0025/max(np.linalg.norm(error),1e-12))
    close=x[-1]>.5
    target=-.0045 if close else -.02
    jaw=np.clip((target-x[6]*.02)/.0006,-.5,.5)
    return np.r_[delta/.0025,jaw/.5].astype(np.float32)


class MicroGrasp:
    def __init__(self,checkpoint=None,oracle_mode=False,initialization_seed=31):
        self.oracle_mode=oracle_mode
        torch.manual_seed(initialization_seed)
        self.models={'acquire':Servo(10),'lift':Servo(10)}
        if checkpoint:
            saved=torch.load(Path(checkpoint),map_location='cpu',weights_only=False)
            for key in self.models:self.models[key].load_state_dict(saved['models'][key])
        for model in self.models.values():model.eval()
        self.started=False
    def start(self,env):
        self.phase='reach';self.started=True
        self.initial_peg=env.data.site_xpos[env.task.pid].copy()
        pr=env.data.site_xmat[env.task.pid].reshape(3,3)
        self.upright=yaw_matrix(np.arctan2(pr[1,0],pr[0,0]))
        self.contact_since=None;self.stable_since=None;self.longest=0.;self.handoffs=[]
    def observe(self,env):
        if not self.started:self.start(env)
        d,t=env.data,env.task
        tool=d.site_xpos[t.sid].copy();peg=d.site_xpos[t.pid].copy()
        rot=d.site_xmat[t.sid].reshape(3,3).copy();pr=d.site_xmat[t.pid].reshape(3,3).copy()
        f=contacts(env)
        vel=np.zeros(6);mujoco.mj_objectVelocity(env.model,d,mujoco.mjtObj.mjOBJ_SITE,t.sid,vel,0)
        target=self.initial_peg+np.array([0,0,.054]);desired=self.upright.copy()
        if self.phase=='reach' and np.linalg.norm(tool-target)<.0008 and np.max(np.abs(d.qvel[env.vadr[:6]]))<.03:
            self.phase='close';self.handoffs.append({'phase':'close','time':float(d.time),'guard':'tool error<0.8mm and arm speed<0.03rad/s'})
        if self.phase=='close':
            good=f[0]>1. and f[1]>1. and abs(d.qvel[env.vadr[6]])<.002 and np.linalg.norm(vel[3:])<.005
            if good:
                if self.contact_since is None:self.contact_since=float(d.time)
                if d.time-self.contact_since>=.25:
                    self.phase='lift';self.handoffs.append({'phase':'lift','time':float(d.time),'guard':'bilateral>1N and jaw/tool velocity settled for0.25s'})
            else:self.contact_since=None
        if self.phase=='lift':
            desired=self.upright@pr.T@rot
            offset=rot.T@(tool-peg)
            target=np.r_[self.initial_peg[:2],.085]+desired@offset
        x=np.r_[(target-tool)/.03,vel[3:]/.1,env.target[6]/.02,f[:2]/5.,float(self.phase!='reach')].astype(np.float32)
        return ('lift' if self.phase=='lift' else 'acquire'),x,desired
    def act(self,env):
        key,x,desired=self.observe(env)
        if self.oracle_mode:y=oracle(x)
        else:
            with torch.no_grad():y=self.models[key](torch.tensor(x)).numpy()
        waypoint=env.data.site_xpos[env.task.sid]+np.clip(y[:3],-1,1)*.0025
        rot=env.data.site_xmat[env.task.sid].reshape(3,3)
        angular=rotation_error(desired,rot);angular*=min(1.,.012/max(np.linalg.norm(angular),1e-9))
        q=env.ik(waypoint,_exp(angular)@rot,initial=env.target[:6])
        return np.r_[np.clip((q-env.target[:6])/env.scales[:6],-.4,.4),np.clip(y[3],-1,1)*.5].astype(np.float32)
    def handoff(self,env):
        z=float(env.data.site_xpos[env.task.pid,2]);f=contacts(env)
        # Same force/clearance thresholds as run_skill_composition; conservative
        # first-to-last timestamp duration instead of inclusive sample counting.
        good=z-self.initial_peg[2]>=.02 and f[0]>.02 and f[1]>.02 and f[2]<.01
        if good:
            if self.stable_since is None:self.stable_since=float(env.data.time)
            self.longest=max(self.longest,float(env.data.time)-self.stable_since)
        else:self.stable_since=None
        duration=0. if self.stable_since is None else env.data.time-self.stable_since
        return bool(duration>=.5 and z>=.065)
