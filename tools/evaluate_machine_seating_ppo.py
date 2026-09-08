"""Resume evaluation from a saved PPO checkpoint without repeating training."""
import json,time,hashlib
from pathlib import Path
import torch
from stable_baselines3 import PPO
from train_machine_seating_ppo import evaluate,StructuredServo
out=Path('runs/machine-seating-ppo-v1');proposal=json.loads((out/'proposal.json').read_text());torch.set_num_threads(2);weights=torch.load('runs/machine-tending-structured-v2/policy.pt',weights_only=True);models={k:StructuredServo() for k in weights}
for k,m in models.items():m.load_state_dict(weights[k]);m.eval()
policy=PPO.load(out/'policy',device='cpu');start=time.time();(out/'status.json').write_text(json.dumps({'phase':'Resumed full-cycle evaluation','training_timesteps':policy.num_timesteps,'note':'Saved policy recovered after training-episode JSON serialization error.'}))
baseline=evaluate(None,models,proposal['dev_seeds'],out,'baseline');candidate=evaluate(policy,models,proposal['dev_seeds'],out,'candidate');report={'proposal':proposal,'baseline':baseline,'candidate':candidate,'baseline_successes':sum(r['success'] for r in baseline),'candidate_successes':sum(r['success'] for r in candidate),'training_timesteps':policy.num_timesteps,'training_seconds':None,'timing_note':'Training finished and saved checkpoint, but JSON export failed before timing was persisted. Do not report an inferred training duration.','evaluation_seconds':time.time()-start,'actor_parameters':sum(p.numel() for p in policy.policy.mlp_extractor.policy_net.parameters())+sum(p.numel() for p in policy.policy.action_net.parameters()),'promoted':False,'evaluation_source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,'tools/train_machine_seating_ppo.py']}}
(out/'report.json').write_text(json.dumps(report,indent=2));(out/'status.json').write_text(json.dumps({'phase':'Evaluation complete','baseline_successes':report['baseline_successes'],'candidate_successes':report['candidate_successes']}));print(report['baseline_successes'],report['candidate_successes'],flush=True)
