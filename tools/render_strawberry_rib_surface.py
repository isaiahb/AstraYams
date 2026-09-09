"""Render recorded deforming contact vertices through MuJoCo, with a matched control."""
from pathlib import Path
import json
import mujoco,numpy as np,imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'assets/workcells/strawberry-specimen/leaf-study/rib-surface-v2'
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',19)
models={kind:mujoco.MjModel.from_xml_path(str(P/'scene.xml')) for kind in ['contact','control']}
data={kind:mujoco.MjData(m) for kind,m in models.items()}
logs={kind:np.load(P/kind/'rollout.npz') for kind in models}
renderers={kind:mujoco.Renderer(m,560,720) for kind,m in models.items()}
cam=mujoco.MjvCamera();cam.lookat[:]=[.047,0,.142];cam.distance=.205;cam.azimuth=120;cam.elevation=-38
def frame(sec):
    parts=[]
    for kind in models:
        log=logs[kind];i=int(np.argmin(abs(log['t']-sec)));d=data[kind];d.qpos[:]=log['qpos'][i];mujoco.mj_forward(models[kind],d)
        # The recorded shared vertices must equal the renderer's reconstruction.
        if not np.allclose(d.flexvert_xpos,log['vertices'][i],atol=.0001):
            raise RuntimeError('Recorded and replayed deforming surface disagree')
        renderer=renderers[kind];renderer.update_scene(d,cam);im=Image.fromarray(renderer.render());dr=ImageDraw.Draw(im)
        dr.rectangle((0,0,720,74),fill='#17251d');dr.text((16,10),'Continuous surface / physical probe' if kind=='contact' else 'Matched no-contact control',font=font,fill='white');dr.text((16,39),f't = {log["t"][i]:.2f}s · articulated ribs + constrained shared surface',font=font,fill='#cbdcc8')
        dr.rectangle((0,523,720,560),fill='#17251d');dr.text((16,532),'Isolated diagnostic · uncalibrated · not yet in the whole plant',font=font,fill='white');parts.append(np.array(im))
    return np.concatenate(parts,axis=1)
with imageio.get_writer(P/'contact-and-control.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as writer:
    for t in np.arange(.00025,4.8,.04):writer.append_data(frame(t))
for sec in [.8,1.8,2.3,4.7]:Image.fromarray(frame(sec)).save(P/f'phase-{sec}.png')
for rr in renderers.values():rr.close()
print(P/'contact-and-control.mp4')
