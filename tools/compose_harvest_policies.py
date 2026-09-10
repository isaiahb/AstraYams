"""Physical state-preserving composition. Every moving arm command is a PPO action.

Idle arms retain motor targets under finite PD forces. No runtime IK, scripted
path fallback, weld attachment to the catcher, or state reset at skill boundaries.
"""
from pathlib import Path
import argparse,json,hashlib,shutil
import numpy as np,mujoco,torch
from stable_baselines3 import PPO
from astrafactory.harvest_basket import HarvestBasketEnv
from astrafactory.harvest_joint_skill import HarvestJointSkill
from astrafactory.cutter_skill import CutterSkillEnv
from astrafactory.cut_release_skill import CutReleaseSkill
from astrafactory.release_withdraw_skill import ReleaseWithdrawSkill


def state_hash(e):
 return hashlib.sha256(e.data.qpos.tobytes()+e.data.qvel.tobytes()+e.data.eq_active.tobytes()).hexdigest()

def bind(skill,e,goal=None,R=None):
 """Reset policy memory and goal only; preserve every physical coordinate."""
 before=state_hash(e);skill.e=e
 if isinstance(skill,HarvestJointSkill):
  skill.qids=e.cq if skill.cutter else e.qids;skill.vids=e.cv if skill.cutter else e.vids;skill.site=e.cutsite if skill.cutter else e.site;skill.body=e.model.site_bodyid[skill.site]
  skill.goal=skill.goal_base.copy() if goal is None else np.asarray(goal).copy()
  if R is not None:skill.goal_R=np.asarray(R).copy()
  skill.hold=0;skill.previous_impact_cost=0.;delta,rot=skill.geometry();skill.previous_cost=float(np.linalg.norm(delta)+.025*np.linalg.norm(rot));skill.last=np.zeros(6)
 elif isinstance(skill,CutReleaseSkill):skill.bind(e)
 else:
  skill.last=np.zeros(7);skill.previous_distance=float(np.linalg.norm(skill.geometry()[0]));skill.previous_work=e.work;skill.previous_jaw=float(e.data.qpos[e.model.joint('cut_joint7').qposadr[0]])
 skill.info={};skill.steps=0
 assert before==state_hash(e),'Skill handoff changed physical state'
 return before

def run(config,out,seed,through='unload'):
 cfg=json.loads(Path(config).read_text());out.mkdir(parents=True,exist_ok=True)
 retreat=['release_withdraw'] if 'release_withdraw' in cfg['policies'] else (['release_cut'] if 'release_cut' in cfg['policies'] else [])+['withdraw']
 order=['support','approach']+(['align'] if 'align' in cfg['policies'] else [])+['clip']+retreat+['carry','unload'];required=order[:order.index(through)+1]
 for key in required:
  if not Path(cfg['policies'][key]).is_file():raise FileNotFoundError(f'Missing learned {key} checkpoint; scripted fallback is forbidden')
 shutil.copytree(cfg['task'],out/'task',dirs_exist_ok=True);e=HarvestBasketEnv(task_dir=out/'task',variation=cfg.get('variation',0));e.reset(seed=seed)
 policies={k:PPO.load(cfg['policies'][k],device='cpu') for k in required}
 profiles={}
 for k in ['approach','align','withdraw','carry','unload']:
  if k not in required:continue
  s=HarvestJointSkill(k,source=cfg['alignment_source'] if k=='align' else cfg['placement_source'] if k in ['carry','unload'] else cfg['cut_source'],difficulty=1.,wrist_only=k=='unload' and cfg.get('unload_actions')=='wrist-pair')
  if k=='approach':offset=s.goal_base-s.e.data.xpos[s.e.branch];support_reference=s.e.initial[s.e.qids].copy()
  bind(s,e);profiles[k]=s
 if 'clip' in required:
  s=CutterSkillEnv(source=cfg['cut_source'],difficulty=.5,joint_scale=cfg.get('clip_joint_scale',.25));bind(s,e);profiles['clip']=s
 if 'release_cut' in required:
  s=CutReleaseSkill(source=cfg['release_source']);bind(s,e);profiles['release_cut']=s
 if 'release_withdraw' in required:
  s=ReleaseWithdrawSkill(source=cfg['release_source'],support_policy=cfg['policies']['support']);bind(s,e);s.support_reference=support_reference.copy();profiles['release_withdraw']=s
 # The cutter approach target is derived from the current physical target stalk.
 approach=profiles['approach']
 if cfg.get('approach_goal')=='stalk-center':offset=np.zeros(3)
 bind(approach,e,goal=e.data.xpos[e.branch]+offset);phase='position both';phase_steps=0;handoffs=[];trace=[];qs=[e.data.qpos.copy()];vs=[e.data.qvel.copy()];eq=[e.data.eq_active.copy()];net=[e.data.flexvert_xpos.copy()];catch_targets=[e.target.copy()];cut_targets=[e.cut_target.copy()];jaw_targets=[e.jaw_target];all_actions=[];reason='horizon';success=False
 for step in range(cfg.get('horizon_steps',1600)):
  ca=cu=None;active=[];e.phase='PPO / '+phase
  if phase=='position both':
   approach.goal=e.data.xpos[e.branch]+offset
   obs=e.observe();obs[:6]=e.data.qpos[e.qids]-support_reference
   ca=None if e.hold>=20 else policies['support'].predict(obs,deterministic=True)[0]
   a=np.zeros(6) if approach.hold>=10 else policies['approach'].predict(approach.observe(),deterministic=True)[0];cu=np.r_[a,0.];active=['support','approach']
  elif phase=='clip':
   s=profiles['clip'];a=policies['clip'].predict(s.observe(),deterministic=True)[0];cu=a.copy();cu[:6]*=s.joint_scale;active=['clip']
  elif phase=='release_cut':
   s=profiles[phase];a=policies[phase].predict(s.observe(),deterministic=True)[0];cu=np.r_[np.zeros(6),a];active=[phase]
  elif phase=='release_withdraw':
   s=profiles[phase];a=policies[phase].predict(s.observe(),deterministic=True)[0];cu=a;ca=s.partner_action();active=[phase]+(['support'] if ca is not None else [])
  else:
   if phase=='align':profiles[phase].goal=e.data.xpos[e.branch].copy()
   s=profiles[phase];a=np.zeros(6) if phase=='withdraw' and s.hold>=10 and e.net_hold<25 else policies[phase].predict(s.observe(),deterministic=True)[0];active=[phase]
   if s.cutter:cu=np.r_[a,0.]
   else:ca=np.r_[np.zeros(4),a] if s.wrist_only else a
  info=e.advance(catch_action=ca,cut_action=cu);phase_steps+=1;next_phase=None
  if phase=='position both':
   _,_,_,_,contract=approach.after_step(a,info)
   if contract['invalid']:info['invalid']=True
   if 'align' in profiles:
    # The new alignment expert owns the final millimeters. This is a coarse
    # entry gate, not a pass for the old fine-approach benchmark.
    gate=bool(info['catcher_ready'] and info['cut_distance_m']<cfg.get('alignment_entry_radius_m',.008) and np.linalg.norm(e.data.qvel[e.cv])<.15 and not info['invalid'])
    info['coarse_handoff_admissible']=gate
    if gate:next_phase='align'
   elif info['catcher_ready'] and contract['is_success'] and info['cut_distance_m']<.004:next_phase='clip'
  elif phase=='clip':
   _,_,_,_,contract=s.after_step(a,info)
   if contract['is_success']:next_phase='release_withdraw' if 'release_withdraw' in profiles else 'release_cut' if 'release_cut' in profiles else 'withdraw'
  else:
   _,_,_,_,contract=s.after_step(a,info)
   if contract['is_success']:
    if phase=='release_withdraw':next_phase='carry'
    elif phase=='release_cut':next_phase='withdraw'
    elif phase=='align' and info['cut_distance_m']<.004:next_phase='clip'
    elif phase=='withdraw' and e.net_hold>=25:next_phase='carry'
    elif phase=='carry':next_phase='unload'
    elif phase=='unload':success=True;reason='fruit settled in basket'
  if next_phase and ((phase=='position both' and through=='approach') or phase==through):
   success=True;reason='requested partial chain completed through '+through
  info.update(active_policies=active,coordinator_phase=phase,phase_steps=phase_steps,local_skill_contract=contract['is_success'],local_goal_error_m=contract.get('goal_error_m',contract.get('cutter_goal_error_m')),local_orientation_error_rad=contract.get('orientation_error_rad'),is_success=success)
  trace.append(info);qs.append(e.data.qpos.copy());vs.append(e.data.qvel.copy());eq.append(e.data.eq_active.copy());net.append(e.data.flexvert_xpos.copy());catch_targets.append(e.target.copy());cut_targets.append(e.cut_target.copy());jaw_targets.append(e.jaw_target);all_actions.append(np.r_[np.zeros(6) if ca is None else ca,np.zeros(7) if cu is None else cu])
  if info['invalid']:reason='physical acceptance check failed';break
  if success:break
  if phase_steps>500:reason='skill timeout: '+phase;break
  if next_phase:
   s=profiles[next_phase];kwargs={}
   if next_phase=='align':kwargs=dict(goal=e.data.xpos[e.branch])
   if next_phase in ['withdraw','release_withdraw']:
    R=s.goal_R.copy();kwargs=dict(goal=e.data.site_xpos[e.cutsite]+R[:,2]*.035+[0,0,.020],R=R)
   digest=bind(s,e,**kwargs);handoffs.append(dict(from_skill=phase,to_skill=next_phase,time_s=e.elapsed,physical_state_sha256=digest));print('HANDOFF',phase,'->',next_phase,'at',e.elapsed,'s',flush=True);phase=next_phase;phase_steps=0
 result=dict(info,seed=seed,is_success=success,full_harvest_success=success and through=='unload',tested_through=through,termination_reason=reason,handoffs=handoffs,policy_sha256={k:hashlib.sha256(Path(cfg['policies'][k]).read_bytes()).hexdigest() for k in required},controller='Learned PPO chain through '+through+'. Support and approach run concurrently; idle-arm finite motor holding. No runtime IK or scripted movement fallback. Privileged simulation state; one designated fruit per episode.')
 (out/f'episode-{seed}.json').write_text(json.dumps(dict(result=result,trace=trace),indent=2))
 np.savez_compressed(out/f'episode-{seed}.npz',qpos=qs,qvel=vs,eq_active=eq,flex_vertices=net,catch_targets=catch_targets,cut_targets=cut_targets,jaw_targets=jaw_targets,actions=all_actions,t=np.arange(len(qs))*.02)
 print(json.dumps(result),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,default=91001);p.add_argument('--through',choices=['approach','clip','withdraw','release_withdraw','unload'],default='unload');a=p.parse_args();torch.set_num_threads(1);run(a.config,a.out,a.seed,a.through)
