"""Predeclared axial-squeeze PPO pilot; fixed comparator and disjoint seed sets."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np,torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from astrafactory.grip_regulation import make_bank,NumpyActor,jaw_action,TASK
from astrafactory.squeeze_skill import SqueezeEnv,squeeze_observation,squeeze_score
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from train_yam_grip_ppo import export,dump


def evaluate(actor,bank,goals=(2.75,3.5,4.25)):
    e=SqueezeEnv(bank);rows=[]
    for i,s in enumerate(bank):
        obs,_=e.reset(options={'index':i,'goal':goals[i%len(goals)]})
        while True:
            obs,_,done,trunc,info=e.step(actor(obs))
            if done or trunc:break
        rows.append(dict(seed=s['seed'],**info))
    e.close();return rows


def full_chain(actor,seed,goal,out,stress=False):
    e=CurriculumEnv(TASK)
    if stress:
        from astrafactory.skill_randomization import SkillRandomization
        _,reset_info=SkillRandomization(e,'stress-v1','stress').reset(seed=seed)
    else:_,reset_info=e.reset(seed=seed)
    w=MicroGrasp('runs/micro-grasp-v1/policy.pt')
    states=[];actions=[];trace=[];passed=False;peak=0.
    for _ in range(e.horizon):
        before=e.data.qpos.copy();a=w.act(e)
        if w.phase!='reach':a[6]=jaw_action(e,actor(squeeze_observation(e,goal)))[6]
        assert np.array_equal(before,e.data.qpos),'Controller changed physical state'
        _,_,done,trunc,info=e.step(a);sc=squeeze_score(e,goal);peak=max(peak,sc['load_n'])
        states.append(e.data.qpos.copy());actions.append(a.copy())
        trace.append(dict(time=float(e.data.time),phase=w.phase,**sc));passed=w.handoff(e)
        if passed or done or trunc or sc['load_n']>8:break
    row=dict(seed=seed,goal_n=goal,handoff_success=bool(passed),elapsed_sim_s=float(e.data.time),
             peak_load_n=peak,final_load_n=trace[-1]['load_n'],final_load_in_band=trace[-1]['in_band'],
             phase=w.phase,handoffs=w.handoffs,reset_between_skills=False,domain_randomization=reset_info.get('domain_randomization'))
    if out:
        np.savez_compressed(out/f'chain-{seed}.npz',qpos=states,actions=actions)
        dump(out/f'chain-{seed}.json',dict(result=row,trace=trace))
    e.close();return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=a.resume);torch.set_num_threads(2);start=time.perf_counter()
    proposal=dict(algorithm='PPO from scratch, closure action mean initialized to +0.1; no BC',
        metric='Sum of net axial object-on-finger squeeze forces, not the v1 sum of magnitudes',
        correction='Net-force projection has mechanical meaning. The v1 task remains rejected; scores are not interchangeable.',
        actor_layers=[6,16,16,1],control_hz=50,physics_hz=500,
        train_seeds=list(range(84000,84008)),dev_seeds=list(range(84100,84103)),holdout_seeds=list(range(84200,84206)),
        goal_range_n=[2.5,4.5],rounds=3,steps_per_round=32768,
        acceptance='Final 0.3s within ±20% of requested net axial squeeze; both fingers >0.05N; no held drop >10mm or axial squeeze >8N. No thresholds change after training.',
        promotion='Exceed the constant-jaw comparator on held-out trials AND pass all three continuous approach-grip-lift chains with final load in band and peak <=8N.',
        scope='Rigid-part simulation only; no new IK/pose policy, tactile hardware, strawberry safety, or real-arm transfer claim.',
        observations='Jaw encoder, velocity, commanded position, motor effort, requested squeeze and requested squeeze minus motor effort. No object pose or true contact force in the actor.',
        limitations='Effort-to-squeeze relationship has not been calibrated on physical YAM; upstream BC and handoff guards use simulator state.',
        source_sha256={s:hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in [__file__,'src/astrafactory/squeeze_skill.py','src/astrafactory/grip_regulation.py','tasks/yam_contact_curriculum/scene.xml','tasks/yam_contact_curriculum/task.json']})
    if a.resume:proposal=json.loads((a.out/'proposal.json').read_text())
    else:dump(a.out/'proposal.json',proposal)
    bank=make_bank(proposal['train_seeds']);dev=make_bank(proposal['dev_seeds'])
    dump(a.out/'prefixes.json',[dict(seed=s['seed'],mode=s['mode'],steps=s['steps']) for s in bank+dev])
    env=DummyVecEnv([lambda:SqueezeEnv(bank) for _ in range(4)])
    policy=PPO('MlpPolicy',env,learning_rate=.002,n_steps=256,batch_size=256,n_epochs=10,gamma=.95,gae_lambda=.95,ent_coef=.001,
               policy_kwargs={'net_arch':dict(pi=[16,16],vf=[16,16]),'log_std_init':-1.2},seed=74,device='cpu',verbose=0)
    with torch.no_grad():policy.policy.action_net.weight.zero_();policy.policy.action_net.bias.fill_(.1)
    fixed=lambda x:np.array([np.clip((-.002-x[2]*.02)/.0003,-1,1)],dtype=np.float32)
    feedback=lambda x:np.array([np.clip(x[5]*6.,-1,1)],dtype=np.float32)
    if a.resume:
        b=json.loads((a.out/'development-baselines.json').read_text());base,fb,untrained=b['fixed'],b['feedback'],b['untrained']
        candidates=[json.loads(f.read_text()) for f in sorted(a.out.glob('round-*.json'))]
        last=max(c['round'] for c in candidates);policy=PPO.load(a.out/f'round-{last}',env=env,device='cpu');policy.set_random_seed(74+last)
        dump(a.out/'resumption.json',dict(reason='Disk full while saving round 2; unsaved optimizer work lost. Continue from last complete round.',last_complete_round=last,
            resumed_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),timing='Report sums completed retained training rounds. Lost round duration was not recorded. Total seconds covers this resumed invocation only.'))
    else:
        base=evaluate(fixed,dev);fb=evaluate(feedback,dev);untrained=evaluate(lambda x:policy.predict(x,deterministic=True)[0],dev)
        dump(a.out/'development-baselines.json',dict(fixed=base,feedback=fb,untrained=untrained));candidates=[]
    for r in [1,2,3]:
        if any(c['round']==r for c in candidates):continue
        t=time.perf_counter();policy.learn(total_timesteps=32768,reset_num_timesteps=r==1);seconds=time.perf_counter()-t
        policy.save(a.out/f'round-{r}');export(policy,a.out/f'actor-{r}.npz');actor=NumpyActor(a.out/f'actor-{r}.npz')
        rows=evaluate(actor,dev);c=dict(round=r,training_seconds=seconds,successes=sum(x['is_success'] for x in rows),episodes=len(rows),rows=rows)
        candidates.append(c);dump(a.out/f'round-{r}.json',c);print(json.dumps({k:v for k,v in c.items() if k!='rows'}),flush=True)
    env.close();chosen=max(candidates,key=lambda c:(c['successes'],-np.mean([r['relative_error'] for r in c['rows']]),-c['round']))
    actor=NumpyActor(a.out/f"actor-{chosen['round']}.npz");selected=PPO.load(a.out/f"round-{chosen['round']}")
    errors=[float(np.max(abs(actor(x)-selected.predict(x,deterministic=True)[0]))) for x in np.random.default_rng(1).normal(size=(100,6)).astype(np.float32)]
    assert max(errors)<1e-5
    x=np.zeros(6,dtype=np.float32)
    for _ in range(1000):actor(x)
    t=time.perf_counter()
    for _ in range(20000):actor(x)
    us=(time.perf_counter()-t)*1e6/20000
    held=make_bank(proposal['holdout_seeds']);hb=evaluate(fixed,held);hf=evaluate(feedback,held);hn=evaluate(actor,held)
    chains=[full_chain(actor,s,3.5,a.out) for s in proposal['holdout_seeds'][:3]]
    report=dict(proposal=proposal,development_baselines=dict(fixed=base,feedback=fb,untrained=untrained),candidates=candidates,selected_round=chosen['round'],
        actor_parameters=sum(v.size for v in [*actor.w,*actor.b]),actor_export_max_error=max(errors),actor_inference_mean_us=us,
        training_seconds=sum(c['training_seconds'] for c in candidates),total_seconds=time.perf_counter()-start,
        holdout_baseline=hb,holdout_feedback=hf,holdout_candidate=hn,continuous_chains=chains,
        holdout_baseline_successes=sum(r['is_success'] for r in hb),holdout_feedback_successes=sum(r['is_success'] for r in hf),holdout_candidate_successes=sum(r['is_success'] for r in hn),
        promoted=sum(r['is_success'] for r in hn)>sum(r['is_success'] for r in hb) and all(r['handoff_success'] and r['peak_load_n']<=8 and r['final_load_in_band'] for r in chains))
    dump(a.out/'report.json',report);print(json.dumps({k:report[k] for k in ['actor_parameters','training_seconds','holdout_baseline_successes','holdout_feedback_successes','holdout_candidate_successes','promoted','total_seconds']}),flush=True)

if __name__=='__main__':main()
