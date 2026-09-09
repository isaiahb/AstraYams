"""Show actual support-study trajectories, contact load and matched controls."""
import argparse
import json
import re
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import render_strawberry_specimen as export_base

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'assets/workcells/strawberry-specimen/support-study/v2'
FONT='/System/Library/Fonts/Helvetica.ttc'


def render(p):
    z=np.load(p/'support/rollout.npz');control=np.load(p/'control/rollout.npz') if (p/'control/rollout.npz').exists() else None
    m=mujoco.MjModel.from_xml_path(str(p/'scene.xml'));d=mujoco.MjData(m)
    renderer=mujoco.Renderer(m,600,700);cam=mujoco.MjvCamera()
    weight=json.loads((p/'support/result.json').read_text())['weight_n']
    titlefont=ImageFont.truetype(FONT,26);font=ImageFont.truetype(FONT,20);small=ImageFont.truetype(FONT,17)
    def view(q,close=False,az=110):
        d.qpos[:]=q;mujoco.mj_forward(m,d)
        cam.lookat[:]=[-.008,-.032,.135] if close else [-.04,.012,.25]
        cam.distance=.20 if close else .80;cam.azimuth=az;cam.elevation=-12
        renderer.update_scene(d,cam);return Image.fromarray(renderer.render())
    def frame(sec):
        i=int(np.argmin(abs(z['t']-sec)));im=Image.new('RGB',(1400,850),'#17251d')
        im.paste(view(z['qpos'][i]),(0,82));im.paste(view(z['qpos'][i],True),(700,82))
        dr=ImageDraw.Draw(im);dr.text((22,12),'Intact strawberry · contact-driven support and recovery',font=titlefont,fill='white')
        dr.text((22,48),f'{z["phase"][i].upper()}   ·   {z["t"][i]:.2f} s / {z["t"][-1]:.0f} s   ·   real-time physics replay',font=font,fill='#d7e8d8')
        dr.rectangle((0,682,1400,850),fill='#17251d')
        for j,(label,force,color) in enumerate([('Cup carries',z['tool_force'][i,2],'#65c5d2'),('Stalk carries',z['stem_force'][i,2],'#cbd990')]):
            y=702+j*45;dr.text((22,y),f'{label}: {force:.3f} N  /  {100*force/weight:.0f}% of weight',font=font,fill='white')
            dr.rectangle((480,y+4,1110,y+23),fill='#34483b');dr.rectangle((480,y+4,480+630*np.clip(force/weight,0,1),y+23),fill=color)
        dr.text((22,806),'Actuated test stage, not a robot policy. Contact forces move the fruit. Tissue response and damage are uncalibrated.',font=small,fill='#d7e8d8')
        return im
    with imageio.get_writer(p/'support-review.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as writer:
        for t in np.arange(0,z['t'][-1],1/25):writer.append_data(np.asarray(frame(t)))
    for t in [0,2.8,6.9,9.,12.8]:frame(t).save(p/f'support-{t:.1f}.png')
    # Same physical instant, alternate cameras; no geometry edits for visibility.
    i=int(np.argmin(abs(z['t']-6.9)))
    for name,az in [('front',90),('side',0),('oblique',160)]:view(z['qpos'][i],True,az).save(p/f'contact-{name}.png')
    renderer.close()

    fig,axes=plt.subplots(1,3,figsize=(14,4.4),layout='constrained')
    axes[0].plot(z['t'],z['tool_force'][:,2],color='#177f93',label='Cup → fruit')
    axes[0].plot(z['t'],z['stem_force'][:,2],color='#718b26',label='Stalk → fruit')
    axes[0].axhline(weight,color='#777',ls='--',label='Fruit weight')
    axes[0].set(title='Measured load transfer',ylabel='Vertical force (N)')
    if control is not None:
        delta=(z['body_positions']-control['body_positions'])*1000
        axes[1].plot(z['t'],delta[:,1,2],label='Primary stalk tip',color='#177f93')
        axes[1].plot(z['t'],np.linalg.norm(delta[:,3:6],axis=2).max(axis=1),label='Largest neighbor displacement',color='#c47b47')
    axes[1].set(title='Response relative to no-contact control',ylabel='Displacement (mm)')
    axes[2].plot(z['t'],np.linalg.norm(z['tool_force'],axis=1),label='Tool resultant · 5 ms samples',color='#177f93')
    result=json.loads((p/'support/result.json').read_text())
    axes[2].axhline(result['peak_target_contact_force_n'],ls=':',color='#9e5139',label='Peak over every integration step')
    axes[2].axhline(.45,color='#666',ls='--',label='Predeclared numerical force budget')
    axes[2].set(title='Contact transition check',ylabel='Resultant force (N)')
    for ax in axes:
        ax.set_xlabel('Time (s)');ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=8)
    fig.suptitle('Contact support diagnostic · intact stalk · simulated, uncalibrated mechanics',fontsize=14)
    fig.savefig(p/'support-response.png',dpi=150);plt.close(fig)
    print(p/'support-review.mp4',flush=True)


def export(p):
    kinds=['support','control']
    for case in ['offset-plus2','offset-minus2']:
        if (p.parent/case/'support/rollout.npz').exists():
            if (p/'scene.xml').read_bytes()!=(p.parent/case/'scene.xml').read_bytes():
                raise RuntimeError('Offset replay cannot share meshes with a different scene')
            kinds.append('../'+case+'/support')
    export_base.P=p;export_base.export(kinds=kinds)
    html=(ROOT/'assets/workcells/strawberry-specimen/parametric-study/v13/index.html').read_text()
    html=re.sub(r'<title>.*?</title>','<title>Intact fruit · contact support study</title>',html)
    html=re.sub(r'<h1>.*?</h1>','<h1>Intact fruit · support &amp; recovery</h1>',html)
    html=re.sub(r'<nav aria-label="Physics recordings">.*?</nav>','<nav aria-label="Physics recordings"><button class="active" data-kind="support">Physical contact</button><button data-kind="control">Same commands · contact disabled control</button></nav>',html)
    buttons=''.join(f'<button data-kind="{kind}">Approach offset {"+2" if "plus" in kind else "−2"} mm</button>' for kind in kinds if kind.startswith('../'))
    html=html.replace('</nav>',buttons+'</nav>',1)
    html=html.replace('Multi-reference morphology hypothesis with age-dependent petiole mechanics.','An actuated bench stage takes part of the fruit’s weight and withdraws. The stalk remains attached. This is an uncalibrated test instrument, not a trained harvesting policy.')
    start=html.index("if(kind==='basal')");end=html.index('orbit.update();clock=',start)
    html=html[:start]+"orbit.target.set(-.02,-.02,.17);cam.position.set(.19,-.50,.24);"+html[end:]
    html=html.replace("document.getElementById('video').href=kind+'/demo.mp4'","document.getElementById('video').href='support-review.mp4'")
    start=html.index(' const hits=Object.keys(report.probe_contacts');end=html.index("document.getElementById('error').textContent='';",start)
    html=html[:start]+" document.getElementById('status').textContent=kind==='control'?'Negative control: instrument contacts disabled; the same motor commands pass through the fruit intentionally.':'Hold average: cup carries '+(report.mean_hold_support_fraction*100).toFixed(1)+'% of weight · episode peak contact '+report.peak_target_contact_force_n.toFixed(3)+' N · see comparison report for all checks';"+html[end:]
    html=html.replace("fetch('reference-graph.json')","fetch('../../fruit-study/v14/reference-graph.json')").replace("load('rest')","load('support')")
    html=html.replace('Crown detail','Contact close-up').replace("orbit.target.set(0,.055,.287);cam.position.set(.10,-.12,.355)","orbit.target.set(-.008,-.032,.135);cam.position.set(.07,-.20,.16)")
    html=html.replace("orbit.target.set(.02,.01,.29);cam.position.set(.02,-.74,.38)","orbit.target.set(-.04,.01,.20);cam.position.set(-.04,-.64,.27)")
    html=html.replace("orbit.target.set(.02,.01,.29);cam.position.set(.37,-.59,.51)","orbit.target.set(-.04,.01,.20);cam.position.set(.3,-.49,.4)")
    html=html.replace('Contact evidence','Trial measurements').replace('Open video recording','Central approach video').replace('<a href="README.md">','<a id="comparison" href="comparison.json">All checks</a><a href="support-response.png">Central load plots</a><a href="README.md">')
    html=html.replace("document.getElementById('report').href=kind+'/result.json';", "document.getElementById('report').href=kind+'/result.json';document.getElementById('comparison').href=kind.startsWith('../')?kind.replace(/\\/support$/,'/comparison.json'):'comparison.json';")
    html=html.replace("clock.toFixed(1)+' s'","clock.toFixed(1)+' s · '+(replay.frames[lo].phase||'')")
    # Attach actual recorded phase labels, keeping the shared body meshes.
    for kind in kinds:
        replay_path=p/kind/'replay.json';r=json.loads(replay_path.read_text());z=np.load(p/kind/'rollout.npz')
        for f in r['frames']:
            i=int(np.argmin(abs(z['t']-f['time'])));f['phase']=str(z['phase'][i])
        replay_path.write_text(json.dumps(r,separators=(',',':')))
    (p/'index.html').write_text(html)
    if not (p/'reference').exists():(p/'reference').symlink_to('../../reference',target_is_directory=True)
    print(p/'index.html',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=DEFAULT);parser.add_argument('--export',action='store_true');a=parser.parse_args()
    export(a.output.resolve()) if a.export else render(a.output.resolve())
