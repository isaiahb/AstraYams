"""Tiny PPO descent residual: real RL, physically reached training prefixes.

Only vertical residual is learned here; frozen BC controls other directions.
Training restores complete physical snapshots. Paired full-chain evaluation never
restores or resets between skills. Privileged sensing/IK/guards remain explicit.
"""
import argparse,copy,hashlib,json,time
from pathlib import Path
import gymnasium as gym
from gymnasium import spaces
import mujoco,numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_downstream_skills import DownstreamSkill,observe,scaffold
from astrafactory.skill_randomization import SkillRandomization
from train_downstream_skills import snapshot,restore_snapshot
from collect_demonstrations import task_hashes


def save_snapshot(e,path):
    state=snapshot(e);arrays={k:v for k,v in state.items() if isinstance(v,np.ndarray)}
    np.savez_compressed(path,**arrays)
    meta={k:v for k,v in state.items() if k not in arrays}
    path.with_suffix('.json').write_text(json.dumps(meta,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item()))


def learned_prefix(e,seed,grasp,align,resetter=None):
    _,ri=(resetter or e).reset(seed=seed);grasp.start(e);align.start(e);phase='grasp';actions=[]
    for _ in range(e.horizon):
        skill=grasp if phase=='grasp' else align
        before=e.data.qpos.copy();a=skill.act(e);assert np.array_equal(before,e.data.qpos)
        _,_,done,trunc,info=e.step(a);actions.append(a)
        ready=skill.handoff(e) if phase=='grasp' else skill.handoff(e,info)
        if ready:
            if phase=='grasp':phase='align';align.start(e)
            else:return True,info,ri,actions
        if done or trunc:return False,info,ri,actions
    return False,info,ri,actions


class ResidualEnv(gym.Env):
    def __init__(self,bank,checkpoint):
        self.base=CurriculumEnv('tasks/yam_contact_curriculum')
        self.skill=DownstreamSkill(checkpoint,'insert');self.bank=list(bank)
        self.observation_space=spaces.Box(-np.inf,np.inf,(15,),dtype=np.float32)
        self.action_space=spaces.Box(-1,1,(1,),dtype=np.float32)
        self.episode_rows=[];self.t=0
    def obs(self):return observe(self.base,'insert').astype(np.float32)
    def reset(self,seed=None,options=None):
        super().reset(seed=seed)
        p=self.bank[int(self.np_random.integers(len(self.bank)))];restore_snapshot(self.base,p)
        self.t=0;self.total=0.;self.components=np.zeros(5)
        return self.obs(),{'prefix':str(p)}
    def step(self,action):
        e=self.base;z=e.data.site_xpos[e.task.pid,2];old=abs(z-e.task.goal[2])
        correction=observe(e,'insert')@self.skill.weight
        # At most 1 mm vertical requested residual, taper near seating.
        scale=.05 if z<.02 else .1
        correction[2]+=float(np.clip(action[0],-1,1))*scale
        a=scaffold(e,'insert',correction);_,_,done,trunc,info=e.step(a)
        distance=abs(e.data.site_xpos[e.task.pid,2]-e.task.goal[2])
        progress=20*(old-distance)/.05
        alignment=-.005*min(info['xy_error_m']/.001,10)-.05*min(info['orientation_error_rad'],1)
        force=-.003*max(info['peak_contact_force_n']-15,0)
        effort=-.001*float(np.square(action).sum())
        terminal=10*int(info['is_success'])-10*int(info['reason']=='force_limit')
        values=np.array([progress,alignment,force,effort,terminal]);reward=float(values.sum())
        self.components+=values;self.total+=reward;self.t+=1
        info['reward_components']=dict(zip(['distance_progress','alignment','force','effort','terminal'],values.tolist()))
        if done or trunc:self.episode_rows.append({'steps':self.t,'return':self.total,'components':self.components.tolist(),'final':dict(info)})
        return self.obs(),reward,done,trunc,info
    def close(self):self.base.close()


class Progress(BaseCallback):
    def __init__(self,out):super().__init__();self.out=out
    def _on_step(self):
        if self.num_timesteps%1024==0:
            row={'timesteps':self.num_timesteps,'episodes':len(self.training_env.envs[0].unwrapped.episode_rows)}
            print(json.dumps(row),flush=True)
            with (self.out/'progress.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        return True


def evaluate(model,args,label):
    e=CurriculumEnv('tasks/yam_contact_curriculum');g=MicroGrasp(args.grasp)
    align=DownstreamSkill(args.downstream/'align.npz','align');ins=DownstreamSkill(args.downstream/'insert.npz','insert')
    rows=[]
    for seed in range(2400,2410):
        reached,info,ri,actions=learned_prefix(e,seed,g,align)
        trace=[]
        if reached:
            while e.steps<e.horizon:
                x=observe(e,'insert');r=np.zeros(1) if model is None else model.predict(x.astype(np.float32),deterministic=True)[0]
                correction=x@ins.weight;z=e.data.site_xpos[e.task.pid,2]
                correction[2]+=float(r[0])*(.05 if z<.02 else .1)
                action=scaffold(e,'insert',correction);_,_,done,trunc,info=e.step(action);actions.append(action)
                trace.append({'step':e.steps,'residual':r.tolist(),'info':dict(info)})
                if done or trunc:break
        row={'seed':seed,'is_success':bool(info['is_success']),'reached_insert':reached,'final':info};rows.append(row)
        np.savez_compressed(args.out/f'{label}-{seed}-actions.npz',actions=np.asarray(actions))
        (args.out/f'{label}-{seed}-trace.json').write_text(json.dumps(trace))
        print(json.dumps({'evaluation':label,**row}),flush=True)
    e.close();(args.out/f'{label}-evaluation.json').write_text(json.dumps(rows,indent=2));return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--steps',type=int,default=8192)
    p.add_argument('--grasp',type=Path,default=Path('runs/micro-grasp-v1/policy.pt'));p.add_argument('--downstream',type=Path,default=Path('runs/downstream-v2-dr'))
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2);start=time.monotonic()
    e=CurriculumEnv('tasks/yam_contact_curriculum');dr=SkillRandomization(e)
    g=MicroGrasp(args.grasp);align=DownstreamSkill(args.downstream/'align.npz','align');bank=[];prefix_results=[]
    for seed in range(100,110):
        reached,info,ri,actions=learned_prefix(e,seed,g,align,dr)
        prefix_results.append({'seed':seed,'reached':reached,'final':info,'reset_info':ri})
        if reached:
            path=args.out/f'prefix-{seed}.npz';save_snapshot(e,path);bank.append(path)
    e.close();(args.out/'prefix-report.json').write_text(json.dumps(prefix_results,indent=2))
    if not bank:raise RuntimeError('No physically reached training prefixes')
    baseline=evaluate(None,args,'baseline')
    env=ResidualEnv(bank,args.downstream/'insert.npz')
    model=PPO('MlpPolicy',env,learning_rate=3e-4,n_steps=512,batch_size=128,n_epochs=5,gamma=.99,
       policy_kwargs={'net_arch':dict(pi=[16,16],vf=[16,16]),'log_std_init':-1.5},device='cpu',seed=73,verbose=0)
    with torch.no_grad():model.policy.action_net.weight.zero_();model.policy.action_net.bias.zero_()
    model.save(args.out/'initial-policy');train_start=time.monotonic()
    model.learn(total_timesteps=args.steps,callback=Progress(args.out));train_seconds=time.monotonic()-train_start
    model.save(args.out/'policy');(args.out/'training-episodes.json').write_text(json.dumps(env.episode_rows,indent=2))
    candidate=evaluate(model,args,'candidate')
    report={'scope':'PPO vertical insertion residual on frozen learned BC; continuous learned grasp/alignment evaluation; privileged state, scripted IK and guards.',
      'training_snapshot_resets':True,'evaluation_resets_between_skills':False,'training_seeds':list(range(100,110)),
      'evaluation_seeds':list(range(2400,2410)),'baseline':baseline,'candidate':candidate,
      'baseline_successes':sum(r['is_success'] for r in baseline),'candidate_successes':sum(r['is_success'] for r in candidate),
      'timesteps':model.num_timesteps,'training_seconds':train_seconds,'wall_seconds':time.monotonic()-start,
      'actor_parameters':sum(p.numel() for p in model.policy.mlp_extractor.policy_net.parameters())+sum(p.numel() for p in model.policy.action_net.parameters()),
      'task_hashes':task_hashes('tasks/yam_contact_curriculum'),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'reward':'20*abs-distance-progress/.05, bounded alignment penalty, force above15N penalty, action effort, +10 actualsuccess/-10 forceabort; no evaluator edits'}
    (args.out/'report.json').write_text(json.dumps(report,indent=2));env.close();print(json.dumps({k:report[k] for k in ['baseline_successes','candidate_successes','training_seconds','actor_parameters']}),flush=True)

if __name__=='__main__':main()
