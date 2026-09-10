"""Review recorded constitutive experiments, without altered motion or geometry."""
import argparse
import json
import re
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from study_strawberry_recovery import P,BASE,HOLD_START,RETURN_DURATION

LABELS={'elastic':'A · Elastic + damping','relaxing':'B · Relaxing component','retained':'C · Rest curvature + 2× stiffness'}
COLORS={'elastic':'#286ea7','relaxing':'#c46f30','retained':'#718642'}
FONT='/System/Library/Fonts/Helvetica.ttc'
ROOT=Path(__file__).resolve().parents[1]


def render(hold,video=True):
    data={name:np.load(P/f'{name}-{hold}s/rollout.npz') for name in LABELS}
    m=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));d=mujoco.MjData(m);r=mujoco.Renderer(m,520,500);cam=mujoco.MjvCamera()
    font=ImageFont.truetype(FONT,22);small=ImageFont.truetype(FONT,17);large=ImageFont.truetype(FONT,26)
    def frame(sec):
        image=Image.new('RGB',(1500,722),'#18271f');draw=ImageDraw.Draw(image)
        draw.text((20,12),f'Same loaded shape · same commanded tool path · {hold}-second hold',font=large,fill='white')
        for j,name in enumerate(LABELS):
            z=data[name];i=int(np.argmin(abs(z['t']-sec)));d.qpos[:]=z['qpos'][i];mujoco.mj_forward(m,d)
            cam.lookat[:]=[-.008,-.035,.153];cam.distance=.245;cam.azimuth=110;cam.elevation=-10
            r.update_scene(d,cam);image.paste(Image.fromarray(r.render()),(j*500,87))
            draw.text((j*500+18,52),LABELS[name],font=font,fill='white')
            draw.text((j*500+18,622),f'Cup: {z["tool_force"][i,2]:.3f} N   |   Stalk: {z["stem_force"][i,2]:.3f} N',font=font,fill='white')
            draw.text((j*500+18,653),f'{z["t"][i]:.2f} s  ·  {z["phase"][i]}',font=small,fill='#d8e4d1')
        draw.text((20,691),'Actual simulated poses at 1× speed. All material hypotheses are uncalibrated. C also has doubled stiffness; no growth is simulated.',font=small,fill='#efcf98')
        return image
    duration=next(iter(data.values()))['t'][-1]
    for sec,label in [(0,'initial'),(HOLD_START+hold-.2,'held'),(HOLD_START+hold+2.4,'early-recovery'),(duration-.1,'late-recovery')]:frame(sec).save(P/f'{hold}s-{label}.png')
    if video:
        with imageio.get_writer(P/f'{hold}s-hold.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as writer:
            for sec in np.arange(0,duration,1/25):writer.append_data(np.asarray(frame(sec)))
    r.close();print(P/(f'{hold}s-hold.mp4' if video else f'{hold}s-held.png'),flush=True)


def plots():
    report=json.loads((P/'comparison.json').read_text());fig,axes=plt.subplots(3,2,figsize=(13,11),layout='constrained')
    for column,hold in enumerate([1,12]):
        for name,label in LABELS.items():
            z=np.load(P/f'{name}-{hold}s/rollout.npz');c=np.load(P/f'{name}-{hold}s-control/rollout.npz');r=json.loads((P/f'{name}-{hold}s/result.json').read_text())
            delta=(z['body_positions']-c['body_positions'])*1000;t=z['t'];after=t-r['last_contact_s'];color=COLORS[name]
            axes[0,column].plot(t,z['tool_force'][:,2],color=color,label=label,lw=1.7)
            visible=(after>=0)&(after<=15)
            axes[1,column].plot(after[visible],delta[visible,1,2],color=color,label=label,lw=1.7)
            axes[2,column].plot(after[visible],np.linalg.norm(delta[visible,3:6],axis=2).max(axis=1),color=color,label=label,lw=1.7)
        axes[0,column].axvspan(HOLD_START,HOLD_START+hold,color='#b5c1a1',alpha=.22)
        axes[0,column].set(title=f'{hold} s hold · contact-force response',ylabel='Cup vertical force (N)',xlabel='Episode time (s)')
        axes[1,column].set(title='Stalk-tip recovery after contact ends',ylabel='Height relative to matched control (mm)',xlabel='Time since last cup contact (s)',xlim=(0,15))
        axes[2,column].set(title='Coupled movement of neighboring berries',ylabel='Largest deviation from matched control (mm)',xlabel='Time since last cup contact (s)',xlim=(0,15))
    for row in [1,2]:
        low=min(ax.get_ylim()[0] for ax in axes[row]);high=max(ax.get_ylim()[1] for ax in axes[row])
        for ax in axes[row]:ax.set_ylim(low,high)
    for ax in axes.ravel():
        ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=8)
    fig.suptitle('Different constitutive laws can share the same loaded photograph\nSimulated hypotheses, not measured strawberry recovery',fontsize=16)
    fig.savefig(P/'recovery-comparison.png',dpi=150);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    t=np.linspace(0,150,1000)
    for hold,ax in zip([1,12],axes):
        for tau in [1,3,10,100]:
            retardation=2*tau;response=(1-np.exp(-hold/retardation))*np.exp(-t/retardation)
            ax.plot(t,response,label=f'Relaxation time {tau} s (assumed)')
        ax.axvspan(0,15,color='#becdad',alpha=.2);ax.set(title=f'Ideal scalar material · {hold} s load pulse',xlabel='Time after load removal (s)',ylabel='Recoverable residual / initial elastic deflection')
        ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=8)
    fig.suptitle('A short observation window cannot establish permanent set\nAnalytical one-joint sensitivity; these are not measured plant curves',fontsize=13)
    fig.savefig(P/'observation-window.png',dpi=150);plt.close(fig)
    print(P/'recovery-comparison.png',flush=True)


def export():
    template=ROOT/'assets/workcells/strawberry-specimen/parametric-study/v13/index.html'
    source=json.loads((BASE/'support/replay.json').read_text())
    # The old isolated-push probe is collision-disabled in every trial and
    # unrelated to this instrument. Omit it from the exported review geometry.
    source['objects']=[o for o in source['objects'] if o['body']!='probe']
    m=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));d=mujoco.MjData(m)
    initial=np.load(P/'initial-state.npz');d.qpos[:]=initial['qpos'];mujoco.mj_kinematics(m,d)
    scene=trimesh.Scene()
    for i,o in enumerate(source['objects']):
        g=trimesh.load(ROOT/o['mesh_path'],force='mesh');bid=m.body(o['body']).id
        transform=np.eye(4);transform[:3,:3]=d.xmat[bid].reshape(3,3);transform[:3,3]=d.xpos[bid]
        color=o['color'];g.visual.vertex_colors=[(color>>16)&255,(color>>8)&255,color&255,255]
        scene.add_geometry(g,node_name=f'{o["body"]}-{i}',transform=transform)
    scene.export(P/'initial-scene.glb')
    cases=[f'{name}-{hold}s' for hold in [1,12] for name in LABELS]
    for case in cases:
        z=np.load(P/case/'rollout.npz');frames=[]
        for i in range(0,len(z['t']),2):
            d.qpos[:]=z['qpos'][i];mujoco.mj_kinematics(m,d)
            bodies={m.body(j).name or 'world':dict(position=d.xpos[j].round(8).tolist(),quaternion=d.xquat[j][[1,2,3,0]].round(8).tolist()) for j in range(m.nbody)}
            frames.append(dict(time=float(z['t'][i]),phase=str(z['phase'][i]),bodies=bodies))
        replay=dict(source);replay.update(frames=frames,scope='Recorded contact with alternative uncalibrated material laws; no pose animation overrides. Shared body-local meshes are unchanged.')
        (P/case/'replay.json').write_text(json.dumps(replay,separators=(',',':')))
    html=template.read_text()
    html=re.sub(r'<title>.*?</title>','<title>Stalk recovery · material hypotheses</title>',html)
    html=re.sub(r'<h1>.*?</h1>','<h1>Stalk recovery · material hypotheses</h1>',html)
    comparison=P/'comparison.json'
    accepted=comparison.exists() and json.loads(comparison.read_text())['all_checks_pass']
    notice=('Numerical checks passed. These material laws remain uncalibrated.' if accepted else 'NOT ACCEPTED: baseline/control checks failed or are incomplete. Preserve as diagnostic evidence.')
    html=html.replace('</header>','</header><p role="status" style="padding:12px;border:1px solid #ba883f">'+notice+'</p>')
    html=re.sub(r'<nav aria-label="Physics recordings">.*?</nav>','<nav aria-label="Physics recordings">'+''.join(f'<button data-kind="{case}"'+(' class="active"' if case=='elastic-1s' else '')+'>'+LABELS[case.split('-')[0]]+' · '+case.split('-')[1]+' hold</button>' for case in cases)+'</nav>',html)
    html=html.replace('Multi-reference morphology hypothesis with age-dependent petiole mechanics.','Compare 1 s and 12 s holds using identical commanded tool paths and a shared loaded plant shape. B adds an uncalibrated relaxing component; C changes pre-existing rest curvature AND stiffness. No measured strawberry recovery curve has been fitted.')
    html=html.replace('href="specimen-settled.glb"','href="initial-scene.glb"').replace('Download 3D specimen (.glb)','Download initial 3D scene (.glb)')
    html=html.replace('<a href="README.md">Assumptions & methodology</a>','<a href="comparison.json">All checks</a><a href="recovery-comparison.png">Recovery plots</a><a href="research.md">Research & unknowns</a><a href="README.md">Methodology</a>')
    start=html.index("if(kind==='basal')");end=html.index('orbit.update();clock=',start)
    html=html[:start]+"orbit.target.set(-.008,-.03,.15);cam.position.set(.10,-.35,.20);"+html[end:]
    html=html.replace("document.getElementById('video').href=kind+'/demo.mp4'","document.getElementById('video').href=kind.split('-')[1]+'-hold.mp4'")
    start=html.index(' const hits=Object.keys(report.probe_contacts');end=html.index("document.getElementById('error').textContent='';",start)
    html=html[:start]+" document.getElementById('status').textContent=report.material+' · '+report.hold_s+' s hold · peak contact '+report.peak_target_contact_n.toFixed(3)+' N · uncalibrated material hypothesis';"+html[end:]
    html=html.replace('Crown detail','Contact close-up').replace("orbit.target.set(0,.055,.287);cam.position.set(.10,-.12,.355)","orbit.target.set(-.008,-.032,.15);cam.position.set(.07,-.20,.17)")
    html=html.replace("fetch('reference-graph.json')","fetch('../../fruit-study/v14/reference-graph.json')").replace("load('rest')","load('elastic-1s')")
    html=html.replace("clock.toFixed(1)+' s'","clock.toFixed(1)+' s · '+(replay.frames[lo].phase||'')")
    (P/'index.html').write_text(html)
    if not (P/'reference').exists():(P/'reference').symlink_to('../../reference',target_is_directory=True)
    print(P/'index.html',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['render','preview','plots','export']);p.add_argument('--hold',type=int,default=1);a=p.parse_args()
    if a.stage=='render':render(a.hold)
    elif a.stage=='preview':render(a.hold,False)
    elif a.stage=='plots':plots()
    else:export()
