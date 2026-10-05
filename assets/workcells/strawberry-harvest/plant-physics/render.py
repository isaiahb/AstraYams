from pathlib import Path
import sys,json,numpy as np,mujoco,argparse
from types import SimpleNamespace
from PIL import Image,ImageDraw,ImageFont
import imageio.v2 as imageio
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'multi-harvest'))
from cel_style import apply_style,toon
p=argparse.ArgumentParser();p.add_argument('--tag',default='contact');p.add_argument('--video',action='store_true');a=p.parse_args();out=P/a.tag
m=mujoco.MjModel.from_xml_path(str(out/'scene.xml'));d=mujoco.MjData(m);apply_style(m);e=SimpleNamespace(model=m,data=d);z=np.load(out/'rollout.npz');r=mujoco.Renderer(m,600,1000)
c=mujoco.MjvCamera();c.lookat[:]=[.54,.145,.36];c.distance=.48;c.azimuth=100;c.elevation=-14
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',22)
def frame(i):
 d.qpos[:]=z['qpos'][i];mujoco.mj_forward(m,d);im=Image.fromarray(toon(r,e,c));dr=ImageDraw.Draw(im);dr.rectangle((0,0,1000,69),fill='#101d27');t=z['t'][i];phase='Gravity settling' if t<3 else 'Contact brush' if t<4.5 else 'Withdraw / branch recovery' if t<5.7 else 'Free response'
 dr.text((18,10),f'Plant physics candidate | {phase} | t={t:.2f}s',font=font,fill='white');dr.text((18,38),'Physical probe test · uncalibrated beam model · not a learned harvest',font=font,fill='white');return im
for sec in [0,3,4.2,5.6,8]:
 i=int(np.argmin(abs(z['t']-sec)));frame(i).save(out/f'frame-{sec}.png')
if a.video:
 with imageio.get_writer(out/'plant-response.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as writer:
  for i in range(len(z['t'])):writer.append_data(np.array(frame(i)))
r.close();print(out)
