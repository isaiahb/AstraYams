"""Train a joint-level PPO specialist and retain per-stage learning evidence."""
import argparse,json,time,hashlib
from pathlib import Path
import torch,numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from astrafactory.harvest_joint_skill import HarvestJointSkill
from astrafactory.training_io import save_policy

def dump(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n')
class Progress(BaseCallback):
 def __init__(self,out):super().__init__();self.out=out;self.rows=[];self.started=time.time();self.ended=[]
 def _on_step(self):
  for done,info in zip(self.locals['dones'],self.locals['infos']):
   if done:self.ended.append(dict(success=bool(info.get('is_success')),invalid=bool(info.get('invalid')),error_m=info.get('goal_error_m')))
  return True
 def _on_rollout_end(self):
  row=dict(steps=self.num_timesteps,wall_s=time.time()-self.started,episodes=self.ended);self.rows.append(row);self.ended=[];dump(self.out/'rollouts.json',self.rows);print('ROLLOUT',row['steps'],'seconds',round(row['wall_s'],1),'episodes',len(row['episodes']),'successes',sum(x['success'] for x in row['episodes']),flush=True)
def evaluate(policy,config,seeds,out=None):
 env=HarvestJointSkill(**config);rows=[]
 for seed in seeds:
  o,_=env.reset(seed=seed);e=env.e;qs=[e.data.qpos.copy()];vs=[e.data.qvel.copy()];eq=[e.data.eq_active.copy()];net=[e.data.flexvert_xpos.copy()];ct=[e.target.copy()];ut=[e.cut_target.copy()];jt=[e.jaw_target];trace=[];actions=[]
  for _ in range(250):
   a=np.zeros(6) if policy is None else policy.predict(o,deterministic=True)[0];o,r,done,trunc,info=env.step(a);qs.append(e.data.qpos.copy());vs.append(e.data.qvel.copy());eq.append(e.data.eq_active.copy());net.append(e.data.flexvert_xpos.copy());ct.append(e.target.copy());ut.append(e.cut_target.copy());jt.append(e.jaw_target);trace.append(info);actions.append(a)
   if done or trunc:break
  row=dict(seed=seed,**info);rows.append(row);print('EVAL',config['skill'],seed,row['is_success'],row['invalid'],round(row['goal_error_m']*1000,2),flush=True)
  if out:
   out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,qvel=vs,eq_active=eq,flex_vertices=net,catch_targets=ct,cut_targets=ut,jaw_targets=jt,actions=actions,t=np.arange(len(qs))*.02);dump(out/f'episode-{seed}.json',dict(result=dict(**row,controller='Six-joint PPO specialist, finite motor control. Recorded reset curriculum; no runtime IK or expert action targets.'),trace=trace))
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--skill',choices=['approach','withdraw','carry','unload'],required=True);p.add_argument('--source',default='runs/dual-harvest-commission-v13');p.add_argument('--curriculum');p.add_argument('--out',type=Path,required=True);p.add_argument('--steps',type=int,default=4096);p.add_argument('--rounds',type=int,default=3);p.add_argument('--envs',type=int,default=2);p.add_argument('--resume');p.add_argument('--difficulties',default='0,.25,.5,1');p.add_argument('--learning-rate',type=float,default=.0005);a=p.parse_args();torch.set_num_threads(1)
 config=dict(skill=a.skill,source=a.source,curriculum=a.curriculum,difficulty=0.,variation=1.);dump(a.out/'proposal.json',dict(**config,method='PPO; no action demonstrations or runtime IK',observations=('87 simulator state features including payload motion and receiving contacts' if a.skill in ['carry','unload'] else '67 simulator state features including nearby fruit and stalk geometry'),learning_rate=a.learning_rate,resume=a.resume,steps_per_round=a.steps,round_count=a.rounds,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('src/astrafactory/harvest_joint_skill.py'),Path('src/astrafactory/dual_harvest.py'),Path('src/astrafactory/harvest_basket.py'),Path(a.source)/'task/scene.xml']},action='Six coordinated joint target increments',score_scope='Contact and impact proxies, not real tissue damage calibration',holdout_seeds=[73001,73002,73003,73004]))
 env=SubprocVecEnv([lambda:HarvestJointSkill(**config) for _ in range(a.envs)],start_method='spawn');policy=PPO('MlpPolicy',env,n_steps=256,batch_size=256,n_epochs=8,learning_rate=a.learning_rate,gamma=.985,ent_coef=.001,policy_kwargs=dict(net_arch=dict(pi=[32,32],vf=[32,32]),log_std_init=-2.),device='cpu',seed=41);
 if a.resume:policy=PPO.load(a.resume,env=env,device='cpu');policy.learning_rate=a.learning_rate;policy.lr_schedule=lambda _: a.learning_rate
 save_policy(policy,a.out/'initial');rounds=[];schedule=[float(x) for x in a.difficulties.split(',')];stage=0
 for j in range(a.rounds):
  difficulty=schedule[min(stage,len(schedule)-1)];env.set_attr('difficulty',difficulty);policy._last_obs=env.reset();policy._last_episode_starts=np.ones(a.envs,dtype=bool);dump(a.out/'progress.json',dict(status='training',round=j+1,difficulty=difficulty,rounds=rounds));start=time.time();policy.learn(a.steps,reset_num_timesteps=False,callback=Progress(a.out/f'round-{j+1}-training'));save_policy(policy,a.out/f'round-{j+1}');dev=evaluate(policy,dict(config,difficulty=difficulty),[74001,74002]);row=dict(round=j+1,difficulty=difficulty,steps=policy.num_timesteps,seconds=time.time()-start,development=dev);rounds.append(row);dump(a.out/f'round-{j+1}.json',row)
  if all(r['is_success'] for r in dev):stage+=1
 env.close();hold=evaluate(policy,dict(config,curriculum=None,difficulty=1.),[73001,73002,73003,73004],a.out/'holdout');baseline=evaluate(None,dict(config,curriculum=None,difficulty=1.),[73001]);cp=a.out/f'round-{a.rounds}.zip';count=sum(p.numel() for p in policy.policy.mlp_extractor.policy_net.parameters())+sum(p.numel() for p in policy.policy.action_net.parameters());report=dict(status='evaluated',skill=a.skill,checkpoint=str(cp),checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),actor_parameters=count,successes=sum(r['is_success'] for r in hold),episodes=len(hold),rows=hold,baseline=baseline,rounds=rounds,scope='Local skill holdouts in the full dynamics. Morphology holdout and composed-chain evaluation are separate.');dump(a.out/'report.json',report);dump(a.out/'progress.json',report)
if __name__=='__main__':main()
