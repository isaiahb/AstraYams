"""Contact-driven support/unweighting of an intact v14 strawberry cluster.

The cup is mounted on force-limited prismatic stages. Its outer controller uses
measured contact forces; no fruit poses, attachment states or material laws are
edited during a trial. This is a virtual test instrument, not a YAM policy or a
biologically calibrated harvesting end effector.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/workcells/strawberry-specimen/fruit-study/v14'
P=ROOT/'assets/workcells/strawberry-specimen/support-study/v1'
ORIGIN=np.array([-.11,-.095,.10])
TIP=np.array([0.,.06,0.])
KP=240.
CONTROL_DT=.01
DURATION=13.


def vec(a):return ' '.join(f'{x:.12g}' for x in np.ravel(a))
def add(p,tag,**kw):return ET.SubElement(p,tag,{k:str(v) for k,v in kw.items()})
def dump(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2)+'\n')
def smooth(t):t=np.clip(t,0.,1.);return t*t*(3-2*t)
def phase(t):
    return next(name for end,name in [(.4,'rest'),(1.9,'approach'),(5.9,'load'),(7.4,'hold'),(8.6,'unload'),(9.6,'lower'),(11.1,'retreat'),(99,'recover')] if t<end)


def prepare():
    P.mkdir(parents=True,exist_ok=True)
    r=ET.parse(BASE/'scene.xml').getroot();w=r.find('worldbody');asset=r.find('asset');act=r.find('actuator')
    frame=add(w,'body',name='stage_frame')
    add(frame,'geom',name='stage_base',type='box',pos='-.11 -.095 .010',size='.039 .030 .01',rgba='.24 .29 .31 1')
    add(frame,'geom',name='stage_column',type='box',pos='-.11 -.095 .10',size='.008 .009 .085',rgba='.55 .59 .61 1')
    z=add(w,'body',name='support_z',pos=vec(ORIGIN));add(z,'joint',name='support_z_axis',type='slide',axis='0 0 1',damping='.15',range='-.025 .09')
    add(z,'geom',name='z_carriage',type='box',size='.013 .014 .009',mass='.04',rgba='.17 .24 .27 1')
    y=add(z,'body',name='support_y');add(y,'joint',name='support_y_axis',type='slide',axis='0 1 0',damping='.15',range='-.025 .035')
    add(y,'geom',name='y_carriage',type='box',pos='0 0 -.009',size='.015 .018 .005',mass='.018',rgba='.46 .53 .55 1')
    add(y,'geom',name='x_guide',type='box',pos='.065 0 -.017',size='.074 .004 .004',mass='.017',rgba='.67 .69 .68 1')
    x=add(y,'body',name='support_x');add(x,'joint',name='support_x_axis',type='slide',axis='1 0 0',damping='.15',range='.015 .16')
    add(x,'geom',name='x_carriage',type='box',pos='0 0 -.014',size='.012 .010 .007',mass='.019',rgba='.2 .27 .3 1')
    add(x,'geom',name='cup_arm',type='capsule',fromto='0 0 -.005 0 .056 -.005',size='.0022',mass='.009',rgba='.58 .64 .67 1')
    add(x,'geom',name='cup_floor',type='cylinder',pos=vec(TIP+[0,0,-.001]),size='.004 .001',mass='.001',rgba='.07 .46 .56 1',solref='.002 1',priority='2',friction='.4 .003 .001')
    # Concave support surface assembled from convex wall sectors. Each sector
    # has the same visible/collision vertices; no invisible enclosing hull.
    for j in range(20):
        vs=[]
        for a in [2*np.pi*j/20,2*np.pi*(j+1)/20]:
            for rad,h in [(.004,0),(.010,.005),(.011,.0047),(.004,-.002)]:vs.append(TIP+[rad*np.cos(a),rad*np.sin(a),h])
        hull=trimesh.convex.convex_hull(vs);name=f'cup_sector_{j}'
        add(asset,'mesh',name=name,vertex=vec(hull.vertices),face=' '.join(str(int(i)) for i in hull.faces.ravel()))
        add(x,'geom',name=name,type='mesh',mesh=name,mass='.00015',rgba='.08 .47 .57 1',solref='.002 1',priority='2',friction='.4 .003 .001')
    add(x,'site',name='cup_center',pos=vec(TIP),size='.001',rgba='0 0 0 0')
    fruit=r.find(".//body[@name='fruit_primary']");add(fruit,'site',name='calyx_loadcell',size='.001',rgba='0 0 0 0')
    sensors=add(r,'sensor');add(sensors,'force',name='stem_force',site='calyx_loadcell');add(sensors,'torque',name='stem_torque',site='calyx_loadcell')
    for a in ['x','y','z']:add(act,'position',name=f'support_{a}_motor',joint=f'support_{a}_axis',kp=str(KP),kv='7',forcerange='-2 2')
    assembly=['stage_frame','support_z','support_y','support_x']
    for i,a in enumerate(assembly):
        for b in assembly[i+1:]:add(r.find('contact'),'exclude',body1=a,body2=b)
    # Guide/slider interfaces are ideal prismatic constraints. Only internal
    # instrument pairs are excluded; every external plant contact stays active.
    ET.indent(r);ET.ElementTree(r).write(P/'scene.xml',encoding='unicode')
    m=mujoco.MjModel.from_xml_path(str(P/'scene.xml'));d=mujoco.MjData(m)
    m0=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));d0=mujoco.MjData(m0);d0.qpos[:]=np.load(BASE/'rest/rollout.npz')['qpos'][-1];mujoco.mj_forward(m0,d0)
    for j in range(m0.njnt):
        n=4 if m0.jnt_type[j]==mujoco.mjtJoint.mjJNT_BALL else 1;a=m0.jnt_qposadr[j];aa=m.joint(m0.joint(j).name).qposadr[0];d.qpos[aa:aa+n]=d0.qpos[a:a+n]
    b=m0.body('fruit_primary').id
    bottom=d0.xpos[b]+d0.xmat[b].reshape(3,3)@np.array([0,0,-.039])
    under=np.array([*d0.xipos[b][:2],bottom[2]-.006]);start=under+[-.050,0,0]
    ids=np.array([m.joint(f'support_{a}_axis').qposadr[0] for a in ['x','y','z']]);mot=np.array([m.actuator(f'support_{a}_motor').id for a in ['x','y','z']])
    ff=np.array([0,0,m.body_subtreemass[m.body('support_z').id]*9.81/KP])
    d.qpos[ids]=start-ORIGIN-TIP;d.ctrl[mot]=d.qpos[ids]+ff
    for i in range(3):d.ctrl[m.actuator(f'probe_{i}').id]=d.qpos[m.joint(f'probe_{i}').qposadr[0]]
    pg=m.geom('probe_surface').id;m.geom_contype[pg]=m.geom_conaffinity[pg]=0
    mujoco.mj_forward(m,d)
    for _ in range(round(2/m.opt.timestep)):mujoco.mj_step(m,d)
    mujoco.mj_forward(m,d)
    if any(w.number for w in d.warning):raise RuntimeError('Stage initialization unstable')
    np.savez_compressed(P/'initial-state.npz',qpos=d.qpos,qvel=d.qvel,ctrl=d.ctrl)
    dump(P/'protocol.json',dict(source_scene_sha256=hashlib.sha256((BASE/'scene.xml').read_bytes()).hexdigest(),scene_sha256=hashlib.sha256((P/'scene.xml').read_bytes()).hexdigest(),mujoco=mujoco.__version__,
        start_m=start.tolist(),under_m=under.tolist(),gravity_feedforward_joint_m=ff.tolist(),fruit_mass_kg=float(m.body_mass[m.body('fruit_primary').id]),
        controller=dict(rate_hz=100,position_kp_n_m=KP,position_kv_ns_m=7,axis_force_limit_n=2,force_feedback_gain_m_ns=.10,maximum_force_feedback_speed_m_s=.014,target_support_fraction=.8),
        acceptance=dict(initial_instrument_plant_contacts=0,non_target_instrument_plant_contacts=0,hold_support_fraction=[.7,.9],minimum_stem_vertical_unloading_fraction=.6,max_cup_fruit_penetration_mm=.25,max_other_plant_penetration_mm=.1,max_target_contact_resultant_n=.45,final_no_contact=True,maximum_final_fruit_displacement_mm=2.,maximum_hold_force_balance_residual_n=.005),
        limits='Engineering diagnostic limits chosen before running, not measured damage/safety thresholds. Fruit/cup rigidity and friction uncalibrated.',
        phases=dict(rest=[0,.4],approach=[.4,1.9],load=[1.9,5.9],hold=[5.9,7.4],unload=[7.4,8.6],lower=[8.6,9.6],retreat=[9.6,11.1],recover=[11.1,13]),
        scope='Intact v14 tree; no weld toggles, cutting, plant-state overrides, or material changes. Ideal actuated bench stages, not a robot policy.',
        exclusions='Internal guide/slider pairs use ideal prismatic joints. No external plant contact exclusions.',
        evidence=[dict(url='https://arxiv.org/html/2207.12552',use='Supports separating attachment, detachment, transport and cluster interaction; reports specific peduncle tests. Its gripping/cutting forces are not used as fruit-body safety thresholds.')]))
    print('Prepared',P,flush=True)


def contact_forces(m,d,target,rig):
    tool=np.zeros(3);other=np.zeros(3);touch={};wrong=set();depth_tool=0.;depth_other=0.
    for k,c in enumerate(d.contact):
        if c.dist>0:continue
        g1,g2=map(int,c.geom);b1,b2=m.geom_bodyid[[g1,g2]];n1,n2=m.geom(g1).name,m.geom(g2).name
        is_tool=(b1 in rig) or (b2 in rig)
        if target in (b1,b2):
            f=np.zeros(6);mujoco.mj_contactForce(m,d,k,f);world=c.frame.reshape(3,3).T@f[:3];on_target=world*(1 if b2==target else -1)
            if is_tool:tool+=on_target;depth_tool=max(depth_tool,float(-c.dist*1000))
            else:other+=on_target
        if is_tool:
            n=n2 if b1 in rig else n1
            if n not in ['ground'] and not (b1 in rig and b2 in rig):
                touch[n]=touch.get(n,0)+1
                if not n.startswith(('berry_primary','seed_primary','calyx_primary')):wrong.add(n)
        elif n1!='ground' and n2!='ground':depth_other=max(depth_other,float(-c.dist*1000))
    return tool,other,touch,wrong,depth_tool,depth_other


def run(control=False,fine=False,commands_from=None):
    protocol=json.loads((P/'protocol.json').read_text());name=('control' if control else 'support')+('-fine' if fine else '')
    out=P/name;out.mkdir(parents=True,exist_ok=True);m=mujoco.MjModel.from_xml_path(str(P/'scene.xml'));d=mujoco.MjData(m)
    if fine:m.opt.timestep/=2
    z=np.load(P/'initial-state.npz');d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl']
    pg=m.geom('probe_surface').id;m.geom_contype[pg]=m.geom_conaffinity[pg]=0
    rig={m.body(n).id for n in ['stage_frame','support_z','support_y','support_x']}
    if control:
        for i in range(m.ngeom):
            if m.geom_bodyid[i] in rig:m.geom_contype[i]=m.geom_conaffinity[i]=0
    target=m.body('fruit_primary').id;sid=m.site('calyx_loadcell').id;mass=m.body_mass[target];weight=mass*9.81
    ids=np.array([m.joint(f'support_{a}_axis').qposadr[0] for a in ['x','y','z']]);mot=np.array([m.actuator(f'support_{a}_motor').id for a in ['x','y','z']])
    start=np.array(protocol['start_m']);under=np.array(protocol['under_m']);ff=np.array(protocol['gravity_feedforward_joint_m']);cmd=start.copy();filtered=np.zeros(3);target_force=np.zeros(3)
    replay=np.load(commands_from) if commands_from else np.load(P/('support-fine' if fine else 'support')/'commands.npz') if control else None
    mujoco.mj_forward(m,d);initial=contact_forces(m,d,target,rig)[2];initial_stem=d.site_xmat[sid].reshape(3,3)@d.sensor('stem_force').data.copy()
    print(name,'initial stem world force',initial_stem,'weight',weight,'initial contacts',initial,flush=True)
    # Sensor sign is independently checked against the held fruit's weight.
    stem_sign=1 if initial_stem[2]>0 else -1
    if abs(abs(initial_stem[2])-weight)>.02:raise RuntimeError('Initial stem load does not account for fruit weight')
    pose_hash=hashlib.sha256(m.qpos_spring.tobytes()+m.jnt_stiffness.tobytes()+m.body_mass.tobytes()+m.body_inertia.tobytes()).hexdigest()
    names=['fruit_primary','primary_stalk_tip','peduncle_tip','fruit_secondary_a','fruit_secondary_b','fruit_green'];bids=[m.body(n).id for n in names]
    logs={k:[] for k in ['t','qpos','qvel','tool_force','other_force','stem_force','stem_torque','fruit_com','fruit_com_velocity','body_positions','cup_position','actuator_force','joint_velocity','command_world','force_target','phase']}
    commands=[];times=[];wrong=set();all_touched={};maxdepth=0.;otherdepth=0.;peakforce=0.;low_start=None;return_start=None;tc=time.time();clocksteps=round(CONTROL_DT/m.opt.timestep);save=round(.005/m.opt.timestep);steps=round(DURATION/m.opt.timestep)
    for k in range(steps+1):
        t=k*m.opt.timestep
        if k%clocksteps==0:
            f=contact_forces(m,d,target,rig)[0];filtered+=.25*(f-filtered)
            if replay is not None:
                idx=min(round(t/CONTROL_DT),len(replay['command_world'])-1);cmd=replay['command_world'][idx].copy();target_force=replay['target_force'][idx].copy()
            elif t<.4:cmd=start.copy()
            elif t<1.9:cmd=start+(under-start)*smooth((t-.4)/1.5)
            elif t<8.6:
                fraction=.8*smooth((t-1.9)/1.) if t<5.9 else .8 if t<7.4 else .8*(1-smooth((t-7.4)/1.2))
                target_force=np.array([0.,0.,fraction*weight]);velocity=np.clip(.10*(target_force-filtered),-.014,.014)
                cmd+=velocity*CONTROL_DT
                cmd=np.clip(cmd,under+[-.025,-.025,-.010],under+[.025,.025,.045])
            elif t<9.6:
                if low_start is None:low_start=cmd.copy()
                target_force[:]=0;cmd=low_start+np.array([0,0,-.010])*smooth((t-8.6)/1.)
            elif t<11.1:
                if return_start is None:return_start=cmd.copy()
                back=start.copy();back[2]=return_start[2];cmd=return_start+(back-return_start)*smooth((t-9.6)/1.5)
            d.ctrl[mot]=cmd-ORIGIN-TIP+ff
            commands.append(cmd.copy());times.append(t)
            # Keep force target alongside the command for exact negative-control playback.
            if k==0:targets=[]
            targets.append(target_force.copy())
        tool,other,touched,bad,dep,dep_other=contact_forces(m,d,target,rig);wrong|=bad;maxdepth=max(maxdepth,dep);otherdepth=max(otherdepth,dep_other);peakforce=max(peakforce,float(np.linalg.norm(tool)))
        for n,c in touched.items():all_touched[n]=all_touched.get(n,0)+c
        if k%save==0:
            mujoco.mj_forward(m,d);tool,other,*_=contact_forces(m,d,target,rig)
            force=stem_sign*(d.site_xmat[sid].reshape(3,3)@d.sensor('stem_force').data)
            torque=stem_sign*(d.site_xmat[sid].reshape(3,3)@d.sensor('stem_torque').data)
            jp=np.zeros((3,m.nv));jr=np.zeros_like(jp);mujoco.mj_jacBodyCom(m,d,jp,jr,target)
            vals=dict(t=t,qpos=d.qpos.copy(),qvel=d.qvel.copy(),tool_force=tool,other_force=other,stem_force=force,stem_torque=torque,fruit_com=d.xipos[target].copy(),fruit_com_velocity=jp@d.qvel,body_positions=d.xpos[bids].copy(),cup_position=d.site_xpos[m.site('cup_center').id].copy(),actuator_force=d.actuator_force[mot].copy(),joint_velocity=d.qvel[[m.joint(f'support_{a}_axis').dofadr[0] for a in ['x','y','z']]].copy(),command_world=cmd.copy(),force_target=target_force.copy(),phase=phase(t))
            for key in logs:logs[key].append(vals[key])
        if k<steps:mujoco.mj_step(m,d)
        if any(w.number for w in d.warning) or not np.isfinite(d.qpos).all():raise RuntimeError('Unstable support study')
    np.savez_compressed(out/'rollout.npz',**logs,body_names=names)
    np.savez_compressed(out/'commands.npz',t=times,command_world=commands,target_force=targets)
    steady=(np.array(logs['t'])>6.4)&(np.array(logs['t'])<7.3)
    tool_fraction=float(np.mean(np.array(logs['tool_force'])[steady,2])/weight);stem_fraction=float(np.mean(np.array(logs['stem_force'])[steady,2])/weight)
    unchanged=pose_hash==hashlib.sha256(m.qpos_spring.tobytes()+m.jnt_stiffness.tobytes()+m.body_mass.tobytes()+m.body_inertia.tobytes()).hexdigest()
    result=dict(kind=name,seconds=float(d.time),wall_s=time.time()-tc,dt_s=float(m.opt.timestep),warnings=[int(w.number) for w in d.warning],initial_instrument_contacts=initial,instrument_contacted_geometries=all_touched,non_target_contacts=sorted(wrong),peak_target_contact_force_n=peakforce,max_cup_fruit_penetration_mm=maxdepth,max_other_plant_penetration_mm=otherdepth,mean_hold_support_fraction=tool_fraction,mean_hold_stem_vertical_fraction=stem_fraction,material_mass_inertia_unchanged=unchanged,stem_sensor_sign=stem_sign,weight_n=weight,scope=protocol['scope'])
    dump(out/'result.json',result);print(json.dumps(result),flush=True)


def compare():
    a=np.load(P/'support/rollout.npz');b=np.load(P/'control/rollout.npz');r=json.loads((P/'support/result.json').read_text());t=a['t'];hold=(t>6.4)&(t<7.3);end=t>12.5;delta=a['body_positions']-b['body_positions'];mass=json.loads((P/'protocol.json').read_text())['fruit_mass_kg']
    # The sensor/contacts and finite-difference COM acceleration are independent
    # routes through Newton's law. Evaluate during the smooth loaded hold.
    accel=np.gradient(a['fruit_com_velocity'],t,axis=0);residual=a['tool_force']+a['other_force']+a['stem_force']+mass*np.array([0,0,-9.81])-mass*accel
    residual_hold=float(np.linalg.norm(residual[hold],axis=1).max())
    initial_same=bool(np.array_equal(a['qpos'][0],b['qpos'][0]) and np.array_equal(a['qvel'][0],b['qvel'][0]))
    ca=np.load(P/'support/commands.npz');cb=np.load(P/'control/commands.npz');commands_same=bool(np.array_equal(ca['command_world'],cb['command_world']))
    final_displacement=float(np.linalg.norm(delta[end,0],axis=1).max()*1000)
    criteria=dict(initial_same=initial_same,commands_same=commands_same,initial_tool_clear=not r['initial_instrument_contacts'],no_non_target_tool_contact=not r['non_target_contacts'],support_fraction=.7<=r['mean_hold_support_fraction']<=.9,stem_unloaded=r['mean_hold_stem_vertical_fraction']<=.4,cup_penetration=r['max_cup_fruit_penetration_mm']<=.25,other_plant_penetration=r['max_other_plant_penetration_mm']<=.1,contact_force_budget=r['peak_target_contact_force_n']<=.45,final_no_contact=bool(np.linalg.norm(a['tool_force'][end],axis=1).max()<1e-5),recovery=final_displacement<=2,force_balance=residual_hold<=.005)
    report=dict(criteria=criteria,all_pass=all(criteria.values()),max_hold_force_balance_residual_n=residual_hold,final_fruit_displacement_from_control_mm=final_displacement,max_fruit_displacement_from_control_mm=float(np.linalg.norm(delta[:,0],axis=1).max()*1000),max_neighbor_displacement_from_control_mm=float(np.linalg.norm(delta[:,3:6],axis=2).max()*1000),mean_supported_stalk_tip_rise_mm=float(delta[hold,1,2].mean()*1000),scope='Uncalibrated contact-driven support diagnostic, not learned robot execution.')
    if (P/'support-fine/rollout.npz').exists():
        f=np.load(P/'support-fine/rollout.npz');report['fine_timestep_comparison']=dict(max_fruit_path_difference_mm=float(np.linalg.norm(a['fruit_com']-f['fruit_com'],axis=1).max()*1000),hold_vertical_support_force_mean_difference_n=float(abs(a['tool_force'][hold,2].mean()-f['tool_force'][hold,2].mean())))
    dump(P/'comparison.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','compare']);p.add_argument('--output',type=Path,default=P);p.add_argument('--control',action='store_true');p.add_argument('--fine',action='store_true');p.add_argument('--commands-from',type=Path);a=p.parse_args();P=a.output
    if a.stage=='prepare':prepare()
    elif a.stage=='run':run(a.control,a.fine,a.commands_from)
    else:compare()
