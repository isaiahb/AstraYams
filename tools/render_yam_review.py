"""Two-camera presentation of logged physics states; does not alter trajectories."""
from pathlib import Path
import argparse,json
import numpy as np
import mujoco
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from astrafactory.yam_env import YamEnv

p=argparse.ArgumentParser();p.add_argument('--recording',type=Path,required=True);p.add_argument('--label',default='Scripted controller — physics validation');p.add_argument('--out',type=Path,required=True)
a=p.parse_args();states=json.loads((a.recording/'states.json').read_text());result=json.loads((a.recording/'result.json').read_text())
root=Path(__file__).resolve().parents[1];e=YamEnv(root/'tasks/yam_keyed_insertion');e.reset(seed=result.get('seed',0))
a.out.mkdir(parents=True,exist_ok=True)
renderer=mujoco.Renderer(e.model,height=720,width=960)
with imageio.get_writer(a.out/'review.mp4',fps=25,codec='libx264',quality=8) as writer:
 for index,state in enumerate(states[::2]):
  e.data.qpos[:]=state['qpos'];e.data.qvel[:]=state['qvel'];mujoco.mj_forward(e.model,e.data)
  canvas=Image.new('RGB',(1920,800),(17,25,35))
  for j,camera in enumerate(['overview','insertion']):
   renderer.update_scene(e.data,camera=camera);canvas.paste(Image.fromarray(renderer.render()),(960*j,80))
  d=ImageDraw.Draw(canvas);d.text((24,12),'ASTRAFACTORY  /  YAM  /  CUSTOM KEYED INSERTION',fill='white',font_size=25)
  d.text((24,47),a.label,fill=(193,211,227),font_size=19)
  d.text((1000,15),f"t={state['sim_time']:.2f}s  |  XY error {state['xy_error_m']*1000:.2f} mm  |  contact {state['peak_contact_force_n']:.1f} N",fill='white',font_size=20)
  d.text((1000,47),'Same physics rollout · Full arm / interface detail',fill=(193,211,227),font_size=19)
  writer.append_data(np.asarray(canvas))
  if index==0:canvas.save(a.out/'start.png')
 canvas.save(a.out/'end.png')
(a.out/'source.json').write_text(json.dumps({'recording':str(a.recording),'label':a.label,'result':result},indent=2))
renderer.close();e.close()
