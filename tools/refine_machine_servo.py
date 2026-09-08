"""Fit structured local feedback from physical demonstrations; same task evaluator."""
from pathlib import Path
import json,time,torch,numpy as np
from train_machine_tending import rollout,registry,sha
from astrafactory.machine_tending_policy import StructuredServo
out=Path('runs/machine-tending-structured-v2');out.mkdir(exist_ok=False);torch.set_num_threads(2);torch.manual_seed(43)
proposal={'training_data':'runs/machine-tending-bc-v1/*-data.npz','dev_seeds':list(range(57000,57005)),'reserved_final_seeds':list(range(58000,58020)),'scope':'Two structured7-gain learned feedback controllers; scripted targets/workflow/IK/force-driven machine commands. BC, state-based; not VLA. Same unchanged physical evaluator.','sources':{p:sha(p) for p in ['src/astrafactory/machine_tending.py','src/astrafactory/machine_tending_policy.py','tools/refine_machine_servo.py','tools/train_machine_tending.py','tasks/yam_machine_tending/scene.xml','tasks/yam_machine_tending/task.json']}}
(out/'proposal.json').write_text(json.dumps(proposal,indent=2));registry('training','Fitting constrained local controllers','The MLP stalled. Fitting axis-separated feedback gains to prevent cross-axis drift; unchanged task evaluation.')
models={};start=time.time()
for k in ['transport','precision']:
 d=np.load(f'runs/machine-tending-bc-v1/{k}-data.npz');x=torch.tensor(d['observation']);y=torch.tensor(d['action']);m=StructuredServo();opt=torch.optim.Adam(m.parameters(),lr=.1)
 for i in range(4000):
  ix=torch.randint(len(x),(1024,));loss=((m(x[ix])-y[ix])**2).mean();opt.zero_grad();loss.backward();opt.step()
 m.eval();models[k]=m;print(k,m.gain.detach().tolist(),float(loss),flush=True)
seconds=time.time()-start;torch.save({k:m.state_dict() for k,m in models.items()},out/'policy.pt');registry('evaluating','Evaluating structured controller candidate','Two14-total-parameter controllers fitted; running physical held-out tests.')
initial={k:StructuredServo() for k in models};trials=[]
for mode,ms in [('initial',initial),('trained',models)]:
 for s in proposal['dev_seeds']:trials.append(rollout(s,ms,out,mode,video=s==57000))
scores={mode:sum(t['success'] for t in trials if t['mode']==mode) for mode in ['initial','trained']};report={'proposal':proposal,'trials':trials,'scores':scores,'training_seconds':seconds,'parameters':14,'gains':{k:m.gain.detach().tolist() for k,m in models.items()}}
(out/'report.json').write_text(json.dumps(report,indent=2));registry('complete' if scores['trained']==5 else 'failed','Structured controller evaluation complete',f"Initial{scores['initial']}/5; fitted{scores['trained']}/5. Engineered workflow with fitted feedback, not learned planning.",metrics=[{'label':'Initial','value':f"{scores['initial']}/5"},{'label':'Fitted controllers','value':f"{scores['trained']}/5"},{'label':'Fit time','value':f'{seconds:.1f}s'}],preview=str(out/'trained-57000.mp4'));print(scores,flush=True)
