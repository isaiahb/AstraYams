"""Compact privileged grasp policy v1; unchanged free-contact physics.

Learned outputs are Cartesian commanded positions and jaw target. Scratch IK,
upright yaw stabilization, rate limits, and physical handoff are scripted.
"""
import numpy as np
import mujoco
import torch
from torch import nn
from astrafactory.yam_env import rotation_error, yaw_matrix

def contacts(env):
    m,d=env.model,env.data
    peg=m.body('free_peg').id
    fingers=[m.body('tip_left').id,m.body('tip_right').id]
    def below(body,root):
        while body:
            if body==root:return True
            body=int(m.body_parentid[body])
        return body==root
    out=np.zeros(3)
    for i in range(d.ncon):
        c=d.contact[i];a,b=[int(m.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
        other=b if below(a,peg) else a if below(b,peg) else None
        if other is None:continue
        group=0 if below(other,fingers[0]) else 1 if below(other,fingers[1]) else 2
        f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f);out[group]+=np.linalg.norm(f[:3])
    return out

def observe(env):
    d,t=env.data,env.task
    tool=d.site_xpos[t.sid];peg=d.site_xpos[t.pid]
    tr=d.site_xmat[t.sid].reshape(3,3);pr=d.site_xmat[t.pid].reshape(3,3)
    handle=peg+pr@np.array([0.,0.,.054])
    velocity=np.zeros(6)
    mujoco.mj_objectVelocity(env.model,d,mujoco.mjtObj.mjOBJ_SITE,t.sid,velocity,0)
    return np.r_[handle-tool,rotation_error(pr,tr),tool[2],peg[2],
                 d.qpos[env.qadr[6]],velocity[5],contacts(env)[:2]].astype(np.float32)

class Network(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(12,64),nn.Tanh(),nn.Linear(64,64),nn.Tanh(),nn.Linear(64,4))
    def forward(self,x):return self.net(x)

class GraspSkill:
    def __init__(self,checkpoint,min_clearance=.065):
        saved=torch.load(checkpoint,map_location='cpu',weights_only=False)
        self.model=Network();self.model.load_state_dict(saved['model']);self.model.eval()
        self.mean=saved['mean'];self.std=saved['std'];self.ymean=saved['ymean'];self.ystd=saved['ystd']
        self.minimum=saved['minimum'];self.maximum=saved['maximum']
        self.min_clearance=min_clearance
        self.initial_z=None;self.stable_since=None;self.longest=0.
    def start(self,env):
        self.initial_z=float(env.data.site_xpos[env.task.pid,2])
        self.stable_since=None;self.longest=0.
    def act(self,env):
        if self.initial_z is None:self.start(env)
        with torch.no_grad():
            y=self.model(torch.tensor((observe(env)-self.mean)/self.std)).numpy()*self.ystd+self.ymean
        y=np.clip(y,self.minimum,self.maximum)
        peg=env.data.site_xpos[env.task.pid]
        position=np.r_[peg[:2]+y[:2],y[2]]
        current=env.data.site_xpos[env.task.sid]
        delta=position-current
        position=current+delta*min(1.,.0025/max(np.linalg.norm(delta),1e-9))
        pr=env.data.site_xmat[env.task.pid].reshape(3,3)
        desired=yaw_matrix(np.arctan2(pr[1,0],pr[0,0]))
        q=env.ik(position,desired,initial=env.target[:6])
        return np.r_[np.clip((q-env.target[:6])/env.scales[:6],-.4,.4),
                     np.clip((y[3]-env.target[6])/env.scales[6],-.5,.5)].astype(np.float32)
    def handoff(self,env):
        if self.initial_z is None:self.start(env)
        z=float(env.data.site_xpos[env.task.pid,2]);left,right,other=contacts(env)
        qualified=z-self.initial_z>=.020 and left>1e-5 and right>1e-5 and other<1e-5
        if qualified:
            if self.stable_since is None:self.stable_since=float(env.data.time)
            self.longest=max(self.longest,float(env.data.time)-self.stable_since)
        else:self.stable_since=None
        duration=0. if self.stable_since is None else float(env.data.time)-self.stable_since
        return bool(duration>=.5 and z>=self.min_clearance)
