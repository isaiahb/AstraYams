"""CAD coverage and contact-response regressions; no harvest success claim."""
import argparse,json
from pathlib import Path
import numpy as np,mujoco
from scipy.spatial import ConvexHull
from astrafactory.dual_harvest import DualHarvestEnv,TASK

def vertices(m,gi):
 k=m.geom_dataid[gi];v=m.mesh_vert[m.mesh_vertadr[k]:m.mesh_vertadr[k]+m.mesh_vertnum[k]];R=np.zeros(9);mujoco.mju_quat2Mat(R,m.geom_quat[gi]);return v@R.reshape(3,3).T+m.geom_pos[gi]

def coverage(path):
 m=mujoco.MjModel.from_xml_path(str(path));report={}
 for vi in range(m.ngeom):
  name=m.geom(vi).name
  if not (name.startswith('cut_') and name.endswith('_visual') and any(p in name for p in ['carrier','clamp_cover','liner'])):continue
  prefix=name[:-7]+'_contact_';v=vertices(m,vi);k=m.geom_dataid[vi];faces=m.mesh_face[m.mesh_faceadr[k]:m.mesh_faceadr[k]+m.mesh_facenum[k]]
  points=np.r_[v,v[faces].mean(axis=1)];dist=np.full(len(points),np.inf);count=0
  for gi in range(m.ngeom):
   if not m.geom(gi).name.startswith(prefix):continue
   planes=ConvexHull(vertices(m,gi)).equations
   # Elementwise plane evaluation avoids large multithreaded BLAS scratch.
   local=np.full(len(points),-np.inf)
   for a,b,c,d in planes:local=np.maximum(local,points[:,0]*a+points[:,1]*b+points[:,2]*c+d)
   dist=np.minimum(dist,local);count+=1
  report[name]=dict(hulls=count,samples=len(points),uncovered_samples=int(sum(dist>2e-6)),max_plane_violation_m=float(max(dist)),tolerance_m=2e-6)
 return report

def response(disable=False):
 source=Path('runs/dual-harvest-commission-v10');z=np.load(source/'episode-61001.npz');meta=json.loads((source/'episode-61001.json').read_text());i=187
 e=DualHarvestEnv();e.reset(seed=61001);m,d=e.model,e.data;d.qpos[:]=z['qpos'][i];d.qvel[:]=z['qvel'][i];d.eq_active[:]=z['eq_active'][i];d.time=.3+float(z['t'][i]);e.target=z['catch_targets'][i].copy();e.cut_target=z['cut_targets'][i].copy();e.jaw_target=-.0028;e.work=meta['trace'][i-1]['cut_work_J'];e.steps=i;e.severed=True;e.cut_time=meta['result']['cut_event']['time_s'];d.eq_active[e.eq]=0
 a,b=sorted([m.body('secondary_b_5').id,e.branch]);m.exclude_signature[m.exclude_signature==(a<<16)+b]=0;m.exclude_signature[:]=np.sort(m.exclude_signature)
 if disable:
  for gi in range(m.ngeom):
   if m.geom_contype[gi]&8:m.geom_conaffinity[gi]&=~1
   if m.geom_contype[gi]&1:m.geom_conaffinity[gi]&=~8
 mujoco.mj_forward(m,d);e.jaw_previous=sum(d.qpos[m.joint(n).qposadr[0]] for n in ['cut_joint7','cut_joint8']);body=m.body('fruit_secondary_a').id;p0=d.xpos[body].copy();q0=d.xquat[body].copy();frames=[]
 for _ in range(10):
  info=e.advance();frames.append(dict(t=float(d.time),position=d.xpos[body].tolist(),quaternion=d.xquat[body].tolist(),peak_contact=info['peak_neighbor_contact']))
 return dict(cutter_plant_contact='disabled only for diagnostic counterfactual' if disable else 'enabled',initial_position=p0.tolist(),final_position=d.xpos[body].tolist(),displacement_m=float(np.linalg.norm(d.xpos[body]-p0)),rotation_rad=float(2*np.arccos(np.clip(abs(np.dot(d.xquat[body],q0)),0,1))),peak_contact=e.neighbor_peak,warnings=sum(w.number for w in d.warning),frames=frames)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('runs/dual-contact-audit'));a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 report=dict(scope='Geometry coverage and controlled same-state contact ablation; not a harvest or calibrated tissue-force test.',old=coverage(Path('runs/dual-harvest-commission-v6/task/scene.xml')),corrected=coverage(TASK/'scene.xml'),response_enabled=response(),response_disabled=response(True))
 report['response_difference_m']=float(np.linalg.norm(np.array(report['response_enabled']['final_position'])-report['response_disabled']['final_position']))
 assert all(v['uncovered_samples']==0 for v in report['corrected'].values())
 assert report['response_difference_m']>.0001
 (a.out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(response_difference_m=report['response_difference_m'],enabled_peak=report['response_enabled']['peak_contact'],disabled_peak=report['response_disabled']['peak_contact']),indent=2),flush=True)
