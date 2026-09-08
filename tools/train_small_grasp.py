"""One compact privileged Cartesian grasp BC candidate; no teacher at evaluation."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import mujoco
import torch
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_grasp_skill import Network,GraspSkill,observe,contacts
from collect_demonstrations import task_hashes,environment_source_hash

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=Path('/workspace/contact-rgb-v1'))
    p.add_argument('--task',type=Path,default=Path('tasks/yam_contact_curriculum'))
    p.add_argument('--out',type=Path,default=Path('runs/small-grasp-v1'))
    p.add_argument('--epochs',type=int,default=400)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(2);torch.manual_seed(31);rng=np.random.default_rng(31)
    env=CurriculumEnv(a.task);scratch=mujoco.MjData(env.model)
    dataset={};episodes=[]
    for split,seeds in [('train',range(100,108)),('development',range(1000,1002))]:
        xs,ys=[],[]
        for seed in seeds:
            path=a.data/split/f'episode_{seed}.npz';data=np.load(path)
            states=data['state'];actions=data['action'];labels=data['teacher_action']
            env.reset(seed=seed);error=0.;above_since=None;count=0
            for state,action,label in zip(states,actions,labels):
                error=max(error,float(np.max(np.abs(env.task.observe()-state))))
                xs.append(observe(env))
                q=np.clip(env.target+label*env.scales,env.limits[:,0],env.limits[:,1])
                scratch.qpos[:]=env.data.qpos;scratch.qpos[env.qadr]=q
                # Coupled jaw is irrelevant to tool FK, but retain physical relation.
                mujoco.mj_forward(env.model,scratch)
                xyz=scratch.site_xpos[env.task.sid].copy()
                peg=env.data.site_xpos[env.task.pid]
                ys.append(np.r_[xyz[:2]-peg[:2],xyz[2],q[6]])
                _,_,term,trunc,info=env.step(action);count+=1
                z=env.data.site_xpos[env.task.pid,2]
                if z>=.083 and above_since is None:above_since=env.data.time
                if above_since is not None and env.data.time-above_since>=.4:break
                if term or trunc:break
            episodes.append(dict(split=split,seed=seed,steps=count,max_replay_state_error=error,
                                 source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            print(json.dumps(episodes[-1]),flush=True)
        dataset[split]=(np.asarray(xs,dtype=np.float32),np.asarray(ys,dtype=np.float32))
    x,y=dataset['train'];xd,yd=dataset['development']
    mean=x.mean(0);std=np.maximum(x.std(0),1e-4);ym=y.mean(0);ys=np.maximum(y.std(0),1e-4)
    tx=torch.tensor((x-mean)/std);ty=torch.tensor((y-ym)/ys)
    dx=torch.tensor((xd-mean)/std);dy=torch.tensor((yd-ym)/ys)
    model=Network();opt=torch.optim.Adam(model.parameters(),lr=.001)
    history=[]
    for epoch in range(a.epochs):
        order=rng.permutation(len(tx))
        for start in range(0,len(tx),256):
            idx=order[start:start+256];loss=((model(tx[idx])-ty[idx])**2).mean()
            opt.zero_grad();loss.backward();opt.step()
        if (epoch+1)%50==0:
            with torch.no_grad(): row=dict(epoch=epoch+1,train_mse=float(((model(tx)-ty)**2).mean()),development_mse=float(((model(dx)-dy)**2).mean()))
            history.append(row);print(json.dumps(row),flush=True)
    checkpoint=a.out/'policy.pt'
    torch.save(dict(model=model.state_dict(),mean=mean,std=std,ymean=ym,ystd=ys,
                    minimum=y.min(0),maximum=y.max(0),training_seed=31,
                    observations='12 privileged pose/contact values',outputs='4 absolute Cartesian/jaw commands',
                    training_seeds=list(range(100,108)),development_seeds=[1000,1001]),checkpoint)
    trials=[]
    for seed in range(2000,2005):
        env.reset(seed=seed);skill=GraspSkill(checkpoint);skill.start(env)
        initial=skill.initial_z;maxrise=0.;peak=0.;bilateral=0;handoff=False
        trace=[]
        for step in range(env.horizon):
            action=skill.act(env);_,_,term,trunc,info=env.step(action)
            f=contacts(env);z=float(env.data.site_xpos[env.task.pid,2]);maxrise=max(maxrise,z-initial)
            peak=max(peak,float(info.get('episode_peak_force_n',info.get('contact_force_n',0))))
            bilateral+=int(f[0]>1e-5 and f[1]>1e-5)
            handoff=skill.handoff(env)
            trace.append(dict(step=step+1,z=z,forces=f.tolist(),action=action.tolist()))
            if handoff or term or trunc:break
        row=dict(seed=seed,handoff=handoff,steps=step+1,max_peg_rise_m=maxrise,
                 longest_qualified_seconds=skill.longest,bilateral_samples=bilateral,
                 final_info=info)
        trials.append(row);print(json.dumps(row),flush=True)
        (a.out/f'seed-{seed}-trace.json').write_text(json.dumps(trace))
    report=dict(scope='privileged compact grasp BC with scripted IK, not VLA or full insertion',
                physics_unchanged=True,no_teacher_at_evaluation=True,
                task_hashes=task_hashes(a.task),
                source_hashes={n:environment_source_hash(n) for n in ['astrafactory.contact_curriculum:CurriculumEnv','astrafactory.contact_env:ContactEnv','astrafactory.contact_grasp_skill:GraspSkill']},
                episodes=episodes,history=history,trials=trials,
                handoff_successes=sum(t['handoff'] for t in trials),evaluated_episodes=len(trials),
                handoff='20mm rise and bilateral forces with zero other support continuously at control samples for .5s, and absolute peg-tip clearance65mm',
                checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest())
    (a.out/'report.json').write_text(json.dumps(report,indent=2));env.close()
if __name__=='__main__':main()
