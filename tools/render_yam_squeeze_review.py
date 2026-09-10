"""Render every saved continuous trial by replaying actions through physics."""
import argparse,hashlib,json
from pathlib import Path
import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mujoco,numpy as np
from PIL import Image,ImageDraw,ImageFont
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.squeeze_skill import squeeze_score
from astrafactory.grip_regulation import TASK


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def render_trial(run,trial,out):
    seed=trial['seed'];source=run/f'chain-{seed}.npz';saved=np.load(source)
    trace=json.loads((run/f'chain-{seed}.json').read_text())['trace']
    e=CurriculumEnv(TASK)
    if trial.get('domain_randomization'):
        from astrafactory.skill_randomization import SkillRandomization
        sample=trial['domain_randomization']
        _,actual=SkillRandomization(e,sample['profile'],'stress').reset(seed=seed,domain_seed=sample['domain_seed'])
        assert actual['domain_randomization']==sample
    else:e.reset(seed=seed)
    renderer=mujoco.Renderer(e.model,height=360,width=540)
    cam=mujoco.MjvCamera();cam.azimuth=135;cam.elevation=-24;cam.distance=.29
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
    small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',15)
    max_q=0.;max_f=0.;selected={0,len(trace)-1}
    for phase in ('reach','close','lift'):
        ids=[i for i,x in enumerate(trace) if x['phase']==phase]
        if ids:selected.add(ids[len(ids)//2])
    frames=[];thumbs=[];goal=trial['goal_n'];duration=trace[-1]['time']
    video=out/f'chain-{seed}.mp4'
    with imageio.get_writer(video,fps=25,codec='libx264',quality=7,macro_block_size=2) as writer:
        for i,action in enumerate(saved['actions']):
            e.step(action);s=squeeze_score(e,goal)
            max_q=max(max_q,float(np.max(abs(e.data.qpos-saved['qpos'][i]))))
            max_f=max(max_f,abs(s['load_n']-trace[i]['load_n']))
            if i%2 and i not in selected:continue
            renderer.update_scene(e.data,camera='overview');full=Image.fromarray(renderer.render())
            cam.lookat[:]=e.data.site_xpos[e.task.pid]+np.array([0,0,.035])
            renderer.update_scene(e.data,camera=cam);close=Image.fromarray(renderer.render())
            frame=Image.new('RGB',(1080,612),(17,27,35));frame.paste(full,(0,86));frame.paste(close,(540,86))
            draw=ImageDraw.Draw(frame)
            draw.text((14,9),'YAM | 401-parameter PPO jaw controller | actual saved-action physics replay',font=font,fill='white')
            draw.text((14,35),'Approach/lift: existing BC + IK. Jaw: new PPO. Transitions: scripted guards. No object attachment.',font=small,fill='#b8cad5')
            draw.text((14,60),f'Seed {seed}   {trace[i]["phase"].upper()}   {trace[i]["time"]:.2f}s   requested squeeze {goal:.1f} N   measured {s["load_n"]:.2f} N',font=small,fill='#b3e6ca')
            left,right,top,bottom=60,1030,474,574
            y=lambda f:bottom-min(8,max(0,f))/8*(bottom-top)
            x=lambda t:left+t/duration*(right-left)
            draw.rectangle((left,y(goal*1.2),right,y(goal*.8)),fill='#244439')
            draw.line((left,y(goal),right,y(goal)),fill='#88c6a6',width=1)
            pts=[(x(v['time']),y(v['load_n'])) for v in trace[:i+1]]
            if len(pts)>1:draw.line(pts,fill='#72bbff',width=2)
            draw.line((x(trace[i]['time']),top,x(trace[i]['time']),bottom),fill='white',width=1)
            draw.text((10,453),'Net axial squeeze (N)',font=small,fill='white')
            draw.text((15,top),'8',font=small,fill='#abc3d0');draw.text((15,bottom-12),'0',font=small,fill='#abc3d0')
            draw.text((60,588),'Playback 1x | blue: net squeeze | green: +/-20% goal band | simulated rigid part, not hardware validation',font=small,fill='#abc3d0')
            if i%2==0:writer.append_data(np.asarray(frame))
            if i in selected:thumbs.append(frame.copy())
            if i==len(trace)-1:frame.save(out/f'chain-{seed}-final.png')
    renderer.close();e.close()
    assert max_q<1e-8 and max_f<1e-8,(max_q,max_f)
    sheet=Image.new('RGB',(1080,306*((len(thumbs)+1)//2)),(17,27,35))
    for i,im in enumerate(thumbs):sheet.paste(im.resize((540,306)),((i%2)*540,(i//2)*306))
    sheet.save(out/f'chain-{seed}-contact-sheet.jpg',quality=90)
    return dict(seed=seed,max_qpos_error=max_q,max_load_error_n=max_f,source_sha256=sha(source),video=video.name,
                source_steps=len(trace),duration_s=duration,playback_speed=1.,passed=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    report=json.loads((a.run/'report.json').read_text());out=a.run/'review';out.mkdir(exist_ok=True)
    audits=[render_trial(a.run,r,out) for r in report['continuous_chains']]
    plt.style.use('dark_background');fig,axes=plt.subplots(3,1,figsize=(10,8),layout='constrained')
    for ax,r in zip(axes,report['continuous_chains']):
        t=json.loads((a.run/f"chain-{r['seed']}.json").read_text())['trace'];times=[x['time'] for x in t]
        ax.axhspan(r['goal_n']*.8,r['goal_n']*1.2,color='#4da879',alpha=.25)
        ax.plot(times,[x['load_n'] for x in t],color='#73baff',label='Net squeeze')
        ax.axhline(r['goal_n'],color='#a8d5bb',lw=1,ls='--')
        for h in r['handoffs']:ax.axvline(h['time'],color='white',alpha=.4,ls=':');ax.text(h['time']+.05,6.8,h['phase'],fontsize=9)
        ax.set(ylim=(0,8),ylabel='Net squeeze (N)',title=f"Seed {r['seed']} | lift handoff: {r['handoff_success']} | final force in band: {r['final_load_in_band']}")
    axes[-1].set_xlabel('Simulated seconds (no reset between skills)')
    fig.suptitle('Tiny policy composition: approach → regulate grip → lift\nNew PPO controls the jaw; existing BC, IK and guards control the rest',fontsize=14)
    fig.savefig(out/'handoff-evidence.png',dpi=140);plt.close(fig)
    (out/'audit.json').write_text(json.dumps(dict(source_report_sha256=sha(a.run/'report.json'),renderer_sha256=sha(__file__),audits=audits),indent=2))
    b=report['holdout_baseline_successes'];n=report['holdout_candidate_successes'];f=report['holdout_feedback_successes']
    cards=''.join(f'<article><h2>Continuous trial {r["seed"]}</h2><p>Lift handoff: {r["handoff_success"]}. Final squeeze in band: {r["final_load_in_band"]}.</p><video controls preload="metadata" poster="chain-{r["seed"]}-final.png" src="chain-{r["seed"]}.mp4"></video></article>' for r in report['continuous_chains'])
    html='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>YAM tiny-policy experiment</title><style>body{margin:40px auto;max-width:1100px;padding:0 20px;background:#111b23;color:#edf4f7;font:17px/1.6 system-ui}h1{font-size:36px}h2{font-size:22px}article{padding:20px 0;border-top:1px solid #385061}video,img{width:100%;border-radius:10px}a{color:#93caff}.metrics{padding:18px;background:#213340;border-radius:8px}small{color:#b8cad5}</style>'''
    html+=f'<h1>A small controller, tested inside the real chain</h1><p>A 401-parameter PPO actor regulates axial jaw squeeze at 50 Hz. The YAM mesh, free object, articulated jaws, friction and motor limits come from the existing contact simulation.</p><p class="metrics">Untouched isolated trials: PPO <b>{n}/12</b> · constant jaw <b>{b}/12</b> · engineered effort feedback <b>{f}/12</b>. Promotion gate: <b>{report["promoted"]}</b>.</p><p>These clips replay saved actions through the physics engine and compare every resulting pose and squeeze value against the original rollout. All three continuous trials are shown. Playback is real time.</p>'
    html+='<p><b>What is learned:</b> jaw target increments from jaw encoders, command, simulated motor effort and requested squeeze. <b>What is engineered:</b> existing approach/lift targets, IK, phase selection and contact guards. This is not vision control, strawberry handling, or a physical-arm result. The simple feedback baseline matters; successful PPO does not establish an advantage over it.</p>'
    html+=cards+'<h2>Every handoff, on one time axis</h2><img src="handoff-evidence.png"><p><a href="../report.json">Full report</a> · <a href="audit.json">Replay audit</a> · <a href="../proposal.json">Predeclared task and evaluation</a> · <a href="../../yam-grip-ppo-v1/report.json">Rejected first experiment</a></p><small>The first trial optimized a different, unsuitable force-magnitude sum. It remains rejected. Disk exhaustion interrupted the second trial; resumption details are preserved alongside its report.</small>'
    html=html.replace('A small controller, tested inside the real chain','YAM · tiny skill pilot')
    start=html.index('<p>These clips');end=html.index('<article>',start);detail=html[start:end]
    html=html[:start]+html[end:]
    html=html.replace('<h2>Every handoff, on one time axis</h2>','<details><summary>What is learned, and what is engineered?</summary>'+detail+'</details><h2>Every handoff, on one time axis</h2>')
    if (a.run/'stress/report.json').exists():
        stress=json.loads((a.run/'stress/report.json').read_text())['methods']
        html=html.replace('Promotion gate: <b>True</b>.',f'Simulation gate passed. Broader stress chains: PPO <b>{stress["ppo"]["successes"]}/12</b>, feedback <b>{stress["feedback"]["successes"]}/12</b>, constant jaw <b>{stress["fixed"]["successes"]}/12</b>.')
        html=html.replace(' · <a href="audit.json">Replay audit</a>',' · <a href="audit.json">Replay audit</a> · <a href="../mechanics-audit.json">500 Hz mechanics audit</a> · <a href="../stress/report.json">Unseen-condition tests</a>')
    (out/'index.html').write_text(html);print(json.dumps(audits),flush=True)

if __name__=='__main__':main()
