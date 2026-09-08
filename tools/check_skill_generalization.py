"""Predeclared, no-retraining robustness audit of the frozen contact skill chain.

All variations occur at reset. Geometry and scored acceptance stay unchanged.
This tests bounded transfer in simulation, not new-object or hardware generality.
"""
from pathlib import Path
import argparse,hashlib,json,time,math
import mujoco,numpy as np,torch
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_downstream_skills import DownstreamSkill
from astrafactory.contact_downstream_skills_v3 import CorrectedInsertSkill
from check_yam_contact import model_checks,physical_state
from collect_demonstrations import task_hashes

CHECKPOINTS={'grasp':'runs/micro-grasp-v1/policy.pt','align':'runs/downstream-v2-dr/align.npz','insert':'runs/downstream-v3-corrected/linear.npz'}
PROFILES={
 'wider_pose':dict(seed_start=6000,xy_m=.010,shared_yaw_rad=.15,mass_scale=[1.,1.],friction_scale=[1.,1.],relative_socket_yaw_rad=0.),
 'dynamics':dict(seed_start=6100,xy_m=.002,shared_yaw_rad=.02,mass_scale=[.7,1.3],friction_scale=[.65,1.35],relative_socket_yaw_rad=0.),
 'independent_socket_yaw':dict(seed_start=6200,xy_m=.002,shared_yaw_rad=.02,mass_scale=[1.,1.],friction_scale=[1.,1.],relative_socket_yaw_rad=.15),
 'combined':dict(seed_start=6300,xy_m=.010,shared_yaw_rad=.15,mass_scale=[.7,1.3],friction_scale=[.65,1.35],relative_socket_yaw_rad=.15),
}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def proposal():
 return {'hypothesis':'Frozen local specialists may transfer beyond their narrow training ranges; independent socket yaw and combined shifts may reveal failures. No tuning follows this audit.',
  'role':'predeclared held-out robustness challenge','episodes_per_profile':10,'profiles':PROFILES,'checkpoint_sha256':{v:sha(v) for v in CHECKPOINTS.values()},'task_hashes':task_hashes('tasks/yam_contact_curriculum'),
  'source_sha256':{p:sha(p) for p in [__file__,'src/astrafactory/contact_micro_grasp.py','src/astrafactory/contact_downstream_skills.py','src/astrafactory/contact_downstream_skills_v3.py','src/astrafactory/contact_env.py','src/astrafactory/env.py','src/astrafactory/contact_curriculum.py']},
  'actual_acceptance':{'xy_error_m_lt':.001,'full_rotation_error_rad_lt':.06,'tip_z_interval_m':[.0075,.012],'linear_speed_m_s_lt':.015,'summed_contact_load_n_lt':45,'consecutive_hold_steps':15,'was_lifted_required':True,'force_abort_n_gt':80,'horizon_steps':1500},
  'strict_posthoc':{'xy_error_m_lt':.0008,'full_rotation_error_rad_lt':.05,'summed_contact_load_n_lt':15,'other_criteria':'unchanged; recorded states only'},
  'scope':'One continuous learned micrograsp→align→insert rollout; privileged state/guards and fixed IK scaffold. No training, teacher commands, or resets between skills. Same peg/socket geometry.',
  'sampling':'Uniform independent ranges. Pose uses environment reset seed; physical parameters and relative socket yaw use seed+1000000. Counts include reset/controller failures.',
  'promotion':'No promotion or tuning; report success/failure rates and boundaries for every profile.'}


def reset_challenge(e,seed,p):
 rng=np.random.default_rng(seed+1000000);mass=float(rng.uniform(*p['mass_scale']));friction=float(rng.uniform(*p['friction_scale']));relative=float(rng.uniform(-p['relative_socket_yaw_rad'],p['relative_socket_yaw_rad']))
 peg=e.model.body('free_peg').id;e.model.body_mass[peg]*=mass;e.model.body_inertia[peg]*=mass
 geoms=[j for j in range(e.model.ngeom) if any(s in (e.model.geom(j).name or '') for s in ['peg','finger_left','finger_right'])]
 e.model.geom_friction[geoms,0]*=friction
 e.specification['curriculum']={'peg_xy_m':p['xy_m'],'socket_xy_m':p['xy_m'],'yaw_rad':p['shared_yaw_rad']}
 mujoco.mj_setConst(e.model,mujoco.MjData(e.model));e.reset(seed=seed)
 peg_yaw=float(e.task.goal[3]);e.task.goal[3]+=relative
 e.model.body_quat[e.task.socket_id]=[np.cos(e.task.goal[3]/2),0,0,np.sin(e.task.goal[3]/2)]
 mujoco.mj_forward(e.model,e.data);e.reward_function.reset()
 return {'seed':seed,'domain_seed':seed+1000000,'mass_scale':mass,'sliding_friction_scale':friction,'peg_mass_kg':float(e.model.body_mass[peg]),'peg_position_m':e.task.pick.tolist(),'socket_goal':e.task.goal.tolist(),'peg_start_yaw_rad':peg_yaw,'relative_socket_yaw_rad':relative,'reset_time':float(e.data.time),'range_provenance':'uncalibrated engineering challenge, not measured real-world distribution'}


def strict(trace):
 n=0;best=0
 for x in trace:
  ok=x['was_lifted'] and x['xy_error_m']<.0008 and x['orientation_error_rad']<.05 and .0075<=x['tip_z_m']<=.012 and x['peg_speed_m_s']<.015 and x['peak_contact_force_n']<15
  n=n+1 if ok else 0;best=max(best,n)
 return {'success':best>=15,'maximum_qualifying_hold':best}


def wilson(k,n):
 z=1.96;center=(k/n+z*z/(2*n))/(1+z*z/n);half=z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n)
 return [max(0,center-half),min(1,center+half)]


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=Path('runs/skill-generalization-v1'));ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);spec=proposal();pp=a.out/'proposal.json'
 if a.prepare_only:
  if pp.exists():raise ValueError('Proposal already exists')
  pp.write_text(json.dumps(spec,indent=2));print(str(pp));return
 if not pp.exists() or json.loads(pp.read_text())!=spec:raise ValueError('Prepare unchanged proposal and register it before evaluation')
 if (a.out/'report.json').exists():raise ValueError('Completed audit is immutable; use a new experiment')
 torch.set_num_threads(2);start=time.time();trials=[]
 for name,p in PROFILES.items():
  for seed in range(p['seed_start'],p['seed_start']+10):
   e=CurriculumEnv('tasks/yam_contact_curriculum');rows=[];actions=[];handoffs=[];phase='reset';sample=None;exception=None;info={'is_success':False};t=time.time()
   try:
    checks=model_checks(e);assert checks['passed'];sample=reset_challenge(e,seed,p)
    skills={'grasp':MicroGrasp(CHECKPOINTS['grasp']),'align':DownstreamSkill(CHECKPOINTS['align'],'align'),'insert':CorrectedInsertSkill(CHECKPOINTS['insert'])};phase='grasp';skills[phase].start(e)
    for _ in range(e.horizon):
     before=e.data.qpos.copy();action=skills[phase].act(e);assert np.array_equal(before,e.data.qpos),'Policy mutated physics state'
     _,_,done,trunc,info=e.step(action);rows.append({'step':e.steps,'phase':phase,**info,**physical_state(e)});actions.append(action)
     ready=skills[phase].handoff(e) if phase=='grasp' else skills[phase].handoff(e,info)
     if ready and phase!='insert':
      old=phase;phase='align' if phase=='grasp' else 'insert';skills[phase].start(e);handoffs.append({'from':old,'to':phase,'step':e.steps,'sim_time':float(e.data.time)})
     if done or trunc:break
   except Exception as exc:exception={'type':type(exc).__name__,'message':str(exc)}
   finally:e.close()
   tp=a.out/f'{name}-{seed}-trace.json';tp.write_text(json.dumps(rows));np.savez_compressed(a.out/f'{name}-{seed}-actions.npz',actions=np.array(actions))
   r={'profile':name,'seed':seed,'realized':sample,'is_success':bool(info['is_success']) and exception is None,'strict_posthoc':strict(rows),'final':info,'final_phase':phase,'handoffs':handoffs,'exception':exception,'trace':str(tp),'trace_sha256':sha(tp),'wall_seconds':time.time()-t};trials.append(r)
   with (a.out/'trials.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
   print(json.dumps(r),flush=True)
 summaries={}
 for name in PROFILES:
  rr=[r for r in trials if r['profile']==name];k=sum(r['is_success'] for r in rr)
  summaries[name]={'successes':k,'episodes':len(rr),'wilson95':wilson(k,len(rr)),'strict_successes':sum(r['strict_posthoc']['success'] for r in rr),'failures_by_phase':{phase:sum(not r['is_success'] and r['final_phase']==phase for r in rr) for phase in ['reset','grasp','align','insert']}}
 report={'proposal_sha256':sha(pp),'summaries':summaries,'trials':trials,'wall_seconds':time.time()-start,'frozen_checkpoints_verified_after':all(sha(p)==h for p,h in spec['checkpoint_sha256'].items()),'limitations':['Same peg/socket geometry only.','Privileged simulator state and engineered IK/guards.','Uniform engineering ranges are not calibrated hardware uncertainty.','Ten trials per profile provide limited statistical confidence; no universal generalization claim.','No retraining or tuning after challenge outcomes.']}
 (a.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(summaries),flush=True)

if __name__=='__main__':main()
