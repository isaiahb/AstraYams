"""Independent fixed-horizon evaluation of sensor-only visual pickup.

Privileged simulator measurements score outcomes after actions. They never enter
student observations, action generation, or a success-based stopping decision.
"""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
import torch
from astrafactory.vision_policy import VisualPolicy,resolve_device
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.deployable_observations import FixedCameraRig,reset_visual_episode
from check_yam_contact import physical_state,model_checks
from collect_demonstrations import task_hashes

THRESHOLDS={'control_steps':450,'control_hz':50,'rise_m':.020,'absolute_clearance_m':.065,
 'left_force_n_gt':.02,'right_force_n_gt':.02,'other_support_n_lt':.01,
 'final_continuous_hold_seconds':.5,'duration':'first-to-last qualifying control timestamps',
 'force_abort_n_gt':80.,'nonfinite_or_unexpected_termination_fails':True,'original_environment_termination_allowed':True,'primary':'valid final held pickup and no force abort','success_based_early_stop':False}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def evaluate(args,mode,checkpoint,seed):
    start=time.perf_counter();env=CurriculumEnv(args.task);reset=reset_visual_episode(env,seed,profile='rollout_development')
    rig=FixedCameraRig(env.model,env.data,env.qadr,env.vadr,seed=seed,augment=False)
    policy=VisualPolicy(checkpoint,device=args.device);policy.reset();checks=model_checks(env);assert checks['passed']
    initial=physical_state(env)['peg_z_m'];stable_since=None;longest=0.;ever=False;rows=[];actions=[];props=[];images=[];image_indices=[];last_image_time=None;error=None;final_duration=0.
    try:
        for step in range(THRESHOLDS['control_steps']):
            obs=rig.read(env.target,env.previous_action)
            if obs.image_time_s!=last_image_time:
                images.append(obs.rgb.copy());last_image_time=obs.image_time_s
            image_indices.append(len(images)-1);props.append(obs.proprio.copy())
            supplied={'rgb':np.zeros_like(obs.rgb) if mode=='blank_rgb' else obs.rgb,'proprio':obs.proprio}
            before=env.data.qpos.copy();action=policy.act(supplied)
            assert np.array_equal(before,env.data.qpos),'Student mutated simulator state'
            _,_,done,trunc,info=env.step(action);physical=physical_state(env);actions.append(action.copy())
            good=(physical['peg_z_m']-initial>=.020 and physical['left_force_n']>.02 and physical['right_force_n']>.02 and physical['nonfinger_support_force_n']<.01)
            if good:
                if stable_since is None:stable_since=physical['sim_time']
                final_duration=physical['sim_time']-stable_since;longest=max(longest,final_duration)
            else:stable_since=None;final_duration=0.
            valid=final_duration>=.5 and physical['peg_z_m']>=.065;ever=ever or valid
            rows.append({'step':step+1,**info,**physical,'sensor_time_s':obs.sensor_time_s,'image_time_s':obs.image_time_s,'qualified_duration_s':final_duration})
            # Only the fixed budget or original environment termination stops execution.
            if done or trunc:break
    except Exception as exc:error=repr(exc)
    final=rows[-1] if rows else {};force_abort=final.get('reason')=='force_limit';safe_termination=final.get('reason') in (None,'success','timeout')
    passed=bool(error is None and final_duration>=.5 and final.get('peg_z_m',0)>=.065 and not force_abort and safe_termination)
    stem=f'{mode}-seed-{seed}';(args.out/f'{stem}-trace.json').write_text(json.dumps(rows))
    np.savez_compressed(args.out/f'{stem}-sensors-actions.npz',images=np.asarray(images),image_index=np.asarray(image_indices),proprio=np.asarray(props),actions=np.asarray(actions))
    result={'mode':mode,'seed':seed,'passed':passed,'ever_validated_pickup':ever,'final_hold_seconds':final_duration,'longest_qualified_seconds':longest,
      'termination_reason':final.get('reason'),'max_rise_m':max((r['peg_z_m']-initial for r in rows),default=0.),'steps':len(rows),'final':final,'exception':error,'reset':reset,
      'camera_contract':rig.visual_sample,'model_checks':checks,'checkpoint_sha256':sha(checkpoint),'wall_seconds':time.perf_counter()-start}
    if mode=='trained_rgb' and seed==args.seed:
        import imageio.v2 as imageio
        from PIL import Image,ImageDraw
        writer=imageio.get_writer(args.out/f'{stem}-sensor-video.mp4',fps=25,codec='libx264',quality=7,macro_block_size=1)
        for n,rgb in enumerate(images):
            canvas=Image.new('RGB',(640,384),(12,24,36));draw=ImageDraw.Draw(canvas)
            draw.text((10,8),'Visual pickup candidate: actual fixed-camera sensor inputs',fill='white')
            draw.text((10,27),f'Seed {seed} | image time {n*.04:.2f}s | final pickup passed={passed}',fill='white')
            draw.text((10,44),'RGB + joint/controller feedback only; no runtime oracle or IK.',fill='white')
            canvas.paste(Image.fromarray(rgb[0]).resize((320,320)),(0,64));canvas.paste(Image.fromarray(rgb[1]).resize((320,320)),(320,64));writer.append_data(np.asarray(canvas))
        writer.close()
    rig.close();env.close();return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--initial-checkpoint',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--task',default='tasks/yam_contact_curriculum');p.add_argument('--device',default='auto')
    p.add_argument('--seed',type=int,default=21000);p.add_argument('--episodes',type=int,default=5);p.add_argument('--modes',nargs='+',default=['trained_rgb','blank_rgb','untrained'])
    a=p.parse_args();a.device=resolve_device(a.device);a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
    if a.seed<21000 or a.seed+a.episodes>22000:raise ValueError('This tool is for the reserved rollout-development namespace only')
    report={'scope':'Visual pickup only, not insertion/hardware transfer','thresholds':THRESHOLDS,'device':a.device,'task_hashes':task_hashes(a.task),
      'source_sha256':{path:sha(path) for path in [__file__,'src/astrafactory/vision_policy.py','src/astrafactory/deployable_observations.py','src/astrafactory/sensor_contract.py','src/astrafactory/contact_env.py','src/astrafactory/env.py']},'trials':[]}
    for mode in a.modes:
        if mode not in ('trained_rgb','blank_rgb','untrained'):raise ValueError(mode)
        checkpoint=a.initial_checkpoint if mode=='untrained' else a.checkpoint
        for seed in range(a.seed,a.seed+a.episodes):
            result=evaluate(a,mode,checkpoint,seed);report['trials'].append(result)
            print(json.dumps({k:result[k] for k in ['mode','seed','passed','ever_validated_pickup','steps','max_rise_m','exception']}),flush=True)
    report['summaries']={mode:{'successes':sum(t['passed'] for t in report['trials'] if t['mode']==mode),'episodes':sum(t['mode']==mode for t in report['trials'])} for mode in a.modes}
    (a.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['summaries']),flush=True)
if __name__=='__main__':main()
