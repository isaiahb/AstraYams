from pathlib import Path
import sys,json,argparse,numpy as np,mujoco
import xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'multi-harvest'))
import env_multi as env
from canopy import build

def run(tag,scale=1,segments=5,contact=True,duration=14,timestep=.001):
 path=build(scale,segments,tag);tree=ET.parse(path);tree.find('option').set('timestep',str(timestep));tree.write(path,encoding='unicode');old=env.build_scene;env.build_scene=lambda:path
 try:e=env.MultiEnv()
 finally:env.build_scene=old
 e.reset(seed=1);m,d=e.model,e.data;m.opt.timestep=timestep
 if not contact:m.geom_contype[m.geom('probe_surface').id]=0;m.geom_conaffinity[m.geom('probe_surface').id]=0
 ids=[m.body('crop_fruit_'+str(j)).id for j in [2,3,4]]
 def positions():return np.array([d.geom_xpos[m.geom('crop'+str(j)+'_berry_collision').id] for j in [2,3,4]])
 pa=np.array([m.joint('probe_'+str(i)).qposadr[0] for i in range(3)]);ai=[m.actuator('probe_'+str(i)).id for i in range(3)]
 d.qpos[pa]=[.85,.05,.35];d.ctrl[ai]=d.qpos[pa];mujoco.mj_forward(m,d)
 records=[];qs=[];ts=[];ps=[];force_peak=0;count=0;penetration=0;allforces=0;target=None
 for k in range(round(duration/m.opt.timestep)):
  t=float(d.time)
  if k==round(5/m.opt.timestep):
   # Set probe at experiment start only, clear of fruit, following plant settling.
   origin=positions()[0];start=origin+[-.06,0,0];end=origin+[.018,0,0];d.qpos[pa]=start;d.qvel[[m.joint('probe_'+str(i)).dofadr[0] for i in range(3)]]=0;target=start.copy();mujoco.mj_forward(m,d)
  if target is not None:
   if t<6.2:u=np.clip((t-5)/1.2,0,1);target=start+(end-start)*(u*u*(3-2*u))
   elif t<6.5:target=end
   elif t<7.7:u=np.clip((t-6.5)/1.2,0,1);target=end+(start-end)*(u*u*(3-2*u))
   else:target=start
   d.ctrl[ai]=target
  for side,arm in e.arms.items():
   d.ctrl[arm['act']]=np.clip(180*(arm['target']-d.qpos[arm['q']])-14*d.qvel[arm['v']]+d.qfrc_bias[arm['v']],-10,10);d.ctrl[m.actuator(side+'_grip').id]=25
  mujoco.mj_step(m,d)
  for ci,c in enumerate(d.contact):
   if m.geom('probe_surface').id in c.geom:
    other=int(c.geom[1] if c.geom[0]==m.geom('probe_surface').id else c.geom[0]);name=m.geom(other).name
    if name and (name.startswith('crop') or name.startswith('pedicel')):
     f=np.zeros(6);mujoco.mj_contactForce(m,d,ci,f);force_peak=max(force_peak,float(abs(f[0])));count+=1;penetration=max(penetration,float(-c.dist));allforces+=abs(f[0])*m.opt.timestep
  if k%round(.04/m.opt.timestep)==0:
   qs.append(d.qpos.copy());ts.append(d.time);ps.append(positions());records.append({'t':d.time,'probe':d.xpos[m.body('test_probe').id].tolist()})
  if not np.all(np.isfinite(d.qpos)) or any(w.number for w in d.warning):break
 out=P/tag;np.savez_compressed(out/'rollout.npz',qpos=qs,t=ts,fruit=ps);(out/'trace.json').write_text(json.dumps(records))
 report={'tag':tag,'seconds':d.time,'fruits':8,'probe_contact_steps':count,'peak_probe_force_n':force_peak,'probe_impulse_ns':allforces,'max_probe_penetration_m':penetration,'finite':bool(np.all(np.isfinite(d.qpos))),'valid_run':bool(abs(d.time-duration)<.01 and not any(w.number for w in d.warning)),'warnings':[int(w.number) for w in d.warning],'stiffness_scale':scale,'segments':segments,'timestep_s':timestep,'contact_enabled':contact,'scope':'Force-limited diagnostic probe. Robot holds pose. No harvest or learned policy claim.'};(out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True);e.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--tag',default='contact');p.add_argument('--scale',type=float,default=1);p.add_argument('--segments',type=int,default=5);p.add_argument('--no-contact',action='store_true');p.add_argument('--timestep',type=float,default=.001);p.add_argument('--duration',type=float,default=14);a=p.parse_args();run(a.tag,a.scale,a.segments,not a.no_contact,timestep=a.timestep,duration=a.duration)
