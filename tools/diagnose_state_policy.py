"""Diagnose learned action errors without feeding teacher phase/actions to the policy."""
from pathlib import Path
import argparse
import json
import numpy as np
import torch
try:
    from .finetune_skill import StatePolicy, predict
    from .collect_demonstrations import load_callable, task_hashes
    from .check_yam_contact import physical_state
except ImportError:
    from finetune_skill import StatePolicy, predict
    from collect_demonstrations import load_callable, task_hashes
    from check_yam_contact import physical_state

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', required=True)
    p.add_argument('--env-class', required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--teacher', default='astrafactory.contact_teacher:teacher')
    p.add_argument('--seed',type=int,default=2000)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.seed>=5000:
        p.error('Diagnostic tuning is restricted to development seeds')
    a.out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(2)
    c=torch.load(a.checkpoint,map_location='cpu',weights_only=False)
    if c['task_hashes']!=task_hashes(a.task):
        raise ValueError('Task mismatch')
    m=StatePolicy(**c['config']);m.load_state_dict(c['model']);m.eval()
    env=load_callable(a.env_class)(a.task);teacher=load_callable(a.teacher)
    rows=[];first_contact=None;first_lift=None;first_large_error=None
    try:
        obs,info=env.reset(seed=a.seed);initial=physical_state(env);m.reset_history()
        for step in range(env.horizon):
            action=predict(m,obs,c['mean'],c['std'])
            before=env._observation().copy();q=env.data.qpos.copy();target=env.target.copy()
            expert=np.asarray(teacher(env))
            assert np.array_equal(before,env._observation()) and np.array_equal(q,env.data.qpos) and np.array_equal(target,env.target), 'Diagnostic teacher modified policy inputs or execution state'
            phase=int(env.task.stage)
            error=float(np.sqrt(np.mean((action-expert)**2)))
            obs,reward,terminated,truncated,info=env.step(action)
            state=physical_state(env)
            bilateral=state['left_force_n']>1e-5 and state['right_force_n']>1e-5
            elevated=state['peg_z_m']-initial['peg_z_m']>=.02 and state['nonfinger_support_force_n']<1e-5
            if bilateral and first_contact is None:first_contact=step+1
            if bilateral and elevated and first_lift is None:first_lift=step+1
            if error>.05 and first_large_error is None:first_large_error=step+1
            rows.append({'step':step+1,'diagnostic_teacher_phase':phase,'action_rmse_from_expert':error,
                         'action':action.tolist(),'expert_action_for_diagnosis_only':expert.tolist(),
                         'observation':obs.tolist(),**state,**info})
            if terminated or truncated:break
    finally:env.close()
    phase_summary={}
    for phase in sorted({r['diagnostic_teacher_phase'] for r in rows}):
        rs=[r for r in rows if r['diagnostic_teacher_phase']==phase]
        phase_summary[str(phase)]={'steps':len(rs),'mean_action_rmse':float(np.mean([r['action_rmse_from_expert'] for r in rs]))}
    result={'checkpoint':str(a.checkpoint),'seed':a.seed,'is_success':bool(rows[-1]['is_success']),
            'reason':rows[-1]['reason'],'steps':len(rows),'first_bilateral_contact_step':first_contact,
            'first_bilateral_unsupported_lift_20mm_step':first_lift,'first_action_rmse_above_0_05_step':first_large_error,
            'max_peg_tip_rise_m':max(r['peg_z_m']-initial['peg_z_m'] for r in rows),
            'peak_contact_metric_n':rows[-1]['episode_peak_force_n'],'phase_summary':phase_summary,
            'teacher_is_diagnostic_only':True,'teacher_did_not_modify_policy_inputs_or_execution_state':True,
            'policy_inputs':'saved observation history only; no teacher stage/action','last':rows[-1]}
    (a.out/'result.json').write_text(json.dumps(result,indent=2))
    (a.out/'trace.json').write_text(json.dumps(rows))
    print(json.dumps({k:v for k,v in result.items() if k!='last'}),flush=True)

if __name__=='__main__':main()
