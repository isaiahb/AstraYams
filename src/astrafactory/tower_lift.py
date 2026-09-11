"""Embodiment-specific, finite-actuator commissioning environment.

This is a control/clearance gym. It does not yet implement a harvesting reward
and cannot reuse YAM policy weights for SO-101.
"""
from pathlib import Path
import gymnasium as gym
from gymnasium import spaces
import mujoco
import numpy as np


class TowerLiftEnv(gym.Env):
    metadata = {'render_modes': []}

    def __init__(self, scene_dir, horizon_s=6.):
        self.scene_dir=Path(scene_dir)
        self.model=mujoco.MjModel.from_xml_path(str((self.scene_dir/'scene.xml').resolve()))
        self.data=mujoco.MjData(self.model)
        self.initial=np.load(self.scene_dir/'initial.npz')
        m=self.model
        self.dt=.02;self.substeps=round(self.dt/m.opt.timestep)
        assert np.isclose(self.substeps*m.opt.timestep,self.dt)
        self.joints=m.actuator_trnid[:,0].copy()
        self.qids=m.jnt_qposadr[self.joints];self.vids=m.jnt_dofadr[self.joints]
        self.lift=m.actuator('lift_motor').id
        self.rate=np.full(m.nu,.40);self.rate[self.lift]=.08
        self.rate[m.jnt_type[self.joints]==mujoco.mjtJoint.mjJNT_SLIDE]=.025
        self.rate[self.lift]=.08
        self.low=m.actuator_ctrlrange[:,0].copy();self.high=m.actuator_ctrlrange[:,1].copy()
        self.action_space=spaces.Box(-1,1,(m.nu,),dtype=np.float32)
        self.observation_space=spaces.Box(-np.inf,np.inf,(2*m.nu+3,),dtype=np.float64)
        self.horizon=round(horizon_s/self.dt)

    def observation(self):
        return np.r_[self.data.qpos[self.qids],self.data.qvel[self.vids],
                     self.data.xpos[self.model.body('fruit_secondary_b').id]]

    def reset(self,seed=None,options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model,self.data)
        self.data.qpos[:]=self.initial['qpos'];self.target=self.initial['ctrl'].copy()
        self.data.ctrl[:]=self.target;self.steps=0;self.peak_overlap=0.;self.peak_contact=0.
        mujoco.mj_forward(self.model,self.data)
        return self.observation(),{'task':'commissioning only; no harvest reward'}

    def step(self,action):
        action=np.asarray(action,dtype=float)
        if action.shape!=(self.model.nu,) or not np.isfinite(action).all():
            raise ValueError('One finite normalized command per actuator is required')
        self.target=np.clip(self.target+np.clip(action,-1,1)*self.rate*self.dt,self.low,self.high)
        self.data.ctrl[:]=self.target
        for _ in range(self.substeps):
            mujoco.mj_step(self.model,self.data)
            for i,c in enumerate(self.data.contact):
                a,b=map(int,c.geom)
                if min(a,b)<0:continue
                if self.model.geom_contype[a]==2 or self.model.geom_contype[b]==2:
                    self.peak_overlap=max(self.peak_overlap,-float(c.dist))
                    f=np.zeros(6);mujoco.mj_contactForce(self.model,self.data,i,f)
                    self.peak_contact=max(self.peak_contact,float(max(0,f[0])))
        self.steps+=1
        warnings=int(np.sum(self.data.warning.number))
        invalid=not(np.isfinite(self.data.qpos).all() and np.isfinite(self.data.qvel).all()) or warnings>0 or not np.isclose(self.data.time,self.steps*self.dt)
        return self.observation(),0.,invalid,self.steps>=self.horizon,dict(
            sim_s=float(self.data.time),lift_height_m=float(self.data.qpos[self.qids[self.lift]]),
            lift_force_N=float(self.data.actuator_force[self.lift]),
            peak_robot_contact_N=self.peak_contact,peak_robot_overlap_m=self.peak_overlap,
            invalid=invalid,simulator_warning_count=warnings,harvest_success=None,controller='Finite actuator commands; scripted commissioning')
