"""Closed-loop SmolVLA camera/proprio evaluation without teacher actions or state input.

Run with pinned LeRobot and MUJOCO_GL=egl on the GPU worker. Saved-checkpoint
processors must match the supplied training dataset statistics. The optional
base-model path adapts feature names and normalization to this task without
training its pretrained weights; that adaptation is explicitly reported.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import time
import subprocess
import lerobot

os.environ.setdefault('MUJOCO_GL', 'egl')
import numpy as np
import torch
import mujoco
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.configs.types import FeatureType
from lerobot.utils.feature_utils import dataset_to_policy_features
from collect_demonstrations import task_hashes

IMAGE_KEY='observation.images.overview'
STATE_KEY='observation.state'
TASK_TEXT='Pick up the keyed peg and insert it into the matching socket.'


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def validate_stats(processor, expected, keys):
    """Reject mismatched checkpoint normalizers; never silently replace them."""
    result={}
    for key in keys:
        found=False
        for step in processor.steps:
            loaded=getattr(step,'_tensor_stats',{}).get(key)
            if loaded is None:continue
            found=True
            for field in ['mean','std','min','max']:
                if field not in expected[key]:continue
                if field not in loaded:raise ValueError(f'Processor missing {key}/{field}')
                actual=loaded[field].detach().cpu().numpy().reshape(-1)
                wanted=np.asarray(expected[key][field],dtype=np.float32).reshape(-1)
                if actual.shape!=wanted.shape or not np.allclose(actual,wanted,rtol=1e-5,atol=1e-7):
                    raise ValueError(f'Checkpoint processor stats mismatch: {key}/{field}')
            result[key]='matches supplied training dataset'
        if not found:raise ValueError(f'No saved normalization statistics for {key}')
    return result


def strict_posthoc(trajectory, thresholds):
    """Score only recorded states; never extend or modify environment termination."""
    consecutive=0;maximum=0;first=None
    for row in trajectory:
        qualifies=(row.get('was_lifted',False)
            and row['xy_error_m']<thresholds['xy_tolerance_m']
            and row['orientation_error_rad']<thresholds['yaw_tolerance_rad']
            and thresholds['tip_z_min_m']<=row['tip_z_m']<=thresholds['tip_z_max_m']
            and row['peg_speed_m_s']<thresholds['speed_max']
            and row['peak_contact_force_n']<thresholds['contact_force_max_n'])
        consecutive=consecutive+1 if qualifies else 0
        maximum=max(maximum,consecutive)
        if first is None and consecutive>=thresholds['hold_steps']:first=row['step']
    return {'success_from_recorded_trace':first is not None,'maximum_consecutive_qualifying_steps':maximum,'first_qualifying_success_step':first}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--checkpoint',help='Saved pretrained_model directory including processor files')
    source.add_argument('--base-model',help='Pretrained HF model adapted to task features/stats, without training')
    parser.add_argument('--dataset-root',type=Path,required=True)
    parser.add_argument('--task',type=Path,default=Path('tasks/yam_contact_curriculum'))
    parser.add_argument('--env-class',default='astrafactory.contact_curriculum:CurriculumEnv')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seed-start',type=int,default=2000)
    parser.add_argument('--episodes',type=int,default=3)
    parser.add_argument('--max-steps',type=int,default=None,help='Smoke-only budget; omit for full-horizon scoring')
    parser.add_argument('--device',default='cuda')
    parser.add_argument('--video',action='store_true')
    parser.add_argument('--video-every',type=int,default=5)
    args=parser.parse_args()
    if args.episodes<1 or args.video_every<1:parser.error('Episode count and video interval must be positive')
    if args.max_steps is not None and args.max_steps<1:parser.error('Step budget must be positive')
    if args.out.exists() and any(args.out.iterdir()):parser.error('Output directory must be empty')
    args.out.mkdir(parents=True,exist_ok=True)
    info_path=args.dataset_root/'meta/info.json';stats_path=args.dataset_root/'meta/stats.json'
    metadata=json.loads(info_path.read_text());stats=json.loads(stats_path.read_text())
    features=dataset_to_policy_features(metadata['features'])
    if tuple(features[STATE_KEY].shape)!=(28,) or tuple(features['action'].shape)!=(7,):
        raise ValueError('Dataset state/action must be exactly 28/7')
    if tuple(features[IMAGE_KEY].shape)!=(3,240,320):raise ValueError('Dataset overview image must be 3x240x320')
    source_path=args.checkpoint or args.base_model
    config=SmolVLAConfig.from_pretrained(source_path)
    config.device=args.device
    # Match the declared training/evaluation action-chunk contract.
    config.n_action_steps=5;config.chunk_size=50;config.num_steps=10
    if args.base_model:
        config.input_features={k:v for k,v in features.items() if v.type!=FeatureType.ACTION}
        config.output_features={k:v for k,v in features.items() if v.type==FeatureType.ACTION}
    if set(config.input_features)!={IMAGE_KEY,STATE_KEY}:
        raise ValueError(f'Unexpected policy inputs: {list(config.input_features)}')
    if tuple(config.input_features[STATE_KEY].shape)!=(28,) or tuple(config.output_features['action'].shape)!=(7,):
        raise ValueError('Checkpoint feature dimensions differ from this task')
    policy=SmolVLAPolicy.from_pretrained(source_path,config=config).to(args.device).eval()
    if args.base_model:
        pre,post=make_pre_post_processors(config,dataset_stats=stats)
    else:
        pre,post=make_pre_post_processors(config,pretrained_path=args.checkpoint,
            preprocessor_overrides={'device_processor':{'device':args.device}},
            postprocessor_overrides={'device_processor':{'device':'cpu'}})
    checks={'pre':validate_stats(pre,stats,[STATE_KEY]),'post':validate_stats(post,stats,['action'])}
    module,name=args.env_class.split(':');Env=getattr(importlib.import_module(module),name)
    env=Env(args.task);renderer=mujoco.Renderer(env.model,height=240,width=320)
    input_paths=sorted(p for p in args.task.rglob('*') if p.is_file() and '__pycache__' not in str(p))
    input_paths+=list(Path(importlib.import_module(module).__file__).parent.glob('*.py'))
    lerobot_root=Path(lerobot.__file__).resolve().parents[2]
    lerobot_commit=subprocess.check_output(['git','-C',str(lerobot_root),'rev-parse','HEAD'],text=True).strip()
    checkpoint_hashes={}
    if args.checkpoint:
        for path in sorted(Path(args.checkpoint).rglob('*')):
            if path.is_file():checkpoint_hashes[str(path.relative_to(args.checkpoint))]=sha(path)
    report={'label':'Actual closed-loop SmolVLA inference; no teacher action calls',
        'source':source_path,'lerobot_commit':lerobot_commit,'evaluation_script_sha256':sha(__file__),'pretrained_task_adaptation':bool(args.base_model),
        'adaptation_note':'Base weights unchanged; camera feature name, 28-value proprioception, 7 actions and training-dataset normalization adapted to task.' if args.base_model else None,
        'dataset_stats_sha256':sha(stats_path),'dataset_info_sha256':sha(info_path),
        'checkpoint_sha256':checkpoint_hashes,'task_sha256':{str(p):sha(p) for p in input_paths},'referenced_task_assets_sha256':task_hashes(args.task),
        'normalization_checks':checks,'policy_inputs':{IMAGE_KEY:'CHW float32 [0,1], 3x240x320',STATE_KEY:'q7, qvel7, commanded targets7, previous action7; no free-peg or socket pose','task':TASK_TEXT},
        'action_contract':'Postprocessed 7 target increments in environment normalized units; clipped to [-1,1] before step.',
        'inference_control':{'n_action_steps':5,'chunk_size':50,'num_steps':10,'control_hz':1/(env.model.opt.timestep*env.frame_skip)},
        'scope':'development' if args.seed_start<5000 else 'final seed range (caller must preserve untouched evaluation)',
        'max_steps_override':args.max_steps,
        'acceptance_discrepancy':{'actual_evaluator':'Frozen ContactTask uses XY < 0.001 m, full rotation < 0.06 rad, contact load < 45 N; was_lifted, tip 0.0075–0.012 m, linear speed < 0.015 m/s, 15 consecutive steps.',
            'configured_success':env.specification['success'],
            'strict_posthoc':'Separate audit applies configured XY, full-rotation (using yaw_tolerance_rad), tip, speed, load and hold thresholds plus was_lifted to recorded states only. Environment success and termination remain unchanged.'},'episodes':[]}
    (args.out/'report.json').write_text(json.dumps(report,indent=2))
    try:
        for seed in range(args.seed_start,args.seed_start+args.episodes):
            torch.manual_seed(seed);np.random.seed(seed)
            if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
            env.reset(seed=seed);policy.reset();pre.reset();post.reset()
            start=time.monotonic();trajectory=[];predicted=[];executed=[];writer=None;clip_count=0
            limit=min(env.horizon,args.max_steps or env.horizon)
            try:
                if args.video:
                    import imageio.v2 as imageio
                    writer=imageio.get_writer(args.out/f'seed-{seed}.mp4',fps=1/(env.model.opt.timestep*env.frame_skip*args.video_every),codec='libx264',quality=6)
                for step in range(limit):
                    renderer.update_scene(env.data,camera='overview');rgb=renderer.render().copy()
                    proprio=np.r_[env.data.qpos[env.qadr],env.data.qvel[env.vadr],env.target,env.previous_action].astype(np.float32)
                    if proprio.shape!=(28,) or not np.isfinite(proprio).all():raise ValueError('Invalid 28-value proprioception')
                    batch={IMAGE_KEY:torch.from_numpy(rgb).permute(2,0,1).float()/255.,STATE_KEY:torch.from_numpy(proprio),'task':TASK_TEXT}
                    with torch.inference_mode():
                        raw=policy.select_action(pre(batch));action=post(raw).detach().cpu().numpy().reshape(-1)
                    if action.shape!=(7,) or not np.isfinite(action).all():raise ValueError('Nonfinite or incorrectly shaped policy action')
                    clipped=np.clip(action,-1,1);clip_count+=int(np.any(clipped!=action))
                    predicted.append(action);executed.append(clipped)
                    # Privileged environment observation and info are never passed to policy.
                    _,reward,terminated,truncated,result=env.step(clipped)
                    trajectory.append({'step':step+1,'reward':float(reward),**result})
                    if writer and (step%args.video_every==0 or terminated or truncated):
                        renderer.update_scene(env.data,camera='overview');writer.append_data(renderer.render().copy())
                    if step%100==0:print(json.dumps({'seed':seed,'step':step+1,'is_success':result['is_success'],'reason':result.get('reason')}),flush=True)
                    if terminated or truncated:break
            finally:
                if writer:writer.close()
            np.savez_compressed(args.out/f'seed-{seed}-actions.npz',predicted=predicted,executed=executed)
            (args.out/f'seed-{seed}-trace.json').write_text(json.dumps(trajectory))
            episode={'seed':seed,'steps':len(trajectory),'wall_seconds':time.monotonic()-start,'clipped_action_steps':clip_count,'final':trajectory[-1],
                'ended_by_budget':not (terminated or truncated),'success':bool(result['is_success']),'strict_posthoc':strict_posthoc(trajectory,env.specification['success'])}
            report['episodes'].append(episode);report['successes']=sum(x['success'] for x in report['episodes'])
            (args.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(episode),flush=True)
    finally:
        renderer.close();env.close()


if __name__=='__main__':main()
