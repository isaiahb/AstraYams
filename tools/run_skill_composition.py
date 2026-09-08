"""Compose a learned pickup with explicitly scripted transport and insertion.

This is a hybrid proof of skill handoff, not three learned policies. The pickup
uses camera/proprioception only. The handoff monitor and downstream controllers
use privileged simulated contact/pose observations. No state reset occurs between
skills, and every movement is executed through the original physics/actuators.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import torch,mujoco
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.observations import CameraObservation
from astrafactory.contact_teacher import feedbackteacher
from check_yam_contact import physical_state,model_checks
from evaluate_smolvla import validate_stats,TASK_TEXT
from collect_demonstrations import task_hashes

def main():
 p=argparse.ArgumentParser(description=__doc__)
 source=p.add_mutually_exclusive_group(required=True)
 source.add_argument('--checkpoint')
 source.add_argument('--small-grasp-checkpoint')
 p.add_argument('--dataset-root',type=Path,required=True)
 p.add_argument('--task',default='tasks/yam_contact_curriculum')
 p.add_argument('--seed',type=int,default=2000)
 p.add_argument('--out',type=Path,required=True)
 args=p.parse_args()
 if args.out.exists() and any(args.out.iterdir()):p.error('Use a new output directory')
 args.out.mkdir(parents=True,exist_ok=True)
 torch.set_num_threads(2)
 small=None;policy=None
 if args.small_grasp_checkpoint:
  from astrafactory.contact_grasp_skill import GraspSkill
  small=GraspSkill(args.small_grasp_checkpoint)
 else:
  config=SmolVLAConfig.from_pretrained(args.checkpoint);config.device='cuda'
  assert config.n_action_steps==5 and config.chunk_size==50 and config.num_steps==10
  policy=SmolVLAPolicy.from_pretrained(args.checkpoint,config=config).to('cuda').eval()
  pre,post=make_pre_post_processors(config,pretrained_path=args.checkpoint,
   preprocessor_overrides={'device_processor':{'device':'cuda'}},
   postprocessor_overrides={'device_processor':{'device':'cpu'}})
  stats=json.loads((args.dataset_root/'meta/stats.json').read_text())
  validate_stats(pre,stats,['observation.state']);validate_stats(post,stats,['action'])
 env=CurriculumEnv(args.task);camera=CameraObservation(env)
 env.reset(seed=args.seed)
 if small:small.start(env)
 else:policy.reset();pre.reset();post.reset()
 torch.manual_seed(args.seed)
 torch.cuda.manual_seed_all(args.seed);np.random.seed(args.seed)
 checks=model_checks(env);assert checks['passed']
 initial_z=physical_state(env)['peg_z_m']
 phase='learned pickup';stable=0.;handoffs=[];rows=[];actions=[]
 renderer=mujoco.Renderer(env.model,height=400,width=600)
 closecam=mujoco.MjvCamera();closecam.azimuth=135;closecam.elevation=-25;closecam.distance=.27
 video=imageio.get_writer(args.out/'hybrid-composition.mp4',fps=25,codec='libx264',quality=7)
 dt=env.model.opt.timestep*env.frame_skip
 try:
  for step in range(env.horizon):
   before=env.data.qpos.copy()
   if phase=='learned pickup':
    if small:action=small.act(env)
    else:
     frame=camera.observation(None)
     batch={'observation.images.overview':torch.from_numpy(frame['image']).permute(2,0,1).float()/255.,
       'observation.state':torch.from_numpy(frame['proprioception']),'task':TASK_TEXT}
     with torch.inference_mode():action=post(policy.select_action(pre(batch))).cpu().numpy().reshape(-1)
   else:
    action=feedbackteacher(env)
    if phase=='scripted transport' and env.task.feedback_state['stage']==5:
     phase='scripted insertion';handoffs.append({'to':phase,'time':env.data.time,'guard':'measured socket alignment / overhead pose','physical_state':physical_state(env)})
   assert np.array_equal(before,env.data.qpos),'Controller changed execution state'
   action=np.clip(action,-1,1)
   _,reward,done,truncated,info=env.step(action)
   physical=physical_state(env)
   rows.append({'phase':phase,'step':step+1,**info,**physical});actions.append(action)
   if phase=='learned pickup':
    supported=(physical['peg_z_m']>=initial_z+.02 and physical['left_force_n']>.02
      and physical['right_force_n']>.02 and physical['nonfinger_support_force_n']<.01)
    stable=stable+dt if supported else 0.
    if stable>=.5 and physical['peg_z_m']>=.065:
     phase='scripted transport'
     env.task.feedback_state={'stage':4,'counter':0,'retract':0}
     handoffs.append({'to':phase,'time':env.data.time,'guard':'unsupported bilateral lift >=20mm for >=0.5s and absolute peg clearance >=65mm','supported_seconds':stable,'physical_state':physical})
   if step%2==0 or done or truncated:
    renderer.update_scene(env.data,camera='overview');overview=renderer.render().copy()
    closecam.lookat[:]=env.data.site_xpos[env.task.pid]+np.array([0,0,.035])
    renderer.update_scene(env.data,camera=closecam);close=renderer.render().copy()
    frame=Image.new('RGB',(1200,464),(12,24,36));frame.paste(Image.fromarray(overview),(0,50));frame.paste(Image.fromarray(close),(600,50))
    draw=ImageDraw.Draw(frame)
    draw.text((12,6),'HYBRID: '+('tiny state-policy pickup' if small else 'learned VLA pickup')+' -> scripted transport -> scripted insertion',fill='white')
    draw.text((12,24),f"Active: {phase} | t={env.data.time:.2f}s | insertion success={info['is_success']} | contact physics throughout",fill='white')
    video.append_data(np.asarray(frame))
   if done or truncated:break
 finally:video.close();renderer.close();camera.close()
 np.savez_compressed(args.out/'actions.npz',executed=actions)
 (args.out/'trace.json').write_text(json.dumps(rows))
 report={'label':'Hybrid skill composition, not a fully learned assembly policy',
  'learned_component':args.checkpoint or args.small_grasp_checkpoint,
  'learned_inputs':'Privileged simulator pose/contact, 5252-parameter state policy with scripted IK' if small else 'Camera and proprioception SmolVLA','scripted_components':['pose-feedback transport','pose-feedback insertion'],
  'monitor_inputs':'Privileged simulator contact and pose; not claimed as deployed hardware sensing.',
  'reset_between_skills':False,'seed':args.seed,'model_checks':checks,'task_hashes':task_hashes(args.task),
  'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'handoffs':handoffs,'final':rows[-1],'success':bool(rows[-1]['is_success'])}
 (args.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['final']),flush=True)

if __name__=='__main__':main()
