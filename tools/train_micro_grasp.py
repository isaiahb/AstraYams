"""Train/evaluate compact Cartesian-and-jaw specialists without modifying v0 physics."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from astrafactory.contact_micro_grasp import MicroGrasp,oracle
from astrafactory.contact_grasp_skill import contacts
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.skill_randomization import SkillRandomization
from collect_demonstrations import task_hashes,environment_source_hash
from check_yam_contact import model_checks


def run(task,seed,skill,profile=None,collect=False):
    start=time.monotonic();env=CurriculumEnv(task)
    if profile:
        role='training' if profile=='training-mild-v1' else 'stress'
        _,reset_info=SkillRandomization(env,profile,role).reset(seed=seed)
    else:_,reset_info=env.reset(seed=seed)
    static=model_checks(env);skill.start(env);samples={'acquire':[],'lift':[]};rows=[];error=None;passed=False
    try:
        for step in range(env.horizon):
            if collect:
                key,x,_=skill.observe(env);samples[key].append((x.copy(),oracle(x)))
            before=env.data.qpos.copy();action=skill.act(env)
            assert np.array_equal(before,env.data.qpos),'controller wrote physical qpos'
            _,_,done,truncated,info=env.step(action)
            f=contacts(env);z=float(env.data.site_xpos[env.task.pid,2]);passed=skill.handoff(env)
            rows.append({'step':step+1,'phase':skill.phase,'time':float(env.data.time),'z':z,'forces':f.tolist(),
                         'action':action.tolist(),'tool_xyz':env.data.site_xpos[env.task.sid].tolist(),
                         'peg_xyz':env.data.site_xpos[env.task.pid].tolist(),'info':info})
            if passed or done or truncated:break
    except Exception as exc:
        error=repr(exc)
    report={'seed':seed,'passed':passed,'steps':len(rows),'seconds':time.monotonic()-start,
            'profile':profile or 'nominal-unwrapped','domain_sample':reset_info.get('domain_randomization'),
            'max_rise_m':max((r['z']-skill.initial_peg[2] for r in rows),default=0.),
            'longest_qualified_seconds':skill.longest,'handoffs':skill.handoffs,'error':error,
            'last':rows[-1] if rows else None,'model_checks':static}
    env.close();return report,samples,rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',type=Path,default=Path('tasks/yam_contact_curriculum'))
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--epochs',type=int,default=300)
    p.add_argument('--train-seed',type=int,default=300)
    p.add_argument('--eval-seed',type=int,default=2300)
    p.add_argument('--eval-episodes',type=int,default=5)
    p.add_argument('--training-dr',action='store_true')
    p.add_argument('--resume',type=Path)
    p.add_argument('--evaluate-only',type=Path)
    p.add_argument('--stress',action='store_true')
    a=p.parse_args()
    if a.eval_seed+a.eval_episodes>5000:raise ValueError('Final seeds require separate authorization')
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2);rng=np.random.default_rng(42)
    all_start=time.monotonic();report={'configuration':vars(a).copy()}
    report['configuration']={k:str(v) if isinstance(v,Path) else v for k,v in report['configuration'].items()}
    report['task_hashes']=task_hashes(a.task)
    report['source_hashes']={n:environment_source_hash(n) for n in ['astrafactory.contact_micro_grasp:MicroGrasp','astrafactory.contact_env:ContactEnv','astrafactory.contact_curriculum:CurriculumEnv','astrafactory.skill_randomization:SkillRandomization']}
    checkpoint=a.evaluate_only
    if checkpoint is None:
        report['untrained']=[]
        for seed in range(a.eval_seed,a.eval_seed+a.eval_episodes):
            r,_,_=run(a.task,seed,MicroGrasp());report['untrained'].append(r)
            print(json.dumps({'untrained':r['seed'],'passed':r['passed'],'steps':r['steps']}),flush=True)
        collected={'acquire':[],'lift':[]};report['teachers']=[]
        for seed in range(a.train_seed,a.train_seed+10):
            r,samples,_=run(a.task,seed,MicroGrasp(oracle_mode=True),
                            'training-mild-v1' if a.training_dr else None,True)
            report['teachers'].append(r)
            for key in collected:collected[key].extend(samples[key])
            print(json.dumps({'teacher':seed,'passed':r['passed'],'steps':r['steps']}),flush=True)
        skill=MicroGrasp(a.resume);train_start=time.monotonic();report['losses']={}
        for key,pairs in collected.items():
            if not pairs:raise ValueError('No demonstration samples for '+key)
            x=np.asarray([z[0] for z in pairs]);y=np.asarray([z[1] for z in pairs])
            # Local controller-state augmentation, not claimed as additional physical episodes.
            # Known analytic oracle relabels each perturbed pose error, velocity, and jaw target.
            augmented=np.repeat(x,4,axis=0)
            augmented[:,:3]+=rng.uniform(-.003/.03,.003/.03,(len(augmented),3))
            augmented[:,3:6]+=rng.normal(0,.015/.1,(len(augmented),3))
            augmented[:,6]=np.clip(augmented[:,6]+rng.normal(0,.001/.02,len(augmented)),-1.,0.)
            ax=np.r_[x,augmented].astype(np.float32);ay=np.asarray([oracle(z) for z in ax])
            tx=torch.tensor(ax);ty=torch.tensor(ay);model=skill.models[key];model.train()
            opt=torch.optim.Adam(model.parameters(),lr=.002)
            for epoch in range(a.epochs):
                order=rng.permutation(len(tx))
                for j in range(0,len(tx),512):
                    ids=order[j:j+512];loss=((model(tx[ids])-ty[ids])**2).mean()
                    opt.zero_grad();loss.backward();opt.step()
            with torch.no_grad():report['losses'][key]={'mse':float(((model(tx)-ty)**2).mean()),'physical_samples':len(x),'augmented_samples':len(augmented)}
            np.savez_compressed(a.out/f'{key}-data.npz',physical_x=x,physical_y=y,training_x=ax,training_y=ay)
            print(json.dumps({key:report['losses'][key]}),flush=True)
        report['training_seconds']=time.monotonic()-train_start
        checkpoint=a.out/'policy.pt'
        torch.save({'models':{k:v.state_dict() for k,v in skill.models.items()},'training_seed':42,
                    'training_reset_seeds':list(range(a.train_seed,a.train_seed+10)),
                    'learned':'two XYZ+jaw servo policies','scripted':'target coordinates, orientation, IK, physical guards'},checkpoint)
    report['trained']=[]
    for seed in range(a.eval_seed,a.eval_seed+a.eval_episodes):
        r,_,rows=run(a.task,seed,MicroGrasp(checkpoint),'stress-v1' if a.stress else None)
        report['trained'].append(r);(a.out/f'seed-{seed}-trace.json').write_text(json.dumps(rows))
        print(json.dumps({'trained':seed,'passed':r['passed'],'steps':r['steps'],'rise':r['max_rise_m'],'phase':r['last']['phase'] if r['last'] else None}),flush=True)
    report['total_seconds']=time.monotonic()-all_start
    report['checkpoint']=str(checkpoint);report['checkpoint_sha256']=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    report['parameters']=sum(p.numel() for m in MicroGrasp(checkpoint).models.values() for p in m.parameters())
    report['successes']=sum(r['passed'] for r in report['trained'])
    (a.out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'successes':report['successes'],'episodes':len(report['trained']),'seconds':report['total_seconds']}),flush=True)

if __name__=='__main__':main()
