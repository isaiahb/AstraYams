"""Contact ablation and timestep refinement on development seeds only."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np,torch
from stable_baselines3 import PPO
from astrafactory.berry_support import BerrySupportEnv

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();torch.set_num_threads(2);model=PPO.load(a.checkpoint,device='cpu');result={}
 for mode in ['nominal','cup_contact_disabled','half_timestep']:
  env=BerrySupportEnv(1.);rows=[]
  if mode=='cup_contact_disabled':
   for g in env.cupids:env.model.geom_contype[g]=0;env.model.geom_conaffinity[g]=0
  if mode=='half_timestep':env.model.opt.timestep/=2;env.skip*=2
  for seed in [31001,31002,31003]:
   obs,_=env.reset(seed=seed);max_target_force=0
   while True:
    action=model.predict(obs,deterministic=True)[0];obs,_,done,trunc,info=env.step(action);max_target_force=max(max_target_force,float(np.linalg.norm(info['force_N'])))
    if done or trunc:break
   rows.append(dict(seed=seed,success=info['is_success'],duration_s=info['sim_s'],support_fraction=info['support_fraction'],max_target_force_N=max_target_force,peak_contact_N=info['peak_contact_N'],invalid=info['invalid']))
  env.close();result[mode]=rows
 assert all(not x['success'] and x['max_target_force_N']==0 for x in result['cup_contact_disabled'])
 env=BerrySupportEnv();obs,_=env.reset(seed=31001)
 for _ in range(100):model.predict(obs,deterministic=True)
 t=time.perf_counter()
 for _ in range(1000):model.predict(obs,deterministic=True)
 result['single_observation_predict_mean_ms']=(time.perf_counter()-t)*1000/1000;env.close()
 result['checkpoint_sha256']=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest();result['scope']='Development seeds only. Not real-hardware calibration; only integration/contact-rubric checks.'
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
