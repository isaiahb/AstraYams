"""Train-only closing-transition loss weights; no dataset or simulator mutations.

Build: python tools/closing_weights.py --dataset-root ... --out /workspace/closing-weights.npz
Integration: install_closing_weighter(); config.sample_weighting =
SampleWeightingConfig(type="closing_window", extra_params={"weights_path": "..."}).
The adapter extends the pinned factory in-process; vendor files are unchanged.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import torch
from lerobot.utils.sample_weighting import SampleWeighter


class ClosingWindowWeighter(SampleWeighter):
    def __init__(self, weights_path, device, dataset_root=None):
        path=Path(weights_path)
        with np.load(path,allow_pickle=False) as data:
            indices=data['index'];weights=data['weight']
        if not np.array_equal(indices,np.arange(len(indices))):
            raise ValueError('Weights must cover every contiguous global dataset index exactly once')
        if not np.isfinite(weights).all() or np.any(weights<=0):
            raise ValueError('All weights must be finite and positive')
        manifest=json.loads(path.with_suffix('.json').read_text())
        if dataset_root:
            actual=hashlib.sha256((Path(dataset_root)/'meta/info.json').read_bytes()).hexdigest()
            if actual!=manifest['dataset_info_sha256']:
                raise ValueError('Weights belong to a different training dataset')
            for relative,digest in manifest['source_parquet_sha256'].items():
                source=Path(dataset_root)/relative
                if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
                    raise ValueError('Training data changed after weight generation: '+relative)
        self.weights=torch.as_tensor(weights,dtype=torch.float32,device=device)
        self.stats={'type':'closing_window','frames':len(indices),'mean_weight':float(weights.mean()),
            'emphasized_frames':int(np.sum(weights>1)),'weights_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def compute_batch_weights(self,batch):
        if 'index' not in batch:
            raise ValueError('Closing-window weighting requires global sample indices; no uniform fallback')
        index=batch['index'].to(device=self.weights.device,dtype=torch.long).reshape(-1)
        if index.min()<0 or index.max()>=len(self.weights):
            raise ValueError('Sample index is outside the immutable weights table')
        raw=self.weights[index]
        normalized=raw/raw.mean()
        return normalized,{'mean_weight':float(raw.mean()),'emphasized_fraction':float((raw>1).float().mean())}

    def get_stats(self):
        return self.stats


def install_closing_weighter():
    """Add one explicit strategy to the official in-process factory."""
    import lerobot.utils.sample_weighting as weighting
    original=weighting.make_sample_weighter
    if getattr(original,'_closing_window_adapter',False):
        return
    def factory(config,policy,device,dataset_root=None,dataset_repo_id=None):
        if config is not None and config.type=='closing_window':
            return ClosingWindowWeighter(config.extra_params['weights_path'],device,dataset_root)
        return original(config,policy,device,dataset_root,dataset_repo_id)
    factory._closing_window_adapter=True
    weighting.make_sample_weighter=factory


def main():
    import pandas as pd
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--threshold',type=float,default=.1)
    parser.add_argument('--before',type=int,default=60)
    parser.add_argument('--after',type=int,default=60)
    parser.add_argument('--weight',type=float,default=5.)
    args=parser.parse_args()
    if args.out.exists() or args.out.with_suffix('.json').exists():
        parser.error('Weights output must be new')
    if args.before<0 or args.after<0 or args.weight<1:
        parser.error('Window counts must be nonnegative and emphasis at least1')
    sources=sorted((args.dataset_root/'data').rglob('*.parquet'))
    frame=pd.concat([pd.read_parquet(p,columns=['index','episode_index','frame_index','action']) for p in sources],ignore_index=True).sort_values('index')
    indices=np.asarray(frame['index'],dtype=np.int64)
    if not np.array_equal(indices,np.arange(len(frame))):
        raise ValueError('Dataset global indices are incomplete or duplicated')
    actions=np.stack(frame['action'].to_numpy())
    if actions.shape!=(len(frame),7):
        raise ValueError('Expected raw7-channel teacher action labels')
    selected=np.zeros(len(frame),dtype=bool);events=np.zeros(len(frame),dtype=bool);episodes=[]
    for episode,rows in frame.groupby('episode_index',sort=True):
        global_indices=np.asarray(rows['index'],dtype=np.int64)
        closing=np.flatnonzero(actions[global_indices,6]>args.threshold)
        if not len(closing):raise ValueError('No closing transitions in training episode '+str(episode))
        local=np.zeros(len(rows),dtype=bool)
        for step in closing:
            local[max(0,step-args.before):min(len(local),step+args.after+1)]=True
        selected[global_indices]=local;events[global_indices[closing]]=True
        episodes.append({'episode':int(episode),'frames':len(rows),'closing_frames':len(closing),
            'weighted_frames':int(local.sum()),'closing_first_frame':int(closing[0]),'closing_last_frame':int(closing[-1])})
    weights=np.where(selected,args.weight,1.).astype(np.float32)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.out,index=indices,weight=weights,closing_event=events)
    manifest={'label':'Training-only loss weighting from expert gripper commands; no progress reward or evaluation labels',
        'dataset_root':str(args.dataset_root),'dataset_info_sha256':hashlib.sha256((args.dataset_root/'meta/info.json').read_bytes()).hexdigest(),
        'source_parquet_sha256':{str(p.relative_to(args.dataset_root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'criterion':{'raw_expert_action_channel':6,'greater_than':args.threshold,'before_frames':args.before,'after_frames':args.after,
            'emphasized_weight':args.weight,'other_weight':1,'episode_boundaries_respected':True},
        'frames':len(frame),'closing_frames':int(events.sum()),'weighted_frames':int(selected.sum()),
        'weighted_frame_fraction':float(selected.mean()),'weighted_loss_mass_fraction':float(weights[selected].sum()/weights.sum()),
        'episodes':episodes,'integration':{'sample_weighting':{'type':'closing_window','extra_params':{'weights_path':str(args.out)}}}}
    args.out.with_suffix('.json').write_text(json.dumps(manifest,indent=2))
    # Check exact indexing, per-batch normalization and type dispatch without changing any model.
    install_closing_weighter()
    from lerobot.utils.sample_weighting import make_sample_weighter,SampleWeightingConfig
    cfg=SampleWeightingConfig(type='closing_window',extra_params={'weights_path':str(args.out)})
    adapter=make_sample_weighter(cfg,None,torch.device('cpu'),str(args.dataset_root))
    selected_index=int(np.flatnonzero(selected)[0]);ordinary_index=int(np.flatnonzero(~selected)[0])
    result,_=adapter.compute_batch_weights({'index':torch.tensor([selected_index,ordinary_index])})
    assert torch.allclose(result,torch.tensor([2*args.weight/(args.weight+1),2/(args.weight+1)]))
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['episodes','source_parquet_sha256']},indent=2))
    print('Factory/index/normalization smoke passed; vendor files and dataset unchanged.')


if __name__=='__main__':main()
