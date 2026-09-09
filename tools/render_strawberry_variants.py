"""Same contact protocol on three separately generated, recorded specimens."""
from pathlib import Path
import mujoco,numpy as np,imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1]/'assets/workcells/strawberry-specimen/parametric-study'
names=['v13','v13-holdout-41','v13-holdout-73'];labels=['Representative / 0° approach','Held-out seed 41 / −25° approach','Held-out seed 73 / +25° approach']
ms=[mujoco.MjModel.from_xml_path(str(P/n/'scene.xml')) for n in names];ds=[mujoco.MjData(m) for m in ms];logs=[np.load(P/n/'leaf/rollout.npz') for n in names]
rs=[mujoco.Renderer(m,560,640) for m in ms];cams=[];font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18)
for m,d,z in zip(ms,ds,logs):
    d.qpos[:]=z['qpos'][0];mujoco.mj_forward(m,d);cam=mujoco.MjvCamera();cam.lookat[:]=d.geom_xpos[m.geom('leaf_left_1_w14_-1').id]+[0,0,.015];cam.distance=.24;cam.azimuth=175;cam.elevation=-35;cams.append(cam)
def frame(t):
    images=[]
    for m,d,z,r,cam,label in zip(ms,ds,logs,rs,cams,labels):
        i=int(np.argmin(abs(z['t']-t)));d.qpos[:]=z['qpos'][i];mujoco.mj_forward(m,d);r.update_scene(d,cam);im=Image.fromarray(r.render());dr=ImageDraw.Draw(im)
        dr.rectangle((0,0,640,72),fill='#17251d');dr.text((16,12),label,font=font,fill='white');dr.text((16,40),f't = {z["t"][i]:.2f}s · physical probe / uncalibrated plant',font=font,fill='#cbdcc8');images.append(np.array(im))
    return np.concatenate(images,axis=1)
with imageio.get_writer(P/'variation-leaf-probes.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as writer:
    for t in np.arange(.000125,4,.04):writer.append_data(frame(t))
Image.fromarray(frame(1.6)).save(P/'variation-contact.png')
for r in rs:r.close()
print(P/'variation-leaf-probes.mp4')
