"""Fine-tune support PPO on three plant topologies, evaluate held-out plants."""
from pathlib import Path
import argparse,json,time,shutil
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from astrafactory.harvest_population import PopulationSupportEnv
from astrafactory.training_io import save_policy

def evaluate(policy,root,split,out=None):
 rows=[];manifest=json.loads((Path(root)/'manifest.json').read_text())
 for model in [r for r in manifest if r['status']=='rest-valid' and r['split']==split]:
  env=PopulationSupportEnv(root,split,seeds=[model['seed']])
  for repeat in range(2):
   seed=81000+model['seed']+repeat;o,_=env.reset(seed=seed);e=env.e;qs=[e.data.qpos.copy()];vs=[e.data.qvel.copy()];eq=[e.data.eq_active.copy()];net=[e.data.flexvert_xpos.copy()];trace=[];actions=[]
   for _ in range(200):
    action=policy.predict(o,deterministic=True)[0];o,r,done,trunc,info=env.step(action);qs.append(e.data.qpos.copy());vs.append(e.data.qvel.copy());eq.append(e.data.eq_active.copy());net.append(e.data.flexvert_xpos.copy());trace.append(info);actions.append(action)
    if done or trunc:break
   row=dict(seed=seed,controller='Six-joint support PPO on a physically different plant. Full dynamics, no runtime IK.',**info);rows.append(row);print('EVAL SUPPORT',model['seed'],repeat,info['is_success'],info['invalid'],round(info['distance_m']*1000,2),flush=True)
   if out:
    dest=out/str(model['seed']);dest.mkdir(parents=True,exist_ok=True)
    if not (dest/'task').exists():shutil.copytree(Path(root)/str(model['seed'])/'task',dest/'task')
    np.savez_compressed(dest/f'episode-{seed}.npz',qpos=qs,qvel=vs,eq_active=eq,flex_vertices=net,actions=actions,t=np.arange(len(qs))*.02)
    (dest/f'episode-{seed}.json').write_text(json.dumps(dict(result=row,trace=trace),indent=2)+'\n')
  env.close()
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--population',default='runs/harvest-skill-suite/population-cells');p.add_argument('--resume',default='runs/catcher-specialist-v3/round-3.zip');p.add_argument('--out',type=Path,required=True);p.add_argument('--steps',type=int,default=8192);p.add_argument('--rounds',type=int,default=3);p.add_argument('--envs',type=int,default=2);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);torch.set_num_threads(1)
 env=SubprocVecEnv([lambda:PopulationSupportEnv(a.population) for _ in range(a.envs)],start_method='spawn');policy=PPO.load(a.resume,env=env,device='cpu');policy.learning_rate=.0003;policy.lr_schedule=lambda _: .0003;policy.n_steps=256
 from stable_baselines3.common.buffers import RolloutBuffer
 policy.rollout_buffer=RolloutBuffer(256,env.observation_space,env.action_space,device='cpu',gae_lambda=policy.gae_lambda,gamma=policy.gamma,n_envs=a.envs)
 baseline=evaluate(policy,a.population,'train');(a.out/'baseline-development.json').write_text(json.dumps(baseline,indent=2))
 rounds=[]
 for j in range(a.rounds):
  start=time.time();policy.learn(a.steps,reset_num_timesteps=False);cp=save_policy(policy,a.out/f'round-{j+1}');dev=evaluate(policy,a.population,'train');row=dict(round=j+1,seconds=time.time()-start,steps=policy.num_timesteps,development=dev);rounds.append(row);(a.out/f'round-{j+1}.json').write_text(json.dumps(row,indent=2));print('ROUND SUPPORT',j+1,sum(x['is_success'] for x in dev),flush=True)
 env.close();holdout=evaluate(policy,a.population,'holdout',a.out/'holdout');report=dict(scope='Support positioning only. Actual held-out plant topologies, not a full harvest claim.',successes=sum(r['is_success'] for r in holdout),episodes=len(holdout),checkpoint=str(cp),rounds=rounds,holdout=holdout);(a.out/'report.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
