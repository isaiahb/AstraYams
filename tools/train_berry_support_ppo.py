"""Scratch PPO, joint-level strawberry support; fixed acceptance, held-out seeds."""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from astrafactory.berry_support import BerrySupportEnv

def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def evaluate(policy,seeds,variation,out=None):
 e=BerrySupportEnv(variation);rows=[]
 for seed in seeds:
  o,_=e.reset(seed=seed);actions=[];qs=[];trace=[]
  while True:
   a=policy.predict(o,deterministic=True)[0] if policy is not None else np.zeros(6)
   o,r,done,trunc,info=e.step(a);actions.append(a);qs.append(e.data.qpos.copy());trace.append({k:v for k,v in info.items() if k!='domain_randomization'})
   if done or trunc:break
  rows.append(dict(seed=seed,**info))
  if out:
   np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,actions=actions)
   dump(out/f'episode-{seed}.json',dict(result=rows[-1],trace=trace))
 e.close();return rows

def main():
 global BerrySupportEnv
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('runs/yam-berry-support-ppo-v1'));p.add_argument('--rounds',type=int,default=4);p.add_argument('--steps',type=int,default=65536);p.add_argument('--envs',type=int,default=8);p.add_argument('--resume',type=Path);p.add_argument('--gripped',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if a.gripped:
  from astrafactory.gripped_berry_support import GrippedBerrySupportEnv
  BerrySupportEnv=GrippedBerrySupportEnv
 torch.set_num_threads(2)
 proposal=dict(algorithm='PPO from scratch; no BC or IK in policy execution',action='six coordinated joint-target increments, bounded to 0.015 rad at 50Hz',actor=[34,32,32,6],physics='MuJoCo 2kHz, finite torque PD; fixed mounted cup, articulated fruit stalks, frozen settled foliage obstacles',observations='privileged simulated joint state, relative fruit target, cup orientation and true contact force; not a vision or real-hardware policy',train_variations=[.1,.35,.7,1.0],dev_seeds=[31001,31002,31003],holdout_seeds=list(range(32001,32013)),acceptance='20 consecutive steps (0.4s): vertical support 60-110% of fruit body weight, XY error <5mm, cup normal Z >0.94, joint speed norm <0.3; abort >0.65N target load, >0.8N other robot contact or >0.8mm target penetration. These are engineering thresholds, not bruise limits.',horizon_s=4,initialization='One fixed arm posture built once using IK; not solved for each target; episode setup only.',scope='Support subskill only, not harvest/cutting; uncalibrated actuator/plant/contact models; robot self-collision disabled in this first constrained local task.',source_hashes={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ['src/astrafactory/berry_support.py',__file__,'tools/build_yam_berry_support.py','tasks/yam_berry_support/scene.xml']})
 if a.gripped:
  proposal.update(train_variations=[.35,1.,1.,1.],physics='MuJoCo 2kHz, finite torque PD; independent free tool held by jaw contact and friction; articulated fruit stalks and frozen foliage',acceptance=proposal['acceptance']+' Also requires both jaws contacting the handle, tool slip below 5mm and rotation below 0.15rad.',initialization='One fixed initial arm posture; tool prepositioned between jaws at reset and released into contact dynamics. No rack pickup claim.',holdout_seeds=list(range(33001,33013)))
  for f in ['src/astrafactory/gripped_berry_support.py','tools/build_gripped_berry_tool.py','tasks/yam_gripped_berry_support/scene.xml']:proposal['source_hashes'][f]=hashlib.sha256(Path(f).read_bytes()).hexdigest()
 if a.resume:proposal.update(algorithm='PPO finetune of earlier PPO approach checkpoint; no BC or execution IK',initial_checkpoint=str(a.resume),initial_checkpoint_sha256=hashlib.sha256(a.resume.read_bytes()).hexdigest())
 dump(a.out/'proposal.json',proposal)
 env=SubprocVecEnv([lambda:BerrySupportEnv(.1) for _ in range(a.envs)],start_method='spawn')
 policy=PPO.load(a.resume,env=env,device='cpu') if a.resume else PPO('MlpPolicy',env,learning_rate=.001,n_steps=256,batch_size=512,n_epochs=5,gamma=.98,gae_lambda=.95,ent_coef=.002,policy_kwargs={'net_arch':dict(pi=[32,32],vf=[32,32]),'log_std_init':-1.0},seed=51,device='cpu',verbose=0)
 if not a.resume:
  dump(a.out/'baseline.json',evaluate(None,proposal['dev_seeds'],.1))
  policy.save(a.out/'untrained')
 results=[]
 for round in range(a.rounds):
  variation=proposal['train_variations'][min(round,3)];env.set_attr('variation',variation)
  t=time.perf_counter();policy.learn(a.steps,reset_num_timesteps=False);seconds=time.perf_counter()-t;policy.save(a.out/f'round-{round+1}')
  rows=evaluate(policy,proposal['dev_seeds'],variation)
  result=dict(round=round+1,variation=variation,train_seconds=seconds,steps=int(policy.num_timesteps),successes=sum(r['is_success'] for r in rows),mean_distance=float(np.mean([r['distance_m'] for r in rows])),mean_return=float(np.mean([r['return_sum'] for r in rows])),rows=rows)
  dump(a.out/f'round-{round+1}.json',result);results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
 env.close();dump(a.out/'development.json',results)

if __name__=='__main__':main()
