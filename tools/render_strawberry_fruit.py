"""Render recorded MuJoCo fruit poses; no animation or orientation overrides."""
from pathlib import Path
import json
import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'assets/workcells/strawberry-specimen/fruit-study'
FONT='/System/Library/Fonts/Helvetica.ttc'


def text(im,title,subtitle):
    dr=ImageDraw.Draw(im);dr.rectangle((0,0,im.width,78),fill='#17251d')
    dr.text((18,12),title,font=ImageFont.truetype(FONT,24),fill='white')
    dr.text((18,46),subtitle,font=ImageFont.truetype(FONT,17),fill='#d1dfcd')
    return im


def setup(path,lookat,distance,az=115,el=-8):
    m=mujoco.MjModel.from_xml_path(str(path));d=mujoco.MjData(m)
    r=mujoco.Renderer(m,640,640);c=mujoco.MjvCamera();c.lookat[:]=lookat;c.distance=distance;c.azimuth=az;c.elevation=el
    return m,d,r,c


def frame(bundle,q):
    m,d,r,c=bundle;d.qpos[:]=q;mujoco.mj_forward(m,d);r.update_scene(d,c)
    return Image.fromarray(r.render())


def main():
    before=ROOT/'assets/workcells/strawberry-specimen/parametric-study/v13'
    after=P/'v14';tiles=[]
    for path,title,sub in [(before,'Previous attachment frame','Fruit axis was independent of its terminal stalk'),
                           (after,'Corrected material frame','Calyx follows stalk; gravity determines the settled pose')]:
        b=setup(path/'scene.xml',[0,-.045,.155],.31,110,-8)
        q=np.load(path/'rest/rollout.npz')['qpos'][-1];im=text(frame(b,q),title,sub)
        tiles.append(im);b[2].close()
    plate=Image.new('RGB',(1280,685),'#17251d');plate.paste(tiles[0],(0,0));plate.paste(tiles[1],(640,0))
    ImageDraw.Draw(plate).text((20,655),'Same masses, stalk stiffness and camera. Both images are gravity-settled simulations; mechanics uncalibrated.',font=ImageFont.truetype(FONT,18),fill='white')
    plate.save(P/'fruit-orientation-comparison.png')

    hypotheses=['elastic','history'];trials={};bundles={}
    for name in hypotheses:
        trials[name]=np.load(P/'release'/f'{name}-release'/'rollout.npz')
        bundles[name]=setup(P/'release/scene.xml',[0,-.043,.147],.49,110,-8)
    def movie_frame(sec):
        row=Image.new('RGB',(1280,706),'#17251d')
        for j,name in enumerate(hypotheses):
            z=trials[name];idx=int(np.argmin(abs(z['t']-sec)))
            im=frame(bundles[name],z['qpos'][idx])
            title='A · Original elastic rest shape' if name=='elastic' else 'B · Different rest shape + stiffness'
            label='Attached' if z['attachment_active'][idx] else 'Attachment released'
            text(im,title,f'{label} · t = {z["t"][idx]:.2f} s · real-time playback')
            row.paste(im,(640*j,0))
        dr=ImageDraw.Draw(row);dr.text((20,650),'Shared initial loaded pose. B assigns half the initial rotation to rest curvature and doubles truss stiffness.',font=ImageFont.truetype(FONT,19),fill='white')
        dr.text((20,679),'Sensitivity experiment, not calibrated growth. Release at 1 s; no blade/fracture simulation.',font=ImageFont.truetype(FONT,18),fill='#d1dfcd')
        return row
    with imageio.get_writer(P/'release-comparison.mp4',fps=30,codec='libx264',quality=8,macro_block_size=2) as w:
        for t in np.arange(0,4,1/30):w.append_data(np.array(movie_frame(t)))
    for t in [0,.99,1.1,1.3,2,3.9]:movie_frame(t).save(P/f'release-{t:.2f}.png')
    for b in bundles.values():b[2].close()

    fig,ax=plt.subplots(1,2,figsize=(12,4.3),layout='constrained')
    for name,color,label in [('elastic','#cc6440','A · original rest shape'),('history','#238172','B · rest-curvature / stiffness hypothesis')]:
        z=trials[name];c=np.load(P/'release'/f'{name}-control'/'rollout.npz');delta=(z['body_positions']-c['body_positions'])*1000
        ax[0].plot(z['t'],delta[:,0,2],color=color,label=label,lw=2)
        ax[1].plot(z['t'],np.linalg.norm(delta[:,4:7],axis=2).max(axis=1),color=color,label=label,lw=2)
    for a in ax:
        a.axvline(1,color='#666',linestyle='--',lw=1);a.set_xlabel('Time (s)');a.grid(alpha=.18);a.spines[['top','right']].set_visible(False)
    ax[0].set(title='Stalk tip rise after fruit release',ylabel='Height relative to uncut control (mm)')
    ax[1].set(title='Movement of the other three berries',ylabel='Largest displacement from uncut control (mm)')
    ax[0].legend(fontsize=8,loc='upper left');fig.suptitle('Same starting shape does not identify unloading behavior\nUncalibrated hypotheses; cut-tool forces and growth dynamics absent',fontsize=12)
    fig.savefig(P/'recoil-response.png',dpi=150);plt.close(fig)
    print(P/'release-comparison.mp4')


if __name__=='__main__':main()
