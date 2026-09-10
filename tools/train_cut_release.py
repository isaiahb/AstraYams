"""PPO jaw release from an actual upstream learned physical cut."""
from pathlib import Path
import argparse,json,time,shutil,hashlib
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from astrafactory.cut_release_skill import CutReleaseSkill
from astrafactory.training_io import save_policy
from train_harvest_joint_skill import Progress

def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def evaluate(policy,config,seeds,out=None):
 e=CutReleaseSkill(**config);rows=[]
 if out:shutil.copytree(Path(config['source'])/'task',out/'task',dirs_exist_ok=True)
 for seed in seeds:
  o,_=e.reset(seed=seed);w=e.e;qs=[w.data.qpos.copy()];vs=[w.data.qvel.copy()];eq=[w.data.eq_active.copy()];net=[w.data.flexvert_xpos.copy()];ct=[w.target.copy()];ut=[w.cut_target.copy()];jt=[w.jaw_target];trace=[];acts=[]
  for _ in range(180):
   a=np.zeros(1) if policy is None else policy.predict(o,deterministic=True)[0];o,r,d,t,i=e.step(a);qs.append(w.data.qpos.copy());vs.append(w.data.qvel.copy());eq.append(w.data.eq_active.copy());net.append(w.data.flexvert_xpos.copy());ct.append(w.target.copy());ut.append(w.cut_target.copy());jt.append(w.jaw_target);trace.append(i);acts.append(a)
   if d or t:break
  row=dict(i,seed=seed,controller='One-jaw PPO release after an actual learned cut. Both six-joint arm targets hold under finite motor forces; flexible net catches the fruit. No runtime IK.');rows.append(row);print('EVAL RELEASE',seed,i['is_success'],i['invalid'],i['jaw_position_m'],i['net_contact_N'],flush=True)
  if out:
   dump(out/f'episode-{seed}.json',dict(result=row,trace=trace));np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,qvel=vs,eq_active=eq,flex_vertices=net,catch_targets=ct,cut_targets=ut,jaw_targets=jt,actions=acts,t=np.arange(len(qs))*.02)
 e.close();return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--steps',type=int,default=1024);p.add_argument('--rounds',type=int,default=3);p.add_argument('--envs',type=int,default=2);a=p.parse_args();torch.set_num_threads(1)
 config=dict(source='runs/harvest-skill-suite/cut-release-source-v1',curriculum='runs/harvest-skill-suite/cut-release-curriculum-v2');env=SubprocVecEnv([lambda:CutReleaseSkill(**config) for _ in range(a.envs)],start_method='spawn');policy=PPO('MlpPolicy',env,n_steps=128,batch_size=128,n_epochs=8,learning_rate=.001,gamma=.985,ent_coef=.003,policy_kwargs=dict(net_arch=dict(pi=[16,16],vf=[16,16]),log_std_init=-.3),device='cpu',seed=153);save_policy(policy,a.out/'initial');rounds=[];best=None;bestscore=-1
 dump(a.out/'proposal.json',dict(algorithm='PPO from scratch',observations=15,actions='One stock cutter jaw target increment',reward='Opening progress, time cost, success only after jaws open and the other arm physically retains fruit for 0.5 s',scope='Local release skill; not a whole harvest policy',source=config))
 for j in range(a.rounds):
  start=time.time();policy.learn(a.steps,reset_num_timesteps=False,callback=Progress(a.out/f'round-{j+1}-training'));cp=save_policy(policy,a.out/f'round-{j+1}');dev=evaluate(policy,config,[76001,76002]);score=sum(x['is_success'] for x in dev);row=dict(round=j+1,seconds=time.time()-start,development=dev);rounds.append(row);dump(a.out/f'round-{j+1}.json',row)
  if score>bestscore:bestscore=score;best=cp
 env.close();policy=PPO.load(best,device='cpu');full=dict(config,curriculum=None);hold=evaluate(policy,full,[77001,77002,77003,77004],a.out/'holdout');baseline=evaluate(None,full,[77001]);dump(a.out/'report.json',dict(checkpoint=str(best),checkpoint_sha256=hashlib.sha256(Path(best).read_bytes()).hexdigest(),successes=sum(x['is_success'] for x in hold),episodes=len(hold),rows=hold,baseline=baseline,rounds=rounds,scope='One-jaw PPO on the actual upstream cut state, full net and plant. No full-chain claim.'))
if __name__=='__main__':main()
