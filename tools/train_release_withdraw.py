"""Transfer a six-joint PPO into a seven-action release/retreat specialist."""
from pathlib import Path
import argparse,json,time,shutil,hashlib
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from astrafactory.release_withdraw_skill import ReleaseWithdrawSkill
from astrafactory.training_io import save_policy
from train_harvest_joint_skill import Progress

def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def evaluate(policy,config,seeds,out=None):
 e=ReleaseWithdrawSkill(**config);rows=[]
 if out:shutil.copytree(Path(config['source'])/'task',out/'task',dirs_exist_ok=True)
 for seed in seeds:
  o,_=e.reset(seed=seed);w=e.e;qs=[w.data.qpos.copy()];vs=[w.data.qvel.copy()];eq=[w.data.eq_active.copy()];net=[w.data.flexvert_xpos.copy()];ct=[w.target.copy()];ut=[w.cut_target.copy()];jt=[w.jaw_target];trace=[];acts=[]
  for _ in range(250):
   a=np.zeros(7) if policy is None else policy.predict(o,deterministic=True)[0];o,r,d,t,i=e.step(a);qs.append(w.data.qpos.copy());vs.append(w.data.qvel.copy());eq.append(w.data.eq_active.copy());net.append(w.data.flexvert_xpos.copy());ct.append(w.target.copy());ut.append(w.cut_target.copy());jt.append(w.jaw_target);trace.append(i);acts.append(a)
   if d or t:break
  row=dict(i,seed=seed,controller='Seven-action PPO coordinates six cutter joints and stock jaw release after an actual learned cut. Catcher holds finite motor targets. Full dynamic net in holdout; no runtime IK.');rows.append(row);print('EVAL RELEASE RETREAT',seed,i['is_success'],i['invalid'],round(i['goal_error_m']*1000,2),i['net_hold_steps'],round(i['jaw_position_m']*1000,2),flush=True)
  if out:
   dump(out/f'episode-{seed}.json',dict(result=row,trace=trace));np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,qvel=vs,eq_active=eq,flex_vertices=net,catch_targets=ct,cut_targets=ut,jaw_targets=jt,actions=acts,t=np.arange(len(qs))*.02)
 e.close();return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--steps',type=int,default=2048);p.add_argument('--rounds',type=int,default=3);p.add_argument('--envs',type=int,default=2);p.add_argument('--support-policy');p.add_argument('--resume');a=p.parse_args();torch.set_num_threads(1)
 config=dict(source='runs/harvest-skill-suite/cut-release-source-v1',curriculum='runs/harvest-skill-suite/cut-release-curriculum-v2',support_policy=a.support_policy);env=SubprocVecEnv([lambda:ReleaseWithdrawSkill(**config) for _ in range(a.envs)],start_method='spawn')
 old=PPO.load('runs/harvest-skill-suite/withdraw-v3/round-3.zip',device='cpu');policy=PPO('MlpPolicy',env,n_steps=128,batch_size=128,n_epochs=8,learning_rate=.0003,gamma=.985,ent_coef=.002,policy_kwargs=dict(net_arch=old.policy_kwargs['net_arch'],log_std_init=-2.),device='cpu',seed=157)
 src=old.policy.state_dict();dst=policy.policy.state_dict()
 for k,v in dst.items():
  if k not in src:continue
  if v.shape==src[k].shape:v.copy_(src[k])
  elif v.ndim==2 and v.shape[0]==src[k].shape[0] and v.shape[1]==71 and src[k].shape[1]==67:v.zero_();v[:,:67].copy_(src[k])
  elif k=='action_net.weight':v.zero_();v[:6].copy_(src[k])
  elif k=='action_net.bias':v.zero_();v[:6].copy_(src[k])
  elif k=='log_std':v.fill_(-2.)
 policy.policy.load_state_dict(dst)
 if a.resume:policy=PPO.load(a.resume,env=env,device='cpu')
 save_policy(policy,a.out/'initial');rounds=[];best=None;bestscore=(-1,-1e9)
 dump(a.out/'proposal.json',dict(algorithm='PPO fine-tuning',initialization='Six-joint withdrawal PPO copied; new jaw head starts at zero. Four new observations start with zero input weights.',observations=71,actions=7,reason='One-jaw release in place hits neighboring calyx; retreat and opening must coordinate.',source=config))
 for j in range(a.rounds):
  start=time.time();policy.learn(a.steps,reset_num_timesteps=False,callback=Progress(a.out/f'round-{j+1}-training'));cp=save_policy(policy,a.out/f'round-{j+1}');dev=evaluate(policy,config,[78001,78002]);score=(sum(x['is_success'] for x in dev),sum((not x['invalid'])-x['goal_error_m']*10 for x in dev));row=dict(round=j+1,seconds=time.time()-start,development=dev);rounds.append(row);dump(a.out/f'round-{j+1}.json',row)
  if score>bestscore:bestscore=score;best=cp
 env.close();policy=PPO.load(best,device='cpu');full=dict(config,curriculum=None);hold=evaluate(policy,full,[79001,79002,79003,79004],a.out/'holdout');baseline=evaluate(None,full,[79001]);dump(a.out/'report.json',dict(checkpoint=str(best),successes=sum(x['is_success'] for x in hold),episodes=len(hold),rows=hold,baseline=baseline,rounds=rounds,scope='Local release/retreat after an actual learned cut; not a whole harvest.'))
if __name__=='__main__':main()
