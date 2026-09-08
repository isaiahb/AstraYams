"""Freeze a presentation bundle from measured results; never train or alter physics."""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/hackathon-demo'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'videos').mkdir(exist_ok=True);(OUT/'evidence').mkdir(exist_ok=True)
 paths={'pickup':'runs/micro-grasp-v1/report.json','early_chain':'runs/full-micro-composition-v1/report.json','nominal':'runs/full-micro-composition-v3-final-nominal/report.json','stress':'runs/full-micro-composition-v3-final-stress/report.json','layouts':'runs/skill-layout-cases-v1/report.json','replay':'runs/full-micro-composition-v3-final-render/report.json','grid_audit':'runs/skill-layout-cases-v1-grid/audit.json','visual':'runs/visual-policy-v2-32episodes-evaluation/report.json'}
 r={k:read(v) for k,v in paths.items()}
 assert all(a['exact_telemetry_within_1e_minus8'] for a in r['replay']['audits'])
 assert r['nominal']['model_checks']['passed'] and not r['nominal']['reset_between_skills']
 checkpoints=[]
 for name,expected in r['nominal']['checkpoint_sha256'].items():
  p=ROOT/name
  if not p.exists():raise ValueError('Checkpoint path missing: '+name)
  assert sha(p)==expected,'Frozen checkpoint changed: '+name
  checkpoints.append({'path':name,'sha256':expected})
 sources=[]
 for key,path in paths.items():
  dest=OUT/'evidence'/f'{key}.json';shutil.copyfile(ROOT/path,dest)
  sources.append({'id':key,'path':str(dest.relative_to(ROOT)),'source_path':path,'sha256':sha(dest)})
 video_specs=[('failure','Earlier chain stalls at insertion','runs/full-micro-composition-v1-render-reviewed/seed-2500-replay.mp4','Selected failed development trial; earlier chain scored 2/10. Different seeds from final evaluation.'),('success','Composed pickup, alignment and insertion','runs/full-micro-composition-v3-final-render/seed-5000-replay.mp4','First final nominal trial, seed 5000; final nominal set 20/20.'),('generalization','Different part locations and key rotations','runs/skill-layout-cases-v1-grid/four-physical-generalization-trials.mp4','Four displayed trials from six named layout cases; all six passed. Same geometry; vertical insertion axis.')]
 videos=[]
 for key,title,path,caption in video_specs:
  dst=OUT/'videos'/f'{key}.mp4';shutil.copyfile(ROOT/path,dst)
  duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(dst)],text=True))
  rel=str(dst.relative_to(ROOT));videos.append({'id':key,'title':title,'caption':caption,'path':rel,'url':'/'+rel,'absolute_path':str(dst),'duration_seconds':duration,'sha256':sha(dst),'kind':'audited saved-action simulation replay'})
 pickup=r['pickup'];before=sum(x['passed'] for x in pickup['untrained']);after=sum(x['passed'] for x in pickup['trained'])
 assert [x['seed'] for x in pickup['untrained']]==[x['seed'] for x in pickup['trained']]
 manifest={'schema_version':1,'title':'AstraFactory — an AI that creates the robotics skills it is missing','status':'frozen presentation evidence','headline':'Build the task. Train the skill. Test it. Compose it.','scope_label':'Simulation-state observations • learned specialists + conventional control • no hardware validation','summary':'A custom keyed-insertion simulation with physical gripper contact and a composed small-policy chain. Prepared experiment evidence, not live training footage.','metrics':[{'id':'pickup','label':'Paired pickup learning','value':f'{before}/5 → {after}/5','detail':'Same five development seeds, before and after imitation training; unchanged control scaffold.','source':'pickup'},{'id':'training','label':'Pickup model training','value':f"{pickup['training_seconds']:.2f} seconds",'detail':'CPU training for two 1,540-parameter pickup specialists only; excludes data generation, evaluation and downstream skill training.','source':'pickup'},{'id':'nominal','label':'Final nominal insertion','value':f"{r['nominal']['successes']}/{r['nominal']['episodes']}",'detail':'Frozen chain; final nominal seeds 5000–5019.','source':'nominal'},{'id':'stress','label':'Final randomized insertion','value':f"{r['stress']['successes']}/{r['stress']['episodes']}",'detail':'Frozen chain; final stress seeds 5100–5119. Declared variation, same part geometry.','source':'stress'}],
 'skills':[{'name':'Acquire','parameters':1540},{'name':'Lift','parameters':1540},{'name':'Align','parameters':72},{'name':'Insert','parameters':90}], 'total_learned_parameters':3242,'videos':videos,'sources':sources,'checkpoints':checkpoints,
 'learning_story':['Define CAD parts, contact task and independent success criteria.','Generate privileged teacher demonstrations; train small imitation-learning specialists.','Observe the early chain stall, correct an insertion-teacher gating bug, retrain the correction.','Freeze checkpoints and evaluate the composed chain on reserved nominal and randomized trials.'],
 'limitations':['Runtime uses exact simulator state, scripted targets/skill guards, IK and stabilization.','Physical MuJoCo contact: no welded peg or reset between composed skills. Dynamics are not hardware-calibrated.','This evidence is imitation learning and engineered control; the tested PPO residual was rejected.','Success means insertion and hold, not release, retention after release, or a complete manufactured assembly.','Early chain 2/10 and final 20/20 use different seed sets; do not call that a paired comparison.'],
 'visual_status':{'promoted':False,'rgb_successes':r['visual']['summaries']['trained_rgb']['successes'],'blank_rgb_successes':r['visual']['summaries']['blank_rgb']['successes'],'episodes_per_condition':5,'label':'Visual student: no demonstrated benefit; not promoted'},'runbook':'docs/HACKATHON-DEMO.md'}
 (OUT/'final-demo.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({'manifest':str(OUT/'final-demo.json'),'videos':len(videos),'verified_checkpoints':len(checkpoints),'metrics':manifest['metrics']},indent=2))
if __name__=='__main__':main()
