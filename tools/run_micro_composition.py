"""Continuous learned micro-grasp -> learned align -> learned insert evaluation.

Privileged state and explicit guards/IK remain scripted. No teacher during rollout.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_downstream_skills import DownstreamSkill
from astrafactory.skill_randomization import SkillRandomization
from check_yam_contact import physical_state,model_checks
from collect_demonstrations import task_hashes


def run(args):
    args.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
    env=CurriculumEnv(args.task);checks=model_checks(env);assert checks['passed']
    randomizer=SkillRandomization(env,'stress-v1','stress') if args.stress else None
    started=time.monotonic();trials=[]
    for seed in range(args.seed,args.seed+args.episodes):
        _,reset_info=(randomizer.reset(seed=seed) if randomizer else env.reset(seed=seed))
        skills={'grasp':MicroGrasp(args.grasp),'align':DownstreamSkill(args.downstream/'align.npz','align'),
                'insert':DownstreamSkill(args.downstream/'insert.npz','insert')}
        if args.insert_v3:
            from astrafactory.contact_downstream_skills_v3 import CorrectedInsertSkill
            skills['insert']=CorrectedInsertSkill(args.insert_v3)
        phase='grasp';skills[phase].start(env);rows=[];actions=[];handoffs=[]
        for step in range(env.horizon):
            before=env.data.qpos.copy();action=skills[phase].act(env)
            assert np.array_equal(before,env.data.qpos),'Policy changed physics state outside step'
            _,_,done,trunc,info=env.step(action)
            rows.append({'step':step+1,'phase':phase,**info,**physical_state(env)});actions.append(action)
            ready=skills[phase].handoff(env) if phase=='grasp' else skills[phase].handoff(env,info)
            if ready and phase!='insert':
                old=phase;phase='align' if phase=='grasp' else 'insert';skills[phase].start(env)
                handoffs.append({'from':old,'to':phase,'step':step+1,'sim_time':float(env.data.time)})
            if done or trunc:break
        trace=args.out/f'seed-{seed}-trace.json';trace.write_text(json.dumps(rows))
        np.savez_compressed(args.out/f'seed-{seed}-actions.npz',actions=np.array(actions))
        row={'seed':seed,'is_success':bool(info['is_success']),'final':info,'final_phase':phase,
             'handoffs':handoffs,'grasp_internal_handoffs':skills['grasp'].handoffs,
             'domain_randomization':reset_info.get('domain_randomization'),'trace':str(trace)}
        trials.append(row);print(json.dumps(row),flush=True)
    checkpoints=[args.grasp,args.downstream/'align.npz',args.insert_v3 or args.downstream/'insert.npz']
    report={'scope':'Learned Cartesian/jaw grasp specialists and learned downstream corrections with scripted target construction, guards, angular grasp stabilization and IK; privileged state, not VLA.',
      'teacher_during_execution':False,'reset_between_skills':False,'model_checks':checks,
      'evaluation_role':('final_stress' if args.stress else 'final') if args.final else ('stress' if args.stress else 'development'),'task_hashes':task_hashes(args.task),
      'checkpoint_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checkpoints},
      'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'successes':sum(t['is_success'] for t in trials),'episodes':len(trials),'trials':trials,
      'wall_seconds':time.monotonic()-started}
    (args.out/'report.json').write_text(json.dumps(report,indent=2));env.close()
    print(json.dumps({k:report[k] for k in ['successes','episodes','wall_seconds']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--grasp',type=Path,default=Path('runs/micro-grasp-v1/policy.pt'))
    p.add_argument('--downstream',type=Path,default=Path('runs/downstream-v1'));p.add_argument('--task',default='tasks/yam_contact_curriculum')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,default=2500);p.add_argument('--episodes',type=int,default=10);p.add_argument('--stress',action='store_true');p.add_argument('--insert-v3',type=Path);p.add_argument('--final',action='store_true')
    a=p.parse_args()
    if a.episodes<1 or (a.final and a.seed<5000) or (not a.final and (a.seed<2000 or a.seed+a.episodes>5000)):p.error('Use disjoint development seeds2000–4999, or explicitly --final seeds5000+')
    run(a)
