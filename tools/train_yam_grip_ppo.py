"""Auditable tiny PPO trial and continuous handoffs on the existing YAM model."""
import argparse,contextlib,hashlib,json,time
from pathlib import Path
import numpy as np,torch,mujoco
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from astrafactory.grip_regulation import GripRegulationEnv,make_bank,NumpyActor,actor_observation,jaw_action,score,TASK,DT
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp


def dump(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')


def evaluate(actor,bank,goals):
    e=GripRegulationEnv(bank);rows=[]
    for i,s in enumerate(bank):
        goal=float(goals[i%len(goals)]);obs,_=e.reset(options={'index':i,'goal':goal})
        for _ in range(150):
            obs,_,done,trunc,info=e.step(actor(obs,e.base,goal))
            if done or trunc:break
        rows.append(dict(seed=s['seed'],**info))
    e.close();return rows


def export(policy,out):
    layers=[policy.policy.mlp_extractor.policy_net[0],policy.policy.mlp_extractor.policy_net[2],policy.policy.action_net]
    arrays={}
    for i,l in enumerate(layers):arrays[f'w{i}']=l.weight.detach().cpu().numpy();arrays[f'b{i}']=l.bias.detach().cpu().numpy()
    np.savez(out,**arrays)


def full_chain(actor,seed,goal,out=None):
    e=CurriculumEnv(TASK);e.reset(seed=seed);w=MicroGrasp('runs/micro-grasp-v1/policy.pt')
    states=[];trace=[];passed=False;peak=0.;first_close=None
    for _ in range(e.horizon):
        before=e.data.qpos.copy();a=w.act(e)
        if w.phase!='reach':
            if first_close is None:first_close=float(e.data.time)
            a[6]=jaw_action(e,actor(actor_observation(e,goal)))[6]
        assert np.array_equal(before,e.data.qpos),'Execution state changed outside physics'
        _,_,done,trunc,info=e.step(a);sc=score(e,goal);peak=max(peak,sc['load_n'])
        states.append(e.data.qpos.copy());trace.append(dict(time=float(e.data.time),phase=w.phase,**sc))
        passed=w.handoff(e)
        if passed or done or trunc or sc['load_n']>12:break
    row=dict(seed=seed,goal_n=goal,handoff_success=bool(passed),elapsed_sim_s=float(e.data.time),
             peak_load_n=peak,final_load_n=trace[-1]['load_n'],final_load_in_band=trace[-1]['in_band'],
             phase=w.phase,handoffs=w.handoffs,reset_between_skills=False)
    if out:
        np.savez_compressed(out/f'chain-{seed}.npz',qpos=states)
        dump(out/f'chain-{seed}.json',dict(result=row,trace=trace))
    e.close();return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--steps',type=int,default=16384);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2);start=time.perf_counter()
    proposal=dict(algorithm='PPO from scratch; no behavior-cloning update',actor_layers=[11,16,16,1],control_hz=50,
        training_seeds=list(range(83000,83008)),development_seeds=list(range(83100,83103)),holdout_seeds=list(range(83200,83206)),
        goals_n=[4.,6.],training_steps_per_round=a.steps,rounds=2,
        acceptance='Final 0.3 seconds within ±20% of requested combined jaw contact load, bilateral contact, no held-object drop, no >12N contact load. Promote only if held-out success exceeds the frozen fixed-jaw baseline; show all outcomes.',
        learned='Jaw target increments up to0.3mm per20ms, from encoder/command/motor-effort inputs and requested load.',
        privileged='Reward and evaluation use actual simulated contact forces; physical prefix generator and upstream/downstream use privileged poses and scripted IK/guards.',
        scope='One rigid-part load regulation pilot, not full dexterity, vision control, real hardware validation, or a strawberry-safe force model.',
        source_sha256={s:hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in [__file__,'src/astrafactory/grip_regulation.py','tasks/yam_contact_curriculum/scene.xml','tasks/yam_contact_curriculum/task.json','runs/micro-grasp-v1/policy.pt']})
    dump(a.out/'proposal.json',proposal)
    bank_start=time.perf_counter();bank=make_bank(proposal['training_seeds']);dev=make_bank(proposal['development_seeds']);bank_seconds=time.perf_counter()-bank_start
    dump(a.out/'prefixes.json',[dict(seed=s['seed'],mode=s['mode'],physical_steps=s['steps']) for s in bank+dev])
    env=DummyVecEnv([lambda:GripRegulationEnv(bank) for _ in range(4)])
    policy=PPO('MlpPolicy',env,learning_rate=.001,n_steps=256,batch_size=256,n_epochs=10,gamma=.98,gae_lambda=.95,ent_coef=.005,
               policy_kwargs={'net_arch':dict(pi=[16,16],vf=[16,16]),'log_std_init':-.8},seed=73,device='cpu',verbose=0)
    with torch.no_grad():policy.policy.action_net.weight.zero_();policy.policy.action_net.bias.fill_(.7)
    initial= lambda obs,e,g:policy.predict(obs,deterministic=True)[0]
    untrained=evaluate(initial,dev,[4.25,5.,5.75]);policy.save(a.out/'initial')
    fixed=lambda obs,e,g:np.array([np.clip((-.002-e.target[6])/.0003,-1,1)],dtype=np.float32)
    baseline=evaluate(fixed,dev,[4.25,5.,5.75]);dump(a.out/'development-baselines.json',dict(untrained=untrained,fixed=baseline))
    candidates=[]
    for round_index in [1,2]:
        t=time.perf_counter();policy.learn(total_timesteps=a.steps,reset_num_timesteps=round_index==1);seconds=time.perf_counter()-t
        path=a.out/f'round-{round_index}';policy.save(path);export(policy,a.out/f'actor-{round_index}.npz');actor=NumpyActor(a.out/f'actor-{round_index}.npz')
        rows=evaluate(lambda obs,e,g:actor(obs),dev,[4.25,5.,5.75]);candidate=dict(round=round_index,training_seconds=seconds,successes=sum(r['is_success'] for r in rows),episodes=len(rows),rows=rows)
        candidates.append(candidate);dump(a.out/f'round-{round_index}.json',candidate);print(json.dumps({k:v for k,v in candidate.items() if k!='rows'}),flush=True)
    env.close();chosen=max(candidates,key=lambda r:(r['successes'],-np.mean([x['relative_error'] for x in r['rows']]),-r['round']))
    actor=NumpyActor(a.out/f"actor-{chosen['round']}.npz");selected=PPO.load(a.out/f"round-{chosen['round']}",device='cpu')
    checks=[];rng=np.random.default_rng(1)
    for x in rng.normal(size=(100,11)).astype(np.float32):checks.append(float(np.max(abs(actor(x)-selected.predict(x,deterministic=True)[0]))))
    assert max(checks)<1e-5
    x=actor_observation(GripRegulationEnv(bank).base,5.) if False else np.zeros(11,dtype=np.float32)
    for _ in range(1000):actor(x)
    t=time.perf_counter()
    for _ in range(20000):actor(x)
    us=(time.perf_counter()-t)*1e6/20000
    held=make_bank(proposal['holdout_seeds']);held_base=evaluate(fixed,held,[4.25,5.,5.75]);held_new=evaluate(lambda obs,e,g:actor(obs),held,[4.25,5.,5.75])
    chain=[full_chain(actor,s,5.,a.out) for s in proposal['holdout_seeds'][:3]]
    report=dict(proposal=proposal,prefix_seconds=bank_seconds,untrained=untrained,baseline=baseline,candidates=candidates,selected_round=chosen['round'],
        actor_parameters=sum(v.size for v in [*actor.w,*actor.b]),actor_inference_mean_us=us,actor_export_max_error=max(checks),
        holdout_baseline=held_base,holdout_candidate=held_new,holdout_baseline_successes=sum(r['is_success'] for r in held_base),holdout_candidate_successes=sum(r['is_success'] for r in held_new),
        continuous_chains=chain,training_seconds=sum(c['training_seconds'] for c in candidates),total_seconds=time.perf_counter()-start,
        promoted=sum(r['is_success'] for r in held_new)>sum(r['is_success'] for r in held_base) and all(r['handoff_success'] and r['peak_load_n']<=12 and r['final_load_in_band'] for r in chain))
    dump(a.out/'report.json',report);print(json.dumps({k:report[k] for k in ['actor_parameters','actor_inference_mean_us','training_seconds','holdout_baseline_successes','holdout_candidate_successes','promoted','total_seconds']}),flush=True)

if __name__=='__main__':main()
