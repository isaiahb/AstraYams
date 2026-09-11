"""Separate simulated deposition from grip stability and damage qualification."""
from pathlib import Path
import argparse,json
import mujoco as mj
import numpy as np

def summarize(run,cases):
    bench=run/'gate-bench';m=mj.MjModel.from_xml_path(str(bench/'scene.xml'));d=mj.MjData(m);rows=[];notes={}
    for name in cases:
        folder=bench/name;r=json.loads((folder/'result.json').read_text());tr=json.loads((folder/'trace.json').read_text());z=np.load(folder/'rollout.npz')
        d.qpos[:]=z['qpos'][-1];d.qvel[:]=z['qvel'][-1];mj.mj_forward(m,d)
        box=m.body('pack_clamshell').id;skin=m.geom('packing_berry_skin').id;i=m.geom_dataid[skin]
        vertices=m.mesh_vert[m.mesh_vertadr[i]:m.mesh_vertadr[i]+m.mesh_vertnum[i]]
        world=vertices@d.geom_xmat[skin].reshape(3,3).T+d.geom_xpos[skin]
        local=(world-d.xpos[box])@d.xmat[box].reshape(3,3)
        height=np.clip(local[:,2],0,.076)
        margins=np.concatenate([.054+.0075*height/.076-.0007-abs(local[:,0]),.084+.009*height/.076-.0007-abs(local[:,1]),local[:,2]-.0007,.076-local[:,2]])
        skin_in_container=bool(margins.min()>-.0005)
        net_empty=bool(np.linalg.norm(r['final']['berry_in_net_frame'])>.08)
        grip_stable=bool(r['maximum_grip_translation_error_mm']<1 and r['maximum_grip_rotation_error_deg']<2)
        deposited=skin_in_container and net_empty and r['final']['forces_N']['berry_fixture']>.05
        rows.append(dict(name=name,deposition_observed=deposited,skin_inside_container_with_0_5mm_tolerance=skin_in_container,minimum_skin_margin_mm=float(margins.min()*1000),net_empty=net_empty,grip_stable=grip_stable,gate_max_deg=max(t['gate_deg'] for t in tr),result=r))
        notes[name]=(f"Berry {'remains in the supported clamshell after release' if deposited else 'deposition is not established'}. Tool shift {r['maximum_grip_translation_error_mm']:.2f} mm / {r['maximum_grip_rotation_error_deg']:.2f}°; {'passes' if grip_stable else 'fails'} the 1 mm / 2° grip criterion. Contact forces are simulation measurements, not validated damage limits.")
    fit=json.loads((bench/'fixture-fit.json').read_text())
    summary=dict(scope=__doc__,cases=rows,fixture_fit=fit,release_ready=False,learned_policy=False,damage_validated=False,
        preserved='V7 stacked direct SO-101 mounts and V8 single supported clamshell concept. The carriage bears the container weight.',
        further_work=['Replace friction-only tool torque retention with a compact positive locating interface or an actuated dock.',
          'Reduce release height and sideways rolling while preserving full opening clearance; evaluate a peel/rolling net floor or supported handoff.',
          'Measure and calibrate textile, fruit and container compliance; compare impact force/pressure and real bruise outcomes.',
          'Resolve the wide levers and front roller support before checking harvest access or carrier exchange.',
          'Complete shaft axial retention, gate return spring/stop and production fastener specification before a hardware build.'])
    (bench/'commission-summary.json').write_text(json.dumps(summary,indent=2)+'\n');(bench/'review-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
    print(json.dumps([dict(name=x['name'],deposition=x['deposition_observed'],grip=x['grip_stable'],skin_margin_mm=x['minimum_skin_margin_mm']) for x in rows],indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('cases',nargs='+');a=p.parse_args();summarize(a.run.resolve(),a.cases)
