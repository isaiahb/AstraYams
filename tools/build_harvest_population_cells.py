"""Compile the exact sampled plant physics into the real two-YAM workcell."""
from pathlib import Path
import argparse,json,subprocess,sys
import numpy as np
from astrafactory.dual_harvest import DualHarvestEnv
ROOT=Path(__file__).resolve().parents[1]

def run(population,out,seeds):
 rows=[]
 for seed in seeds:
  specimen=population/str(seed);spec=json.loads((specimen/'population.json').read_text());folder=out/str(seed);folder.mkdir(parents=True,exist_ok=True)
  if not spec['quiet']:
   rows.append(dict(seed=seed,status='rejected',reason='Plant did not reach the settling criterion'));continue
  commands=[['tools/build_catcher_positioning.py','--comfortable','--plant',str(specimen),'--out',str(folder/'catcher-task')],['tools/build_dual_harvest.py','--source',str(folder/'catcher-task'),'--out',str(folder/'task')]]
  try:
   with (folder/'build.log').open('w') as log:
    for command in commands:subprocess.run([sys.executable,*command],check=True,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
   e=DualHarvestEnv(task_dir=folder/'task');e.reset(seed=seed);start=e.data.qpos.copy();trace=[]
   for _ in range(50):
    info=e.advance(allow_cut=False);trace.append(info)
    if info['invalid']:break
   row=dict(seed=seed,split=spec['split'],status='rest-valid' if not info['invalid'] else 'rejected',fruit_count=spec['fruit_count'],leaf_count=spec['leaf_count'],plant=spec,initial_contact_audit=info,scope='Physical workcell compilation and 1 s stationary motor/contact test; not policy generalization evidence.')
   np.savez_compressed(folder/'rest.npz',initial_qpos=start,final_qpos=e.data.qpos)
   e.close()
  except Exception as ex:row=dict(seed=seed,status='rejected',reason=str(ex))
  (folder/'workcell.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row);(out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n');print(seed,row['status'],flush=True)
 return rows
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--population',type=Path,default=Path('runs/harvest-skill-suite/population'));p.add_argument('--out',type=Path,default=Path('runs/harvest-skill-suite/population-cells'));p.add_argument('--seeds',type=int,nargs='+',default=[71001,71002,71003,72001,72002,72003]);a=p.parse_args();run(a.population.resolve(),a.out.resolve(),a.seeds)
