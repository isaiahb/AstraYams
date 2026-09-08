"""PPO local seating corrections; physical prefixes, continuous composed evaluation."""
import argparse,copy,json,time,hashlib
from pathlib import Path
import gymnasium as gym,mujoco,numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from astrafactory.machine_tending import MachineTendingEnv,active_contacts
from astrafactory.machine_tending_policy import Workflow,StructuredServo
from astrafactory.yam_env import rotation_error,yaw_matrix


def observe(e):
 t=e.task;p=e.data.site_xpos[t.parts['raw']['site']];r=e.data.site_xmat[t.parts['raw']['site']].reshape(3,3);v=int(e.model.jnt_dofadr[t.parts['raw']['joint']]);f=active_contacts(e)
 return np.r_[(t.seat_position-p)/.03,rotation_error(yaw_matrix(np.pi),r)/.3,e.data.qvel[v:v+3]/.1,f/10,e.target[6]/.02].astype(np.float32)

class SeatingWorkflow(Workflow):
 def __init__(self,models):super().__init__(models);self.residual=np.zeros(3)
 def target(self,e):
  original=self.phase;target,rot,grip=super().target(e)
  if original=='seat_raw' and self.phase=='seat_raw':target=target+np.clip(self.residual,-1,1)*.002
  return target,rot,grip

def snapshot(e,w):
 mask=mujoco.mjtState.mjSTATE_INTEGRATION;s=np.empty(mujoco.mj_stateSize(e.model,mask));mujoco.mj_getState(e.model,e.data,s,mask)
 return {'integration':s,'target':e.target.copy(),'previous_action':e.previous_action.copy(),'steps':e.steps,'peak':e.episode_peak_force,'vise':e.vise_target_gap,'task':{k:copy.deepcopy(v) for k,v in e.task.__dict__.items() if k!='env'},'workflow':{k:copy.deepcopy(v) for k,v in w.__dict__.items() if k!='models'}}

def restore(e,w,s):
 mujoco.mj_setState(e.model,e.data,s['integration'],mujoco.mjtState.mjSTATE_INTEGRATION);e.target=s['target'].copy();e.previous_action=s['previous_action'].copy();e.steps=s['steps'];e.episode_peak_force=s['peak'];e.vise_target_gap=s['vise']
 for k,v in s['task'].items():setattr(e.task,k,copy.deepcopy(v))
 for k,v in s['workflow'].items():setattr(w,k,copy.deepcopy(v))
 mujoco.mj_forward(e.model,e.data)

def prefix(e,w,seed):
 e.reset(seed=seed);actions=[]
 for _ in range(e.horizon):
  before=e.data.qpos.copy();a=w.act(e);assert np.array_equal(before,e.data.qpos);_,_,done,trunc,info=e.step(a);actions.append(a)
  if w.phase=='seat_raw':return snapshot(e,w),actions
  if done or trunc:break
 raise RuntimeError(f'Physical prefix failed seed {seed}: {w.phase}')

class SeatEnv(gym.Env):
 def __init__(self,bank,models):
  self.base=MachineTendingEnv();self.workflow=SeatingWorkflow(models);self.bank=bank;self.observation_space=gym.spaces.Box(-np.inf,np.inf,(13,),dtype=np.float32);self.action_space=gym.spaces.Box(-1,1,(3,),dtype=np.float32);self.rows=[]
 def reset(self,seed=None,options=None):
  super().reset(seed=seed);i=int(self.np_random.integers(len(self.bank)));restore(self.base,self.workflow,self.bank[i]);self.total=0.;self.n=0;return observe(self.base),{'prefix_index':i}
 def step(self,action):
  e=self.base;w=self.workflow;before_error=np.linalg.norm(observe(e)[:3]*.03);w.residual=np.asarray(action);before=e.data.qpos.copy()
  try:
   a=w.act(e);assert np.array_equal(before,e.data.qpos);_,_,done,trunc,info=e.step(a)
  except ValueError as ex:
   info={'is_success':False,'reason':'ik_failure','exception':str(ex)};self.rows.append({'return':self.total-20,'final':info});return observe(e),-20.,True,False,info
  error=np.linalg.norm(observe(e)[:3]*.03);terms={'progress':100*(before_error-error),'force':-.005*max(info['peak_contact_force_n']-10,0),'effort':-.001*float(np.square(action).sum()),'time':-.002,'terminal':20*int(info['is_success'])-20*int(info['reason']=='force_limit')};terms={k:float(v) for k,v in terms.items()};reward=float(sum(terms.values()));self.total+=reward;self.n+=1;info['reward_components']=terms
  if done or trunc:self.rows.append({'steps':self.n,'return':self.total,'final':dict(info)})
  return observe(e),reward,done,trunc,info
 def close(self):self.base.close()

class Progress(BaseCallback):
 def __init__(self,out):super().__init__();self.out=out
 def _on_step(self):
  if self.num_timesteps%512==0:
   r={'phase':'PPO training','timesteps':self.num_timesteps,'episodes':len(self.training_env.envs[0].unwrapped.rows)};(self.out/'status.json').write_text(json.dumps(r));print(json.dumps(r),flush=True)
  return True

def evaluate(policy,models,seeds,out,label):
 results=[]
 for seed in seeds:
  e=MachineTendingEnv();e.reset(seed=seed);w=SeatingWorkflow(models);actions=[];states=[];trace=[];exc=None
  try:
   for _ in range(e.horizon):
    w.residual=np.zeros(3) if policy is None or w.phase!='seat_raw' else policy.predict(observe(e),deterministic=True)[0]
    before=e.data.qpos.copy();a=w.act(e);assert np.array_equal(before,e.data.qpos);_,_,done,trunc,info=e.step(a);actions.append(a);states.append(e.data.qpos.copy());trace.append({'phase':w.phase,'residual':w.residual.tolist(),**info})
    if done or trunc:break
  except Exception as ex:exc=repr(ex)
  r={'seed':seed,'success':bool(trace and trace[-1]['is_success'] and not exc),'exception':exc,'final':trace[-1] if trace else {},'handoffs':w.history};results.append(r);np.savez_compressed(out/f'{label}-{seed}.npz',actions=actions,qpos=states);(out/f'{label}-{seed}.json').write_text(json.dumps({'result':r,'trace':trace}));e.close();print(json.dumps({'evaluation':label,'seed':seed,'success':r['success'],'reason':r['final'].get('reason')}),flush=True)
 return results

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--steps',type=int,default=8192);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);torch.set_num_threads(2);start=time.time();ck='runs/machine-tending-structured-v2/policy.pt';weights=torch.load(ck,weights_only=True);models={k:StructuredServo() for k in weights}
 for k,m in models.items():m.load_state_dict(weights[k]);m.eval()
 sources=[__file__,'src/astrafactory/machine_tending.py','src/astrafactory/machine_tending_policy.py','tasks/yam_machine_tending/task.json','tasks/yam_machine_tending/scene.xml',ck];proposal={'algorithm':'PPO','train_prefix_seeds':list(range(56000,56004)),'dev_seeds':list(range(59000,59005)),'reserved_final_seeds':list(range(58000,58020)),'steps':a.steps,'action':'3D tool-target residual ±2mm only in seat_raw','observations':'13D privileged pose/velocity/contact/grip','training_reset':'Complete integration snapshots from real physical prefix rollouts; restores ONLY at isolated training episode reset','evaluation':'Continuous full cycle with frozen fitted transport/precision, workflow and IK; no resets between skills','source_sha256':{s:hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in sources}};(a.out/'proposal.json').write_text(json.dumps(proposal,indent=2))
 bank=[];e=MachineTendingEnv()
 for seed in proposal['train_prefix_seeds']:
  w=SeatingWorkflow(models);s,actions=prefix(e,w,seed);bank.append(s);np.savez_compressed(a.out/f'prefix-{seed}.npz',integration=s['integration'],actions=actions);print(json.dumps({'prefix':seed,'physical_steps':s['steps']}),flush=True)
 e.close();env=SeatEnv(bank,models);policy=PPO('MlpPolicy',env,learning_rate=3e-4,n_steps=512,batch_size=128,n_epochs=5,gamma=.995,policy_kwargs={'net_arch':dict(pi=[16,16],vf=[16,16]),'log_std_init':-2},device='cpu',seed=73,verbose=0)
 with torch.no_grad():policy.policy.action_net.weight.zero_();policy.policy.action_net.bias.zero_()
 policy.save(a.out/'initial');t=time.time();policy.learn(total_timesteps=a.steps,callback=Progress(a.out));seconds=time.time()-t;policy.save(a.out/'policy');(a.out/'training-episodes.json').write_text(json.dumps(env.rows));env.close();(a.out/'status.json').write_text(json.dumps({'phase':'Evaluating full cycle','training_seconds':seconds}))
 baseline=evaluate(None,models,proposal['dev_seeds'],a.out,'baseline');candidate=evaluate(policy,models,proposal['dev_seeds'],a.out,'candidate');report={'proposal':proposal,'baseline':baseline,'candidate':candidate,'baseline_successes':sum(r['success'] for r in baseline),'candidate_successes':sum(r['success'] for r in candidate),'training_seconds':seconds,'wall_seconds':time.time()-start,'actor_parameters':sum(p.numel() for p in policy.policy.mlp_extractor.policy_net.parameters())+sum(p.numel() for p in policy.policy.action_net.parameters()),'promoted':False};(a.out/'report.json').write_text(json.dumps(report,indent=2));(a.out/'status.json').write_text(json.dumps({'phase':'Completed development evaluation',**{k:report[k] for k in ['baseline_successes','candidate_successes','training_seconds']}}));print(json.dumps({k:report[k] for k in ['baseline_successes','candidate_successes','training_seconds']}),flush=True)
if __name__=='__main__':main()
