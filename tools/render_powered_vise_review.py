"""Visual-only powered-vise review, replaying unchanged recorded physical states."""
import argparse,json
from pathlib import Path
import imageio.v2 as imageio,mujoco,numpy as np
from PIL import Image,ImageDraw,ImageFont
from astrafactory.machine_tending import MachineTendingEnv
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=Path('runs/machine-seating-ppo-v1'));p.add_argument('--seed',type=int,default=58000);a=p.parse_args();font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
out=a.run/'visual-review';out.mkdir(exist_ok=True)
for mode in ['baseline','candidate']:
 data=np.load(a.run/f'{mode}-{a.seed}.npz');report=json.loads((a.run/f'{mode}-{a.seed}.json').read_text());e=MachineTendingEnv();e.reset(seed=a.seed);e.model=mujoco.MjModel.from_xml_path('tasks/yam_machine_tending/scene_visual.xml');e.data=mujoco.MjData(e.model);renderer=mujoco.Renderer(e.model,height=360,width=540);camera=mujoco.MjvCamera();camera.lookat[:]=[.28,0,.06];camera.distance=.38;camera.azimuth=135;camera.elevation=-30
 with imageio.get_writer(out/f'{mode}-{a.seed}.mp4',fps=12.5,codec='libx264',quality=7,macro_block_size=1) as writer:
  for k in list(range(3250,len(data['qpos']),4)) + [len(data['qpos'])-1]*13:
   # Playback recorded simulator states only; these assignments are not policy actions.
   e.data.qpos[:]=data['qpos'][k];mujoco.mj_forward(e.model,e.data);renderer.update_scene(e.data,camera='overview');left=renderer.render().copy();renderer.update_scene(e.data,camera=camera);right=renderer.render().copy();im=Image.new('RGB',(1080,448),(12,23,32));im.paste(Image.fromarray(left),(0,88));im.paste(Image.fromarray(right),(540,88));d=ImageDraw.Draw(im);row=report['trace'][k]
   d.text((12,8),f"Machine tending | {mode} | seed {a.seed} | {row['phase']}",font=font,fill='white');d.text((12,34),'Powered vise | scripted '+('CLOSE command' if row['vise_target_gap_m']<.02 else 'OPEN command')+' | actuator forces drive the jaw',font=font,fill=(196,218,230));d.text((12,60),f"Recorded physics | visual-only hardware detail | t={row['sim_time']:.2f}s | success={row['is_success']}",font=font,fill=(255,209,110));writer.append_data(np.asarray(im))
 renderer.close();e.close()
