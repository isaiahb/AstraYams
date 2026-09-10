"""PPO cutter specialist, explicit reset curriculum and untouched local holdout."""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from astrafactory.cutter_skill import CutterSkillEnv
from astrafactory.training_io import save_policy

def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def evaluate(policy,source,seeds,out=None,difficulty=1.,curriculum=None,joint_scale=1.,entry_run=None):
 env=CutterSkillEnv(source,difficulty,1.,curriculum,joint_scale,entry_run);rows=[]
 for seed in seeds:
  o,_=env.reset(seed=seed);e=env.e;qs=[e.data.qpos.copy()];vs=[e.data.qvel.copy()];eq=[e.data.eq_active.copy()];net=[e.data.flexvert_xpos.copy()];tr=[];obs=[];acts=[];ctrl=[]
  for _ in range(250):
   a=policy.predict(o,deterministic=True)[0] if policy else np.zeros(7);obs.append(o);acts.append(a);o,r,done,trunc,info=env.step(a);qs.append(e.data.qpos.copy());vs.append(e.data.qvel.copy());eq.append(e.data.eq_active.copy());net.append(e.data.flexvert_xpos.copy());ctrl.append(e.data.ctrl.copy());tr.append(info)
   if done or trunc:break
  row=dict(seed=seed,controller='Learned seven-action cutter PPO; fixed catcher joint targets under finite-torque motors. Reset from a recorded catcher-ready state. No IK or scripted cutter movement in this episode.',**info);rows.append(row)
  if out:
   out.mkdir(exist_ok=True,parents=True);np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,qvel=vs,eq_active=eq,flex_vertices=net,observations=obs,actions=acts,controls=ctrl,t=np.arange(len(qs))*.02);dump(out/f'episode-{seed}.json',dict(result=row,trace=tr))
  print('EVAL',seed,row['is_success'],row['invalid'],row['severed'],round(row['cutter_goal_error_m']*1000,2),flush=True)
 env.close();return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--entry-run');p.add_argument('--holdout-start',type=int,default=63001);p.add_argument('--source',default='runs/dual-harvest-commission-v13');p.add_argument('--out',type=Path,default=Path('runs/cutter-specialist-v1'));p.add_argument('--curriculum');p.add_argument('--resume');p.add_argument('--start-difficulty',type=float,default=0.);p.add_argument('--steps',type=int,default=8192);p.add_argument('--envs',type=int,default=4);p.add_argument('--rounds',type=int,default=3);p.add_argument('--fixed-difficulty',type=float);p.add_argument('--joint-scale',type=float,default=1.);a=p.parse_args();torch.set_num_threads(1)
 proposal=dict(algorithm='PPO continuation' if a.resume else 'PPO from scratch',source=a.source,task='Local alignment and physical clipping; ends at separation.',action='Six joint-target increments + stock jaw target increment at 50 Hz, finite motor forces.',observations='38 simulator state values; no image observations.',reset_curriculum='Recorded physical commissioning states initialize increasingly earlier approach positions. No expert action targets, behavior-cloning initialization or runtime IK.',randomization='Independent cutter joint entry offsets +/-0.003 rad on all six joints and plant stiffness +/-15%. Local entry robustness only, not arbitrary plant morphology or global positions.',acceptance='Local approach and physical stem separation with the catcher held; this specialist ends at cutting, before withdrawal or receiving; unexpected contacts <=0.8 N, penetration <=0.8 mm, no inter-arm strike or solver warning.',development_seeds=[62001,62002,62003],holdout_seeds=list(range(a.holdout_start,a.holdout_start+8)),training_curriculum=a.curriculum,action_joint_scale=a.joint_scale,actual_upstream_entry=a.entry_run,eval_difficulty=a.fixed_difficulty if a.fixed_difficulty is not None else 1.,final_evaluation='Full dynamic plant and flex net',steps_per_round=a.steps,rounds=a.rounds,scope='Simulation-only PPO specialist. Uncalibrated fracture, textile, actuator and grip parameters. Same-arm self-collision unresolved.')
 dump(a.out/'proposal.json',proposal)
 env=SubprocVecEnv([lambda:CutterSkillEnv(a.source,0.,.5,a.curriculum,a.joint_scale,a.entry_run) for _ in range(a.envs)],start_method='spawn');env.seed(193)
 policy=PPO('MlpPolicy',env,n_steps=256,batch_size=256,n_epochs=8,learning_rate=.0005,gamma=.985,gae_lambda=.95,ent_coef=.002,policy_kwargs=dict(net_arch=dict(pi=[32,32],vf=[32,32]),log_std_init=-1.6),seed=193,device='cpu');
 if a.resume:policy=PPO.load(a.resume,env=env,device='cpu');policy.learning_rate=.0005;policy.lr_schedule=lambda _: .0005
 policy.policy.log_std.data[:6]=-2.2;policy.policy.log_std.data[6]=-.1;save_policy(policy,a.out/'initial')
 rows=[];best=None;score=(-1,-1,-1e9)
 for j in range(a.rounds):
  difficulty=a.fixed_difficulty if a.fixed_difficulty is not None else min(1.,a.start_difficulty+.5*j);env.set_attr('difficulty',difficulty);env.set_attr('variation',1.);policy._last_obs=env.reset();policy._last_episode_starts=np.ones(a.envs,dtype=bool);dump(a.out/'progress.json',dict(status='training',round=j+1,difficulty=difficulty,rounds=rows));t=time.time();policy.learn(a.steps,reset_num_timesteps=False);sec=time.time()-t;cp=a.out/f'round-{j+1}.zip';save_policy(policy,cp)
  dev=evaluate(policy,a.source,proposal['development_seeds'],difficulty=proposal['eval_difficulty'],curriculum=a.curriculum,joint_scale=a.joint_scale,entry_run=a.entry_run);row=dict(round=j+1,steps=int(policy.num_timesteps),train_seconds=sec,difficulty=difficulty,successes=sum(r['is_success'] for r in dev),cuts=sum(r['severed'] for r in dev),mean_error_m=float(np.mean([r['cutter_goal_error_m'] for r in dev])),rows=dev);rows.append(row);dump(a.out/f'round-{j+1}.json',row);print('ROUND',j+1,row['successes'],row['cuts'],row['mean_error_m'],flush=True)
  s=(row['successes'],row['cuts'],-row['mean_error_m'])
  if s>score:best=cp;score=s
 env.close();policy=PPO.load(best,device='cpu');hold=evaluate(policy,a.source,proposal['holdout_seeds'],a.out/'holdout',difficulty=proposal['eval_difficulty'],joint_scale=a.joint_scale,entry_run=a.entry_run);baseline=evaluate(None,a.source,proposal['holdout_seeds'][:3],difficulty=proposal['eval_difficulty'],joint_scale=a.joint_scale,entry_run=a.entry_run);count=sum(p.numel() for p in policy.policy.mlp_extractor.policy_net.parameters())+sum(p.numel() for p in policy.policy.action_net.parameters());report=dict(status='evaluated',checkpoint=str(best),checkpoint_sha256=hashlib.sha256(best.read_bytes()).hexdigest(),actor_parameters=count,successes=sum(r['is_success'] for r in hold),episodes=len(hold),rows=hold,baseline=baseline,rounds=rows,scope=proposal['scope']);dump(a.out/'report.json',report);dump(a.out/'progress.json',report);print('FINAL',report['successes'],report['episodes'],count,flush=True)
if __name__=='__main__':main()
