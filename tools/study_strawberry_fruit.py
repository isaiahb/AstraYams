"""Finite-body orientation audit and an explicitly diagnostic attachment release.

This is NOT a blade/fracture or harvesting simulation. Release only disables a
weld; it never edits mass, pose, velocity, spring rest shape, or stiffness.
The history hypothesis is deliberately non-identifiable from a loaded photo:
half the initial joint rotation is assigned to rest curvature and stiffness is
doubled BEFORE the trial, preserving the initial elastic restoring moment.
It is a sensitivity counterexample, not a fitted model of biological growth.
"""
import argparse
import copy
import hashlib
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'assets/workcells/strawberry-specimen/fruit-study'
OLD = ROOT / 'assets/workcells/strawberry-specimen/parametric-study/v13'
NEW = P / 'v14'
FRUITS = ['green', 'primary', 'secondary_a', 'secondary_b']
BRANCHES = ['peduncle', 'green_stalk', 'primary_stalk', 'secondary', 'secondary_a', 'secondary_b']


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n')


def vector(a):
    return ' '.join(f'{x:.15g}' for x in np.ravel(a))


def spring_energy(m, d):
    total = 0.
    for j in range(m.njnt):
        if int(m.jnt_type[j]) != int(mujoco.mjtJoint.mjJNT_BALL):
            continue
        a = m.jnt_qposadr[j]
        q = Rotation.from_quat(d.qpos[a:a+4][[1, 2, 3, 0]])
        r = Rotation.from_quat(m.qpos_spring[a:a+4][[1, 2, 3, 0]])
        total += .5*m.jnt_stiffness[j]*(r.inv()*q).magnitude()**2
    return float(total)


def audit():
    rows = []
    for label, path in [('v13', OLD), ('v14', NEW)]:
        m = mujoco.MjModel.from_xml_path(str(path/'scene.xml'))
        d = mujoco.MjData(m)
        d.qpos[:] = np.load(path/'rest/rollout.npz')['qpos'][-1]
        mujoco.mj_forward(m, d)
        for fruit in FRUITS:
            b = m.body('fruit_'+fruit).id
            tip = m.body_parentid[b]
            segment = m.body_parentid[tip]
            tangent = d.xmat[segment].reshape(3, 3) @ m.body_pos[tip]
            tangent /= np.linalg.norm(tangent)
            axis = -d.xmat[b].reshape(3, 3)[:, 2]
            arm = d.xipos[b]-d.xpos[b]
            rows.append(dict(model=label, fruit=fruit, mass_g=float(m.body_mass[b]*1000),
                inertia_kg_m2=m.body_inertia[b].tolist(),
                COM_in_fruit_frame_mm=(1000*m.body_ipos[b]).tolist(),
                COM_world_m=d.xipos[b].tolist(), attachment_world_m=d.xpos[b].tolist(),
                angle_from_down_deg=float(np.degrees(np.arccos(np.clip(-axis[2], -1, 1)))),
                axis_to_terminal_stalk_deg=float(np.degrees(np.arccos(np.clip(axis@tangent, -1, 1)))),
                gravity_moment_about_attachment_Nm=np.cross(arm, m.body_mass[b]*m.opt.gravity).tolist()))
    dump(P/'orientation-audit.json', dict(rows=rows, density='Homogeneous fruit mesh plus five calyx geoms. No spatial tissue-density measurement.',
        orientation='Material-frame correction only. No state edited after settling.',
        caveat='Gravity moment need not be zero at equilibrium: elastic and contact moments can balance it.'))

    # Independent check: suspend the actual mesh/calyx at a torque-free ball
    # joint, then compare gravity acceleration to the parallel-axis theorem.
    tree = ET.parse(NEW/'scene.xml'); root = tree.getroot()
    r = ET.Element('mujoco'); ET.SubElement(r, 'compiler', angle='radian')
    ET.SubElement(r, 'option', gravity='0 0 -9.81')
    r.append(copy.deepcopy(root.find('asset')))
    w = ET.SubElement(r, 'worldbody')
    fruit = copy.deepcopy(root.find(".//body[@name='fruit_primary']"))
    fruit.set('pos', '0 0 .3'); fruit.set('quat', vector(Rotation.from_euler('x', 45, degrees=True).as_quat()[[3,0,1,2]]))
    ET.SubElement(fruit, 'joint', name='anchor', type='ball', damping='0', stiffness='0', armature='0')
    w.append(fruit)
    m = mujoco.MjModel.from_xml_string(ET.tostring(r, encoding='unicode')); d = mujoco.MjData(m)
    mujoco.mj_forward(m, d); b = m.body('fruit_primary').id
    R = d.xmat[b].reshape(3,3); Ri = d.ximat[b].reshape(3,3)
    arm = d.xipos[b]-d.xpos[b]; tau = np.cross(arm, m.body_mass[b]*m.opt.gravity)
    inertia = Ri@np.diag(m.body_inertia[b])@Ri.T + m.body_mass[b]*(np.dot(arm,arm)*np.eye(3)-np.outer(arm,arm))
    expected = np.linalg.solve(inertia,tau)
    jp=np.zeros((3,m.nv));jr=np.zeros_like(jp);mujoco.mj_jacBody(m,d,jp,jr,b)
    actual=jr@d.qacc
    error=float(np.linalg.norm(actual-expected))
    if error > 1e-7: raise RuntimeError('Finite-mass gravity torque check failed')
    dump(P/'finite-body-check.json', dict(expected_angular_accel_rad_s2=expected.tolist(),simulated_angular_accel_rad_s2=actual.tolist(),error_rad_s2=error,
        torque_Nm=tau.tolist(),pass_check=True,scope='Independent gravity/inertia unit check; not a biological calibration.'))


def prepare():
    out=P/'release';out.mkdir(parents=True,exist_ok=True)
    root=ET.parse(NEW/'scene.xml').getroot()
    m0=mujoco.MjModel.from_xml_path(str(NEW/'scene.xml'));d0=mujoco.MjData(m0);mujoco.mj_forward(m0,d0)
    fruit=root.find(".//body[@name='fruit_primary']")
    parent=next(x for x in root.iter('body') if fruit in list(x))
    b=m0.body('fruit_primary').id
    fruit.set('pos',vector(d0.xpos[b]));fruit.set('quat',vector(d0.xquat[b]))
    parent.remove(fruit);root.find('worldbody').append(fruit)
    ET.SubElement(fruit,'freejoint',name='fruit_release_free')
    equality=ET.SubElement(root,'equality')
    ET.SubElement(equality,'weld',name='fruit_attachment',body1=parent.get('name'),body2='fruit_primary',solref='.001 1',solimp='.9999 .9999 .001',torquescale='.03')
    # No post-release ghosting through the former attachment; the berry begins
    # 2 mm beyond the stalk tip, outside its rounded collision cap.
    contact=root.find('contact')
    for e in list(contact):
        if 'fruit_primary' in e.attrib.values():contact.remove(e)
    ET.SubElement(root.find('option'),'flag',energy='enable')
    ET.indent(root);ET.ElementTree(root).write(out/'scene.xml',encoding='unicode')
    m=mujoco.MjModel.from_xml_path(str(out/'scene.xml'));d=mujoco.MjData(m)
    d0.qpos[:]=np.load(NEW/'rest/rollout.npz')['qpos'][-1];mujoco.mj_forward(m0,d0)
    for j in range(m0.njnt):
        a=m0.jnt_qposadr[j];jj=m.joint(m0.joint(j).name).id;aa=m.jnt_qposadr[jj]
        n=4 if m0.jnt_type[j]==mujoco.mjtJoint.mjJNT_BALL else 1
        d.qpos[aa:aa+n]=d0.qpos[a:a+n]
    a=m.joint('fruit_release_free').qposadr[0];d.qpos[a:a+3]=d0.xpos[b];d.qpos[a+3:a+7]=d0.xquat[b]
    for i in range(3):d.ctrl[m.actuator('probe_'+str(i)).id]=d.qpos[m.joint('probe_'+str(i)).qposadr[0]]
    m.geom_contype[m.geom('probe_surface').id]=m.geom_conaffinity[m.geom('probe_surface').id]=0
    mujoco.mj_forward(m,d)
    # Let only the representation change (rigid tree -> soft equality) settle.
    for _ in range(round(2/m.opt.timestep)):mujoco.mj_step(m,d)
    mujoco.mj_forward(m,d)
    if any(w.number for w in d.warning):raise RuntimeError('Preparation unstable')
    np.savez_compressed(out/'initial-state.npz',qpos=d.qpos,qvel=d.qvel,ctrl=d.ctrl)
    dump(out/'protocol.json',dict(source_scene_sha256=hashlib.sha256((NEW/'scene.xml').read_bytes()).hexdigest(),
        scene_sha256=hashlib.sha256((out/'scene.xml').read_bytes()).hexdigest(),mujoco=mujoco.__version__,
        event='Disable calyx attachment weld at 1 s. No blade, fracture force, cutter work, or distal stem remnant modeled.',
        preprocessing='Start from v14 settled pose, reset velocities for this experiment, settle changed weld representation 2 s; both trials copy this state including its residual velocities.',
        growth_hypothesis='Before simulation: q_spring = exp(0.5 log(q_loaded)) and k_new = 2 k_old on truss ball joints. Restoring moment at the shared initial pose is preserved; tangent stiffness doubles. No growth law is being integrated.',
        unchanged_at_release=['all qpos','all qvel','masses','inertias','stiffness','spring references','contact filters'],
        interpretation='Hypothesis sensitivity; no known biological growth fraction, damping, or recoil magnitude.'))


def run(history=0., control=False, fine=False):
    name=('history' if history else 'elastic')+('-control' if control else '-release')+('-fine' if fine else '')
    out=P/'release'/name;out.mkdir(exist_ok=True,parents=True)
    m=mujoco.MjModel.from_xml_path(str(P/'release/scene.xml'));d=mujoco.MjData(m)
    if fine:m.opt.timestep*=.5
    z=np.load(P/'release/initial-state.npz');d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl']
    pg=m.geom('probe_surface').id;m.geom_contype[pg]=m.geom_conaffinity[pg]=0
    mujoco.mj_forward(m,d);before=d.qfrc_spring.copy();changed=[]
    if history:
        for j in range(m.njnt):
            if not any(m.joint(j).name.startswith(x+'_') for x in BRANCHES):continue
            a=m.jnt_qposadr[j];q=Rotation.from_quat(d.qpos[a:a+4][[1,2,3,0]])
            m.qpos_spring[a:a+4]=Rotation.from_rotvec(history*q.as_rotvec()).as_quat()[[3,0,1,2]]
            m.jnt_stiffness[j]/=1-history
            changed.append(dict(joint=m.joint(j).name,rest_quat=m.qpos_spring[a:a+4].tolist(),k_nm_per_rad=float(m.jnt_stiffness[j])))
    mujoco.mj_forward(m,d)
    moment_error=float(np.max(abs(d.qfrc_spring-before)))
    if moment_error>1e-8:raise RuntimeError('Hypotheses do not preserve initial spring forces')
    b=m.body('fruit_primary').id;tip=m.body('primary_stalk_tip').id;eq=m.equality('fruit_attachment').id
    names=['primary_stalk_tip','peduncle_tip','secondary_tip','fruit_primary','fruit_secondary_a','fruit_secondary_b','fruit_green','crown']
    ids=[m.body(x).id for x in names]
    states=[];vels=[];ts=[];poses=[];quats=[];coms=[];energies=[];active=[];contacts=[];maxpen=0.;weld_gap=0.;event=None
    rest_hash=hashlib.sha256(m.qpos_spring.tobytes()+m.jnt_stiffness.tobytes()).hexdigest()
    initial_energy=spring_energy(m,d);start=time.time();steps=round(4/m.opt.timestep);stride=round(.005/m.opt.timestep)
    for k in range(steps+1):
        if k==round(1/m.opt.timestep):
            q=d.qpos.copy();v=d.qvel.copy()
            if not control:d.eq_active[eq]=0
            mujoco.mj_forward(m,d)
            event=dict(time_s=float(d.time),qpos_jump=float(np.max(abs(d.qpos-q))),qvel_jump=float(np.max(abs(d.qvel-v))),spring_energy_J=spring_energy(m,d))
        if k%stride==0:
            # mj_forward synchronizes saved geometry with saved qpos.
            mujoco.mj_forward(m,d)
            states.append(d.qpos.copy());vels.append(d.qvel.copy());ts.append(float(d.time));poses.append(d.xpos[ids].copy());quats.append(d.xquat[ids].copy());coms.append(d.xipos[b].copy());active.append(int(d.eq_active[eq]));energies.append(spring_energy(m,d))
            berry_contacts=[]
            for c in d.contact:
                if c.dist<0:maxpen=max(maxpen,float(-c.dist*1000))
                if m.geom_bodyid[c.geom[0]]==b or m.geom_bodyid[c.geom[1]]==b:
                    if c.dist<=0:berry_contacts.append([m.geom(int(g)).name for g in c.geom])
            contacts.append(berry_contacts)
            if d.eq_active[eq]:weld_gap=max(weld_gap,float(np.linalg.norm(d.xpos[b]-d.xpos[tip])*1000))
        if k<steps:mujoco.mj_step(m,d)
        if any(w.number for w in d.warning) or not np.isfinite(d.qpos).all():raise RuntimeError('Unstable release diagnostic')
    unchanged=rest_hash==hashlib.sha256(m.qpos_spring.tobytes()+m.jnt_stiffness.tobytes()).hexdigest()
    np.savez_compressed(out/'rollout.npz',qpos=states,qvel=vels,t=ts,body_positions=poses,body_quaternions=quats,fruit_com=coms,spring_energy=energies,attachment_active=active,body_names=names)
    dump(out/'result.json',dict(name=name,dt_s=float(m.opt.timestep),seconds=float(d.time),wall_s=time.time()-start,
        initial_spring_energy_J=initial_energy,initial_spring_force_match_error=moment_error,history_fraction_hypothesis=history,
        initial_qpos_sha256=hashlib.sha256(z['qpos'].tobytes()).hexdigest(),initial_qvel_sha256=hashlib.sha256(z['qvel'].tobytes()).hexdigest(),
        event=event,constitutive_parameters_unchanged_during_trial=unchanged,warnings=[int(w.number) for w in d.warning],
        max_attached_weld_gap_mm=weld_gap,max_sampled_contact_penetration_mm=maxpen,modified_material_parameters=changed,
        target_contact_log=contacts,scope='Diagnostic attachment release, not blade cutting. Recoil is a model prediction; growth/stiffness hypothesis uncalibrated.'))
    print(name,'done',round(time.time()-start,2),'s',flush=True)


def compare():
    rows=[];convergence=[]
    for history in ['elastic','history']:
        p=P/'release';z=np.load(p/(history+'-release')/'rollout.npz');c=np.load(p/(history+'-control')/'rollout.npz')
        delta=z['body_positions']-c['body_positions'];t=z['t'];end=t>3.5
        report=json.loads((p/(history+'-release')/'result.json').read_text())
        rows.append(dict(hypothesis=history,max_primary_tip_recoil_mm=float(np.linalg.norm(delta[t>=1,0],axis=1).max()*1000),
            final_primary_tip_rise_mm=float(delta[end,0,2].mean()*1000),peduncle_tip_max_displacement_mm=float(np.linalg.norm(delta[t>=1,1],axis=1).max()*1000),
            neighbor_max_displacement_mm=float(np.linalg.norm(delta[t>=1,4:7],axis=2).max()*1000),
            initial_spring_energy_J=report['initial_spring_energy_J'],weld_gap_mm=report['max_attached_weld_gap_mm']))
        # Paired controls must agree up to the release event, independently of
        # the second hypothesis's own response to residual settling motion.
        if not np.array_equal(z['qpos'][t<1],c['qpos'][t<1]):
            raise RuntimeError('Release and control do not have the same pre-event history')
        if (p/(history+'-release-fine')/'rollout.npz').exists() and (p/(history+'-control-fine')/'rollout.npz').exists():
            f=np.load(p/(history+'-release-fine')/'rollout.npz');fc=np.load(p/(history+'-control-fine')/'rollout.npz')
            df=f['body_positions']-fc['body_positions'];fine_final=float(df[f['t']>3.5,0,2].mean()*1000)
            convergence.append(dict(hypothesis=history,coarse_dt_s=.000125,fine_dt_s=.0000625,
                final_tip_rise_fine_mm=fine_final,final_tip_rise_change_mm=abs(fine_final-rows[-1]['final_primary_tip_rise_mm']),
                max_tip_response_curve_difference_mm=float(np.linalg.norm(delta[:,0]-df[:,0],axis=1).max()*1000)))
    dump(P/'release/comparison.json',dict(results=rows,measurement='Difference from the matching uncut control at the same time. Final is last 0.5 s; not necessarily final equilibrium.',
        timestep_comparison=convergence,
        interpretation='Both initial loaded configurations and spring moments match; different rest curvature AND tangent stiffness predict different unloading. This does not identify which model fits real strawberries.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['audit','prepare','run','compare']);p.add_argument('--history',type=float,default=0.);p.add_argument('--control',action='store_true');p.add_argument('--fine',action='store_true');a=p.parse_args()
    if not 0<=a.history<1:raise ValueError('History fraction must be in [0,1)')
    if a.stage=='audit':audit()
    elif a.stage=='prepare':prepare()
    elif a.stage=='run':run(a.history,a.control,a.fine)
    else:compare()
