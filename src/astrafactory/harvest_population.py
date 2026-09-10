"""PPO support skill over different compiled anatomical models, not camera poses."""
from pathlib import Path
import json
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import mujoco
from astrafactory.dual_harvest import DualHarvestEnv


class PopulationSupportEnv(gym.Env):
 def __init__(self,population='runs/harvest-skill-suite/population-cells',split='train',seeds=None):
  self.root=Path(population);rows=json.loads((self.root/'manifest.json').read_text())
  self.rows=[r for r in rows if r['status']=='rest-valid' and (r['seed'] in seeds if seeds else r['split']==split)]
  if not self.rows:raise ValueError('No validated physical plant variants for this split')
  reference=Path('runs/dual-harvest-commission-v13/task');model=mujoco.MjModel.from_xml_path(str(reference/'scene.xml'));q=np.load(reference/'initial.npz')['qpos']
  self.reference_q=np.array([q[model.joint(f'joint{i}').qposadr[0]] for i in range(1,7)])
  self.envs={};self.action_space=spaces.Box(-1,1,(6,),np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(35,),np.float32)
 def reset(self,*,seed=None,options=None):
  super().reset(seed=seed);row=self.rows[int(self.np_random.integers(len(self.rows)))];key=row['seed']
  if key not in self.envs:self.envs[key]=DualHarvestEnv(variation=.2,task_dir=self.root/str(key)/'task')
  self.e=self.envs[key];o,i=self.e.reset(seed=int(self.np_random.integers(2**31)));self.row=row;self.steps=0;self.last=np.zeros(6)
  self.previous_distance=float(np.linalg.norm(self.e.geometry()[0]-self.e.geometry()[1]));return self.observe(),dict(**i,morphology_seed=key)
 def observe(self):
  o=self.e.observe();o[:6]=self.e.data.qpos[self.e.qids]-self.reference_q
  return o
 def step(self,action):
  a=np.asarray(action,float)
  if a.shape!=(6,) or not np.isfinite(a).all():raise ValueError('Six finite joint actions required')
  a=np.clip(a,-1,1);e=self.e;e.phase='PPO / support';info=e.advance(catch_action=a,allow_cut=False);self.steps+=1;distance=info['distance_m']
  success=bool(info['catcher_ready'] and not info['invalid']);reward=80*(self.previous_distance-distance)+1.2*np.exp(-distance/.025)+.15*info['normal_z']-.003*(a@a)-.006*np.square(a-self.last).sum()
  if e.hold>0:reward+=1
  if info['invalid']:reward-=8
  if success:reward+=200
  self.previous_distance=distance;self.last=a.copy();info.update(is_success=success,skill='support',morphology_seed=self.row['seed'],fruit_count=self.row['fruit_count'],leaf_count=self.row['leaf_count'],population_split=self.row['split'])
  return self.observe(),float(reward),bool(success or info['invalid']),self.steps>=200,info
 def close(self):
  for e in self.envs.values():e.close()
