"""Repeat recorded actions at refined physics steps; do not tune task thresholds."""
import argparse,json
from pathlib import Path
import mujoco,numpy as np
from astrafactory.catcher_positioning import CatcherPositioningEnv,TASK

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--split',default='baseline');p.add_argument('--seeds',type=int,nargs='+',default=[41001,41002]);a=p.parse_args()
 proposal=json.loads((a.run/'proposal.json').read_text());task=Path(proposal.get('task_dir',TASK));rows=[]
 for seed in a.seeds:
  actions=np.load(a.run/a.split/f'episode-{seed}.npz')['actions'];reference=None
  for dt in [.0005,.00025,.000125]:
   e=CatcherPositioningEnv(1.,task);e.model.opt.timestep=dt;e.skip=round(.02/dt);e.reset(seed=seed)
   fruit=[e.model.body(i).id for i in range(e.model.nbody) if (e.model.body(i).name or '').startswith('fruit_')]
   positions=[];joint=[];rim=[];max_torque=0.;peak_jaw=0.
   for action in actions:
    _,_,done,trunc,info=e.step(action);positions.append(e.data.xipos[fruit].copy());joint.append(e.data.qpos[e.qids].copy());rim.append(e.geometry()[1].copy());max_torque=max(max_torque,max(abs(e.data.ctrl[e.aids])));peak_jaw=max(peak_jaw,info['left_jaw_N'],info['right_jaw_N'])
    if done or trunc:break
   state=dict(fruit=np.array(positions),joint=np.array(joint),rim=np.array(rim));row=dict(seed=seed,dt=dt,result=info,max_commanded_torque_Nm=float(max_torque),peak_sampled_jaw_N=float(peak_jaw))
   if reference is None:reference=state
   n=min(len(state['joint']),len(reference['joint']))
   row['compared_steps']=n;row['max_fruit_position_difference_m']=float(np.linalg.norm(state['fruit'][:n]-reference['fruit'][:n],axis=-1).max());row['max_joint_difference_rad']=float(abs(state['joint'][:n]-reference['joint'][:n]).max());row['max_rim_difference_m']=float(np.linalg.norm(state['rim'][:n]-reference['rim'][:n],axis=-1).max())
   rows.append(row);print(seed,dt,info['is_success'],round(row['max_rim_difference_m']*1000,3),'mm rim difference',flush=True)
 out=a.run/f'timestep-audit-{a.split}.json';out.write_text(json.dumps(dict(method='Same recorded 50 Hz actions, fresh reset at each timestep, including grip settling. Maximum pointwise differences at matching samples. This tests numerical sensitivity, not real-world accuracy.',rows=rows),indent=2)+'\n')
 print(out,flush=True)
if __name__=='__main__':main()
