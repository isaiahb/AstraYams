"""Six named, visibly distinct same-geometry cases; no statistical claim."""
from pathlib import Path
import argparse,json,time
import numpy as np,mujoco,torch
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_downstream_skills import DownstreamSkill
from astrafactory.contact_downstream_skills_v3 import CorrectedInsertSkill
from astrafactory.yam_env import yaw_matrix
from check_skill_generalization import CHECKPOINTS,sha,strict
from check_yam_contact import physical_state,model_checks
from collect_demonstrations import task_hashes
CASES=[
 {'seed':6400,'name':'left pickup to right socket','peg_offset_m':[-.03,0],'socket_offset_m':[.04,0],'relative_yaw_deg':0},
 {'seed':6401,'name':'right pickup to left socket','peg_offset_m':[.03,0],'socket_offset_m':[-.04,0],'relative_yaw_deg':0},
 {'seed':6402,'name':'front pickup to back socket plus30deg','peg_offset_m':[0,-.03],'socket_offset_m':[0,.04],'relative_yaw_deg':30},
 {'seed':6403,'name':'back pickup to front socket minus30deg','peg_offset_m':[0,.03],'socket_offset_m':[0,-.04],'relative_yaw_deg':-30},
 {'seed':6404,'name':'diagonal outward plus30deg','peg_offset_m':[-.03,.03],'socket_offset_m':[.04,-.04],'relative_yaw_deg':30},
 {'seed':6405,'name':'diagonal across minus30deg','peg_offset_m':[.03,-.03],'socket_offset_m':[-.04,.04],'relative_yaw_deg':-30},
]

def reset_case(e,case):
 """Explicit physical initial-condition reset, before any simulated time elapses."""
 e.specification['curriculum']={'peg_xy_m':0.,'socket_xy_m':0.,'yaw_rad':0.};e.reset(seed=case['seed'])
 t=e.task;peg_yaw=np.pi;t.pick=np.r_[np.array([.26,-.08])+case['peg_offset_m'],.001];t.goal=np.r_[np.array([.32,0])+case['socket_offset_m'],.009,peg_yaw+np.deg2rad(case['relative_yaw_deg'])]
 e.data.qpos[t.pa:t.pa+7]=np.r_[t.pick,[np.cos(peg_yaw/2),0,0,np.sin(peg_yaw/2)]]
 e.model.body_pos[t.socket_id]=np.r_[t.goal[:2],0.];e.model.body_quat[t.socket_id]=[np.cos(t.goal[3]/2),0,0,np.sin(t.goal[3]/2)]
 mujoco.mj_forward(e.model,e.data)
 e.data.qpos[e.qadr[:6]]=e.ik(t.pick+np.array([0,0,.115]),yaw_matrix(peg_yaw),initial=e.data.qpos[e.qadr[:6]],restarts=12)
 e.target=e.data.qpos[e.qadr].copy();t.desired=t.pick+np.array([0,0,.115]);mujoco.mj_forward(e.model,e.data);e.reward_function.reset()
 return {'case':case,'peg_position_m':t.pick.tolist(),'socket_goal':t.goal.tolist(),'peg_start_yaw_rad':peg_yaw,'relative_socket_yaw_rad':float(np.deg2rad(case['relative_yaw_deg'])),'mass_scale':1.,'sliding_friction_scale':1.,'peg_mass_kg':float(e.model.body_mass[t.peg_body]),'reset_time':float(e.data.time),'hole_axis':'world vertical; yaw changes key orientation only','initial_tool_position_m':e.data.site_xpos[t.sid].tolist()}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=Path('runs/skill-layout-cases-v1'));p.add_argument('--prepare-only',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 spec={'hypothesis':'Fixed policies may transfer to visibly different layouts and ±30-degree relative key yaw; all named cases count including resetIK failures.','cases':CASES,'checkpoints':{v:sha(v) for v in CHECKPOINTS.values()},'source_sha256':{v:sha(v) for v in [__file__,'tools/check_skill_generalization.py','src/astrafactory/contact_micro_grasp.py','src/astrafactory/contact_downstream_skills.py','src/astrafactory/contact_downstream_skills_v3.py','src/astrafactory/contact_env.py','src/astrafactory/env.py']},'task_hashes':task_hashes('tasks/yam_contact_curriculum'),'acceptance':{'xy_m_lt':.001,'full_rotation_rad_lt':.06,'tip_z_interval_m':[.0075,.012],'speed_m_s_lt':.015,'load_n_lt':45,'hold_steps':15,'was_lifted':True,'abort_n_gt':80,'horizon':1500},'constraints':['No retraining or policy change','Only legal reset placements and initial-arm IK before simulation','One continuous rollout, no teacher commands or state resets between skills','Same peg/socket geometry, vertical hole, keyed yaw not tilted insertion','Named cases are demonstrations of bounded transfer, not a statistical generalization sample']};pp=a.out/'proposal.json'
 if a.prepare_only:
  if pp.exists():raise ValueError('Existing immutable proposal')
  pp.write_text(json.dumps(spec,indent=2));print(pp);return
 if not pp.exists() or json.loads(pp.read_text())!=spec:raise ValueError('Prepare and register unchanged proposal first')
 if (a.out/'report.json').exists():raise ValueError('Completed audit already exists')
 torch.set_num_threads(2);trials=[];start=time.time()
 for case in CASES:
  e=CurriculumEnv('tasks/yam_contact_curriculum');rows=[];actions=[];handoffs=[];phase='reset';sample=None;info={'is_success':False};exc=None
  try:
   checks=model_checks(e);assert checks['passed'];sample=reset_case(e,case)
   skills={'grasp':MicroGrasp(CHECKPOINTS['grasp']),'align':DownstreamSkill(CHECKPOINTS['align'],'align'),'insert':CorrectedInsertSkill(CHECKPOINTS['insert'])};phase='grasp';skills[phase].start(e)
   for _ in range(e.horizon):
    before=e.data.qpos.copy();action=skills[phase].act(e);assert np.array_equal(before,e.data.qpos)
    _,_,done,trunc,info=e.step(action);rows.append({'step':e.steps,'phase':phase,**info,**physical_state(e)});actions.append(action)
    ready=skills[phase].handoff(e) if phase=='grasp' else skills[phase].handoff(e,info)
    if ready and phase!='insert':
     old=phase;phase='align' if phase=='grasp' else 'insert';skills[phase].start(e);handoffs.append({'from':old,'to':phase,'step':e.steps,'sim_time':float(e.data.time)})
    if done or trunc:break
  except Exception as err:exc={'type':type(err).__name__,'message':str(err)}
  finally:e.close()
  stem=f"case-{case['seed']}";tp=a.out/f'{stem}-trace.json';tp.write_text(json.dumps(rows));np.savez_compressed(a.out/f'{stem}-actions.npz',actions=actions)
  row={'seed':case['seed'],'case':case,'realized':sample,'is_success':bool(info['is_success']) and exc is None,'strict_posthoc':strict(rows),'final':info,'final_phase':phase,'handoffs':handoffs,'exception':exc,'trace':str(tp),'trace_sha256':sha(tp)};trials.append(row);(a.out/f'{stem}-trial.json').write_text(json.dumps(row,indent=2));print(json.dumps(row),flush=True)
 report={'proposal_sha256':sha(pp),'trials':trials,'successes':sum(t['is_success'] for t in trials),'cases':len(trials),'strict_successes':sum(t['strict_posthoc']['success'] for t in trials),'wall_seconds':time.time()-start,'frozen_checkpoints_verified_after':all(sha(v)==h for v,h in spec['checkpoints'].items()),'scope':'Six named same-geometry layout/vertical-key-yaw challenges; no statistical/hardware/new-geometry claim'};(a.out/'report.json').write_text(json.dumps(report,indent=2));print(report['successes'],report['cases'])

if __name__=='__main__':main()
