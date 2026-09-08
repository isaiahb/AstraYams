"""Fine-tune pretrained SmolVLA on the versioned YAM contact camera dataset."""
from pathlib import Path
import argparse
from lerobot.configs.train import TrainPipelineConfig
from lerobot.configs.default import DatasetConfig, WandBConfig
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
from lerobot.scripts.lerobot_train import train

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset-root',type=Path,required=True)
    p.add_argument('--repo-id',default='astrafactory/yam-contact-train')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--steps',type=int,default=1000)
    p.add_argument('--save-freq',type=int,default=500)
    p.add_argument('--policy-path',default='lerobot/smolvla_base',help='Base model or checkpoint; starts a new fine-tuning phase with a fresh optimizer')
    args=p.parse_args()
    policy=SmolVLAConfig.from_pretrained(args.policy_path)
    # Direct assignment replaces the base embodiment's three cameras/six joints.
    policy.input_features={};policy.output_features={}
    policy.pretrained_path=Path(args.policy_path)
    policy.device='cuda';policy.push_to_hub=False
    policy.n_action_steps=5;policy.chunk_size=50;policy.num_steps=10
    policy.scheduler_warmup_steps=100
    config=TrainPipelineConfig(
        dataset=DatasetConfig(repo_id=args.repo_id,root=str(args.dataset_root)),
        policy=policy,output_dir=args.out,job_name=args.out.name,
        batch_size=16,steps=args.steps,save_freq=args.save_freq,env_eval_freq=0,
        log_freq=25,num_workers=2,wandb=WandBConfig(enable=False))
    train(config)

if __name__=='__main__':main()
