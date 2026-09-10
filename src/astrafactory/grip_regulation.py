"""Small YAM jaw skill, using proprioception/effort; no contact-state actor input.

Physical prefixes and independent scoring use simulator state. Motor telemetry
and its relationship to real jaw loads are not hardware calibrated.
"""
import copy
import gymnasium as gym
import mujoco
import numpy as np
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_grasp_skill import contacts

TASK='tasks/yam_contact_curriculum'
MAX_DELTA=.0003
HORIZON=150
DT=.02


def actor_observation(env,goal):
    d=env.data
    return np.r_[d.qpos[env.qadr[:6]]/np.pi,d.qpos[env.qadr[6]]/.02,
                 d.qvel[env.vadr[6]]/.03,env.target[6]/.02,
                 d.actuator_force[env.aids[6]]/6.,goal/6.].astype(np.float32)


def jaw_action(env,value):
    a=np.zeros(7,dtype=np.float32)
    a[6]=float(np.clip(np.asarray(value).reshape(-1)[0],-1,1))*MAX_DELTA/env.scales[6]
    return a


def snapshot(e,mode,seed):
    mask=mujoco.mjtState.mjSTATE_INTEGRATION;s=np.empty(mujoco.mj_stateSize(e.model,mask))
    mujoco.mj_getState(e.model,e.data,s,mask)
    return dict(state=s,target=e.target.copy(),previous_action=e.previous_action.copy(),
                body_pos=e.model.body_pos.copy(),body_quat=e.model.body_quat.copy(),
                task={k:copy.deepcopy(v) for k,v in e.task.__dict__.items() if k!='env'},
                mode=mode,seed=seed,steps=e.steps)


def restore(e,s):
    # Only called at isolated training/evaluation reset, never at a handoff.
    e.model.body_pos[:]=s['body_pos'];e.model.body_quat[:]=s['body_quat']
    mujoco.mj_setState(e.model,e.data,s['state'],mujoco.mjtState.mjSTATE_INTEGRATION)
    e.target=s['target'].copy();e.previous_action=s['previous_action'].copy()
    e.steps=0;e.episode_peak_force=0.
    for k,v in s['task'].items():setattr(e.task,k,copy.deepcopy(v))
    mujoco.mj_forward(e.model,e.data);e.reward_function.reset()


def make_bank(seeds,checkpoint='runs/micro-grasp-v1/policy.pt'):
    bank=[];e=CurriculumEnv(TASK)
    for seed in seeds:
        e.reset(seed=int(seed));w=MicroGrasp(checkpoint);open_saved=False
        for _ in range(e.horizon):
            before=e.data.qpos.copy();a=w.act(e)
            assert np.array_equal(before,e.data.qpos)
            if w.phase=='close' and not open_saved:
                bank.append(snapshot(e,'open',int(seed)));open_saved=True
            _,_,done,truncated,info=e.step(a)
            if w.handoff(e):
                bank.append(snapshot(e,'held',int(seed)));break
            if done or truncated:raise RuntimeError(f'Physical prefix failed: {seed} {info}')
        else:raise RuntimeError(f'No physical handoff for {seed}')
    e.close();return bank


def score(e,goal):
    f=contacts(e);load=float(f[:2].sum());err=abs(load-goal)/goal
    return dict(load_n=load,left_n=float(f[0]),right_n=float(f[1]),other_n=float(f[2]),
                relative_error=err,in_band=bool(err<=.2 and min(f[:2])>.05),
                jaw_m=float(e.data.qpos[e.qadr[6]]),jaw_effort_n=float(e.data.actuator_force[e.aids[6]]))


class GripRegulationEnv(gym.Env):
    def __init__(self,bank):
        self.base=CurriculumEnv(TASK);self.bank=bank
        self.observation_space=gym.spaces.Box(-np.inf,np.inf,(11,),dtype=np.float32)
        self.action_space=gym.spaces.Box(-1,1,(1,),dtype=np.float32)
        self.rows=[]

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed);options=options or {}
        i=int(options.get('index',self.np_random.integers(len(self.bank))))
        self.goal=float(options.get('goal',self.np_random.uniform(4.,6.)))
        restore(self.base,self.bank[i]);self.mode=self.bank[i]['mode'];self.n=0;self.stable=0;self.first=None;self.peak=0.;self.total=0.
        self.initial_z=float(self.base.data.site_xpos[self.base.task.pid,2])
        return actor_observation(self.base,self.goal),{'mode':self.mode,'goal_n':self.goal}

    def step(self,action):
        _,_,base_done,_,base_info=self.base.step(jaw_action(self.base,action))
        row=score(self.base,self.goal);self.n+=1;self.peak=max(self.peak,row['load_n'])
        dropped=self.mode=='held' and self.base.data.site_xpos[self.base.task.pid,2]<self.initial_z-.01
        violation=row['load_n']>12 or dropped or (base_done and base_info['reason']!='success')
        self.stable=self.stable+1 if row['in_band'] else 0
        if self.stable>=15 and self.first is None:self.first=self.n*DT
        # Reward actual load tracking, not an action label or desired jaw pose.
        reward=1.-min(row['relative_error'],2.)-.002*float(np.square(action).sum())-.005
        if min(row['left_n'],row['right_n'])>.05:reward+=.05
        if violation:reward-=5
        self.total+=reward;truncated=self.n>=HORIZON and not violation
        row.update(goal_n=self.goal,mode=self.mode,peak_load_n=self.peak,steps=self.n,
                   is_success=bool(self.stable>=15 and not violation),violation=bool(violation),
                   dropped=bool(dropped),first_stable_s=self.first,return_sum=self.total)
        if violation or truncated:self.rows.append(row.copy())
        return actor_observation(self.base,self.goal),float(reward),bool(violation),truncated,row

    def close(self):self.base.close()


class NumpyActor:
    """Deterministic PPO actor only, with SB3's action clipping; no critic."""
    def __init__(self,path):
        z=np.load(path);self.w=[z[f'w{i}'] for i in range(3)];self.b=[z[f'b{i}'] for i in range(3)]
    def __call__(self,x):
        x=np.asarray(x,dtype=np.float32)
        for i in range(2):x=np.tanh(self.w[i]@x+self.b[i])
        return np.clip(self.w[2]@x+self.b[2],-1,1)
