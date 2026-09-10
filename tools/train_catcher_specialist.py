"""PPO specialist -> fixed holdout -> successful synthetic demonstrations."""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from astrafactory.catcher_positioning import CatcherPositioningEnv,TASK

def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def evaluate(policy,seeds,variation=1.,out=None,task_dir=TASK,completion_bonus=12.):
 e=CatcherPositioningEnv(variation,task_dir,completion_bonus);rows=[]
 for seed in seeds:
  o,_=e.reset(seed=seed);obs=[];acts=[];qpos=[e.data.qpos.copy()];qvel=[e.data.qvel.copy()];trace=[];ctrl=[]
  while True:
   a=policy.predict(o,deterministic=True)[0] if policy is not None else np.zeros(6);obs.append(o);acts.append(a)
   o,r,done,trunc,info=e.step(a);qpos.append(e.data.qpos.copy());qvel.append(e.data.qvel.copy());trace.append(info);ctrl.append(e.data.ctrl.copy())
   if done or trunc:break
  rows.append(dict(seed=seed,**info))
  if out:
   out.mkdir(exist_ok=True,parents=True)
   np.savez_compressed(out/f'episode-{seed}.npz',observations=obs,actions=acts,qpos=qpos,qvel=qvel,ctrl=ctrl,t=np.arange(len(qpos))*.02,terminal_observation=o)
   dump(out/f'episode-{seed}.json',dict(result=rows[-1],trace=trace))
  print('evaluation',seed,info['is_success'],round(info['distance_m']*1000,2),'mm',flush=True)
 e.close();return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('runs/catcher-specialist-v1'));p.add_argument('--steps',type=int,default=16384);p.add_argument('--rounds',type=int,default=3);p.add_argument('--envs',type=int,default=4);p.add_argument('--seed',type=int,default=67);p.add_argument('--task-dir',type=Path,default=TASK);p.add_argument('--lr',type=float,default=.001);p.add_argument('--epochs',type=int,default=5);p.add_argument('--holdout-start',type=int,default=42001);p.add_argument('--holdout-count',type=int,default=12);p.add_argument('--dev-count',type=int,default=3);p.add_argument('--completion-bonus',type=float,default=12.);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 torch.set_num_threads(1)
 proposal=dict(title='Astra teaches a small catcher-positioning specialist',algorithm='PPO from scratch',actor_hidden_layers=[32,32],observations='35 privileged simulator state values: joints, joint-target error, target position/velocity, catcher normal, previous action, grasp quality, hold progress. Not a camera policy.',action='Six joint-target increments at 50 Hz; finite-torque PD underneath. No IK or BC in execution.',task='Place the gripper-held catcher rim 18 mm below the lowest point of the outer berry, center it and hold 0.4 s.',success='3D rim-center error <5 mm, normal_z >0.96, joint speed norm <0.35, both jaws >0.2 N, tool slip <5 mm and rotation <0.15 rad for 20 steps.',failure='Unexpected robot/tool contact >0.8 N, penetration >0.8 mm, tool slip >25 mm, rotation >0.5 rad, or numerical warning. These are engineering criteria, not biological limits.',variation='Plant XYZ +/-20/20/12 mm, yaw +/-0.2 rad, stalk stiffness +/-15%; full plant joints retained. Priors, not identified real distributions.',train_variation=[.2,.6,1.],dev_seeds=list(range(41001,41001+a.dev_count)),holdout_seeds=list(range(a.holdout_start,a.holdout_start+a.holdout_count)),reward_design='Dense progress and proximity reward, upright-tool term, action/jerk costs, sustained-success bonus and invalid-contact penalty. Defined before training; see source.',scope='Positioning subskill only. Catcher is prepositioned between jaws at reset; no pickup. Textile is a visual rest shape, no net/fruit contact or cutting. Self-collision disabled; uncalibrated actuators, stiffness and friction. State-based simulated generalization only.',source_hashes={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ['src/astrafactory/catcher_positioning.py','tools/build_catcher_positioning.py',__file__,str(a.task_dir/'scene.xml')]})
 proposal.update(completion_bonus=a.completion_bonus,task_dir=str(a.task_dir.resolve()),learning_rate=a.lr,ppo_epochs=a.epochs,max_rounds=a.rounds,steps_per_round=a.steps,early_stop='Two consecutive full-variation rounds with all development cases passing; success criteria unchanged.')
 dump(a.out/'proposal.json',proposal);dump(a.out/'progress.json',dict(status='baseline',proposal='proposal.json',rounds=[]))
 env=SubprocVecEnv([lambda:CatcherPositioningEnv(.2,a.task_dir,a.completion_bonus) for _ in range(a.envs)],start_method='spawn');env.seed(a.seed)
 policy=PPO('MlpPolicy',env,learning_rate=a.lr,n_steps=256,batch_size=512,n_epochs=a.epochs,gamma=.98,gae_lambda=.95,ent_coef=.002,policy_kwargs={'net_arch':dict(pi=[32,32],vf=[32,32]),'log_std_init':-1.2},seed=a.seed,device='cpu',verbose=0)
 policy.save(a.out/'untrained');base=evaluate(policy,proposal['dev_seeds'],1.,a.out/'baseline',a.task_dir,a.completion_bonus);dump(a.out/'baseline.json',base)
 rows=[];best=None;best_score=(-1,-1e9);started=time.perf_counter()
 for j in range(a.rounds):
  variation=proposal['train_variation'][min(j,2)];env.set_attr('variation',variation);dump(a.out/'progress.json',dict(status='training',active_round=j+1,rounds=rows,baseline=base,elapsed_seconds=time.perf_counter()-started))
  start=time.perf_counter();policy.learn(a.steps,reset_num_timesteps=False);duration=time.perf_counter()-start;checkpoint=a.out/f'round-{j+1}.zip';policy.save(checkpoint)
  dev=evaluate(policy,proposal['dev_seeds'],1.,task_dir=a.task_dir,completion_bonus=a.completion_bonus);success=sum(x['is_success'] for x in dev);distance=float(np.mean([x['distance_m'] for x in dev]));row=dict(round=j+1,variation=variation,steps=int(policy.num_timesteps),train_seconds=duration,successes=success,episodes=len(dev),mean_distance_m=distance,rows=dev);rows.append(row);dump(a.out/f'round-{j+1}.json',row)
  score=(success,-distance)
  if score>best_score:best_score=score;best=checkpoint
  print('ROUND',json.dumps({k:v for k,v in row.items() if k!='rows'}),flush=True)
  if len(rows)>=2 and all(x['variation']==1. and x['successes']==x['episodes'] for x in rows[-2:]):break
 env.close();dump(a.out/'progress.json',dict(status='holdout',rounds=rows,baseline=base,selected_checkpoint=str(best)))
 policy=PPO.load(best,device='cpu');holdout=evaluate(policy,proposal['holdout_seeds'],1.,a.out/'holdout',a.task_dir,a.completion_bonus);fixed=evaluate(None,proposal['holdout_seeds'],1.,task_dir=a.task_dir,completion_bonus=a.completion_bonus)
 successful=[x['seed'] for x in holdout if x['is_success'] and not x['invalid']]
 actor=sum(p.numel() for p in policy.policy.mlp_extractor.policy_net.parameters())+sum(p.numel() for p in policy.policy.action_net.parameters())
 report=dict(status='evaluated',actor_parameters=actor,checkpoint=str(best),checkpoint_sha256=hashlib.sha256(best.read_bytes()).hexdigest(),successes=len(successful),episodes=len(holdout),baseline_successes=sum(x['is_success'] for x in fixed),rows=holdout,baseline_rows=fixed,rounds=rows,scope=proposal['scope'],split='single untouched holdout, model selected using development seeds only')
 dump(a.out/'report.json',report);dump(a.out/'progress.json',report)
 dump(a.out/'demonstrations.json',dict(accepted_seeds=successful,episodes=[f'holdout/episode-{s}.npz' for s in successful],fields=['observations','actions','qpos','qvel','ctrl','t','terminal_observation'],quality_filter='Fixed positioning success and no invalid flag. Failures retained under holdout; acceptance is not a bruise-safety result.',scope='Simulator state/action demonstrations from the PPO specialist. Camera frames and student imitation learning are separate follow-on steps.'))
 print('FINAL',json.dumps({k:v for k,v in report.items() if k not in ['rows','baseline_rows','rounds']}),flush=True)

if __name__=='__main__':main()
