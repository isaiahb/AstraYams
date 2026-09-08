"""Frozen five-case holdout; no training or model selection in this script."""
import json,hashlib,time
from pathlib import Path
import torch
from stable_baselines3 import PPO
from train_machine_seating_ppo import evaluate,StructuredServo
source=Path('runs/machine-seating-ppo-v1');out=Path('runs/machine-seating-ppo-v1-holdout');out.mkdir(exist_ok=False);torch.set_num_threads(2)
proposal={'role':'final five-case holdout','seeds':list(range(58000,58005)),'checkpoint_sha256':hashlib.sha256((source/'policy.zip').read_bytes()).hexdigest(),'selection':'Frozen after development 4/5 vs baseline2/5; no further training permitted before this evaluation','scope':'Five of20 reserved seeds; remaining58005–58019 untouched. Small-sample evidence only.'};(out/'proposal.json').write_text(json.dumps(proposal,indent=2))
weights=torch.load('runs/machine-tending-structured-v2/policy.pt',weights_only=True);models={k:StructuredServo() for k in weights}
for k,m in models.items():m.load_state_dict(weights[k]);m.eval()
policy=PPO.load(source/'policy',device='cpu');start=time.time();baseline=evaluate(None,models,proposal['seeds'],out,'baseline');candidate=evaluate(policy,models,proposal['seeds'],out,'candidate');report={'proposal':proposal,'baseline':baseline,'candidate':candidate,'baseline_successes':sum(r['success'] for r in baseline),'candidate_successes':sum(r['success'] for r in candidate),'evaluation_seconds':time.time()-start};(out/'report.json').write_text(json.dumps(report,indent=2));print(report['baseline_successes'],report['candidate_successes'],flush=True)
