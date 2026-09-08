"""Explicit training-only closing-window loss emphasis for pinned LeRobot.

This starts a separate phase with a fresh optimizer. It does not modify the
training dataset, vendor code, policy action API, simulator or acceptance.
"""
from pathlib import Path
import argparse
import hashlib
import json
from closing_weights import install_closing_weighter
from lerobot.configs.train import TrainPipelineConfig
from lerobot.configs.default import DatasetConfig,WandBConfig
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
from lerobot.scripts.lerobot_train import train
from lerobot.utils.sample_weighting import SampleWeightingConfig


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root',type=Path,required=True)
    parser.add_argument('--repo-id',default='astrafactory/yam-contact-train')
    parser.add_argument('--policy-path',required=True)
    parser.add_argument('--weights',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=1000)
    parser.add_argument('--batch-size',type=int,default=16)
    parser.add_argument('--save-freq',type=int,default=500)
    args=parser.parse_args()
    policy=SmolVLAConfig.from_pretrained(args.policy_path)
    policy.input_features={};policy.output_features={}
    policy.pretrained_path=Path(args.policy_path)
    policy.device='cuda';policy.push_to_hub=False
    policy.n_action_steps=5;policy.chunk_size=50;policy.num_steps=10
    policy.scheduler_warmup_steps=100
    install_closing_weighter()
    config=TrainPipelineConfig(dataset=DatasetConfig(repo_id=args.repo_id,root=str(args.dataset_root)),
        policy=policy,output_dir=args.out,job_name=args.out.name,batch_size=args.batch_size,
        steps=args.steps,save_freq=args.save_freq,env_eval_freq=0,log_freq=1 if args.steps<25 else 25,
        num_workers=2,wandb=WandBConfig(enable=False),
        sample_weighting=SampleWeightingConfig(type='closing_window',extra_params={'weights_path':str(args.weights)}))
    train(config)
    manifest={'label':'Separate fresh-optimizer phase with training-only closing-window loss weights',
        'initial_policy':args.policy_path,'steps':args.steps,'weights_sha256':hashlib.sha256(args.weights.read_bytes()).hexdigest(),
        'weight_definition':json.loads(args.weights.with_suffix('.json').read_text()),
        'action_contract_unchanged':{'n_action_steps':5,'chunk_size':50,'num_steps':10}}
    (args.out/'closing-weighting-manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
