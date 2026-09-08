"""Deployment-facing data/command codec; no hardware connection or task state.

The gripper stroke conversion is an explicit simulation calibration assumption.
It must be measured on the chosen physical gripper before deployment.
"""
from dataclasses import dataclass
import numpy as np

SIM_FINGER_STROKE_M=.04695
PROPRIOCEPTION_SIZE=28


def finite_vector(value,size,name):
    x=np.asarray(value,dtype=np.float32).reshape(-1)
    if x.shape!=(size,) or not np.isfinite(x).all():raise ValueError(f'{name} must contain {size} finite values')
    return x


def pack_feedback(joint_pos,joint_vel,gripper_pos,gripper_vel,command_target,previous_action):
    """SDK feedback + locally known command history, in documented channel order."""
    q=np.r_[finite_vector(joint_pos,6,'joint_pos'),finite_vector(gripper_pos,1,'gripper_pos')]
    v=np.r_[finite_vector(joint_vel,6,'joint_vel'),finite_vector(gripper_vel,1,'gripper_vel')]
    return np.r_[q,v,finite_vector(command_target,7,'command_target'),
                 finite_vector(previous_action,7,'previous_action')].astype(np.float32)


def simulation_feedback(q7,qd7,target7,previous_action):
    """Convert simulated encoder channels only. No object/contact/model access."""
    q=finite_vector(q7,7,'q7').copy();v=finite_vector(qd7,7,'qd7').copy();t=finite_vector(target7,7,'target7').copy()
    q[6]/=-SIM_FINGER_STROKE_M;v[6]/=-SIM_FINGER_STROKE_M;t[6]/=-SIM_FINGER_STROKE_M
    return pack_feedback(q[:6],v[:6],q[6:],v[6:],t,previous_action)


@dataclass
class JointTargetCodec:
    """Pure conversion for a future SDK adapter. Does not send motor commands."""
    target: np.ndarray
    arm_limits: np.ndarray
    def __post_init__(self):
        self.target=finite_vector(self.target,7,'target').copy()
        self.arm_limits=np.asarray(self.arm_limits,dtype=np.float32)
        if self.arm_limits.shape!=(6,2) or not np.isfinite(self.arm_limits).all() or np.any(self.arm_limits[:,0]>=self.arm_limits[:,1]):
            raise ValueError('Expected six valid arm-limit pairs')
    def update(self,normalized_action):
        a=np.clip(finite_vector(normalized_action,7,'action'),-1,1)
        self.target[:6]=np.clip(self.target[:6]+.01*a[:6],self.arm_limits[:,0],self.arm_limits[:,1])
        self.target[6]=np.clip(self.target[6]-.0006/SIM_FINGER_STROKE_M*a[6],0,1)
        return self.target.copy()
