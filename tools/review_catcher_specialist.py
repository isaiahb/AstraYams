"""Cel-shaded presentation of recorded PPO states, including failed episodes."""
import argparse,json,shutil
from pathlib import Path
import numpy as np,mujoco
from astrafactory.catcher_positioning import CatcherPositioningEnv,TASK
import render_strawberry_specimen as exporter

ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=Path('runs/catcher-specialist-v1'));a=p.parse_args();run=a.run.resolve();review=run/'review';review.mkdir(exist_ok=True)
 proposal=json.loads((run/'proposal.json').read_text());task_dir=Path(proposal.get('task_dir',TASK));shutil.copy2(task_dir/'scene.xml',review/'scene.xml');shutil.copy2(ROOT/'tools/templates/catcher-specialist-review.html',review/'index.html');mesh=review/'mesh-export';mesh.mkdir(exist_ok=True)
 z=np.load(run/'baseline/episode-41001.npz');np.savez_compressed(mesh/'rollout.npz',qpos=z['qpos'][:1],t=[0.])
 exporter.P=review;exporter.export(['mesh-export'],skip_finger_collision_visuals=True);objects=json.loads((mesh/'replay.json').read_text())['objects'];cases=[]
 sources=[('baseline',41001),('baseline',41002),('baseline',41003)]
 if (run/'development/index.json').exists():
  sources += [('development',x['seed']) for x in json.loads((run/'development/index.json').read_text())['rows']]
 if (run/'report.json').exists():
  rows=json.loads((run/'report.json').read_text())['rows'];selected=rows[:3];failed=next((x for x in rows if not x['is_success']),None)
  if failed and failed not in selected:selected.append(failed)
  sources += [('holdout',x['seed']) for x in selected]
 for split,seed in sources:
  e=CatcherPositioningEnv(1.,task_dir);e.reset(seed=seed);m,d=e.model,e.data;z=np.load(run/split/f'episode-{seed}.npz');trace=json.loads((run/split/f'episode-{seed}.json').read_text());frames=[]
  for i in sorted(set(range(0,len(z['qpos']),2))|{len(z['qpos'])-1}):
   d.qpos[:]=z['qpos'][i];mujoco.mj_forward(m,d);bodies={m.body(j).name or 'world':dict(position=d.xpos[j].round(7).tolist(),quaternion=d.xquat[j][[1,2,3,0]].round(7).tolist()) for j in range(m.nbody)}
   metrics=trace['trace'][max(0,i-1)].copy();goal,rim,normal=e.geometry()
   if i==0:metrics.update(is_success=False,hold_steps=0,sim_s=0.,distance_m=float(np.linalg.norm(goal-rim)),normal_z=float(normal[2]),**e.grip)
   frames.append(dict(time=float(z['t'][i]),bodies=bodies,metrics=metrics,goal=goal.tolist(),rim=rim.tolist()))
  name=f'{split}-{seed}.json';(review/name).write_text(json.dumps(dict(objects=objects,frames=frames,scope='Actual recorded policy trajectory; no interpolated success or kinematic motion script.'),separators=(',',':')))
  cases.append(dict(split=split,seed=seed,success=trace['result']['is_success'],replay=name));e.close()
 (review/'manifest.json').write_text(json.dumps(dict(cases=cases),indent=2)+'\n')
 print(review/'index.html',flush=True)

if __name__=='__main__':main()
