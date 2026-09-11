"""Record separate fit/hold/release evidence, without treating stability as success."""
from pathlib import Path
import json
import numpy as np
import mujoco as mj
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/tower-lift-v9';B=R/'gate-bench'
m=mj.MjModel.from_xml_path(str(B/'scene.xml'));d=mj.MjData(m);d.qpos[:]=np.load(B/'initial.npz')['qpos'];mj.mj_forward(m,d)
box=m.body('pack_clamshell').id;center=d.xpos[box].copy();cases=[]
for name in ['hold-gate-v2','hold-refined-dt','corrected-release-final','ground-contact-check']:
 p=B/name
 if not (p/'result.json').exists():continue
 r=json.loads((p/'result.json').read_text());tr=json.loads((p/'trace.json').read_text());pos=np.array(r['final']['berry_com'])-center
 held=r['maximum_grip_translation_error_mm']<1 and r['maximum_grip_rotation_error_deg']<2
 contained=bool(abs(pos[0])<.052 and abs(pos[1])<.082 and .002<pos[2]<.068)
 empty=np.linalg.norm(r['final']['berry_in_net_frame'])>.08
 cases.append(dict(name=name,grip_stable=bool(held),berry_center_inside_container=contained,net_empty=bool(empty),release_demonstrated=bool(held and contained and empty),gate_max_deg=max(t['gate_deg'] for t in tr),result=r))
minx=1e9;limiting=''
for g in range(m.ngeom):
 name=m.body(m.geom_bodyid[g]).name or ''
 if not name.startswith('pack_') or m.geom_rgba[g,3]<=0 or m.geom_type[g]!=7:continue
 i=m.geom_dataid[g];v=m.mesh_vert[m.mesh_vertadr[i]:m.mesh_vertadr[i]+m.mesh_vertnum[i]];w=v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g]
 if w[:,0].min()<minx:minx=w[:,0].min();limiting=name
summary=dict(scope=__doc__,container_center_m=center.tolist(),frame_inner_plane_x_m=-.290,nominal_left_frame_clearance_mm=float((minx+.290)*1000),clearance_limiting_part=limiting,cases=cases,release_ready=False,force_evidence='Contact-force peaks are sampled at 50 Hz; not injury thresholds or guaranteed peak loads.',further_work=['Mechanically resist net twisting at its interface or support it in a docking fixture.','Open the floor fully above the container without bottom/wall contact; evaluate side actuation.','Plan and check cutter retreat and lower-arm transport together.','Specify spring, travel stop, shaft retention, roller axle and actual jaw interface hardware.','Measure and calibrate forces, friction, textile stiffness and fruit damage response.'])
(B/'commission-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='cases'},indent=2))
