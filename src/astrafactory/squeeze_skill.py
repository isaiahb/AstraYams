"""Goal-conditioned axial squeeze experiment, separate from v1 magnitude-sum task.

Contact wrenches are summed as vectors before projection along each closing axis.
The actor sees only jaw proprioception, command, motor effort, and requested load.
Hardware effort calibration is still required; no tactile sensors are assumed.
"""
import numpy as np
import mujoco
from astrafactory.grip_regulation import GripRegulationEnv, NumpyActor, jaw_action, DT, HORIZON


def squeeze_observation(e, goal):
    effort=float(e.data.actuator_force[e.aids[6]])
    return np.array([e.data.qpos[e.qadr[6]]/.02, e.data.qvel[e.vadr[6]]/.03,
                     e.target[6]/.02, effort/6., goal/6., (goal-effort)/6.], dtype=np.float32)


def squeeze_load(e):
    """Net object-on-finger force opposed to each finger's closing direction."""
    m,d=e.model,e.data
    peg=m.body('free_peg').id
    fingers=[m.body('tip_left').id,m.body('tip_right').id]
    result=np.zeros((2,3))
    for i in range(d.ncon):
        c=d.contact[i];a,b=[int(m.geom_bodyid[g]) for g in (c.geom1,c.geom2)]
        if peg not in (a,b):continue
        f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f)
        world=c.frame.reshape(3,3).T@f[:3]  # Force on geom2; rows are world-frame axes.
        for j,body in enumerate(fingers):
            if a==body:result[j]-=world
            if b==body:result[j]+=world
    axes=[d.xaxis[m.joint(name).id] for name in ('joint7','joint8')]
    return np.array([-result[j]@axes[j] for j in range(2)])


def squeeze_score(e,goal):
    forces=squeeze_load(e);load=float(forces.sum());error=abs(load-goal)/goal
    return dict(load_n=load,left_n=float(forces[0]),right_n=float(forces[1]),
                relative_error=error,in_band=bool(error<=.2 and min(forces)>.05),
                jaw_effort_n=float(e.data.actuator_force[e.aids[6]]))


class SqueezeSkill:
    """Reusable jaw-channel controller; keep active concurrently with arm motion.

    Goal bounds describe the trained experimental range, not a hardware safety
    guarantee. Entry/exit and force guards remain responsibilities of the caller.
    """
    skill_id='yam.regulate_axial_squeeze.v2'
    controls=('joint7',)
    control_hz=50

    def __init__(self,checkpoint,goal_n):
        if not np.isfinite(goal_n) or not 2.5<=goal_n<=4.5:
            raise ValueError('Requested squeeze is outside trained 2.5–4.5 N range')
        self.actor=NumpyActor(checkpoint);self.goal_n=float(goal_n)

    def act(self,env):
        return jaw_action(env,self.actor(squeeze_observation(env,self.goal_n)))


class SqueezeEnv(GripRegulationEnv):
    def __init__(self,bank):
        import gymnasium as gym
        super().__init__(bank)
        self.observation_space=gym.spaces.Box(-np.inf,np.inf,(6,),dtype=np.float32)

    def reset(self,*,seed=None,options=None):
        _,info=super().reset(seed=seed,options=options)
        self.goal=float((options or {}).get('goal',self.np_random.uniform(2.5,4.5)))
        info['goal_n']=self.goal
        return squeeze_observation(self.base,self.goal),info

    def step(self,action):
        _,_,base_done,_,base_info=self.base.step(jaw_action(self.base,action))
        row=squeeze_score(self.base,self.goal);self.n+=1;self.peak=max(self.peak,row['load_n'])
        dropped=self.mode=='held' and self.base.data.site_xpos[self.base.task.pid,2]<self.initial_z-.01
        violation=row['load_n']>8 or dropped or (base_done and base_info['reason']!='success')
        self.stable=self.stable+1 if row['in_band'] else 0
        if self.stable>=15 and self.first is None:self.first=self.n*DT
        reward=1.-min(row['relative_error'],2.)-.002*float(np.square(action).sum())-.005
        if min(row['left_n'],row['right_n'])>.05:reward+=.05
        if violation:reward-=5
        self.total+=reward;truncated=self.n>=HORIZON and not violation
        row.update(goal_n=self.goal,mode=self.mode,peak_load_n=self.peak,steps=self.n,
                   is_success=bool(self.stable>=15 and not violation),violation=bool(violation),
                   dropped=bool(dropped),first_stable_s=self.first,return_sum=self.total)
        if violation or truncated:self.rows.append(row.copy())
        return squeeze_observation(self.base,self.goal),float(reward),bool(violation),truncated,row
