"""Generate a separate synthetic dataset and a portable tiny NumPy actor.

Only the frozen, evaluated checkpoint is used. Never train on the holdout here.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np,torch
from stable_baselines3 import PPO
from train_catcher_specialist import evaluate,dump
from astrafactory.catcher_positioning import TASK

def predict(weights,obs):
 x=np.asarray(obs,dtype=np.float32)
 for i in range(2):x=np.tanh(x@weights[f'w{i}'].T+weights[f'b{i}'])
 return np.clip(x@weights['w2'].T+weights['b2'],-1,1)

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--count',type=int,default=64);p.add_argument('--start',type=int,default=50001);a=p.parse_args();torch.set_num_threads(1)
 report=json.loads((a.run/'report.json').read_text());proposal=json.loads((a.run/'proposal.json').read_text());checkpoint=Path(report['checkpoint'])
 assert report['status']=='evaluated' and report['successes']>0,'No successful evaluated checkpoint to export'
 assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==report['checkpoint_sha256']
 seeds=list(range(a.start,a.start+a.count));assert not set(seeds)&set(proposal['dev_seeds']+proposal['holdout_seeds'])
 policy=PPO.load(checkpoint,device='cpu');out=a.run/'synthetic-demonstrations';out.mkdir(exist_ok=True)
 dump(out/'proposal.json',dict(checkpoint=str(checkpoint),sha256=report['checkpoint_sha256'],seeds=seeds,variation=1.,acceptance='Unchanged task criteria; retain failures separately. This generation split is disjoint from training/development/evaluation seeds.'))
 rows=evaluate(policy,seeds,1.,out,Path(proposal.get('task_dir',TASK)),proposal.get('completion_bonus',12.))
 accepted=[x['seed'] for x in rows if x['is_success'] and not x['invalid']];pairs=[]
 for seed in accepted:
  z=np.load(out/f'episode-{seed}.npz');pairs.append((z['observations'],z['actions']))
 if pairs:
  obs=np.concatenate([x[0] for x in pairs]);actions=np.concatenate([x[1] for x in pairs]);np.savez_compressed(out/'accepted-state-action.npz',observations=obs,actions=actions)
 else:obs=np.zeros((1,35),np.float32)
 sd=policy.policy.state_dict();weights={}
 for i,prefix in enumerate(['mlp_extractor.policy_net.0','mlp_extractor.policy_net.2','action_net']):
  weights[f'w{i}']=sd[prefix+'.weight'].cpu().numpy();weights[f'b{i}']=sd[prefix+'.bias'].cpu().numpy()
 np.savez_compressed(out/'actor.npz',**weights)
 err=float(abs(predict(weights,obs)-policy.predict(obs,deterministic=True)[0]).max());assert err<1e-5,err
 t=time.perf_counter()
 for _ in range(10000):predict(weights,obs[0])
 micros=(time.perf_counter()-t)*100
 summary=dict(checkpoint_sha256=report['checkpoint_sha256'],attempted=len(rows),accepted=len(accepted),accepted_seeds=accepted,rows=rows,state_action_pairs=sum(len(x[0]) for x in pairs),dataset='accepted-state-action.npz',actor='actor.npz',actor_parameter_count=sum(x.size for x in weights.values()),numpy_actor_max_action_error=err,numpy_actor_mean_inference_us=micros,actor_bytes=(out/'actor.npz').stat().st_size,scope='Fresh simulated state/action demonstrations from a frozen PPO checkpoint. No camera student trained, no cutting/catching skill, and no real-world transfer established.')
 dump(out/'manifest.json',summary);dump(a.run/'synthetic-demonstrations.json',dict(manifest='synthetic-demonstrations/manifest.json',**{k:v for k,v in summary.items() if k!='rows'}));print('DATASET',json.dumps({k:v for k,v in summary.items() if k not in ['rows','accepted_seeds']}),flush=True)

if __name__=='__main__':main()
