"""Bounded machine-tending teacher collection and local-servo distillation."""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np,torch,mujoco
from astrafactory.machine_tending import MachineTendingEnv
from astrafactory.machine_tending_policy import Workflow,Servo

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registry(status,phase,message,metrics=None,preview=None):
 p=Path('runs/skill-studio/skills.json');r=json.loads(p.read_text())
 for s in r['skills']:
  if s['id']=='machine-tending-v1':
   s.update(status=status,phase=phase,message=message,updated_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
   if metrics is not None:s['metrics']=metrics
   if preview:s['preview_path']=preview
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2)+'\n');tmp.replace(p)

def rollout(seed,models,out,label,collect=None,video=False):
 e=MachineTendingEnv('tasks/yam_machine_tending');e.reset(seed=seed);w=Workflow(models);rows=[];actions=[];qpos=[];vise=[];err=None;writer=None;renderer=None
 if video:
  import imageio.v2 as imageio
  from PIL import Image,ImageDraw,ImageFont
  renderer=mujoco.Renderer(e.model,height=360,width=540);writer=imageio.get_writer(str(out/f'{label}-{seed}.mp4'),fps=12.5,codec='libx264',quality=7,macro_block_size=1);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
  cam=mujoco.MjvCamera();cam.lookat[:]=[.28,0,.06];cam.distance=.43;cam.azimuth=135;cam.elevation=-30
 try:
  for k in range(e.horizon):
   before=e.data.qpos.copy();a=w.act(e,collect=collect);assert np.array_equal(before,e.data.qpos),'Controller changed physical state'
   _,_,done,trunc,info=e.step(a);rows.append({'step':k+1,'phase':w.phase,**info});actions.append(a.copy());qpos.append(e.data.qpos.copy());vise.append(float(e.vise_target_gap))
   if writer and k%4==0:
    renderer.update_scene(e.data,camera='overview');left=renderer.render().copy();renderer.update_scene(e.data,camera=cam);right=renderer.render().copy();im=Image.new('RGB',(1080,448),(12,23,32));im.paste(Image.fromarray(left),(0,88));im.paste(Image.fromarray(right),(540,88));d=ImageDraw.Draw(im)
    d.text((12,8),f'Machine tending | {label} | seed{seed} | {w.phase}',font=font,fill='white');d.text((12,34),('Simulation state | scripted teacher feasibility' if models is None else 'Simulation state | learned local servos + scripted workflow/IK/machine interface'),font=font,fill=(196,218,230));d.text((12,60),f"t={e.data.time:.2f}s | success={info['is_success']} | physical contact, no object attachment",font=font,fill=(255,209,110));writer.append_data(np.asarray(im))
   if done or trunc:break
 except Exception as ex:err=repr(ex)
 finally:
  if writer:writer.close();renderer.close()
  e.close()
 result={'seed':seed,'mode':label,'success':bool(rows and rows[-1]['is_success'] and err is None),'exception':err,'steps':len(rows),'final_phase':w.phase,'handoffs':w.history,'final':rows[-1] if rows else {}}
 (out/f'{label}-{seed}-trace.json').write_text(json.dumps(rows));np.savez_compressed(out/f'{label}-{seed}-actions.npz',actions=np.array(actions),vise_target=np.array(vise),qpos=np.array(qpos));(out/f'{label}-{seed}-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--teacher-only',action='store_true');p.add_argument('--episodes',type=int,default=8);p.add_argument('--updates',type=int,default=800);p.add_argument('--seed',type=int,default=56000);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2);torch.manual_seed(43);rng=np.random.default_rng(43)
 start=time.time();sources=[__file__,'src/astrafactory/machine_tending.py','src/astrafactory/machine_tending_policy.py','tasks/yam_machine_tending/task.json','tasks/yam_machine_tending/scene.xml']
 proposal={'task':'yam-machine-tending-v1','train_seeds':list(range(a.seed,a.seed+a.episodes)),'dev_seeds':list(range(57000,57005)),'reserved_final_seeds':list(range(58000,58020)),'updates':a.updates,'source_sha256':{s:sha(s) for s in sources},'scope':'Two localCartesian/angular/jaw servo models; explicit target/phase/IK/machine-command scaffold. State-based BC, not VLA or hardware.'};(a.out/'proposal.json').write_text(json.dumps(proposal,indent=2))
 data={k:[[],[]] for k in ['transport','precision']};teachers=[]
 registry('building','Physical teacher feasibility','Checking the complete contact-driven unload/load/clamp cycle before promotion.')
 for seed in proposal['train_seeds']:
  result=rollout(seed,None,a.out,'teacher',collect=data,video=seed==a.seed);teachers.append(result)
  registry('building','Collecting physical demonstrations',f'{len(teachers)}/{a.episodes} teacher trials checked; {sum(t["success"] for t in teachers)} passed.',preview=str(a.out/f'teacher-{a.seed}.mp4'))
  if a.teacher_only:break
 if a.teacher_only:
  (a.out/'report.json').write_text(json.dumps({'proposal':proposal,'teachers':teachers,'scope':'Scripted teacher feasibility only; no learned results.'},indent=2));return
 if not any(t['success'] for t in teachers):
  registry('blocked','Teacher feasibility failed','No complete teacher cycle yet. Failures preserved; no learned-success claim.');(a.out/'report.json').write_text(json.dumps({'proposal':proposal,'teachers':teachers,'blocked':'no successful teacher'}));return
 models={k:Servo() for k in data};initial={k:Servo() for k in data}
 for k in models:initial[k].load_state_dict(models[k].state_dict())
 torch.save({k:m.state_dict() for k,m in initial.items()},a.out/'initial.pt')
 registry('training','Training transport and precision servos','Behavior cloning on physical teacher traces. Evaluation has not run.')
 train_start=time.time();losses={}
 for kind,(xs,ys) in data.items():
  x=np.array(xs,dtype=np.float32);y=np.array(ys,dtype=np.float32);np.savez_compressed(a.out/f'{kind}-data.npz',observation=x,action=y)
  xt=torch.tensor(x);yt=torch.tensor(y);model=models[kind];opt=torch.optim.Adam(model.parameters(),lr=.001);log=[]
  for i in range(a.updates):
   ix=torch.tensor(rng.integers(len(x),size=256));loss=((model(xt[ix])-yt[ix])**2).mean();opt.zero_grad();loss.backward();opt.step()
   if i%100==0:log.append({'update':i,'mse':float(loss.detach())})
  losses[kind]=log;model.eval()
 train_seconds=time.time()-train_start;torch.save({k:m.state_dict() for k,m in models.items()},a.out/'policy.pt')
 registry('evaluating','Paired held-out task evaluation','Training complete. Comparing initial and trained models under the same workflow.')
 trials=[]
 for mode,model in [('initial',initial),('trained',models)]:
  for seed in proposal['dev_seeds']:trials.append(rollout(seed,model,a.out,mode,video=seed==57000))
 report={'proposal':proposal,'teachers':teachers,'trials':trials,'losses':losses,'training_seconds':train_seconds,'parameters':sum(sum(p.numel() for p in m.parameters()) for m in models.values()),'wall_seconds':time.time()-start,'checkpoint_sha256':sha(a.out/'policy.pt')};(a.out/'report.json').write_text(json.dumps(report,indent=2))
 scores={k:sum(t['success'] for t in trials if t['mode']==k) for k in ['initial','trained']};passed=scores['trained']==5
 registry('complete' if passed else 'failed','Evaluation complete',f'Initial {scores["initial"]}/5; trained {scores["trained"]}/5. '+('Simulation milestone only.' if passed else 'Not promoted; inspect failures.'),metrics=[{'label':'Initial','value':f'{scores["initial"]}/5'},{'label':'Trained','value':f'{scores["trained"]}/5'},{'label':'Training','value':f'{train_seconds:.1f}s'}],preview=str(a.out/'trained-57000.mp4'))
 print(json.dumps(scores),flush=True)
if __name__=='__main__':main()
