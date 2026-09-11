"""Finite-torque scripted commissioning, with no runtime position overwrites."""
from pathlib import Path
import argparse
import json
import time
import hashlib
import mujoco as mj
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BENCH=ROOT/'runs/tower-lift-v9/gate-bench'


def run(seconds=1.5,name='settle',plan=None,dt=.00025,initial_path=None,grip_torque=.35,grip_patch_mm=0):
    out=BENCH/name;out.mkdir(exist_ok=True,parents=True)
    m=mj.MjModel.from_xml_path(str(BENCH/'scene.xml'));m.opt.timestep=dt
    m.actuator_forcerange[m.actuator('right_gripper').id]=[-grip_torque,grip_torque]
    if grip_patch_mm:
        for g in range(m.ngeom):
            nameg=m.geom(g).name or ''
            if 'robot_geom' in nameg and '_piece_' in nameg:
                m.geom_condim[g]=6;m.geom_friction[g,1]=grip_patch_mm*.001
    d=mj.MjData(m);initial=np.load(initial_path or BENCH/'initial.npz')
    d.qpos[:]=initial['qpos'];d.ctrl[:]=initial['ctrl'];mj.mj_forward(m,d)
    net=m.body('right_packing_net').id;wrist=m.body('right_gripper').id;berry=m.body('packing_berry').id
    gate=m.joint('right_gate_hinge').qposadr[0]
    rel0=d.xmat[wrist].reshape(3,3).T@(d.xpos[net]-d.xpos[wrist])
    rot0=d.xmat[wrist].reshape(3,3).T@d.xmat[net].reshape(3,3)
    base=d.ctrl.copy();trace=[];qs=[];vs=[];cs=[];flex=[];times=[];maxima={};start=time.monotonic()
    jointnames=['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll']
    if plan is not None:plan=json.loads(Path(plan).read_text())
    (out/'inputs.json').write_text(json.dumps(dict(scene_sha256=hashlib.sha256((BENCH/'scene.xml').read_bytes()).hexdigest(),initial_qpos=d.qpos.tolist(),initial_ctrl=d.ctrl.tolist(),plan=plan,dt=dt,grip_torque_cap_Nm=grip_torque,grip_patch_torsion_length_mm=grip_patch_mm),indent=2)+'\n')
    def record():
        rel=d.xmat[wrist].reshape(3,3).T@(d.xpos[net]-d.xpos[wrist])
        rot=d.xmat[wrist].reshape(3,3).T@d.xmat[net].reshape(3,3)
        forces=dict(grip=0.,cam=0.,berry=0.,berry_fixture=0.,robot_fixture=0.,net_fixture=0.,interarm=0.)
        minimum=0.
        for i,c in enumerate(d.contact):
            names=[(m.geom(g).name or '') if g>=0 else 'textile' for g in [c.geom1,c.geom2]]
            f=np.zeros(6);mj.mj_contactForce(m,d,i,f);force=float(np.linalg.norm(f[:3]));joined=' '.join(names)
            if 'robot_geom' in joined and 'pack_net_frame' in joined:forces['grip']+=force
            if any(n.startswith('left_') for n in names) and any(n.startswith('right_') for n in names):forces['interarm']+=force
            if any(s in joined for s in ['gate_ring','pack_net_frame']) and any(s in joined for s in ['container_','carrier_','pack_liner']):forces['net_fixture']+=force
            if 'gate_trigger' in joined and 'roller' in joined:forces['cam']+=force
            if 'packing_berry_contact' in joined:
                forces['berry']+=force
                if any(s in joined for s in ['container_','pack_deck','pack_liner','pack_clamshell']):forces['berry_fixture']+=force
            if 'robot_geom' in joined and any(s in joined for s in ['container_','pack_gate','pack_mount','pack_deck']):forces['robot_fixture']+=force
            minimum=min(minimum,float(c.dist))
        local=d.xmat[net].reshape(3,3).T@(d.xipos[berry]-d.xpos[net])
        r=dict(time_s=float(d.time),grip_translation_error_mm=float(np.linalg.norm(rel-rel0)*1000),
               grip_rotation_error_deg=float(np.rad2deg(np.arccos(np.clip((np.trace(rot0.T@rot)-1)/2,-1,1)))),
               gate_deg=float(np.rad2deg(d.qpos[gate])),net_center=d.xpos[net].tolist(),
               berry_com=d.xipos[berry].tolist(),berry_in_net_frame=local.tolist(),
               forces_N=forces,minimum_contact_distance_m=minimum,
               max_joint_speed_rad_s=float(np.max(np.abs(d.qvel[[m.jnt_dofadr[m.actuator_trnid[i,0]] for i in range(m.nu)]]))),warnings=int(d.warning.number.sum()))
        trace.append(r);qs.append(d.qpos.copy());vs.append(d.qvel.copy());cs.append(d.ctrl.copy());flex.append(d.flexvert_xpos.copy());times.append(d.time)
        for k,v in forces.items():maxima[k]=max(maxima.get(k,0.),v)
    record()
    stride=max(1,round(.02/dt))
    for step in range(round(seconds/dt)):
        if plan is not None:
            for side in ['left','right']:
                for j,namej in enumerate(jointnames):
                    target=np.interp(d.time,[p['time_s'] for p in plan['waypoints']],[p[side][j] for p in plan['waypoints']])
                    d.ctrl[m.actuator(side+'_'+namej).id]=target
        mj.mj_step(m,d)
        if step%stride==stride-1:record()
        if step%(stride*25)==0 and step:print(name,round(d.time,2),'grip mm',round(trace[-1]['grip_translation_error_mm'],2),'gate',round(trace[-1]['gate_deg'],1),'berry z',round(d.xipos[berry][2],3),flush=True)
        if d.warning.number.sum():break
    report=dict(scope=__doc__,seconds=seconds,wall_s=time.monotonic()-start,dt=dt,grip_torque_cap_Nm=grip_torque,grip_patch_torsion_length_mm=grip_patch_mm,
        plan=str(plan is not None),initial_path=str(initial_path or BENCH/'initial.npz'),peak_forces_N=maxima,
        force_sampling_hz=1/(stride*dt),
        maximum_grip_translation_error_mm=max(x['grip_translation_error_mm'] for x in trace),
        maximum_grip_rotation_error_deg=max(x['grip_rotation_error_deg'] for x in trace),
        final=trace[-1],warnings=int(d.warning.number.sum()),
        qualification='Commissioning evidence only; no learned policy, hardware calibration or bruise-safe claim.')
    np.savez_compressed(out/'rollout.npz',qpos=qs,qvel=vs,ctrl=cs,flex_vertices=flex,t=times)
    (out/'trace.json').write_text(json.dumps(trace,separators=(',',':')))
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=1.5);p.add_argument('--name',default='settle');p.add_argument('--plan');p.add_argument('--grip-patch-mm',type=float,default=0);p.add_argument('--grip-torque',type=float,default=.35);p.add_argument('--initial');p.add_argument('--dt',type=float,default=.00025);a=p.parse_args()
    run(a.seconds,a.name,a.plan,a.dt,a.initial,a.grip_torque,a.grip_patch_mm)
