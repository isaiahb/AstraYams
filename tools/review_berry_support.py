"""Evaluate disjoint cases and render audited action replays, with no UI changes."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np,mujoco,torch,imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont
from stable_baselines3 import PPO
from astrafactory.berry_support import BerrySupportEnv
from train_berry_support_ppo import evaluate,dump

def render(run,row):
 seed=row['seed'];z=np.load(run/f'episode-{seed}.npz');e=BerrySupportEnv(1.);e.reset(seed=seed)
 rr=mujoco.Renderer(e.model,360,540);opt=mujoco.MjvOption();opt.geomgroup[3]=0;close=mujoco.MjvCamera();close.distance=.18;close.azimuth=110;close.elevation=-18
 font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18);small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',15)
 error=0.;frames=[]
 with imageio.get_writer(run/f'episode-{seed}.mp4',fps=25,codec='libx264',quality=7,macro_block_size=2) as writer:
  for k,a in enumerate(z['actions']):
   _,_,_,_,info=e.step(a);error=max(error,float(np.max(abs(e.data.qpos-z['qpos'][k]))))
   if k%2:continue
   rr.update_scene(e.data,camera='overview',scene_option=opt);im=Image.new('RGB',(1080,450),(239,242,236));im.paste(Image.fromarray(rr.render()),(0,65))
   close.lookat[:]=e.geometry()[0]
   if hasattr(e,'grasp'):
    close.distance=.29;close.azimuth=5;close.elevation=-22;close.lookat[:]=e.data.xpos[e.wrist]+e.data.xmat[e.wrist].reshape(3,3)@np.array([0,0,-.165])
   rr.update_scene(e.data,camera=close,scene_option=opt);im.paste(Image.fromarray(rr.render()),(540,65));draw=ImageDraw.Draw(im)
   draw.text((16,10),'PPO controls all six YAM arm joints | attached berry support',font=font,fill='#20342b')
   draw.text((16,37),f'Evaluation seed {seed}  |  {info["sim_s"]:.2f}s  |  support {info["support_fraction"]*100:.0f}% of fruit weight  |  hold {info["hold_steps"]}/20',font=small,fill='#20342b')
   draw.text((16,426),('1x physics replay | simulated state | tool held by jaw contact + friction | no execution IK' if hasattr(e,'grasp') else '1x physics replay | simulated state inputs | fixed mounted cup | no execution IK | not a bruising or hardware test'),font=small,fill='#20342b')
   writer.append_data(np.asarray(im));frames.append(im)
 rr.close();e.close()
 assert error<1e-8,error
 frames[-1].save(run/f'episode-{seed}-final.png')
 # Sparse contact sheet to inspect progression before presenting the recording.
 selected=[frames[i] for i in np.linspace(0,len(frames)-1,4).astype(int)];sheet=Image.new('RGB',(1080,450))
 for i,im in enumerate(selected):sheet.paste(im.resize((540,225)),((i%2)*540,(i//2)*225))
 sheet.save(run/f'episode-{seed}-sheet.jpg')
 return dict(seed=seed,max_replay_qpos_error=error,success=row['is_success'])

def main():
 global BerrySupportEnv
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--dev-only',action='store_true');p.add_argument('--gripped',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);torch.set_num_threads(2)
 if a.gripped:
  from astrafactory.gripped_berry_support import GrippedBerrySupportEnv
  import train_berry_support_ppo as trainer
  BerrySupportEnv=GrippedBerrySupportEnv;trainer.BerrySupportEnv=GrippedBerrySupportEnv
 model=PPO.load(a.checkpoint,device='cpu');seeds=[31001,31002,31003] if a.dev_only else list(range(33001,33013)) if a.gripped else list(range(32001,32013))
 rows=evaluate(model,seeds,1.,a.out);baseline=evaluate(None,seeds,1.)
 report=dict(checkpoint=str(a.checkpoint),sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),split='development' if a.dev_only else 'holdout',actor_parameters=sum(x.numel() for x in model.policy.mlp_extractor.policy_net.parameters())+sum(x.numel() for x in model.policy.action_net.parameters()),steps_trained=int(model.num_timesteps),gripped_tool=a.gripped,successes=sum(r['is_success'] for r in rows),episodes=len(rows),baseline_successes=sum(r['is_success'] for r in baseline),rows=rows,baseline=baseline)
 dump(a.out/'report.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['rows','baseline']}),flush=True)
 # First three predetermined seeds plus the first failure, if separate.
 chosen=rows[:3];failed=next((r for r in rows if not r['is_success']),None)
 if failed and failed not in chosen:chosen.append(failed)
 audits=[render(a.out,row) for row in chosen];dump(a.out/'replay-audit.json',audits)

if __name__=='__main__':main()
