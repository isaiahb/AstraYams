"""Extract reviewable contact evidence and candidate interventions from a rollout.

This deterministic triage does not establish causes or automatically change rewards.
Astra reviews these measurements together with video before launching experiments.
"""
import argparse
import hashlib
import json
from pathlib import Path


def analyze(path):
    path=Path(path)
    raw=json.loads(path.read_text())
    rows=raw if isinstance(raw,list) else raw.get('trace',raw.get('rows',[]))
    if not rows:raise ValueError('Expected nonempty trace rows')
    initial_z=float(rows[0].get('peg_z_m',rows[0].get('z',0)))
    segments=[];start=None;max_lift=0.;peak=None;last_held=False;lost=[]
    for i,row in enumerate(rows):
        z=float(row.get('peg_z_m',row.get('z',initial_z)))
        f=row.get('forces',[row.get('left_force_n',0),row.get('right_force_n',0),row.get('nonfinger_support_force_n',0)])
        t=float(row.get('sim_time',row.get('time',(row.get('step',i+1))*.02)))
        held=z-initial_z>=.02 and f[0]>.02 and f[1]>.02 and f[2]<.01
        if held and start is None:start=t
        if not held and start is not None:
            segments.append({'start_s':start,'end_s':previous_t,'duration_s':previous_t-start});start=None
        if last_held and not held:lost.append({'time_s':t,'peg_z_m':z,'forces_n':f,'phase':row.get('phase','unknown')})
        last_held=held;previous_t=t
        max_lift=max(max_lift,z-initial_z)
        load=row.get('episode_peak_force_n',row.get('peak_contact_force_n'))
        if load is not None:peak=max(peak or 0.,float(load))
    if start is not None:segments.append({'start_s':start,'end_s':previous_t,'duration_s':previous_t-start})
    final=rows[-1];success=bool(final.get('is_success',False))
    proposals=[]
    longest=max((s['duration_s'] for s in segments),default=0.)
    if longest<.5:
        proposals.append({'hypothesis':'Acquisition or retention is the bottleneck; video review must distinguish them.',
          'candidate':'Separate acquire from lift; include finger forces and vertical velocity in observations.',
          'training_rubric':'Reward sustained unsupported bilateral lift, not finger proximity alone; penalize dropping and excessive force.',
          'randomization':'Mild friction/mass and pickup pose variation in training only.'})
    elif not success:
        proposals.append({'hypothesis':'A grasp was sustained; later pose control or handoff coverage may be the bottleneck.',
          'candidate':'Train downstream skill on actual grasp handoff states, including measured grip offsets.',
          'training_rubric':'Reward decreasing pose error with contact retention; insertion progress conditional on alignment and force.',
          'randomization':'Vary reached grip offset via physical prefixes, then socket pose; report separately from nominal.'})
    if peak is not None and peak>45:
        proposals.append({'hypothesis':'Contact load exceeded the frozen success-window force limit somewhere in the episode.',
          'candidate':'Inspect first force spike and approach velocity before changing descent scale or training examples.',
          'training_rubric':'Bound force penalty and test whether the policy avoids all contact rather than completing the task.',
          'randomization':'Do not relax the evaluation threshold.'})
    return {'schema_version':1,'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
       'method':'deterministic telemetry triage; proposed hypotheses require Astra/video review',
       'time_assumption':'uses sim_time/time when present; otherwise 20 ms per step from frozen task',
       'measurements':{'max_rise_from_first_logged_sample_m':max_lift,'longest_unsupported_bilateral_lift_s':longest,
           'support_segments':segments,'lost_support_events':lost,'episode_peak_force_n':peak,
           'final_success':success,'final_reason':final.get('reason'),'samples':len(rows)},
       'candidate_interventions':proposals,'evaluation_changed':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();report=analyze(a.trace);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['measurements'],indent=2))
