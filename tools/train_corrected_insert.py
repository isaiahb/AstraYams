"""Corrected insertion BC on physically executed learned predecessor states."""
import argparse
from pathlib import Path
import json,time,hashlib
import numpy as np,torch
from torch import nn
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_downstream_skills import DownstreamSkill,observe,scaffold
from astrafactory.contact_downstream_skills_v3 import expert_label,CorrectedInsertSkill
from astrafactory.skill_randomization import SkillRandomization
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--grasp',default='runs/micro-grasp-v1/policy.pt');p.add_argument('--align',default='runs/downstream-v2-dr/align.npz');args=p.parse_args()
out=args.out;out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(42);rng=np.random.default_rng(42)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
proposal={'scope':'Corrected angular-only label gate, trained on actual learned micrograsp and frozen align handoffs; continuous learned development execution','train_seeds':list(range(100,124)),'dev_seeds':list(range(2400,2410)),'source_sha256':{p:sha(p) for p in ['src/astrafactory/contact_downstream_skills_v3.py',__file__]},'checkpoints':{p:sha(p) for p in [args.grasp,args.align]},'change':'Training label angular gate x[3:6], not x[3:] (velocity/load are not angular error). Original evaluator unchanged.'}
(out/'proposal.json').write_text(json.dumps(proposal,indent=2));start=time.time()

def enter(e,seed,dr=None):
 (dr or e).reset(seed=seed);g=MicroGrasp(args.grasp);g.start(e);a=DownstreamSkill(args.align,'align');phase='grasp';history=[]
 for _ in range(e.horizon):
  act=g.act(e) if phase=='grasp' else a.act(e)
  _,_,done,trunc,info=e.step(act);history.append(act)
  if done or trunc:return False,info,history
  if phase=='grasp' and g.handoff(e):phase='align';a.start(e)
  elif phase=='align' and a.handoff(e,info):return True,info,history
 return False,info,history

def insert(e,policy=None,collect=None):
 rows=[]
 while e.steps<e.horizon:
  x=observe(e,'insert');label=expert_label(e) if policy is None else None
  if collect is not None:collect[0].append(x);collect[1].append(label)
  before=e.data.qpos.copy();a=scaffold(e,'insert',label) if policy is None else policy.act(e);assert np.array_equal(before,e.data.qpos)
  _,_,done,trunc,info=e.step(a);rows.append({'step':e.steps,'action':a.tolist(),**info})
  if done or trunc:break
 return info,rows

data=[[],[]];train=[];e=CurriculumEnv('tasks/yam_contact_curriculum');dr=SkillRandomization(e,'training-mild-v1','training')
for seed in proposal['train_seeds']:
 ok,entry,history=enter(e,seed,dr);result={'seed':seed,'entered_insertion':ok,'entry':entry,'dr':dr.last_sample}
 if ok:
  info,rows=insert(e,collect=data);result['final']=info
  np.savez_compressed(out/f'train-{seed}-prefix.npz',actions=np.array(history))
 train.append(result);print(json.dumps(result),flush=True)
e.close();x=np.array(data[0]);y=np.array(data[1]);np.savez_compressed(out/'dataset.npz',observation=x,label=y)
weight=np.linalg.solve(x.T@x+1e-8*np.eye(15),x.T@y);np.savez(out/'linear.npz',weight=weight)
mean=x.mean(0);std=x.std(0).clip(.01);xn=torch.tensor((x-mean)/std,dtype=torch.float32);target=torch.tensor(y-x@weight,dtype=torch.float32)
net=nn.Sequential(nn.Linear(15,32),nn.Tanh(),nn.Linear(32,32),nn.Tanh(),nn.Linear(32,6));nn.init.zeros_(net[-1].weight);nn.init.zeros_(net[-1].bias);opt=torch.optim.Adam(net.parameters(),lr=.0003);losses=[]
for k in range(600):
 idx=torch.tensor(rng.integers(len(x),size=256));pred=net(xn[idx]);loss=((pred-target[idx])**2).mean();opt.zero_grad();loss.backward();opt.step()
 if k%50==0:losses.append({'step':k,'loss':float(loss.detach())})
params={'weight':weight,'mean':mean,'std':std}
for i,j in [(1,0),(2,2),(3,4)]:params[f'w{i}']=net[j].weight.detach().numpy().T;params[f'b{i}']=net[j].bias.detach().numpy()
np.savez(out/'nonlinear.npz',**params);dev=[]
for version in ['linear','nonlinear']:
 e=CurriculumEnv('tasks/yam_contact_curriculum');policy=CorrectedInsertSkill(out/f'{version}.npz')
 for seed in proposal['dev_seeds']:
  ok,entry,history=enter(e,seed);result={'version':version,'seed':seed,'entered_insertion':ok,'entry':entry}
  if ok:
   info,rows=insert(e,policy=policy);result['final']=info;(out/f'{version}-{seed}-trace.json').write_text(json.dumps(rows));np.savez_compressed(out/f'{version}-{seed}-prefix.npz',actions=history)
  dev.append(result);print(json.dumps(result),flush=True)
 e.close()
report={'proposal':proposal,'training':train,'development':dev,'train_samples':len(x),'linear_mse':float(np.mean((x@weight-y)**2)),'residual_losses':losses,'wall_seconds':time.time()-start,'checkpoint_sha256':{v:sha(out/f'{v}.npz') for v in ['linear','nonlinear']},'label':'Tiny privileged controller distillation + nonlinear residual BC; learned micrograsp/align/insert with fixed IK scaffold, no teacher calls or commands at eval'}
(out/'report.json').write_text(json.dumps(report,indent=2));print('DONE',len(x))
