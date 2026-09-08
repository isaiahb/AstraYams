"""Physically reached downstream BC dataset and continuous learned evaluation."""
from pathlib import Path
import argparse,copy,hashlib,json,time
import mujoco,numpy as np
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_teacher import teacher
from astrafactory.contact_downstream_skills import DownstreamSkill,observe,expert_label,scaffold


def snapshot(e):
    mask=mujoco.mjtState.mjSTATE_INTEGRATION
    state=np.empty(mujoco.mj_stateSize(e.model,mask));mujoco.mj_getState(e.model,e.data,state,mask)
    return {'integration':state,'target':e.target.copy(),'previous_action':e.previous_action.copy(),'steps':e.steps,'episode_peak_force':e.episode_peak_force,'body_pos':e.model.body_pos.copy(),'body_quat':e.model.body_quat.copy(),'task':{k:copy.deepcopy(v) for k,v in e.task.__dict__.items() if k!='env'},'rng':copy.deepcopy(e.np_random.bit_generator.state),'reward_last_distance':e.reward_function.last_distance,'body_mass':e.model.body_mass.copy(),'body_inertia':e.model.body_inertia.copy(),'geom_friction':e.model.geom_friction.copy()}


def restore_snapshot(e,path):
    """Isolated skill training only; never call this between composed skills."""
    path=Path(path);meta=json.loads(path.with_suffix('.json').read_text())
    with np.load(path,allow_pickle=False) as d:
        for key in ['body_pos','body_quat','body_mass','body_inertia','geom_friction']:
            getattr(e.model,key)[:]=d[key]
        mujoco.mj_setConst(e.model,mujoco.MjData(e.model))
        mujoco.mj_setState(e.model,e.data,d['integration'],mujoco.mjtState.mjSTATE_INTEGRATION)
        e.target=d['target'].copy();e.previous_action=d['previous_action'].copy()
    e.steps=meta['steps'];e.episode_peak_force=meta['episode_peak_force']
    for key,value in meta['task'].items():
        setattr(e.task,key,np.array(value) if key in ['goal','pick','desired'] else value)
    e.np_random.bit_generator.state=meta['rng'];e.reward_function.last_distance=meta['reward_last_distance']
    mujoco.mj_forward(e.model,e.data)
    return meta


def prefix(e,seed,resetter=None):
    reset_info=(resetter or e).reset(seed=seed)[1];commands=[]
    for _ in range(700):
        a=teacher(e,stop_after_lift=True);_,_,done,trunc,info=e.step(a);commands.append(a)
        if done or trunc:raise RuntimeError('Pickup failed: '+str(info))
        if e.task.stage==3 and e.task.feedback_state['counter']>=25:return commands,{**info,'reset_info':reset_info}
    raise RuntimeError('Pickup prefix budget')


def rollout(e,skills=None,collect=None,trace=None,zero=False):
    info={};kind='align';counter=0
    if skills:skills[kind].start(e)
    transitions=[]
    for _ in range(e.horizon-e.steps):
        if skills:
            before=e.data.qpos.copy();a=skills[kind].act(e);assert np.array_equal(before,e.data.qpos)
            if zero:a=scaffold(e,kind,np.zeros(6))
        else:
            x=observe(e,kind);y=expert_label(e,kind);collect[kind][0].append(x);collect[kind][1].append(y);a=scaffold(e,kind,y)
        before_error=np.linalg.norm(observe(e,kind)[:6]);_,_,done,trunc,info=e.step(a)
        if trace is not None:trace.append({'step':e.steps,'skill':kind,'action':a.tolist(),'info':dict(info),'skill_diagnostic_reward':float(before_error-np.linalg.norm(observe(e,kind)[:6])-.001*min(info['peak_contact_force_n'],50))})
        if kind=='align':
            if skills:ready=skills[kind].handoff(e,info)
            else:
                x=observe(e,kind);valid=np.linalg.norm(x[:2])*.05<.0005 and abs(x[2])*.05<.001 and np.linalg.norm(x[3:6])*.1<.01 and np.linalg.norm(x[6:9])*.1<.015 and info['grasp_contacts'];counter=counter+1 if valid else 0;ready=counter>=10
            if ready:
                transitions.append({'step':e.steps,'info':dict(info)});kind='insert'
                if skills:skills[kind].start(e)
        if done or trunc:break
    return {'final':info,'handoffs':transitions}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--train-episodes',type=int,default=12);p.add_argument('--dev-episodes',type=int,default=5);p.add_argument('--train-seed',type=int,default=100);p.add_argument('--dev-seed',type=int,default=2000);p.add_argument('--randomize-training',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);start=time.time();e=CurriculumEnv('tasks/yam_contact_curriculum');data={k:[[],[]] for k in ['align','insert']};train=[]
    from astrafactory.skill_randomization import SkillRandomization
    resetter=SkillRandomization(e,'training-mild-v1','training') if a.randomize_training else None
    for seed in range(a.train_seed,a.train_seed+a.train_episodes):
        commands,pi=prefix(e,seed,resetter);s=snapshot(e)
        # Full-state capture is evidence for later isolated skill resets, not used in this continuous evaluation.
        np.savez_compressed(a.out/f'prefix-{seed}.npz',integration=s['integration'],target=s['target'],previous_action=s['previous_action'],body_pos=s['body_pos'],body_quat=s['body_quat'],commands=np.array(commands),body_mass=s['body_mass'],body_inertia=s['body_inertia'],geom_friction=s['geom_friction'])
        meta={k:v for k,v in s.items() if k not in ['integration','target','previous_action','body_pos','body_quat','body_mass','body_inertia','geom_friction']}
        meta['reset_info']=pi['reset_info'];(a.out/f'prefix-{seed}.json').write_text(json.dumps(meta,default=lambda o:o.tolist() if isinstance(o,np.ndarray) else o.item(),indent=2))
        result=rollout(e,collect=data);result['seed']=seed;result['reset_info']=pi['reset_info'];train.append(result);print(json.dumps({'train_seed':seed,**result}),flush=True)
    for kind,(xs,ys) in data.items():
        x=np.array(xs);y=np.array(ys);np.savez_compressed(a.out/f'{kind}-dataset.npz',observation=x,label=y)
        weight=np.linalg.solve(x.T@x+np.eye(x.shape[1])*1e-8,x.T@y)
        np.savez(a.out/f'{kind}.npz',weight=weight,kind=kind)
        print(kind,len(x),'mse',np.mean((x@weight-y)**2),flush=True)
    e.close();e=CurriculumEnv('tasks/yam_contact_curriculum')
    skills={k:DownstreamSkill(a.out/f'{k}.npz',k) for k in data};dev=[]
    for seed in range(a.dev_seed,a.dev_seed+a.dev_episodes):
        _,pi=prefix(e,seed);trace=[];result=rollout(e,skills=skills,trace=trace);result['seed']=seed;dev.append(result);(a.out/f'dev-{seed}-trace.json').write_text(json.dumps(trace));print(json.dumps({'dev_seed':seed,**result}),flush=True)
    _,pi=prefix(e,a.dev_seed);zero_result=rollout(e,skills=skills,zero=True)
    report={'zero_output_ablation':zero_result,'training_randomization':a.randomize_training,'checkpoint_sha256':{str(a.out/f'{k}.npz'):hashlib.sha256((a.out/f'{k}.npz').read_bytes()).hexdigest() for k in data},'label':'Learned linear privileged state-feedback BC with fixed IK scaffold; teacher pickup prefix, continuous learned alignment and insertion','training':train,'development':dev,'wall_seconds':time.time()-start,'train_successes':sum(x['final']['is_success'] for x in train),'dev_successes':sum(x['final']['is_success'] for x in dev),'source_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [Path(__file__),Path('src/astrafactory/contact_downstream_skills.py')]},'limitations':['Goal-relative simulator pose is privileged input.','Linear local-controller distillation with hand-designed observations and IK scaffold; not visual learning or autonomous pickup.','Final seeds untouched.','Snapshots are evidence only; continuous evaluations replay real teacher pickup and never restore state.']}
    (a.out/'report.json').write_text(json.dumps(report,indent=2));e.close();print(json.dumps(report),flush=True)

if __name__=='__main__':main()
