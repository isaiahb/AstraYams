"""Replay recorded policy commands through unchanged physics for a close-up diagnosis."""
import argparse
from pathlib import Path
import json
import os
os.environ.setdefault('MUJOCO_GL','egl')
import numpy as np
import mujoco
import imageio.v2 as imageio
from PIL import Image, ImageDraw
from astrafactory.contact_curriculum import CurriculumEnv

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--actions',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True)
 p.add_argument('--task',default='tasks/yam_contact_curriculum')
 p.add_argument('--seed',type=int,default=2000)
 p.add_argument('--max-steps',type=int,default=400)
 args=p.parse_args()
 actions=np.load(args.actions)['executed']
 env=CurriculumEnv(args.task);env.reset(seed=args.seed)
 renderer=mujoco.Renderer(env.model,height=480,width=640)
 args.out.mkdir(parents=True,exist_ok=True)
 records=[]
 writer=imageio.get_writer(args.out/'failed-pickup-closeup.mp4',fps=25,codec='libx264',quality=7)
 try:
  for i,action in enumerate(actions[:args.max_steps]):
   _,_,done,truncated,info=env.step(action)
   records.append(info)
   if i%2==0 or done or truncated:
    renderer.update_scene(env.data,camera='insertion')
    frame=Image.fromarray(renderer.render())
    draw=ImageDraw.Draw(frame);draw.rectangle((0,0,640,65),fill=(12,24,36))
    draw.text((12,8),'FINE-TUNED SmolVLA (1,000 steps) - FAILED PICKUP',fill='white')
    draw.text((12,27),f"t={env.data.time:.2f}s | finger contacts: L={info['left_contact']} R={info['right_contact']}",fill='white')
    draw.text((12,44),f"peg tip={info['tip_z_m']*1000:.1f}mm | jaw joint={env.data.qpos[env.qadr[6]]*1000:.1f}mm",fill='white')
    writer.append_data(np.asarray(frame))
    if i in (0,100,200,300):frame.save(args.out/f'frame-{i}.jpg')
   if done or truncated:break
 finally:writer.close();renderer.close();env.close()
 (args.out/'report.json').write_text(json.dumps({'scope':'Deterministic physics replay of saved learned-policy actions, first eight simulated seconds; not a new inference trial.','actions':str(args.actions),'seed':args.seed,'steps':len(records),'final':records[-1]},indent=2))

if __name__=='__main__':main()
