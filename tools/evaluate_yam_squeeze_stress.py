"""Freeze the selected PPO; test complete chains under unseen physical variations."""
import argparse,hashlib,time
from pathlib import Path
import json,numpy as np
from astrafactory.grip_regulation import NumpyActor
from train_yam_squeeze_ppo import full_chain,dump


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    report=json.loads((a.run/'report.json').read_text());out=a.run/'stress';out.mkdir(exist_ok=False)
    checkpoint=a.run/f"actor-{report['selected_round']}.npz";actor=NumpyActor(checkpoint)
    seeds=list(range(84300,84312));goals=[2.75,3.5,4.25]
    dump(out/'proposal.json',dict(seeds=seeds,goals_n=goals,profile='stress-v1',actor_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
         ranges='Object mass and shared sliding friction 0.8–1.2x; XY randomization ±4mm and yaw ±0.04rad, outside training ±2mm/±0.02rad.',
         calibration='Engineering sensitivity assumptions, not measured hardware distributions.',
         acceptance='Physical lift handoff, final net squeeze within ±20% and measured peak axial squeeze <=8N; full chain from reset with no transition reset.',
         selection='Actor frozen before stress evaluation; results will not select another checkpoint.'))
    methods={'ppo':actor,'feedback':lambda x:np.array([np.clip(x[5]*6.,-1,1)],dtype=np.float32),
             'fixed':lambda x:np.array([np.clip((-.002-x[2]*.02)/.0003,-1,1)],dtype=np.float32)}
    start=time.perf_counter();results={}
    for name,policy in methods.items():
        target=out/name;target.mkdir();rows=[]
        for i,seed in enumerate(seeds):
            r=full_chain(policy,seed,goals[i%len(goals)],target,stress=True)
            r['passed']=bool(r['handoff_success'] and r['final_load_in_band'] and r['peak_load_n']<=8);rows.append(r)
        results[name]=dict(successes=sum(r['passed'] for r in rows),episodes=len(rows),trials=rows)
        dump(out/f'{name}.json',results[name]);print(name,results[name]['successes'],len(rows),flush=True)
    dump(out/'report.json',dict(methods=results,seconds=time.perf_counter()-start,frozen=True))

if __name__=='__main__':main()
