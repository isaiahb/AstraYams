"""Audit and render exact saved micro-composition actions; never infer new actions."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import mujoco
import imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.skill_randomization import SkillRandomization
from check_yam_contact import physical_state,model_checks
from collect_demonstrations import task_hashes


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def render_trial(task,run_dir,trial,out,stride=4):
    seed=trial['seed'];source=run_dir/f'seed-{seed}-actions.npz';trace=run_dir/f'seed-{seed}-trace.json'
    actions=np.load(source)['actions'];original=json.loads(trace.read_text())
    if len(actions)!=len(original):raise ValueError('Action/trace count mismatch')
    env=CurriculumEnv(task)
    if trial.get('domain_randomization'):
        sample=trial['domain_randomization']
        _,reset_info=SkillRandomization(env,sample['profile'],'stress').reset(seed=seed,domain_seed=sample['domain_seed'])
        if reset_info['domain_randomization']!=sample:raise ValueError('Stress reset sample mismatch')
    else:env.reset(seed=seed)
    static=model_checks(env);assert static['passed']
    renderer=mujoco.Renderer(env.model,height=360,width=540)
    cam=mujoco.MjvCamera();cam.azimuth=135;cam.elevation=-24;cam.distance=.29
    try:font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
    except OSError:font=ImageFont.load_default()
    dt=env.model.opt.timestep*env.frame_skip
    video_path=out/f'seed-{seed}-replay.mp4'
    writer=imageio.get_writer(video_path,fps=1/(stride*dt),codec='libx264',quality=7,macro_block_size=1)
    max_error={};mismatches=[];qpos=[];qvel=[];frames={};replayed=[]
    stages={r['phase'] for r in original}
    selected={0,len(original)-1}
    for phase in sorted(stages):
        indices=[i for i,r in enumerate(original) if r['phase']==phase]
        selected.update([indices[0],indices[len(indices)//2]])
    try:
        for index,(action,old) in enumerate(zip(actions,original)):
            _,_,done,trunc,info=env.step(action)
            actual={**info,**physical_state(env)}
            for key,value in old.items():
                if key in ('phase','step','peg_contacts'):continue
                if key not in actual:continue
                if isinstance(value,(float,int)) and not isinstance(value,bool):
                    difference=abs(float(value)-float(actual[key]));max_error[key]=max(max_error.get(key,0.),difference)
                elif value!=actual[key]:mismatches.append({'step':index+1,'key':key,'expected':value,'actual':actual[key]})
            replayed.append(actual);qpos.append(env.data.qpos.copy());qvel.append(env.data.qvel.copy())
            if index%stride==0 or index in selected or index==len(actions)-1:
                renderer.update_scene(env.data,camera='overview');full=renderer.render().copy()
                cam.lookat[:]=env.data.site_xpos[env.task.pid]+np.array([0,0,.035])
                renderer.update_scene(env.data,camera=cam);close=renderer.render().copy()
                frame=Image.new('RGB',(1080,448),(12,23,32));frame.paste(Image.fromarray(full),(0,88));frame.paste(Image.fromarray(close),(540,88))
                draw=ImageDraw.Draw(frame)
                draw.text((12,7),'Learned micro-policy composition | privileged state | exact saved-action replay',font=font,fill='white')
                draw.text((12,31),'Learned grasp XYZ/jaw + align/insert corrections; scripted targets, guards, IK, angular/grip hold.',font=font,fill=(196,218,230))
                draw.text((12,56),f"Seed {seed} | {old['phase']} | t={env.data.time:.2f}s | tip={actual['peg_z_m']*1000:.1f}mm | success={actual['is_success']}",font=font,fill=(255,209,110))
                if index%stride==0 or index==len(actions)-1:writer.append_data(np.asarray(frame))
                if index in selected:frames[index]=frame
            if (done or trunc) and index!=len(actions)-1:raise ValueError('Replay terminated before original action sequence')
    finally:writer.close();renderer.close();env.close()
    passed=not mismatches and all(value<=1e-8 for value in max_error.values())
    # Original trace lacks full qpos/qvel, so these are new replay evidence only.
    np.savez_compressed(out/f'seed-{seed}-replay-state.npz',qpos=qpos,qvel=qvel)
    keys=sorted(frames);thumbs=[frames[k].resize((540,224)) for k in keys]
    sheet=Image.new('RGB',(1080,224*((len(thumbs)+1)//2)),(8,18,27))
    for n,thumb in enumerate(thumbs):sheet.paste(thumb,((n%2)*540,(n//2)*224))
    sheet.save(out/f'seed-{seed}-contact-sheet.jpg',quality=92)
    report={'seed':seed,'original_success':trial['is_success'],'replay_success':replayed[-1]['is_success'],
            'exact_telemetry_within_1e_minus8':passed,'max_absolute_numeric_errors':max_error,'categorical_mismatches':mismatches,
            'qpos_comparison':'Unavailable: original runner did not save full qpos/qvel. Replayed arrays are preserved, not independently compared.',
            'action_sha256':sha(source),'trace_sha256':sha(trace),'action_count':len(actions),'model_checks':static,
            'video':str(video_path),'contact_sheet':str(out/f'seed-{seed}-contact-sheet.jpg'),
            'selected_frame_steps':[k+1 for k in keys],'final':replayed[-1]}
    (out/f'seed-{seed}-audit.json').write_text(json.dumps(report,indent=2))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--task',default='tasks/yam_contact_curriculum')
    p.add_argument('--stride',type=int,default=4);p.add_argument('--seed',type=int)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=json.loads((a.run_dir/'report.json').read_text())
    if task_hashes(a.task)!=source['task_hashes']:raise ValueError('Task assets/provenance changed since source rollout')
    trials=sorted(source['trials'],key=lambda t:t['seed']);chosen=[]
    if a.seed is not None:chosen=[t for t in trials if t['seed']==a.seed]
    else:
        for success in (True,False):
            matching=[t for t in trials if t['is_success']==success]
            if matching:chosen.append(matching[0])
    if not chosen:raise ValueError('No matching source trial')
    audits=[render_trial(a.task,a.run_dir,t,a.out,a.stride) for t in chosen]
    result={'source_report_sha256':sha(a.run_dir/'report.json'),'renderer_sha256':sha(__file__),
            'selection':'first success and first failure in sorted seed order, when each exists' if a.seed is None else 'explicit seed',
            'source_successes':source['successes'],'source_episodes':source['episodes'],'audits':audits,
            'limitations':'Exact action replay of simulator evidence. No new policy inference, physics changes, camera-policy or hardware claim.'}
    (a.out/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ['source_successes','source_episodes']}),flush=True)
    if not all(r['exact_telemetry_within_1e_minus8'] for r in audits):raise SystemExit('Replay mismatch: inspect audit before using video')
if __name__=='__main__':main()
