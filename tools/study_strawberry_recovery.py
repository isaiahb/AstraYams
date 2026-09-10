"""Load/hold/unload identification experiment; alternative, uncalibrated laws.

Same loaded plant and motor-command histories, intact fruit, real cup contact.
The Maxwell internal state evolves by a passive constitutive law, never by a
desired fruit pose. No biological fit is claimed without matching observations.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
import study_strawberry_support as support

ROOT=Path(__file__).resolve().parents[1]
BASE=support.P
P=ROOT/'assets/workcells/strawberry-specimen/recovery-study/v1'
HOLD_START=5.9
RETURN_DURATION=3.7
RECOVERY=15.
TAU=3.


def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2)+'\n')


def truss_joints(m):
    return np.array([j for j in range(m.njnt) if m.joint(j).name.endswith('_bend') and not m.joint(j).name.startswith(('leaf','petiole'))])


class MaxwellArm:
    """Isotropic rotational spring + dashpot in series, on SO(3).

    E = .5 k |Log(qv^-1 q)|²; torque = -k Log(qv^-1 q).
    qv evolves toward q with angular speed Log(qv^-1 q) / tau.
    A fixed-q update is exact, with E_new = E_old exp(-2 dt/tau).
    This arm is parallel to the unchanged MuJoCo equilibrium springs.
    """
    def __init__(self,m,q,tau=TAU,ratio=1.):
        self.joints=truss_joints(m)
        self.qindex=m.jnt_qposadr[self.joints,None]+np.arange(4)
        self.vindex=m.jnt_dofadr[self.joints,None]+np.arange(3)
        self.qv=q[self.qindex].copy();self.k=m.jnt_stiffness[self.joints]*ratio
        self.tau=tau;self.dissipation=0.;self.max_energy=0.;self.rv=np.zeros((len(self.joints),3))

    def strain(self,q):
        for i,idx in enumerate(self.qindex):mujoco.mju_subQuat(self.rv[i],q[idx],self.qv[i])
        return self.rv

    def callback(self,m,d):
        # No time/state advancement here: MuJoCo can call passive more than once.
        rv=self.strain(d.qpos)
        d.qfrc_passive[self.vindex.ravel()] -= (self.k[:,None]*rv).ravel()

    def energy(self,q):
        return float(.5*np.sum(self.k[:,None]*self.strain(q)**2))

    def advance(self,q,dt):
        rv=self.strain(q);energy=float(.5*np.sum(self.k[:,None]*rv**2))
        alpha=-np.expm1(-dt/self.tau)
        for i in range(len(self.joints)):mujoco.mju_quatIntegrate(self.qv[i],rv[i],alpha)
        self.dissipation+=energy*(-np.expm1(-2*dt/self.tau));self.max_energy=max(self.max_energy,energy)


def commands(t,hold,recorded):
    def sample(sec):
        return recorded['command_world'][int(round(sec/.01))].copy()
    anchor=sample(HOLD_START)
    if t<HOLD_START:return sample(t)
    if t<HOLD_START+hold:return anchor
    # The existing withdrawal path is translated so position stays continuous
    # at the new hold endpoint. Actuators, not qpos assignments, execute it.
    return sample(min(11.1,7.4+t-HOLD_START-hold))+anchor-sample(7.4)


def phase(t,hold):
    if t<.4:return 'rest'
    if t<1.9:return 'approach'
    if t<HOLD_START:return 'support'
    if t<HOLD_START+hold:return 'fixed-command hold'
    if t<HOLD_START+hold+RETURN_DURATION:return 'withdraw'
    return 'recovery'


def unit_checks():
    """Independent energy gradient, fixed-strain relaxation, analytic SLS creep."""
    rng=np.random.default_rng(42);worst=0.;decay_error=0.;loss_error=0.
    for _ in range(30):
        q=Rotation.from_rotvec(rng.normal(size=3)*.5).as_quat()[[3,0,1,2]]
        qv=Rotation.from_rotvec(rng.normal(size=3)*.4).as_quat()[[3,0,1,2]]
        k=.07;rv=np.zeros(3);mujoco.mju_subQuat(rv,q,qv);torque=-k*rv
        def energy(x):
            r=np.zeros(3);mujoco.mju_subQuat(r,x,qv);return .5*k*r@r
        grad=[]
        for axis in np.eye(3):
            qp=q.copy();qm=q.copy();mujoco.mju_quatIntegrate(qp,axis,1e-6);mujoco.mju_quatIntegrate(qm,axis,-1e-6)
            grad.append((energy(qp)-energy(qm))/2e-6)
        worst=max(worst,float(np.max(abs(np.array(grad)+torque))))
        before=energy(q);dt=.019;v=qv.copy();mujoco.mju_quatIntegrate(v,rv,1-np.exp(-dt/TAU))
        rnew=np.zeros(3);mujoco.mju_subQuat(rnew,q,v);after=.5*k*rnew@rnew
        decay_error=max(decay_error,float(np.max(abs(rnew-rv*np.exp(-dt/TAU)))))
        loss_error=max(loss_error,abs((before-after)-before*(1-np.exp(-2*dt/TAU))))
    # Independent scalar standard-solid step load + release. A material update
    # at constant strain is compared with the closed-form force-driven solution.
    k0=.07;k1=.07;moment=.001;dt=.001;hold=8.;qv=0.;max_creep=0.;max_recovery=0.
    ret=TAU*(k0+k1)/k0
    for i in range(round(20/dt)+1):
        t=i*dt;M=moment if t<hold else 0.;q=(M+k1*qv)/(k0+k1)
        if t<hold:
            expected=moment/k0*(1-k1/(k0+k1)*np.exp(-t/ret));max_creep=max(max_creep,abs(q-expected))
        else:
            expected=moment*k1/(k0*(k0+k1))*(1-np.exp(-hold/ret))*np.exp(-(t-hold)/ret);max_recovery=max(max_recovery,abs(q-expected))
        qv += (q-qv)*(-np.expm1(-dt/TAU))
    report=dict(max_noncommuting_rotation_energy_gradient_error_nm=worst,max_exact_relaxation_error_rad=decay_error,max_dissipation_identity_error_j=loss_error,max_scalar_creep_error_rad=max_creep,max_scalar_recovery_error_rad=max_recovery,
        checks=dict(conservative_torque=worst<1e-8,exact_relaxation=decay_error<1e-12,dissipation=loss_error<1e-12,scalar_creep=max_creep<1e-6,scalar_recovery=max_recovery<1e-6),scope='Mathematical implementation checks only, not strawberry calibration.')
    report['checks']={key:bool(value) for key,value in report['checks'].items()}
    dump(P/'constitutive-checks.json',report);print(json.dumps(report,indent=2),flush=True)
    if not all(report['checks'].values()):raise RuntimeError('Constitutive checks failed')


def prepare():
    P.mkdir(parents=True,exist_ok=True)
    dump(P/'protocol.json',dict(source_checkpoint='b02ff19',scene_path=str(BASE/'scene.xml'),scene_sha256=hashlib.sha256((BASE/'scene.xml').read_bytes()).hexdigest(),initial_state_sha256=hashlib.sha256((BASE/'initial-state.npz').read_bytes()).hexdigest(),
        intervention='Identical position-actuator commands across material models. Replay approach/support to 5.9 s; freeze command 1 or 12 s; continuous translated withdrawal; observe 15 s after withdrawal. Actual tool position and forces remain dynamic.',
        holds_s=[1.,12.],recovery_s=RECOVERY,hold_start_s=HOLD_START,withdraw_duration_s=RETURN_DURATION,
        material_hypotheses=dict(elastic='Original 45 MPa equilibrium truss, existing viscous damping; fixed rest shape.',relaxing='Original equilibrium branch plus equal-stiffness rotational Maxwell arm at all 42 truss joints; tau_relax=3 s, local scalar tau_creep=6 s. All numbers are uncalibrated sensitivity choices.',retained='Before trial, assign half loaded joint rotation to fixed rest curvature and double spring stiffness, preserving initial restoring moments. No growth, damage or plastic flow during trial.'),
        unknown_parameter_ranges=dict(equilibrium_truss_modulus_mpa='45 inherited modeling assumption, not a published fruit-stalk calibration',maxwell_ratio='1 illustrative, unmeasured',relaxation_time_s='3 illustrative; alternative 1/10/100 s scalar sensitivity, not biological bounds',retained_rest_fraction='.5 illustrative and confounded with stiffness'),
        acceptance=dict(initial_spring_moment_match_nm=1e-10,maximum_contact_force_n=.45,maximum_tool_overlap_mm=.25,maximum_other_plant_overlap_mm=.1,unintended_instrument_contacts=0,no_contact_control_drift_mm=.1,max_hold_stage_drift_mm=1.,newton_hold_residual_n=.005,half_timestep_fruit_path_difference_mm=.25),
        outcome_not_acceptance='Residual curvature, force relaxation and recovery time are model predictions. Do not tune them to pass a preferred rebound appearance.',
        limitations='No real recovery observations fitted. Fixed crown, rigid fruit, no cutting, tissue damage, measured relaxation spectrum or evolved growth history. One relaxing branch is a discrimination prototype, not an established plant constitutive law.'))
    unit_checks()


def run(material,hold,control=False,fine=False):
    name=f'{material}-{int(hold)}s'+('-control' if control else '')+('-fine' if fine else '')
    out=P/name;out.mkdir(parents=True,exist_ok=True)
    m=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));d=mujoco.MjData(m);z=np.load(BASE/'initial-state.npz')
    if fine:m.opt.timestep/=2
    d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl']
    pg=m.geom('probe_surface').id;m.geom_contype[pg]=m.geom_conaffinity[pg]=0
    rig={m.body(n).id for n in ['stage_frame','support_z','support_y','support_x']}
    if control:
        for i in range(m.ngeom):
            if m.geom_bodyid[i] in rig:m.geom_contype[i]=m.geom_conaffinity[i]=0
    mujoco.mj_forward(m,d);before=d.qfrc_spring.copy();joints=truss_joints(m)
    if material=='retained':
        for j in joints:
            a=m.jnt_qposadr[j];q=Rotation.from_quat(d.qpos[a:a+4][[1,2,3,0]])
            m.qpos_spring[a:a+4]=Rotation.from_rotvec(.5*q.as_rotvec()).as_quat()[[3,0,1,2]];m.jnt_stiffness[j]*=2
    arm=MaxwellArm(m,d.qpos) if material=='relaxing' else None
    if arm:mujoco.set_mjcb_passive(arm.callback)
    mujoco.mj_forward(m,d);moment_error=float(abs(d.qfrc_spring-before).max())
    if moment_error>1e-10:raise RuntimeError('Initial material spring moments differ')
    frozen=hashlib.sha256(m.qpos_spring.tobytes()+m.jnt_stiffness.tobytes()+m.body_mass.tobytes()+m.body_inertia.tobytes()).hexdigest()
    source=np.load(BASE/'support/commands.npz');proto=json.loads((BASE/'protocol.json').read_text());ff=np.array(proto['gravity_feedforward_joint_m'])
    mot=np.array([m.actuator(f'support_{a}_motor').id for a in 'xyz']);target=m.body('fruit_primary').id;sid=m.site('calyx_loadcell').id
    names=['fruit_primary','primary_stalk_tip','peduncle_tip','fruit_secondary_a','fruit_secondary_b','fruit_green'];bids=[m.body(n).id for n in names]
    duration=HOLD_START+hold+RETURN_DURATION+RECOVERY;steps=round(duration/m.opt.timestep);save=round(.02/m.opt.timestep);ctrlsteps=round(.01/m.opt.timestep)
    logs={k:[] for k in ['t','qpos','qvel','tool_force','stem_force','other_force','body_positions','fruit_com','fruit_com_velocity','fruit_quaternion','cup_position','command_world','phase','maxwell_energy_j','maxwell_dissipated_j','maxwell_qv']}
    peak=0.;depth=0.;other_depth=0.;wrong=set();first_touch=None;last_touch=None;tc=time.time();command_log=[];cmd=source['command_world'][0].copy()
    print('Running',name,round(duration,2),'s',flush=True)
    try:
        for k in range(steps+1):
            t=k*m.opt.timestep
            if k%ctrlsteps==0:
                cmd=commands(round(t,8),hold,source);d.ctrl[mot]=cmd-support.ORIGIN-support.TIP+ff;command_log.append(cmd.copy())
            tool,other,_,bad,dep,depo=support.contact_forces(m,d,target,rig)
            peak=max(peak,float(np.linalg.norm(tool)));depth=max(depth,dep);other_depth=max(other_depth,depo);wrong|=bad
            if np.linalg.norm(tool)>1e-5:
                if first_touch is None:first_touch=t
                last_touch=t
            if k%save==0 or k==steps:
                mujoco.mj_forward(m,d);tool,other,*_=support.contact_forces(m,d,target,rig)
                jp=np.zeros((3,m.nv));jr=np.zeros_like(jp);mujoco.mj_jacBodyCom(m,d,jp,jr,target)
                vals=dict(t=t,qpos=d.qpos.copy(),qvel=d.qvel.copy(),tool_force=tool,other_force=other,stem_force=d.site_xmat[sid].reshape(3,3)@d.sensor('stem_force').data,
                    body_positions=d.xpos[bids].copy(),fruit_com=d.xipos[target].copy(),fruit_com_velocity=jp@d.qvel,fruit_quaternion=d.xquat[target].copy(),cup_position=d.site_xpos[m.site('cup_center').id].copy(),command_world=cmd.copy(),phase=phase(t,hold),
                    maxwell_energy_j=arm.energy(d.qpos) if arm else 0.,maxwell_dissipated_j=arm.dissipation if arm else 0.,maxwell_qv=arm.qv.copy() if arm else np.empty((0,4)))
                for key in logs:logs[key].append(vals[key])
            if k<steps:
                mujoco.mj_step(m,d)
                if arm:arm.advance(d.qpos,m.opt.timestep)
            if any(w.number for w in d.warning) or not np.isfinite(d.qpos).all():raise RuntimeError('Unstable trial')
    finally:mujoco.set_mjcb_passive(None)
    np.savez_compressed(out/'rollout.npz',**logs,body_names=names)
    np.savez_compressed(out/'commands.npz',command_world=command_log)
    report=dict(name=name,material=material,hold_s=hold,control=control,dt_s=float(m.opt.timestep),duration_s=duration,wall_s=time.time()-tc,first_contact_s=first_touch,last_contact_s=last_touch,peak_target_contact_n=peak,max_tool_overlap_mm=depth,max_other_plant_overlap_mm=other_depth,unintended_contacts=sorted(wrong),initial_spring_moment_error_nm=moment_error,constants_unchanged=frozen==hashlib.sha256(m.qpos_spring.tobytes()+m.jnt_stiffness.tobytes()+m.body_mass.tobytes()+m.body_inertia.tobytes()).hexdigest(),maxwell_dissipation_j=arm.dissipation if arm else 0.,warnings=[int(w.number) for w in d.warning],scope='Uncalibrated constitutive hypotheses, physical contact with identical commanded stage paths. No plant pose overrides.')
    dump(out/'result.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','run']);parser.add_argument('--material',choices=['elastic','relaxing','retained'],default='elastic');parser.add_argument('--hold',type=float,default=1.);parser.add_argument('--control',action='store_true');parser.add_argument('--fine',action='store_true');a=parser.parse_args()
    if a.stage=='prepare':prepare()
    else:run(a.material,a.hold,a.control,a.fine)
