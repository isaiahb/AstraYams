"""Orbitable cel-shaded replay of two-arm states and deforming net fibers."""
import argparse,json,shutil,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np,mujoco
import render_strawberry_specimen as exporter
from astrafactory.dual_harvest import DualHarvestEnv,TASK
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();run=a.run.resolve();review=run/'review';review.mkdir(exist_ok=True);mesh=review/'mesh-export';mesh.mkdir(exist_ok=True)
 task=run/'task' if (run/'task').exists() else TASK
 root=E.parse(task/'scene.xml').getroot()
 for g in root.iter('geom'):
  if (g.get('name') or '').startswith(('finger_','cut_finger_')):g.set('rgba','0 0 0 0')
 E.ElementTree(root).write(review/'scene.xml',encoding='unicode');paths=sorted(run.glob('episode-*.npz'));assert paths
 z=np.load(paths[0]);np.savez_compressed(mesh/'rollout.npz',qpos=z['qpos'][:1],t=[0.]);exporter.P=review;exporter.export(['mesh-export'],skip_finger_collision_visuals=True);objects=json.loads((mesh/'replay.json').read_text())['objects'];cases=[]
 e=DualHarvestEnv(task_dir=task);m,d=e.model,e.data;elements=m.flex_elem.reshape(-1,2).tolist()
 for path in paths:
  z=np.load(path);meta=json.loads(path.with_suffix('.json').read_text());seed=meta['result']['seed'];e.variation=max(0.,float(meta['result'].get('variation',0.)));e.reset(seed=seed)
  dr=meta['result']['domain_randomization'];m.body_pos[e.frame]=e.pos[e.frame]+dr['offset_m'];yaw=dr['yaw_rad'];m.body_quat[e.frame]=[np.cos(yaw/2),0,0,np.sin(yaw/2)]
  frames=[]
  for i in sorted(set(range(0,len(z['qpos']),2))|{len(z['qpos'])-1}):
   d.qpos[:]=z['qpos'][i];d.eq_active[:]=z['eq_active'][i];mujoco.mj_forward(m,d)
   bodies={m.body(j).name or 'world':dict(position=d.xpos[j].round(7).tolist(),quaternion=d.xquat[j][[1,2,3,0]].round(7).tolist()) for j in range(m.nbody) if not m.body(j).name.startswith('net_node')}
   metrics=meta['trace'][max(0,i-1)].copy()
   if i==0:metrics.update(phase='Initial physical state',sim_s=0.,severed=False,is_success=False,net_contact_N=0.,cut_work_J=0.)
   frames.append(dict(time=float(z['t'][i]),bodies=bodies,net=z['flex_vertices'][i].round(7).tolist(),metrics=metrics))
  filename=path.stem+'.json';(review/filename).write_text(json.dumps(dict(objects=objects,net_edges=elements,frames=frames,result=meta['result']),separators=(',',':')));cases.append(dict(seed=seed,success=meta['result']['is_success'],replay=filename))
 (review/'manifest.json').write_text(json.dumps(dict(cases=cases),indent=2)+'\n');shutil.copy2(ROOT/'tools/templates/dual-harvest-review.html',review/'index.html');print(review/'index.html',flush=True)
if __name__=='__main__':main()
