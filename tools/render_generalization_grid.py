"""Four exact-action challenge replays, synchronized by simulator time.

Selection JSON contains trials with seed, profile_spec, realized, trace, actions.
Yaw changes rotate the keyed hole about the vertical axis; no tilted-hole claim.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import mujoco,imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont
from astrafactory.contact_curriculum import CurriculumEnv
from check_skill_generalization import reset_challenge
from check_yam_contact import physical_state,model_checks
from collect_demonstrations import task_hashes


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--selection',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--stride',type=int,default=4);a=p.parse_args()
 selected=json.loads(a.selection.read_text());trials=selected['trials'];assert len(trials)==4
 proposal_path=Path(trials[0]['trace']).parent/'proposal.json';proposal=json.loads(proposal_path.read_text())
 assert task_hashes('tasks/yam_contact_curriculum')==proposal['task_hashes'],'Task provenance changed'
 for path,expected in proposal.get('source_sha256',{}).items():assert sha(path)==expected,'Source changed: '+path
 a.out.mkdir(parents=True,exist_ok=False)
 try:font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17);titlefont=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',21)
 except OSError:font=titlefont=ImageFont.load_default()
 states=[]
 for t in trials:
  e=CurriculumEnv('tasks/yam_contact_curriculum')
  if 'case_spec' in t:
   from check_skill_layout_cases import reset_case
   realized=reset_case(e,t['case_spec'])
  else:realized=reset_challenge(e,t['seed'],t['profile_spec'])
  assert realized==t['realized'],'Realized reset differs from recorded challenge'
  checks=model_checks(e);assert checks['passed']
  rows=json.loads(Path(t['trace']).read_text());actions=np.load(t['actions'])['actions'];assert len(rows)==len(actions)
  r=mujoco.Renderer(e.model,height=360,width=640);close=mujoco.MjvCamera();close.azimuth=135;close.elevation=-24;close.distance=.28
  states.append(dict(env=e,renderer=r,cam=close,trial=t,rows=rows,actions=actions,maxerr={},mismatches=[],last=None,checks=checks))
 dt=states[0]['env'].model.opt.timestep*states[0]['env'].frame_skip;maxsteps=max(len(s['actions']) for s in states)
 writer=imageio.get_writer(a.out/'four-physical-generalization-trials.mp4',fps=1/(a.stride*dt),codec='libx264',quality=7,macro_block_size=1)
 picked=set([0,maxsteps//4,maxsteps//2,3*maxsteps//4,maxsteps-1]);frames={}
 try:
  for index in range(maxsteps):
   for s in states:
    if index>=len(s['actions']):continue
    _,_,done,trunc,info=s['env'].step(s['actions'][index]);actual={**info,**physical_state(s['env'])};old=s['rows'][index];s['last']=actual
    for key,value in old.items():
     if key in ('step','phase','peg_contacts') or key not in actual:continue
     if isinstance(value,(int,float)) and not isinstance(value,bool):s['maxerr'][key]=max(s['maxerr'].get(key,0.),abs(float(value)-float(actual[key])))
     elif value!=actual[key]:s['mismatches'].append({'step':index+1,'key':key,'old':value,'actual':actual[key]})
    if (done or trunc) and index!=len(s['actions'])-1:raise ValueError('Replay stopped early')
   if index%a.stride and index not in picked and index!=maxsteps-1:continue
   canvas=Image.new('RGB',(1280,1016),(10,20,30));d=ImageDraw.Draw(canvas)
   d.text((12,7),'Frozen learned micro-policies | four real simulator rollouts | exact saved-action replay',font=titlefont,fill='white')
   d.text((12,34),'Privileged state; scripted target frames, guards, IK and grip/angular stabilization. Yaw = vertical-axis rotation, not hole tilt.',font=font,fill=(205,222,231))
   for j,s in enumerate(states):
    e,r=s['env'],s['renderer'];r.update_scene(e.data,camera='overview');overview=r.render().copy()
    s['cam'].lookat[:]=e.data.site_xpos[e.task.pid]+np.array([0,0,.035]);r.update_scene(e.data,camera=s['cam']);inset=Image.fromarray(r.render().copy()).resize((274,154))
    panel=Image.new('RGB',(640,476),(16,30,42));panel.paste(Image.fromarray(overview),(0,0));panel.paste(inset,(364,204))
    draw=ImageDraw.Draw(panel);t=s['trial'];z=s['last'];real=t['realized'];peg=(np.array(real['peg_position_m'][:2])-np.array([.26,-.08]))*1000;socket=(np.array(real['socket_goal'][:2])-np.array([.32,0]))*1000
    finished=index>=len(s['actions'])-1;phase=s['rows'][min(index,len(s['rows'])-1)]['phase'];status=('SUCCESS' if z['is_success'] else 'FAILED')+' / final paused' if finished else phase
    draw.text((10,365),f"Seed {t['seed']} | t={e.data.time:.2f}s | {status}",font=font,fill=(132,238,170) if z['is_success'] else (255,218,127))
    draw.text((10,389),f"Peg XY {peg[0]:+.1f}, {peg[1]:+.1f}mm | Socket XY {socket[0]:+.1f}, {socket[1]:+.1f}mm",font=font,fill='white')
    draw.text((10,413),f"Relative key yaw {np.degrees(real['relative_socket_yaw_rad']):+.1f}deg | Mass {real['mass_scale']:.2f}x | Friction {real['sliding_friction_scale']:.2f}x",font=font,fill='white')
    draw.text((10,437),f"Tip {z['peg_z_m']*1000:.1f}mm | Peak contact {z['episode_peak_force_n']:.1f}N",font=font,fill=(197,218,228))
    canvas.paste(panel,((j%2)*640,64+(j//2)*476))
   if index%a.stride==0 or index==maxsteps-1:writer.append_data(np.asarray(canvas))
   if index in picked:frames[index]=canvas
 finally:
  writer.close()
  for s in states:s['renderer'].close();s['env'].close()
 audits=[]
 for s in states:
  audits.append({'seed':s['trial']['seed'],'realized':s['trial']['realized'],'max_numeric_errors':s['maxerr'],'categorical_mismatches':s['mismatches'],'exact_telemetry':not s['mismatches'] and all(v<=1e-8 for v in s['maxerr'].values()),'final':s['last'],'action_sha256':sha(s['trial']['actions']),'trace_sha256':sha(s['trial']['trace']),'model_checks':s['checks']})
 report={'proposal_sha256':sha(proposal_path),'selection_sha256':sha(a.selection),'renderer_sha256':sha(__file__),'trials':audits,'no_new_policy_actions':True,'changes_only_at_original_declared_reset':True,'qpos_comparison':'Original trace has no complete qpos arrays; only recorded telemetry compared.','finished_panels':'Hold final recorded state, explicitly labeled paused; no extra physics steps.','angle_scope':'Key/socket yaw about vertical axis. No roll/pitch or tilted-hole challenge.'}
 (a.out/'audit.json').write_text(json.dumps(report,indent=2))
 for index,frame in frames.items():frame.save(a.out/f'grid-step-{index+1}.jpg',quality=93)
 assert all(x['exact_telemetry'] for x in audits),'Do not use mismatched replay video'
 print(json.dumps([{'seed':x['seed'],'success':x['final']['is_success'],'maxerror':max(x['max_numeric_errors'].values())} for x in audits]),flush=True)
if __name__=='__main__':main()
