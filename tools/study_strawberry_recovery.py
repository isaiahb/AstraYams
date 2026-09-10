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
P=ROOT/'assets/workcells/strawberry-specimen/recovery-study/v2'
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


def settle():
    """Continue gravity equilibration; never reset plant poses or velocities."""
    m=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));d=mujoco.MjData(m)
    z=np.load(BASE/'initial-state.npz');d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl']
    mujoco.mj_forward(m,d)
    bid=m.body('fruit_primary').id;start=d.xpos[bid].copy();history=[]
    # The v1 controls showed a slow ~10-second mode. Observe at least 60 s,
    # then require a quiet 20-second window, without changing material values.
    for sec in range(1,181):
        mujoco.mj_step(m,d,nstep=round(1/m.opt.timestep));mujoco.mj_forward(m,d)
        history.append(dict(t_s=sec,position_m=d.xpos[bid].copy().tolist(),max_generalized_speed=float(abs(d.qvel).max())))
        if any(w.number for w in d.warning):raise RuntimeError('Settling warning')
        if sec>=60:
            recent=np.array([h['position_m'] for h in history[-21:]])
            drift=float(np.linalg.norm(recent-recent[0],axis=1).max()*1000)
            if drift<.003 and abs(d.qvel).max()<1e-5:break
    else:raise RuntimeError('Baseline did not settle within 180 s')
    np.savez_compressed(P/'initial-state.npz',qpos=d.qpos.copy(),qvel=d.qvel.copy(),ctrl=d.ctrl.copy())
    dump(P/'settling.json',dict(extra_gravity_time_s=sec,fruit_shift_from_v1_mm=((d.xpos[bid]-start)*1000).tolist(),last_20s_fruit_drift_mm=drift,max_generalized_speed=float(abs(d.qvel).max()),history=history,
        scope='Unchanged geometry, masses, springs, damping and constraints. Actual integrated gravity settling, no velocity reset. Each trial still requires its matched no-contact control.'))
    print('Settled baseline',sec,'s; final-window drift',drift,'mm',flush=True)


def prepare():
    P.mkdir(parents=True,exist_ok=True)
    settle()
    dump(P/'protocol.json',dict(source_checkpoint='b02ff19',rejected_recovery_checkpoint='05d0147',scene_path=str(BASE/'scene.xml'),scene_sha256=hashlib.sha256((BASE/'scene.xml').read_bytes()).hexdigest(),initial_state_sha256=hashlib.sha256((P/'initial-state.npz').read_bytes()).hexdigest(),
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
    m=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));d=mujoco.MjData(m);z=np.load(P/'initial-state.npz')
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


def compare():
    rows=[];reference={};mass=json.loads((BASE/'protocol.json').read_text())['fruit_mass_kg']
    for hold in [1,12]:
        reference[hold]=np.load(P/f'elastic-{hold}s/commands.npz')['command_world']
        initial_reference=np.load(P/f'elastic-{hold}s/rollout.npz')
        for material in ['elastic','relaxing','retained']:
            name=f'{material}-{hold}s';z=np.load(P/name/'rollout.npz');c=np.load(P/(name+'-control')/'rollout.npz')
            r=json.loads((P/name/'result.json').read_text());t=z['t'];endhold=HOLD_START+hold;delta=z['body_positions']-c['body_positions']
            hi=(t>HOLD_START+.2)&(t<endhold-.1);first=(t>HOLD_START+.1)&(t<HOLD_START+.3);last=(t>endhold-.3)&(t<endhold-.1)
            end=t>t[-1]-.5;force=z['tool_force'][:,2]
            accel=np.gradient(z['fruit_com_velocity'],t,axis=0)
            residual=z['tool_force']+z['other_force']+z['stem_force']+mass*np.array([0,0,-9.81])-mass*accel
            stage_drift=float(np.linalg.norm(z['cup_position'][hi]-z['cup_position'][hi][0],axis=1).max()*1000)
            control_drift=float(np.linalg.norm(c['body_positions'][:,0]-c['body_positions'][0,0],axis=1).max()*1000)
            own_commands=np.load(P/name/'commands.npz')['command_world'];control_commands=np.load(P/(name+'-control')/'commands.npz')['command_world']
            after_last=r['last_contact_s'];recover={}
            for sec in [.5,1,3,10]:
                i=int(np.argmin(abs(t-(after_last+sec))))
                recover[str(sec)]=dict(sample_time_s=float(t[i]),primary_tip_vertical_mm=float(delta[i,1,2]*1000),primary_tip_distance_mm=float(np.linalg.norm(delta[i,1])*1000),largest_neighbor_distance_mm=float(np.linalg.norm(delta[i,3:6],axis=1).max()*1000))
            row=dict(name=name,material=material,hold_s=hold,hold_force_start_n=float(force[first].mean()),hold_force_end_n=float(force[last].mean()),hold_force_change_n=float(force[last].mean()-force[first].mean()),max_hold_stage_drift_mm=stage_drift,
                max_hold_newton_residual_n=float(np.linalg.norm(residual[hi],axis=1).max()),control_fruit_drift_mm=control_drift,
                final_tip_distance_mm=float(np.linalg.norm(delta[end,1],axis=1).max()*1000),recovery_after_last_contact=recover,
                max_tip_displacement_mm=float(np.linalg.norm(delta[:,1],axis=1).max()*1000),max_neighbor_displacement_mm=float(np.linalg.norm(delta[:,3:6],axis=2).max()*1000),peak_contact_n=r['peak_target_contact_n'],max_overlap_mm=r['max_tool_overlap_mm'],
                checks=dict(initial_state_matched=bool(np.array_equal(z['qpos'][0],c['qpos'][0]) and np.array_equal(z['qvel'][0],c['qvel'][0])),identical_model_commands=bool(np.array_equal(own_commands,reference[hold])),identical_control_commands=bool(np.array_equal(own_commands,control_commands)),no_unintended_contact=not r['unintended_contacts'],contact_force_budget=r['peak_target_contact_n']<=.45,tool_overlap=r['max_tool_overlap_mm']<=.25,other_overlap=r['max_other_plant_overlap_mm']<=.1,no_warnings=not any(r['warnings']),initial_moments=r['initial_spring_moment_error_nm']<=1e-10,constants_unchanged=r['constants_unchanged'],control_drift=control_drift<=.1,hold_stage_drift=stage_drift<=1.,force_balance=float(np.linalg.norm(residual[hi],axis=1).max())<=.005,dissipation_monotone=bool(np.min(np.diff(z['maxwell_dissipated_j']))>=-1e-12),final_tool_clear=bool(np.linalg.norm(z['tool_force'][end],axis=1).max()<1e-5)))
            cr=json.loads((P/(name+'-control')/'result.json').read_text())
            row['checks']['initial_state_matches_other_hypotheses']=bool(np.array_equal(z['qpos'][0],initial_reference['qpos'][0]) and np.array_equal(z['qvel'][0],initial_reference['qvel'][0]))
            row['checks']['control_has_no_contact']=cr['peak_target_contact_n']==0 and not cr['unintended_contacts']
            row['checks']['control_no_warnings_or_constant_changes']=not any(cr['warnings']) and cr['constants_unchanged']
            row['all_checks_pass']=all(row['checks'].values());rows.append(row)
    fine=None
    if (P/'relaxing-1s-fine/rollout.npz').exists():
        a=np.load(P/'relaxing-1s/rollout.npz');b=np.load(P/'relaxing-1s-fine/rollout.npz')
        error=float(np.linalg.norm(a['fruit_com']-b['fruit_com'],axis=1).max()*1000)
        fr=json.loads((P/'relaxing-1s-fine/result.json').read_text())
        fc=dict(fruit_path=error<=.25,contact_force=fr['peak_target_contact_n']<=.45,tool_overlap=fr['max_tool_overlap_mm']<=.25,other_overlap=fr['max_other_plant_overlap_mm']<=.1,no_unintended_contact=not fr['unintended_contacts'],no_warnings=not any(fr['warnings']),constants_unchanged=fr['constants_unchanged'],initial_moments=fr['initial_spring_moment_error_nm']<=1e-10,initial_state_matched=bool(np.array_equal(a['qpos'][0],b['qpos'][0]) and np.array_equal(a['qvel'][0],b['qvel'][0])))
        fine=dict(max_fruit_path_difference_mm=error,max_cumulative_dissipation_difference_j=float(abs(a['maxwell_dissipated_j']-b['maxwell_dissipated_j']).max()),checks=fc,pass_check=all(fc.values()))
    result=dict(rows=rows,fine_timestep=fine,all_checks_pass=all(x['all_checks_pass'] for x in rows) and (fine is not None and fine['pass_check']),
        scope='Contact/numerical checks only. No matching real strawberry recovery curve was found or fitted. Model differences are hypotheses, not established tissue behavior.')
    dump(P/'comparison.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','run','compare']);parser.add_argument('--material',choices=['elastic','relaxing','retained'],default='elastic');parser.add_argument('--hold',type=float,default=1.);parser.add_argument('--control',action='store_true');parser.add_argument('--fine',action='store_true');a=parser.parse_args()
    if a.stage=='prepare':prepare()
    elif a.stage=='compare':compare()
    else:run(a.material,a.hold,a.control,a.fine)
