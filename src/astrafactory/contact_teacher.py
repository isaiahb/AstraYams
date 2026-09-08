"""Privileged pose-feedback scripted teacher for free-body YAM manipulation.

The controller observes the free peg; it never writes qpos, changes contacts,
adds constraints, or modifies acceptance. IK uses ContactEnv's scratch state.
"""
import numpy as np
from astrafactory.yam_env import yaw_matrix, rotation_error


def _exp(vector):
    theta=np.linalg.norm(vector)
    if theta<1e-12:return np.eye(3)
    a=vector/theta
    k=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return np.eye(3)+np.sin(theta)*k+(1-np.cos(theta))*(k@k)


def feedbackteacher(env,stop_after_lift=False):
    e=env.unwrapped;t=e.task
    if e.steps==0 or not hasattr(t,'feedback_state'):
        t.feedback_state={'stage':0,'counter':0,'retract':0}
    state=t.feedback_state;stage=state['stage']
    pos=e.data.site_xpos[t.sid].copy();rot=e.data.site_xmat[t.sid].reshape(3,3).copy()
    peg=e.data.site_xpos[t.pid].copy();pegrot=e.data.site_xmat[t.pid].reshape(3,3).copy()
    desired_rot=yaw_matrix(t.goal[3]);grip=-.02
    target=t.pick+np.array([0,0,.054]);limit=.0025
    if stage==0:
        if np.linalg.norm(pos-target)<.0008 and np.max(np.abs(e.data.qvel[e.vadr[:6]]))<.03:
            stage=1;state['counter']=0
    if stage==1:
        grip=-.0045;state['counter']+=1
        if state['counter']>45:stage=2
    if stage>=2:
        grip=-.0045
        # Reconstruct tool pose needed for desired peg pose from measured grasp.
        desired_rot=yaw_matrix(t.goal[3])@pegrot.T@rot
        local_offset=rot.T@(pos-peg)
        peg_target=np.r_[t.pick[:2],.085]
        if stage==2:
            if peg[2]>.083:stage=3;state['counter']=0
        if stage==3:
            state['counter']+=1
            if not stop_after_lift and state['counter']>25:stage=4
        if stage==4:
            peg_target=np.r_[t.goal[:2],.065]
            if np.linalg.norm(peg[:2]-t.goal[:2])<.0002 and abs(peg[2]-.065)<.0008 and np.linalg.norm(rotation_error(yaw_matrix(t.goal[3]),pegrot))<.007:
                stage=5
        if stage==5:
            peg_target=t.goal[:3].copy();limit=.0006 if peg[2]<.047 else .0012
            # Maintain lateral/angular alignment before approaching the rim.
            if np.linalg.norm(peg[:2]-t.goal[:2])>.0004 or np.linalg.norm(rotation_error(yaw_matrix(t.goal[3]),pegrot))>.008:
                peg_target[2]=peg[2]
            if t.force>32:
                state['retract']=35
            if state['retract']>0:
                peg_target[2]=max(.048,peg[2]+.004);state['retract']-=1
        target=peg_target+desired_rot@local_offset
    state['stage']=stage;t.stage=stage
    delta=target-pos;norm=np.linalg.norm(delta)
    waypoint=pos+delta*min(1,limit/max(norm,1e-9))
    if stage>=4:waypoint=pos+np.clip(delta,-limit,limit)
    angular=rotation_error(desired_rot,rot)
    angular*=min(1,.012/max(np.linalg.norm(angular),1e-9))
    q=e.ik(waypoint,_exp(angular)@rot,initial=e.target[:6])
    return np.r_[np.clip((q-e.target[:6])/e.scales[:6],-.4,.4),np.clip((grip-e.target[6])/e.scales[6],-.5,.5)].astype(np.float32)


teacher=feedbackteacher
